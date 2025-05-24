#!/usr/bin/env python
"""Main entry point for pyvanc package.

This module provides a command-line interface to extract and analyze VANC data,
with a focus on SCTE-104 messages in MXF files.
"""

import argparse
import datetime
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.syntax import Syntax
from rich.table import Table

from .extractors.mxf import extract_scte104_from_mxf, extract_vanc_from_mxf
from .parsers.scte104 import parse_scte104
from .utils.scte104_utils import get_segmentation_type_name
from .utils.vanc_utils import VANCJSONEncoder, format_timecode

# Initialize Rich console
console = Console()


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """Set up logging configuration with Rich formatting.

    Args:
        verbose: Whether to enable verbose logging
        debug: Whether to enable debug logging
    """
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    # Configure rich logging
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )

    # Set separate log levels for specific modules if not in debug mode
    if not debug:
        logging.getLogger("pyvanc.extractors.mxf").setLevel(logging.WARNING)
        logging.getLogger("pyvanc.parsers.scte104").setLevel(logging.WARNING)


def extract_scte104_events(
    input_file: str,
    framerate: float = 25.0,
    frame_offset: int = 0,
    show_progress: bool = True,
    use_pts_time: bool = False,
) -> List[Dict[str, Any]]:
    """Extract SCTE-104 events from an MXF file with progress indicator.

    Args:
        input_file: Path to the MXF file
        framerate: Frame rate of the video
        frame_offset: Optional frame offset to adjust timecodes
        show_progress: Whether to show a progress spinner
        use_pts_time: Whether to use PTS time from the MXF file instead of frame-based timecode

    Returns:
        List of event dictionaries with timecode and type information
    """
    events = []

    # Use context manager for progress display
    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Extracting SCTE-104 events..."),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Extracting", total=None)

            for frame_idx, pts_time, scte104_msg in extract_scte104_from_mxf(
                input_file
            ):
                # Process events (same as before)
                events.extend(
                    _process_scte104_message(
                        frame_idx,
                        pts_time,
                        scte104_msg,
                        framerate,
                        frame_offset,
                        use_pts_time,
                    )
                )
                progress.update(task)
    else:
        # Extract without progress display
        for frame_idx, pts_time, scte104_msg in extract_scte104_from_mxf(input_file):
            events.extend(
                _process_scte104_message(
                    frame_idx,
                    pts_time,
                    scte104_msg,
                    framerate,
                    frame_offset,
                    use_pts_time,
                )
            )

    return events


def _process_scte104_message(
    frame_idx: int,
    pts_time: float,
    scte104_msg: Any,
    framerate: float,
    frame_offset: int = 0,
    use_pts_time: bool = False,
) -> List[Dict[str, Any]]:
    """Process a SCTE-104 message into events.

    Args:
        frame_idx: Frame index
        pts_time: Presentation timestamp in seconds
        scte104_msg: SCTE-104 message
        framerate: Frame rate
        frame_offset: Optional frame offset to adjust timecodes
        use_pts_time: Whether to use PTS time from the MXF file instead of frame-based timecode

    Returns:
        List of event dictionaries
    """
    events = []

    # Calculate timecode
    if use_pts_time:
        # Use the actual PTS time from the MXF file
        total_seconds = int(pts_time)
        remaining_frames = int((pts_time - total_seconds) * framerate)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        timecode = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{remaining_frames:02d}"
    else:
        # Use frame-based timecode with offset
        timecode = format_timecode(frame_idx, framerate, frame_offset)

    # Base event info
    event_base = {
        "frame": frame_idx,
        "pts_time": pts_time,
        "timecode": timecode,
        "message_type": scte104_msg.type,
        "protocol_version": scte104_msg.protocol_version,
    }

    # Process each operation in the message
    if scte104_msg.operations:
        for op in scte104_msg.operations:
            event = event_base.copy()
            event["operation_type"] = op.type
            event["operation_id"] = f"0x{op.opid:04x}"

            # Check if operation has segmentation data
            if op.data and "segmentation_type_id" in op.data:
                type_id = op.data["segmentation_type_id"]
                event_id = op.data.get("segmentation_event_id", 0)

                # Add segmentation data
                event["segmentation_type_id"] = type_id
                event["segmentation_type_name"] = get_segmentation_type_name(type_id)
                event["event_id"] = event_id
                event["event_id_hex"] = f"0x{event_id:08x}"

            events.append(event)

    return events


def get_event_color(event_type: str) -> str:
    """Get color for event based on type.

    Args:
        event_type: Event type name

    Returns:
        Color name for Rich formatting
    """
    if "Program Boundary" in event_type:
        return "bright_green"
    elif "Content Marker" in event_type:
        return "bright_yellow"
    elif "Advertisement" in event_type:
        return "bright_cyan"
    elif "Chapter" in event_type:
        return "bright_magenta"
    elif "Break" in event_type:
        return "bright_red"
    else:
        return "bright_white"


def get_mxf_timecode_info(input_file: str) -> Optional[Dict[str, Any]]:
    """Get timecode and duration information from an MXF file.

    Args:
        input_file: Path to the MXF file

    Returns:
        Dictionary with timecode and duration information or None if not available
    """
    try:
        # Run ffprobe to get file metadata
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",  # To get framerate for total frame calculation
            input_file,
        ]

        result = subprocess.run(
            cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        data = json.loads(result.stdout)
        timecode_info = {}

        # Extract format information
        if "format" in data:
            format_data = data["format"]
            if "duration" in format_data:
                timecode_info["duration_seconds"] = float(format_data["duration"])

            if "tags" in format_data:
                tags = format_data["tags"]
                if "timecode" in tags:
                    timecode_info["start_timecode_str"] = tags["timecode"]
                if "creation_time" in tags:
                    timecode_info["creation_time_utc_str"] = tags["creation_time"]
                elif "modification_date" in tags:
                    timecode_info["creation_time_utc_str"] = tags["modification_date"]

        # Extract framerate from the first video stream for total frame calculation
        if "streams" in data:
            for stream in data["streams"]:
                if stream.get("codec_type") == "video":
                    if "r_frame_rate" in stream:
                        num, den = map(int, stream["r_frame_rate"].split("/"))
                        if den > 0:
                            timecode_info["framerate"] = num / den
                            break

        return timecode_info if timecode_info else None

    except Exception as e:
        logging.warning(f"Failed to get timecode info: {e}")
        return None


def convert_pts_to_utc(pts_time: float, timecode_info: Dict[str, Any]) -> Optional[str]:
    """Convert PTS time to UTC time if possible.

    Args:
        pts_time: The presentation timestamp in seconds
        timecode_info: Timecode information from the MXF file

    Returns:
        UTC time string or None if conversion not possible
    """
    try:
        if "creation_time" in timecode_info:
            # Parse the creation time
            creation_time_str = timecode_info["creation_time"]

            # Handle different datetime formats
            try:
                # Try ISO format first
                creation_time = datetime.datetime.fromisoformat(
                    creation_time_str.replace("Z", "+00:00")
                )
            except ValueError:
                # Try other common formats
                for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S"):
                    try:
                        creation_time = datetime.datetime.strptime(
                            creation_time_str, fmt
                        )
                        break
                    except ValueError:
                        continue
                else:
                    return None  # No format matched

            # Add the PTS time to get the actual UTC time
            event_time = creation_time + datetime.timedelta(seconds=pts_time)

            # Return formatted UTC time
            return event_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "Z"

        return None

    except Exception as e:
        logging.warning(f"Failed to convert to UTC: {e}")
        return None


def extract_command(args: argparse.Namespace) -> None:
    """Execute the extract command with Rich formatting.

    Args:
        args: Command line arguments
    """
    input_file = args.input_file
    output_file = args.output
    framerate = args.framerate
    format_type = args.format
    frame_offset = args.frame_offset
    use_pts_time = args.use_pts_time
    show_utc = args.show_utc

    # Validate input file
    if not Path(input_file).exists():
        console.print(f"[bold red]Error:[/] Input file '{input_file}' does not exist")
        sys.exit(1)

    # Get timecode info if showing UTC
    timecode_info = None
    if show_utc:
        timecode_info = get_mxf_timecode_info(input_file)
        if not timecode_info or "creation_time" not in timecode_info:
            console.print(
                "[yellow]Warning:[/] Could not extract UTC time information, falling back to relative timecode"
            )
            show_utc = False

    # Extract SCTE-104 events
    try:
        events = extract_scte104_events(
            input_file, framerate, frame_offset, True, use_pts_time
        )

        # Add UTC time if requested
        if show_utc and timecode_info:
            for event in events:
                utc_time = convert_pts_to_utc(event["pts_time"], timecode_info)
                if utc_time:
                    event["utc_time"] = utc_time

    except Exception as e:
        console.print(f"[bold red]Error extracting SCTE-104 data:[/] {e}")
        sys.exit(1)

    # Output results based on format
    if format_type == "json":
        # JSON output
        json_output = json.dumps(events, cls=VANCJSONEncoder, indent=2)

        if output_file:
            with open(output_file, "w") as f:
                f.write(json_output)
            console.print(f"[green]SCTE-104 data written to {output_file}[/]")
        else:
            # Pretty-print JSON
            syntax = Syntax(json_output, "json", theme="monokai", line_numbers=True)
            console.print(syntax)

    else:
        # Rich table output
        if events:
            # Create header
            console.print()
            console.print(
                Panel(
                    f"[bold]Found {len(events)} SCTE-104 events in [cyan]{input_file}[/]",
                    border_style="blue",
                )
            )

            # Create table
            table = Table(
                title="SCTE-104 EVENTS SUMMARY",
                box=box.ROUNDED,
                header_style="bold white on blue",
                border_style="blue",
                min_width=100,
            )

            # Add columns
            if show_utc and any("utc_time" in event for event in events):
                table.add_column("UTC TIME", style="bright_magenta", no_wrap=True)
            table.add_column("TIMECODE", style="bright_cyan", no_wrap=True)
            table.add_column("FRAME", justify="right", style="bright_white")
            table.add_column("EVENT TYPE", style="bright_white")
            table.add_column("EVENT ID", no_wrap=True, style="bright_white")

            # Add rows
            for event in sorted(events, key=lambda e: e["frame"]):
                # Get event description
                if "segmentation_type_name" in event:
                    event_type = event["segmentation_type_name"]
                else:
                    event_type = event["message_type"]

                # Get event ID if available
                event_id = event.get("event_id_hex", "N/A")

                # Get color based on event type
                color = get_event_color(event_type)

                # Create row
                row_data = []
                if show_utc and "utc_time" in event:
                    row_data.append(event["utc_time"])
                row_data.extend(
                    [
                        event["timecode"],
                        str(event["frame"]),
                        f"[{color}]{event_type}[/]",
                        event_id,
                    ]
                )

                table.add_row(*row_data)

            # Print the table
            console.print(table)

        else:
            console.print("[yellow]No SCTE-104 events found in the MXF file[/]")


def analyze_command(args: argparse.Namespace) -> None:
    """Execute the analyze command with Rich formatting.

    Args:
        args: Command line arguments
    """
    input_file = args.input_file
    output_file = args.output
    cli_framerate = args.framerate
    frame_offset = args.frame_offset
    use_pts_time = args.use_pts_time
    show_utc = args.show_utc

    # Validate input file
    if not Path(input_file).exists():
        console.print(f"[bold red]Error:[/] Input file '{input_file}' does not exist")
        sys.exit(1)

    # Get timecode info from MXF
    mxf_info = get_mxf_timecode_info(input_file)

    # Determine framerate: use CLI arg, then MXF metadata, then default
    framerate = cli_framerate
    if mxf_info and "framerate" in mxf_info:
        framerate = mxf_info["framerate"]
        logging.info(f"Detected framerate from MXF: {framerate:.2f} fps")
    else:
        logging.info(f"Using specified or default framerate: {framerate:.2f} fps")

    start_timecode_offset_seconds = 0.0
    start_timecode_str = "00:00:00:00"  # Default if not in MXF
    if mxf_info and "start_timecode_str" in mxf_info:
        start_timecode_str = mxf_info["start_timecode_str"]
        try:
            tc_parts = list(map(int, start_timecode_str.split(":")))
            if len(tc_parts) == 4:
                start_timecode_offset_seconds = (
                    tc_parts[0] * 3600
                    + tc_parts[1] * 60
                    + tc_parts[2]
                    + tc_parts[3] / framerate
                )
                logging.info(
                    f"MXF start timecode {start_timecode_str} translates to {start_timecode_offset_seconds:.3f}s offset."
                )
        except ValueError:
            logging.warning(f"Could not parse MXF start timecode: {start_timecode_str}")

    # Extract SCTE-104 events for analysis
    try:
        events = extract_scte104_events(
            input_file, framerate, frame_offset, True, use_pts_time
        )

        # Adjust pts_time and recalculate timecode if MXF start_timecode is present
        # This ensures event timecodes are relative to the MXF's embedded start timecode
        logging.info(
            f"Adjusting event timestamps by MXF start timecode offset: {start_timecode_offset_seconds:.3f}s"
        )
        for event in events:
            event["pts_time"] += start_timecode_offset_seconds
            # Recalculate timecode string based on new pts_time
            total_seconds_event = int(event["pts_time"])
            remaining_frames_event = int(
                (event["pts_time"] - total_seconds_event) * framerate
            )
            hours_event = total_seconds_event // 3600
            minutes_event = (total_seconds_event % 3600) // 60
            seconds_event = total_seconds_event % 60
            event["timecode"] = (
                f"{hours_event:02d}:{minutes_event:02d}:{seconds_event:02d}:{remaining_frames_event:02d}"
            )

        # Add UTC time if requested
        if show_utc and mxf_info and "creation_time_utc_str" in mxf_info:
            for event in events:
                # For UTC, add the event's original pts_time (relative to stream start) to file's creation_time.
                original_pts_time = (
                    event["pts_time"] - start_timecode_offset_seconds
                )  # Get original relative PTS
                utc_time = convert_pts_to_utc(original_pts_time, mxf_info)
                if utc_time:
                    event["utc_time"] = utc_time

    except Exception as e:
        console.print(f"[bold red]Error extracting SCTE-104 data:[/] {e}")
        sys.exit(1)

    # Display Clip Info Panel
    if mxf_info:
        clip_info_table = Table(
            box=box.MINIMAL, show_header=False, padding=(0, 1), show_edge=False
        )
        clip_info_table.add_column(style="dim italic", justify="right")
        clip_info_table.add_column()

        clip_info_table.add_row(
            "Filename:", f"[bright_white]{Path(input_file).name}[/]"
        )

        if "start_timecode_str" in mxf_info:
            clip_info_table.add_row(
                "Clip Start Timecode:",
                f"[bright_cyan]{mxf_info['start_timecode_str']}[/]",
            )

        clip_duration_sec = mxf_info.get("duration_seconds", 0.0)
        total_seconds_duration = int(clip_duration_sec)
        remaining_frames_duration = int(
            (clip_duration_sec - total_seconds_duration) * framerate
        )
        hours_duration = total_seconds_duration // 3600
        minutes_duration = (total_seconds_duration % 3600) // 60
        seconds_duration = total_seconds_duration % 60
        duration_timecode_str = f"{hours_duration:02d}:{minutes_duration:02d}:{seconds_duration:02d}:{remaining_frames_duration:02d}"

        clip_info_table.add_row(
            "Clip Duration (TC):", f"[bright_yellow]{duration_timecode_str}[/]"
        )
        clip_info_table.add_row(
            "Clip Duration (sec):", f"{clip_duration_sec:.2f} seconds"
        )

        total_frames = int(clip_duration_sec * framerate)
        clip_info_table.add_row(
            "Total Frames:", f"[bright_white]{total_frames}[/] (at {framerate:.2f} fps)"
        )

        if "creation_time_utc_str" in mxf_info:
            clip_info_table.add_row(
                "Clip Creation UTC:",
                f"[bright_magenta]{mxf_info['creation_time_utc_str']}[/]",
            )
            try:
                creation_dt = datetime.datetime.fromisoformat(
                    mxf_info["creation_time_utc_str"].replace("Z", "+00:00")
                )
                end_dt = creation_dt + datetime.timedelta(seconds=clip_duration_sec)
                clip_info_table.add_row(
                    "Clip End UTC:",
                    f"[bright_magenta]{end_dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'}[/]",
                )
            except ValueError:
                pass

        console.print(
            Panel(
                clip_info_table,
                title="[bold blue]MXF Clip Information[/]",
                border_style="blue",
                expand=False,
            )
        )

    # Analyze the events
    if events:
        # Create header
        console.print()
        console.print(
            Panel(
                f"[bold]Analyzing {len(events)} SCTE-104 events in [cyan]{input_file}[/]",
                border_style="blue",
            )
        )

        # Categorize events
        program_boundaries = []
        content_markers = []
        other_events = []

        for event in events:
            if "segmentation_type_name" in event:
                type_name = event["segmentation_type_name"]
                if "Program Boundary" in type_name:
                    program_boundaries.append(event)
                elif "Content Marker" in type_name:
                    content_markers.append(event)
                else:
                    other_events.append(event)
            else:
                other_events.append(event)

        # Create combined table for all events
        table = Table(
            title="SCTE-104 Events Analysis",
            box=box.ROUNDED,
            header_style="bold white on blue",
            border_style="blue",
            min_width=100,
        )

        # Add columns
        table.add_column("CATEGORY", style="bright_white", no_wrap=True)
        table.add_column("EVENT TYPE", style="bright_white")
        if show_utc and any("utc_time" in event for event in events):
            table.add_column("UTC TIME", style="bright_magenta", no_wrap=True)
        table.add_column("TIMECODE", style="bright_cyan", no_wrap=True)
        table.add_column("FRAME", justify="right", style="bright_white")
        table.add_column("EVENT ID", no_wrap=True, style="bright_white")

        # Add all events in chronological order
        all_events = []
        for event in program_boundaries:
            event_copy = event.copy()
            event_copy["category"] = "Program Boundary"
            event_copy["category_color"] = "bright_green"
            all_events.append(event_copy)

        for event in content_markers:
            event_copy = event.copy()
            event_copy["category"] = "Content Marker"
            event_copy["category_color"] = "bright_yellow"
            all_events.append(event_copy)

        for event in other_events:
            event_copy = event.copy()
            event_copy["category"] = "Other"
            event_copy["category_color"] = "bright_blue"
            all_events.append(event_copy)

        # Sort all events by frame number
        all_events.sort(key=lambda e: e["frame"])

        # Add rows to table
        for event in all_events:
            category = event["category"]
            category_color = event["category_color"]

            # Get event type
            if "segmentation_type_name" in event:
                event_type = event["segmentation_type_name"]
                event_color = get_event_color(event_type)
            else:
                event_type = event["message_type"]
                event_color = "bright_white"

            # Get event ID
            event_id = event.get("event_id_hex", "N/A")

            # Create row
            row_data = [
                f"[{category_color}]{category}[/]",
                f"[{event_color}]{event_type}[/]",
            ]

            if show_utc and "utc_time" in event:
                row_data.append(event["utc_time"])

            row_data.extend(
                [
                    event["timecode"],
                    str(event["frame"]),
                    event_id,
                ]
            )

            table.add_row(*row_data)

        # Print the table
        console.print(table)

        # Calculate and display segment durations
        if len(program_boundaries) >= 2:
            # Create segment durations table
            duration_table = Table(
                title="Segment Durations",
                box=box.ROUNDED,
                header_style="bold black on bright_cyan",
                border_style="bright_cyan",
            )

            duration_table.add_column("SEGMENT", justify="right", style="bright_white")
            duration_table.add_column("START", style="bright_green")
            duration_table.add_column("END", style="bright_red")
            duration_table.add_column("DURATION", style="bright_cyan", justify="right")
            duration_table.add_column("FRAMES", justify="right", style="bright_white")

            boundaries = sorted(program_boundaries, key=lambda e: e["frame"])

            for i in range(len(boundaries) - 1):
                start = boundaries[i]
                end = boundaries[i + 1]
                frames = end["frame"] - start["frame"]
                seconds = frames / framerate
                minutes = seconds / 60

                duration_str = f"{minutes:.2f} min ({seconds:.2f} sec)"

                duration_table.add_row(
                    str(i + 1),
                    f"{start['timecode']}",
                    f"{end['timecode']}",
                    duration_str,
                    str(frames),
                )

            console.print()
            console.print(duration_table)
    else:
        console.print("[yellow]No SCTE-104 events found in the MXF file[/]")


def main() -> None:
    """Main entry point for pyvanc."""
    parser = argparse.ArgumentParser(
        description="Extract and analyze VANC/SCTE-104 data from MXF files"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Extract command
    extract_parser = subparsers.add_parser(
        "extract", help="Extract SCTE-104 events from an MXF file"
    )
    extract_parser.add_argument("input_file", help="Input MXF file")
    extract_parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    extract_parser.add_argument(
        "-f",
        "--framerate",
        type=float,
        default=25.0,
        help="Frame rate of the input file (default: 25.0)",
    )
    extract_parser.add_argument(
        "--frame-offset",
        type=int,
        default=0,
        help="Frame offset to adjust timecodes (default: 0, will use 137 for TESTSCHED1405.mxf)",
    )
    extract_parser.add_argument(
        "--use-pts-time",
        action="store_true",
        help="Use PTS time from MXF file instead of calculating from frame counts (more accurate)",
    )
    extract_parser.add_argument(
        "--show-utc",
        action="store_true",
        help="Show UTC timestamps based on file creation time and PTS values",
    )
    extract_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    extract_parser.set_defaults(func=extract_command)

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze SCTE-104 events in an MXF file"
    )
    analyze_parser.add_argument("input_file", help="Input MXF file")
    analyze_parser.add_argument(
        "-o", "--output", help="Output report file (default: stdout)"
    )
    analyze_parser.add_argument(
        "-f",
        "--framerate",
        type=float,
        default=25.0,
        help="Frame rate of the input file (default: 25.0)",
    )
    analyze_parser.add_argument(
        "--frame-offset",
        type=int,
        default=0,
        help="Frame offset to adjust timecodes (default: 0, will use 137 for TESTSCHED1405.mxf)",
    )
    analyze_parser.add_argument(
        "--use-pts-time",
        action="store_true",
        help="Use PTS time from MXF file instead of calculating from frame counts (more accurate)",
    )
    analyze_parser.add_argument(
        "--show-utc",
        action="store_true",
        help="Show UTC timestamps based on file creation time and PTS values",
    )
    analyze_parser.set_defaults(func=analyze_command)

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose, args.debug)

    # Execute command
    if hasattr(args, "func"):
        args.func(args)
    else:
        # Use Rich to display help
        console.print(
            Panel.fit(
                "[bold blue]PyVANC - VANC Data Extraction and Analysis Tool[/]",
                subtitle="[italic]Extract and analyze SCTE-104 messages from MXF files[/]",
            )
        )
        console.print()

        # Print command help
        parser.print_help()

        # Print example usage
        console.print()
        console.print(
            Panel(
                "[bold]Example usage:[/]\n"
                "  [cyan]pyvanc_cli.py extract MXFInputfiles/example.mxf[/]\n"
                "  [cyan]pyvanc_cli.py analyze MXFInputfiles/example.mxf[/]\n"
                "  [cyan]pyvanc_cli.py extract MXFInputfiles/example.mxf --format json -o output.json[/]",
                border_style="dim",
            )
        )

        sys.exit(1)


if __name__ == "__main__":
    main()

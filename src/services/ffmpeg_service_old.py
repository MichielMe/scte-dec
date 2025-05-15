"""
FFMPEG Service module for handling FFMPEG and FFProbe operations.

This module provides classes and functions to interact with FFMPEG and FFProbe
for analyzing media files, extracting frames, and generating thumbnails.
"""

import datetime
import json
import logging
import os
import subprocess
from math import modf
from pathlib import Path
from string import Template
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

from timecode import Timecode

from ..models.splice_event import SCTE104Packet

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
DID_SDID = ["4105", "4107", "4108"]
DID_SDID_TO_EXTRACT = "4107"
FRAME_RATE = 25
FRAME_DURATION = 40  # milliseconds


class FFMPEGResult(NamedTuple):
    """Result of an FFMPEG operation."""

    return_code: int
    args: str
    error: str


class FFProbeResult(NamedTuple):
    """Result of an FFProbe operation."""

    return_code: int
    json: str
    error: str


class Packet(NamedTuple):
    """Packet data extracted from FFProbe."""

    anc_data: List[str]
    pts_time: Timecode
    utc_time: Timecode
    pts_frame_number: int


class FFMPEGFrameData(NamedTuple):
    """Frame data with SCTE-104 information."""

    frame_number: int
    marker_type: str
    frame_text_data: Optional[SCTE104Packet]


class FFMPEGService:
    """
    Service for interacting with FFMPEG and FFProbe.

    This class provides methods to analyze media files, extract frames,
    and generate thumbnails using FFMPEG and FFProbe.
    """

    def __init__(
        self,
        did_sdid_to_extract: str = DID_SDID_TO_EXTRACT,
        frame_rate: int = FRAME_RATE,
        frame_duration: int = FRAME_DURATION,
    ):
        """
        Initialize the FFMPEG service.

        Args:
            did_sdid_to_extract: DID/SDID value to extract from the media file
            frame_rate: Frame rate of the media file
            frame_duration: Duration of each frame in milliseconds
        """
        self.did_sdid_to_extract = did_sdid_to_extract
        self.frame_rate = frame_rate
        self.frame_duration = frame_duration

    def analyze(self, filename: str) -> FFProbeResult:
        """
        Analyze a media file using FFProbe.

        Args:
            filename: Path to the media file

        Returns:
            FFProbeResult: Result of the FFProbe analysis
        """
        commands = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-select_streams",
            "2",
            "-show_packets",
            "-show_data",
            filename,
        ]

        logger.info(f"Analyzing file: {filename}")
        result = subprocess.run(
            commands,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        return FFProbeResult(
            return_code=result.returncode, json=result.stdout, error=result.stderr
        )

    def analyze_and_save_json(self, output_dir: Path, filename: str) -> None:
        """
        Analyze a media file using FFProbe and save the results to a JSON file.

        Args:
            output_dir: Directory to save the output JSON file
            filename: Path to the media file
        """
        result = self.analyze(filename)

        if result.return_code != 0:
            logger.error(f"Error analyzing file: {result.error}")
            return None

        try:
            # Ensure the output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)

            # Create the full file path
            output_file = output_dir / "output.json"

            # Parse the JSON
            parsed_json = json.loads(result.json)

            # Write the JSON to a file
            with output_file.open("w", encoding="utf-8") as f:
                json.dump(parsed_json, f, indent=2)

            logger.info(f"JSON result written to {output_file}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return None

    def parse_ffprobe_output(self, ffprobe_result: FFProbeResult) -> List[Packet]:
        """
        Parse the output of FFProbe.

        Args:
            ffprobe_result: Result of the FFProbe analysis

        Returns:
            List[Packet]: List of packets extracted from the media file
        """
        all_packets = []
        data = json.loads(ffprobe_result.json)

        start_timecode = data["format"]["tags"]["timecode"]

        for packet in data["packets"]:
            anc_packet = self._extract_packet(
                packet["data"], packet["pts_time"], start_timecode, packet["pts"]
            )

            if anc_packet is not None:
                all_packets.append(anc_packet)

        return all_packets

    def parse_ffprobe_json_output(self, input_file: Path) -> Optional[List[Packet]]:
        """
        Parse the output of FFProbe from a JSON file.

        Args:
            input_file: Path to the JSON file containing FFProbe output

        Returns:
            Optional[List[Packet]]: List of packets extracted from the media file,
                                   or None if there was an error
        """
        try:
            with input_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            all_packets = []
            start_timecode = data["format"]["tags"]["timecode"]

            for packet in data["packets"]:
                anc_packet = self._extract_packet(
                    packet["data"], packet["pts_time"], start_timecode, packet["pts"]
                )

                if anc_packet is not None:
                    all_packets.append(anc_packet)

            return all_packets

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return None
        except KeyError as e:
            logger.error(f"Missing key in JSON: {e}")
            return None

    def extract_thumbnails(
        self,
        video_filename: str,
        frames: List[FFMPEGFrameData],
        padding: int = 0,
        folder: Union[str, Path] = "",
    ) -> FFMPEGResult:
        """
        Extract thumbnails from a media file.

        Args:
            video_filename: Path to the media file
            frames: List of frame data with SCTE-104 information
            padding: Number of frames to include before and after each identified frame
            folder: Directory to save the thumbnails

        Returns:
            FFMPEGResult: Result of the FFMPEG operation
        """
        # Ensure padding is at least 2 frames
        if padding < 2:
            logger.warning(
                f"Padding was set to {padding}, increasing to minimum of 2 frames"
            )
            padding = 2

        # Log frame data
        for frame in frames:
            logger.debug(
                f"Frame: {frame.frame_number}, SCTE message: {frame.marker_type}"
            )

        # Extract frame numbers and organize by event
        frame_numbers = []
        all_frames_with_metadata = []

        # Group frames that are close to each other (likely part of the same event)
        event_groups = []
        sorted_frames = sorted(frames, key=lambda x: x.frame_number)

        current_group = []
        for frame in sorted_frames:
            if (
                not current_group
                or frame.frame_number - current_group[-1].frame_number <= 10
            ):
                current_group.append(frame)
            else:
                event_groups.append(current_group)
                current_group = [frame]

        if current_group:
            event_groups.append(current_group)

        logger.info(f"Identified {len(event_groups)} event groups")

        # Process each event group with proper padding
        for group_index, group in enumerate(event_groups):
            event_frame_numbers = [frame.frame_number for frame in group]
            min_frame = min(event_frame_numbers)
            max_frame = max(event_frame_numbers)

            logger.info(
                f"Group {group_index+1}: Event frames {event_frame_numbers}, adding {padding} frame padding"
            )

            # Calculate padding range ensuring we don't go below 0
            start_frame = max(0, min_frame - padding)
            end_frame = max_frame + padding

            # Add frames with padding to the list
            for frame_num in range(start_frame, end_frame + 1):
                if frame_num in event_frame_numbers:
                    # This is an event frame
                    frame_obj = next(f for f in group if f.frame_number == frame_num)
                    frame_numbers.append(frame_num)
                    all_frames_with_metadata.append(
                        {
                            "frame_number": frame_num,
                            "is_event": True,
                            "event_info": frame_obj,
                            "padding_for": None,
                        }
                    )
                else:
                    # This is a padding frame
                    closest_event = min(
                        event_frame_numbers, key=lambda x: abs(x - frame_num)
                    )
                    frame_numbers.append(frame_num)
                    all_frames_with_metadata.append(
                        {
                            "frame_number": frame_num,
                            "is_event": False,
                            "event_info": None,
                            "padding_for": closest_event,
                        }
                    )

        logger.info(f"Total frames to extract (with padding): {len(frame_numbers)}")

        # Check if we have frames to extract
        if not frame_numbers:
            logger.error("No frames to extract!")
            return FFMPEGResult(1, "", "No frames to extract")

        # Build the select string - make sure frame numbers are unique and sorted
        unique_frame_numbers = sorted(list(set(frame_numbers)))
        frame_number_selectstring = self._build_frame_select_string(
            unique_frame_numbers
        )

        # Build the drawtext command
        draw_text_command = self._build_improved_draw_text_command(
            unique_frame_numbers, all_frames_with_metadata
        )

        # Set output path
        if isinstance(folder, str):
            folder = Path(folder)
        outputpath = str(folder / "frames%d.jpg")

        # Create a mapping between sequential output numbers and actual frame numbers
        frame_number_mapping = {}
        for i, frame_num in enumerate(unique_frame_numbers, start=1):
            frame_number_mapping[i] = frame_num

        # Save the mapping to a file for later use by the HTML generator
        try:
            mapping_file = folder / "frame_mapping.json"
            with open(mapping_file, "w") as f:
                json.dump(frame_number_mapping, f)
            logger.info(f"Saved frame number mapping to {mapping_file}")
        except Exception as e:
            logger.error(f"Error saving frame number mapping: {e}")

        # Build FFMPEG command
        commands = [
            "ffmpeg",
            "-i",
            video_filename,
            "-vf",
            f"select={frame_number_selectstring},{draw_text_command}",
            "-fps_mode",
            "passthrough",
            "-frames",
            str(len(unique_frame_numbers)),
            outputpath,
        ]

        logger.info(f"Running FFMPEG to extract {len(unique_frame_numbers)} frames")
        result = subprocess.run(
            commands,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        if result.returncode != 0:
            logger.error(f"FFMPEG error: {result.stderr}")
        else:
            logger.info("FFMPEG completed successfully")

        # Generate metadata.json for visualization with frame mapping
        self._generate_improved_metadata_json(
            folder,
            all_frames_with_metadata,
            unique_frame_numbers,
            padding,
            frame_number_mapping,
        )

        return FFMPEGResult(
            return_code=result.returncode, args=str(commands), error=result.stderr
        )

    def _build_improved_draw_text_command(
        self,
        frame_numbers: List[int],
        all_frames_metadata: List[Dict[str, Any]],
    ) -> str:
        """
        Build an improved drawtext command for FFMPEG with better organization.

        Args:
            frame_numbers: List of all frame numbers to extract
            all_frames_metadata: List of metadata for all frames

        Returns:
            str: Drawtext command string
        """
        draw_text_command = ""
        n_frames = len(frame_numbers)

        for idx, frame_num in enumerate(frame_numbers, start=0):
            # Find the metadata for this frame
            frame_metadata = next(
                meta
                for meta in all_frames_metadata
                if meta["frame_number"] == frame_num
            )

            if frame_metadata["is_event"]:
                # This is an event frame
                frame_data = frame_metadata["event_info"]

                if frame_data.frame_text_data is None:
                    text = (
                        f"Frame_number = {frame_data.frame_number} "
                        f"Frame type = {frame_data.marker_type}"
                    )
                else:
                    text = (
                        f"Frame_number = {frame_data.frame_number} "
                        f"Frame type = {frame_data.marker_type}\n"
                        f"Type = {frame_data.frame_text_data.segmentation_type['name']}\n"
                        f"Event ID = {frame_data.frame_text_data.segmentation_event_id}\n"
                        f"Duration = {frame_data.frame_text_data.duration}"
                    )
            else:
                # This is a padding frame
                associated_event = frame_metadata["padding_for"]
                text = f"PADDING FRAME {frame_num} (for Event Frame {associated_event})"

            cmd = (
                f"drawtext=text='{text}'"
                f":x=(w-tw)/2:y=(h-th):fontsize=24:fontcolor=yellow:boxborderw=10:borderw=1:box=1:boxcolor=black@0.5:enable='eq(n,{idx})'"
            )

            draw_text_command += cmd

            if idx < n_frames - 1:
                draw_text_command += ","

        return draw_text_command

    def _generate_improved_metadata_json(
        self,
        folder: Path,
        all_frames_metadata: List[Dict[str, Any]],
        frame_numbers: List[int],
        padding: int,
        frame_number_mapping: Optional[Dict[int, int]] = None,
    ) -> None:
        """
        Generate an improved metadata.json file for the extracted frames.

        Args:
            folder: Directory to save the metadata.json file
            all_frames_metadata: List of metadata for all frames
            frame_numbers: List of all frame numbers (unique and sorted)
            padding: Number of frames included before and after each identified frame
            frame_number_mapping: Optional mapping from output number to original frame number
        """
        metadata = {
            "frames": [],
            "padding": padding,
            "total_frames": len(frame_numbers),
            "frame_groups": [],
            "frame_mapping": frame_number_mapping or {},
        }

        # Create frame metadata
        for frame_meta in all_frames_metadata:
            frame_number = frame_meta["frame_number"]

            if frame_meta["is_event"]:
                # This is an event frame
                frame_data = frame_meta["event_info"]
                frame_info = {
                    "frame_number": frame_number,
                    "type": frame_data.marker_type,
                    "is_padding": False,
                    "event_type": frame_data.marker_type,
                }

                # Add SCTE data if available
                if frame_data.frame_text_data:
                    scte_data = {
                        "event_timestamp": str(
                            frame_data.frame_text_data.splice_event_timestamp
                        ),
                        "pre_roll_time": frame_data.frame_text_data.pre_roll_time,
                        "segmentation_event_id": frame_data.frame_text_data.segmentation_event_id,
                        "duration": frame_data.frame_text_data.duration,
                        "segmentation_upid": str(
                            frame_data.frame_text_data.segmentation_upid
                        ),
                    }

                    # Handle segmentation_type
                    if isinstance(frame_data.frame_text_data.segmentation_type, dict):
                        segmentation_type = {}
                        for (
                            key,
                            value,
                        ) in frame_data.frame_text_data.segmentation_type.items():
                            if isinstance(value, (str, int, float, bool, type(None))):
                                segmentation_type[key] = value
                            else:
                                segmentation_type[key] = str(value)
                        scte_data["segmentation_type"] = segmentation_type
                    else:
                        scte_data["segmentation_type"] = str(
                            frame_data.frame_text_data.segmentation_type
                        )

                    frame_info["scte_data"] = scte_data
            else:
                # This is a padding frame
                frame_info = {
                    "frame_number": frame_number,
                    "type": "Padding Frame",
                    "is_padding": True,
                    "padding_for": frame_meta["padding_for"],
                }

            metadata["frames"].append(frame_info)

        # Create event groups for better organization in the HTML view
        # Group frames by the events they belong to
        event_frames = [f for f in all_frames_metadata if f["is_event"]]
        event_frame_numbers = [f["frame_number"] for f in event_frames]

        for event_frame in sorted(event_frames, key=lambda x: x["frame_number"]):
            event_frame_num = event_frame["frame_number"]
            event_type = event_frame["event_info"].marker_type

            # Get padding frames for this event
            padding_frames = [
                f
                for f in all_frames_metadata
                if not f["is_event"] and f["padding_for"] == event_frame_num
            ]

            # Create a group with this event frame and its padding
            group_frames = padding_frames + [event_frame]
            group_frames.sort(key=lambda x: x["frame_number"])

            group_info = {
                "event_frame": event_frame_num,
                "event_type": event_type,
                "frames": [f["frame_number"] for f in group_frames],
            }

            metadata["frame_groups"].append(group_info)

        # Sort all frames by frame number
        metadata["frames"].sort(key=lambda x: x["frame_number"])
        metadata["frame_groups"].sort(key=lambda x: x["event_frame"])

        # Write metadata to file
        metadata_file = folder / "metadata.json"
        try:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Metadata written to {metadata_file}")
        except TypeError as e:
            logger.error(f"Error serializing metadata to JSON: {e}")
            # Fallback: Write a simplified version
            simplified_metadata = {
                "frames": [
                    {
                        "frame_number": frame["frame_number"],
                        "type": frame["type"],
                        "is_padding": frame.get("is_padding", False),
                    }
                    for frame in metadata["frames"]
                ],
                "padding": padding,
                "total_frames": len(frame_numbers),
                "frame_mapping": frame_number_mapping or {},
            }
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(simplified_metadata, f, indent=2)
            logger.info(
                f"Simplified metadata written to {metadata_file} due to serialization issues"
            )

    def _extract_frame_numbers(self, frame_data: List[FFMPEGFrameData]) -> List[int]:
        """
        Extract frame numbers from frame data.

        Args:
            frame_data: List of frame data

        Returns:
            List[int]: List of frame numbers
        """
        return [frame.frame_number for frame in frame_data]

    def _build_frame_select_string(self, frame_numbers: List[int]) -> str:
        """
        Build the frame select string for FFMPEG.

        Args:
            frame_numbers: List of frame numbers

        Returns:
            str: Frame select string
        """
        frame_number_selectstring = "'"
        n_frames = len(frame_numbers)

        for idx, frame_number in enumerate(frame_numbers, start=1):
            frame_number_selectstring += f"eq(n,{frame_number})"

            if idx < n_frames:
                frame_number_selectstring += "+"

        frame_number_selectstring += "'"

        return frame_number_selectstring

    def _extract_packet(
        self,
        packet_data: str,
        pts_time: str,
        start_timecode: str,
        pts_frame_number: int,
    ) -> Optional[Packet]:
        """
        Extract packet data from an FFProbe packet.

        Args:
            packet_data: Packet data string
            pts_time: Presentation timestamp
            start_timecode: Start timecode of the media file
            pts_frame_number: Presentation timestamp frame number

        Returns:
            Optional[Packet]: Extracted packet data, or None if no relevant data was found
        """
        anc_packet = ""

        # Convert fractional time
        ms, seconds = modf(float(pts_time))
        seconds = datetime.timedelta(seconds=seconds)
        ms = self._ms_to_frames(ms)

        # Format file timestamp
        file_timestamp = Template("0${seconds}:${ms}")
        file_timestamp = file_timestamp.substitute(seconds=seconds, ms=ms)

        # Convert to Timecode objects
        start_timecode = Timecode(self.frame_rate, start_timecode)
        file_timestamp = Timecode(self.frame_rate, file_timestamp)

        # Calculate adjusted timestamp
        adjusted_timestamp = start_timecode + file_timestamp
        adjusted_timestamp.add_frames(-1)  # Timecode module calculates 1 frame off

        # Parse packet data
        packet_data_per_line = packet_data.split("\n")

        for line in packet_data_per_line[1:]:
            data_per_line = line.split(" ")

            # Ignore memory address at [0] and empty space at [9] and decoded symbols at [10]
            for hex_data in data_per_line[1:9]:
                if hex_data in DID_SDID:
                    # New packet of interest found
                    if anc_packet == "":
                        anc_packet += hex_data
                    else:
                        # We're at the beginning of a new ANC packet, export the latest built packet
                        if anc_packet[0:4] == self.did_sdid_to_extract:
                            return Packet(
                                anc_packet,
                                file_timestamp,
                                adjusted_timestamp,
                                pts_frame_number,
                            )
                        # Reset to build a new packet
                        anc_packet = hex_data
                else:
                    # Still building the ANC packet
                    if len(anc_packet) > 0:
                        anc_packet += hex_data

        # Check if we have a final packet to return
        if anc_packet and anc_packet[0:4] == self.did_sdid_to_extract:
            return Packet(
                anc_packet, file_timestamp, adjusted_timestamp, pts_frame_number
            )

        return None

    def _ms_to_frames(self, ms: float) -> int:
        """
        Convert milliseconds to frames.

        Args:
            ms: Milliseconds

        Returns:
            int: Equivalent number of frames
        """
        return round((ms / self.frame_duration) * 1000)

#!/usr/bin/env python
"""Command-line interface for pyvanc."""

import argparse
import json
import logging
import sys
from pathlib import Path

from .extractors.mxf import extract_scte104_from_mxf, extract_vanc_from_mxf
from .utils.vanc_utils import VANCJSONEncoder


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration.

    Args:
        verbose: Whether to enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def extract_vanc_command(args: argparse.Namespace) -> None:
    """Execute the extract-vanc command.

    Args:
        args: Command line arguments
    """
    input_file = args.input_file
    output_file = args.output_file
    scte104_only = args.scte104_only

    # Validate input file
    if not Path(input_file).exists():
        print(f"Error: Input file '{input_file}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Extract VANC data
    results = []

    try:
        if scte104_only:
            # Extract only SCTE-104 messages
            for frame_idx, scte104_msg in extract_scte104_from_mxf(input_file):
                results.append({"frame": frame_idx, "scte104": scte104_msg})
        else:
            # Extract all VANC packets
            for frame_idx, vanc_packets in extract_vanc_from_mxf(input_file):
                for packet in vanc_packets:
                    results.append({"frame": frame_idx, "vanc": packet})
    except Exception as e:
        print(f"Error extracting VANC data: {e}", file=sys.stderr)
        sys.exit(1)

    # Output results
    json_output = json.dumps(results, cls=VANCJSONEncoder, indent=2)

    if output_file:
        with open(output_file, "w") as f:
            f.write(json_output)
        print(f"VANC data written to {output_file}")
    else:
        print(json_output)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Extract and analyze VANC data from video files"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Extract VANC command
    extract_parser = subparsers.add_parser(
        "extract", help="Extract VANC data from a video file"
    )
    extract_parser.add_argument("input_file", help="Input video file (MXF format)")
    extract_parser.add_argument(
        "-o", "--output", dest="output_file", help="Output JSON file (default: stdout)"
    )
    extract_parser.add_argument(
        "--scte104",
        dest="scte104_only",
        action="store_true",
        help="Extract only SCTE-104 messages",
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Execute command
    if args.command == "extract":
        extract_vanc_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

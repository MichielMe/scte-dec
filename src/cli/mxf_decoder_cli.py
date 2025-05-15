import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from ..decoders.mxf_decoder import MXFDecoder
from ..utils.html_generator import generate_html_viewer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: Command-line arguments to parse. If None, use sys.argv

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="MXF decoder for extracting SCTE-104 messages and generating frame thumbnails"
    )

    parser.add_argument("filename", help="Path to the MXF file")

    parser.add_argument(
        "-o", "--output", help="Custom output folder path", default=None
    )

    parser.add_argument(
        "-p",
        "--padding",
        help="Number of frames to include before and after each identified frame",
        type=int,
        default=2,
    )

    parser.add_argument(
        "-v", "--verbose", help="Enable verbose output", action="store_true"
    )

    parser.add_argument(
        "--html", help="Generate HTML viewer for the results", action="store_true"
    )

    return parser.parse_args(args)


def setup_logging(verbose: bool) -> None:
    """
    Set up logging based on verbosity.

    Args:
        verbose: Whether to enable verbose output
    """
    log_level = logging.DEBUG if verbose else logging.INFO

    # Configure root logger
    logging.getLogger().setLevel(log_level)

    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    # Add console handler to root logger
    logging.getLogger().addHandler(console_handler)


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the MXF decoder CLI.

    Args:
        args: Command-line arguments to parse. If None, use sys.argv

    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    parsed_args = parse_args(args)

    # Set up logging
    setup_logging(parsed_args.verbose)

    # Get input file path
    file_path = Path(parsed_args.filename)

    # Setup output folder
    if parsed_args.output:
        output_folder = Path(parsed_args.output)
    else:
        output_folder = Path("results") / file_path.stem

    # Create MXF decoder
    decoder = MXFDecoder()

    # Decode MXF file
    try:
        success = decoder.decode(
            parsed_args.filename,
            str(output_folder) if parsed_args.output else None,
            parsed_args.padding,
        )

        if success:
            logger.info(f"Successfully decoded MXF file: {parsed_args.filename}")

            # Generate HTML viewer if requested
            if parsed_args.html:
                logger.info("Generating HTML viewer...")
                generate_html_viewer(output_folder, parsed_args.filename)
                logger.info(f"HTML viewer generated at {output_folder / 'index.html'}")
                logger.info(f"Open this file in your browser to view the frames")

            return 0
        else:
            logger.error(f"Failed to decode MXF file: {parsed_args.filename}")
            return 1

    except Exception as e:
        logger.exception(f"Error decoding MXF file: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

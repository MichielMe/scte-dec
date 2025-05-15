"""
MXF Decoder module for handling MXF files and extracting SCTE-104 messages.

This module provides classes and functions to decode MXF files and extract
relevant SCTE-104 messages and frame data.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

from ..models.splice_event import SCTE104Packet
from ..services.ffmpeg_service import FFMPEGFrameData, FFMPEGService
from ..utils.scte104_utils import decode_SCTE104

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MXFDecoder:
    """
    Class for decoding MXF files and extracting SCTE-104 messages.

    This class provides methods to analyze MXF files, extract SCTE-104 messages,
    and generate thumbnails for relevant frames.
    """

    # Default frame padding for thumbnails
    DEFAULT_PADDING = 2

    def __init__(self, ffmpeg_service: Optional[FFMPEGService] = None):
        """
        Initialize the MXF decoder.

        Args:
            ffmpeg_service: Optional custom FFMPEGService. If not provided, a default one will be created.
        """
        self.ffmpeg_service = ffmpeg_service or FFMPEGService()

    def decode(
        self,
        filename: str,
        output_folder: Optional[str] = None,
        padding: int = DEFAULT_PADDING,
    ) -> bool:
        """
        Decode an MXF file and extract SCTE-104 messages.

        Args:
            filename: Path to the MXF file
            output_folder: Custom output folder path. If not provided, a default one will be created.
            padding: Number of frames to include before and after each identified frame

        Returns:
            bool: True if decoding was successful, False otherwise
        """
        file_path = Path(filename)

        # Validate input file
        if not file_path.is_file():
            logger.error(f"File does not exist: {filename}")
            return False

        # Set up output folder
        results_folder = self._setup_output_folder(file_path, output_folder)

        # Analyze file with ffprobe
        output_file = results_folder / "output.json"
        if not output_file.is_file():
            logger.info(
                f"No previous ffprobe result found. Analyzing MXF file: {filename}"
            )
            self.ffmpeg_service.analyze_and_save_json(results_folder, filename)

        # Parse ffprobe output
        logger.info("Parsing ffprobe output")
        ffprobe_output = self.ffmpeg_service.parse_ffprobe_json_output(output_file)

        if ffprobe_output is None:
            logger.error(f"Error parsing ffprobe output for {filename}")
            return False

        # Process SCTE-104 packets
        frame_data = self._process_scte104_packets(ffprobe_output)

        # Generate thumbnails
        logger.info("Extracting frame thumbnails")
        ffmpeg_result = self.ffmpeg_service.extract_thumbnails(
            filename, frame_data, padding, results_folder
        )

        if ffmpeg_result.return_code != 0:
            logger.error(f"Error generating thumbnails: {ffmpeg_result.error}")
            return False

        return True

    def _setup_output_folder(
        self, file_path: Path, custom_folder: Optional[str] = None
    ) -> Path:
        """
        Set up output folder for results.

        Args:
            file_path: Path to the input file
            custom_folder: Optional custom folder path

        Returns:
            Path: Path to the output folder
        """
        if custom_folder:
            output_folder = Path(custom_folder)
        else:
            output_folder = Path("results") / file_path.stem

        output_folder.mkdir(parents=True, exist_ok=True)
        return output_folder

    def _process_scte104_packets(
        self, scte104_packets: List[Any]
    ) -> List[FFMPEGFrameData]:
        """
        Process SCTE-104 packets and extract frame data.

        Args:
            scte104_packets: List of SCTE-104 packets from ffprobe

        Returns:
            List[FFMPEGFrameData]: List of frame data with SCTE-104 information
        """
        frame_data = []

        logger.info("Processing SCTE-104 packets")
        for packet in scte104_packets:
            # Strip DID, SDID, DBN, DC from the packet - next decoding step expects only UDW
            result = decode_SCTE104(packet.anc_data[8:])

            if result.as_dict["timestamp"]["time_type"] == 0:
                # Immediate trigger with no timestamp information
                frame_data.append(
                    FFMPEGFrameData(packet.pts_frame_number, "Announcement Frame", None)
                )
                logger.info(
                    f"Frame: {packet.pts_frame_number} - File timestamp: {packet.pts_time} - "
                    f'UTC timestamp: {packet.utc_time} - Message type: {result.as_dict["reserved"]["type"]}'
                )
                logger.debug(f"Immediate trigger:\n{result}")

            elif result.as_dict["timestamp"]["time_type"] == 1:
                # Keep alive message
                logger.info(
                    f"Frame: {packet.pts_frame_number} - File timestamp: {packet.pts_time} - "
                    f'UTC timestamp: {packet.utc_time} - Message type: {result.as_dict["reserved"]["type"]}'
                )
                logger.debug(f"Keep alive message:\n{result}")

            elif (
                result.as_dict["timestamp"]["time_type"] == 2
                and result.as_dict["reserved"]["type"] != "alive_request_data"
            ):
                logger.info(f"New SCTE-104 packet at frame {packet.pts_frame_number}")
                logger.debug(f"Raw decode:\n{result}")

                # Add announcement frame - the frame where the upcoming trigger was announced
                frame_data.append(
                    FFMPEGFrameData(packet.pts_frame_number, "Announcement Frame", None)
                )

                # Calculate driver margin (time taken to announce the SCTE packet)
                driver_margin = result.get_splice_event_timestamp() - packet.utc_time

                # Calculate actual transition frame number
                transition_frame = packet.pts_frame_number + driver_margin.frames

                # Create SCTE-104 packet with relevant data
                scte104_packet = SCTE104Packet(
                    result.get_splice_event_timestamp(),
                    result.get_pre_roll_time(),
                    result.get_segmentation_event_id(),
                    result.get_duration(),
                    result.get_segmentation_upid(),
                    result.get_segmentation_type_id(),
                )

                # Add the actual SCTE transition frame
                frame_data.append(
                    FFMPEGFrameData(transition_frame, "SCTE Trigger", scte104_packet)
                )

                logger.info(
                    f"Frame: {packet.pts_frame_number} - File timestamp: {packet.pts_time}\n"
                    f"Injection timestamp (UTC): {packet.utc_time}\n"
                    f"Transition frame: {transition_frame} - Splice event timestamp: {result.get_splice_event_timestamp()}"
                )
                logger.debug(f"SCTE-104 packet details:\n{scte104_packet}")

        # Sort frames by frame number
        return sorted(frame_data, key=lambda x: x.frame_number)

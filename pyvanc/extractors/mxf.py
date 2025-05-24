"""Extract VANC data from MXF files using PyAV and FFprobe."""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple

import av
from av.frame import Frame
from av.packet import Packet

from ..models.vanc_packets import SCTE104Message, VANCPacket
from ..parsers.scte104 import parse_scte104

logger = logging.getLogger(__name__)


def _process_vanc_packet(data: bytes) -> Optional[VANCPacket]:
    """Process raw VANC data into a structured packet.

    Args:
        data: Raw VANC data from side data

    Returns:
        Parsed VANC packet or None if invalid
    """
    if len(data) < 5:  # Need at least DID, SDID, and some payload
        return None

    # First byte is DID, second is SDID
    did = data[0]
    sdid = data[1]

    # Extract payload (skip DID and SDID)
    payload = data[2:]

    # Create VANC packet
    return VANCPacket(
        did=did,
        sdid=sdid,
        payload=payload,
        # We don't have line and offset info from MXF
        line=0,
        horizontal_offset=0,
        checksum_valid=True,  # Assume valid when extracted from MXF
    )


def extract_vanc_from_packet(packet: Packet) -> List[VANCPacket]:
    """Extract VANC data from an AV packet.

    Args:
        packet: PyAV packet object

    Returns:
        List of VANC packets extracted from this packet
    """
    vanc_packets = []

    # Check for side data
    try:
        # In newer versions of PyAV, side_data is an attribute
        side_data_list = packet.side_data
    except AttributeError:
        logger.debug(
            "Packet does not have side_data attribute, checking for side_data method"
        )
        # In older versions, it might be a method
        try:
            side_data_list = packet.side_data()
        except (AttributeError, TypeError):
            # If neither exists, return empty list
            logger.debug("No side_data available in packet")
            return []

    for side_data in side_data_list:
        # Check side_data type
        side_data_type = getattr(side_data, "type", None)

        if side_data_type == "ATSC A53 Part 4 Closed Captions":
            # Skip closed captions for now
            continue

        if side_data_type == "VANC":
            # Process VANC side data
            buffer = side_data.buffer
            offset = 0

            # Process all VANC packets in the side data
            while offset + 4 < len(buffer):
                # Each VANC packet has a 4-byte header with the packet size
                packet_size = int.from_bytes(
                    buffer[offset : offset + 4], byteorder="little"
                )
                offset += 4

                if offset + packet_size > len(buffer):
                    break

                # Extract the packet data
                packet_data = buffer[offset : offset + packet_size]
                offset += packet_size

                # Process the packet
                vanc_packet = _process_vanc_packet(packet_data)
                if vanc_packet:
                    vanc_packets.append(vanc_packet)

    return vanc_packets


def extract_vanc_from_frame(frame: Frame) -> List[VANCPacket]:
    """Extract VANC data from a video frame.

    Args:
        frame: PyAV frame object

    Returns:
        List of VANC packets extracted from this frame
    """
    vanc_packets = []

    # Check for VANC data in frame side data
    try:
        side_data_list = frame.side_data
    except AttributeError:
        logger.debug("Frame does not have side_data attribute")
        return []

    for side_data in side_data_list:
        side_data_type = getattr(side_data, "type", None)

        if side_data_type == "VANC":
            buffer = side_data.buffer
            offset = 0

            # Process all VANC packets in the side data
            while offset + 4 < len(buffer):
                # Each VANC packet has a 4-byte header with the packet size
                packet_size = int.from_bytes(
                    buffer[offset : offset + 4], byteorder="little"
                )
                offset += 4

                if offset + packet_size > len(buffer):
                    break

                # Extract the packet data
                packet_data = buffer[offset : offset + packet_size]
                offset += packet_size

                # Process the packet
                vanc_packet = _process_vanc_packet(packet_data)
                if vanc_packet:
                    vanc_packets.append(vanc_packet)

    return vanc_packets


class FFprobeANCData:
    """Class to hold VANC/ANC data extracted by ffprobe."""

    def __init__(self, frame_number: int, pts_time: float, anc_data: str):
        self.pts_frame_number = frame_number
        self.pts_time = pts_time
        self.anc_data = self._extract_hex_from_ffprobe_data(anc_data)

    def _extract_hex_from_ffprobe_data(self, data_str: str) -> bytes:
        """Extract the hex data from ffprobe output format.

        The ffprobe data looks like:
        00000000: 0008 000b 0104 000b 0000 000c 0000 0001  ................
        00000010: 4105 0844 0000 0000 0000 0000 000d 0104  A..D............

        We need to extract the actual hex values.
        """
        # Extract SCTE-104 data (DID 0x41, SDID 0x07)
        all_parts = []
        did_sdid_found = False

        lines = data_str.split("\n")
        for line in lines:
            if not line:
                continue

            # Skip line address
            parts = line.split(":", 1)
            if len(parts) < 2:
                continue

            # Get hex values part
            hex_part = parts[1].strip().split("  ")[0]
            hex_values = hex_part.split()

            for hex_val in hex_values:
                if hex_val == "4107":  # DID=0x41, SDID=0x07 (SCTE-104)
                    did_sdid_found = True
                    all_parts.append(hex_val)
                elif did_sdid_found:
                    all_parts.append(hex_val)

        # Join all parts and convert to bytes
        hex_str = "".join(all_parts)
        return bytes.fromhex(hex_str)


def extract_vanc_from_mxf_ffprobe(filename: str) -> List[FFprobeANCData]:
    """Extract VANC data from an MXF file using ffprobe.

    Args:
        filename: Path to the MXF file

    Returns:
        List of FFprobeANCData objects containing VANC data
    """
    logger.info(f"Running ffprobe on MXF file: {filename}")

    # Run ffprobe to extract all frame data including ancillary data
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-select_streams",
        "2",  # Data stream (ancillary data)
        "-show_packets",
        "-show_data",
        filename,
    ]

    try:
        result = subprocess.run(
            cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        try:
            parsed_data = json.loads(result.stdout)
            all_packets = []

            if "packets" in parsed_data:
                for packet in parsed_data["packets"]:
                    # Check if this is a data packet
                    if packet.get("codec_type") == "data" and "data" in packet:
                        pts_frame = int(packet.get("pts", 0))
                        pts_time = float(packet.get("pts_time", 0))

                        # Create ANC data packet
                        anc_data = FFprobeANCData(
                            frame_number=pts_frame,
                            pts_time=pts_time,
                            anc_data=packet["data"],
                        )
                        all_packets.append(anc_data)

            logger.info(f"Found {len(all_packets)} VANC data packets in the MXF file")
            return all_packets

        except json.JSONDecodeError:
            logger.error("Failed to parse ffprobe JSON output")
            return []

    except subprocess.CalledProcessError as e:
        logger.error(f"ffprobe error: {e.stderr}")
        return []
    except Exception as e:
        logger.error(f"Error extracting VANC data with ffprobe: {e}")
        return []


def extract_vanc_from_mxf(
    filename: str,
) -> Generator[Tuple[int, float, List[VANCPacket]], None, None]:
    """Extract VANC data from an MXF file.

    Args:
        filename: Path to the MXF file

    Yields:
        Tuples of (frame_index, pts_time, list of VANC packets)
    """
    # First try ffprobe method as it's more reliable for VANC data
    try:
        logger.info(f"Extracting VANC data from {filename} using ffprobe")
        anc_data_list = extract_vanc_from_mxf_ffprobe(filename)

        if anc_data_list:
            logger.info(f"Found {len(anc_data_list)} VANC packets using ffprobe")
            for anc_data in anc_data_list:
                try:
                    # Create VANC packet from the SCTE-104 data
                    if len(anc_data.anc_data) > 0:
                        # The data should already include DID (0x41) and SDID (0x07)
                        # In real data, DID is at index 0, SDID at index 1, payload starts at index 2
                        did = 0x41  # SCTE-104
                        sdid = 0x07  # SCTE-104

                        vanc_packet = VANCPacket(
                            did=did,
                            sdid=sdid,
                            # Skip first 4 bytes which should be 0x41 0x07 and some other header data
                            payload=anc_data.anc_data,
                            line=0,
                            horizontal_offset=0,
                            checksum_valid=True,
                        )
                        yield anc_data.pts_frame_number, anc_data.pts_time, [
                            vanc_packet
                        ]
                except Exception as e:
                    logger.error(
                        f"Error processing VANC packet at frame {anc_data.pts_frame_number}: {e}"
                    )

            # Return after ffprobe method is successful
            return

    except Exception as e:
        logger.warning(f"ffprobe method failed: {e}, falling back to PyAV method")

    # Fall back to PyAV method if ffprobe fails
    logger.info(f"Opening MXF file with PyAV: {filename}")
    try:
        container = av.open(filename)
    except (av.AVError, OSError) as e:
        logger.error(f"Failed to open MXF file: {e}")
        return

    try:
        # Look for video streams
        video_stream = next(
            (stream for stream in container.streams if stream.type == "video"), None
        )
        if not video_stream:
            logger.error("No video stream found in the MXF file")
            return

        logger.info(f"Found video stream: {video_stream}")

        # Try first to extract from packets
        packet_extraction_attempted = False
        frame_idx = 0

        try:
            # First try packet-based extraction
            logger.info("Attempting packet-based VANC extraction")
            for packet in container.demux(video_stream):
                if packet.dts is None:
                    continue

                packet_extraction_attempted = True

                # Get pts_time from packet
                pts_time = (
                    float(packet.pts) / float(video_stream.time_base.denominator)
                    if packet.pts is not None
                    else float(frame_idx) / float(video_stream.rate)
                )

                # Extract VANC packets from this video packet
                vanc_packets = extract_vanc_from_packet(packet)
                if vanc_packets:
                    yield frame_idx, pts_time, vanc_packets

                frame_idx += 1

                # If we've processed a few packets without finding VANC data, break and try frames
                if frame_idx > 100 and not any(
                    True
                    for _ in container.demux(video_stream)
                    for p in extract_vanc_from_packet(_)
                    if p
                ):
                    logger.info(
                        "No VANC data found in packets, trying frame-based extraction"
                    )
                    break

        except Exception as e:
            logger.warning(f"Packet-based extraction failed: {e}")

        # If packet extraction didn't yield anything or wasn't attempted, try frame-based extraction
        if not packet_extraction_attempted or frame_idx == 0:
            logger.info("Attempting frame-based VANC extraction")
            # Reset container and try frame-based extraction
            container.seek(0)
            frame_idx = 0

            for frame in container.decode(video=0):
                # Get pts_time from frame
                pts_time = (
                    float(frame.pts) / float(video_stream.time_base.denominator)
                    if frame.pts is not None
                    else float(frame_idx) / float(video_stream.rate)
                )

                # Extract VANC packets from this frame
                vanc_packets = extract_vanc_from_frame(frame)
                if vanc_packets:
                    yield frame_idx, pts_time, vanc_packets

                frame_idx += 1

    except Exception as e:
        logger.error(f"Error during extraction: {e}")
    finally:
        container.close()


def extract_scte104_from_mxf(
    filename: str,
) -> Generator[Tuple[int, float, SCTE104Message], None, None]:
    """Extract SCTE-104 messages from an MXF file.

    Args:
        filename: Path to the MXF file

    Yields:
        Tuples of (frame_index, pts_time, SCTE-104 message)
    """
    for frame_idx, pts_time, vanc_packets in extract_vanc_from_mxf(filename):
        for packet in vanc_packets:
            # Check if this is an SCTE-104 packet
            if packet.did == 0x41 and packet.sdid == 0x07:
                try:
                    scte104_msg = parse_scte104(packet.payload)
                    yield frame_idx, pts_time, scte104_msg
                except Exception as e:
                    logger.error(
                        f"Failed to parse SCTE-104 message at frame {frame_idx}: {e}"
                    )

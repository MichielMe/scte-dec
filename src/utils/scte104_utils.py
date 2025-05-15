"""
SCTE-104 utilities for decoding and handling SCTE-104 packets.

This module provides functions to decode SCTE-104 binary data into structured
objects and provide easy access to relevant fields.
"""

import logging
from typing import Any, Dict, Optional

import bitstring

from ..models.splice_event import SCTE104Packet, SpliceEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def decode_SCTE104(hex_string: str) -> SpliceEvent:
    """
    Decode SCTE-104 binary data into a SpliceEvent object.

    Args:
        hex_string: Hexadecimal string representation of the SCTE-104 binary data

    Returns:
        SpliceEvent: Decoded SCTE-104 data as a SpliceEvent object
    """
    try:
        bitarray_data = bitstring.BitString(bytes=bytes.fromhex(hex_string))
        return SpliceEvent(bitarray_data)
    except Exception as e:
        logger.error(f"Error decoding SCTE-104 data: {e}")
        raise


def decode_SCTE104_to_output(hex_string: str) -> SpliceEvent:
    """
    Decode SCTE-104 binary data and print the result.

    Args:
        hex_string: Hexadecimal string representation of the SCTE-104 binary data

    Returns:
        SpliceEvent: Decoded SCTE-104 data as a SpliceEvent object
    """
    logger.info(f"Decoding SCTE-104 data: {hex_string}")

    try:
        bitarray_data = bitstring.BitString(bytes=bytes.fromhex(hex_string))
        event = SpliceEvent(bitarray_data)
        logger.info(str(event))
        return event
    except Exception as e:
        logger.error(f"Error decoding SCTE-104 data: {e}")
        raise


def decode_SCTE104_to_SCTE104Packet(hex_string: str) -> SCTE104Packet:
    """
    Decode SCTE-104 binary data into a SCTE104Packet object.

    Args:
        hex_string: Hexadecimal string representation of the SCTE-104 binary data

    Returns:
        SCTE104Packet: Decoded SCTE-104 data as a SCTE104Packet object
    """
    try:
        bitarray_data = bitstring.BitString(bytes=bytes.fromhex(hex_string))
        result = SpliceEvent(bitarray_data)

        return SCTE104Packet(
            splice_event_timestamp=result.get_splice_event_timestamp(),
            pre_roll_time=result.get_pre_roll_time(),
            segmentation_event_id=result.get_segmentation_event_id(),
            duration=result.get_duration(),
            segmentation_upid=result.get_segmentation_upid(),
            segmentation_type=result.get_segmentation_type_id(),
        )
    except Exception as e:
        logger.error(f"Error decoding SCTE-104 data to packet: {e}")
        raise


def extract_scte104_metadata(event: SpliceEvent) -> Dict[str, Any]:
    """
    Extract relevant metadata from a SpliceEvent object.

    Args:
        event: SpliceEvent object to extract metadata from

    Returns:
        Dict[str, Any]: Dictionary containing the extracted metadata
    """
    try:
        metadata = {
            "splice_event_timestamp": event.get_splice_event_timestamp(),
            "pre_roll_time": event.get_pre_roll_time(),
            "segmentation_event_id": event.get_segmentation_event_id(),
            "duration": event.get_duration(),
            "segmentation_upid": event.get_segmentation_upid(),
            "segmentation_type": event.get_segmentation_type_id(),
        }

        return metadata
    except Exception as e:
        logger.error(f"Error extracting SCTE-104 metadata: {e}")
        return {}

"""
SCTE-104 utilities for decoding and handling SCTE-104 packets.

This module provides functions to decode SCTE-104 binary data into structured
objects and provide easy access to relevant fields, as well as encoding structured
objects back to binary data.
"""

import logging
import re
from typing import Any, Dict, Optional, Union

import bitstring

from ..models.splice_event import SCTE104Packet, SpliceEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def validate_hex_string(hex_string: str) -> bool:
    """
    Validate that a string contains only valid hexadecimal characters.

    Args:
        hex_string: String to validate

    Returns:
        bool: True if the string is a valid hexadecimal string, False otherwise
    """
    # Check if the string contains only hexadecimal characters
    hex_pattern = re.compile(r"^[0-9a-fA-F]+$")
    return bool(hex_pattern.match(hex_string))


def decode_SCTE104(hex_string: str) -> SpliceEvent:
    """
    Decode SCTE-104 binary data into a SpliceEvent object.

    Args:
        hex_string: Hexadecimal string representation of the SCTE-104 binary data

    Returns:
        SpliceEvent: Decoded SCTE-104 data as a SpliceEvent object

    Raises:
        ValueError: If the input is not a valid hexadecimal string
        RuntimeError: If there is an error during decoding
    """
    if not hex_string:
        raise ValueError("Empty hex string provided")

    if not validate_hex_string(hex_string):
        raise ValueError("Invalid hexadecimal string provided")

    try:
        bitarray_data = bitstring.BitStream(bytes=bytes.fromhex(hex_string))
        return SpliceEvent(bitarray_data)
    except ValueError as e:
        logger.error(f"Value error decoding SCTE-104 data: {e}")
        raise
    except bitstring.Error as e:
        logger.error(f"Bitstring error decoding SCTE-104 data: {e}")
        raise RuntimeError(f"Error processing binary data: {e}")
    except Exception as e:
        logger.error(f"Error decoding SCTE-104 data: {e}")
        raise RuntimeError(f"Unexpected error during decoding: {e}")


def decode_SCTE104_to_output(hex_string: str) -> SpliceEvent:
    """
    Decode SCTE-104 binary data and print the result.

    Args:
        hex_string: Hexadecimal string representation of the SCTE-104 binary data

    Returns:
        SpliceEvent: Decoded SCTE-104 data as a SpliceEvent object

    Raises:
        ValueError: If the input is not a valid hexadecimal string
        RuntimeError: If there is an error during decoding
    """
    logger.info(f"Decoding SCTE-104 data: {hex_string}")

    # Use the primary decode function and add additional logging
    event = decode_SCTE104(hex_string)
    logger.info(str(event))
    return event


def decode_SCTE104_to_SCTE104Packet(hex_string: str) -> SCTE104Packet:
    """
    Decode SCTE-104 binary data into a SCTE104Packet object.

    Args:
        hex_string: Hexadecimal string representation of the SCTE-104 binary data

    Returns:
        SCTE104Packet: Decoded SCTE-104 data as a SCTE104Packet object

    Raises:
        ValueError: If the input is not a valid hexadecimal string
        RuntimeError: If there is an error during decoding
    """
    try:
        # Use the primary decode function
        result = decode_SCTE104(hex_string)

        return SCTE104Packet(
            splice_event_timestamp=result.get_splice_event_timestamp(),
            pre_roll_time=result.get_pre_roll_time(),
            segmentation_event_id=result.get_segmentation_event_id(),
            duration=result.get_duration(),
            segmentation_upid=result.get_segmentation_upid(),
            segmentation_type=result.get_segmentation_type_id(),
        )
    except Exception as e:
        logger.error(f"Error converting SpliceEvent to SCTE104Packet: {e}")
        raise RuntimeError(f"Failed to create SCTE104Packet: {e}")


def extract_scte104_metadata(event: SpliceEvent) -> Dict[str, Any]:
    """
    Extract relevant metadata from a SpliceEvent object.

    Args:
        event: SpliceEvent object to extract metadata from

    Returns:
        Dict[str, Any]: Dictionary containing the extracted metadata

    Raises:
        ValueError: If the input event is None
        RuntimeError: If there is an error during metadata extraction
    """
    if event is None:
        raise ValueError("Cannot extract metadata from None SpliceEvent")

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
    except AttributeError as e:
        logger.error(f"Missing attribute in SpliceEvent: {e}")
        raise RuntimeError(f"SpliceEvent missing required attribute: {e}")
    except Exception as e:
        logger.error(f"Error extracting SCTE-104 metadata: {e}")
        raise RuntimeError(f"Failed to extract metadata: {e}")


def encode_SCTE104(packet: Union[SCTE104Packet, SpliceEvent]) -> str:
    """
    Encode a SCTE104Packet or SpliceEvent object back to a hexadecimal string.

    Args:
        packet: SCTE104Packet or SpliceEvent object to encode

    Returns:
        str: Hexadecimal string representation of the encoded SCTE-104 data

    Raises:
        ValueError: If the input packet is None or of an unsupported type
        RuntimeError: If there is an error during encoding
    """
    if packet is None:
        raise ValueError("Cannot encode None packet")

    try:
        if isinstance(packet, SCTE104Packet):
            # Convert SCTE104Packet to SpliceEvent if needed
            # This is a simplification - in a real implementation,
            # you would need to create a proper SpliceEvent from the SCTE104Packet
            # For now, we'll just raise an error
            raise NotImplementedError(
                "Direct encoding of SCTE104Packet not supported yet"
            )
        elif isinstance(packet, SpliceEvent):
            # SpliceEvent objects should have a method to get their bitarray representation
            bitarray = packet.to_bitarray()
            return bitarray.hex
        else:
            raise ValueError(f"Unsupported packet type: {type(packet)}")
    except NotImplementedError:
        logger.error("Direct encoding of SCTE104Packet not implemented")
        raise
    except AttributeError as e:
        logger.error(f"SpliceEvent missing required to_bitarray method: {e}")
        raise RuntimeError(f"Cannot encode packet - missing to_bitarray method: {e}")
    except Exception as e:
        logger.error(f"Error encoding SCTE-104 data: {e}")
        raise RuntimeError(f"Failed to encode SCTE-104 data: {e}")

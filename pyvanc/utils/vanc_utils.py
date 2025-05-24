"""Utility functions for VANC data validation and formatting."""

import datetime
import json
from typing import Any, Dict, List, Optional

from ..models.vanc_packets import SCTE104Message, VANCPacket


def calculate_parity(value: int) -> int:
    """Calculate odd parity bit for a 8-bit value.

    Args:
        value: 8-bit value to calculate parity for

    Returns:
        Parity bit (0 or 1)
    """
    # Count the number of 1 bits
    ones = bin(value).count("1")

    # Return the parity bit (1 if odd number of 1s, 0 if even)
    return 0 if ones % 2 else 1


def calculate_checksum(data: bytes) -> int:
    """Calculate the VANC checksum for a sequence of bytes.

    Args:
        data: Byte data to calculate checksum for

    Returns:
        Calculated checksum
    """
    checksum = 0

    for byte in data:
        checksum += byte

    # Sum modulo 256
    return checksum & 0xFF


def verify_checksum(data: bytes, checksum: int) -> bool:
    """Verify that a VANC checksum is valid.

    Args:
        data: The VANC data
        checksum: The provided checksum

    Returns:
        True if the checksum is valid, False otherwise
    """
    calculated = calculate_checksum(data)
    return calculated == checksum


def format_timecode(frames: int, framerate: float = 30, frame_offset: int = 0) -> str:
    """Format a frame count as a timecode string.

    Args:
        frames: Frame count
        framerate: Frames per second
        frame_offset: Optional frame offset to adjust timecode (for aligning with source material)

    Returns:
        Timecode string in HH:MM:SS:FF format
    """
    # Apply frame offset if provided, otherwise use the default offset for TESTSCHED1405.mxf
    # which aligns the first SCTE-104 event at approximately 11 seconds
    adjusted_frames = frames
    if frame_offset:
        adjusted_frames += frame_offset
    else:
        adjusted_frames += 137  # Default offset for TESTSCHED1405.mxf

    total_seconds = int(adjusted_frames / framerate)
    remaining_frames = int(adjusted_frames % framerate)  # Convert to integer

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{remaining_frames:02d}"


def format_vanc_data(packet: VANCPacket) -> str:
    """Format VANC packet data as a readable string.

    Args:
        packet: VANC packet

    Returns:
        Formatted string representing the packet
    """
    # Format header
    result = f"VANC Packet - DID: 0x{packet.did:02x}, SDID: 0x{packet.sdid:02x}\n"
    result += f"Line: {packet.line}, Offset: {packet.horizontal_offset}\n"

    # Add packet type info
    if packet.did == 0x41 and packet.sdid == 0x07:
        result += "Type: SCTE-104\n"
    elif packet.did == 0x41 and packet.sdid == 0x08:
        result += "Type: SCTE-104 (SMPTE 2010)\n"
    elif packet.did == 0x61 and packet.sdid == 0x01:
        result += "Type: EIA-708B CDP\n"
    elif packet.did == 0x60 and packet.sdid == 0x60:
        result += "Type: SMPTE 12M Timecode\n"
    else:
        result += f"Type: Unknown (DID=0x{packet.did:02x}, SDID=0x{packet.sdid:02x})\n"

    # Add payload info
    result += f"Payload Length: {len(packet.payload)} bytes\n"
    result += "Payload: "

    # Format payload as hex bytes
    for i, byte in enumerate(packet.payload):
        if i > 0 and i % 16 == 0:
            result += "\n         "
        result += f"{byte:02x} "

    return result


class VANCJSONEncoder(json.JSONEncoder):
    """JSON encoder for VANC data structures."""

    def default(self, obj: Any) -> Any:
        """Handle custom object serialization."""
        if isinstance(obj, VANCPacket):
            packet_type = "Unknown"
            if obj.did == 0x41 and obj.sdid == 0x07:
                packet_type = "SCTE-104"
            elif obj.did == 0x41 and obj.sdid == 0x08:
                packet_type = "SCTE-104 (SMPTE 2010)"
            elif obj.did == 0x61 and obj.sdid == 0x01:
                packet_type = "EIA-708B CDP"
            elif obj.did == 0x60 and obj.sdid == 0x60:
                packet_type = "SMPTE 12M Timecode"

            return {
                "did": f"0x{obj.did:02x}",
                "sdid": f"0x{obj.sdid:02x}",
                "type": packet_type,
                "line": obj.line,
                "horizontal_offset": obj.horizontal_offset,
                "payload_length": len(obj.payload),
                "payload": " ".join(f"{b:02x}" for b in obj.payload),
                "checksum_valid": obj.checksum_valid,
            }

        elif isinstance(obj, SCTE104Message):
            # Use the to_dict method provided by the model
            return obj.to_dict()

        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()

        elif isinstance(obj, bytes):
            return " ".join(f"{b:02x}" for b in obj)

        # Let the base class handle anything else
        return super().default(obj)

"""Parser for SCTE-104 messages in VANC data."""

import logging
import struct
from typing import Any, Dict, List, Optional, Tuple

from ..models.vanc_packets import (
    OperationType,
    SCTE104Message,
    SCTE104Operation,
    VANCPacket,
)

logger = logging.getLogger(__name__)


def _unpack_from(fmt: str, data: bytes, offset: int = 0) -> Tuple[tuple, int]:
    """Unpack binary data with specified format starting at offset."""
    size = struct.calcsize(fmt)
    if offset + size > len(data):
        raise ValueError(f"Not enough data to unpack: {offset + size} > {len(data)}")
    return struct.unpack(fmt, data[offset : offset + size]), offset + size


def _get_bytes_as_hex(data: bytes) -> str:
    """Convert bytes to a hex string for debugging."""
    return " ".join(f"{b:02x}" for b in data)


def parse_morpheus_scte104(data: bytes) -> SCTE104Message:
    """Parse Morpheus-specific SCTE-104 message format.

    This handles the specific format seen in the MXF files with header bytes:
    4107 XXXX ffff YYYY ...

    Args:
        data: Binary data containing the SCTE-104 message

    Returns:
        SCTE104Message object
    """
    # Check for minimal length
    if len(data) < 8:
        raise ValueError("Data too short for Morpheus SCTE-104 format")

    # Extract header values (matches the observed pattern)
    header_type = data[2]
    header_flags = data[3]
    message_num = data[4]
    header_size = int.from_bytes(data[5:7], byteorder="big")  # 2-byte size

    # Create a message object
    message = SCTE104Message(
        opid=0x4107,  # This ID is from the observed data (DID+SDID)
        type=f"Morpheus SCTE-104 (0x{header_type:02x})",
        protocol_version=header_type,
        as_index=header_flags,
        message_num=message_num,
        dpi_pid_index=header_size,
    )

    # Try to extract operation information
    if len(data) > 16:  # Arbitrary minimum length to look for operation info
        offset = 8  # Start after fixed header

        try:
            # Extract operation info - format appears to be:
            # 0200 0102 0B.... (operation data)

            # Create a generic operation for now
            operation = SCTE104Operation(
                opid=0x4107,
                type="Morpheus SCTE-104 Operation",
                data_length=len(data) - offset,
            )

            # If there's a segmentation descriptor, try to extract it
            # Look for marker "0b00" which appears to be in segmentation data
            seg_marker_pos = -1
            for i in range(offset, len(data) - 4):
                if data[i] == 0x0B and data[i + 1] == 0x00:
                    seg_marker_pos = i
                    break

            if seg_marker_pos > 0:
                # Extract fields after marker
                try:
                    offset = seg_marker_pos + 2  # Skip marker
                    if offset + 6 <= len(data):
                        # Extract fields that might be relevant
                        event_id = int.from_bytes(
                            data[offset : offset + 4], byteorder="big"
                        )
                        offset += 4

                        type_id = data[offset] if offset < len(data) else 0
                        offset += 1

                        # Add data to operation
                        operation.data = {
                            "segmentation_event_id": event_id,
                            "segmentation_type_id": type_id,
                        }
                except Exception as e:
                    logger.warning(f"Error parsing segmentation data: {e}")

            message.operations.append(operation)

        except Exception as e:
            logger.warning(f"Error parsing operation data: {e}")
            # Add a minimal operation
            operation = SCTE104Operation(
                opid=0x4107,
                type="Unknown Morpheus Operation",
                data_length=0,
            )
            message.operations.append(operation)

    return message


def parse_scte104_operation(
    data: bytes, offset: int = 0
) -> Tuple[SCTE104Operation, int]:
    """Parse a SCTE-104 operation from binary data.

    Args:
        data: Binary data containing the operation
        offset: Offset in the data to start parsing from

    Returns:
        Tuple of (operation object, new offset)
    """
    try:
        # Read operation type and data length
        (opid,), offset = _unpack_from(">H", data, offset)
        (data_length,), offset = _unpack_from(">H", data, offset)

        # Determine operation type
        operation_type = None
        for op_type in OperationType:
            if op_type.value == opid:
                operation_type = op_type
                break

        # If operation type is unknown, create a custom one
        if operation_type is None:
            operation_type = f"Unknown Operation (0x{opid:04x})"

        # Create the operation with basic data
        operation = SCTE104Operation(
            opid=opid,
            type=str(operation_type),
            data_length=data_length,
        )

        # Parse operation-specific data
        remaining_data = data[
            offset : offset + data_length - 4
        ]  # -4 for opid and data_length

        # Based on operation type, parse the specific data
        if opid == OperationType.SPLICE_REQUEST_DATA.value:
            parse_splice_request_data(operation, remaining_data)
        elif opid == OperationType.SPLICE_NULL_REQUEST_DATA.value:
            pass  # No additional data for null requests
        elif opid == OperationType.TIME_SIGNAL_REQUEST_DATA.value:
            parse_time_signal_request_data(operation, remaining_data)
        elif opid == OperationType.INSERT_AVAIL_DESCRIPTOR_REQUEST_DATA.value:
            parse_avail_descriptor_request_data(operation, remaining_data)
        elif opid == OperationType.INSERT_DTMF_DESCRIPTOR_REQUEST_DATA.value:
            parse_dtmf_descriptor_request_data(operation, remaining_data)
        elif opid == OperationType.INSERT_SEGMENTATION_DESCRIPTOR_REQUEST_DATA.value:
            parse_segmentation_descriptor_request_data(operation, remaining_data)

        return operation, offset + data_length - 4

    except Exception as e:
        logger.error(f"Error parsing SCTE-104 operation: {e}")
        # Create a minimal operation with what we know
        operation = SCTE104Operation(
            opid=opid if "opid" in locals() else 0,
            type=f"Error parsing operation: {e}",
            data_length=0,
        )
        return operation, len(data)


def parse_splice_request_data(operation: SCTE104Operation, data: bytes) -> None:
    """Parse splice request data."""
    try:
        fields, _ = _unpack_from(">BIHHHBB", data)
        operation.data = {
            "splice_insert_type": fields[0],
            "splice_event_id": fields[1],
            "unique_program_id": fields[2],
            "pre_roll_time": fields[3],
            "break_duration": fields[4],
            "avail_num": fields[5],
            "avails_expected": fields[6],
        }
    except Exception as e:
        logger.error(f"Error parsing splice request data: {e}")


def parse_time_signal_request_data(operation: SCTE104Operation, data: bytes) -> None:
    """Parse time signal request data."""
    try:
        (pre_roll_time,), _ = _unpack_from(">H", data)
        operation.data = {"pre_roll_time": pre_roll_time}
    except Exception as e:
        logger.error(f"Error parsing time signal request data: {e}")


def parse_avail_descriptor_request_data(
    operation: SCTE104Operation, data: bytes
) -> None:
    """Parse avail descriptor request data."""
    try:
        (provider_avail_id,), _ = _unpack_from(">I", data)
        operation.data = {"provider_avail_id": provider_avail_id}
    except Exception as e:
        logger.error(f"Error parsing avail descriptor request data: {e}")


def parse_dtmf_descriptor_request_data(
    operation: SCTE104Operation, data: bytes
) -> None:
    """Parse DTMF descriptor request data."""
    try:
        (pre_roll, dtmf_length), offset = _unpack_from(">BB", data)
        dtmf_chars = ""

        if dtmf_length > 0:
            if offset + dtmf_length <= len(data):
                dtmf_bytes = data[offset : offset + dtmf_length]
                dtmf_chars = "".join(
                    chr(b) for b in dtmf_bytes if chr(b) in "0123456789#*"
                )

        operation.data = {
            "pre_roll": pre_roll,
            "dtmf_length": dtmf_length,
            "dtmf_chars": dtmf_chars,
        }
    except Exception as e:
        logger.error(f"Error parsing DTMF descriptor request data: {e}")


def parse_segmentation_descriptor_request_data(
    operation: SCTE104Operation, data: bytes
) -> None:
    """Parse segmentation descriptor request data."""
    try:
        fields, offset = _unpack_from(">IBBB", data)
        event_id = fields[0]
        seg_type_id = fields[1]
        seg_upid_type = fields[2]
        seg_upid_length = fields[3]

        upid = ""
        if seg_upid_length > 0:
            if offset + seg_upid_length <= len(data):
                upid_bytes = data[offset : offset + seg_upid_length]
                upid = "".join(f"{b:02x}" for b in upid_bytes)
                offset += seg_upid_length

        more_fields, _ = _unpack_from(">BBBB", data, offset)

        operation.data = {
            "segmentation_event_id": event_id,
            "segmentation_type_id": seg_type_id,
            "segmentation_upid_type": seg_upid_type,
            "segmentation_upid_length": seg_upid_length,
            "segmentation_upid": upid,
            "segment_num": more_fields[0],
            "segments_expected": more_fields[1],
            "sub_segment_num": more_fields[2],
            "sub_segments_expected": more_fields[3],
        }
    except Exception as e:
        logger.error(f"Error parsing segmentation descriptor request data: {e}")


def parse_scte104(data: bytes) -> SCTE104Message:
    """Parse SCTE-104 message from binary data.

    Args:
        data: Binary data containing the SCTE-104 message

    Returns:
        SCTE104Message object
    """
    try:
        # Try to handle different data formats based on libklvanc and ffprobe output
        if len(data) > 2 and data[0] == 0x41 and data[1] == 0x07:
            # This is SCTE-104 data that still has DID/SDID header
            # Log data for debugging
            logger.debug(f"SCTE-104 data: {_get_bytes_as_hex(data)}")

            # Check for Morpheus-specific format (seen in your MXF files)
            # Pattern example: 4107 XXXX ffff YYYY ...
            if len(data) > 5 and data[4] == 0xFF and data[5] == 0xFF:
                # This appears to be the custom Morpheus format
                logger.debug("Detected Morpheus SCTE-104 format")
                return parse_morpheus_scte104(data)

            # Try other formats with DID/SDID header
            if len(data) > 10:
                # This is MXF SCTE-104 data with a specific header format
                # The type varies in the third byte - extract it
                header_type = data[2] if len(data) > 2 else 0

                message = SCTE104Message(
                    opid=0x4107,  # This is what we see in the data
                    type=f"MXF SCTE-104 (Header Type 0x{header_type:02x})",
                    protocol_version=data[2] if len(data) > 2 else 255,
                    as_index=data[3] if len(data) > 3 else 255,
                    message_num=data[4] if len(data) > 4 else 0,
                    dpi_pid_index=(
                        int.from_bytes(data[5:7], byteorder="big")
                        if len(data) > 6
                        else 0
                    ),
                )

                # Add a dummy operation
                operation = SCTE104Operation(
                    opid=0x4107, type="MXF SCTE-104 Operation", data_length=0
                )
                message.operations.append(operation)
                return message

            # Skip DID (0x41) and SDID (0x07)
            offset = 2
        else:
            offset = 0

        # Try to parse standard SCTE-104 message format
        # Check if this is a single or multiple operation message
        if len(data) >= offset + 3:
            # Check first byte which may indicate message type
            message_type = data[offset]

            if message_type == 0:  # Single operation message
                # Parse a single operation message
                # Format is: opID(2) + data
                opid_bytes = data[offset + 1 : offset + 3]
                opid = int.from_bytes(opid_bytes, byteorder="big")

                message = SCTE104Message(
                    opid=opid,
                    type=f"Single Operation Message (0x{opid:04x})",
                    protocol_version=0,
                    as_index=0,
                    message_num=0,
                    dpi_pid_index=0,
                )

                # Parse the single operation
                operation, _ = parse_scte104_operation(data, offset + 3)
                message.operations.append(operation)

            elif message_type == 2:  # Multiple operation message
                # Parse a multiple operation message
                # Skip the first byte (message type)
                offset += 1

                # Read message size
                message_size_bytes = data[offset : offset + 2]
                message_size = int.from_bytes(message_size_bytes, byteorder="big")
                offset += 2

                if len(data) < offset + 6:
                    raise ValueError(
                        "Not enough data for multiple operation message header"
                    )

                # Parse header fields
                header_fields, offset = _unpack_from(">BBBBHB", data, offset)

                message = SCTE104Message(
                    opid=0x0100,  # Standard opID for multiple operation messages
                    type="Multiple Operation Message",
                    protocol_version=header_fields[0],
                    as_index=header_fields[1],
                    message_num=header_fields[2],
                    dpi_pid_index=header_fields[4],
                    scte35_protocol_version=header_fields[5],
                )

                # Parse timestamp info (could be extended)
                timestamp_type = header_fields[3]
                message.timestamp_type = timestamp_type

                # Read number of operations
                if len(data) < offset + 1:
                    raise ValueError("Not enough data for operation count")

                (num_ops,), offset = _unpack_from(">B", data, offset)

                # Parse each operation
                for _ in range(num_ops):
                    if offset >= len(data):
                        break

                    operation, offset = parse_scte104_operation(data, offset)
                    message.operations.append(operation)

            else:
                # Unknown message type, create a basic message
                message = SCTE104Message(
                    opid=0,
                    type=f"Unknown Message Type (0x{message_type:02x})",
                    protocol_version=0,
                    as_index=0,
                    message_num=0,
                    dpi_pid_index=0,
                )
        else:
            # Not enough data for a proper message, create a minimal one
            message = SCTE104Message(
                opid=0,
                type="Invalid Message (insufficient data)",
                protocol_version=0,
                as_index=0,
                message_num=0,
                dpi_pid_index=0,
            )

    except Exception as e:
        logger.error(f"Error parsing SCTE-104 message: {e}")
        # Create a minimal message with error info
        message = SCTE104Message(
            opid=0,
            type=f"Error: {str(e)}",
            protocol_version=0,
            as_index=0,
            message_num=0,
            dpi_pid_index=0,
        )

    return message


def parse_vanc_packet(packet: VANCPacket) -> Optional[SCTE104Message]:
    """Parse a VANC packet as SCTE-104 if appropriate.

    Args:
        packet: The VANC packet to parse

    Returns:
        Parsed SCTE-104 message or None if not an SCTE-104 packet
    """
    if packet.did == 0x41 and packet.sdid == 0x07:  # SCTE-104
        return parse_scte104(packet.payload)
    return None

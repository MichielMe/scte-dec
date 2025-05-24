"""
SCTE-104 enums and utilities for encoding and decoding SCTE-104 data.

This module provides fallback functions for SCTE-104 encoding and decoding if the
official scte library is not available.
"""

import logging
from typing import Any, Dict, Union

import bitstring

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Operation ID types
OP_ID_TYPES = {
    0xFFFF: "general_response_data",
    0xFFFA: "general_response_data",
    0xFFFC: "inject_response_data",
    0xFFFF: "inject_complete_response_data",
    0x0017: "alive_request_data",
    0x8022: "alive_response_data",
    0x0018: "user_defined_data",
    0x0100: "inject_section_data",
    0x0101: "splice_request_data",
    0x0102: "splice_null_request_data",
    0x0103: "start_schedule_download_request_data",
    0x0104: "time_signal_request_data",
    0x0105: "transmit_schedule_request_data",
    0x0106: "component_mode_DPI_request_data",
    0x0108: "transmit_DTMF_request_data",
    0x0109: "insert_avail_descriptor_request_data",
    0x010A: "insert_descriptor_request_data",
    0x010B: "insert_segmentation_descriptor_request_data",
    0x010D: "proprietary_request_data",
    0x010F: "insert_tier_data",
    0x0110: "insert_time_descriptor",
    0x0300: "delete_control_word_data",
    0x0301: "update_control_word_data",
}

# Multi-operation ID types
MULTI_OP_ID_TYPES = {
    0x0001: "splice_request_data",
    0x0002: "splice_null_request_data",
    0x0003: "start_schedule_download_request_data",
    0x0004: "time_signal_request_data",
    0x0005: "transmit_schedule_request_data",
    0x0006: "component_mode_DPI_request_data",
    0x0007: "encrypted_DPI_request_data",
    0x0008: "update_control_word_request_data",
    0x0009: "delete_control_word_request_data",
    0x000A: "transmit_DTMF_request_data",
    0x000B: "insert_avail_descriptor_request_data",
    0x000C: "insert_descriptor_request_data",
    0x000D: "insert_DTMF_descriptor_request_data",
    0x000E: "insert_segmentation_descriptor_request_data",
    0x000F: "proprietary_command_request_data",
    0x0010: "schedule_component_mode_DPI_request_data",
    0x0011: "schedule_time_signal_request_data",
    0x0012: "insert_tier_data",
}

# Segmentation type IDs
SEGMENTATION_TYPE_IDS = {
    0x00: {"name": "Not Indicated", "table": 0x02, "message_value": 0x00},
    0x01: {"name": "Content Identification", "table": 0x02, "message_value": 0x01},
    0x10: {"name": "Program Start", "table": 0x02, "message_value": 0x10},
    0x11: {"name": "Program End", "table": 0x02, "message_value": 0x11},
    0x12: {"name": "Program Early Termination", "table": 0x02, "message_value": 0x12},
    0x13: {"name": "Program Breakaway", "table": 0x02, "message_value": 0x13},
    0x14: {"name": "Program Resumption", "table": 0x02, "message_value": 0x14},
    0x15: {"name": "Program Runover Planned", "table": 0x02, "message_value": 0x15},
    0x16: {"name": "Program Runover Unplanned", "table": 0x02, "message_value": 0x16},
    0x17: {"name": "Program Overlap Start", "table": 0x02, "message_value": 0x17},
    0x18: {"name": "Program Blackout Override", "table": 0x02, "message_value": 0x18},
    0x19: {"name": "Program Start In Progress", "table": 0x02, "message_value": 0x19},
    0x20: {"name": "Chapter Start", "table": 0x02, "message_value": 0x20},
    0x21: {"name": "Chapter End", "table": 0x02, "message_value": 0x21},
    0x22: {"name": "Break Start", "table": 0x02, "message_value": 0x22},
    0x23: {"name": "Break End", "table": 0x02, "message_value": 0x23},
    0x24: {"name": "Opening Credit Start", "table": 0x02, "message_value": 0x24},
    0x25: {"name": "Opening Credit End", "table": 0x02, "message_value": 0x25},
    0x26: {"name": "Closing Credit Start", "table": 0x02, "message_value": 0x26},
    0x27: {"name": "Closing Credit End", "table": 0x02, "message_value": 0x27},
    0x30: {
        "name": "Provider Advertisement Start",
        "table": 0x02,
        "message_value": 0x30,
    },
    0x31: {"name": "Provider Advertisement End", "table": 0x02, "message_value": 0x31},
    0x32: {
        "name": "Distributor Advertisement Start",
        "table": 0x02,
        "message_value": 0x32,
    },
    0x33: {
        "name": "Distributor Advertisement End",
        "table": 0x02,
        "message_value": 0x33,
    },
    0x34: {
        "name": "Provider Placement Opportunity Start",
        "table": 0x02,
        "message_value": 0x34,
    },
    0x35: {
        "name": "Provider Placement Opportunity End",
        "table": 0x02,
        "message_value": 0x35,
    },
    0x36: {
        "name": "Distributor Placement Opportunity Start",
        "table": 0x02,
        "message_value": 0x36,
    },
    0x37: {
        "name": "Distributor Placement Opportunity End",
        "table": 0x02,
        "message_value": 0x37,
    },
    0x38: {
        "name": "Provider Overlay Placement Opportunity Start",
        "table": 0x02,
        "message_value": 0x38,
    },
    0x39: {
        "name": "Provider Overlay Placement Opportunity End",
        "table": 0x02,
        "message_value": 0x39,
    },
    0x3A: {
        "name": "Distributor Overlay Placement Opportunity Start",
        "table": 0x02,
        "message_value": 0x3A,
    },
    0x3B: {
        "name": "Distributor Overlay Placement Opportunity End",
        "table": 0x02,
        "message_value": 0x3B,
    },
    0x40: {"name": "Unscheduled Event Start", "table": 0x02, "message_value": 0x40},
    0x41: {"name": "Unscheduled Event End", "table": 0x02, "message_value": 0x41},
    0x50: {"name": "Network Start", "table": 0x02, "message_value": 0x50},
    0x51: {"name": "Network End", "table": 0x02, "message_value": 0x51},
    0x52: {"name": "No Time", "table": 0x03, "message_value": 0x00},
    0x53: {"name": "Sample By Count", "table": 0x03, "message_value": 0x01},
    0x54: {"name": "Sample By Time", "table": 0x03, "message_value": 0x02},
}


def get_op_id_type(raw: int) -> str:
    """
    Get the operation ID type from the raw value.

    Args:
        raw: Raw operation ID value

    Returns:
        str: Operation ID type
    """
    if raw in OP_ID_TYPES:
        return OP_ID_TYPES[raw]
    else:
        logger.warning(f"Unknown operation ID type: {hex(raw)}")
        return f"unknown_op_id_type_{hex(raw)}"


def get_multi_op_id_type(op_id: int) -> str:
    """
    Get the multi-operation ID type from the operation ID.

    Args:
        op_id: Operation ID value

    Returns:
        str: Multi-operation ID type
    """
    if op_id in MULTI_OP_ID_TYPES:
        return MULTI_OP_ID_TYPES[op_id]
    else:
        logger.warning(f"Unknown multi-operation ID type: {hex(op_id)}")
        return f"unknown_multi_op_id_type_{hex(op_id)}"


def read_data(op_id: int, bit_subdata: bitstring.BitStream) -> Dict[str, Any]:
    """
    Read data from a BitString based on the operation ID.

    Args:
        op_id: Operation ID value
        bit_subdata: BitString containing the data

    Returns:
        Dict[str, Any]: Dictionary containing the read data
    """
    # This is a simplified version of the actual SCTE-104 data reading
    # In a real implementation, we would need to handle all operation types
    if op_id == 0x0001:  # splice_request_data
        data = {}
        data["splice_insert_type"] = bit_subdata.read("uint:8")
        data["splice_event_id"] = bit_subdata.read("uint:32")
        data["unique_program_id"] = bit_subdata.read("uint:16")
        data["pre_roll_time"] = bit_subdata.read("uint:16")
        data["break_duration"] = bit_subdata.read("uint:16")
        data["avail_num"] = bit_subdata.read("uint:8")
        data["avails_expected"] = bit_subdata.read("uint:8")
        data["auto_return_flag"] = bit_subdata.read("uint:8")
        return data
    elif op_id == 0x0004:  # time_signal_request_data
        data = {}
        data["pre_roll_time"] = bit_subdata.read("uint:16")
        return data
    elif op_id == 0x000E:  # insert_segmentation_descriptor_request_data
        data = {}
        data["segmentation_event_id"] = bit_subdata.read("uint:32")
        data["segmentation_event_cancel_indicator"] = bit_subdata.read("uint:8")
        data["duration"] = bit_subdata.read("uint:16")
        data["segmentation_upid_type"] = bit_subdata.read("uint:8")
        data["segmentation_upid_length"] = bit_subdata.read("uint:8")
        upid_length = data["segmentation_upid_length"]

        # Read UPID
        if upid_length > 0:
            data["segmentation_upid"] = bit_subdata.read("hex:" + str(upid_length * 8))
        else:
            data["segmentation_upid"] = ""

        data["segmentation_type_id"] = bit_subdata.read("uint:8")

        # Look up segmentation type
        if data["segmentation_type_id"] in SEGMENTATION_TYPE_IDS:
            data["segmentation_type_id"] = SEGMENTATION_TYPE_IDS[
                data["segmentation_type_id"]
            ]
        else:
            logger.warning(
                f"Unknown segmentation type ID: {hex(data['segmentation_type_id'])}"
            )
            data["segmentation_type_id"] = {
                "name": f"Unknown_{hex(data['segmentation_type_id'])}",
                "table": 0x00,
                "message_value": data["segmentation_type_id"],
            }

        data["segment_num"] = bit_subdata.read("uint:8")
        data["segments_expected"] = bit_subdata.read("uint:8")
        data["sub_segment_num"] = bit_subdata.read("uint:8")
        data["sub_segments_expected"] = bit_subdata.read("uint:8")

        return data
    else:
        logger.warning(f"Unsupported operation ID for data reading: {hex(op_id)}")
        return {"error": f"Unsupported operation ID: {hex(op_id)}"}


def encode_data(
    op_id: int, bit_array: bitstring.BitArray, data: Dict[str, Any], position: int
) -> int:
    """
    Encode data into a BitArray based on the operation ID.

    Args:
        op_id: Operation ID value
        bit_array: BitArray to encode the data into
        data: Dictionary containing the data to encode
        position: Position in the BitArray to start encoding

    Returns:
        int: New position in the BitArray after encoding
    """
    if op_id == 0x0001:  # splice_request_data
        bit_array[position : position + 8] = bitstring.pack(
            "uint:8", data.get("splice_insert_type", 0)
        )
        position += 8
        bit_array[position : position + 32] = bitstring.pack(
            "uint:32", data.get("splice_event_id", 0)
        )
        position += 32
        bit_array[position : position + 16] = bitstring.pack(
            "uint:16", data.get("unique_program_id", 0)
        )
        position += 16
        bit_array[position : position + 16] = bitstring.pack(
            "uint:16", data.get("pre_roll_time", 0)
        )
        position += 16
        bit_array[position : position + 16] = bitstring.pack(
            "uint:16", data.get("break_duration", 0)
        )
        position += 16
        bit_array[position : position + 8] = bitstring.pack(
            "uint:8", data.get("avail_num", 0)
        )
        position += 8
        bit_array[position : position + 8] = bitstring.pack(
            "uint:8", data.get("avails_expected", 0)
        )
        position += 8
        bit_array[position : position + 8] = bitstring.pack(
            "uint:8", data.get("auto_return_flag", 0)
        )
        position += 8
    elif op_id == 0x0004:  # time_signal_request_data
        bit_array[position : position + 16] = bitstring.pack(
            "uint:16", data.get("pre_roll_time", 0)
        )
        position += 16
    elif op_id == 0x000E:  # insert_segmentation_descriptor_request_data
        bit_array[position : position + 32] = bitstring.pack(
            "uint:32", data.get("segmentation_event_id", 0)
        )
        position += 32
        bit_array[position : position + 8] = bitstring.pack(
            "uint:8", data.get("segmentation_event_cancel_indicator", 0)
        )
        position += 8
        bit_array[position : position + 16] = bitstring.pack(
            "uint:16", data.get("duration", 0)
        )
        position += 16
        bit_array[position : position + 8] = bitstring.pack(
            "uint:8", data.get("segmentation_upid_type", 0)
        )
        position += 8

        # Get UPID length and data
        upid_length = data.get("segmentation_upid_length", 0)
        bit_array[position : position + 8] = bitstring.pack("uint:8", upid_length)
        position += 8

        # Write UPID if present
        if upid_length > 0:
            upid = data.get("segmentation_upid", "")
            # Convert hex string to bits if needed
            if isinstance(upid, str) and upid:
                upid_bits = bitstring.BitArray(hex=upid)
                bit_array[position : position + (upid_length * 8)] = upid_bits
            elif isinstance(upid, bytes):
                bit_array[position : position + (upid_length * 8)] = bitstring.BitArray(
                    bytes=upid
                )
            position += upid_length * 8

        # Write segmentation type ID
        seg_type = data.get("segmentation_type_id", {})
        if isinstance(seg_type, dict):
            seg_value = seg_type.get("message_value", 0)
        else:
            seg_value = seg_type
        bit_array[position : position + 8] = bitstring.pack("uint:8", seg_value)
        position += 8

        bit_array[position : position + 8] = bitstring.pack(
            "uint:8", data.get("segment_num", 0)
        )
        position += 8
        bit_array[position : position + 8] = bitstring.pack(
            "uint:8", data.get("segments_expected", 0)
        )
        position += 8
        bit_array[position : position + 8] = bitstring.pack(
            "uint:8", data.get("sub_segment_num", 0)
        )
        position += 8
        bit_array[position : position + 8] = bitstring.pack(
            "uint:8", data.get("sub_segments_expected", 0)
        )
        position += 8
    else:
        logger.warning(f"Unsupported operation ID for data encoding: {hex(op_id)}")

    return position

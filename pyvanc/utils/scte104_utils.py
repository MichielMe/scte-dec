"""SCTE-104 utility functions."""

from typing import Dict, Optional

# Mapping of segmentation type IDs to descriptive names
SEGMENTATION_TYPE_NAMES = {
    # Common types
    0x00: "Not Indicated",
    0x01: "Content Identification",
    # Program
    0x10: "Program Start",
    0x11: "Program End",
    0x12: "Program Early Termination",
    0x13: "Program Breakaway",
    0x14: "Program Resumption",
    0x15: "Program Runover Planned",
    0x16: "Program Runover Unplanned",
    0x17: "Program Overlap Start",
    0x18: "Program Blackout Override",
    0x19: "Program Start - In Progress",
    # Chapter
    0x20: "Chapter Start",
    0x21: "Chapter End",
    # Break
    0x22: "Break Start",
    0x23: "Break End",
    # Opening/Closing Credits
    0x24: "Opening Credit Start",
    0x25: "Opening Credit End",
    0x26: "Closing Credit Start",
    0x27: "Closing Credit End",
    # Provider Advertisement
    0x30: "Provider Advertisement Start",
    0x31: "Provider Advertisement End",
    # Distributor Advertisement
    0x32: "Distributor Advertisement Start",
    0x33: "Distributor Advertisement End",
    # Provider Placement Opportunity
    0x34: "Provider Placement Opportunity Start",
    0x35: "Provider Placement Opportunity End",
    # Distributor Placement Opportunity
    0x36: "Distributor Placement Opportunity Start",
    0x37: "Distributor Placement Opportunity End",
    # Overlay Placement Opportunity
    0x38: "Provider Overlay Placement Opportunity Start",
    0x39: "Provider Overlay Placement Opportunity End",
    0x3A: "Distributor Overlay Placement Opportunity Start",
    0x3B: "Distributor Overlay Placement Opportunity End",
    # Unscheduled Event
    0x40: "Unscheduled Event Start",
    0x41: "Unscheduled Event End",
    # Network
    0x50: "Network Start",
    0x51: "Network End",
    # Morpheus-specific types (based on observation)
    0x88: "Morpheus Content Marker",
    0x98: "Morpheus Program Boundary",
    0xA0: "Morpheus Advertisement",
    0xB0: "Morpheus Interstitial",
    0xC0: "Morpheus Other Content",
}

# Mapping of UPID types to descriptive names
UPID_TYPE_NAMES = {
    0x00: "Not Used",
    0x01: "User Defined",
    0x02: "ISCI",
    0x03: "Ad-ID",
    0x04: "UMID",
    0x05: "ISAN",
    0x06: "EIDR",
    0x07: "TID",
    0x08: "TI",
    0x09: "ADI",
    0x0A: "UUID",
}


def get_segmentation_type_name(type_id: int) -> str:
    """Get descriptive name for a segmentation type ID.

    Args:
        type_id: Segmentation type ID

    Returns:
        Descriptive name or formatted hex value for unknown types
    """
    if type_id in SEGMENTATION_TYPE_NAMES:
        return SEGMENTATION_TYPE_NAMES[type_id]
    else:
        return f"Unknown Type (0x{type_id:02x})"


def get_upid_type_name(type_id: int) -> str:
    """Get descriptive name for a UPID type.

    Args:
        type_id: UPID type ID

    Returns:
        Descriptive name or formatted hex value for unknown types
    """
    if type_id in UPID_TYPE_NAMES:
        return UPID_TYPE_NAMES[type_id]
    else:
        return f"Unknown UPID Type (0x{type_id:02x})"


def format_morpheus_scte104(event_id: int, type_id: int) -> Dict[str, str]:
    """Format Morpheus SCTE-104 data in a human-readable form.

    Args:
        event_id: Segmentation event ID
        type_id: Segmentation type ID

    Returns:
        Dictionary with formatted information
    """
    type_name = get_segmentation_type_name(type_id)

    return {
        "event_id": f"0x{event_id:08x}",
        "event_id_decimal": str(event_id),
        "type_id": f"0x{type_id:02x}",
        "type_name": type_name,
    }


def parse_upid(upid_type: int, upid_hex: str) -> Dict[str, str]:
    """Parse and format UPID based on its type.

    Args:
        upid_type: UPID type ID
        upid_hex: UPID as a hex string

    Returns:
        Dictionary with parsed UPID information
    """
    type_name = get_upid_type_name(upid_type)
    result = {
        "type": upid_type,
        "type_name": type_name,
        "hex": upid_hex,
    }

    # Format the UPID based on its type
    if upid_type == 0x01:  # User Defined
        # Try to interpret as ASCII if possible
        try:
            upid_bytes = bytes.fromhex(upid_hex)
            ascii_str = upid_bytes.decode("ascii", errors="replace")
            result["value"] = ascii_str
        except Exception:
            result["value"] = upid_hex
    elif upid_type == 0x0A:  # UUID
        # Format as UUID if possible (8-4-4-4-12 format)
        if len(upid_hex) == 32:
            uuid = f"{upid_hex[0:8]}-{upid_hex[8:12]}-{upid_hex[12:16]}-{upid_hex[16:20]}-{upid_hex[20:32]}"
            result["value"] = uuid
        else:
            result["value"] = upid_hex
    else:
        # For other types, just keep the hex representation
        result["value"] = upid_hex

    return result

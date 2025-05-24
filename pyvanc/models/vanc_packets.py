"""VANC packet data models."""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional


class OperationType(IntEnum):
    """SCTE-104 operation types."""

    SPLICE_REQUEST_DATA = 0x0101
    SPLICE_NULL_REQUEST_DATA = 0x0102
    TIME_SIGNAL_REQUEST_DATA = 0x0104
    INSERT_AVAIL_DESCRIPTOR_REQUEST_DATA = 0x0108
    INSERT_DTMF_DESCRIPTOR_REQUEST_DATA = 0x010A
    INSERT_SEGMENTATION_DESCRIPTOR_REQUEST_DATA = 0x010B


class SegmentationTypeID(IntEnum):
    """SCTE-104/35 segmentation type IDs."""

    NOT_INDICATED = 0x00
    CONTENT_ID = 0x01
    PROGRAM_START = 0x10
    PROGRAM_END = 0x11
    PROGRAM_EARLY_TERMINATION = 0x12
    PROGRAM_BREAKAWAY = 0x13
    PROGRAM_RESUMPTION = 0x14
    PROGRAM_RUNOVER_PLANNED = 0x15
    PROGRAM_RUNOVER_UNPLANNED = 0x16
    PROGRAM_OVERLAP_START = 0x17
    PROGRAM_BLACKOUT_OVERRIDE = 0x18
    PROGRAM_START_IN_PROGRESS = 0x19
    CHAPTER_START = 0x20
    CHAPTER_END = 0x21
    BREAK_START = 0x22
    BREAK_END = 0x23
    OPENING_CREDIT_START = 0x24
    OPENING_CREDIT_END = 0x25
    CLOSING_CREDIT_START = 0x26
    CLOSING_CREDIT_END = 0x27
    PROVIDER_ADVERTISEMENT_START = 0x30
    PROVIDER_ADVERTISEMENT_END = 0x31
    DISTRIBUTOR_ADVERTISEMENT_START = 0x32
    DISTRIBUTOR_ADVERTISEMENT_END = 0x33
    PROVIDER_PLACEMENT_OPPORTUNITY_START = 0x34
    PROVIDER_PLACEMENT_OPPORTUNITY_END = 0x35
    DISTRIBUTOR_PLACEMENT_OPPORTUNITY_START = 0x36
    DISTRIBUTOR_PLACEMENT_OPPORTUNITY_END = 0x37
    PROVIDER_OVERLAY_PLACEMENT_OPPORTUNITY_START = 0x38
    PROVIDER_OVERLAY_PLACEMENT_OPPORTUNITY_END = 0x39
    DISTRIBUTOR_OVERLAY_PLACEMENT_OPPORTUNITY_START = 0x3A
    DISTRIBUTOR_OVERLAY_PLACEMENT_OPPORTUNITY_END = 0x3B
    UNSCHEDULED_EVENT_START = 0x40
    UNSCHEDULED_EVENT_END = 0x41
    NETWORK_START = 0x50
    NETWORK_END = 0x51


class UPIDType(IntEnum):
    """SCTE-104/35 UPID types."""

    NOT_USED = 0x00
    USER_DEFINED = 0x01
    ISCI = 0x02
    AD_ID = 0x03
    UMID = 0x04
    ISAN = 0x05
    EIDR = 0x06
    TID = 0x07
    TI = 0x08
    ADI = 0x09
    UUID = 0x0A


@dataclass
class VANCPacket:
    """
    VANC packet model.

    Attributes:
        did: Data Identifier
        sdid: Secondary Data Identifier
        payload: Packet payload data
        line: Line number in the video frame
        horizontal_offset: Horizontal position in the video line
        checksum_valid: Whether the packet checksum is valid
    """

    did: int
    sdid: int
    payload: bytes
    line: int = 0
    horizontal_offset: int = 0
    checksum_valid: bool = True

    @property
    def has_valid_checksum(self) -> bool:
        """Return whether the packet checksum is valid."""
        return self.checksum_valid

    def __str__(self) -> str:
        """String representation of the packet."""
        return (
            f"VANC Packet DID=0x{self.did:02x} SDID=0x{self.sdid:02x} "
            f"Line={self.line} HOffset={self.horizontal_offset} "
            f"DataLen={len(self.payload)} ChecksumValid={self.checksum_valid}"
        )


@dataclass
class SCTE104Operation:
    """
    SCTE-104 operation model.

    Attributes:
        opid: Operation identifier
        type: Operation type name or description
        data_length: Length of the operation data
        data: Dictionary of operation-specific data
    """

    opid: int
    type: str = ""
    data_length: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    upid_type: Optional[int] = None
    upid: Optional[bytes] = None

    def __str__(self) -> str:
        """String representation of the operation."""
        result = f"Operation: {self.type} (0x{self.opid:04x})"
        if self.data:
            result += f"\nData: {self.data}"
        return result


@dataclass
class SCTE104Message:
    """
    SCTE-104 message model.

    Attributes:
        opid: Operation identifier
        type: Message type (single or multiple operation)
        protocol_version: Protocol version
        as_index: AS index
        message_num: Message number
        dpi_pid_index: DPI PID index
        operations: List of operations in the message
    """

    opid: int
    type: str = ""
    protocol_version: int = 0
    as_index: int = 0
    message_num: int = 0
    dpi_pid_index: int = 0
    scte35_protocol_version: int = 0
    timestamp_type: int = 0
    timestamp: int = 0
    result_code: int = 0
    result_str: str = ""
    result_str_length: int = 0
    operations: List[SCTE104Operation] = field(default_factory=list)

    def __str__(self) -> str:
        """String representation of the message."""
        result = (
            f"SCTE-104 Message: {self.type}\n"
            f"ProtocolVersion: {self.protocol_version}\n"
            f"AS_index: {self.as_index}\n"
            f"MessageNum: {self.message_num}\n"
            f"DPI_PID_index: {self.dpi_pid_index}\n"
        )

        if self.operations:
            result += f"Operations: {len(self.operations)}\n"
            for i, op in enumerate(self.operations):
                result += f"  [{i}] {op}\n"

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary for serialization."""
        result = {
            "type": self.type,
            "opid": f"0x{self.opid:04x}",
            "protocol_version": self.protocol_version,
            "as_index": self.as_index,
            "message_num": self.message_num,
            "dpi_pid_index": self.dpi_pid_index,
        }

        if self.operations:
            operations = []
            for op in self.operations:
                op_dict = {
                    "opid": f"0x{op.opid:04x}",
                    "type": op.type,
                }
                if op.data:
                    op_dict.update(op.data)
                operations.append(op_dict)
            result["operations"] = operations

        return result

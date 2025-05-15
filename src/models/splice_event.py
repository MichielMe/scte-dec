"""
SpliceEvent models for representing SCTE-104 splice events.

This module provides classes to represent SCTE-104 splice events and related data.
"""

import copy
import json
import logging
from dataclasses import dataclass
from string import Template
from typing import Any, Dict, Optional, Union

import bitstring
from dataclasses_json import LetterCase, Undefined, dataclass_json
from timecode import Timecode

# Try importing from official scte module if available
try:
    from scte.Scte104 import scte104_enums
except ImportError:
    # Fall back to local copy if not available
    import os
    import sys

    # Add parent directory to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.scte104_enums import (
        encode_data,
        get_multi_op_id_type,
        get_op_id_type,
        read_data,
    )

    # Create a mock module to avoid modifying too much code
    class scte104_enums:
        @staticmethod
        def get_op_id_type(raw):
            return get_op_id_type(raw)

        @staticmethod
        def get_multi_op_id_type(op_id):
            return get_multi_op_id_type(op_id)

        @staticmethod
        def read_data(op_id, bit_subdata):
            return read_data(op_id, bit_subdata)

        @staticmethod
        def encode_data(op_id, bit_array, data, position):
            return encode_data(op_id, bit_array, data, position)


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
BYTE_SIZE = 8
FRAME_RATE = 25


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass(frozen=True)
class SCTE104Packet:
    """
    Represents a simplified SCTE-104 packet with essential fields.

    This class provides a simplified representation of a SCTE-104 packet
    with only the most important fields for easier handling and serialization.
    """

    splice_event_timestamp: Union[str, Timecode]
    pre_roll_time: int
    segmentation_event_id: int
    duration: int
    segmentation_upid: str
    segmentation_type: Dict[str, Any]


class SpliceEvent:
    """
    Represents a SCTE-104 splice event.

    This class provides methods to decode, manipulate, and serialize SCTE-104
    splice events.
    """

    def __init__(
        self,
        bitarray_data: Optional[bitstring.BitString] = None,
        init_dict: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a SpliceEvent from either bitarray data or a dictionary.

        Args:
            bitarray_data: Binary data representing the SCTE-104 splice event
            init_dict: Dictionary representation of the SCTE-104 splice event
        """
        if init_dict is not None:
            self.as_dict = init_dict
            return

        if bitarray_data is None:
            raise ValueError("Either bitarray_data or init_dict must be provided")

        message_dict = {}
        message_dict["reserved"] = {"raw": bitarray_data.read("uint:16")}
        message_dict["reserved"]["type"] = scte104_enums.get_op_id_type(
            message_dict["reserved"]["raw"]
        )
        message_dict["message_size"] = bitarray_data.read("uint:16")
        message_dict["protocol_version"] = bitarray_data.read("uint:8")
        message_dict["as_index"] = bitarray_data.read("uint:8")
        message_dict["message_number"] = bitarray_data.read("uint:8")
        message_dict["dpi_pid_index"] = bitarray_data.read("uint:16")
        message_dict["scte35_protocol_version"] = bitarray_data.read("uint:8")
        message_dict["timestamp"] = {}
        message_dict["timestamp"]["time_type"] = bitarray_data.read("uint:8")

        if message_dict["timestamp"]["time_type"] == 1:
            message_dict["timestamp"]["UTC_seconds"] = bitarray_data.read("uint:32")
            message_dict["timestamp"]["UTC_microseconds"] = bitarray_data.read(
                "uint:16"
            )
        elif message_dict["timestamp"]["time_type"] == 2:
            message_dict["timestamp"]["hours"] = bitarray_data.read("uint:8")
            message_dict["timestamp"]["minutes"] = bitarray_data.read("uint:8")
            message_dict["timestamp"]["seconds"] = bitarray_data.read("uint:8")
            message_dict["timestamp"]["frames"] = bitarray_data.read("uint:8")
        elif message_dict["timestamp"]["time_type"] == 3:
            message_dict["timestamp"]["GP_number"] = bitarray_data.read("uint:8")
            message_dict["timestamp"]["GP_edge"] = bitarray_data.read("uint:8")

        message_dict["num_ops"] = bitarray_data.read("uint:8")
        message_dict["ops"] = []

        for index in range(message_dict["num_ops"]):
            message_dict["ops"].append({})
            message_dict["ops"][index]["op_id"] = bitarray_data.read("uint:16")
            message_dict["ops"][index]["type"] = scte104_enums.get_multi_op_id_type(
                message_dict["ops"][index]["op_id"]
            )
            message_dict["ops"][index]["data_length"] = bitarray_data.read("uint:16")
            bit_subdata = bitstring.BitString(
                bytes=bytes.fromhex(
                    bitarray_data.read(
                        "hex:"
                        + str(message_dict["ops"][index]["data_length"] * BYTE_SIZE)
                    )
                )
            )
            message_dict["ops"][index]["data"] = scte104_enums.read_data(
                message_dict["ops"][index]["op_id"], bit_subdata
            )

        self.as_dict = message_dict

    def __str__(self) -> str:
        """
        Return a string representation of the SpliceEvent.

        Returns:
            str: JSON string representation of the SpliceEvent
        """
        return json.dumps(self.to_dict(upid_as_str=True), indent=4, sort_keys=False)

    def to_json(self) -> str:
        """
        Convert the SpliceEvent to a JSON string.

        Returns:
            str: JSON string representation of the SpliceEvent
        """
        return json.dumps(self.to_dict(upid_as_str=True), indent=4, sort_keys=False)

    def to_dict(self, upid_as_str: bool = False) -> Dict[str, Any]:
        """
        Convert the SpliceEvent to a dictionary.

        Args:
            upid_as_str: Whether to convert the segmentation_upid to a string

        Returns:
            Dict[str, Any]: Dictionary representation of the SpliceEvent
        """
        the_dict = copy.deepcopy(self.as_dict)

        if upid_as_str:
            if "ops" in the_dict:
                for idx, op in enumerate(the_dict["ops"]):
                    if "data" in op:
                        if "segmentation_upid" in op["data"]:
                            the_dict["ops"][idx]["data"]["segmentation_upid"] = str(
                                the_dict["ops"][idx]["data"]["segmentation_upid"]
                            )

        return the_dict

    def deep_copy(self) -> Dict[str, Any]:
        """
        Create a deep copy of the SpliceEvent's dictionary representation.

        Returns:
            Dict[str, Any]: Deep copy of the SpliceEvent's dictionary
        """
        return copy.deepcopy(self.as_dict)

    def to_binary(self) -> bitstring.BitArray:
        """
        Convert the SpliceEvent to binary data.

        Returns:
            bitstring.BitArray: Binary representation of the SpliceEvent
        """
        self.position = 0
        bit_array = bitstring.BitArray(length=self.as_dict["message_size"] * BYTE_SIZE)

        self._manipulate_bits(bit_array, self.as_dict["reserved"]["raw"], bytes=2)
        self._manipulate_bits(bit_array, self.as_dict["message_size"], bytes=2)
        self._manipulate_bits(bit_array, self.as_dict["protocol_version"], bytes=1)
        self._manipulate_bits(bit_array, self.as_dict["as_index"], bytes=1)
        self._manipulate_bits(bit_array, self.as_dict["message_number"], bytes=1)
        self._manipulate_bits(bit_array, self.as_dict["dpi_pid_index"], bytes=2)
        self._manipulate_bits(
            bit_array, self.as_dict["scte35_protocol_version"], bytes=1
        )
        self._manipulate_bits(
            bit_array, self.as_dict["timestamp"]["time_type"], bytes=1
        )  # timestamp

        if self.as_dict["timestamp"]["time_type"] == 1:
            self._manipulate_bits(
                bit_array, self.as_dict["timestamp"]["UTC_seconds"], bytes=4
            )
            self._manipulate_bits(
                bit_array, self.as_dict["timestamp"]["UTC_microseconds"], bytes=2
            )
        elif self.as_dict["timestamp"]["time_type"] == 2:
            self._manipulate_bits(
                bit_array, self.as_dict["timestamp"]["hours"], bytes=1
            )
            self._manipulate_bits(
                bit_array, self.as_dict["timestamp"]["minutes"], bytes=1
            )
            self._manipulate_bits(
                bit_array, self.as_dict["timestamp"]["seconds"], bytes=1
            )
            self._manipulate_bits(
                bit_array, self.as_dict["timestamp"]["frames"], bytes=1
            )
        elif self.as_dict["timestamp"]["time_type"] == 3:
            self._manipulate_bits(
                bit_array, self.as_dict["timestamp"]["GP_number"], bytes=1
            )
            self._manipulate_bits(
                bit_array, self.as_dict["timestamp"]["GP_edge"], bytes=1
            )

        self._manipulate_bits(bit_array, self.as_dict["num_ops"], bytes=1)

        for index in range(self.as_dict["num_ops"]):
            # Read in metadata to bit string
            self._manipulate_bits(
                bit_array, self.as_dict["ops"][index]["op_id"], bytes=2
            )
            self._manipulate_bits(
                bit_array, self.as_dict["ops"][index]["data_length"], bytes=2
            )

            # Read in actual position to metadata
            scte104_enums.encode_data(
                self.as_dict["ops"][index]["op_id"],
                bit_array,
                self.as_dict["ops"][index]["data"],
                self.position,
            )

            # Adjust position by data offset
            self.position = (
                self.position + (self.as_dict["ops"][index]["data_length"]) * BYTE_SIZE
            )

        return bit_array

    def _manipulate_bits(
        self, bit_array: bitstring.BitArray, value: int, bytes: int = 1
    ) -> None:
        """
        Manipulate bits in a bit array.

        Args:
            bit_array: Bit array to manipulate
            value: Value to write to the bit array
            bytes: Number of bytes to write
        """
        hex_val = self._hex_string(value, bytes)
        bit_array.overwrite(hex_val, pos=self.position)
        self.position = self.position + bytes * BYTE_SIZE

    def _hex_string(self, value: int, bytes: int) -> str:
        """
        Convert an integer to a hexadecimal string.

        Args:
            value: Integer value to convert
            bytes: Number of bytes in the output string

        Returns:
            str: Hexadecimal string representation of the value
        """
        s = hex(value)
        return "0x" + s[2:].zfill(bytes * 2)

    def get_pre_roll_time(self) -> int:
        """
        Get the pre-roll time from the SpliceEvent.

        Returns:
            int: Pre-roll time in milliseconds
        """
        return self.as_dict["ops"][0]["data"]["pre_roll_time"]

    def get_splice_event_timestamp(self) -> Timecode:
        """
        Get the splice event timestamp from the SpliceEvent.

        Returns:
            Timecode: Splice event timestamp
        """
        if self.as_dict["timestamp"]["time_type"] == 2:
            splice_event_template = Template("${hours}:${minutes}:${seconds}:${frames}")
            hours = int(self.as_dict["timestamp"]["hours"])
            minutes = int(self.as_dict["timestamp"]["minutes"])
            seconds = int(self.as_dict["timestamp"]["seconds"])
            frames = int(self.as_dict["timestamp"]["frames"])

            splice_event_timestamp = Timecode(
                FRAME_RATE,
                splice_event_template.substitute(
                    hours=hours, minutes=minutes, seconds=seconds, frames=frames
                ),
            )

            # Convert preroll in milliseconds to frames
            preroll_to_frames = (
                int(self.as_dict["ops"][0]["data"]["pre_roll_time"]) // 40
            )
            preroll = Timecode(FRAME_RATE, None, None, preroll_to_frames, False)

            # Add announced timestamp and preroll to return timestamp of transition point
            return splice_event_timestamp + preroll
        else:
            # Not implemented for other time types
            logger.warning(
                f"get_splice_event_timestamp not implemented for time_type {self.as_dict['timestamp']['time_type']}"
            )
            return None

    def get_segmentation_upid(self) -> str:
        """
        Get the segmentation UPID from the SpliceEvent.

        Returns:
            str: Segmentation UPID
        """
        return self.as_dict["ops"][1]["data"]["segmentation_upid"]

    def get_segmentation_type_id(self) -> Dict[str, Any]:
        """
        Get the segmentation type ID from the SpliceEvent.

        Returns:
            Dict[str, Any]: Segmentation type ID information
        """
        return self.as_dict["ops"][1]["data"]["segmentation_type_id"]

    def get_segmentation_event_id(self) -> int:
        """
        Get the segmentation event ID from the SpliceEvent.

        Returns:
            int: Segmentation event ID
        """
        return self.as_dict["ops"][1]["data"]["segmentation_event_id"]

    def get_duration(self) -> int:
        """
        Get the duration from the SpliceEvent.

        Returns:
            int: Duration in seconds
        """
        return self.as_dict["ops"][1]["data"]["duration"]  # seconds

    def set_pre_roll_time(self, time: int) -> None:
        """
        Set the pre-roll time in the SpliceEvent.

        Args:
            time: Pre-roll time in milliseconds
        """
        self.as_dict["ops"][0]["data"]["pre_roll_time"] = time

    def print_detailed(self) -> None:
        """
        Print detailed information about the SpliceEvent.
        """
        print(
            "reserved",
            hex(self.as_dict["reserved"]["raw"]),
            self.as_dict["reserved"]["type"],
        )
        print(
            "message_size",
            hex(self.as_dict["message_size"]),
            self.as_dict["message_size"],
        )
        print(
            "protocol_version",
            hex(self.as_dict["protocol_version"]),
            self.as_dict["protocol_version"],
        )
        print("as_index", hex(self.as_dict["as_index"]), self.as_dict["as_index"])
        print(
            "message_number",
            hex(self.as_dict["message_number"]),
            self.as_dict["message_number"],
        )
        print(
            "dpi_pid_index",
            hex(self.as_dict["dpi_pid_index"]),
            self.as_dict["dpi_pid_index"],
        )
        print(
            "scte35_protocol_version",
            hex(self.as_dict["scte35_protocol_version"]),
            self.as_dict["scte35_protocol_version"],
        )
        print(
            "timestamp",
            hex(self.as_dict["timestamp"]["time_type"]),
            self.as_dict["timestamp"]["time_type"],
        )

        if self.as_dict["timestamp"]["time_type"] == 2:
            print(
                "  hours",
                hex(self.as_dict["timestamp"]["hours"]),
                self.as_dict["timestamp"]["hours"],
            )
            print(
                "  minutes",
                hex(self.as_dict["timestamp"]["minutes"]),
                self.as_dict["timestamp"]["minutes"],
            )
            print(
                "  seconds",
                hex(self.as_dict["timestamp"]["seconds"]),
                self.as_dict["timestamp"]["seconds"],
            )
            print(
                "  frames",
                hex(self.as_dict["timestamp"]["frames"]),
                self.as_dict["timestamp"]["frames"],
            )
            print("num_ops", hex(self.as_dict["num_ops"]), self.as_dict["num_ops"])

        if self.as_dict["timestamp"]["time_type"] == 1:
            print(
                "  UTC_seconds",
                hex(self.as_dict["timestamp"]["UTC_seconds"]),
                self.as_dict["timestamp"]["UTC_seconds"],
            )
            print(
                "  UTC_microseconds",
                hex(self.as_dict["timestamp"]["UTC_microseconds"]),
                self.as_dict["timestamp"]["UTC_microseconds"],
            )

        for index in range(len(self.as_dict["ops"])):
            print(
                "op_id",
                hex(self.as_dict["ops"][index]["op_id"]),
                self.as_dict["ops"][index]["op_id"],
                self.as_dict["ops"][index]["type"],
            )
            print(
                "data_length",
                hex(self.as_dict["ops"][index]["data_length"]),
                self.as_dict["ops"][index]["data_length"],
            )
            print("data")

            for key in self.as_dict["ops"][index]["data"]:
                print("  ", key, self.as_dict["ops"][index]["data"][key])

    def log_detailed(self) -> None:
        """
        Log detailed information about the SpliceEvent.
        """
        logger.info(
            "reserved %s %s",
            hex(self.as_dict["reserved"]["raw"]),
            self.as_dict["reserved"]["type"],
        )
        logger.info(
            "message_size %s %s",
            hex(self.as_dict["message_size"]),
            self.as_dict["message_size"],
        )
        logger.info(
            "protocol_version %s %s",
            hex(self.as_dict["protocol_version"]),
            self.as_dict["protocol_version"],
        )
        logger.info(
            "as_index %s %s", hex(self.as_dict["as_index"]), self.as_dict["as_index"]
        )
        logger.info(
            "message_number %s %s",
            hex(self.as_dict["message_number"]),
            self.as_dict["message_number"],
        )
        logger.info(
            "dpi_pid_index %s %s",
            hex(self.as_dict["dpi_pid_index"]),
            self.as_dict["dpi_pid_index"],
        )
        logger.info(
            "scte35_protocol_version %s %s",
            hex(self.as_dict["scte35_protocol_version"]),
            self.as_dict["scte35_protocol_version"],
        )
        logger.info(
            "timestamp %s %s",
            hex(self.as_dict["timestamp"]["time_type"]),
            self.as_dict["timestamp"]["time_type"],
        )

        if self.as_dict["timestamp"]["time_type"] == 2:
            logger.info(
                "  hours %s %s",
                hex(self.as_dict["timestamp"]["hours"]),
                self.as_dict["timestamp"]["hours"],
            )
            logger.info(
                "  minutes %s %s",
                hex(self.as_dict["timestamp"]["minutes"]),
                self.as_dict["timestamp"]["minutes"],
            )
            logger.info(
                "  seconds %s %s",
                hex(self.as_dict["timestamp"]["seconds"]),
                self.as_dict["timestamp"]["seconds"],
            )
            logger.info(
                "  frames %s %s",
                hex(self.as_dict["timestamp"]["frames"]),
                self.as_dict["timestamp"]["frames"],
            )
            logger.info(
                "num_ops %s %s", hex(self.as_dict["num_ops"]), self.as_dict["num_ops"]
            )

        if self.as_dict["timestamp"]["time_type"] == 1:
            logger.info(
                "  UTC_seconds %s %s",
                hex(self.as_dict["timestamp"]["UTC_seconds"]),
                self.as_dict["timestamp"]["UTC_seconds"],
            )
            logger.info(
                "  UTC_microseconds %s %s",
                hex(self.as_dict["timestamp"]["UTC_microseconds"]),
                self.as_dict["timestamp"]["UTC_microseconds"],
            )

        for index in range(len(self.as_dict["ops"])):
            logger.info(
                "op_id %s %s %s",
                hex(self.as_dict["ops"][index]["op_id"]),
                self.as_dict["ops"][index]["op_id"],
                self.as_dict["ops"][index]["type"],
            )
            logger.info(
                "data_length %s %s",
                hex(self.as_dict["ops"][index]["data_length"]),
                self.as_dict["ops"][index]["data_length"],
            )
            logger.info("data")

            for key in self.as_dict["ops"][index]["data"]:
                logger.info("   %s %s", key, self.as_dict["ops"][index]["data"][key])

        # Add newline
        logger.info("")

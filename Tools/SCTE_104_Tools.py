from SpliceEvent import SpliceEvent
import bitstring
from dataclasses import dataclass
from typing import List

from dataclasses_json import LetterCase, Undefined, dataclass_json

@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass(frozen=True)
class SCTE104Packet:
    splice_event_timestamp: str
    pre_roll_time: int
    segmentation_event_id: int
    duration: int
    segmentation_upid: str
    segmentation_type: dict

def decode_SCTE104(hex_string) -> SpliceEvent:
    bitarray_data = bitstring.BitString(bytes=bytes.fromhex(hex_string))
    return SpliceEvent(bitarray_data)

def decode_SCTE104_to_output(hex_string) -> SpliceEvent:
    print("Decoding:", hex_string)
    bitarray_data = bitstring.BitString(bytes=bytes.fromhex(hex_string))
    my_event = SpliceEvent(bitarray_data)
    print(my_event)

def decode_SCTE104_to_SCTE104Packet(hex_string) -> SCTE104Packet:
    bitarray_data = bitstring.BitString(bytes=bytes.fromhex(hex_string))
    result = SpliceEvent(bitarray_data)
    return (SCTE104Packet(
            result.get_splice_event_timestamp(), 
            result.get_pre_roll_time(),
            result.get_segmentation_event_id(),
            result.get_duration(),
            result.get_segmentation_upid(),
            result.get_segmentation_type_id()))


from scte.Scte104.SpliceEvent import SpliceEvent
import bitstring
import json

def decode_SCTE104(hex_string) -> SpliceEvent:
    print("Decoding:", hex_string)
    bitarray_data = bitstring.BitString(bytes=bytes.fromhex(hex_string))
    return SpliceEvent(bitarray_data)

def decode_SCTE104_to_output(hex_string) -> SpliceEvent:
    print("Decoding:", hex_string)
    bitarray_data = bitstring.BitString(bytes=bytes.fromhex(hex_string))
    my_event = SpliceEvent(bitarray_data)
    print(my_event)

def decode_SCTE104_to_file(hex_string):
    print("Logging to file. Decoding:", hex_string)
    bitarray_data = bitstring.BitString(bytes=bytes.fromhex(hex_string))
    my_event = SpliceEvent(bitarray_data)
    my_event.log_detailed()
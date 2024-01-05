from functools import reduce
import logging
from shutil import ReadError
import pytz
import datetime
from datetime import timezone
from timecode import Timecode
from SCTE_104_Tools import decode_SCTE104, decode_SCTE104_to_file
from bitstring import ReadError
from PhabrixTools import make_fake_phabrix_anc_data, fake_anc_decode

# make helper function to make processing pipeline of data
def compose(*functions):
    return reduce(lambda f, g: lambda x: g(f(x)), functions)

# this is copied from the probel controller card log
    
#probel_string = "0xff [0] 0xff [1] 0x0 [2] 0x50 [3] 0x0 [4] 0x0 [5] 0xe3 [6] 0x0 [7] 0x0 [8] 0x0 [9] 0x2 [10] 0xe [11] 0xe [12] 0x10 [13] 0x3 [14] 0x2 [15] 0x1 [16] 0x4 [17] 0x0 [18] 0x2 [19] 0x1f [20] 0x40 [21] 0x1 [22] 0xb [23] 0x0 [24] 0x36 [25] 0x0 [26] 0x0 [27] 0x0 [28] 0x0 [29] 0x0 [30] 0x0 [31] 0x1e [32] 0xf [33] 0x24 [34] 0x61 [35] 0x65 [36] 0x39 [37] 0x65 [38] 0x33 [39] 0x36 [40] 0x39 [41] 0x33 [42] 0x2d [43] 0x30 [44] 0x34 [45] 0x33 [46] 0x37 [47] 0x2d [48] 0x34 [49] 0x66 [50] 0x32 [51] 0x32 [52] 0x2d [53] 0x62 [54] 0x37 [55] 0x61 [56] 0x66 [57] 0x2d [58] 0x31 [59] 0x66 [60] 0x35 [61] 0x39 [62] 0x37 [63] 0x63 [64] 0x63 [65] 0x30 [66] 0x63 [67] 0x30 [68] 0x61 [69] 0x63 [70] 0xa [71] 0x0 [72] 0x0 [73] 0x0 [74] 0x0 [75] 0x0 [76] 0x0 [77] 0x0 [78] 0x0 [79]"
# Program Start
#probel_string = "0xff [0] 0xff [1] 0x0 [2] 0x2c [3] 0x0 [4] 0x0 [5] 0xdb [6] 0x0 [7] 0x0 [8] 0x0 [9] 0x2 [10] 0x13 [11] 0x6 [12] 0xc [13] 0x15 [14] 0x2 [15] 0x1 [16] 0x4 [17] 0x0 [18] 0x2 [19] 0x1f [20] 0x40 [21] 0x1 [22] 0xb [23] 0x0 [24] 0x12 [25] 0x0 [26] 0x0 [27] 0x0 [28] 0x0 [29] 0x0 [30] 0x0 [31] 0x3c [32] 0xf [33] 0x0 [34] 0x10 [35] 0x0 [36] 0x0 [37] 0x0 [38] 0x0 [39] 0x0 [40] 0x0 [41] 0x0 [42] 0x0 [43]"
# Ad start

def list_to_string(my_list):
    line = ""
    for item in my_list:
        line = line + item
    return line

def convert_to_int(dataframe):
    raw_anc = ['1023', '1023', '577', '263', '557', '264', '767', '767', '512', '300', '512', '512', '731', '512', '512', '512', '258', '275', '518', '20', '524', '277', '258', '257', '260', '512', '258', '287', '320', '257', '267', '512', '530', '512', '512', '512', '512', '512', '512', '572', '40', '527', '512', '272', '512', '512', '512', '512', '512', '512', '512', '512', '415', '0', '0', '0', '0', '0', '0', '0', '0']
    print("bitshift:", [(int(hex_data) >> 2) for hex_data in raw_anc])
    print(dataframe, type(dataframe))

    return [(int(hex_data.zfill(2) , 16)) for hex_data in dataframe]

def make_fake_phabrix_anc_data(probel_string):
    probel_string = filter_probel_string(probel_string)
    raw_anc = ['1023', '1023', '577', '263', '557', '264', '767', '767', '512', '300', '512', '512', '731', '512', '512', '512', '258', '275', '518', '20', '524', '277', '258', '257', '260', '512', '258', '287', '320', '257', '267', '512', '530', '512', '512', '512', '512', '512', '512', '572', '40', '527', '512', '272', '512', '512', '512', '512', '512', '512', '512', '512', '415', '0', '0', '0', '0', '0', '0', '0', '0']
    print(probel_string)
    print(raw_anc[6:])
    print([hex(int(hex_data,16)).zfill(2) for hex_data in probel_string])
    for hex_data in probel_string:
        print(hex_data, bin(int(hex_data, 16) << 2), hex((int(hex_data,16))), (int(hex_data,16)), hex((int(hex_data,16))<< 2))
    for hex_data in raw_anc[6:]:
        print(hex_data, bin(int(hex_data)), hex(int(hex_data)), hex(int(hex_data) >> 2))
    #print([hex(int(hex_data) >> 2).zfill(2) for hex_data in raw_anc[6:]])
    print(hex(1023 >> 2) )
    

    #chunks = [probel_string[i:i+chunk_length] for i in range(0, len(probel_string), chunk_length)]


def filter_probel_string(probel_string):
    return ([n[2:].zfill(2) for index, n in enumerate(probel_string.split(" ")) if not index%2])

morpheus_preprocessor = compose(filter_probel_string, list_to_string)

def log_filtered_kerneldiag_logs(line, ignore_keep_alive=False):
    logging.basicConfig(filename='scte_diags.log', encoding='utf-8', filemode='w', format='%(message)s', level=logging.INFO)
    log = logging.getLogger(__name__)
    all_log_lines = []
    '''
    if only one item is needed from the generator object:
    #result = next(itertools.islice(line, 0, None))
    '''
    # get utc hour offset
    naive = datetime.datetime.now()
    timezone = pytz.timezone("Europe/Brussels")
    utc_offset = timezone.localize(naive)
    utc_adjusted_hour = (utc_offset.utcoffset().seconds//3600)

    for result in line:
        single_log_line = {}
        '''
        example line:
        10_240_33_166|167 26-AUG-2022 12:30:40:06: SCTE104_AdsProtocol,SendData, data sent: 0x0 [0] 0x3 [1] 0x0 [2] 0xd [3] 0xff [4] 0xff [5] 0xff [6] 0xff [7] 0x0 [8] 0x0 [9] 0x3 [10] 0x0 [11] 0x2 [12]  [166-Active]
        1. First we split on the semicolon to separate the [card pair][timestamp], [topic], [data string], [active controller]
        2. Then we reconstruct the timecode from the first field, using some string slicing to reconstruct a timecode string. Then we convert this to a Timecode object at 25fps.
        3. The rest of the dict items is selected from the other fields
        4. Finally, constructing a single dict with the timecode, device, the original data for debugging purposes and the hex data send. This data is converted into a hex stream string.
        '''
        result = result.split(":")
        
        hours = result[0][len(result[0])-2:]
        minutes = result[1]
        seconds = result[2]
        frames = result[3]

        timecode_string = f"{hours}:{minutes}:{seconds}:{frames}"
        automation_ts = Timecode('25', timecode_string)

        utc_adjusted_timecode_string = f"{int(hours)+utc_adjusted_hour}:{minutes}:{seconds}:{frames}"
        utc_adjusted_automation_ts = Timecode('25', utc_adjusted_timecode_string)

        single_log_line["timecode"] = str(automation_ts)
        single_log_line["timecode_utc_adjusted"] = str(utc_adjusted_automation_ts)
        automation_ts.set_fractional(True)
        utc_adjusted_automation_ts.set_fractional(True)
        single_log_line["timecode_frac"] = str(automation_ts)
        single_log_line["timecode_utc_adjusted_frac"] = str(utc_adjusted_automation_ts)
        

        # only device needed
        single_log_line["device"] = result[4].split(",")[0]
        # sent data
        probel_string = result[5][1:-14]
        single_log_line["orig"] = probel_string
        single_log_line["data"] = morpheus_preprocessor(probel_string)
    
        
        all_log_lines.append(single_log_line)

    for scte_event_in_log in all_log_lines:
        #print(scte_event_in_log)
        try:
            # 0003000dffffffff0000 = keep_alive message
            if ignore_keep_alive == True and "0003000dffffffff0000" in scte_event_in_log["data"]:
                    # skip keep alive messages
                    pass
            else:
                log.info("@ %s (%s) ~ %s (%s)", scte_event_in_log["timecode"], scte_event_in_log["timecode_frac"], scte_event_in_log["timecode_utc_adjusted"], scte_event_in_log["timecode_utc_adjusted_frac"])
                print("trying decode ", single_log_line["data"])
                decode_SCTE104_to_file(scte_event_in_log["data"])
        except ReadError:
            print("error decoding: ", scte_event_in_log)

def filter_kernel_diags_on_device_and_keyword(file, device, keyword):
    
    #filtered = (line for filtered_lines in open('KernelDiags.log') if device in filtered_lines for line in filtered_lines if keyword in filtered_lines)
    line = (line for line in open(file) if device in line )
    filtered = (filtered for filtered in line if keyword in filtered )
    return filtered

def morpheus_log_parser(probel_string):
    #manual_anc = "ffff002c000073000200020a1f190c02010400021f40010b0012000002290000000000310000000000000000000a0104000b0000000c00000001"
    manual_anc = "ffff002c0000dd0002000209153b0402010400021f40010b0012000002290000000000310000000000000000000b0104000b0000000c00000001"
    #manual_anc = "ffff002200001b000100020c0d0e0f010101000e0100010000029a0fa007d00100011e"
    #print ("** Manually entered ANC:", manual_anc)

    #make_fake_phabrix_anc_data(probel_string)
    #raw_anc = ['1023', '1023', '577', '263', '557', '264', '767', '767', '512', '300', '512', '512', '731', '512', '512', '512', '258', '275', '518', '20', '524', '277', '258', '257', '260', '512', '258', '287', '320', '257', '267', '512', '530', '512', '512', '512', '512', '512', '512', '572', '40', '527', '512', '272', '512', '512', '512', '512', '512', '512', '512', '512', '415', '0', '0', '0', '0', '0', '0', '0', '0']
    #print("** raw anc:", fake_anc_decode(raw_anc))
    decode_SCTE104(manual_anc)
    '''
    data = morpheus_preprocessor(probel_string)
    print("** Probel: ", data)
    
    decode_SCTE104(data)
    '''

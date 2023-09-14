from ctypes import cdll, c_int, c_char_p, c_uint, c_ulonglong, create_string_buffer, pointer
import sys
from time import sleep
import logging
import datetime
from datetime import timezone
from pathlib import Path


from SCTE_104_Tools import decode_SCTE104, decode_SCTE104_to_output
from PhabrixTools import phabrix_preprocessor
from MorpheusTools import morpheus_preprocessor, log_filtered_kerneldiag_logs, filter_kernel_diags_on_device_and_keyword, make_fake_phabrix_anc_data
from FFMPEGTools import ffprobe, parse_ffprobe_output, ffmpeg

log = logging.getLogger(__name__)

###########
IP = b'10.240.36.70'
PORT = 2100

MSG_PRESS_KEY = 4
MSG_SET_VALUE = 5
MSG_GET_VALUE = 21
MSG_GET_TEXT = 20
MSG_GET_ITEM_TEXT = 25
MSG_SET_TEXT = 6
MSG_GET_ITEM_STRINGS = 29
MSG_GET_ITEM_VALUES = 28

COM_ANLYS_ANC_DATA = 603
COM_ANLYS_2_ANC_DATA = 8004
COM_ANLYS_3_ANC_DATA = 8104
###########

PADDING = 1

def get_anc_data():
    mydll = cdll.LoadLibrary('./PhabrixRemoteDllSid64.dll')
    StString = ""
    RtString = create_string_buffer(500)
    RetVal = c_int()

    '''
    int SendStatus = PhSendMsg(IpAd, PortNum, MSG_GET_ITEM_VALUES, COM_ANLYS_ANC_DATA, 0, 0, SendText, ReturnText, ref RetValue, 500); // Get the ANC data using MSG_GET_ITEM_VALUES on COM_ANLYS_ANC_DATA
    '''
    Status = mydll.PhSendMsg(c_char_p(IP), 
                             c_uint(PORT), 
                             c_uint(MSG_GET_ITEM_VALUES), 
                             c_uint(COM_ANLYS_ANC_DATA), 
                             c_int(0), c_int(0), 
                             StString, 
                             RtString, 
                             pointer(RetVal), 
                             500)
    print("\n")
      
    anc_data = RtString.value.decode('utf-8').split('\t')
    #print("Raw ANC data:", anc_data)

    if (Status == 0):
        print("Bad ip address or port number\n")
        return

    if (Status == -5):
        print("Remote control disabled\n")
        return

    return anc_data


def DecodeANC(oneshot):
    dateTag = datetime.datetime.now().strftime("%Y-%b-%d_%H-%M-%S")
    #logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.basicConfig(filename='scte.log_%s' % dateTag, encoding='utf-8', format='%(message)s', level=logging.INFO)

    if oneshot == True:
        anc_data = get_anc_data()
        data = phabrix_preprocessor(anc_data)
        decode_SCTE104_to_output(data)
    else:
        try:
            tmp_line = ""
            while(1):    
                anc_data = get_anc_data()
                # phabrix preprocessor is a function to combine all necessary data processing steps to get to the relevant anc data for our purposes
                data = phabrix_preprocessor(anc_data)
                                    
                timestamp = datetime.datetime.now(timezone.utc)

                if data != tmp_line:
                    print("@", timestamp)
                    print("Newly fetched:", data)
                    
                    decode_SCTE104_to_output(data)
                    
                    tmp_line = data
                else:
                    print("@", timestamp, "Same data. Omitted.")

                sleep(1)

        except KeyboardInterrupt:
            #traceback.print_exc()
            print("Shutting down loop..") 


def fake_anc_decode(anc_data):
    return phabrix_preprocessor(anc_data)

def TestStringDecode(probel_string):
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

def TestOldApi():
    print ("Testing Old Api")
    mydll = cdll.LoadLibrary('./PhabrixRemoteDllSid64.dll')

    StString = ""
    RtString = create_string_buffer(500)
    
    Conn = mydll.OpenConnection(c_char_p(IP), c_uint(PORT))
    print (Conn)

    print ("Getting the HDMI bitmap")

	#	const int HDMI_LCD = 2;
        #       const int LH_LCD = 1;
        #       const int RH_LCD = 0;
	# SX/TAG LCD = 0
    WHICH_LCD = 0

    BMP = b"hdmi.bmp"

#	Status = mydll.GetLCD(Conn, c_uint(2), c_char_p(BMP))
    Status = mydll.GetLCD(Conn, c_uint(WHICH_LCD), c_char_p(BMP))
        
    print ("Got the HDMI bitmap")

    mydll.CloseConnection(Conn)
    
    mydll.CloseConnection.argtypes = [c_ulonglong]

    mydll.CloseConnection(Conn)

def DecodeMXF(filename):
    if not Path(filename).is_file():
        print("Could not read file: " + filename)
        exit(1)
    ffprobe_result = ffprobe(filename)
    frame_number_list = []
    if ffprobe_result.return_code == 0:
        ffprobe_output = parse_ffprobe_output(ffprobe_result.json)
        for scte104_packet in ffprobe_output:
            # strip:
            # DID Data Identifier
            # SDID Secondary Data Identifier
            # DBN Data Block Number
            # DC Data Count
            # from the packet as the next decoding step expects only the UDW
            result = decode_SCTE104(scte104_packet.anc_data[8:])
            frame_number_list.append(scte104_packet.pts_frame_number)
            print ('@frame_number: {} file timestamp: {} - utc timestamp: {} - broadcast timestamp: {}'.format(scte104_packet.pts_frame_number, scte104_packet.pts_time, scte104_packet.utc_time, result.get_splice_event_timestamp()))
            print(result)
        print("Extracting frame thumbnails..")
        ffmpeg_result = ffmpeg(filename, frame_number_list, PADDING)
    else:
        print("ERROR while reading {}".format(filename))
        print(ffprobe_result.error, file=sys.stderr)
        print(ffmpeg_result.error, file=sys.stderr)

if __name__ == "__main__":    
    #DecodeANC(oneshot=False)
    #decode_SCTE104("ffff002c0000dc0002000209142c0402010400021f40010b0012000002290000f00000300000000000000000000b0104000b0000000c00000001")
    DecodeMXF("SCTE_36.mxf")
    
    

    #TestOldApi()
    #probel_string = "0xff [0] 0xff [1] 0x0 [2] 0x2c [3] 0x0 [4] 0x0 [5] 0xb2 [6] 0x0 [7] 0x2 [8] 0x0 [9] 0x2 [10] 0xd [11] 0x8 [12] 0x20 [13] 0x17 [14] 0x2 [15] 0x1 [16] 0x4 [17] 0x0 [18] 0x2 [19] 0x1f [20] 0x40 [21] 0x1 [22] 0xb [23] 0x0 [24] 0x12 [25] 0x0 [26] 0x0 [27] 0x0 [28] 0x0 [29] 0x0 [30] 0x0 [31] 0x2d [32] 0xf [33] 0x0 [34] 0x30 [35] 0x0 [36] 0x0 [37] 0x4 [38] 0x0 [39] 0x0 [40] 0x0 [41] 0x0 [42] 0x0 [43]"
    #TestStringDecode(probel_string)
    #TestStringDecode("")
    
    '''
    FILE = "KernelDiags.log"
    DEVICE = "SCTE104_AdsProtocol"
    KEYWORD = "SendData"
    log_filtered_kerneldiag_logs(filter_kernel_diags_on_device_and_keyword(file = FILE, device = DEVICE, keyword = KEYWORD), ignore_keep_alive=True)
    '''

    '''
    strings waarop ik crash:
    ffff002e0000bd0002000100005e82017702010400021f40010b00120000000000002d0f0030000004000000
    
    zie raw hex phabrix voorbeeld.png
    raw hex data = 000 3ff 3ff 241 107 22d 108 2ff 2ff 200 12c 200 200 24e 200 102 200 102 10d 120 217 102 102 101 104 200 102 11f 140 101 10b 200 212 200 200 102 129 200 200 200 200 200 131 200 200 200 200 200 200 200 200 121 (121=checksum?)
    ffff002c00004e000200020d04170202010400021f40010b0012000002290000080000310000000000
    deze werkt wel: (6 '0' langer)
    ffff002c00004e000200020d04170202010400021f40010b0012000002290000080000310000000000000000
    
    deze werkt wel:
    ffff002e0000bd0002000100005e82017702010400021f40010b00120000000000002d0f00300000040000000000

    ffff002e00006e000200010000ad02009602010400021f40010b00120000000000002d0f0030000004000000
    ffff002e000070000200010000ad2a009602010400021f40010b0012000000000000000f0031000000000000
    ffff002e0000e30002000100006e5800e102010400021f40010b0012000000000000000f0031000000000000
    '''
    

    
    

import logging
import datetime
from datetime import timezone
from time import sleep

from Tools.PhabrixTools import get_anc_data, phabrix_preprocessor
from Tools.SCTE_104_Tools import decode_SCTE104_to_output

'''
These are values that need to be sent to the Phabrix.
The majority of these values can be derived from the documentation that is provided in the SDK (don't expect much, the docs are pretty horrible)

IP can be configured through the front panel and is ofcourse VRT-specific

The most important value is the correct SDK command, in this case COM_ANLYS_ANC_DATA

Again; the docs are pretty horrible but the commands could be reverse engineered from the supplied examples in various coding languages. The C++ and .NET example was the most helpful.
'''
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

COM_ANLYS_LOG_VIEW = 400
COM_ANLYS_ANC_DATA = 603
COM_ANLYS_INP1_STD  = 560
COM_ANLYS_2_ANC_DATA = 8004
COM_ANLYS_3_ANC_DATA = 8104
###########

log = logging.getLogger(__name__)

'''
The oneshot boolean value can be used if you want to measure one specific trigger and is usually only useful in test environments. In real-life, the heartbeat message every 30sec will interrupt measures.
The oneshot value is very helpful if you put the Phabrix into "freeze on trigger"-mode. (don't forget to reset the freeze option after measurement or you will read the same one over and over again.
'''
def DecodeANC(oneshot):
    dateTag = datetime.datetime.now().strftime("%Y-%b-%d_%H-%M-%S")
    #logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.basicConfig(filename='scte.log_%s' % dateTag, encoding='utf-8', format='%(message)s', level=logging.INFO)

    if oneshot == True:
        anc_data = get_anc_data(IP, PORT, MSG_GET_ITEM_VALUES, COM_ANLYS_ANC_DATA)
        data = phabrix_preprocessor(anc_data)
        decode_SCTE104_to_output(data)
    else:
        try:
            '''
            It's a bit annoying to use this method as the SDK is designed to constantly 
            print out connection messages to terminal output so we need some working around
            this fact by ignoring some of the messages.
            The other SDK version can be used to circumvent this, but I never got the 
            correct SDK message. It's supposed to be COM_ANLYS_2_ANC_DATA etc.
            '''
            tmp_line = ""
            while(1):    
                anc_data = get_anc_data(IP, PORT, MSG_GET_ITEM_VALUES, COM_ANLYS_ANC_DATA)
                # phabrix preprocessor is a function to combine all necessary data
                # processing steps to get to the relevant anc data for our purposes
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

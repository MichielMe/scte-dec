
# Python script to test Phabrix Remote Api DLL (PhabrixRemoteDllSid.dll) for RX and SX line products

from ctypes import *
import time
from ftplib import FTP


#        MSG_SET_VALUE=5,
#        MSG_SET_TEXT=6,
#        MSG_SET_ENABLE=7,
#        MSG_SET_VISIBLE=8,
#        MSG_SET_COLOUR=9,
#        MSG_SET_ITEM_TEXT=12,
#        MSG_SET_ITEM_VALUE=13,
#        MSG_SET_ITEM_TEXT_VALUE=14,
#        MSG_SET_ITEM_ENABLED=15,
#        MSG_SET_ITEM_VALUES=16,
#        MSG_SET_ITEM_STRINGS=17,
#        
#         * 
#         * 
#         * 
#        MSG_GET_TEXT=20,
#        MSG_GET_VALUE=21,
#        MSG_GET_COLOUR=22,
#        MSG_GET_ITEM_COUNT=23,
#        MSG_GET_ITEM_VALUE=24,
#        MSG_GET_ITEM_TEXT=25,
#        MSG_GET_ITEM_TEXT_VALUE=26,
#        MSG_GET_ITEM_ENABLED=27,
#        MSG_GET_ITEM_VALUES=28,
#        MSG_GET_ITEM_STRING=29.
#        MSG_GET_LCD = 56; // on rx2000, ItemIndex = 0 for left hand tft, 1 = right hand tft, 2 = hdmi, SX/TAG LCD=0
		
		
IP = b'10.240.36.70'
PORT = 2100

MSG_SET_VALUE = 5
MSG_GET_VALUE = 21
MSG_GET_TEXT = 20
MSG_SET_TEXT = 6
MSG_GET_ITEM_STRINGS = 29
MSG_GET_ITEM_VALUES = 28
MSG_GET_LCD = 56

COM_GEN1_MOVING_BOX = 16
COM_STATUS_ALL_PIXELS_A = 682
COM_SLOT_1_INFO_1 = 2713
FILTER_LOG_TEXT = 10882
COM_ANLYS_LINE = 575
COM_ANLYS_LOG_VIEW = 400

COM_ANLYS_FRAME_CAPT_PLAY_STOP_BTN	= 9794
COM_ANLYS_FRAME_CAPT_REC_BTN	    = 9791
COM_ANLYS_FRAME_CAPT_MAN_TRIG_BTN	= 9793
COM_ANLYS_FRAME_CAPT_FRM_MODE_BTN	= 9830
COM_ANLYS_FRAME_CAPT_PLAY_FWD_BTN	= 9795
COM_ANLYS_FRM_POSITION_DISPLAY      = 10230
COM_ANLYS_FRM_SAVE_BOX	= 9987
COM_ANLYS_FRM_SAVE_SINGLE = 10215

COM_ANLYS_FRM_SAVE_BTN	= 9979

COM_ANLYS_PIC_GRAB_SETUP = 10120

def TriggerAndSaveSingleGrab():
	print ("Trigger and Get Grab Demo Started")

	# Note a 0 to 1 transition is a button press!
	
	
	mydll = cdll.LoadLibrary('./PhabrixRemoteDllSid64.dll')

	Conn = mydll.OpenConnection(c_char_p(IP), c_uint(PORT))

	print ("Step 1 - Show grab buttons on picture dialog")

	
	Val = c_int()
	
	
	Val.value = 0 
	
	Status = mydll.GetValue(Conn, c_uint(COM_ANLYS_FRAME_CAPT_FRM_MODE_BTN), pointer( Val))

	if (Val.value == 0):
		Val.value = 1 
		Status = mydll.SetValue(Conn, c_uint(COM_ANLYS_FRAME_CAPT_FRM_MODE_BTN), pointer( Val))
	
	
	
	print ("Step 2 - Ensure any current recording is stopped-Press grab stop button!")

	Val.value = 0 
	Status = mydll.SetValue(Conn, c_uint(COM_ANLYS_FRAME_CAPT_PLAY_STOP_BTN), pointer( Val))

	Val.value = 1 
	Status = mydll.SetValue(Conn, c_uint(COM_ANLYS_FRAME_CAPT_PLAY_STOP_BTN), pointer( Val))
	
	
	print ("Step 3 - Start recording is stopped-Press grab record button!")

	Val.value = 0 
	Status = mydll.SetValue(Conn, c_uint(COM_ANLYS_FRAME_CAPT_REC_BTN), pointer( Val))
	

	Val.value = 1 
	Status = mydll.SetValue(Conn, c_uint(COM_ANLYS_FRAME_CAPT_REC_BTN), pointer( Val))

	
	
	print ("Step 4 - Get record status for filled buffer i.e. changed from BUFFERING to RECORDING")
	
	StString = create_string_buffer(50)

	while (1):
		Status = mydll.GetText(Conn, c_uint(COM_ANLYS_FRM_POSITION_DISPLAY), StString, 50)
	
		RecordStatus = str(StString.value.decode('utf-8'))

		print ("Grab status: " + RecordStatus)
		if RecordStatus == "RECORDING":
			break
			
			
	print ("Step 5 - Hit the Grab trigger button")
	
	Val.value = 0 
	Status = mydll.SetValue(Conn, c_uint(COM_ANLYS_FRAME_CAPT_MAN_TRIG_BTN), pointer( Val))
	

	Val.value = 1 
	Status = mydll.SetValue(Conn, c_uint(COM_ANLYS_FRAME_CAPT_MAN_TRIG_BTN), pointer( Val))


#	Val.value = 1 
#	Status = mydll.SetValue(Conn, c_uint(COM_ANLYS_PIC_GRAB_SETUP), pointer( Val))



	
	
	print ("Step 6 - Hit the single frame button on the Grab settings box")
	
	Val.value = 0 
	
	Status = mydll.GetValue(Conn, c_uint(COM_ANLYS_FRM_SAVE_SINGLE), pointer( Val))

	if (Val.value == 0):
		Val.value = 1 
		Status = mydll.SetValue(Conn, c_uint(COM_ANLYS_FRM_SAVE_SINGLE), pointer( Val))
	


	GrabFileString = create_string_buffer(50)
	
	GrabName = "DemoGrabFile"
	
#	GrabFileString.value = b"GrabTestFile1"

	GrabFileString = GrabName.encode('utf-8')

	Status = mydll.SetText(Conn, c_uint(COM_ANLYS_FRM_SAVE_BOX), GrabFileString, 50)
	

	print ("Step 7 - Hit the save grab button on the Grab settings box")



	
	
	Val.value = 0 
	Status = mydll.SetValue(Conn, c_uint(COM_ANLYS_FRM_SAVE_BTN), pointer( Val))
	
	Val.value = 1 
	Status = mydll.SetValue(Conn, c_uint(COM_ANLYS_FRM_SAVE_BTN), pointer( Val))
	
	mydll.CloseConnection(Conn)


	return




def Trig():
	print ("Trigger and Get Grab Demo Started")

	# Note a 0 to 1 transition is a button press!
	
	
	mydll = cdll.LoadLibrary('./PhabrixRemoteDllSid64.dll')

	#mydll.CloseConnection(Conn)





TriggerAndSaveSingleGrab()
Trig()


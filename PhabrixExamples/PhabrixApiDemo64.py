
# Python script to test Phabrix Remote Api DLL (PhabrixRemoteDllSid.dll) for RX and SX line products


import ctypes
from ctypes import *

import traceback

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
#        MSG_GET_ITEM_STRING=29. // Tab seperated string
#        MSG_GET_LCD = 56; // on rx2000, ItemIndex = 0 for left hand tft, 1 = right hand tft, 2 = hdmi, SX/TAG LCD=0
		
		
IP = b'10.240.36.70' # # NOTE:- please change this IP address to match the IP address of your SX, TAG or RX!
PORT = 2100

MSG_SET_VALUE = 5
MSG_GET_VALUE = 21
MSG_GET_TEXT = 20
MSG_SET_TEXT = 6
MSG_GET_ITEM_STRINGS = 29
MSG_GET_ITEM_VALUES = 28
MSG_GET_LCD = 56




COM_GEN1_MOVING_BOX = 16

COM_GEN1_LINK_TYPE = 36

COM_STATUS_ALL_PIXELS_A = 682
COM_SLOT_1_INFO_1 = 2713
COM_ANLYS_INP1_STD  = 560
FILTER_LOG_TEXT = 10882
COM_ANLYS_LINE = 575
COM_ANLYS_LOG_VIEW = 400
COM_GEN1_IDENT_INFO = 812

COM_ANLYS_ANC_DATA = 603


def TestOldApi():
	print ("Testing Old Api")
	mydll = cdll.LoadLibrary('./PhabrixRemoteDllSid64.dll')


	Conn = mydll.OpenConnection
	Conn.restype = c_ulonglong


	Conn = mydll.OpenConnection(c_char_p(IP), c_uint(PORT))

	StString = ""
	RtString = create_string_buffer(500)
	RetVal = c_int()

	Status = mydll.PhSendMsg(c_char_p(IP), c_uint(PORT), c_uint(MSG_GET_ITEM_VALUES), c_uint(COM_ANLYS_ANC_DATA), c_int(0), c_int(0), StString, RtString, pointer(RetVal), 500)
	print("\n")

	'''	


		
	print ("Turn on Bouncing Box")

	
	Val = c_int()
	Val.value = 1 # turn on bouncing box


	mydll.SetValue.argtypes = [c_ulonglong]
	
	Status = mydll.SetValue(Conn, c_uint(COM_GEN1_MOVING_BOX), pointer( Val))


	if (Status!=0):
		print("Error:Bad IP address or port-Exiting\n")
		return

	
	print ("Done-Turn on Bouncing Box")

	# Note:- status
	# 0 is good
	# 1 is bad
	
	print ('Return status is:' + str(Status))
	
	print ("Get all pixels value")



	mydll.GetValue.argtypes = [c_ulonglong]


	Status = mydll.GetValue(Conn, c_uint(COM_STATUS_ALL_PIXELS_A), pointer( Val))
	
	print ("All pixels value is:" + str (Val.value) )

	print ("Get input 1 status")
	
#	StString = create_string_buffer(50)

#	Status = mydll.GetText(Conn, c_uint(COM_SLOT_1_INFO_1), StString, 50)
	
#	print ("Input 1 status: " + str(StString.value.decode('utf-8')))


	StString = create_string_buffer(50)


	mydll.GetText.argtypes = [c_ulonglong]

	Status = mydll.GetText(Conn, c_uint(COM_ANLYS_INP1_STD), StString, 50)
	
	print ("Input 1 status: " + str(StString.value.decode('utf-8')))



	print ("Get Count of items in the generator LINK TYPE dropdown")


	mydll.GetItemCount.argtypes = [c_ulonglong]


	Status = mydll.GetItemCount(Conn, c_uint(COM_GEN1_LINK_TYPE), pointer( Val))
	
	print ("Number of Generaror LINK TYPES is:" + str (Val.value) )



	print ("Get Generator Link Type - What is Item 3 in the dropdown list")

	StString = create_string_buffer(500)

	WhichItem = 2 # Note: zero based index , first item index is 0, third item index is 2 etc


	mydll.GetItemText.argtypes = [c_ulonglong]


	Status = mydll.GetItemText(Conn, c_uint(COM_GEN1_LINK_TYPE), StString, 500, WhichItem)
	
	print ("Generator Link Type Item 3 in the dropdown: " + str(StString.value.decode('utf-8')))



	print ("Get Count of Log Entries")

	mydll.GetItemCount.argtypes = [c_ulonglong]


	Status = mydll.GetItemCount(Conn, c_uint(COM_ANLYS_LOG_VIEW), pointer( Val))
	
	print ("Number of Log Entries is:" + str (Val.value) )


	print ("Get Log Entry Number 3")

	StString = create_string_buffer(500)

	WhichItem = 2 # Note: zero based index 


	mydll.GetItemText.argtypes = [c_ulonglong]


	Status = mydll.GetItemText(Conn, c_uint(COM_ANLYS_LOG_VIEW), StString, 500, WhichItem)
	
	print ("Log Entry 3: " + str(StString.value.decode('utf-8')))



	
#	print ("Setting event filter text to: Phabrix")
#	
#	FILT_TEXT = b"Phabrix"
#	
#	Status = mydll.SetText(Conn, c_uint(FILTER_LOG_TEXT),c_char_p(FILT_TEXT))
	
	print ("Setting generator Ident text to: Phabrix")
	
	IDENT_TEXT = b"Phabrix"

	mydll.SetText.argtypes = [c_ulonglong]


	
	Status = mydll.SetText(Conn, c_uint(COM_GEN1_IDENT_INFO),c_char_p(IDENT_TEXT))







	# Get cursor line number
#	Status = mydll.PhSendMsg(c_char_p(IP), c_uint(PORT), c_uint(MSG_GET_VALUE), c_uint(COM_ANLYS_LINE),c_int (0), c_int(0), c_char_p(b''), c_char_p(b''), pointer (RetVal), 0)
	
#	print ('Cursor line number:' + str (RetVal.value))
	
#	print ("Get input 1 status")
	
	# Get input 1 status
#	StString = create_string_buffer(50)
	
#	Status = mydll.PhSendMsg(c_char_p(IP), c_uint(PORT), c_uint(MSG_GET_TEXT), c_uint(COM_SLOT_1_INFO_1),c_int (0), c_int(0), c_char_p(b''), StString, pointer (RetVal), 50)
	
#	print ("Input 1 status: " + str(StString.value.decode('utf-8')))

	
	print ("Getting the HDMI bitmap")

	#	const int HDMI_LCD = 2;
        #       const int LH_LCD = 1;
        #       const int RH_LCD = 0;
	# SX/TAG LCD = 0
	WHICH_LCD = 2

	BMP = b".\\hdmi.bmp"


	mydll.GetLCD.argtypes = [c_ulonglong]


#	Status = mydll.GetLCD(Conn, c_uint(2), c_char_p(BMP))
	Status = mydll.GetLCD(Conn, c_uint(WHICH_LCD), c_char_p(BMP))
        
	print ("Got the HDMI bitmap")
	'''
	mydll.CloseConnection.argtypes = [c_ulonglong]

	mydll.CloseConnection(Conn)
	print ("Closed connection..")



TestOldApi()

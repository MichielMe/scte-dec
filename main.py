from PhabrixDecoder import DecodeANC
from MXFDecoder import DecodeMXF
from TelenetTools import read_telenet_log

if __name__ == "__main__":    
    #DecodeANC(oneshot=False)
    #read_telenet_log("VRT_testloop markers_271123.xls.xlsx")
    DecodeMXF("MXFInputfiles/SCTE_56.mxf")
    

    

    

    
    

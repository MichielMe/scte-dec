import sys
from pathlib import Path
from Tools.FFMPEGTools import ffprobe, parse_ffprobe_output, ffmpeg_extract_thumbnails, FFMPEGFrameData
from Tools.SCTE_104_Tools import decode_SCTE104, SCTE104Packet
import operator


PADDING = 3

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
            if result.as_dict["timestamp"]["time_type"] == 0:
                # add scte transition frame, no timestamp adjustment due to immediate trigger not containing timestamp information
                frame_number_list.append(FFMPEGFrameData(scte104_packet.pts_frame_number, "injection", None))
                print ('@frame_number: {} - file timestamp: {} - utc timestamp: {}'.format(scte104_packet.pts_frame_number, scte104_packet.pts_time, scte104_packet.utc_time))
            if result.as_dict["timestamp"]["time_type"] == 2:
                # add announcement frame - on this frame we announced an incoming trigger
                frame_number_list.append(FFMPEGFrameData(scte104_packet.pts_frame_number, "injection", None))
                # the morpheus driver took this margin to announce the scte packet
                driver_margin = result.get_splice_event_timestamp() - scte104_packet.utc_time
                # calculate actual transition frame number
                transition_frame = scte104_packet.pts_frame_number + driver_margin.frames
                # add scte transition frame, the actual transition frame
                frame_number_list.append(FFMPEGFrameData(transition_frame, "scte", SCTE104Packet))
                print('\n@frame_number: {}/(marker found at file timestamp: {}) '.format(scte104_packet.pts_frame_number, scte104_packet.pts_time))
                print('|_> marker injection timestamp (utc): {}'.format(scte104_packet.utc_time))
                print('|_> @frame_number: {}/(marker start/end splice event (=timestamp+preroll (utc)): {}'.format(transition_frame, result.get_splice_event_timestamp()))
                packet = SCTE104Packet(result.get_splice_event_timestamp(), result.get_pre_roll_time(), result.get_segmentation_upid(), result.get_segmentation_type_id())
                print(packet)
                print(result)
                
        # output the frame thumbnails to folder named like inputfile
        outputfolder = Path('results')
        outputfolder = outputfolder / (Path(filename).stem)
        outputfolder.mkdir(parents=True, exist_ok=True)

        frame_number_list = sorted(frame_number_list, key=operator.attrgetter("frame_number"))
        
        print("Extracting frame thumbnails..")
        ffmpeg_result = ffmpeg_extract_thumbnails(filename, frame_number_list, PADDING, outputfolder)
        if (ffmpeg_result.return_code != 0):
            print(ffmpeg_result.error, file=sys.stderr)
    else:
        print("ERROR while reading {}".format(filename))
        print(ffprobe_result.error, file=sys.stderr)
        
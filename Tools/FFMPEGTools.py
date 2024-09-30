import os
import subprocess
import json
import datetime
from math import modf
from string import Template
from timecode import Timecode
from typing import NamedTuple
from Tools.SCTE_104_Tools import SCTE104Packet

DID_SDID = ["4105", "4107", "4108"]
DID_SDID_TO_EXTRACT = "4107"
FRAME_RATE = 25
FRAME_DURATION = 40 #milliseconds

class FFMPEGResult(NamedTuple):
    return_code: int
    args: str
    error: str

class FFProbeResult(NamedTuple):
    return_code: int
    json: str
    error: str

class Packet(NamedTuple):
    anc_data: list
    pts_time: Timecode
    utc_time: Timecode
    pts_frame_number: int

class FFMPEGFrameData(NamedTuple):
    frame_number: int
    marker_type: str
    frame_text_data: SCTE104Packet

def extract_frame_numbers(frame_data: list[FFMPEGFrameData]) -> list[int]:
    frame_number_list = []
    for frame in frame_data:
        frame_number_list.append(frame.frame_number)
    return frame_number_list

def ffmpeg_extract_thumbnails(video_filename: str, frames: list[FFMPEGFrameData], padding: int=0, folder: str="") -> FFMPEGResult:
    for frame in frames:
        print(frame.frame_number, frame.marker_type)
    frame_numbers = extract_frame_numbers(frames)
    orig_frame_numbers = frame_numbers
    print("Frame nrs:", frame_numbers)
    '''
    if padding is needed, overwrite the frame_numbers list with a new list to add each frame number plus/minus the padding size
    e.g. frame_numbers [5, 177] with padding size 3 will become: [2, 3, 4, 5, 6, 7, 8, 174, 175, 176, 177, 178, 179, 180]
    X = len(frame_numbers), Y=(PADDING*2)+1 = ((PADDING * 2 ) + 1) * len(frame_numbers) = TOTAL FRAMES
    
    FRAMES | PADDING | TOTAL FRAMES
    0           0           0
    1           0           1
    2           0           2
    1           1           3
    2           1           6
    3           1           9
    3           2           15
    3           3           21
    3           5           = ((5 * 2) + 1) * 3 = 33
    '''
    if padding > 0:
        frame_numbers = [frame for frame_number in frame_numbers for frame in range(frame_number - padding, frame_number + padding + 1, 1) ]
    
    # build the select string and skip the plus at the end
    frame_number_selectstring = "\'"
    n_frames = len(frame_numbers)
    for idx, frame_number in enumerate(frame_numbers, start=1):
        frame_number_selectstring += ('eq(n,' + str(frame_number) + ')')
        if idx < n_frames:
            frame_number_selectstring += '+'
    frame_number_selectstring += "\'"

    # build draw text command
    # drawtext=text='Frame 30':x=(w-tw)/2:y=(h-th)/2:fontsize=24:fontcolor=white:enable='eq(n,0)', 
    # drawtext=text='Frame 43':x=(w-tw)/2:y=(h-th)/2:fontsize=24:fontcolor=white:enable='eq(n,1)

    # ffmpeg -i SCTE_5.mxf -vf "select='eq(n\,29)+eq(n\,42)', drawtext=text='Frame 30':x=(w-tw)/2:y=(h-th)/2:fontsize=24:fontcolor=white:enable='eq(n,0)', 
    # drawtext=text='Frame 43':x=(w-tw)/2:y=(h-th)/2:fontsize=24:fontcolor=white:enable='eq(n,1)'" -vsync 0 -vframes 2 -q:v 2 %03d.jpg
    draw_text_command = ""
    
    for idx, frame in enumerate(frame_numbers, start=0):
        if frame in orig_frame_numbers:          
            text = "Frame_number " + str(frames[orig_frame_numbers.index(frame)].frame_number) + " Frame type " + frames[orig_frame_numbers.index(frame)].marker_type
            print(idx, frame, text)
            
        else:
            text = "PADDING FRAME"
            print(idx, frame, text)
        
        cmd = ("drawtext=text=\'", text, "\'", \
               ":x=(w-tw)/2:y=(h-th)/2:fontsize=24:fontcolor=yellow:boxborderw=10:borderw=1:enable=\'eq(n,", \
               str(idx), \
               ")\'"
        )
        draw_text_command += "".join(cmd)
        if idx < n_frames-1:
            draw_text_command += ","
        #print(draw_text_command)
    #draw_text_command += "\'"
        
    #print("draw txt cmd:", draw_text_command)
    #print("Frame nrs with padding:", frame_numbers)
    outputpath = os.path.join(folder, "frames%d.jpg")

    '''
    ffmpeg -i SCTE_5.mxf -vf "select='eq(n\,29)+eq(n\,42)', 
    drawtext=text='Frame 30':x=(w-tw)/2:y=(h-th)/2:fontsize=24:fontcolor=white:enable='eq(n,0)', 
    drawtext=text='Frame 43':x=(w-tw)/2:y=(h-th)/2:fontsize=24:fontcolor=white:enable='eq(n,1)'" 
    -vsync 0 -vframes 2 %03d.jpg
    '''

    # write each supplied frame number to a jpeg thumbnail  
    commands = []
    commands.append("ffmpeg")
    # -i = input file
    commands.extend(("-i", video_filename))
    # -vf filtergraph (output)
    # Create the filtergraph specified by filtergraph and use it to filter the stream. 
    # select only the frame(s) we supply
    #commands.extend(("-vf", "select=" + frame_number_selectstring))
    filter_cmd = "".join([frame_number_selectstring, ",", draw_text_command])
    #filter_cmd = frame_number_selectstring
    commands.extend(("-vf", "select=" + filter_cmd))
    # -vsync 0 was previously used, but is deprecated
    commands.extend(("-fps_mode", "passthrough"))
    # stop processing after we outputted our requested frames, this speeds up the process considerably
    commands.extend(("-frames", str(len(frame_numbers))))
    # write output
    commands.append(outputpath)

    
    print(commands)

    
    # -vf "drawtext=text='%{gmtime}.%{eif\:mod(n, 30)\:d\:02d}': fontsize=40: fontcolor=white: x=10: y=10: box=1: boxborderw=10: boxcolor=black,fps=30"
    
    result = subprocess.run(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return FFMPEGResult(return_code=result.returncode,
                        args=result.args, 
                        error=result.stderr)

'''
FFProbe example data
{
    "packets": [
        {
            "codec_type": "data",
            "stream_index": 2,
            "pts": 0,
            "pts_time": "0.000000",
            "dts": 0,
            "dts_time": "0.000000",
            "duration": 1,
            "duration_time": "0.040000",
            "size": "450",
            "pos": "15087",
            "flags": "K_",
            "data": "\n00000000: 0008 000b 0104 000b 0000 000c 0000 0001  ................\n00000010: 4105 0844 0000 0000 0000 0000 000d 0104  A..D............\n00000020: 0032 0000 0034 0000 0001 4108 2f10 022c  .2...4....A./..,\n00000030: e7e4 0b57 261c e3e3 e3e3 e3e3 5049 4949  ...W&.......PIII\n00000040: 4949 4949 4949 4949 4949 49c9 c9c9 c9c9  IIIIIIIIIII.....\n00000050: c9c9 c9c9 c9c9 c9c9 c9c9 4423 0000 000d  ..........D#....\n00000060: 0104 0032 0000 0034 0000 0001 4108 2f10  ...2...4....A./.\n00000070: 022c e8e4 0b57 261c e3e3 e3e3 e3e3 d0c9  .,...W&.........\n00000080: 2929 2929 2929 2929 2929 2929 2929 2929  ))))))))))))))))\n00000090: a9a9 a9a9 a9a9 a9a9 a9a9 a9a9 7f7f 0000  ................\n000000a0: 000d 0104 0032 0000 0034 0000 0001 4108  .....2...4....A.\n000000b0: 2f10 022c e9e4 0b57 261c e3e3 e3e3 e3e3  /..,...W&.......\n000000c0: 30a9 a9a9 a969 6969 6969 6969 6969 6969  0....iiiiiiiiiii\n000000d0: 6969 6969 69e9 e9e9 e9e9 e9e9 e9e9 e50c  iiiii...........\n000000e0: 0000 023e 0104 000b 0000 000c 0000 0001  ...>............\n000000f0: 4105 0844 0000 0000 0000 0000 0240 0104  A..D.........@..\n00000100: 0032 0000 0034 0000 0001 4108 2f10 022c  .2...4....A./..,\n00000110: c9e4 0b57 261c e3e3 e3e3 e3e3 b0e9 e9e9  ...W&...........\n00000120: e9e9 e9e9 1919 1919 1919 1919 1919 1919  ................\n00000130: 1919 1919 9999 9999 9999 1a6a 0000 0240  ...........j...@\n00000140: 0104 0032 0000 0034 0000 0001 4108 2f10  ...2...4....A./.\n00000150: 022c cae4 0b57 261c e3e3 e3e3 e3e3 7099  .,...W&.......p.\n00000160: 9999 9999 9999 9999 9959 5959 5959 5959  .........YYYYYYY\n00000170: 5959 5959 5959 5959 59d9 d9d9 7d7f 0000  YYYYYYYYY...}...\n00000180: 0240 0104 0032 0000 0034 0000 0001 4108  .@...2...4....A.\n00000190: 2f10 022c cbe4 0b57 261c e3e3 e3e3 e3e3  /..,...W&.......\n000001a0: f0d9 d9d9 d9d9 d9d9 d9d9 d9d9 d9d9 3939  ..............99\n000001b0: 3939 3939 3939 3939 3939 3939 3939 74c5  99999999999999t.\n000001c0: 0000                                     ..\n"
        },
        {
            "codec_type": "data",
            "stream_index": 2,
            "pts": 1,
            "pts_time": "0.040000",
            "dts": 1,
            "dts_time": "0.040000",
            "duration": 1,
            "duration_time": "0.040000",
            "size": "450",
            "pos": "631119",
            "flags": "K_",
            "data": "\n00000000: 0008 000b 0104 000b 0000 000c 0000 0001  ................\n00000010: 4105 0844 0000 0000 0000 0000 000d 0104  A..D............\n00000020: 0032 0000 0034 0000 0001 4108 2f10 022c  .2...4....A./..,\n00000030: e7e4 0b57 261c e3e3 e3e3 e3e3 08b9 b9b9  ...W&...........\n00000040: b9b9 b9b9 b9b9 b9b9 b9b9 b9b9 b979 7979  .............yyy\n00000050: 7979 7979 7979 7979 7979 7165 0000 000d  yyyyyyyyyyqe....\n00000060: 0104 0032 0000 0034 0000 0001 4108 2f10  ...2...4....A./.\n00000070: 022c e8e4 0b57 261c e3e3 e3e3 e3e3 8879  .,...W&........y\n00000080: 7979 f9f9 f9f9 f9f9 f9f9 f9f9 f9f9 f9f9  yy..............\n00000090: f9f9 0505 0505 0505 0505 0505 9ba4 0000  ................\n000000a0: 000d 0104 0032 0000 0034 0000 0001 4108  .....2...4....A.\n000000b0: 2f10 022c e9e4 0b57 261c e3e3 e3e3 e3e3  /..,...W&.......\n000000c0: 4805 0505 0505 0585 8585 8585 8585 8585  H...............\n000000d0: 8585 8585 8585 8545 4545 4545 4545 1f62  .......EEEEEEE.b\n000000e0: 0000 023e 0104 000b 0000 000c 0000 0001  ...>............\n000000f0: 4105 0844 0000 0000 0000 0000 0240 0104  A..D.........@..\n00000100: 0032 0000 0034 0000 0001 4108 2f10 022c  .2...4....A./..,\n00000110: c9e4 0b57 261c e3e3 e3e3 e3e3 c845 4545  ...W&........EEE\n00000120: 4545 4545 4545 c5c5 c5c5 c5c5 c5c5 c5c5  EEEEEE..........\n00000130: c5c5 c5c5 c5c5 2525 2525 9a2c 0000 0240  ......%%%%.,...@\n00000140: 0104 0032 0000 0034 0000 0001 4108 2f10  ...2...4....A./.\n00000150: 022c cae4 0b57 261c e3e3 e3e3 e3e3 2825  .,...W&.......(%\n00000160: 2525 2525 2525 2525 2525 25a5 a5a5 a5a5  %%%%%%%%%%%.....\n00000170: a5a5 a5a5 a5a5 a5a5 a5a5 a565 3783 0000  ...........e7...\n00000180: 0240 0104 0032 0000 0034 0000 0001 4108  .@...2...4....A.\n00000190: 2f10 022c cbe4 0b57 261c e3e3 e3e3 e3e3  /..,...W&.......\n000001a0: a865 6565 6565 6565 6565 6565 6565 6565  .eeeeeeeeeeeeeee\n000001b0: e5e5 e5e5 e5e5 e5e5 e5e5 e5e5 e5e5 f7b9  ................\n000001c0: 0000                                     ..\n"
        }
    ]
}
'''

def ffprobe(fname: str) -> FFProbeResult:
    commands = ["ffprobe", 
                "-v", "quiet", 
                "-print_format", "json",
                "-show_format", 
                "-select_streams", "2",
                "-show_packets",
                "-show_data",
                fname]
    print('Reading file: {}'.format(fname))
    result = subprocess.run(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return FFProbeResult(return_code=result.returncode,
                         json=result.stdout,
                         error=result.stderr)

def parse_ffprobe_output(ffprobe_result: FFProbeResult) -> list[Packet]:
    all_packets = []
    data = json.loads(ffprobe_result)
    start_timecode = data['format']['tags']['timecode']
    for packet in data['packets']:
        anc_packet = extract(packet['data'], packet['pts_time'], start_timecode, packet['pts'])
        if anc_packet != None:
            all_packets.append(anc_packet)
    return all_packets

def ms_to_frames(ms: int) -> int:
    return round((ms / FRAME_DURATION) * 1000)

def extract(packet_data: str, pts_time: int, start_timecode: str, pts_frame_number: int, did_sdid_to_extract: str=DID_SDID_TO_EXTRACT) -> Packet:
    anc_packet = ""
    
    # convert fractional time
    ms, seconds = modf(float(pts_time))
    seconds = (datetime.timedelta(seconds=seconds))
    ms = ms_to_frames(ms)

    file_timestamp = Template('0${seconds}:${ms}')
    file_timestamp = file_timestamp.substitute(seconds=seconds, ms=ms)

    # cast as Timecode type
    start_timecode = Timecode(FRAME_RATE, start_timecode)
    file_timestamp = Timecode(FRAME_RATE, file_timestamp)
    adjusted_timestamp = (start_timecode+file_timestamp)
    # Timecode module calculates 1 frame off
    adjusted_timestamp.add_frames(-1)
    
    packet_data_per_line = (packet_data.split("\n"))
    for line in packet_data_per_line[1:]:
        '''
        example data:
        [0]       [1]  [2]  [3]  [4]  [5]  [6]  [7]  [8] [9] [10]
        00000000: 0008 000b 0104 000b 0000 000c 0000 0001  ................\n
        00000010: 4105 0844 0000 0000 0000 0000 000d 0104  A..D............\n
        '''
        # TODO: this needs to be rewritten to actually parse the number of packets in the VANC and parse accordingly instead of the quick hack here
        data_per_line = line.split(" ")
        # ignore memory adress at [0] and empty space at [9] and decoded symbol jibberish at [10]
        for hex_data in data_per_line[1:9]:
            if hex_data in DID_SDID:
                # we found a new packet that interest us, since it's the start of the packet, we build a completely new ANC Packet
                if anc_packet == "":
                    anc_packet += hex_data
                else:
                    # we are at the beginning of a new ANC packet, so we export the latest built packet
                    if anc_packet[0:4] == did_sdid_to_extract:
                        packet = Packet(anc_packet, file_timestamp, adjusted_timestamp, pts_frame_number)
                        return packet
                    # reset to be able to build new packet
                    anc_packet = ""
            else:
                # still building the anc packet 
                if len(anc_packet)>0:
                    anc_packet += hex_data
  
###############
'''
    analyse van data
    packet met de scte data heeft een pts time, deze vertaalt zich in de tijdcode van de file en start van 00:00:00:00.
    pts start van 0 en is de frame nummer?

    voorbeeld: een scte trigger zit op tijdcode 00:00:31:22 van de opname.
    output data dump:
    "pts": 797,
    "pts_time": "31.880000",

    31.88 = 00:00:31:22. Als naar deze tijdcode wordt gesprongen, zie we utc tijdcode van 09:20:29:20

    als we in de ffmpeg thumbnails springen naar nummer 797 zoals de pts nummer, zien we tijdcode 09:20:29:19. Off by one, omdat de thumbnails starten vanaf 001 tot 4526. Data dump telt van 0 naar 4525.

    totale duurtijd testfile is 00:03:01:01

    4526 frames van 40 ms = 4526 * 0.04 (40ms) = 181 sec, 1 frame = 00:03:01:01

    => pts time van 31.88 = pts nummer 798 = 00:00:31:22, utc tijdcode van 09:20:29:20 ==> scte timed trigger met tijdcode 09:20:44:04 + 8000 ms preroll 
    = 09:20:52:04 (22s9fr verschil, 14s9fr (min preroll), 569 frames later

    start tijdcode uitlezen? die is 10:19:57:23
    '''
##### EOF ######
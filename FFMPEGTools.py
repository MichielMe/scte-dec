import os
import subprocess
import json
import datetime
from math import modf
from string import Template
from timecode import Timecode
from typing import NamedTuple

DID_SDID = ["4105", "4107", "4108"]
DID_SDID_TO_EXTRACT = "4107"
FRAME_RATE = 25
FRAME_DURATION = 40

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

def ffmpeg(fname: str, frame_numbers: list[int], padding: int=0, folder: str="") -> FFMPEGResult:
    print("Frame nrs:", frame_numbers)
    frame_number_selectstring = "\'"

    # if padding is needed, overwrite the frame_numbers list with a new list to add each frame number plus/minus the padding size
    # e.g. frame_numbers [5, 177] with padding size 3 will become: [2, 3, 4, 5, 6, 7, 8, 174, 175, 176, 177, 178, 179, 180]
    if padding > 0:
        frame_numbers = [frame for frame_number in frame_numbers for frame in range(frame_number - padding, frame_number + padding + 1, 1) ]
    
    # build the select string and skip the plus at the end
    length = len(frame_numbers)
    for idx, frame_number in enumerate(frame_numbers, start=1):
        frame_number_selectstring += ('eq(n,' + str(frame_number) + ')')
        if idx < length:
            frame_number_selectstring += '+'
    frame_number_selectstring += "\'"

    print("Frame nrs with padding:", frame_numbers)
    outputhpath = os.path.join(folder, "frames%d.jpg")

    # write each supplied frame number to a jpeg thumbnail
    # select string needs to be combined, otherwise gives "Error splitting the argument list: Option not found" when splitted in commands list
    commands = ["ffmpeg", 
                "-i", fname, 
                "-vf", "select=" + frame_number_selectstring,
                "-vsync", "0", 
                outputhpath]
    
    result = subprocess.run(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return FFMPEGResult(return_code=result.returncode,
                        args=result.args, 
                        error=result.stderr)

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
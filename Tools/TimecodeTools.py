from timecode import Timecode

FRAMERATE = 25

def timecode_to_frames(timecode):
    return sum(f * int(t) for f,t in zip((3600*FRAMERATE, 60*FRAMERATE, FRAMERATE, 1), timecode.split(':')))

def frames_to_timecode(frames):
    return '{0:02d}:{1:02d}:{2:02d}:{3:02d}'.format(int(frames / (3600*FRAMERATE)),
                                                    int(frames / (60*FRAMERATE) % 60),
                                                    int(frames / FRAMERATE % 60),
                                                    int(frames % FRAMERATE))


def test_timecode():
    tc1 = Timecode('25', '07:01:26:11')
    preroll = Timecode('25', '00:00:08:00')
    chain_delay = Timecode('25', '00:00:00:04')
    print(tc1 - preroll + chain_delay)

    tc4 = Timecode('25', '07:02:41:11')
    print(tc4 - preroll + chain_delay)

    tc2 = Timecode('25', '07:02:16:11')
    duration =  Timecode('25', '00:00:25:00')
    print(tc2 + duration - preroll + chain_delay)

    tc3_begin = Timecode('25', '20:15:41:16')
    tc3_duration = Timecode('25', '00:00:31:00')
    print(tc3_begin + tc3_duration)

    tc5_begin = Timecode('25', '00:00:00:00')
    #print(tc5_begin.back())
    #print (tc5_begin - Timecode('25', '00:00:02:04'))
    tc5_duration = Timecode('25', '00:00:10:00')
    tc6 = tc5_begin + tc5_duration

    print(tc6, tc6.frames, tc6.frames_to_tc, tc6.tc_to_string)
    tc7 = timecode_to_frames('00:00:10:00') 
    tc8 = timecode_to_frames('00:00:04:00')
    print( tc7, tc8)
    print( frames_to_timecode(tc7-tc8) )

    tc9 = Timecode('25', '00:00:10:00')
    tc10 = Timecode('25', '00:00:04:00')
    print(tc9.frames, tc10.frames) 

    tc11 = tc9 - tc10
    tc11.add_frames(1)
    print(tc11)

    tc12 = tc9 + tc10
    tc12.add_frames(-1)
    print(tc12)

    tc13 = Timecode('25', '00:00:08.927')
    tc14 = Timecode('25', '00:00:08.917')
    tc15 = Timecode('25', '00:00:08.937')
    tc16 = Timecode('25', '00:00:09.058')
    tc13.set_fractional(False)
    tc14.set_fractional(False)
    tc15.set_fractional(False)
    tc16.set_fractional(False)
    print(tc13, tc14, tc15, tc16)

if __name__ == "__main__":
    test_timecode()

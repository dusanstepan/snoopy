#!/usr/bin/env python
"""

DESCRIPTION

    Detects when sound is higher than threshold and records it in the output
    directory. Threshold is a number on a dB scale. A good value for threshold is
    around 40-50. The default value is 45. The default output directory
    is ./recorded_files/. Use Ctrl-c to exit the program.

EXAMPLES

    snoopy.py
    snoopy.py 40
    snoopy.py 40 -o /output/dir/where/files/are/going/to/be/saved/

AUTHOR

    Dusan Stepanovic <dusanstepan@yahoo.com>

LICENSE

    This script is in the public domain, free from copyrights or restrictions.
"""

import argparse
import sys, os, traceback
import pyaudio
import wave
import collections
import audioop
import os
import time
import math

CHUNK = 8096
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
EXTEND_LEFT_SECONDS = 1
EXTEND_RIGHT_SECONDS = 2

class NoDirError(Exception):
    def __init__(self, d):
        self.directory = d
    def __str__(self):
        return "The directory {} does not exist".format(self.directory)

def is_loud (data, threshold):
    rms_data = audioop.rms(data, 2)
    db_val = 20 * math.log10(rms_data) if rms_data > 0 else -1000
    return db_val > threshold

def generate_wav_name(outdir):
    outdir = outdir + '/' if not outdir.endswith('/') else outdir
    filename = ''.join([outdir, "rec_", time.strftime("%Y_%m_%d_%H_%M_%S"), ".wav"])
    return filename

def setup_wav_file(outdir, p):
    current_wav_file = generate_wav_name(outdir)
    wf = wave.open(current_wav_file, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    return wf

def write_left_extension(wf, frames):
    wf.writeframes(b''.join(frames))
    return

def quiet_for_some_time(loudness):
    return not (True in loudness)

def main (threshold, outdir):
    try:
        if not os.path.isdir(outdir):
            raise NoDirError(outdir)
        p = pyaudio.PyAudio()
        #dev_info = p.get_default_input_device_info()
        #CHANNELS = dev_info['maxInputChannels']
        #RATE = int(dev_info['defaultSampleRate'])
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
        MAXLEN_LEFT = int(RATE / CHUNK * EXTEND_LEFT_SECONDS)
        MAXLEN_RIGHT = int(RATE / CHUNK * EXTEND_RIGHT_SECONDS)
        frames = collections.deque(maxlen = MAXLEN_LEFT)
        loudness = collections.deque(maxlen = MAXLEN_RIGHT)
        record_on = False

        while True:
            data = stream.read(CHUNK)
            data_is_loud = is_loud(data, threshold)
            if not record_on and data_is_loud: 
                record_on = True
                print "Recording..."
                wf = setup_wav_file(outdir, p)
                write_left_extension(wf, frames)
            frames.append(data)
            loudness.append(data_is_loud)
            if record_on and quiet_for_some_time(loudness):
                record_on = False
                print "Done recording."
                wf.close()
            if record_on is True:
                wf.writeframes(data)
    except NoDirError as e:
        print e

    except KeyboardInterrupt as e:
        print "\nUser interrupt detected. Exiting..."

    except IOError as e:
        print str(e)
        traceback.print_exc()
        sys.exit(1)

    except Exception as e:
        print 'ERROR, UNEXPECTED EXCEPTION'
        print str(e)
        traceback.print_exc()
        sys.exit(2)

    print "Closing..."
    try:
        wf
    except NameError:
        pass
    else:
        wf.close()
    try:
        stream
    except NameError:
        pass
    else:
        stream.stop_stream()
        stream.close()
    try:
        p
    except NameError:
        pass
    else:
        p.terminate()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('threshold', type=float, nargs='?', default=45.0, help="Threshold for sound detection")
    parser.add_argument('-o', '--outdir', help="Output directory",
            default="./recorded_files/")
    args = parser.parse_args()

    main(**vars(args))


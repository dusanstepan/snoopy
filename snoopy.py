#!/usr/bin/env python
"""

DESCRIPTION

    Detects when sound is higher than threshold and records it in the output
    directory with snoopy.py listen. Threshold is a number on a dB scale.
    A good value for threshold is around 40-50. The default value is 45.
    The default output directory is ./recorded_files/. Use Ctrl-c to exit the program.
    Plays recorded files with snoopy.py play.

EXAMPLES

    snoopy.py listen
    snoopy.py listen 40
    snoopy.py listen 40 -o /output/dir/where/files/are/going/to/be/saved/
    snoopy.py play
    snoopy.py play -o /output/dir/with/wav/files/

AUTHOR

    Dusan Stepanovic <dusanstepan@yahoo.com>

LICENSE

    This script is in the public domain, free from copyrights or restrictions.
"""

import argparse
import pyaudio
import wave
import collections
import audioop
import time
import datetime
import math
import sys
import os
import traceback

CHUNK = 8192
FORMAT = pyaudio.paInt16
#CHANNELS = 2
#RATE = 44100
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

def setup_wav_file(outdir, p, CHANNELS, RATE):
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

def main_listen (func, threshold, outdir):
    try:
        if not os.path.isdir(outdir):
            raise NoDirError(outdir)
        p = pyaudio.PyAudio()
        dev_info = p.get_default_input_device_info()
        CHANNELS = dev_info['maxInputChannels']
        RATE = int(dev_info['defaultSampleRate'])
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
            try:
                data = stream.read(CHUNK)
            except IOError as e:
                print 'Problem reading from stream. Probably input overflow. Ignoring...'
            else:
                data_is_loud = is_loud(data, threshold)
                if not record_on and data_is_loud: 
                    record_on = True
                    print "Recording..."
                    wf = setup_wav_file(outdir, p, CHANNELS, RATE)
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

def main_play(func, outdir, datestring):

    try:
        if not os.path.isdir(outdir):
            raise NoDirError(outdir)
        else:
            if datestring == 'today':
                substr_contained = time.strftime("%Y_%m_%d")
            elif datestring == 'yesterday':
                substr_contained = str(datetime.date.today() - datetime.timedelta(days=1)).replace('-', '_')
            elif datestring == 'all':
                substr_contained = ''
            else:
                substr_contained = datestring.replace('-', '_')
            wav_files = [os.path.join(outdir, fn) for fn in os.listdir(outdir) 
                    if os.path.isfile(os.path.join(outdir,fn)) and fn.endswith('.wav') and substr_contained in fn]
        p = pyaudio.PyAudio()
        for wav_name in wav_files:
            wf = wave.open(wav_name, 'rb')
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)
            print('Playing file {}'.format(wav_name))
            data = wf.readframes(CHUNK)
            while data != '':
                stream.write(data)
                data = wf.readframes(CHUNK)
            wf.close()
            stream.stop_stream()
            stream.close()
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
    subparsers = parser.add_subparsers(help='Listen or play')
    
    parser_listen = subparsers.add_parser('listen', 
            help='Listen for sounds louder than threshold and record')
    parser_listen.add_argument('threshold', type=float, nargs='?', default=45.0, 
            help="Threshold for sound detection")
    parser_listen.add_argument('-o', '--outdir', help="Output directory",
            default="./recorded_files/")
    parser_listen.set_defaults(func=main_listen)
    
    parser_play = subparsers.add_parser('play', help='Plays recorded files')
    parser_play.add_argument('-o', '--outdir', help="Output directory",
            default="./recorded_files/")
    parser_play.add_argument('-d', '--datestring', help="Date files were recorded",
            default="today")
    parser_play.set_defaults(func=main_play)

    args = parser.parse_args()

    args.func(**vars(args))


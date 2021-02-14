#!/usr/bin/python
# -*- coding:utf-8 -*-

# *************************
# ** Before running this **
# ** code ensure you've  **
# ** turned on SPI on    **
# ** your Raspberry Pi   **
# ** & installed the     **
# ** Waveshare library   **
# ** & installed the     **
# ** FFMPEG library      **
# *************************

import os
import time
import random
import math
import argparse
import ffmpeg
from PIL import Image
from waveshare_epd import epd7in5_HD

## Defining screen Constants
WIDTH = 880
HEIGHT = 528
# Screen driver, Ensure this matches your particular screen
epd = epd7in5_HD.EPD()

class FrameNotCreatedError(Exception):
    """Exception raised for errors due to ffmpeg trying to create a frame

    Attributes:
        message -- explanation of the error
    """

    def __init__(self,message="The Frame is out of bound"):
        self.message = message
        super().__init__(self.message)

def generate_frame(in_filename, out_filename, time_frame, width, height):
    """ Takes input video with screen resolution and return a frame from the specified timestamp
    """
    (out,err) = (
        ffmpeg
        .input(in_filename, ss=time_frame)
        .filter('scale', width, height, force_original_aspect_ratio=1)
        .filter('pad', width, height, -1, -1)
        .output(out_filename, vframes=1)
        # .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
        # .run(capture_stderr=True)
        # .run(quiet=True)
    )
    # if str(err).find("Output file is empty, nothing was encoded"):
    #     raise FrameNotCreatedError()

def check_convert_video(value):
    """Check the video and return an error if its not an MKV or MP4
        if it is a MKV it convert the file to mp4
    """
    if value.endswith('.mkv'):
        return convert_to_mp4(value)
    elif value.endswith('.mp4'):
        return value
    else:
        raise argparse.ArgumentTypeError("%s should be an .mp4 or mkv file" % value)

def check_video(value):
    """Check the video and return an error if its not an MKV or MP4
    """
    if value.endswith('.mkv') or  value.endswith('.mp4'):
        return value
    else:
        raise argparse.ArgumentTypeError("%s should be an .mp4 or mkv file" % value)

def list_movies_from_directory (directory) :
    """Scan through video folder until it find an .mp4 or .mkv file
        return the list of files"""
    movie_list = []
    for entry in os.listdir(directory) :
        if (entry.endswith(".mkv") or entry.endswith('.mp4')) :
            movie_list.append(entry)
    if len(movie_list)==0 :
        print("No mp4 or mkv found in folder :"+ directory)
    return movie_list

def convert_to_mp4(mkv_file_path):
    'convert a file to mp4'
    name, ext = os.path.splitext(mkv_file_path)
    out_name = name + ".mp4"
    stream = ffmpeg.input(mkv_file_path)
    stream = ffmpeg.output(stream, out_name)
    ffmpeg.run(stream)

    print("Finished converting {}".format(mkv_file_path))
    os.remove(mkv_file_path)
    return out_name

def get_frame_number(video_path) :
    """ Get the number of frames of a video
    """
    if str.endswith(video_path,".mp4") :
        frame_count = int(ffmpeg.probe(video_path)['streams'][0]['nb_frames'])
        return frame_count
    elif str.endswith(video_path,".mkv"):
        duration = math.trunc(float(ffmpeg.probe(video_path)['format']['duration']))
        frame_rate= ffmpeg.probe(video_path)['streams'][0]['r_frame_rate'].split("/")
        frame_rate = float(int(frame_rate[0])/int(frame_rate[1]))
        frame_count = int(duration*frame_rate)
        return frame_count
    else:
        raise Exception

def main():
    # Ensure this is the correct path to your video folder
    vid_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Videos')
    log_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'logs')

    parser = argparse.ArgumentParser(description='SlowMovie Settings')
    parser.add_argument('-r', '--random', action='store_true',
        help="Random mode: chooses a random frame every refresh")
    parser.add_argument('-f', '--file', type=check_video,
        help='''Add a filename to start playing a specific film.
        Otherwise will pick a random file, and will move to another film randomly afterwards.''')
    parser.add_argument('-d', '--delay',  default=180,
        help="Delay between screen updates, in seconds")
    parser.add_argument('-i', '--inc',  default=10,
        help="Number of frames skipped between screen updates")
    parser.add_argument('-s', '--start',
        help="Start at a specific frame")
    args = parser.parse_args()

    frame_delay = float(args.delay)
    print("Frame Delay = %f s" %frame_delay )

    increment = float(args.inc)
    print("Increment = %f s" %increment )

    if args.random:
        print("In random mode")
    else:
        print ("In play-through mode")

    if args.file:
        print('Try to start playing %s' %args.file)
    else:
        print ("Continue playing existing file")




    ## variables
    movie_list = []
    saved_video=''
    saved_video_exists = False
    desired_file_exists = False
    current_video=''


    # the nowPlaying file stores the current video file
    try:
        file = open('nowPlaying.txt')
        for line in file:
            saved_video = line.strip()
        file.close()
    except FileNotFoundError :
        print('now playing not found')
    # if the now playing file exists check if the file argument is not empty 
    # and check if the saved video is equals

    # Scan through video folder until you find a valid .mp4 or .mkv file
    movie_list = list_movies_from_directory(vid_dir)
    desired_file_exists = False
    if args.file:
        if args.file in movie_list:
            desired_file_exists = True
            current_video = args.file
        else:
            print ('%s not found' %args.file)

    saved_video_exists = True if saved_video in movie_list else False
    if desired_file_exists:
        current_video = args.file
    elif saved_video_exists:
        current_video = saved_video
    else :
        current_video = movie_list[random.randint(0,len(movie_list)-1)]

    file = open('nowPlaying.txt', 'w')
    file.write(current_video)
    file.close()




    print("The current video is %s" %current_video)

    # Initialise and clear the screen
    epd.init()
    epd.Clear()

    current_position = 0

    # Open the log file and update the current position
    try:
        log = open(os.path.join(log_dir, '%s-progress'%current_video))
    except FileNotFoundError:
        log = open(os.path.join(log_dir, '%s-progress'%current_video), 'w')
        log.write(str(current_position))
        log.close()
    finally:
        log = open(os.path.join(log_dir, '%s-progress'%current_video))
        for line in log:
            current_position = float(line)
        if args.start:
            print('Start at frame %f' %float(args.start))
            current_position = float(args.start)
        log.close()


    input_vid = os.path.join(vid_dir, current_video)

    # Check how many frames are in the movie
    frame_count = get_frame_number(input_vid)
    print("there are %d frames in this video" %frame_count)

    while 1:
        start_time = time.time()
        if args.random:
            frame = random.randint(0,frame_count)
        else:
            frame = current_position

        ms_timecode = "%dms"%(frame*41.666666)

        #
        #frame_name = 'frame-{}.jpg'.format(current_position)
        frame_name = 'img_tmp.jpg'

        # Use ffmpeg to extract a frame from the movie, crop it, letterbox it and save it as grab.jpg
        try:
            generate_frame(input_vid, frame_name, ms_timecode, WIDTH, HEIGHT)
            # Open grab.jpg in PIL
            pil_im = Image.open(frame_name)

            # Dither the image into a 1 bit bitmap (Just zeros and ones)
            pil_im = pil_im.convert(mode='1',dither=Image.FLOYDSTEINBERG)

            # pil_im.save('dither-{}.jpg'.format(current_position),"PNG")
            pil_im.save('dither_tmp.jpg',"PNG")

            # display the image
            # epd.display(epd.getbuffer(pil_im))
            print('Diplaying frame %d of %s' %(frame,current_video))
        except FrameNotCreatedError :
            #Reset frame count with the value from the exception
            frame_count = current_position

        current_position = current_position + increment
        if current_position >= frame_count:
            current_position = 0
            log = open(os.path.join(log_dir, '%s-progress'%current_video), 'w')
            log.write(str(current_position))
            log.close()

            this_video = movie_list.index(current_video)
            if this_video < len(movie_list)-1:
                current_video = movie_list[this_video+1]
            else:
                current_video = movie_list[0]

        log = open(os.path.join(log_dir, '%s-progress'%current_video), 'w')
        log.write(str(current_position))
        log.close()


        file = open('nowPlaying.txt', 'w')
        file.write(current_video)
        file.close()

        # to aadjust the delay for computer with limited processing power
        end_time = time.time()
        processtime = int(end_time-start_time)
        if frame_delay < processtime:
            print ('increase frame delay to match process time : {} s'.format(processtime))
            time.sleep(0)
        else:
            time.sleep(frame_delay-processtime)
        epd.init()




    epd.sleep()

    epd7in5_HD.epdconfig.module_exit()
    exit()

if __name__=="__main__":
    main()

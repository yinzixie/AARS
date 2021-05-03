import os
import glob
from ffmpy import FFmpeg


def convert2(input, output):
    # ffmpeg -i fast-01.mp4 -vcodec h264 test.mp4
    ff = FFmpeg(inputs={input:'-ss 00:00:00'}, outputs={output: '-vcodec h264'})
    #print(ff.cmd)
    ff.run()


if __name__ == "__main__":
    # os.chdir("./video/robustness/new")
    # files = glob.glob("*.mp4")
    #
    # for path in files:
    #     dir, file = os.path.split(path)
    #     convert2(path, "new-" + file)

    convert2("F:\GraduationDesign\Adatpive Auto Recording System\wrong_gesture-03.mp4", "new-wrong_gesture-03.mp4")
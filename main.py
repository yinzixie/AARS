'''
Author: XYZ
Date: 2020-11-20 14:06:48
LastEditors: XYZ
LastEditTime: 2021-05-03 14:46:47
Description: file content
'''
import cv2
import time
import math
import threading
import numpy as np

from modules.render import *
from modules.recorder import *
from modules.adaptive_unit import *
from modules.image_processor import *


CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080

REC_WIDTH = 700  # 录像区域
REC_HEIGHT = 700

ROI_TUPLE = (0, 0, CAMERA_WIDTH, CAMERA_HEIGHT)  # roi

if __name__ == "__main__":
    # 0 many cam
    # 1 integrated
    # 2 split cam
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)  # 设置宽度
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)  # 设置长度

    render = Render("UI")
    recorder = Recorder("output.mp4", REC_WIDTH, REC_HEIGHT, 30)
    img_processor = ImageProcessor(CAMERA_WIDTH, CAMERA_HEIGHT, REC_WIDTH, REC_HEIGHT, ROI_TUPLE, render, recorder)

    adaptive_unit = AdaptiveUnit(img_processor, render, recorder)

    adaptive_unit.start()
    img_processor.start()

    while True:
        retval, frame = cap.read()
        if retval:
            # 翻转
            render_frame = cv2.flip(frame, 1)

            # record
            recorder.frame = render_frame.copy()
            # process image
            img_processor.frame = render_frame
            # render ui
            render.render_ui()

            k = cv2.waitKey(5) & 0xFF
            if k == 27:
                break
            if k == ord('b'):
                img_processor.calibration_frame_counter = 0
                img_processor.calibration = True
            if k == ord('r'):
                recorder.is_finished = False
        else:
            raise Exception("Can't read cap")
    with open(recorder.name + '.txt','w') as f:
        f.write(str(adaptive_unit.time_info))
    cv2.destroyAllWindows()
    cap.release()

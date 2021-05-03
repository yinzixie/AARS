import cv2
from .fps_monitor import *


class Render:
    def __init__(self, name):
        self.name = name

        self.msg = ""  # 在屏幕上显示的msg
        self.warning_msg = ""
        self.warning_type = ""

        self.frame = None

        cv2.namedWindow(name, 0)
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.fps_monitor = FPSMonitor()
        self.fps_monitor.start()

    def render_ui(self):
        if self.frame is not None:
            self.fps_monitor.monitor()
            cv2.putText(self.frame, self.msg, (100, 100), self.font, 2, (0, 255, 0), 4, cv2.LINE_AA)
            cv2.putText(self.frame, self.warning_msg, (100, 200), self.font, 2, (0, 0, 255), 4, cv2.LINE_AA)
            cv2.putText(self.frame, "FPS:" + str(self.fps_monitor.fps), (1800, 50), self.font, 1, (255, 255, 255), 4, cv2.LINE_AA)
            cv2.imshow(self.name, self.frame)

import cv2
import time
import threading


class Recorder:

    def __init__(self, name, width, height, fps):
        self.name = name
        self.REC_WIDTH = width  # 录像区域
        self.REC_HEIGHT = height
        self.fps = fps

        self.frame = None
        self.output = None
        self.in_recording = False
        self.is_finished = False

        self.rec_x = 0
        self.rec_y = 0

    def __recording(self):
        while self.in_recording:
            s = time.time()
            # cv2.imshow("2", self.frame)
            # k = cv2.waitKey(1)
            self.output.write(self.frame[self.rec_y:self.rec_y + self.REC_HEIGHT, self.rec_x:self.rec_x + self.REC_WIDTH])
            wait_time = 1 / self.fps - time.time() + s
            wait_time = 0 if wait_time < 0 else wait_time
            time.sleep(wait_time)

    def start(self):
        t = time.strftime("%Y-%m-%d %H.%M.%S", time.localtime())
        fourcc = cv2.VideoWriter_fourcc(*'H264')
        print(t)
        self.output = cv2.VideoWriter(t + " " + self.name, fourcc, self.fps, (self.REC_WIDTH, self.REC_HEIGHT))
        self.in_recording = True
        self.is_finished = False

        t = threading.Thread(target=self.__recording)
        t.start()

    def stop(self):
        self.in_recording = False
        self.is_finished = True

    def clear(self):
        self.output = None

    def interrupt(self):
        self.stop()
        self.is_finished = False
        self.clear()

    def save(self):
        self.output.release()

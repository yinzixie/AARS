import time
import threading


class FPSMonitor:
    def __init__(self):
        self.is_check = False
        self.__counter = 0
        self.fps = 0

    def monitor(self):
        self.__counter += 1

    def __check(self):
        while self.is_check:
            self.fps = self.__counter
            self.__counter = 0
            time.sleep(0.99)

    def start(self):
        self.is_check = True
        t = threading.Thread(target=self.__check)
        t.start()

    def stop(self):
        self.is_check = False
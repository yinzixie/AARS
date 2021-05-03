import cv2
import time
import threading


class AdaptiveUnit:
    TOO_FAR = 200
    TOO_CLOSE = 700
    REQUIRE_HAND = "left"
    time_info = []

    def __init__(self, image_processor, render, recorder):
        self.render = render
        self.recorder = recorder
        self.image_processor = image_processor

        self.is_check = False
        self.check_rate = 0.05  # 多少秒检查一次
        self.in_prepare = False
        self.prepare_time = 1.0  # prepare time
        self.count_down_time = self.prepare_time

        self.max_progress = 10
        self.progress_counter = 0
        self.opened = False

    def __process(self):
        while self.is_check:
            start = time.time()
            # 校正背景状态
            if self.image_processor.calibration:
                self.render.msg = "[STATUS] please wait! calibrating..."
                time.sleep(self.check_rate)
                continue
            # 录制完成状态
            if self.recorder.is_finished:
                self.render.msg = "[STATUS] Press r to re-record test"
                self.render.warning_msg = ""
                time.sleep(self.check_rate)
                continue

            # 装备录像状态
            if self.image_processor.hand is not None and self.TOO_FAR < self.image_processor.hand_width < self.TOO_CLOSE:
                # 录制中。。。
                if self.recorder.in_recording:
                    # 监控progress
                    if self.image_processor.finger_num == 2:
                        self.opened = True
                    if self.image_processor.finger_num <= 1 and self.opened:
                        self.opened = False
                        # print("tapping-close")
                        self.progress_counter += 1

                        r = {"tapping-" + str(self.progress_counter): time.time()}
                        self.time_info.append(r)

                        self.render.msg = "Your progress: " + str(self.progress_counter) + "/" + str(self.max_progress)
                        print(self.render.msg)
                        if self.progress_counter >= self.max_progress:
                            r = {"stop": time.time()}
                            self.time_info.append(r)

                            self.opened = False
                            self.progress_counter = 0
                            self.is_recording = False
                            self.render.msg = "recording finished"
                            self.recorder.stop()
                            self.recorder.save()
                            print(self.render.msg)
                    if self.image_processor.finger_num > 2 and self.opened:
                        r = {"wrong_gesture": time.time()}
                        self.time_info.append(r)

                        self.opened = False
                        self.progress_counter = 0
                        self.render.warning_type = "wrong_gesture"
                        self.render.warning_msg = "Interrupt recording.Wrong gesture!"
                        self.recorder.interrupt()
                        print(self.render.warning_msg)

                # 非录制
                else:
                    if self.render.warning_type != "wrong_gesture":
                        self.render.warning_msg = ""

                    # 准备手势
                    if self.image_processor.finger_num == 5:
                        if self.image_processor.hand == self.REQUIRE_HAND:
                            if self.render.warning_type == "wrong_hand":
                                self.render.warning_msg = ""

                            if self.count_down_time == self.prepare_time:
                                r = {"read_time": time.time()}
                                self.time_info.append(r)

                            self.in_prepare = True
                            self.count_down_time -= self.check_rate
                            self.render.msg = "start in " + str("%0.1f" % self.count_down_time) + " s"
                            print(self.render.msg)
                        else:
                            r = {"wrong_hand": time.time()}
                            self.time_info.append(r)

                            self.render.warning_type = "wrong_hand"
                            self.render.warning_msg = "Please use your left hand with palm face to the screen!"

                        # 准备时间到
                        if float("%0.2f"%self.count_down_time) <= 0:
                            r = {"start": time.time()}
                            self.time_info.append(r)

                            self.count_down_time = self.prepare_time
                            self.in_prepare = False
                            self.recorder.start()

                            self.render.msg = "[STATUS] Recording..."
                            print(self.render.msg)

                    # 非准备手势
                    else:
                        if self.in_prepare:
                            self.in_prepare = False
                            self.count_down_time = self.prepare_time
                            print("[STATUS] Interrupt Preparation...")
                        else:
                            self.render.msg = "Please make a ready gesture"

            else:
                # 判断错误类型
                if self.image_processor.hand is None:
                    self.render.msg = "Please put your hand in screen"
                    self.render.warning_type = "no_hand"
                    self.render.warning_msg = "Can't find hand!"
                elif self.image_processor.hand_width < self.TOO_FAR:
                    self.render.warning_type = "hand_distance"
                    self.render.warning_msg = "Please move your hand closer to the camera"
                elif self.image_processor.hand_width > self.TOO_CLOSE:
                    self.render.warning_type = "hand_distance"
                    self.render.warning_msg = "Please move your a little far away to the camera"

                # 中断准备或者录制状态
                if self.recorder.in_recording:
                    r = {self.render.warning_type: time.time()}
                    self.time_info.append(r)
                    r = {"stop": time.time()}
                    self.time_info.append(r)
                    self.progress_counter = 0
                    self.recorder.interrupt()
                    self.render.msg = "[STATUS] Interrupt Recording..."
                    print(self.render.warning_msg)
                    print("Interrupt Recording...")
                if self.in_prepare:
                    r = {self.render.warning_type: time.time()}
                    self.time_info.append(r)
                    r = {"stop_prepare": time.time()}
                    self.time_info.append(r)

                    self.in_prepare = False
                    self.count_down_time = self.prepare_time
                    print("[STATUS] Interrupt Preparation...")

            # print(time.time() - start)
            sleep_time = self.check_rate - (time.time() - start)
            sleep_time = 0 if sleep_time < 0 else sleep_time
            time.sleep(sleep_time)

    def interrupt_prepare(self):
        pass

    def start(self):
        self.is_check = True
        t = threading.Thread(target=self.__process)
        t.start()

    def stop(self):
        self.is_check = False

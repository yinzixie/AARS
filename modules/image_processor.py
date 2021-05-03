import cv2
import math
import time
import threading
import numpy as np


class ImageProcessor:
    kernel = np.ones((3, 3), np.uint8)
    min_hand_valid_width = 100  # 最小有效区域大小，小于阈值则视为噪声
    min_hand_valid_ratio = 0.02  # 最小有效区域大小，小于阈值则视为噪声

    def __init__(self, c_w, c_h, r_w, r_h, roi_tuple, render, recorder):
        self.render = render
        self.recorder = recorder

        self.bgs = []  # 背景

        self.hand = None
        self.frame = None
        self.render_frame = None
        self.in_process = False
        self.calibration = True
        self.accum_weight = 0.5
        self.calibration_frame = 30  # 用于校正背景的帧数
        self.calibration_frame_counter = 0

        self.CAMERA_WIDTH = c_w
        self.CAMERA_HEIGHT = c_h

        self.REC_WIDTH = r_w  # 录像区域
        self.REC_HEIGHT = r_h
        (self.TOP, self.LEFT, self.BOTTOM, self.RIGHT) = roi_tuple

    # ---------------------------------------------
    # 计算背景 只支持单通道
    # ---------------------------------------------
    @staticmethod
    def accumulate_bg(bg, gray, accum_weight=0.5):
        # initialize the background
        if bg is None:
            bg = gray.copy().astype("float")
            return bg

        # compute weighted average, accumulate it and update the background
        cv2.accumulateWeighted(gray, bg, accum_weight)
        return bg

    # ---------------------------------------------
    # Get a binary mask from bgs
    # ---------------------------------------------
    @classmethod
    def extract_mask(cls, bg, gray, threshold=20):
        # find the absolute difference between background and current frame
        diff_gray = cv2.absdiff(bg.astype("uint8"), gray)

        # threshold the diff image so that we get the foreground
        mask_img = cv2.threshold(diff_gray, threshold, 255, cv2.THRESH_BINARY)[1]
        mask_img = cv2.morphologyEx(mask_img, cv2.MORPH_CLOSE, cls.kernel)
        return mask_img

    # ---------------------------------------------
    # To segment the region of hand from binary mask
    # ---------------------------------------------
    @staticmethod
    def segment_hand(mask_img):
        # get the contours in the thresholded image
        (cnts, _) = cv2.findContours(mask_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # return None, if no contours detected
        if len(cnts) == 0:
            return None
        else:
            # based on contour area, get the maximum contour which is the hand
            segmented = max(cnts, key=cv2.contourArea)
            return segmented

    def __count_finger_num(self, approx, defects):
        # 轮廓
        # approx the contour a little 周长
        points = []
        valid_point = []

        if approx is None or defects is None:
            return 0, points

        try:
            # num_of_finger = no. of defects + 1
            num_of_finger = 0

            # code for finding no. of defects due to fingers
            for i in range(defects.shape[0]):
                s, e, f, d = defects[i, 0]
                start = tuple(approx[s][0])
                end = tuple(approx[e][0])
                far = tuple(approx[f][0])
                pt = (100, 180)

                # find length of all sides of triangle
                a = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
                b = math.sqrt((far[0] - start[0]) ** 2 + (far[1] - start[1]) ** 2)
                c = math.sqrt((end[0] - far[0]) ** 2 + (end[1] - far[1]) ** 2)
                s = (a + b + c) / 2
                ar = math.sqrt(s * (s - a) * (s - b) * (s - c))

                # distance between point and convex hull
                d = (2 * ar) / a

                # apply cosine rule here
                angle = math.acos((b ** 2 + c ** 2 - a ** 2) / (2 * b * c)) * 57

                # ignore angles > 90 and ignore points very close to convex hull(they generally come due to noise)
                if angle <= 90 and d > 30:
                    # num_of_finger += 1
                    # cv2.circle(self.render_frame, far, 3, [255, 0, 0], -1)
                    points.append(far)

                # draw lines around hand
                cv2.line(self.render_frame, start, end, [0, 255, 0], 2)


            # 确保在rec 范围内
            for p in points:
                if self.rec_x <= p[0] <= self.rec_x + self.REC_WIDTH and self.rec_y <= p[1] <= self.rec_y + self.REC_HEIGHT:
                    valid_point.append(p)
                    num_of_finger += 1
                    cv2.circle(self.render_frame, far, 3, [255, 0, 0], -1)

            if num_of_finger != 0:
                num_of_finger += 1
            return num_of_finger, points
        except Exception as err:
            # print(err)
            return 0, points

    def __calibrate_bg(self, new_bgs, names):
        # to get the background, keep looking till a threshold is reached
        # so that our weighted average model gets calibrated
        if self.calibration_frame_counter < 30:
            self.calibration_frame_counter += 1

            for index, bg in enumerate(self.bgs):
                self.bgs[index] = self.accumulate_bg(bg, new_bgs[index], self.accum_weight)
                #cv2.imshow(names[index], self.bgs[index])

            if self.calibration_frame_counter == 1:
                msg = "[STATUS] please wait! calibrating..."
                print(msg)
            elif self.calibration_frame_counter == 30:
                self.calibration = False
                msg = "[STATUS] calibration successful..."
                print(msg)

    # 判断左右手
    @staticmethod
    def which_hand(defects):
        if defects:
            right_x = max(defects, key=lambda item: item[0])
            left_x = min(defects, key=lambda item: item[0])

            # top_y = min(defects, key=lambda item: item[1])
            bottom_y = max(defects, key=lambda item: item[1])

            # right hand
            if left_x[0] == bottom_y[0]:
                return "right"
            elif right_x[0] == bottom_y[0]:
                return "left"
        return "uncertain"

    def __get_recording_area(self, approx):
        if approx is None:
            return -1, -1, -1
        # s = cv2.boundingRect(approx)
        rect = cv2.minAreaRect(approx)
        degree = rect[2]
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        # 获取四个顶点坐标
        left_point_x = np.min(box[:, 0])
        right_point_x = np.max(box[:, 0])
        top_point_y = np.min(box[:, 1])
        bottom_point_y = np.max(box[:, 1])

        left_point_y = box[:, 1][np.where(box[:, 0] == left_point_x)][0]
        right_point_y = box[:, 1][np.where(box[:, 0] == right_point_x)][0]
        top_point_x = box[:, 0][np.where(box[:, 1] == top_point_y)][0]
        bottom_point_x = box[:, 0][np.where(box[:, 1] == bottom_point_y)][0]

        height = right_point_y - top_point_y
        width = right_point_x - top_point_x
        hand_width = int((height * height + width * width) ** 0.5)
        # print(hand_width)

        # 定位recording area的点
        offset = 80
        rec_x = right_point_x - self.REC_WIDTH + offset
        rec_y = top_point_y - offset

        rec_x = 0 if rec_x < 0 else rec_x
        rec_x = self.CAMERA_WIDTH - self.REC_WIDTH if rec_x > self.CAMERA_WIDTH - self.REC_WIDTH else rec_x

        rec_y = 0 if rec_y < 0 else rec_y
        rec_y = self.CAMERA_HEIGHT - self.REC_HEIGHT if rec_y > self.CAMERA_HEIGHT - self.REC_HEIGHT else rec_y

        if hand_width > self.min_hand_valid_width:
            cv2.rectangle(self.render_frame, (rec_x, rec_y), (rec_x + self.REC_WIDTH, rec_y + self.REC_HEIGHT), (255, 255, 0), 2)
            cv2.drawContours(self.render_frame, [box], 0, (0, 0, 255), 2)

        return hand_width, rec_x, rec_y

    def __process(self):
        self.bgs = [None, None, None, None]
        #self.bgs = [None, None]
        while self.in_process:
            if self.frame is None:
                continue
            self.render_frame = self.frame.copy()
            roi = self.render_frame[:]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (7, 7), 0)
            b, g, r = cv2.split(roi)
            # b = cv2.GaussianBlur(b, (13, 13), 0)
            # g = cv2.GaussianBlur(g, (13, 13), 0)
            # r = cv2.GaussianBlur(r, (13, 13), 0)

            # cv2.imshow("gray", gray)
            # cv2.imshow("b", b)
            # cv2.imshow("g", g)
            # cv2.imshow("r", r)
            # k = cv2.waitKey(5)
            if self.calibration:
                self.__calibrate_bg([gray, r, g, b], ["b_gray", "b_r", "b_g", "b_b"])
                #self.__calibrate_bg([gray, r], ["b_gray", "r"])
                time.sleep(0.05)
            else:
                masks = []
                for index, bg in enumerate(self.bgs):
                    # segment the hand region
                    masks.append(self.extract_mask(bg, [gray, r, g, b][index]))
                    #masks.append(self.extract_mask(bg, [gray, r][index]))
                mask = masks[0]
                for m in masks:
                    mask = cv2.add(mask, m)

                # 通过mask分割出手
                hand_mask = self.segment_hand(mask)
                if hand_mask is None:
                    self.hand = None
                    continue
                else:
                    try:
                        cnt = hand_mask
                        epsilon = 0.0005 * cv2.arcLength(cnt, True)  # 精度 原始曲线与近似曲线之间的最大距离
                        # 最近似多边形
                        approx = cv2.approxPolyDP(cnt, epsilon, True)  # true 为闭合
                        # find the defects in convex hull with respect to hand 凸包
                        hull = cv2.convexHull(approx, returnPoints=False)
                        # defects
                        defects = cv2.convexityDefects(approx, hull)
                        #  判断占比
                        hand_area = cv2.contourArea(cnt)
                        ratio = int(hand_area) / int(self.REC_WIDTH * self.REC_HEIGHT)
                    except Exception as err:
                        approx = None
                        hull = None
                        defects = None
                        ratio = 0
                    self.hand_width, self.rec_x, self.rec_y = self.__get_recording_area(approx)
                    # print(self.hand_width, ratio)
                    if self.hand_width > self.min_hand_valid_width and ratio >  self.min_hand_valid_ratio:
                        self.recorder.rec_y = self.rec_y
                        self.recorder.rec_x = self.rec_x
                        self.finger_num, finger_defects = self.__count_finger_num(approx, defects)
                        self.hand = self.which_hand(finger_defects)
                        cv2.drawContours(self.render_frame, [cnt + (self.LEFT, self.TOP)], -1, (0, 0, 255))
                    else:
                        self.hand = None

            self.render.frame = self.render_frame.copy()

    def start(self):
        self.in_process = True
        t = threading.Thread(target=self.__process)
        t.start()

    def stop(self):
        self.in_process = False

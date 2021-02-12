import os
import cv2
import json
import copy
import numpy as np

MAX_POS_VALUE = 1e6
MIN_POS_VALUE = -1e6


class Render:
    def __init__(self, maps):
        self.maps = copy.deepcopy(maps)
        min_x, max_x, min_y, max_y = self.calc_position_range()
        self.border = 50
        self.offset_x = - min_x + self.border
        self.offset_y = - min_y + self.border
        self.canvas_width = max_x - min_x + 1 + self.border * 2
        self.canvas_height = max_y - min_y + 1 + self.border * 2

        pass

    def calc_position_range(self):
        min_x, min_y = MAX_POS_VALUE, MAX_POS_VALUE
        max_x, max_y = MIN_POS_VALUE, MIN_POS_VALUE

        for node_id in self.maps:
            min_x = min(self.maps[node_id].absolute_coord.x, min_x)
            min_y = min(self.maps[node_id].absolute_coord.y, min_y)
            max_x = max(self.maps[node_id].absolute_coord.x, max_x)
            max_y = max(self.maps[node_id].absolute_coord.y, max_y)
            pass
        return min_x, max_x, min_y, max_y

    def render(self):
        image = np.zeros((self.canvas_height, self.canvas_width, 3))

        for node_id in self.maps:
            ori_x = self.maps[node_id].absolute_coord.x
            ori_y = self.maps[node_id].absolute_coord.y
            update_x = ori_x + self.offset_x
            update_y = ori_y + self.offset_y
            cv2.putText(image, '%d' % node_id, (update_x, update_y),
                        fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=1.0, color=(255,255,255), thickness=1)

        cv2.imshow('canvas', image)
        cv2.waitKey(0)

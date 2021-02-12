import os
import cv2
import json
import copy
import numpy as np

MAX_POS_VALUE = 1e6
MIN_POS_VALUE = -1e6

FONT_SCALE = 0.8

def get_default_text_size():
    text_size, baseline = cv2.getTextSize('0000', fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=FONT_SCALE, thickness=1)
    text_width = text_size[0]
    text_height = text_size[1]
    return text_width, text_height

class Render:
    def __init__(self, maps, groups):
        self.maps = copy.deepcopy(maps)
        self.groups = copy.deepcopy(groups)
        min_x, max_x, min_y, max_y = self.calc_position_range()
        self.border = 50
        self.offset_x = - min_x + self.border
        self.offset_y = - min_y + self.border
        self.canvas_width = max_x - min_x + 1 + self.border * 2
        self.canvas_height = max_y - min_y + 1 + self.border * 2
        print('canvas: %dx%d' % (self.canvas_width, self.canvas_height))
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
        text_width, text_height = get_default_text_size()
        for node_id in self.maps:
            ori_x = self.maps[node_id].absolute_coord.x
            ori_y = self.maps[node_id].absolute_coord.y
            update_x = ori_x + self.offset_x
            update_y = ori_y + self.offset_y
            cv2.putText(image, '%d' % node_id, (update_x, update_y),
                        fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=FONT_SCALE, color=(255,255,255), thickness=1)

        for group_id in self.groups:
            lt = self.groups[group_id].lt
            rb = self.groups[group_id].rb
            cv2.rectangle(image,
                          (lt.x + self.offset_x, lt.y + self.offset_y), (rb.x + self.offset_x, rb.y + self.offset_y),
                          (0, 0, 255), 1)

            parent_node_id = self.groups[group_id].parent_node_id
            if parent_node_id in self.maps:
                parent_node_coord = self.maps[parent_node_id].absolute_coord
                start_pt = (parent_node_coord.x+int(text_width/2) + self.offset_x, parent_node_coord.y + self.offset_y)
                end_pt = (int((lt.x+rb.x)/2) + self.offset_x, lt.y + self.offset_y)
                cv2.line(image, start_pt, end_pt, (0, 0, 255), 1)

        cv2.imshow('canvas', image)
        cv2.imwrite('./canvas.jpg', image)
        cv2.waitKey(0)

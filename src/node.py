import os
import cv2
import json
import copy
import numpy as np



def get_default_text_size():
    text_size, baseline = cv2.getTextSize('0000', fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=1.0, thickness=1)
    text_width = text_size[0]
    text_height = text_size[1]
    return text_width, text_height

class Coordinate:
    def __init__(self, x=None, y=None):
        self.x = x
        self.y = y

    def set_coord(self, x, y):
        self.x = x
        self.y = y


class Node:
    def __init__(self, node_id, layer_id, children, parent, group_id):
        self.node_id = node_id
        self.layer_id = layer_id
        self.children = children
        self.parent = parent
        self.group_id = group_id
        self.absolute_coord = Coordinate()
        self.relative_coord = Coordinate()

    def assign_absolute_coord(self, x, y):
        self.absolute_coord.x = x
        self.absolute_coord.y = y

    def valid_absolute_coord(self):
        if self.absolute_coord.x is None or self.absolute_coord.y is None:
            return False
        return True

    def assign_relative_coord(self, x, y):
        self.relative_coord.x = x
        self.relative_coord.y = y

    def valid_relative_coord(self):
        if self.relative_coord.x is None or self.relative_coord.y is None:
            return False
        return True




class Group:
    def __init__(self, contains, group_id, layer_id, parent_node_id):
        self.contains = copy.deepcopy(contains)
        self.group_id = group_id
        self.layer_id = layer_id
        self.parent_node_id = parent_node_id
        # from config , need update later
        self.text_width, self.text_height = get_default_text_size()
        self.boarder = self.text_width
        self.bbox_size = None

    def calc_relative_coord(self, maps):
        pos_x, pos_y = self.boarder, self.boarder
        for idx in range(len(self.contains)):
            node_id = self.contains[idx]
            maps[node_id].assign_relative_coord(pos_x, pos_y)
            pos_x += self.text_width+self.boarder
        pos_y += self.text_height + self.boarder
        self.bbox_size = (pos_x, pos_y)
        pass

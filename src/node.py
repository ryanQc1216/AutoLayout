import os
import cv2
import json
import copy
import numpy as np

from src.render import get_default_text_size



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

    def assign_absolute_by_relative(self, group_sx, group_sy):
        assert self.valid_relative_coord()
        self.absolute_coord.x = self.relative_coord.x + group_sx
        self.absolute_coord.y = self.relative_coord.y + group_sy

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
        self.lt = Coordinate()
        self.rb = Coordinate()

    def calc_relative_coord(self, maps):
        pos_x, pos_y = self.boarder, self.boarder
        for idx in range(len(self.contains)):
            node_id = self.contains[idx]
            maps[node_id].assign_relative_coord(pos_x, pos_y)
            pos_x += self.text_width + self.boarder
        pos_y += self.text_height + self.boarder
        self.bbox_size = (pos_x, pos_y)
        pass

    def assign_group_bbox(self, sx, sy, maps):
        self.lt.set_coord(sx, sy)
        self.rb.set_coord(sx + self.bbox_size[0], sy + self.bbox_size[1])
        # let's modify the map's valid_absolute_coord of nodes
        for idx in range(len(self.contains)):
            node_id = self.contains[idx]
            maps[node_id].assign_absolute_by_relative(sx, sy)

    def valid_bbox_lt(self):
        if self.lt.x is None or self.lt.y is None:
            return False
        return True

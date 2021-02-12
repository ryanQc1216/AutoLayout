import os
import cv2
import json
import copy
import numpy as np

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
        # self.Relative_x = None

    def valid_absolute_coord(self):
        if self.absolute_coord.x is None or self.absolute_coord.y is None:
            return False
        else:
            return True

    def assign_absolute_position(self, x, y):
        self.absolute_coord.x = x
        self.absolute_coord.y = y


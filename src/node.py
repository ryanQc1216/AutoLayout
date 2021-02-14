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
    def __init__(self, node_id, children, parent, depth):
        self.node_id = node_id
        self.children = children
        self.parent = parent
        self.group_id = None
        self.depth = depth
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
    def __init__(self, contains, group_id, depth, parent_node_id):
        self.contains = copy.deepcopy(contains)
        self.group_id = group_id
        self.depth = depth
        self.parent_node_id = parent_node_id
        self.text_width, self.text_height = get_default_text_size()
        self.boarder = self.text_width

        # matrix of nodes
        self.rows = None
        self.cols = None

        # from config , need update later
        self.bbox_size = None
        self.lt = Coordinate()
        self.rb = Coordinate()
        self.is_stack_group = False

    def assign_group_offset(self, sx, sy, maps):
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

    def get_bbox_as_list(self):
        return [self.lt.x, self.lt.y, self.rb.x, self.rb.y]

    def pick_children_nodes(self, maps):
        has_children = []
        for node_id in self.contains:
            if len(maps[node_id].children) > 0:
                has_children.append(node_id)
        return has_children

    def modify_contains_order(self, maps):
        has_children = self.pick_children_nodes(maps)
        update_contains = []
        for node_id in self.contains:
            if node_id not in has_children:
                update_contains.append(node_id)
        update_contains += has_children.copy()
        self.contains = update_contains

    def assign_node_relative_coord(self, maps, max_cols_contains):
        total_nodes = len(self.contains)
        has_children = self.pick_children_nodes(maps)
        if len(self.contains) <= max_cols_contains:
            self.rows = 1
            self.cols = total_nodes
        elif len(has_children) == 0:
            self.rows = total_nodes//max_cols_contains + 1
            self.cols = max_cols_contains
        else:
            self.cols = max(max_cols_contains, len(has_children))
            self.rows = total_nodes // max_cols_contains + 1
            self.modify_contains_order(maps)

        # assign from right bottom to left top
        node_cnt = 0
        start_y = self.boarder
        max_x = 0
        for row in range(0, self.rows):
            start_x = self.boarder
            for cols in range(0, self.cols):
                if node_cnt >= len(self.contains):
                    break
                node_id = self.contains[node_cnt]
                if node_id in has_children and row != self.rows-1:
                    break
                # assign here
                maps[node_id].assign_relative_coord(start_x, start_y)
                # end assign
                start_x += self.text_width + self.boarder
                max_x = max(start_x, max_x)
                node_cnt += 1
            start_y += self.text_height + self.boarder

        box_height = start_y
        box_width = max_x #self.cols*(self.boarder+self.text_width) + self.boarder
        self.bbox_size = (box_width, box_height)
        pass
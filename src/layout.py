import os
import cv2
import json
import copy
import numpy as np
from src.node import Coordinate, Node, Group, get_default_text_size
from src.render import Render


def parsing_children_description(description):
    if 'children' not in description:
        return [], []
    return [x for x in description['children']], [x['id'] for x in description['children']]


class Layout:
    def __init__(self, description):
        self.description = description
        self.max_node_support = 999
        self.start_parent_id = -1
        self.maps, self.groups = self.translate_maps()
        self.replace_groups_key()
        assert self.check_all_node_relative_assigned()
        self.calc_canvas()

    def translate_maps(self):
        maps = dict()
        groups = dict()
        children_description, children_node_id = parsing_children_description(self.description)
        start_node = Node(node_id=self.description['id'],
                          layer_id=0,
                          children=children_node_id,
                          parent=self.start_parent_id,
                          group_id=0)
        groups[self.start_parent_id] = Group(contains=[self.description['id']],
                                             group_id=0,
                                             layer_id=0,
                                             parent_node_id=self.start_parent_id)
        maps[start_node.node_id] = start_node
        candidates = children_description.copy()

        _iter = 0
        while len(candidates) > 0:
            candidate = candidates.pop()
            candidate_children_description, candidate_children_node_id = parsing_children_description(candidate)
            node_id = candidate['id']
            parent_node_id = candidate['parentId']
            parent_layer_id = maps[parent_node_id].layer_id
            if parent_node_id not in groups:
                groups[parent_node_id] = Group(contains=maps[parent_node_id].children.copy(),
                                               group_id=len(groups),
                                               layer_id=parent_layer_id + 1,
                                               parent_node_id=parent_node_id)
            else:
                pass
            this_node = Node(node_id=node_id,
                             layer_id=parent_layer_id + 1,
                             children=candidate_children_node_id,
                             parent=parent_node_id,
                             group_id=groups[parent_node_id].group_id)
            maps[node_id] = this_node
            candidates += candidate_children_description
            _iter += 1
            assert _iter < self.max_node_support, 'Surpass the max node number limit'

        for group_id in groups:
            groups[group_id].calc_relative_coord(maps)
        return maps, groups

    def replace_groups_key(self):
        groups_update = dict()
        for parent_node_id in self.groups:
            groups_update[self.groups[parent_node_id].group_id] = copy.deepcopy(self.groups[parent_node_id])
        self.groups = groups_update

    def check_all_node_relative_assigned(self):
        cnt_assigned = 0
        for node_id in self.maps:
            if self.maps[node_id].valid_relative_coord():
                cnt_assigned += 1
        if cnt_assigned == len(self.maps):
            return True
        else:
            return False

    def check_all_group_assigned(self):
        cnt_assigned = 0
        for group_id in self.groups:
            if self.groups[group_id].valid_bbox_lt():
                cnt_assigned += 1
        if cnt_assigned == len(self.groups):
            return True
        else:
            return False

    def node_id_to_group_id(self, node_id):
        group_id = self.maps[node_id].group_id
        return group_id

    def inference_children_group_coord(self, parent_node_id, children_group_id):
        parent_group_id = self.node_id_to_group_id(parent_node_id)
        text_width, text_height = get_default_text_size()
        children_group_cx = self.maps[parent_node_id].absolute_coord.x + int(text_width / 2)
        children_group_sy = self.groups[parent_group_id].rb.y + text_width
        children_group_sx = children_group_cx - int(self.groups[children_group_id].bbox_size[0] / 2)
        return children_group_sx, children_group_sy

    def calc_canvas(self):
        self.maps = self.maps
        self.groups = self.groups
        self.groups[0].assign_group_offset(sx=0, sy=0, maps=self.maps)
        while self.check_all_group_assigned() is False:
            for group_id in self.groups:
                parent_node_id = self.groups[group_id].parent_node_id
                if parent_node_id == self.start_parent_id or self.groups[group_id].valid_bbox_lt() is True:
                    continue
                parent_group_id = self.node_id_to_group_id(parent_node_id)
                if self.groups[parent_group_id].valid_bbox_lt() is False:
                    continue
                sx, sy = self.inference_children_group_coord(parent_node_id, group_id)
                self.groups[group_id].assign_group_offset(sx=sx, sy=sy, maps=self.maps)
                pass

        self.groups[9].assign_group_offset(sx=self.groups[9].lt.x - 300,
                                           sy=self.groups[9].lt.y,
                                           maps=self.maps)
        self.update_related_groups(9)
        ins_render = Render(self.maps, self.groups)
        ins_render.render()
        pass

    def update_related_groups(self, group_id):
        contains = self.groups[group_id].contains.copy()
        stack_info = []
        for node_id in contains:
            stack_info.append({'node_id': node_id, 'group_id': group_id})
        while len(stack_info) > 0:
            parent_info = stack_info.pop()
            parent_node_id = parent_info['node_id']
            parent_group_id = parent_info['group_id']

            # update this parent_node_id's next group
            if len(self.maps[parent_node_id].children) > 0:
                first_children_id = self.maps[parent_node_id].children[0]
                children_group_id = self.maps[first_children_id].group_id
                sx, sy = self.inference_children_group_coord(parent_node_id, children_group_id)
                self.groups[children_group_id].assign_group_offset(sx=sx, sy=sy, maps=self.maps)
                for node_id in self.maps[parent_node_id].children:
                    stack_info.append({'node_id': node_id, 'group_id': children_group_id})

        kk = 1

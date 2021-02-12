import os
import cv2
import json
import copy
import numpy as np
from src.node import Coordinate, Node
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
        self.maps, self.raw_groups = self.translate_maps()
        self.refine_groups()
        self.group = copy.deepcopy(self.raw_groups)
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
        groups[self.start_parent_id] = {'group_id': 0, 'contains': [self.description['id']], 'layer_id': 0}
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
                groups[parent_node_id] = {'group_id': len(groups),
                                          'contains': maps[parent_node_id].children.copy(),
                                          'layer_id': parent_layer_id + 1}
            else:
                pass
            this_node = Node(node_id=node_id,
                             layer_id=parent_layer_id + 1,
                             children=candidate_children_node_id,
                             parent=parent_node_id,
                             group_id=groups[parent_node_id])
            maps[node_id] = this_node
            candidates += candidate_children_description
            _iter += 1
            assert _iter < self.max_node_support, 'Surpass the max node number limit'

        # check groups contain equal to maps
        cnt = 0
        for p in groups:
            cnt += len(groups[p]['contains'])
        assert cnt == len(maps), 'translate_maps error happened!!'
        return maps, groups

    # if one group has only one nodes
    def refine_groups(self):

        pass

    def get_text_size(self):
        text_size, baseline = cv2.getTextSize('1111', fontFace=cv2.FONT_HERSHEY_PLAIN, fontScale=1.0, thickness=1)
        return text_size

    def calc_groups_bbox(self):

        pass

    def check_all_node_position_assigned(self):
        cnt_assigned = 0
        for node_id in self.maps:
            if self.maps[node_id].absolute_coord.x is not None and self.maps[node_id].absolute_coord.y is not None:
                cnt_assigned += 1
        if cnt_assigned == len(self.maps):
            return True
        else:
            return False

    def calc_pos_by_parent(self, layer_step, node_step, parent_node_id, contains):
        parent_x = self.maps[parent_node_id].absolute_coord.x
        parent_y = self.maps[parent_node_id].absolute_coord.y
        width = (len(contains) - 1) * node_step
        start_x = - width / 2.0
        positions = []
        for idx in range(len(contains)):
            temp_x = parent_x + start_x + idx * node_step
            temp_y = parent_y + layer_step
            positions.append((int(temp_x), int(temp_y)))
        return positions

    def calc_canvas(self):
        maps = self.maps
        groups = self.raw_groups
        text_size = self.get_text_size()
        layer_step = text_size[0] * 2
        node_step = text_size[0] * 2

        # assign first node's position
        start_node_id = groups[self.start_parent_id]['contains'][0]
        maps[start_node_id].assign_absolute_position(x=0, y=0)

        while self.check_all_node_position_assigned() is False:
            for parent_node_id in groups:
                if parent_node_id == self.start_parent_id:
                    continue
                if self.maps[parent_node_id].valid_absolute_coord() is False:
                    continue
                contains = groups[parent_node_id]['contains']
                positions = self.calc_pos_by_parent(layer_step, node_step, parent_node_id, contains)
                for idx in range(len(contains)):
                    node_id = contains[idx]
                    self.maps[node_id].assign_absolute_position(x=positions[idx][0], y=positions[idx][1])

        ins_render = Render(self.maps)
        ins_render.render()

        pass



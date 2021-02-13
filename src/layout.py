import os
import cv2
import json
import copy
import numpy as np
import itertools
import functools
from src.node import Coordinate, Node, Group, get_default_text_size
from src.render import Render, MAX_POS_VALUE, MIN_POS_VALUE, SMALL_POS_VALUE


def parsing_children_description(description):
    if 'children' not in description:
        return [], []
    return [x for x in description['children']], [x['id'] for x in description['children']]


class Layout:
    def __init__(self, description):
        self.description = description
        self.max_loop_support = 999
        self.start_parent_id = -1
        self.maps, self.groups = self.translate_maps()
        self.replace_groups_key()
        assert self.check_all_node_relative_assigned()
        self.init_group_coord()
        self.layer_info = self.update_layer_info()
        self.placement_group()

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
        while len(candidates) > 0 and _iter < self.max_loop_support:
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
        assert _iter < self.max_loop_support, 'Error happened in While loop'

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

    def init_group_coord(self):
        self.maps = self.maps
        self.groups = self.groups
        self.groups[0].assign_group_offset(sx=0, sy=0, maps=self.maps)
        _iter = 0
        while self.check_all_group_assigned() is False and _iter < self.max_loop_support:
            for group_id in self.groups:
                parent_node_id = self.groups[group_id].parent_node_id
                if parent_node_id == self.start_parent_id or self.groups[group_id].valid_bbox_lt() is True:
                    continue
                parent_group_id = self.node_id_to_group_id(parent_node_id)
                if self.groups[parent_group_id].valid_bbox_lt() is False:
                    continue
                sx, sy = self.inference_children_group_coord(parent_node_id, group_id)
                self.groups[group_id].assign_group_offset(sx=sx, sy=sy, maps=self.maps)
                _iter += 1
        assert _iter < self.max_loop_support, 'Error happened in While loop'
        pass

    def update_related_groups(self, group_id):
        contains = self.groups[group_id].contains.copy()
        stack_info = []
        for node_id in contains:
            stack_info.append({'node_id': node_id, 'group_id': group_id})

        _iter = 0
        while len(stack_info) > 0 and _iter < self.max_loop_support:
            parent_info = stack_info.pop()
            parent_node_id = parent_info['node_id']
            # update this parent_node_id's next group
            if len(self.maps[parent_node_id].children) > 0:
                first_children_id = self.maps[parent_node_id].children[0]
                children_group_id = self.maps[first_children_id].group_id
                sx, sy = self.inference_children_group_coord(parent_node_id, children_group_id)
                self.groups[children_group_id].assign_group_offset(sx=sx, sy=sy, maps=self.maps)
                for node_id in self.maps[parent_node_id].children:
                    stack_info.append({'node_id': node_id, 'group_id': children_group_id})
            _iter += 1
        assert _iter < self.max_loop_support, 'Error happened in While loop'
        pass

    def sort_by_parent_cx(self, group_ids):
        group_ids_sort = group_ids.copy()
        for i in range(len(group_ids_sort)):
            for j in range(i + 1, len(group_ids_sort)):
                group_id_i = group_ids_sort[i]
                group_id_j = group_ids_sort[j]
                if self.maps[self.groups[group_id_i].parent_node_id].absolute_coord.x > \
                        self.maps[self.groups[group_id_j].parent_node_id].absolute_coord.x:
                    temp = group_ids_sort[i]
                    group_ids_sort[i] = group_ids_sort[j]
                    group_ids_sort[j] = temp
        return group_ids_sort

    def update_layer_info(self):
        layer_info = {}
        for group_id in self.groups:
            layer_index = self.groups[group_id].layer_id
            if layer_index not in layer_info:
                layer_info[layer_index] = [group_id]
            else:
                layer_info[layer_index].append(group_id)
        # rank group-id list by parent node cx
        for layer_index in layer_info:
            if layer_index == 0:
                continue
            group_ids = layer_info[layer_index]
            layer_info[layer_index] = self.sort_by_parent_cx(group_ids)
        return layer_info

    def calc_two_bbox_overlap(self, bbox_0, bbox_1):
        sx0, ex0, sy0, ey0 = bbox_0
        sx1, ex1, sy1, ey1 = bbox_1
        sx = max(sx0, sx1)
        sy = max(sy0, sy1)
        ex = min(ex0, ex1)
        ey = min(ey0, ey1)
        width = max(0, ex - sx + 1)
        height = max(0, ey - sy + 1)
        overlap = width * height
        return overlap

    def calc_layer_group_overlap(self, layer_id):
        group_ids = self.layer_info[layer_id]
        overlap = 0
        for select in itertools.combinations(group_ids, 2):
            group_id_0 = select[0]
            group_id_1 = select[1]
            overlap += self.calc_two_bbox_overlap(self.groups[group_id_0].get_bbox_as_list(),
                                                  self.groups[group_id_1].get_bbox_as_list())
        return overlap

    def find_valid_placement_area(self, group_id, group_ids, already_placement):
        start_x = MIN_POS_VALUE
        end_x = MAX_POS_VALUE
        left_group_ids = group_ids[:group_ids.index(group_id)]
        right_group_ids = group_ids[group_ids.index(group_id) + 1:]
        border = self.groups[group_id].boarder
        for l_idx in left_group_ids:
            if l_idx in already_placement:
                start_x = max(start_x, already_placement[l_idx][2] + border)  # use ex
        for r_idx in right_group_ids:
            if r_idx in already_placement:
                end_x = min(end_x, already_placement[r_idx][0] - border)  # use sx
        return start_x, end_x

    def constrain_placement_group(self, group_id, original_bbox, start_x, end_x):
        # not valid
        if self.groups[group_id].bbox_size[0] > (end_x - start_x):
            return None
        # use original
        if original_bbox[0] > start_x and original_bbox[2] < end_x:
            return original_bbox.copy()
        # left overlap
        if original_bbox[0] <= start_x:
            distance = start_x - original_bbox[0] + 1
            return original_bbox[0] + distance, original_bbox[1], original_bbox[2] + distance, original_bbox[3]
        # right overlap
        if original_bbox[2] >= end_x:
            distance = original_bbox[2] - end_x + 1
            return original_bbox[0] - distance, original_bbox[1], original_bbox[2] - distance, original_bbox[3]
        raise Exception('Error Happened in constrain_placement_group')

    def calc_placement_movement_cost(self, original_bbox_info, update_bbox_info):
        move_cnt = 0
        move_dis = 0
        for group_id in original_bbox_info:
            contain_num = len(self.groups[group_id].contains)
            dis = abs(original_bbox_info[group_id][0] - update_bbox_info[group_id][0])
            if dis > SMALL_POS_VALUE:
                move_cnt += contain_num
                move_dis += move_dis
        return move_cnt, move_dis

    def search_minimal_movement_policy(self, layer_id):
        if layer_id==7:
            kk = 1
        # group_ids is ordered from left to right
        group_ids = self.layer_info[layer_id].copy()
        original_bbox = {}
        for group_id in group_ids:
            original_bbox[group_id] = self.groups[group_id].get_bbox_as_list().copy()
        best_placement_info = {'placement': None, 'move_cnt': MAX_POS_VALUE, 'move_dis': MAX_POS_VALUE}

        all_placement_order = list(itertools.permutations(group_ids))[:self.max_loop_support]
        print('layer %d generate all placement order %d' % (layer_id, len(all_placement_order)))
        for placement_order in all_placement_order:
            already_placement = dict()  # {saved_new_bbox}
            for idx in range(len(placement_order)):
                group_id = placement_order[idx]
                start_x, end_x = self.find_valid_placement_area(group_id, group_ids, already_placement)
                update_bbox = self.constrain_placement_group(group_id, original_bbox[group_id], start_x, end_x)
                if update_bbox is None:
                    break
                already_placement[group_id] = update_bbox
                pass
            if len(already_placement) == len(group_ids):
                move_cnt, move_dis = self.calc_placement_movement_cost(original_bbox, already_placement)
                if (move_cnt < best_placement_info['move_cnt']) or \
                        (move_cnt == best_placement_info['move_cnt'] and move_dis == best_placement_info['move_dis']):
                    best_placement_info = {'placement': already_placement, 'move_cnt': move_cnt, 'move_dis': move_dis}
        assert best_placement_info['placement'] is not None, 'Error in search_minimal_movement_policy!!'
        return best_placement_info


    # placement layer by layer
    # 1) Layer by Layer 的遍历Group
    # 2) 每次检查当前layer内部group重叠情况，以IOU作为得分 (如果默认没有重叠，则不改变原json顺序)
    # 3) 如果最小IOU仍然重叠，则尝试移动某些Group来满足无重叠的要求，a)最小移动的Group个数，b)不改变当前Group的顺序(无交叉线)
    def placement_group(self):
        # self.groups[9].assign_group_offset(sx=self.groups[9].lt.x - 300,
        #                                    sy=self.groups[9].lt.y,
        #                                    maps=self.maps)
        # self.update_related_groups(9)

        for layer_id in self.layer_info:
            if layer_id ==7:
                break
            overlap = self.calc_layer_group_overlap(layer_id)
            if overlap > 0:
                placement_dict = self.search_minimal_movement_policy(layer_id)
                print('update layer %d' % layer_id, placement_dict)
                for group_id in placement_dict['placement']:
                    update_sx = placement_dict['placement'][group_id][0]
                    update_sy = placement_dict['placement'][group_id][1]
                    self.groups[group_id].assign_group_offset(sx=update_sx,
                                                              sy=update_sy,
                                                              maps=self.maps)
                    self.update_related_groups(group_id)

        ins_render = Render(self.maps, self.groups)
        ins_render.render()

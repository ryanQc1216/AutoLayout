import os
import cv2
import json
import copy
import numpy as np
import itertools
import functools
import random
from src.node import Coordinate, Node, Group, get_default_text_size
from src.render import Render, MAX_VALUE, MIN_VALUE, SMALL_VALUE


def parsing_children_description(description):
    if 'children' not in description:
        return [], []
    return [x for x in description['children']], [x['id'] for x in description['children']]


class Layout:
    def __init__(self, description):
        # static param
        self.ratio_standard = 4/3
        self.ratio_score_weight = 0.9
        self.move_score_weight = 0.1
        self.max_loop_support = 999

        self.description = description
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
        start_x = MIN_VALUE
        end_x = MAX_VALUE
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

    def calc_placement_movement_score(self, original_bbox_info, update_bbox_info):
        total_width = 0
        move_dis = 0
        delta = 0.1
        for group_id in original_bbox_info:
            contain_num = len(self.groups[group_id].contains)
            dis = abs(original_bbox_info[group_id][0] - update_bbox_info[group_id][0])
            move_dis += dis*contain_num
            total_width += original_bbox_info[group_id][2] - original_bbox_info[group_id][0]
        score = 1 - min(1.0, (move_dis*delta/total_width))
        return score

    def calc_previous_placement_range(self, curr_layer_id):
        min_x, min_y = MAX_VALUE, MAX_VALUE
        max_x, max_y = MIN_VALUE, MIN_VALUE
        for layer_id in self.layer_info:
            group_ids = self.layer_info[layer_id]
            for group_id in group_ids:
                for node_id in self.groups[group_id].contains:
                    min_y = min(self.maps[node_id].absolute_coord.y, min_y)
                    max_y = max(self.maps[node_id].absolute_coord.y, max_y)
                    if layer_id <= curr_layer_id:
                        min_x = min(self.maps[node_id].absolute_coord.x, min_x)
                        max_x = max(self.maps[node_id].absolute_coord.x, max_x)
                        pass
        return min_x, min_y, max_x, max_y

    def calc_placement_ratio_score(self, update_bbox_info, previous_range):
        update_sx = previous_range[0]
        update_ex = previous_range[2]
        for group_id in update_bbox_info:
            update_sx = min(update_bbox_info[group_id][0], update_sx)
            update_ex = max(update_bbox_info[group_id][2], update_ex)
        width = update_ex - update_sx
        height = previous_range[3] - previous_range[1]
        ratio = width/height
        delta = 2.0
        score = 1 - abs(self.ratio_standard-ratio)/delta
        score = min(1.0, max(score, 0))
        return score

    def calc_all_placement_order(self, group_ids):
        group_num_thresh = 8
        if len(group_ids) <= group_num_thresh:
            all_placement_order = list(itertools.permutations(group_ids))
            return all_placement_order
        else:
            all_placement_order = [group_ids.copy()]
            indexes = [x for x in range(len(group_ids))]
            while len(all_placement_order) < self.max_loop_support:
                random.shuffle(indexes)
                placement = []
                for idx in indexes:
                    placement.append(group_ids[idx])
                all_placement_order.append(placement)
            return all_placement_order

    def search_movement_policy(self, layer_id):
        # group_ids is ordered from left to right
        group_ids = self.layer_info[layer_id].copy()
        original_bbox = {}
        for group_id in group_ids:
            original_bbox[group_id] = self.groups[group_id].get_bbox_as_list().copy()
        best_placement_info = {'placement': None, 'score': MIN_VALUE,
                               'movement_score': MIN_VALUE, 'ratio_score': MIN_VALUE}
        all_placement_order = self.calc_all_placement_order(group_ids)
        print('layer %d generate all placement order %d' % (layer_id, len(all_placement_order)))
        previous_range = self.calc_previous_placement_range(layer_id)
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
                movement_score = self.calc_placement_movement_score(original_bbox, already_placement)
                ratio_score = self.calc_placement_ratio_score(already_placement, previous_range)
                score = movement_score*self.move_score_weight + ratio_score*self.ratio_score_weight
                if score > best_placement_info['score']:
                    best_placement_info = {'placement': already_placement,
                                           'score': score,
                                           'movement_score': movement_score,
                                           'ratio_score': ratio_score}
        assert best_placement_info['placement'] is not None, 'Error in search_minimal_movement_policy!!'
        return best_placement_info


    # placement layer by layer
    # 1) Layer by Layer 的遍历Group
    # 2) 每次检查当前layer内部group重叠情况，以IOU作为得分 (如果默认没有重叠，则不改变原json顺序)
    # 3) 如果最小IOU仍然重叠，则尝试移动某些Group来满足无重叠的要求，a)最小移动的Group个数，b)不改变当前Group的顺序(无交叉线)
    def placement_group(self):
        for layer_id in self.layer_info:
            overlap = self.calc_layer_group_overlap(layer_id)
            if overlap > 0:
                placement_dict = self.search_movement_policy(layer_id)
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

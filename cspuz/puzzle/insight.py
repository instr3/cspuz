import sys
import subprocess

import cspuz
from cspuz import Solver, graph
from cspuz.grid_frame import BoolGridFrame
from cspuz.constraints import count_true, fold_and, fold_or
from cspuz.puzzle import util
from cspuz.generator import (generate_problem, count_non_default_values,
                             ArrayBuilder2D)
import time

DIRX = [-1, 0, 1, 0]
DIRY = [0, -1, 0, 1]


def solve_insight(problem, problem_title):
    height = len(problem)
    width = len(problem[0])
    # calculate n_regions
    n_regions = 0
    for num in problem_title:
        n_regions += num
    for y in range(height):
        for x in range(width):
            if (problem[y][x] in '+-|s23456789'):
                n_regions += 1
            if (problem[y][x] == 'O'):
                n_regions += 0.5
    n_regions = int(round(n_regions))

    # preprocess
    region_property = []
    cells_xy = []
    cells_xy_dict = set()
    solver = Solver()
    region_ids = solver.int_array((height, width), 0, n_regions - 1)
    is_problem = solver.bool_array((height, width))
    k_symbol_region = solver.int_var(0, n_regions - 1)

    def add_equality_constraint(region_id_a, region_id_b, is_equal, mappings_set):
        mapping_conditions = []
        for mapping in mappings_set:
            mapping_condition = []
            mapped_source = set()
            mapped_target = set()
            for ((x1, y1), (x2, y2)) in mapping:
                mapped_source.add((x1, y1))
                mapped_target.add((x2, y2))
                mapping_condition.append((region_ids[y1][x1] == region_id_a) == (region_ids[y2][x2] == region_id_b))
            for (x1, y1) in cells_xy:
                if ((x1, y1) not in mapped_source):
                    mapping_condition.append(~(region_ids[y1][x1] == region_id_a))
            for (x2, y2) in cells_xy:
                if ((x2, y2) not in mapped_target):
                    mapping_condition.append(~(region_ids[y2][x2] == region_id_b))
            mapping_conditions.append(fold_and(mapping_condition))
        if (is_equal):
            solver.ensure(fold_or(mapping_conditions))
        else:
            for mapping_condition in mapping_conditions:
                solver.ensure(~mapping_condition)
    def node_degree(x, y, degree, region_id=-1):
        neighbor_conditions = []
        for dir in range(4):
            xp = x + DIRX[dir]
            yp = y + DIRY[dir]
            if (xp, yp) in cells_xy_dict:
                if (region_id == -1):
                    neighbor_conditions.append(region_ids[yp][xp] == region_ids[y][x])
                else:
                    neighbor_conditions.append(region_ids[yp][xp] == region_id)
        if (region_id == -1):
            return count_true(neighbor_conditions) == degree
        else:
            return (region_ids[y][x] == region_id) & (count_true(neighbor_conditions) == degree)
    def count_degree(degree, region_id, cond=None):
        node_degree_conditions = []
        for (x, y) in cells_xy:
            if (cond is None):
                node_degree_conditions.append(node_degree(x, y, degree, region_id))
            else:
                node_degree_conditions.append(cond[y][x] & node_degree(x, y, degree, region_id))
        return count_true(node_degree_conditions)

    for num in problem_title:
        ref_region_id = len(region_property)
        region_property.append(['EQUAL', -1])
        for i in range(1, num):
            region_property.append(['EQUAL', ref_region_id])
    segment_pairing = False
    for y in range(height):
        for x in range(width):
            if (problem[y][x] == '.'):
                solver.ensure(~is_problem[y][x])
            else:
                cells_xy.append((x, y))
                cells_xy_dict.add((x, y))
                solver.ensure(is_problem[y][x])
                if (problem[y][x] == 'k'):
                    solver.ensure(region_ids[y][x] == k_symbol_region)
                elif (problem[y][x] in '|-+s'):
                    solver.ensure(region_ids[y][x] == len(region_property))
                    region_property.append(['SYMMETRY', problem[y][x]])
                elif (problem[y][x] in '23456789'):
                    solver.ensure(region_ids[y][x] == len(region_property))
                    region_property.append(['TREE', ord(problem[y][x]) - ord('0')])
                elif (problem[y][x] == 'O'):
                    if (segment_pairing):
                        segment_pairing = False
                    else:
                        segment_pairing = True
                        region_property.append(['SEGMENT'])


    assert(len(region_property) == n_regions)
    print(region_property)
    for region_id in range(n_regions):
        graph.active_vertices_connected(solver, (region_ids == region_id) & is_problem)
        solver.ensure(count_true((region_ids == region_id) & is_problem) > 0)
    mappings = set()
    translation_limit = max(width, height)
    self_mappings = [[set(), set()], [set(), set()]]
    for flip_x in [False, True]:
        for flip_y in [False, True]:
            for swap_xy in [False, True]:
                for translate_x in range(-translation_limit + 1, translation_limit):
                    for translate_y in range(-translation_limit + 1, translation_limit):
                        current_mapping = []
                        ok = False
                        for (x1, y1) in cells_xy:
                            x2 = x1 + translate_x
                            y2 = y1 + translate_y
                            if (swap_xy):
                                x2, y2 = y2, x2
                            if (flip_x):
                                x2 = width - 1 - x2
                            if (flip_y):
                                y2 = height - 1 - y2
                            if (x2, y2) in cells_xy_dict:
                                current_mapping.append(((x1, y1), (x2, y2)))
                                ok = True
                        if (ok):
                            current_mapping = tuple(current_mapping)
                            if (current_mapping not in mappings):
                                mappings.add(current_mapping)
                            is_self_mapping = False
                            mapped_source = set()
                            for (p1, _) in current_mapping:
                                mapped_source.add(p1)
                            for (_, p2) in current_mapping:
                                if (p2 in mapped_source):
                                    is_self_mapping = True
                                    break
                            if (is_self_mapping):
                                if (swap_xy == False):
                                    if (current_mapping not in self_mappings[flip_y][flip_x]):
                                        self_mappings[flip_y][flip_x].add(current_mapping)
                                        # print('self', flip_x, flip_y, current_mapping)
    for region_id in range(n_regions):
        if (region_property[region_id][0] == 'EQUAL'):
            val = region_property[region_id][1]
            if (val >= 0):
                ref_region_id = val
                add_equality_constraint(region_id, ref_region_id, True, mappings)
            elif (val == -1):
                for ref_region_id in range(region_id):
                    if (region_property[ref_region_id][0] == 'EQUAL' and
                        region_property[ref_region_id][1] == -1):
                        add_equality_constraint(region_id, ref_region_id, False, mappings)
        elif (region_property[region_id][0] == 'SYMMETRY'):
            val = region_property[region_id][1]
            if (val == '|'):
                add_equality_constraint(region_id, region_id, True, self_mappings[False][True])
                add_equality_constraint(region_id, region_id, False, self_mappings[True][False])
            elif (val == '-'):
                add_equality_constraint(region_id, region_id, False, self_mappings[False][True])
                add_equality_constraint(region_id, region_id, True, self_mappings[True][False])
            elif (val == '+'):
                add_equality_constraint(region_id, region_id, True, self_mappings[False][True])
                add_equality_constraint(region_id, region_id, True, self_mappings[True][False])
            elif (val == 's'):
                add_equality_constraint(region_id, region_id, True, self_mappings[True][True])
                add_equality_constraint(region_id, region_id, False, self_mappings[False][True])
                add_equality_constraint(region_id, region_id, False, self_mappings[True][False])
        elif (region_property[region_id][0] == 'TREE'):
            val = region_property[region_id][1]
            solver.ensure(count_degree(1, region_id) == val)
            deg_4 = count_degree(4, region_id)
            solver.ensure(count_degree(3, region_id) + deg_4 + deg_4 == val - 2)
        elif (region_property[region_id][0] == 'SEGMENT'):
            for (x, y) in cells_xy:
                if (problem[y][x] != 'O'):
                    solver.ensure((region_ids[y][x] == region_id).then(node_degree(x, y, 2, region_id)))
    for (x, y) in cells_xy:
        if (problem[y][x] == 'O'):
            cond = []
            for region_id in range(n_regions):
                if (region_property[region_id][0] == 'SEGMENT'):
                    cond.append((region_ids[y][x] == region_id) & node_degree(x, y, 1, region_id))
            solver.ensure(fold_or(cond))
    is_sat = solver.find_answer()
    return is_sat, region_ids

if __name__ == '__main__':
    start_time = time.time()
    problem_title = [2]
    problem = [
        'o+ooo.ooo|o',
        '.ooo...ooo.',
        '.ooo...ooo.',
        'ooooo.ooooo',
        'ooooo.ooooo',
    ]
    print(problem_title)
    print('\n'.join(problem))
    is_sat, answer = solve_insight(problem, problem_title)
    end_time = time.time()
    print('solved in', end_time - start_time, 'seconds')
    print('has answer:', is_sat)
    if is_sat:
        for y in range(len(problem)):
            for x in range(len(problem[0])):
                if (problem[y][x] == '.'):
                    print('.', end='')
                else:
                    print(answer[y][x].sol, end='')
            print()
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


def solve_insight(height, width, problem, region_property):
    solver = Solver()
    n_regions = len(region_property)
    region_ids = solver.int_array((height, width), 0, n_regions - 1)
    is_problem = solver.bool_array((height, width))
    for region_id in range(n_regions):
        graph.active_vertices_connected(solver, (region_ids == region_id) & is_problem)
        solver.ensure(count_true((region_ids == region_id) & is_problem) > 0)
    cells_xy = []
    cells_xy_dict = set()
    for y in range(height):
        for x in range(width):
            if (problem[y][x] == 'o'):
                solver.ensure(is_problem[y][x])
                cells_xy.append((x, y))
                cells_xy_dict.add((x, y))
            else:
                solver.ensure(~is_problem[y][x])
    mappings = set()
    translation_limit = max(width, height)
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
                                # print(current_mapping)
    def add_equality_constraint(region_id_a, region_id_b, is_equal):
        mapping_conditions = []
        for mapping in mappings:
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
    for region_id in range(n_regions):
        if (region_property[region_id] >= 0):
            ref_region_id = region_property[region_id]
            add_equality_constraint(region_id, ref_region_id, True)
        elif ((region_property[region_id]) == -1):
            for ref_region_id in range(region_id):
                if ((region_property[ref_region_id]) == -1):
                    add_equality_constraint(region_id, ref_region_id, False)


    is_sat = solver.find_answer()
    return is_sat, region_ids

if __name__ == '__main__':
    start_time = time.time()
    height = 5
    width = 6
    print('2 2')
    problem = [
        '..oo..',
        '..ooo.',
        '..oo..',
        '.ooooo',
        'oooooo',
    ]
    print('\n'.join(problem))
    is_sat, answer = solve_insight(height, width, problem, [-1, 0, -1, 2])
    end_time = time.time()
    print('solved in', end_time - start_time, 'seconds')
    print('has answer:', is_sat)
    if is_sat:
        for y in range(height):
            for x in range(width):
                if (problem[y][x] == '.'):
                    print('.', end='')
                else:
                    print(answer[y][x].sol, end='')
            print()
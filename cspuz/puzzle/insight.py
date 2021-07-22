import sys
import subprocess

import cspuz
from cspuz import Solver, graph
from cspuz.grid_frame import BoolGridFrame
from cspuz.constraints import count_true
from cspuz.puzzle import util
from cspuz.generator import (generate_problem, count_non_default_values,
                             ArrayBuilder2D)

DIRX = [-1, 0, 1, 0]
DIRY = [0, -1, 0, 1]

def solve_insight(height, width, problem, region_property):
    solver = Solver()
    n_regions = len(region_property)
    region_ids = solver.int_array((height, width), 0, n_regions - 1)
    is_root = solver.bool_array((height, width))
    transform_swap_xy = solver.bool_array(n_regions)
    transform_flip_x = solver.bool_array(n_regions)
    transform_flip_y = solver.bool_array(n_regions)
    cells_xy = []
    cells_xy_dict = set()
    for y in range(height):
        for x in range(width):
            if (problem[y][x] == 'o'):
                cells_xy.append((x, y))
                cells_xy_dict.add((x, y))
    ranks = solver.int_array((height, width), 0, 6 - 1)  # todo: fix me
    for (x, y) in cells_xy:
        less_ranks = []
        for dir in range(4):
            xp = x + DIRX[dir]
            yp = y + DIRY[dir]
            if ((xp, yp) in cells_xy_dict):
                less_ranks.append((ranks[yp, xp] < ranks[y, x]) & (region_ids[yp, xp] == region_ids[y, x]))
                if (dir < 2):
                    pass
                    # solver.ensure(ranks[yp, xp] != ranks[y, x])

        solver.ensure(count_true(less_ranks + [is_root[y, x]]) >= 1)
    for region_id in range(n_regions):
        is_root_list = []
        for (x, y) in cells_xy:
            is_root_list.append(is_root[y, x] & (region_ids[y, x] == region_id))
        solver.ensure(count_true(is_root_list) == 1)
    for (x, y) in cells_xy:
        solver.ensure(is_root[y, x].then(ranks[y, x] == 0))

    for region_id in range(n_regions):
        if (region_property[region_id] >= 0):
            ref_region_id = region_property[region_id]
            solver.ensure(count_true(region_ids == region_id) == count_true(region_ids == ref_region_id))
            for (x1, y1) in cells_xy:
                for (x2, y2) in cells_xy:
                    for flip_x in [False, True]:
                        for flip_y in [False, True]:
                            for swap_xy in [False, True]:
                                for dir in range(4):
                                    x1p = x1 + DIRX[dir]
                                    y1p = y1 + DIRY[dir]
                                    tdx = -DIRX[dir] if not flip_x else DIRX[dir]
                                    tdy = -DIRY[dir] if not flip_y else DIRY[dir]
                                    if (swap_xy):
                                        tdx, tdy = tdy, tdx
                                    x2p = x2 + tdx
                                    y2p = y2 + tdy
                                    rank_requirement = True
                                    if (x1p, y1p) in cells_xy_dict:
                                        req1 = region_ids[y1p][x1p] == region_id
                                    else:
                                        req1 = False
                                        rank_requirement = False
                                    if (x2p, y2p) in cells_xy_dict:
                                        req2 = region_ids[y2p][x2p] == ref_region_id
                                    else:
                                        req2 = False
                                        rank_requirement = False
                                    solver.ensure(((ranks[y1][x1] == ranks[y2][x2]) &
                                                   (region_ids[y1][x1] == region_id) &
                                                   (region_ids[y2][x2] == ref_region_id) &
                                                   (flip_x == transform_flip_x[region_id]) &
                                                   (flip_y == transform_flip_y[region_id]) &
                                                   (swap_xy == transform_swap_xy[region_id])
                                                   ).then(req1 == req2))
                                    if (rank_requirement):
                                        solver.ensure(((ranks[y1][x1] == ranks[y2][x2]) &
                                                       (region_ids[y1][x1] == region_id) &
                                                       (region_ids[y2][x2] == ref_region_id) &
                                                       req1 &
                                                       (flip_x == transform_flip_x[region_id]) &
                                                       (flip_y == transform_flip_y[region_id]) &
                                                       (swap_xy == transform_swap_xy[region_id])
                                                       ).then(ranks[y2p][x2p] == ranks[y1p][x1p]))
    is_sat = solver.find_answer()
    return is_sat, region_ids

if __name__ == '__main__':
    height = 5
    width = 6
    problem = [
        '..oo..',
        '..ooo.',
        '..oo..',
        '.ooooo',
        'oooooo',
    ]
    is_sat, answer = solve_insight(height, width, problem, [-1, 0, -1, 2])
    print('has answer:', is_sat)
    if is_sat:
        for y in range(height):
            for x in range(width):
                if (problem[y][x] == '.'):
                    print('.', end='\t')
                else:
                    print(answer[y][x].sol, end='\t')
            print('\n')
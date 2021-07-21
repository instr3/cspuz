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
    ranks = solver.int_array((height, width), 0, height * width - 1)
    is_root = solver.bool_array((height, width))
    cells_xy = []
    cells_xy_dict = set()
    for y in range(height):
        for x in range(width):
            if (problem[y][x] == 'o'):
                cells_xy.append((x, y))
                cells_xy_dict.add((x, y))
    for (x, y) in cells_xy:
        less_ranks = []
        for dir in range(4):
            xp = x + DIRX[dir]
            yp = y + DIRY[dir]
            if ((xp, yp) in cells_xy_dict):
                less_ranks.append((ranks[yp, xp] < ranks[y, x]) & (region_ids[yp, xp] == region_ids[y, x]))
                # if (dir < 2):
                #     solver.ensure(ranks[yp, xp] != ranks[y, x])

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
            for (x1, y1) in cells_xy:
                for (x2, y2) in cells_xy:
                    for dir in range(4):
                        x1p = x1 + DIRX[dir]
                        y1p = y1 + DIRY[dir]
                        x2p = x2 + DIRX[dir]
                        y2p = y2 + DIRY[dir]
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
                                       (region_ids[y2][x2] == ref_region_id)
                                       ).then(req1 == req2))
                        if (rank_requirement):
                            solver.ensure(((ranks[y1][x1] == ranks[y2][x2]) &
                                           (region_ids[y1][x1] == region_id) &
                                           (region_ids[y2][x2] == ref_region_id) &
                                           req1
                                           ).then(ranks[y2p][x2p] == ranks[y1p][x1p]))
    is_sat = solver.find_answer()
    return is_sat, region_ids

if __name__ == '__main__':
    height = 3
    width = 3
    problem = [
        'oo.',
        'ooo',
        '.o.'
    ]
    is_sat, answer = solve_insight(height, width, problem, [-1, 0])
    print('has answer:', is_sat)
    if is_sat:
        for y in range(height):
            for x in range(width):
                if (problem[y][x] == '.'):
                    print('.', end='\t')
                else:
                    print(answer[y][x].sol, end='\t')
            print('\n')
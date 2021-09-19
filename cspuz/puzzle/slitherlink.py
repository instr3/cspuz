import sys
import subprocess

import cspuz
from cspuz import Solver, graph
from cspuz.grid_frame import BoolGridFrame
from cspuz.constraints import count_true
from cspuz.puzzle import util
from cspuz.generator import (generate_problem, count_non_default_values,
                             ArrayBuilder2D)


def solve_slitherlink(height, width, problem):
    solver = Solver()
    grid_frame = BoolGridFrame(solver, height, width)
    solver.add_answer_key(grid_frame)
    graph.active_edges_single_cycle(solver, grid_frame)
    for y in range(height):
        for x in range(width):
            if problem[y][x] >= 0:
                solver.ensure(
                    count_true(grid_frame.cell_neighbors(y, x)) == problem[y]
                    [x])
    for answer in solver.find_answers():
        yield grid_frame


def generate_slitherlink(height, width, symmetry=False, verbose=False):
    def no_neighboring_zero(problem):
        for y in range(height):
            for x in range(width):
                if problem[y][x] != 0:
                    continue
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        y2 = y + dy
                        x2 = x + dx
                        if (dy, dx) != (
                                0, 0
                        ) and 0 <= y2 < height and 0 <= x2 < width and problem[
                                y2][x2] == 0:
                            return False
        return True

    generated = generate_problem(
        lambda problem: solve_slitherlink(height, width, problem),
        builder_pattern=ArrayBuilder2D(height,
                                       width,
                                       range(-1, 4),
                                       default=-1,
                                       symmetry=symmetry,
                                       disallow_adjacent=True),
        clue_penalty=lambda problem: count_non_default_values(
            problem, default=-1, weight=5),
        pretest=no_neighboring_zero,
        verbose=verbose)
    return generated


def _main():
    if len(sys.argv) == 1:
        # original example: http://pzv.jp/p.html?slither/4/4/dgdh2c7b
        height = 15
        width = 20
        problem = [
            '**2***02*21*12***3**',
            '2**30***2**3***33**3',
            '*3***1**1**1**1***3*',
            '*0***1***30***3***3*',
            '**32**13****01**31**',
            '1***2***3**1***2***2',
            '2***3***3**3***2***0',
            '*30**10**11**31**23*',
            '2***3***3**3***1***1',
            '2***2***1**3***1***2',
            '**03**13****32**01**',
            '*3***3***13***3***0*',
            '*1***3**3**1**3***3*',
            '3**23***2**2***03**0',
            '**3***13*22*20***0**',
        ]
        problem = [['*0123'.index(c) - 1 for c in line] for line in problem]
        for is_line in solve_slitherlink(height, width, problem):
            print(util.stringify_grid_frame(is_line))
    else:
        cspuz.config.solver_timeout = 1800.0
        height, width = map(int, sys.argv[1:])
        while True:
            try:
                problem = generate_slitherlink(height,
                                               width,
                                               symmetry=True,
                                               verbose=True)
                if problem is not None:
                    print(
                        util.stringify_array(problem, {
                            -1: '.',
                            0: '0',
                            1: '1',
                            2: '2',
                            3: '3'
                        }))
                    print(flush=True)
            except subprocess.TimeoutExpired:
                print('timeout', file=sys.stderr)


if __name__ == '__main__':
    _main()

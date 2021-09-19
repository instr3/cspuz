import sys
import subprocess

import cspuz
from cspuz import Solver, graph
from cspuz.grid_frame import BoolGridFrame
from cspuz.constraints import count_true, fold_or, fold_and
from cspuz.puzzle import util
from cspuz.generator import (generate_problem, count_non_default_values,
                             ArrayBuilder2D)

def ensure_not_solution(solver, height, width, grid_frame, solution):

    conds = []
    for y in range(height + 1):
        for x in range(width):
            if (solution[y * 2][x * 2 + 1] != 'x'):
                conds.append(grid_frame.horizontal[y][x])
            else:
                conds.append(~grid_frame.horizontal[y][x])
    for y in range(height):
        for x in range(width + 1):
            if (solution[y * 2 + 1][x * 2] != 'x'):
                conds.append(grid_frame.vertical[y][x])
            else:
                conds.append(~grid_frame.vertical[y][x])
    solver.ensure(~fold_and(conds))

def solve_slitherlink(height, width, problem, known_solution):
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
    if (known_solution is not None):
        ensure_not_solution(solver, height, width, grid_frame, known_solution)
    for answer in solver.find_answers(1):
        return True, grid_frame
    return False, grid_frame

def ensure_positive_solution(solver, height, width, problem, solution):
    for y in range(height):
        for x in range(width):
            cell_neighbors = (solution[y * 2][x * 2 + 1] != 'x') + (solution[y * 2 + 1][x * 2] != 'x') + \
                             (solution[y * 2 + 2][x * 2 + 1] != 'x') + (solution[y * 2 + 1][x * 2 + 2] != 'x')
            solver.ensure((problem[y][x] >= 0).then(
                cell_neighbors == problem[y][x]
            ))

def ensure_negative_solution(solver, height, width, problem, solution):
    conds = []
    for y in range(height):
        for x in range(width):
            cell_neighbors = (solution[y * 2][x * 2 + 1] != 'x') + (solution[y * 2 + 1][x * 2] != 'x') + \
                             (solution[y * 2 + 2][x * 2 + 1] != 'x') + (solution[y * 2 + 1][x * 2 + 2] != 'x')
            conds.append((problem[y][x] >= 0).then(
                cell_neighbors == problem[y][x]
            ))
    solver.ensure(count_true([~cond for cond in conds]) >= 50)

def give_slitherlink(height, width, solution, avoid_solutions):
    solver = Solver()
    problem = solver.int_array((height, width), -1, 3)
    solver.add_answer_key(problem)
    solver.ensure(count_true(problem >= 0) == 100)
    ensure_positive_solution(solver, height, width, problem, solution)
    for avoid_solution in avoid_solutions:
        ensure_negative_solution(solver, height, width, problem, avoid_solution)
    is_sat = solver.solve()
    for answer in solver.find_answers(2):
        return True, problem
    return False, problem

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


def give():
    solution = [
        '+x+x+-+-+x+x+x+x+-+-+-+-+x+x+-+-+-+-+x+x+',
        'x x | x | x x x | x x x | x | x x x | x x',
        '+-+-+x+-+x+x+x+-+x+-+x+-+x+-+x+-+x+-+x+-+',
        '| x x | x x x | x | | | x | x | | | x | |',
        '+x+-+x+-+x+x+x+-+-+x+x+-+-+x+x+x+-+x+-+x+',
        '| | | x | x x x x x | x x x x | x x | x |',
        '+-+x+-+x+-+-+-+-+x+-+x+x+-+-+x+x+x+x+-+x+',
        'x x x | x x x x | | x x | x | | x x x | |',
        '+x+x+-+x+-+x+x+-+x+-+x+-+x+x+-+x+-+-+-+x+',
        'x x | x | | x | x x | | x x x x | x x x |',
        '+x+x+-+-+x+x+x+-+-+x+x+x+x+-+-+x+-+x+x+-+',
        'x x x x x | x x x | | | x | x | x | x | x',
        '+-+-+x+x+-+x+x+x+-+x+x+x+-+x+x+-+-+x+-+x+',
        '| x | x | x x x | x | | | x x x x x | x x',
        '+x+-+x+x+-+x+x+x+-+-+x+-+x+-+-+-+-+x+-+x+',
        '| | x x x | x x x x x x x | x x x | x | x',
        '+x+-+x+x+-+x+x+x+-+x+-+-+x+-+x+x+x+-+-+x+',
        '| x | x | x x x | | | x | x | x x x x x x',
        '+-+x+-+x+-+x+x+-+x+x+x+-+x+x+-+-+-+x+-+-+',
        'x | x | x | x | x | | | x x x x x | | x |',
        '+x+x+x+-+x+-+x+-+x+x+x+-+x+-+-+x+x+-+x+x+',
        'x | x x | x | x | | | x | | x | x x x x |',
        '+x+-+x+-+x+-+x+-+x+x+-+x+-+x+-+x+x+x+x+x+',
        'x x | | x | x | x | x | x x | x x x x x |',
        '+-+-+x+x+x+-+x+x+-+x+-+x+x+x+-+x+-+-+x+-+',
        '| x x | x x | | | x | x x x x | | x | | x',
        '+-+x+x+-+x+-+x+x+-+x+x+-+-+x+-+x+-+x+-+x+',
        'x | x x | | x | x | | | x | | x x | x x x',
        '+-+x+-+x+-+x+x+-+x+x+-+x+-+x+-+x+-+x+x+x+',
        '| x | | x x x x | | x x | x x | | x x x x',
        '+-+-+x+-+-+-+-+-+x+-+-+-+x+x+x+-+x+x+x+x+',
    ]
    height = 15
    width = 20
    avoid_solutions = []
    while True:
        is_sat, problem = give_slitherlink(height, width, solution, avoid_solutions)
        print('has problem:', is_sat)
        if (not is_sat):
            break
        problem_formatted = []
        if is_sat:
            for y in range(height):
                problem_line = []
                for x in range(width):
                    if (problem[y][x].sol != -1):
                        print('%d' % problem[y][x].sol, end='')
                    else:
                        print(' ', end='')
                    problem_line.append(problem[y][x].sol)
                print('')
                problem_formatted.append(problem_line)
        is_sat, grid_frame = solve_slitherlink(height, width, problem_formatted, solution)
        print('has another solution:', is_sat)
        if (not is_sat):
            break
        if is_sat:
            avoid_solution = util.stringify_grid_frame(grid_frame)
            print(avoid_solution)
            avoid_solutions.append(avoid_solution.split('\n'))

if __name__ == '__main__':
    give()

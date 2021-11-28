from cspuz import Solver, graph
from cspuz.grid_frame import BoolGridFrame
from cspuz.constraints import count_true, fold_or, fold_and
from cspuz.puzzle import util
from cspuz.generator import (generate_problem, count_non_default_values,
                             ArrayBuilder2D)
DIR_X = [-1, 0, 1, 0]
DIR_Y = [0, -1, 0, 1]

class SokobanState:

    def __init__(self, height, width, cells_xy_dict, box_init_positions, solver):
        self.height = height
        self.width = width
        self.cells_xy_dict = cells_xy_dict
        self.is_p = solver.bool_array((height, width))
        self.box_init_positions = box_init_positions
        self.n_boxes = len(box_init_positions)
        self.is_b = [solver.bool_array((height, width)) for _ in range(self.n_boxes)]


    def is_empty(self, i, j):
        if ((i, j) not in self.cells_xy_dict):
            return False
        conds = [self.is_p[i, j]]
        for b in range(self.n_boxes):
            conds.append(self.is_b[b][i, j])
        return ~fold_or(conds)


def ensure_transition(state1: SokobanState, state2: SokobanState, solver):
    cells_xy_dict = state1.cells_xy_dict
    possible_moves = []
    n_boxes = state1.n_boxes
    for (i, j) in cells_xy_dict:
        for dir in range(4):
            next_i = i + DIR_X[dir]
            next_j = j + DIR_Y[dir]
            if ((next_i, next_j) not in cells_xy_dict):
                continue
            cond = [state1.is_p[i, j], state1.is_empty(next_i, next_j),
                state2.is_p[next_i, next_j], state2.is_empty(i, j)]
            for (x, y) in cells_xy_dict:
                for b in range(n_boxes):
                    cond.append(state1.is_b[b][x, y] == state2.is_b[b][x, y])
            possible_moves.append(fold_and(cond))
            next_next_i = next_i + DIR_X[dir]
            next_next_j = next_j + DIR_Y[dir]
            if ((next_next_i, next_next_j) not in cells_xy_dict):
                continue
            for b in range(n_boxes):
                cond = [state1.is_p[i, j], state1.is_b[b][next_i, next_j], state1.is_empty(next_next_i, next_next_j),
                        state2.is_p[next_i, next_j], state2.is_b[b][next_next_i, next_next_j], state2.is_empty(i, j)]
                for (x, y) in cells_xy_dict:
                    if ((x, y) == (next_i, next_j) or (x, y) == (next_next_i, next_next_j)):
                        continue
                    for b2 in range(n_boxes):
                        cond.append(state1.is_b[b2][x, y] == state2.is_b[b2][x, y])
                possible_moves.append(fold_and(cond))
    cond = []
    for (x, y) in cells_xy_dict:
        for b in range(n_boxes):
            cond.append(state1.is_b[b][x, y] == state2.is_b[b][x, y])
        cond.append(state1.is_p[x, y] == state2.is_p[x, y])
    possible_moves.append(fold_and(cond))
    solver.ensure(fold_or(possible_moves))

def ensure_long_term_dependency(solver, states):
    cells_xy_dict = states[0].cells_xy_dict
    dist = {}
    for c1 in cells_xy_dict:
        for c2 in cells_xy_dict:
            dist[(c1, c2)] = 99999999
        dist[(c1, c1)] = 0
        for dir in range(4):
            c2 = (c1[0] + DIR_X[dir], c1[1] + DIR_Y[dir])
            if (c2 in cells_xy_dict):
                dist[(c1, c2)] = 1
    for ck in cells_xy_dict:
        for c1 in cells_xy_dict:
            for c2 in cells_xy_dict:
                if (dist[(c1, c2)] > dist[(c1, ck)] + dist[(ck, c2)]):
                    dist[(c1, c2)] = dist[(c1, ck)] + dist[(ck, c2)]

    for c1 in cells_xy_dict:
        for c2 in cells_xy_dict:
            min_duration = dist[(c1, c2)]
            for k in range(min_duration):
                for t in range(len(states) - k):
                    solver.ensure(~(states[t].is_p[c1[0], c1[1]] & states[t + k].is_p[c2[0], c2[1]]))
                    for b in range(states[t].n_boxes):
                        solver.ensure(~(states[t].is_b[b][c1[0], c1[1]] & states[t + k].is_b[b][c2[0], c2[1]]))


def solver_sokoban(height, width, problem, max_steps):
    solver = Solver()
    cells_xy_dict = set()
    box_init_positions = []
    for i in range(height):
        for j in range(width):
            if (problem[i][j] != '#'):
                cells_xy_dict.add((i, j))
            if (problem[i][j] in '*$'):
                box_init_positions.append((i, j))
    n_boxes = len(box_init_positions)
    states = [SokobanState(height, width, cells_xy_dict, box_init_positions, solver) for _ in range(max_steps)]
    for t, state in enumerate(states):
        for i in range(height):
            for j in range(width):
                conds = [state.is_p[i, j]]
                for b in range(n_boxes):
                    conds.append(state.is_b[b][i, j])
                if (problem[i][j] == '#'):
                    for cond in conds:
                        solver.ensure(~cond)
                else:
                    solver.ensure(count_true(conds) <= 1)
        solver.ensure(count_true(state.is_p) == 1)
        for b in range(n_boxes):
            solver.ensure(count_true(state.is_b[b]) == 1)
        if (t == 0):
            for i in range(height):
                for j in range(width):
                    solver.ensure(state.is_p[i, j] == (problem[i][j] in '@+'))
                    for b in range(n_boxes):
                        solver.ensure(state.is_b[b][i, j] == (box_init_positions[b] == (i, j)))
        else:
            ensure_transition(states[t - 1], states[t], solver)
        if (t + 1 == max_steps):
            for i in range(height):
                for j in range(width):
                    conds = []
                    for b in range(n_boxes):
                        conds.append(state.is_b[b][i, j])
                    if (problem[i][j] in '*.+'):
                        solver.ensure(fold_or(conds))
                    else:
                        for cond in conds:
                            solver.ensure(~cond)
    # ensure_long_term_dependency(solver, states)
    is_sat = solver.find_answer()
    return is_sat, states

def main():
    max_steps = 40
    problem_easy = [
        '######',
        '# .###',
        '#  ###',
        '#*@  #',
        '#  $ #',
        '#  ###',
        '######',
    ]
    problem_mid = [
        '#########',
        '# @ #   #',
        '# $ $   #',
        '##$### ##',
        '#  ...  #',
        '#   #   #',
        '######  #',
        '#########',
    ]
    problem_hard = [
        '###########',
        '#    ######',
        '#  # $ ####',
        '#  $ @ ####',
        '## ## #####',
        '#  #......#',
        '# $ $ $ $ #',
        '##   ######',
        '###########',
    ]
    problem = problem_mid
    height, width = len(problem), len(problem[0])
    is_sat, states = solver_sokoban(height, width, problem, max_steps)
    print('has answer:', is_sat)
    if is_sat:
        for t in range(max_steps):
            print('Step %d' % t)
            for i in range(height):
                for j in range(width):
                    is_target = 1 if problem[i][j] in '.*+' else 0
                    if (problem[i][j] == '#'):
                        print('#', end='')
                    elif (states[t].is_p[i, j].sol):
                        print('@+'[is_target], end='')
                    else:
                        has_box = False
                        for b in range(states[0].n_boxes):
                            if (states[t].is_b[b][i, j].sol):
                                has_box = True
                                break
                        print('$*'[is_target] if has_box else ' .'[is_target], end='')
                print()
            print()

if __name__ == '__main__':
    main()
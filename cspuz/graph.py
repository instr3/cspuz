from typing import (Iterator, List, Optional, Sequence, Tuple, Union, cast,
                    overload)

from .array import (Array2D, BoolArray1D, BoolArray2D, IntArray1D, IntArray2D,
                    _infer_shape)
from .constraints import (IntExpr, BoolExpr, Op, count_true, then)
from .expr import BoolExprLike, IntExprLike
from .grid_frame import BoolGridFrame
from .configuration import config
from .solver import Solver


class Graph(object):
    num_vertices: int
    edges: List[Tuple[int, int]]
    incident_edges: List[List[Tuple[int, int]]]

    def __init__(self, num_vertices):
        self.num_vertices = num_vertices
        self.edges = []
        self.incident_edges = [[] for i in range(self.num_vertices)]

    def __len__(self) -> int:
        return len(self.edges)

    def __iter__(self) -> Iterator[Tuple[int, int]]:
        return iter(self.edges)

    def __getitem__(self, item: int) -> Tuple[int, int]:
        return self.edges[item]

    def add_edge(self, i: int, j: int):
        edge_id = len(self.edges)
        self.edges.append((i, j))
        self.incident_edges[i].append((j, edge_id))
        self.incident_edges[j].append((i, edge_id))


def _get_array_shape_2d(array):
    if isinstance(array, Array2D):
        return array.shape
    else:
        shape = _infer_shape(array)
        return shape


def _grid_graph(height: int, width: int) -> Graph:
    graph = Graph(height * width)
    for y in range(height):
        for x in range(width):
            if x < width - 1:
                graph.add_edge(y * width + x, y * width + (x + 1))
            if y < height - 1:
                graph.add_edge(y * width + x, (y + 1) * width + x)
    return graph


def _from_grid_frame(grid_frame):
    height = grid_frame.height
    width = grid_frame.width
    edges = []
    graph = Graph((height + 1) * (width + 1))
    for y in range(height + 1):
        for x in range(width + 1):
            if y != height:
                edges.append(grid_frame[y * 2 + 1, x * 2])
                graph.add_edge(y * (width + 1) + x, (y + 1) * (width + 1) + x)
            if x != width:
                edges.append(grid_frame[y * 2, x * 2 + 1])
                graph.add_edge(y * (width + 1) + x, y * (width + 1) + (x + 1))
    return edges, graph


def _active_vertices_connected(solver: Solver,
                               is_active: Sequence[BoolExprLike],
                               graph: Graph,
                               acyclic: bool = False,
                               use_graph_primitive: Optional[bool] = None):
    if use_graph_primitive is None:
        use_graph_primitive = config.use_graph_primitive
    if use_graph_primitive and not acyclic:
        solver.ensure(
            BoolExpr(
                Op.GRAPH_ACTIVE_VERTICES_CONNECTED,
                [graph.num_vertices, len(graph)] +
                list(is_active) +  # type: ignore
                sum([[x, y] for x, y in graph.edges], [])))
        return

    n = graph.num_vertices

    ranks = solver.int_array(n, 0, n - 1)
    is_root = solver.bool_array(n)

    for i in range(n):
        less_ranks = [((ranks[j] < ranks[i]) & is_active[j])
                      for j, _ in graph.incident_edges[i]]
        if acyclic:
            for j, _ in graph.incident_edges[i]:
                if i < j:
                    solver.ensure(ranks[j] != ranks[i])
            solver.ensure(
                then(is_active[i],
                     count_true(less_ranks + [is_root[i]]) == 1))
        else:
            solver.ensure(
                then(is_active[i],
                     count_true(less_ranks + [is_root[i]]) >= 1))
    solver.ensure(count_true(is_root) <= 1)


@overload
def active_vertices_connected(solver: Solver,
                              is_active: Union[Sequence[BoolExprLike],
                                               BoolArray1D],
                              graph: Graph,
                              *,
                              acyclic: bool = False,
                              use_graph_primitive: Optional[bool] = None):
    ...


@overload
def active_vertices_connected(solver: Solver,
                              is_active: BoolArray2D,
                              *,
                              acyclic: bool = False,
                              use_graph_primitive: Optional[bool] = None):
    ...


def active_vertices_connected(
    solver: Solver,
    is_active: Union[Sequence[BoolExprLike], BoolArray1D, BoolArray2D],
    graph: Optional[Graph] = None,
    *,
    acyclic: bool = False,
    use_graph_primitive: Optional[bool] = None,
):
    if graph is None:
        if not isinstance(is_active, BoolArray2D):
            raise TypeError(
                '\'is_active\' should be a BoolArray2D if graph is not '
                'specified')
        height, width = is_active.shape
        is_active2: Sequence[BoolExprLike] = is_active.flatten().data
        graph2 = _grid_graph(height, width)
    else:
        if isinstance(is_active, BoolArray2D):
            raise TypeError(
                '\'is_active\' should be sequence-like if graph is specified')
        elif isinstance(is_active, BoolArray1D):
            is_active2 = is_active.data
        else:
            is_active2 = is_active
        graph2 = graph

    _active_vertices_connected(solver,
                               is_active2,
                               graph2,
                               acyclic=acyclic,
                               use_graph_primitive=use_graph_primitive)


@overload
def active_vertices_not_adjacent(solver: Solver,
                                 is_active: Union[Sequence[BoolExprLike],
                                                  BoolArray1D], graph: Graph):
    ...


@overload
def active_vertices_not_adjacent(solver: Solver, is_active: BoolArray2D):
    ...


def active_vertices_not_adjacent(solver: Solver,
                                 is_active: Union[Sequence[BoolExprLike],
                                                  BoolArray1D, BoolArray2D],
                                 graph: Optional[Graph] = None):
    if graph is None:
        if not isinstance(is_active, BoolArray2D):
            raise TypeError(
                '\'is_active\' should be a BoolArray2D if graph is not '
                'specified')
        solver.ensure(~(is_active[1:, :] & is_active[:-1, :]))
        solver.ensure(~(is_active[:, 1:] & is_active[:, :-1]))
    else:
        if isinstance(is_active, BoolArray2D):
            raise TypeError(
                '\'is_active\' should be sequence-like if graph is specified')
        for i, j in graph:
            solver.ensure(~(is_active[i] & is_active[j]))


@overload
def active_vertices_not_adjacent_and_not_segmenting(solver: Solver,
                                                    is_active: BoolArray1D,
                                                    graph: Graph):
    ...


@overload
def active_vertices_not_adjacent_and_not_segmenting(solver: Solver,
                                                    is_active: BoolArray2D):
    ...


# TODO: support Sequence[BoolExprLike]
def active_vertices_not_adjacent_and_not_segmenting(
        solver: Solver,
        is_active: Union[BoolArray1D, BoolArray2D],
        graph: Optional[Graph] = None):
    if graph is None:
        if not isinstance(is_active, BoolArray2D):
            raise TypeError(
                '\'is_active\' should be a BoolArray2D if graph is not '
                'specified')
        active_vertices_not_adjacent(solver, is_active)
        height, width = is_active.shape
        ranks = solver.int_array((height, width), 0, (height * width - 1) // 2)
        for y in range(height):
            for x in range(width):
                less_ranks = []
                nonzero = False
                for dy in [-1, 1]:
                    for dx in [-1, 1]:
                        y2 = y + dy
                        x2 = x + dx
                        if 0 <= y2 < height and 0 <= x2 < width:
                            less_ranks.append((ranks[y2, x2] < ranks[y, x])
                                              & is_active[y2, x2])
                            if (y2, x2) < (y, x):
                                solver.ensure(ranks[y2, x2] != ranks[y, x])
                        else:
                            nonzero = True
                solver.ensure(is_active[y, x].then(
                    count_true(less_ranks) <= (0 if nonzero else 1)))
    else:
        if isinstance(is_active, BoolArray2D):
            raise TypeError(
                '\'is_active\' should be sequence-like if graph is specified')
        active_vertices_not_adjacent(solver, is_active, graph)
        active_vertices_connected(solver, ~is_active, graph)


def active_edges_acyclic(solver: Solver,
                         is_active_edge: Union[Sequence[BoolExprLike],
                                               BoolArray1D], graph: Graph):
    n = graph.num_vertices

    ranks = solver.int_array(n, 0, n - 1)

    for i in range(n):
        less_ranks = []
        for j, e in graph.incident_edges[i]:
            less_ranks.append((ranks[j] < ranks[i]) & is_active_edge[e])
            if i < j:
                solver.ensure(ranks[i] != ranks[j])
        solver.ensure(count_true(less_ranks) <= 1)


def _division_connected(solver: Solver,
                        division: Union[Sequence[IntExprLike], IntArray1D],
                        num_regions: int,
                        graph: Graph,
                        roots: Optional[Sequence[Optional[int]]] = None,
                        allow_empty_group: bool = False,
                        use_graph_primitive: Optional[bool] = None):
    if use_graph_primitive is None:
        use_graph_primitive = config.use_graph_primitive

    n = graph.num_vertices
    m = len(graph)

    if use_graph_primitive:
        for i in range(num_regions):
            region = solver.bool_array(n)
            solver.ensure(region == (division == i))
            _active_vertices_connected(solver,
                                       region.data,
                                       graph,
                                       use_graph_primitive=True)

            if not allow_empty_group:
                solver.ensure(count_true(region) >= 1)

        if roots is not None:
            for i, r in enumerate(roots):
                if r is not None:
                    if not isinstance(r, int):
                        raise TypeError(
                            'each element in \'roots\' must be \'int\'')
                    solver.ensure(division[r] == i)
        return

    rank = solver.int_array(n, 0, n - 1)
    is_root = solver.bool_array(n)
    spanning_forest = solver.bool_array(m)

    for i in range(n):
        less_ranks = []
        for j, e in graph.incident_edges[i]:
            less_ranks.append(spanning_forest[e] & (rank[i] > rank[j]))
            if i < j:
                solver.ensure(
                    spanning_forest[e].then((division[i] == division[j])
                                            & (rank[i] != rank[j])))
        solver.ensure(count_true(less_ranks) == is_root[i].cond(0, 1))
    for i in range(num_regions):
        if allow_empty_group:
            solver.ensure(
                count_true([r & (n == i)
                            for r, n in zip(is_root, division)]) <= 1)
        else:
            solver.ensure(
                count_true([r & (n == i)
                            for r, n in zip(is_root, division)]) == 1)
    if roots is not None:
        for i, r in enumerate(roots):
            if r is not None:
                solver.ensure(division[r] == i)
                solver.ensure(is_root[r])


@overload
def division_connected(solver: Solver,
                       division: Union[Sequence[IntExprLike], IntArray1D],
                       num_regions: int,
                       graph: Graph = None,
                       *,
                       roots: Optional[Sequence[Optional[int]]] = None,
                       allow_empty_group=False):
    ...


@overload
def division_connected(solver: Solver,
                       division: IntArray2D,
                       num_regions: int,
                       *,
                       roots: Optional[Sequence[Optional[int]]] = None,
                       allow_empty_group=False):
    ...


def division_connected(solver: Solver,
                       division: Union[Sequence[IntExprLike], IntArray1D,
                                       IntArray2D],
                       num_regions: int,
                       graph: Optional[Graph] = None,
                       *,
                       roots: Union[Sequence[Optional[int]],
                                    Sequence[Optional[Tuple[int,
                                                            int]]]] = None,
                       allow_empty_group=False):
    if graph is None:
        if not isinstance(division, IntArray2D):
            raise TypeError(
                '\'division\' should be a IntArray2D if graph is not '
                'specified')
        height, width = division.shape
        if roots is None:
            roots_conv: Optional[List[Optional[int]]] = None
        else:
            roots_conv = []
            for a in roots:
                if a is None:
                    roots_conv.append(a)
                else:
                    if isinstance(a, int):
                        raise TypeError(
                            'each element in \'roots\' must be tuple (y, x) '
                            'if \'division\' is an IntArray2D')
                    y, x = a
                    roots_conv.append(y * width + x)
        _division_connected(solver,
                            division.flatten(),
                            num_regions,
                            _grid_graph(height, width),
                            roots=roots_conv,
                            allow_empty_group=allow_empty_group)
    else:
        if isinstance(division, IntArray2D):
            raise TypeError(
                '\'division\' should be sequence-like if graph is specified')
        _division_connected(solver,
                            division,
                            num_regions,
                            graph,
                            roots=cast('Union[Sequence[Optional[int]]]',
                                       roots),
                            allow_empty_group=allow_empty_group)


def _division_connected_variable_groups(
    solver: Solver,
    graph: Graph,
    group_size: Union[None, IntExprLike,
                      Sequence[Optional[IntExprLike]]] = None
) -> IntArray1D:
    n = graph.num_vertices
    m = len(graph)

    group_id = solver.int_array(n, 0, n - 1)
    rank = solver.int_array(n, 0, n - 1)
    is_root = solver.bool_array(n)
    is_active_edge = solver.bool_array(m)
    solver.ensure(is_root == (rank == 0))

    for i in range(n):
        solver.ensure(is_root[i].then(group_id[i] == i))
        for j, e in graph.incident_edges[i]:
            solver.ensure(is_active_edge[e].then(rank[j] != rank[i]))
        solver.ensure(
            count_true([
                is_active_edge[e] & (rank[j] < rank[i])
                for j, e in graph.incident_edges[i]
            ]) == is_root[i].cond(0, 1))
    for i, (u, v) in enumerate(graph):
        solver.ensure(is_active_edge[i].then(group_id[u] == group_id[v]))
    if group_size is not None:
        downstream_size = solver.int_array(n, 1, n)
        total_size = solver.int_array(n, 1, n)
        solver.ensure(downstream_size <= total_size)
        solver.ensure(is_root.then(downstream_size == total_size))
        for i in range(n):
            solver.ensure(
                sum([(is_active_edge[e]
                      & (rank[j] > rank[i])).cond(downstream_size[j], 0)
                     for j, e in graph.incident_edges[i]]) +
                1 == downstream_size[i])

            if isinstance(group_size, (int, IntExpr)):
                s: Optional[IntExprLike] = group_size
            else:
                gi = group_size[i]
                if gi is not None and not isinstance(gi, (int, IntExpr)):
                    raise TypeError(
                        'invalid type for element of \'group_size\'')
                s = gi
            if s is not None:
                solver.ensure(total_size[i] == s)
        if not isinstance(group_size, (int, IntExpr)):
            for i, (u, v) in enumerate(graph):
                s = total_size[u]
                t = total_size[v]
                solver.ensure(is_active_edge[i].then(s == t))
    return group_id


@overload
def division_connected_variable_groups(
    solver: Solver,
    *,
    shape: Optional[Tuple[int, int]] = None,
    group_size: Union[None, IntExprLike, IntArray2D,
                      Sequence[Sequence[Optional[IntExprLike]]]] = None):
    ...


@overload
def division_connected_variable_groups(
    solver: Solver,
    *,
    graph: Graph,
    group_size: Union[None, IntExprLike, IntArray1D,
                      Sequence[Optional[IntExprLike]]] = None):
    ...


def division_connected_variable_groups(
    solver: Solver,
    *,
    graph: Optional[Graph] = None,
    shape: Optional[Tuple[int, int]] = None,
    group_size: Union[None, IntExprLike, IntArray1D,
                      Sequence[Optional[IntExprLike]], IntArray2D,
                      Sequence[Sequence[Optional[IntExprLike]]]] = None):
    if graph is None:
        if shape is None:
            if group_size is None:
                raise ValueError('grid size cannot be inferred')
            shape = _get_array_shape_2d(group_size)
        if group_size is None:
            group_size_converted: Union[None, IntExprLike,
                                        Sequence[Optional[IntExprLike]]] = None
        elif isinstance(group_size, (int, IntExpr)):
            group_size_converted = group_size
        elif isinstance(group_size, IntArray2D):
            group_size_converted = group_size.flatten().data
        else:
            group_size_converted = []
            for row in group_size:
                if row is None or isinstance(row, (int, IntExpr)):
                    raise TypeError('invalid type for \'group_size\'')
                group_size_converted += row
        height, width = shape
        group_id_flat = _division_connected_variable_groups(
            solver,
            _grid_graph(height, width),
            group_size=group_size_converted)
        return group_id_flat.reshape(shape)
    else:
        if shape is not None:
            raise ValueError(
                '`graph` and `shape` cannot be specified at the same time')
        return _division_connected_variable_groups(
            solver, graph, group_size=group_size)  # type: ignore


def _active_edges_single_cycle(solver: Solver,
                               is_active_edge: Sequence[BoolExprLike],
                               graph: Graph,
                               use_graph_primitive: Optional[bool] = None):
    if use_graph_primitive is None:
        use_graph_primitive = config.use_graph_primitive
    n = graph.num_vertices

    is_passed = solver.bool_array(n)

    if use_graph_primitive:
        for i in range(n):
            degree = count_true(
                [is_active_edge[e] for j, e in graph.incident_edges[i]])
            solver.ensure(degree == is_passed[i].cond(2, 0))
        edge_graph = set()
        for v in range(n):
            for i in range(len(graph.incident_edges[v])):
                for j in range(i):
                    x = graph.incident_edges[v][i][1]
                    y = graph.incident_edges[v][j][1]
                    if x < y:
                        edge_graph.add((x, y))
                    else:
                        edge_graph.add((y, x))
        solver.ensure(
            BoolExpr(
                Op.GRAPH_ACTIVE_VERTICES_CONNECTED,
                [len(graph), len(edge_graph)] +
                list(is_active_edge) +  # type: ignore
                sum([[x, y] for x, y in edge_graph], [])))
    else:
        rank = solver.int_array(n, 0, n - 1)
        is_root = solver.bool_array(n)

        for i in range(n):
            degree = count_true(
                [is_active_edge[e] for j, e in graph.incident_edges[i]])
            solver.ensure(degree == is_passed[i].cond(2, 0))
            solver.ensure(is_passed[i].then(
                count_true([
                    is_active_edge[e] & (rank[j] >= rank[i])
                    for j, e in graph.incident_edges[i]
                ]) <= is_root[i].cond(2, 1)))
        solver.ensure(count_true(is_root) == 1)
    return is_passed


@overload
def active_edges_single_cycle(solver: Solver,
                              is_active_edge: BoolGridFrame,
                              *,
                              use_graph_primitive: Optional[bool] = None):
    ...


@overload
def active_edges_single_cycle(solver: Solver,
                              is_active_edge: Union[Sequence[BoolExprLike],
                                                    BoolArray1D],
                              graph: Graph,
                              *,
                              use_graph_primitive: Optional[bool] = None):
    ...


def active_edges_single_cycle(solver: Solver,
                              is_active_edge: Union[BoolGridFrame,
                                                    Sequence[BoolExprLike],
                                                    BoolArray1D],
                              graph: Optional[Graph] = None,
                              *,
                              use_graph_primitive: Optional[bool] = None):
    if graph is None:
        if not isinstance(is_active_edge, BoolGridFrame):
            raise TypeError(
                '`is_active_edge` should be a BoolGridFrame if graph is not '
                'specified')
        edges, graph = _from_grid_frame(is_active_edge)
        is_passed_flat = _active_edges_single_cycle(
            solver, edges, graph, use_graph_primitive=use_graph_primitive)
        return is_passed_flat.reshape(
            (is_active_edge.height + 1, is_active_edge.width + 1))
    else:
        if isinstance(is_active_edge, BoolGridFrame):
            raise TypeError(
                '\'is_active_edge\' should be sequence-like if graph is '
                'specified')
        if isinstance(is_active_edge, BoolArray1D):
            is_active_edge = is_active_edge.data
        return _active_edges_single_cycle(
            solver,
            is_active_edge,
            graph,
            use_graph_primitive=use_graph_primitive)

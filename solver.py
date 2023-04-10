"""Solve for a bracelet pattern matching a given set of coordinates.

Example here is the serpinski triangle, with an implied triangular start.
"""

from dataclasses import dataclass
from dataclasses import field
from typing import Union
import z3


@dataclass
class KnotNode:
    i: int
    j: int
    enter_left: z3.Int
    enter_right: z3.Int
    exit_left: z3.Int
    exit_right: z3.Int
    knot: z3.Int
    color: z3.Int

    def id(self):
        return (self.i, self.j)


@dataclass
class EdgeNode:
    i: int
    j: int
    enter_and_exit: z3.Int

    @property
    def exit_left(self):
        return self.enter_and_exit

    @property
    def exit_right(self):
        return self.enter_and_exit

    @property
    def enter_left(self):
        return self.enter_and_exit

    @property
    def enter_right(self):
        return self.enter_and_exit

    def id(self):
        return (self.i, self.j)


@dataclass
class InitialStringNode:
    i: int
    j: int
    # initial strings have only one allowed exit direction
    # depending on the parity
    exit: z3.Int
    color: z3.Int

    @property
    def exit_left(self):
        return self.exit

    @property
    def exit_right(self):
        return self.exit

    def id(self):
        return (self.i, self.j)


@dataclass
class Grid:
    width: int
    height: int
    nodes: dict[tuple[int, int], Union[KnotNode, EdgeNode, InitialStringNode]] = field(
        default_factory=dict
    )
    knot_nodes: dict[tuple[int, int], KnotNode] = field(default_factory=dict)
    edge_nodes: dict[tuple[int, int], EdgeNode] = field(default_factory=dict)
    string_nodes: dict[tuple[int, int], InitialStringNode] = field(default_factory=dict)

    def add(self, node):
        assert isinstance(node, Union[KnotNode, EdgeNode, InitialStringNode])
        self.nodes[node.id()] = node
        match node:
            case KnotNode():
                self.knot_nodes[node.id()] = node
            case EdgeNode():
                self.edge_nodes[node.id()] = node
            case InitialStringNode():
                self.string_nodes[node.id()] = node

    def upper_left(self, i, j):
        if i == 1:
            return self.nodes[(i-1, j-1)]
        return self.nodes[(i-2, j-2)}

    def upper_right(self, i, j):
        if i == 1:
            return self.nodes[(i-1, j+1)]
        return self.nodes[(i-2, j+2)]

    def knot_at(self, i, j):
        """Returns true if there is a knot at (i, j) in the grid."""
        return (i % 4 == 1 and j % 4 == 2) or (i % 4 == 3 and j % 4 == 0)


def setup_grid(num_strings: int, num_rows: int):
    assert num_strings % 2 == 0, "Need even num_strings"

    grid = Grid(
        # last allowed index is a right edge
        width=2 * num_strings + 1,
        height=2 * num_rows,
    )
    for j in range(num_strings):
        grid.add(
            InitialStringNode(
                i=0,
                j=2 * j + 1,
                exit=z3.Int(f"initial_string_exit_{j}"),
                color=z3.Int(f"initial_string_color_{j}"),
            )
        )

    for i in range(grid.height):
        if i % 4 == 3:
            # left edge node
            grid.add(
                EdgeNode(
                    i=i,
                    j=0,
                    enter_and_exit=z3.Int(f"left_edge_{j}"),
                )
            )
            # right edge node
            grid.add(
                EdgeNode(
                    i=i,
                    # 1 past the column index of the last initial string
                    j=2 * num_strings,
                    enter_and_exit=z3.Int(f"right_edge_{j}"),
                )
            )

        # knot nodes
        for j in range(grid.width):
            if grid.knot_at(i, j):
                grid.add(
                    KnotNode(
                        i=i,
                        j=j,
                        enter_left=z3.Int(f"enter_left_{i}_{j}"),
                        enter_right=z3.Int(f"enter_right_{i}_{j}"),
                        exit_left=z3.Int(f"exit_left_{i}_{j}"),
                        exit_right=z3.Int(f"exit_right_{i}_{j}"),
                        knot=z3.Int(f"knot_{i}_{j}"),
                        color=z3.Int(f"color_{i}_{j}"),
                    )
                )

    return grid.nodes


def setup_constraints(grid: Grid, colors: str):
    constraints = []
    colors = dict(enumerate(colors))
    num_colors = len(colors)

    for node_id, knot_node in grid.knot_nodes.items():
        # enter_left == upper_left.exit_right
        constraints.append(
            knot_node.enter_left == grid.upper_left(*node_id).exit_right
        )

        # enter_right == upper_right.exit_left
        constraints.append(
            knot_node.enter_right == grid.upper_right(*node_id).exit_left
        )

        # knot constraints:
        # knot is exactly one of 0, 1, 2, 3.

        # if knot == 0 (🡦), then exit_left == enter_right, exit_right = enter_left
        # and color = enter_left
        # if knot == 1 (🡧), then exit_left == enter_right, exit_right = enter_left
        # and color = enter_right
        # if knot == 2 (⤸), then exit_left == enter_left, exit_right = enter_right
        # and color = enter_left
        # if knot == 3 (⤹), then exit_right == enter_right, exit_left = enter_left
        # and color = enter_right

        # grouped:
        # if knot = 0 or 1, then exit_left == enter_right and exit_right == enter_left
        # if knot = 2 or 3, then exit_left == enter_left and exit_right == enter_right
        # if knot = 0 or 2, then color = enter_left
        # if knot = 1 or 3, then color = enter_right




if __name__ == "__main__":
    grid = setup_grid(num_strings=4, num_rows=8)
    constraints = setup_constraints(grid, "RB")

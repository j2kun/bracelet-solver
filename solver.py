"""Solve for a bracelet pattern matching a given set of coordinates.

Example here is the serpinski triangle, with an implied triangular start.
"""

from dataclasses import dataclass
from dataclasses import field
from itertools import groupby
from typing import Union
import z3

ConstVarT = z3.z3.DatatypeRef
ConstraintT = z3.z3.BoolRef


"""
A knot variable enumerates the possible ways to tie a knot. The notation
signifies <knot color><exit direction>. E.g., "LR = left right" means that the
left string is the overhand part of the knot, making the stitch have that color,
and exits on the right, implying the two parent strings switch sides. Note this
is NOT the direction in which the knots are tied. For that, an LR would be a
"forward forward knot", and an LL would be a "forward backward knot", because
the left string is tied on top to expose its color, and then exits on the left.
"""
(KnotType, (LR, RL, LL, RR)) = z3.EnumSort(
    "KnotType",
    ["leftright", "rightleft", "leftleft", "rightright"],
)

(Color, (black, white)) = z3.EnumSort(
    "Color",
    ["black", "white"],
)


@dataclass
class KnotNode:
    i: int
    j: int
    enter_left: ConstVarT
    enter_right: ConstVarT
    exit_left: ConstVarT
    exit_right: ConstVarT
    knot: ConstVarT
    color: ConstVarT

    def id(self):
        return (self.i, self.j)


@dataclass
class EdgeNode:
    i: int
    j: int
    enter_and_exit: ConstVarT

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

    @property
    def color(self):
        return self.enter_and_exit

    def id(self):
        return (self.i, self.j)


@dataclass
class InitialStringNode:
    i: int
    j: int
    # initial strings have only one allowed exit direction
    # depending on the parity, and it is equal to their color
    color: ConstVarT

    @property
    def exit_left(self):
        return self.color

    @property
    def exit_right(self):
        return self.color

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

    def knot_rows(self):
        return [list(g) for k, g in groupby(self.knot_nodes.items(), lambda x: x[0][0])]

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

    def upper_left_index(self, i, j):
        if i == 1:
            return (i - 1, j - 1)
        return (i - 2, j - 2)

    def upper_right_index(self, i, j):
        if i == 1:
            return (i - 1, j + 1)
        return (i - 2, j + 2)

    def has_upper_left(self, node):
        return self.upper_left_index(node.i, node.j) in self.nodes

    def has_upper_right(self, node):
        return self.upper_right_index(node.i, node.j) in self.nodes

    def upper_left(self, node):
        return self.nodes[self.upper_left_index(*node.id())]

    def upper_right(self, node):
        return self.nodes[self.upper_right_index(*node.id())]

    def knot_at(self, i, j):
        """Returns true if there is a knot at (i, j) in the grid."""
        on_edge = j == 0 or j == self.width - 1
        on_left_staggered = i % 4 == 1 and j % 4 == 2
        on_right_staggered = i % 4 == 3 and j % 4 == 0
        return not on_edge and (on_left_staggered or on_right_staggered)


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
                color=z3.Const(f"initial_string_color_{j}", Color),
            )
        )

    for i in range(grid.height):
        if i % 4 == 3:
            # left edge node
            grid.add(
                EdgeNode(
                    i=i,
                    j=0,
                    enter_and_exit=z3.Const(f"left_edge_{j}", Color),
                )
            )
            # right edge node
            grid.add(
                EdgeNode(
                    i=i,
                    # 1 past the column index of the last initial string
                    j=2 * num_strings,
                    enter_and_exit=z3.Const(f"right_edge_{j}", Color),
                )
            )

        # knot nodes
        for j in range(grid.width):
            if grid.knot_at(i, j):
                grid.add(
                    KnotNode(
                        i=i,
                        j=j,
                        enter_left=z3.Const(f"enter_left_{i}_{j}", Color),
                        enter_right=z3.Const(f"enter_right_{i}_{j}", Color),
                        exit_left=z3.Const(f"exit_left_{i}_{j}", Color),
                        exit_right=z3.Const(f"exit_right_{i}_{j}", Color),
                        knot=z3.Const(f"knot_{i}_{j}", KnotType),
                        color=z3.Const(f"color_{i}_{j}", Color),
                    )
                )

    return grid


def setup_constraints(grid: Grid):
    constraints = []

    # constraints that apply to all nodes
    for node in grid.nodes.values():
        if grid.has_upper_left(node):
            constraints.append(node.enter_left == grid.upper_left(node).exit_right)
        if grid.has_upper_right(node):
            constraints.append(node.enter_right == grid.upper_right(node).exit_left)

    # knot constraints
    for node_id, knot_node in grid.knot_nodes.items():
        """
        if knot == LR (🡦), then
          exit_right = enter_left
          exit_left == enter_right
          color = enter_left
        """
        constraints.append(
            z3.If(
                knot_node.knot == LR,
                z3.And(
                    knot_node.exit_right == knot_node.enter_left,
                    knot_node.exit_left == knot_node.enter_right,
                    knot_node.color == knot_node.enter_left,
                ),
                True,
            )
        )

        """
          if knot == RL (🡧), then
            exit_left == enter_right
            exit_right = enter_left
            color = enter_right
        """
        constraints.append(
            z3.If(
                knot_node.knot == RL,
                z3.And(
                    knot_node.exit_left == knot_node.enter_right,
                    knot_node.exit_right == knot_node.enter_left,
                    knot_node.color == knot_node.enter_right,
                ),
                True,
            )
        )

        """
          if knot == LL (⤸), then
            exit_left == enter_left
            exit_right = enter_right
            color = enter_left
        """
        constraints.append(
            z3.If(
                knot_node.knot == LL,
                z3.And(
                    knot_node.exit_left == knot_node.enter_left,
                    knot_node.exit_right == knot_node.enter_right,
                    knot_node.color == knot_node.enter_left,
                ),
                True,
            )
        )

        """
          if knot == RR (⤹), then
            exit_right == enter_right
            exit_left = enter_left
            color = enter_right
        """
        constraints.append(
            z3.If(
                knot_node.knot == RR,
                z3.And(
                    knot_node.exit_left == knot_node.enter_left,
                    knot_node.exit_right == knot_node.enter_right,
                    knot_node.color == knot_node.enter_right,
                ),
                True,
            )
        )

    return constraints


def setup_serpinski_constraints(grid: Grid):
    constraints = []

    # In this dict, 1 is black and 0 is white.
    # The keys are the node ids.
    serpinski = dict()

    for node_id, knot_node in grid.knot_nodes.items():
        # check to see if the knot is within the triangle
        x, y = node_id
        mid = (grid.width - 1) / 2
        if abs(y - mid) == x - 3:
            serpinski[node_id] = 1
            constraints.append(knot_node.color == black)
        elif abs(y - mid) < x - 3:
            # enforce that the color is equal to the mod 2 sum of the parent colors,
            # and actually evaluate it
            upper_left = serpinski[grid.upper_left_index(*knot_node.id())]
            upper_right = serpinski[grid.upper_right_index(*knot_node.id())]
            serpinski_value = (upper_left + upper_right) % 2
            serpinski[node_id] = serpinski_value
            constraints.append(
                knot_node.color == (black if serpinski_value == 1 else white)
            )

    return constraints


if __name__ == "__main__":
    num_strings = 32
    num_rows = 17
    grid = setup_grid(num_strings=num_strings, num_rows=num_rows)

    print("\ngeneral constraints")
    constraints = setup_constraints(grid)
    for constraint in constraints:
        print(constraint)

    print("\nserpinski constraints")
    serpinski_constraints = setup_serpinski_constraints(grid)
    for constraint in serpinski_constraints:
        print(constraint)

    solver = z3.Solver()
    solver.add(constraints)
    solver.add(serpinski_constraints)

    if solver.check() == z3.sat:
        model = solver.model()
        for string_node in grid.string_nodes.values():
            print(f"{string_node.color.decl()}=" f"{model.eval(string_node.color)}")

        for knot_node in grid.knot_nodes.values():
            print(f"{knot_node.knot.decl()}=" f"{model.eval(knot_node.knot)}")

        # Print as input to https://catherinesyeh.github.io/digidemo/
        # A = LR
        # B = RL
        # C = LL
        # D = RR
        print("\n\n")
        print("(name SERPINSKI)\n")

        color_names = {white: "PeachPuff", black: "PaleVioletRed"}
        knot_names = {LR: "A", RL: "B", LL: "C", RR: "D"}
        strings = " ".join(
            color_names[model.eval(n.color)] for n in grid.string_nodes.values()
        )
        print(f"(strings {num_strings} {strings})\n")

        for row in grid.knot_rows():
            first_col = row[0][0][1]
            last_col = row[-1][0][1]
            start = "" if first_col == 2 else "_"
            end = "" if last_col == grid.width - 3 else "_"
            print(
                f"{start}{'_'.join(knot_names[model.eval(n[1].knot)] for n in row)}{end}"
            )
    else:
        print("The problem is unsatisfiable")

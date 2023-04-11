import solver


def test_grid_setup():
    grid = solver.setup_grid(num_strings=6, num_rows=3)
    knot_nodes = grid.knot_nodes

    assert set(knot_nodes.keys()) == set(
        [
            (1, 2),
            (1, 6),
            (1, 10),
            (3, 4),
            (3, 8),
            (5, 2),
            (5, 6),
            (5, 10),
        ]
    )

    assert set(grid.edge_nodes.keys()) == set(
        [
            (3, 0),
            (3, 12),
        ]
    )

    assert set(grid.string_nodes.keys()) == set(
        [
            (0, 1),
            (0, 3),
            (0, 5),
            (0, 7),
            (0, 9),
            (0, 11),
        ]
    )

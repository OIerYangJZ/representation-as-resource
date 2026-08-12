import itertools
import math
import unittest


def vectors(q, m):
    return list(itertools.product(range(q), repeat=m))


def valid_common_continuations(u, up, q):
    """Continuations keeping both aggregates outside the excluded residue."""
    choices = []
    for a, b in zip(u, up):
        allowed = [v for v in range(q)
                   if (a + v) % q != q - 1 and (b + v) % q != q - 1]
        choices.append(allowed)
    return itertools.product(*choices)


def aggregates_differ(u, up, v, q):
    x = tuple((a + c) % q for a, c in zip(u, v))
    xp = tuple((b + c) % q for b, c in zip(up, v))
    return x != xp


def confusability_graph(q, m):
    nodes = vectors(q, m)
    edges = set()
    witnesses = {}
    for i, u in enumerate(nodes):
        for j in range(i + 1, len(nodes)):
            up = nodes[j]
            witness = next((v for v in valid_common_continuations(u, up, q)
                            if aggregates_differ(u, up, v, q)), None)
            if witness is not None:
                edges.add((i, j))
                witnesses[(i, j)] = witness
    return nodes, edges, witnesses


def colorable(vertex_count, edges, colors):
    adjacency = [set() for _ in range(vertex_count)]
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    order = sorted(range(vertex_count), key=lambda v: -len(adjacency[v]))
    assigned = [-1] * vertex_count

    def visit(position):
        if position == vertex_count:
            return True
        vertex = order[position]
        forbidden = {assigned[n] for n in adjacency[vertex] if assigned[n] >= 0}
        for color in range(colors):
            if color not in forbidden:
                assigned[vertex] = color
                if visit(position + 1):
                    return True
                assigned[vertex] = -1
        return False

    return visit(0)


class SmallCompilerCounterexampleSearch(unittest.TestCase):
    def test_one_pass_collision_graph_is_complete(self):
        for q, m in ((3, 1), (3, 2), (4, 1)):
            nodes, edges, witnesses = confusability_graph(q, m)
            expected_edges = len(nodes) * (len(nodes) - 1) // 2
            self.assertEqual(len(edges), expected_edges)
            self.assertEqual(len(witnesses), expected_edges)
            self.assertFalse(colorable(len(nodes), edges, len(nodes) - 1))
            self.assertTrue(colorable(len(nodes), edges, len(nodes)))

    def test_two_round_block_hybrid_respects_proved_lower_constants(self):
        for m in range(1, 9):
            for k in range(2, 6):
                q = k + 1
                for p in range(1, 5):
                    for h in range(0, m + 1):
                        recovered = min(m, p * h)
                        a_bits = (m - recovered) * math.log2(q)
                        state_bits = h * math.log2(q)
                        output_bits = (recovered * math.log2(k)
                                       + 2 * (m - recovered) * math.log2(q))
                        lower = m * math.log2(k)
                        self.assertGreaterEqual(
                            a_bits + (2 * p - 1) * state_bits + 1e-12,
                            lower)
                        self.assertGreaterEqual(output_bits + 1e-12, lower)

    def test_abort_upper_does_not_undercut_fano_bound(self):
        for m in range(1, 9):
            for k in range(2, 6):
                for delta in (0.0, 0.1, 0.25, 0.49):
                    h2 = 0.0 if delta == 0 else (
                        -delta * math.log2(delta)
                        -(1 - delta) * math.log2(1 - delta))
                    lower = (1 - delta) * m * math.log2(k) - h2
                    abort_upper = 1 + (1 - delta) * m * math.log2(k)
                    self.assertGreaterEqual(abort_upper + 1e-12, lower)


if __name__ == "__main__":
    unittest.main()

import itertools
import math
import unittest


TAU = 2.0 * math.pi


def wrap_margin(k, delta):
    return min(abs(d * delta - TAU * round(d * delta / TAU))
               for d in range(1, k))


def relative_spectrum(x, y, delta):
    """Spectrum for independent Z characters, represented by phases."""
    s = [a - b for a, b in zip(x, y)]
    return [(-0.5 * delta * sum(v * sign for v, sign in zip(s, signs))) % TAU
            for signs in itertools.product((-1, 1), repeat=len(s))]


def projective_distance_from_phases(phases):
    phases = sorted({round(theta % TAU, 14) for theta in phases})
    if len(phases) <= 1:
        return 0.0
    gaps = [phases[i + 1] - phases[i] for i in range(len(phases) - 1)]
    gaps.append(phases[0] + TAU - phases[-1])
    shortest_covering_arc = TAU - max(gaps)
    return 2.0 * math.sin(shortest_covering_arc / 4.0)


class QaryPackingTests(unittest.TestCase):
    def assert_close(self, actual, expected, tol=1e-10):
        self.assertLessEqual(abs(actual - expected), tol,
                             (actual, expected))

    def test_exact_worst_pair_formula_with_and_without_wrap(self):
        grids = [
            (2, math.pi / 5),       # no wrap
            (4, 2 * math.pi / 5),   # cyclic interval crosses pi
            (4, 2 * math.pi / 3),   # resonance: labels 0 and 3 collide
        ]
        for m in (1, 2):
            for k, delta in grids:
                vectors = list(itertools.product(range(k), repeat=m))
                observed = min(
                    projective_distance_from_phases(
                        relative_spectrum(x, y, delta))
                    for i, x in enumerate(vectors)
                    for y in vectors[i + 1:]
                )
                predicted = 2.0 * math.sin(wrap_margin(k, delta) / 4.0)
                self.assert_close(observed, predicted)

    def test_cyclic_q_equals_k_plus_one_has_one_step_margin(self):
        for k in range(2, 6):
            q = k + 1
            delta = TAU / q
            self.assert_close(wrap_margin(k, delta), delta)

    def test_epsilon_tuning(self):
        for epsilon in (1 / 8, 1 / 10, 1 / 16, 1 / 32):
            q = math.floor(math.pi / (2 * math.asin(2 * epsilon)))
            k = q - 1
            separation = 2 * math.sin(math.pi / (2 * q))
            self.assertGreaterEqual(k + 1e-12, 1 / (4 * epsilon))
            self.assertLessEqual(k, math.pi / (4 * epsilon) + 1e-12)
            self.assertGreaterEqual(separation + 1e-12, 4 * epsilon)


if __name__ == "__main__":
    unittest.main()

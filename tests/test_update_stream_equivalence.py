import itertools
import math
import unittest


TAU = 2.0 * math.pi


def all_vectors(alphabet_size, m):
    return itertools.product(range(alphabet_size), repeat=m)


def complete_last_share(x, prefix_shares, q):
    return tuple((x[j] - sum(share[j] for share in prefix_shares)) % q
                 for j in range(len(x)))


def diagonal_phases(coefficients, delta):
    return [(-0.5 * delta * sum(c * sign
                               for c, sign in zip(coefficients, signs))) % TAU
            for signs in itertools.product((-1, 1), repeat=len(coefficients))]


def projectively_equivalent(phases_a, phases_b, tol=1e-10):
    relative = [((a - b) % TAU) for a, b in zip(phases_a, phases_b)]
    anchor = relative[0]
    return all(abs(math.atan2(math.sin(v - anchor), math.cos(v - anchor))) <= tol
               for v in relative)


class UpdateStreamEquivalenceTests(unittest.TestCase):
    def test_exhaustive_small_streams_match_semantic_unitary(self):
        for m, q, r in ((1, 3, 2), (2, 3, 2), (1, 4, 3), (2, 3, 3)):
            k = q - 1
            delta = TAU / q
            share_vectors = list(all_vectors(q, m))
            for x in all_vectors(k, m):
                semantic = diagonal_phases(x, delta)
                for flat_prefix in itertools.product(share_vectors,
                                                     repeat=r - 1):
                    last = complete_last_share(x, flat_prefix, q)
                    total = tuple(sum(share[j]
                                      for share in flat_prefix + (last,))
                                  for j in range(m))
                    flat = diagonal_phases(total, delta)
                    self.assertTrue(projectively_equivalent(flat, semantic),
                                    (m, q, r, x, flat_prefix, last))

    def test_every_single_token_is_compatible_with_every_aggregate(self):
        for q in (3, 4, 5):
            k = q - 1
            for r in (2, 3, 4):
                for token_round in range(r):
                    for residue in range(q):
                        attainable = set()
                        for target in range(k):
                            shares = [0] * r
                            shares[token_round] = residue
                            mate = (token_round + 1) % r
                            shares[mate] = (target - sum(shares)) % q
                            if sum(shares) % q == target:
                                attainable.add(target)
                        self.assertEqual(attainable, set(range(k)))

    def test_canonical_individual_share_marginals_do_not_depend_on_x(self):
        q, r = 4, 3
        for target in range(q - 1):
            counts = [[0] * q for _ in range(r)]
            for prefix in itertools.product(range(q), repeat=r - 1):
                last = (target - sum(prefix)) % q
                shares = prefix + (last,)
                for t, value in enumerate(shares):
                    counts[t][value] += 1
            for marginal in counts:
                self.assertEqual(len(set(marginal)), 1)


if __name__ == "__main__":
    unittest.main()

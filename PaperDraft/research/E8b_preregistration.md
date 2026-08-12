# E8b Preregistration — is the commitment toll visible in third-party emitted streams?

Date: 2026-08-08.  **Committed before any E8b run; the git commit order is
the timestamp.**  Successor to E8, whose Arm B (P5) failed on a design flaw:
it placed every rotation on the low-index qubits and therefore never varied
the quantity it was meant to vary.  E8b does not repair P5 and does not
reuse it.  It tests something stronger and different.

## Why the previous third-party arm was the wrong target

P5 asked whether real toolchains spend committed bytes on addresses.  Even
had it been designed correctly, a positive answer would have supported the
*address-width* reading that E8's P4 refuted.  `prop:commitment-toll` says
the irreducible cost of committing early is the entropy of the commitment
schedule, log2 C(m,k) bits.  The right third-party question is therefore:

  **Does a stream emitted by a compiler we do not control carry
  log2 C(m,k) more information when the set of early-committed coordinates
  is unpredictable than when it is predictable, holding everything else
  fixed?**

## Design

Two circuit variants, identical in every respect except the *predictability*
of the dispersal mask:

- `arith`  — the k dispersed generators sit at an arithmetic progression
  {0, m/k, 2m/k, ...}.  The mask is describable in O(log m) bits.
- `random` — the k dispersed generators are a uniform random k-subset,
  seeded.  The mask carries log2 C(m,k) bits.

Held fixed by construction, and asserted in the script:

- identical m, identical k, identical total rotation count (m + k);
- identical multiset of angles (round-one residues are drawn from one seeded
  sequence indexed by generator, so both variants consume the same values);
- comparable address magnitudes.  The arithmetic progression spans the whole
  register exactly as a random subset does, so digit counts in the emitted
  text are close.  This is the control that separates *information* from
  *text length*: an address-width effect would move both variants equally.

A dispersed generator is emitted as two rotations (round-major: all round-one
records, then all round-two records); an aggregated generator is emitted as
one round-two rotation.  No aggregation pass is run -- the third-party tool
acts as the *emitter* of the committed stream, which is the materialize-first
pipeline of `sec:introduction`.

- **Scan**: m = 4096; k/m in {1/8, 1/4, 1/2, 3/4, 1}; seeds {1, 2, 3}.
- **Tools** (not controlled by the authors): Qiskit 2.4.0
  `transpile(..., basis_gates=['rz','cx','h'], optimization_level=0)` then
  `qasm3.dumps`; pytket 2.16.0 `AutoRebase({CX, Rz, H})` then
  `circuit_to_qasm_str`.
- **Measurements per cell**: raw serialized bytes; xz-compressed bytes
  (`lzma.compress`, preset 9 | PRESET_EXTREME); gzip-compressed bytes
  (`zlib.compress`, level 9).  Compression is used as a standard proxy for
  the information content of the emitted stream; it yields an upper bound on
  entropy, so it can only *understate* the effect.

Primary quantity, per tool and compressor:

    excess(k) = 8 * (compressed_bytes(random) - compressed_bytes(arith))

in bits, averaged over seeds, compared against log2 C(m,k).

## Preregistered predictions

- **P6 (sign)**: excess(k) > 0 for every k < m, for both tools, under xz.
- **P7 (shape)**: excess(k) is concave in k with its maximum at k = m/2, and
  excess(m) <= 0.02 * excess(m/2).  This is the distinctive signature: the
  entropy of a k-subset mask vanishes at k = m, whereas any cost that scales
  with the number of committed records is monotone increasing in k.  No
  address-width or per-record-cost model produces a return to zero.
- **P8 (magnitude)**: at k = m/2, excess >= 0.4 * log2 C(m,k) under xz for
  both tools.  The 0.4 allows for compressor inefficiency; xz is not an
  optimal entropy coder for this structure and can only lose.
- **P9 (control -- the effect is informational, not textual)**: the raw
  uncompressed byte difference between the two variants is at most 1% of
  the raw size, at every k and for both tools.
- **P10 (separation)**: at k = m/2 the excess exceeds three times the
  seed-to-seed standard deviation of the compressed size within either
  variant.

## Decision rule (frozen)

- **P6 AND P7 AND P8 AND P9** -> the commitment toll is confirmed on
  compilers the authors do not control, in the form
  `prop:commitment-toll` predicts and with the shape no competing model
  predicts.  The third-party leg is licensed for the abstract.
- **NOT P7** -> the shape signature is absent; whatever the excess is, it is
  not schedule entropy.  Report as-is; no third-party claim; the proposition
  stands on Arm A alone.
- **NOT P9** -> the two variants differ textually, so the comparison is
  confounded and the arm is void.  Report as void, not as evidence.
- **P6 AND P7 AND NOT P8** -> the signature is present but attenuated;
  report the measured fraction and describe the arm as qualitative
  (shape only, not magnitude).
- **NOT P10** -> underpowered; report as inconclusive at this m.

No post-hoc metric substitution, no repair of a failed arm, no re-run at a
different m after seeing results.  If a variant fails its
construction asserts (equal counts, equal angle multiset) the run aborts.

## Outputs

`PaperDraft/generated/e8b_thirdparty_toll.json` — per-cell rows, summary,
verdict — produced by `PaperDraft/scripts/run_thirdparty_toll.py`.

---

## Amendment 1 (2026-08-08, before any comparison was computed)

The first execution aborted on the preregistered construction assert
("equal angle multiset"), exactly as the decision rule requires.  No
size, excess, or comparison was produced or observed; the abort happened
during instance construction.

Cause: the design text said round-one residues are "drawn from one seeded
sequence indexed by generator".  Indexing by *generator* cannot satisfy the
equal-multiset invariant, because the two variants disperse different
generators and would therefore consume different residues.  The two clauses
were mutually inconsistent, and the invariant is the one that matters -- it
is what keeps the comparison from being confounded by angle text.

Resolution, which implements the invariant rather than changing the test:

- round-one record i (i = 0..k-1) carries residue `a[i]`, a seeded sequence
  indexed by **rank within the mask**;
- round-two record j (j = 0..m-1) carries residue `b[j]`, a seeded sequence
  indexed by generator.

Both multisets are then identical across the two variants by construction,
and the *only* difference between the emitted streams is which addresses
appear in the round-one block -- which is precisely the commitment schedule
whose entropy is under test.

No prediction, tool, scan range, compressor, or decision rule is changed.

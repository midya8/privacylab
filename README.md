# PrivacyLab

An exact finite-channel differential-privacy reference. Supply rational probability tables and explicit neighboring-secret edges; inspect the smallest delta at a multiplicative privacy factor, every attaining event, and the complete directed-pair arithmetic. Independent product and stochastic postprocessing helpers make randomness assumptions visible.

**Private marginals can reveal a secret jointly.** In the developed shared-coin control, `A = secret XOR Z` and `B = Z`, with `P(Z=0)=3/4`. The first marginal has pure factor 3 and the second has factor 1, yet the joint output reveals `secret = A XOR B` exactly. Its two conditional distributions have disjoint supports and delta 1 at every finite factor. This does not contradict a composition theorem: the required conditional-mechanism premise is false.

![Exact privacy factors, deltas and a shared-coin joint-release counterexample](assets/privacy-audit.svg)

## Run offline

Python 3.10+, standard library at runtime. No private datasets, credentials, network calls, paid APIs or random sampling.

```sh
python -m privacylab demo
python -m privacylab audit examples/input.json
python -m unittest discover -s tests -v
python examples/render_figure.py --check
python -m pip wheel --no-deps . -w dist
```

[Full exact demo report](examples/demo.json) · [caller input](examples/input.json) · [equations, assumptions and limits](DESIGN.md).

```python
from privacylab import audit, independent_product, postprocess

rr = {
    'schema_version': 1,
    'secrets': ['secret/0', 'secret/1'],
    'outputs': ['0', '1'],
    'neighbors': [[0, 1]],
    'probabilities': [['3/4', '1/4'], ['1/4', '3/4']],
}
assert audit(rr, '3')['delta'] == '0'
assert audit(rr, '3')['pure_factor'] == '3'

joint = independent_product(rr, rr)['channel']
assert audit(joint, '3')['delta'] == '3/8'
assert audit(joint, '9')['delta'] == '0'
```

## Factor is not epsilon

The API accepts an exact rational factor `t = exp(epsilon) >= 1`, not epsilon itself. Factor3 means epsilon `ln(3)`; factor9 means epsilon `ln(9)`. No approximate exponential or logarithm participates in a decision.

For each listed undirected neighbor edge, inspect **both directions** `P,Q`. At factor `t`, the smallest valid slack for that pair is

```text
delta_pair(t) = max_event [P(event) - t Q(event)]
              = sum_output max(P(output) - t Q(output), 0)
```

The report's delta is the maximum over all directed neighbor pairs. It retains every signed/positive excess, P/Q ratio or support-mismatch status, the canonical strict-positive attaining event and its P/Q masses, zero-excess ties, singular mass, every worst pair, and the minimal pure factor with output-level witnesses when finite. `pure_factor = null` is explicitly tagged infinite due to support mismatch, never mistaken for no data or zero privacy loss. Unlisted secret pairs remain visible; the audit says nothing about their adjacency.

## Developed controls

All numbers below are exact for small supplied channels, not empirical privacy measurements.

| Channel | Minimal pure factor | delta at factor 1 | delta at factor 3 | delta at factor9 |
| --- | --- | --- | --- | --- |
| Randomized response, truthful probability 3/4 | 3 | 1/2 | 0 | 0 |
| Two independent randomized-response releases | 9 | 1/2 | 3/8 | 0 |
| Joint release postprocessed by vote with a fresh fair tie-break | 3 | 1/2 | 0 | 0 |
| Only the parity of two independent releases | 1 | 0 | 0 | 0 |
| Shared coin, first marginal | 3 | 1/2 | 0 | 0 |
| Shared coin, second marginal | 1 | 0 | 0 | 0 |
| Shared coin, joint release | infinite | 1 | 1 | 1 |

The stochastic vote is exactly the original randomized-response channel. Parity is secret-independent with distribution `[5/8,3/8]`; more privacy is not a utility claim. Conditioning the shared-coin example on `A=0` makes B deterministic 0 versus 1, explicitly showing why the second release does not satisfy the required conditional privacy premise. The independent-product helper cannot validate independence in an external implementation; it constructs the product table **under that assumption**. Postprocessing uses one supplied secret-independent row-stochastic kernel for every secret, with fresh kernel randomness. Feeding in extra secret information or reusing correlated coins is outside that contract.

## Strict inputs and limits

- Channels have exactly `schema_version` (integer 1), `secrets`, `outputs`, `neighbors`, `probabilities`. API accepts lists/tuples for arrays; JSON uses arrays.
- Between 2 and 8 secrets, 1..64 outputs, 1..28 undirected edges. Both edge directions are audited. Self edges, duplicate undirected edges, invalid indices and empty graphs are rejected. Helpers require identical ordered secrets and canonical neighbor edges.
- Unique ASCII labels are 1..40 characters using letters, digits, spaces and `_.:/-`. Labels are identifiers, not private-data discovery requests.
- Probabilities are integers, exact decimal/fraction strings or API `Fraction` values. Floats and booleans are rejected. Rows must sum **exactly** to 1; no clipping, renormalization or tolerance. Fraction syntax is unsigned, with a positive denominator; no exponent notation or surrounding whitespace. Each rational numerator/denominator is limited to 512 bits; strings to 160 characters. Computed transform outputs must also satisfy that limit, or the helper fails explicitly.
- Factors are exact rationals in `[1,10^12]`. Reports are point queries, not an interpolated full privacy curve or an adaptive stopping rule.
- The strict audit CLI wrapper has exactly `schema_version` (integer 1), `channel`, `factor`. Input cap 100000 bytes; duplicate/unknown/missing keys, nonfinite JSON, bad UTF-8 and invalid values fail with exit 2 and empty stdout.

## Verification

29 tests: 14 core probability/audit tests, 9 transform tests, 3 CLI tests and 3 SVG tests. Twenty-four seeded three-secret/four-output channels are checked against exhaustive enumeration of all 16 events per directed pair at four exact factors. Every demo term/event/support field is reconstructed. Tests also cover a `10^-100` singular leak retained exactly, minimal pure-factor witnesses, factor monotonicity/convexity, adjacency omissions, permutations, exact decimal parsing, full 8-secret/64-output capacity, strict validation and nonmutation/RNG state.

Transform tests reconstruct every product probability/mapping; compare repeated randomized response through four releases with exact binomial count channels; test 24 seeded stochastic postprocessing contractions; verify shared-coin reconstruction and its conditional failure; and cover identity/constant/permutation kernels, alignment, output capacity and computed rational limits. SVG checks verify all 36 exact cells and their coordinates, full compressed JSON metadata, a hidden attaining-event tamper, and byte-exact regeneration. The five-module wheel reproduces both complete CLI JSON outputs outside checkout. CI runs the suite on Python 3.10-3.13 plus installed-wheel parity.

## What this does not certify

A table certificate applies to the supplied finite mechanism and listed neighbor graph only. It does not prove that a program samples that table, that randomness is secure/fresh/independent, that a neighboring-dataset relation covers a real application, or that unlisted possible inputs are protected. No trained-model guarantee, DP-SGD accountant, continuous Gaussian mechanism, privacy-loss convolution, advanced/adaptive composition implementation, privacy-utility optimum or production security claim. A low delta is not a probability that any particular person's secret leaks, and differential privacy does not promise that useful population facts remain hidden.

This implements established finite-distribution DP and hockey-stick divergence arithmetic, not a new privacy theorem. Primary references: Dwork and Roth's [Algorithmic Foundations of Differential Privacy](https://homepage.divms.uiowa.edu/~sriram/5980/spring17/privacybook.pdf), definition 2.4 and proposition 2.1; [modern privacy accounting notes](https://arxiv.org/pdf/2210.00597), proposition 7 and theorem 9; and Google Research's [privacy accounting overview](https://research.google/blog/differential-privacy-accounting-by-connecting-the-dots/). See [DESIGN.md](DESIGN.md) for the finite proof and implementation boundaries.

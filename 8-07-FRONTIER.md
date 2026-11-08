# Exact finite privacy-factor frontiers and inverse budget certificates

## Separate, bounded interface

`frontier(channel)` returns the full worst-directed-neighbor delta(t) for every **finite multiplicative factor t >= 1**. This is not epsilon: epsilon is symbolically ln(t). `minimum_factor(channel, target_delta)` returns that frontier and the smallest factor meeting a target delta, or an explicit unattainability certificate. The CLI `frontier INPUT.json` takes exactly integer `schema_version: 1`, `channel` and `target_delta`; `frontier-demo` reproduces four developed controls. The target is an exact rational in [0,1], never a float or boolean.

This new interface accepts at most four secrets and eight outputs, and therefore at most six listed undirected edges/twelve directed pairs. It reuses the original exact channel schema, label/edge validation, 512-bit input probability components and 160-character string-input cap. No normalization or tolerance is added. Internal frontier coefficients/intersections use exact Fraction arithmetic and are not rounded back into an input-size cap. Canonical output fractions can be longer than the input string limit; convert long output probabilities to API Fraction values before resubmitting them. CLI input is separately limited to 100000 bytes.

The smaller domain bounds exhaustive ratio-cell/intersection enumeration. This is not a scalability or performance claim. The original `audit` interface still permits up to eight secrets and 64 outputs, with its separate 10^12 factor cap and 512-bit factor-component limit. An inverse result marks whether its exact factor is inside that original numeric domain. A mathematically necessary larger factor is reported exactly, not truncated and not confused with unattainability. Adaptive-tree certificates keep their existing domain and semantics.

## Local finite profiles

Fix a directed listed neighbor pair and its exact rows p,q. For any finite t>=1,

```text
D_pq(t) = max_E [P(E)-tQ(E)]
        = sum_k max(p_k-t*q_k,0).
```

For q_k>0, a term changes activity only at ratio p_k/q_k. Ratios below or equal to 1 do not create interior knots in this domain. For q_k=0 and p_k>0, its contribution p_k is constant at every finite t. If both probabilities are zero, the term is zero. On every interval between consecutive ratios greater than 1, the strict-positive event set is fixed in the interior, hence

```text
D_pq(t) = A - B*t,
A = sum_active p_k,
B = sum_active q_k >= 0.
```

At a ratio endpoint, the vanishing term has zero excess, so neighboring affine formulas agree. A strict-positive event excludes ties; knot queries separately retain all zero-excess ties. Local profiles are continuous, nonincreasing and convex. Their tail is the singular-support mass `sum_{q_k=0} p_k`.

## Global envelope requires more than the ratio grid

The requested table-level profile is the maximum of D_pq over both directions of every listed edge. Each local profile is affine inside a common grid cell formed by all local ratios plus 1. Within one such cell, any change in which line is largest must occur at a pairwise line intersection

```text
A-B*t = A'-B'*t,
t = (A-A') / (B-B')    when B != B'.
```

The implementation inserts every such intersection strictly inside the cell, determines the maximizing line(s) on the resulting open subintervals and merges adjacent pieces only when coefficients and interior maximizing pair sets match. The final tail is included with a null upper endpoint meaning unbounded factors, not a missing interval. No arbitrary factor grid, binary search, floating-point slope test or query-point interpolation is used.

Interior maximizers need not include every pair tying at an isolated factor. Every reported global knot has a complete exact point audit over all listed directions, including all ties. Inverse queries also return complete point audits at the minimum factor. The affine pieces describe profile values everywhere; they do not promise a separate record of every possible isolated pair tie that leaves the global affine formula unchanged.

## Whole-interval domination certificate

Choosing the largest line at a midpoint is not by itself the exported certificate. Each global piece L(t)=A-Bt is compared with **every overlapping piece** of each local curve. The report retains their overlap bounds and the affine difference at both finite endpoints. Nonnegative endpoint slacks certify L>=D_pq throughout a finite overlap. For an unbounded overlap, the difference has nonnegative start value and nonnegative derivative, retained as the tail-slope slack. Thus L dominates every local curve over its entire interval. A named interior maximizing pair supplies equality with L, giving the exact upper envelope, rather than merely an upper bound.

The implementation also checks interval coverage/adjacency, exact continuity at every global boundary, nonincreasing slope magnitudes (convexity), and the final constant singular plateau. Tests independently reconstruct all overlap certificates and compare endpoint/interior/tail values with all-event enumeration. This is finite affine arithmetic and the established hockey-stick event formula, not a new privacy theorem.

## Inverse budget and minimality

Let d be the target delta. The global profile is continuous and nonincreasing. If d is already at least the value at t=1, the smallest valid factor is the domain boundary 1. Otherwise the first decreasing affine piece reaching d gives the exact root

```text
minimum factor = (A-d)/B,   B>0.
```

The result retains the actual all-pair point audit, exact root, positive left slope, supporting pair indices and that left interval. Immediately smaller factors on that interval have delta>d. Monotonicity then rules out every earlier factor too. This also covers a target reached exactly at a global knot or the start of the final plateau. The minimum is attained, not only an infimum approached from above.

The global plateau is the maximum directed singular mass. If d lies below it, no finite factor works. The result is `unattainable`, with a directed pair and event E where Q(E)=0 and P(E)>d. That event obstructs every finite factor. Pure DP has d=0; its minimum factor is finite precisely when no directed pair has positive singular mass. A long finite minimum factor is different from an impossible target.

## Developed control with an extra envelope knot

Rows are secret 0 `[1/16,5/16,1/8,1/2]`, secret 1 `[5/16,3/8,1/16,1/4]` and secret 2 `[1/8,5/16,3/16,3/8]`. Listed edges are 0-1 and 1-2. Pair indices 0/1 are 0->1 and 1->0; indices 2/3 are 1->2 and 2->1. Secret pair 0-2 remains explicitly unlisted.

| Global interval | Exact delta(t) | Interior maximizers |
|---|---|---|
| [1,5/4] | 5/8 - 5t/16 | pair 0 |
| [5/4,5] | 5/16 - t/16 | pair 1 |
| [5,infinity) | 0 | all four directed pairs |

At t=5/4 the first two directions tie at delta=15/64. The common local ratio grid is `{1,6/5,3/2,2,5/2,3,5}` and **does not contain 5/4**. Inverting delta=1/4 yields factor 6/5, delta=15/64 yields 5/4, and delta=0 yields 5. At t=1 the point audit retains boundary ties even though only pair 0 is the interior maximizer immediately to its right.

Other controls include randomized response (minimum factors 3,2,1 at deltas 0,1/4,1/2), a constant singular plateau 1/2 (target 1/4 impossible; equality target attained at 1), and a finite full-support table with q_0=10^-30, p_0=1/2. The last has pure factor `5*10^29`, exactly represented but outside the old point-audit domain. It is not evidence of a useful production privacy mechanism or a claim about epsilon having that numerical value.

## Verification

63 tests retain all earlier 46 and add fourteen frontier behavior tests and three SVG tests. Thirty-two seeded three-secret/four-output channels use exhaustive all-16-event references at global endpoints, several interior factors and tail factors, alongside original point-audit comparisons inside its domain. Four target deltas per seeded channel are checked for feasibility and exact inverse minimality. Every domination overlap, endpoint/tail slack and local/global boundary is reconstructed; continuity, convex slopes and plateau assertions are checked.

Coverage also includes the exact non-ratio switch, inverse targets exactly at knots and the domain floor, positive singular plateaus reached only after a decreasing piece, singular event obstructions, huge but finite factors, 10^-100 API probabilities, all-zero-support terms, one output/equal rows/disjoint supports, all directions/omitted edges, output/secret permutations, nonmutation/RNG state, exact decimal strings, scope/schema/number errors, duplicate/nonfinite/oversize/invalid-UTF8 CLI input and empty stdout on failure. Full four-secret/eight-output/six-edge capacity includes equal, deterministic and dense seeded rational tables.

The figure tests check every one of its ten query cells and coordinates, all three global vertices, every directed local-curve vertex, complete compressed JSON metadata, hidden interval-domination tampering and byte-exact regeneration. All three figures and prior demo JSON artifacts remain reproducible. The seven-module installed wheel matches all six full CLI JSON outputs outside the checkout. CI runs Python 3.10-3.13 plus installed-wheel parity.

```sh
python -m privacylab frontier-demo
python -m privacylab frontier examples/frontier-input.json
python -m unittest discover -s tests -v
python examples/render_frontier.py --check
```

## Attribution and boundaries

The event characterization and discrete piecewise-linear hockey-stick connection are established DP mathematics. Sources: [Dwork and Roth, The Algorithmic Foundations of Differential Privacy](https://homepage.divms.uiowa.edu/~sriram/5980/spring17/privacybook.pdf), [modern privacy accounting notes](https://arxiv.org/pdf/2210.00597), and [Google Research, Differential privacy accounting by connecting the dots](https://research.google/blog/differential-privacy-accounting-by-connecting-the-dots/). Google's overview explains discrete PLDs and connecting prescribed divergence values; this code instead directly enumerates exact finite tables and computes a worst-neighbor affine envelope. It does not implement Connect-the-Dots, PLD convolution or a production accountant. Original [static design](DESIGN.md) and [adaptive notes](ADAPTIVE.md) describe their separate scope and sources.

No trained-model guarantee, secure sampling, real-data adjacency proof, protection for unlisted secret pairs, optimal composition across unspecified mechanisms, advanced composition, privacy-loss convolution, parameter-adaptive filter/odometer or production-security claim is made. The frontier is exact only for the supplied finite table and listed neighbor graph. Delta is not a per-person disclosure probability.

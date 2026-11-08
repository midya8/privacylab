# Finite probability tables, exact witnesses and assumptions

## The modeled mechanism

A channel row is the exact distribution of a finite output given one supplied secret. `neighbors` specifies undirected edges between secret indices. Every edge expands to both directed pairs. This graph may model neighboring databases, a local secret, or another explicit relation; the implementation does not infer or enlarge it. Disconnected/omitted pairs are reported, not silently certified. A finite table need not cover all possible real datasets.

For a supplied exact rational factor `t >= 1`, set epsilon symbolically to`ln(t)`. The DP inequality for every directed neighbor pair and every output event E is

```text
P(E) <= t Q(E) + delta.
```

We do not approximate `exp(epsilon)`, convert exact inputs to float, or assume delta is a personalized leak probability.

## Why the event witness is exact

For a fixed pair, write `d_k = P_k - t Q_k`. Then `P(E)-tQ(E) = sum_{k in E} d_k`. Each output can be included or excluded separately. The maximum is attained by taking all positive d_k and none of the negative d_k, giving `sum max(d_k,0)`. Zero terms may be added without changing the value; the report uses the canonical strict-positive event and separately lists all zero-excess ties. The empty event is valid and gives zero, so no negative delta is returned. Since P(E)<=1 and tQ(E)>=0, delta<=1.

Taking the maximum over both directions of every listed edge yields the smallest common delta at this factor for the supplied table. `worst_pairs` retains all ties. Each directed pair keeps the full term table and event P/Q masses; exact equality `event_p - t*event_q = sum positive_parts` is checked internally and independently in tests. The exhaustive event test uses a different all-subsets calculation, not the positive-part formula under test.

Pure DP means delta 0 for all those events. When Q_k>0, this is equivalent to `t >= P_k/Q_k`. A positive P_k with Q_k=0 rules out every finite pure factor. P=Q=0 contributes neither a ratio nor a leak; it has a separate `both_zero` status. Otherwise the maximum finite ratio over every directed neighbor/output is the minimal pure factor. It is at least 1 because normalized distributions cannot all have P_k<Q_k. Output-level witnesses attain the maximum. For a fixed pair, singular mass is the sum of P where Q=0; it survives every finite factor.

These exact point queries determine delta only at the requested factors. Although the mathematical profile is convex, nonincreasing and piecewise-linear in t, the software does not interpolate between requested points or return a globally enumerated curve. It does not compute a privacy-loss convolution or advanced-composition bound.

## Independent joint release

Given channels P and R with the same ordered secrets and neighboring edges, the helper constructs

```text
Joint_x(a,b) = P_x(a) * R_x(b).
```

This is a model assumption of independent fresh mechanism randomness **conditional on the secret**. It is not inferred from marginal distributions or verified in another program. Every output index maps explicitly to the original output indices/labels, avoiding collisions from concatenated user labels. The product has at most 64 outputs; otherwise it fails before building the table. Computed rationals are validated again rather than returning an artifact outside the accepted domain.

For finite pure factors t1 and t2, each directed likelihood ratio of an independent product is at most t1*t2, so its pure factor is at most the product. The demo's repeated randomized-response mechanism attains factors 3 and 9, while tests extend it to 27 and 81. Exact binomial count postprocessing retains the same profile in those symmetric controls. These tests are not an advanced-composition implementation or a universal sharp-composition claim.

## Secret-independent stochastic postprocessing

The caller supplies one exact row-stochastic kernel K indexed by the channel's ordered outputs. It is used unchanged for every secret. The helper computes

```text
Processed_x(z) = sum_a Channel_x(a) * K(a,z).
```

For any event E in the processed output space, `f(a)=sum_{z in E} K(a,z)` lies in [0,1]. Therefore

```text
Processed_P(E) - t Processed_Q(E)
= sum_a f(a) * (P(a)-tQ(a))
<= sum_a max(P(a)-tQ(a),0).
```

Thus the processed delta cannot exceed the input delta at any factor. Twenty-four exact seeded table/kernel tests check this contraction, alongside identity, constant, permutation, parity and random-tie vote controls. The helper has no per-secret kernel argument. A caller using extra secret information or mechanism-correlated randomness is not implementing this kernel product and cannot use its certificate.

## Why the shared-coin example is not a theorem counterexample

Let Z be zero with probability 3/4, independent of the bit secret x. Release `A=x XOR Z` and `B=Z` using the same Z. A alone is randomized response (pure factor 3), and B alone has the same distribution for both secrets (factor 1). But joint supports are disjoint:

```text
output (A,B):    00    01    10    11
secret 0:       3/4     0     0   1/4
secret 1:         0   1/4   3/4     0
```

The attaining event `{00,11}` has P = 1, Q = 0, so delta 1 at any finite factor; A XOR B reconstructs x on every nonzero-probability output. Conditioned on A=0, B is deterministically0 under x=0 and1 under x=1. That conditional second mechanism is not private. Combining marginal guarantees as if fresh independent noise or valid conditional privacy were established is the mistake. No composition theorem is contradicted.

## Arithmetic and validation

Integers, exact unsigned decimal/fraction strings and API `Fraction` values are accepted; floats and booleans are rejected instead of being silently rounded or interpreted as decimal ideals. Probability rows sum exactly to1. No renormalization, epsilon tolerance, clipping or fallback. Up to 8 secrets, 64 outputs, 28 undirected edges and 512-bit rational components bound work. String input length 160 and CLI byte cap 100000 prevent unbounded numeric parsing. Factors are in[1,10^12]. Labels are unique bounded ASCII identifiers, never executable expressions. Serialized outputs use canonical reduced fractions.

No stochastic sampling or global RNG use occurs. A five-module wheel contains `core`, `transforms`, `demo`, `__init__`, `__main__`. Both full JSON CLI outputs are compared outside the checkout in CI. Complete report data is compressed into the SVG metadata so hidden witness edits change the reproducible asset; all 36 visible numeric cells and positions are checked too. There is no performance benchmark or implementation-level security claim.

## Sources and scope

- Dwork and Roth, [The Algorithmic Foundations of Differential Privacy](https://homepage.divms.uiowa.edu/~sriram/5980/spring17/privacybook.pdf), definition 2.4, proposition 2.1 and composition context. Standard DP definition and secret-independent randomized postprocessing.
- [Modern privacy accounting notes](https://arxiv.org/pdf/2210.00597), proposition 7 and theorem 9. Hockey-stick event characterization and the explicit independent-product premise for convolution.
- Google Research, [Differential privacy accounting by connecting the dots](https://research.google/blog/differential-privacy-accounting-by-connecting-the-dots/). Privacy-profile/accounting context; this repository does not implement Connect-the-Dots.
- Wang, [Modern Tools for Privacy Accounting](https://cseweb.ucsd.edu/~yuxiangw/classes/DPCourse-2021Fall/Lectures/lecture7_modern_tools_annotated.pdf). Hockey-stick divergence and testing interpretation.
- Awan, [Lecture Notes on Differential Privacy](https://jordan-awan.com/DP_notes.pdf). Postprocessing/composition background.
- [Differential Privacy Overview and Fundamental Techniques](https://doi.org/10.48550/arxiv.2411.04710). Background survey, not a numerical authority for these developed fixtures.

This is a small exact reference for supplied finite channels. It does not learn a table from private data, audit a sampler, prove fresh randomness, protect unlisted inputs, certify training, infer a real dataset adjacency, or replace a production accountant/security review. Differential privacy's population-inference limits remain; delta is not a per-person disclosure probability.

# Finite adaptive transcripts, clipped mass and conditional premises

## Input is a conditional mechanism tree

`adaptive(tree, factors)` takes exactly `schema_version`, `secrets`, `neighbors`, `round_outputs`, `steps` in the tree. Schema version is integer 1, not a boolean. Secrets and undirected neighbor edges use the existing channel contract. `round_outputs[i]` is an ordered alphabet of one to eight unique bounded ASCII labels. There are one to six rounds. The Cartesian product has at most 64 transcripts; the number of internal conditional nodes is at most 128. Fixed round alphabets permit arbitrary history-dependent tables, not different alphabets or variable stopping rules.

`steps[i]` contains every index history of length i exactly once, in any input order. Each node has exactly `history` and `probabilities`. A history uses actual integer output indices, not floats or booleans. Its probability matrix has one row per secret and one column per next-round output. Every row sums exactly to 1. All syntactically possible histories are required and validated, even when no secret can reach them. Null-history rows are supplied extensions of the conditional law, not conditional probabilities inferred by dividing zero prefix mass.

The factors argument has one exact rational `t_i >= 1` per round. The factors and their product T are at most 10^12. These are fixed in advance and independent of the transcript. They are multiplicative likelihood factors, not epsilon; epsilon sums correspond symbolically to `ln(T)`. There is no exponential/logarithm rounding in a decision.

The same exact-number rules apply: API integers/Fraction or unsigned decimal/fraction strings, no floats/bools, no row normalization or tolerance. Probability components, constructed transcript probabilities and clipped/removed flow components are bounded to 512 bits per numerator/denominator. Arithmetic that exceeds this domain fails, rather than rounding or silently expanding the accepted problem. Input strings are at most 160 characters; canonical output fraction strings need not obey this input cap. Long exact output values can be submitted again as API `Fraction` values. CLI inputs stay capped at 100000 bytes, so some large valid API trees cannot be supplied through the CLI.

## Exact transcript channel

For secret x and transcript h=(y_1,...,y_k), the chain rule gives

```text
P_x(h) = product_i K_i(x, h_<i, y_i).
```

The implementation propagates prefix masses round by round, retaining the probability of each conditional history under every secret and the indices of reachable secrets. It uses generic transcript output identifiers plus an explicit index/label map, so concatenated user labels cannot collide. The complete resulting finite channel is audited by the existing exact hockey-stick routine at factor T. All directed neighbor pairs, attaining events, support mismatches and pure factors remain in `joint_audit`.

Kernels must be the actual full conditional laws for the intended finite mechanism. Fresh independent coins given the secret are a sufficient special case, not a required restriction of this API. Correlation across rounds can be represented when its effect is correctly included in the history-conditioned laws. The program cannot derive those laws from an arbitrary external sampler or prove that a real program follows them. It never treats a supplied unconditional marginal as the correct conditional law by inference.

## Directional clipped subdistribution certificate

Fix one directed neighbor pair x,x'. Write local distributions p_i(.|h) and q_i(.|h). At each node form a substochastic kernel

```text
c_i(y|h) = min(p_i(y|h), t_i * q_i(y|h)).
local_delta_i(h) = 1 - sum_y c_i(y|h)
                 = sum_y max(p_i(y|h) - t_i*q_i(y|h), 0).
```

Start with incoming good mass g(empty)=1 and propagate `g(h,y)=g(h)*c_i(y|h)`. No normalization occurs. At every node,

```text
incoming_good_mass = removed_mass + sum(child_good_mass)
removed_mass = incoming_good_mass * local_delta_i(h).
```

Consequently all removed mass telescopes: `D_clip = sum_nodes removed_mass = 1 - sum_leaves g`. For every leaf, `g <= P_x` since each c_i<=p_i, and `g <= T*P_x'` since each c_i<=t_i*q_i. Therefore, for any transcript event E,

```text
P_x(E) - T*P_x'(E)
<= P_x(E) - g(E)
<= 1 - sum_leaves g = D_clip.
```

This is a one-sided subdistribution domination proof, not a statement that normalized surviving draws have the original mechanism's distribution. The code reports both directions separately, including every clipped local entry, incoming/removed/child mass, per-round loss, leaf g/P/Q and both nonnegative domination slacks. It asserts flow conservation, leaf inequalities and actual joint delta <= clipped deficit. The global clipped bound is the maximum directional deficit; its maximizing pairs can differ from the actual profile's maximizing pairs.

## Uniform survival and additive bounds

Let d_i be the maximum conditional delta at factor t_i across every history and every directed listed pair. It includes unreachable histories. Each surviving prefix keeps at least fraction `1-d_i`, so good mass after all rounds is at least `product_i(1-d_i)`. Thus every direction satisfies

```text
actual_joint_delta(T)
<= D_clip
<= 1 - product_i(1-d_i)
<= min(1, sum_i d_i).
```

The final inequality is the elementary union bound for numbers in [0,1]. The report retains every d_i, its tied histories, the unclamped sum and the clamped additive bound. These are sufficient bounds for this supplied tree, not an optimal composition result. They are point queries for a specified allocation of factors, not optimization over factor allocations or a whole privacy curve.

## Controls that expose the gaps

The six developed two-round controls use binary secret x. Randomized response (RR) reports x with probability 3/4, so its pure factor is 3. The first three controls use RR for the first release.

| Control | Round factors | Actual delta at T | Clipped deficit | Uniform survival bound | Clamped additive bound |
|---|---|---:|---:|---:|---:|
| Two independent RR releases | 3,3 | 0 | 0 | 0 | 0 |
| RR again if first output is 0, constant 0 otherwise | 1,3 | 3/8 | 1/2 | 1/2 | 1/2 |
| Two independent RR releases | 1,1 | 1/2 | 3/4 | 3/4 | 1 |
| Fair secret-independent first bit, reveal x only after 0 | 1,1 | 1/2 | 1/2 | 1 | 1 |
| Constant first bit 0, reveal x only after impossible 1 | 1,1 | 0 | 0 | 1 | 1 |
| Shared-coin laws: A=x XOR Z, B=Z, P(Z=0)=3/4 | 3,1 | 1 | 1 | 1 | 1 |

For the fair-branch control, the revealing node has conditional delta 1, but only incoming good mass 1/2. Its killed charge is exactly 1/2. The constant branch kills zero. Using only the round's worst local delta loses this branch weighting. In the impossible-history control, the revealing node is still checked and has delta 1, but incoming probability and good mass are both zero, so its killed charge is zero. Omitting that table is still invalid input.

For shared coins, fixing A and comparing secrets makes B deterministic with opposite values: B=A XOR x. Both reachable second-round conditional nodes have delta 1 at factor 1. The transcript supports are disjoint and A XOR B=x. This reproduces the original static shared-coin joint distribution and explicitly exposes why the unconditional marginal factor of B (1) cannot be used as its conditional guarantee. No composition theorem is contradicted.

## Verification and reproducibility

The original 29 static-channel/transform/CLI/SVG tests remain. Fourteen new behavior tests independently reconstruct all flow conservation and leaf inequalities. They use recursive transcript enumeration, distinct from production's layer-by-layer propagation; 24 seeded three-round, three-secret trees are compared with exhaustive all-256-event searches per directed pair. Conditional audits are separately compared with all-event searches. Other checks include the six controls, shared-coin equality with the old report, independent-product equality, exact 10^-100 mass, computed-rational failures, the full six-round/64-leaf/eight-secret/28-edge domain, unary rounds, permutations, node order, omitted edges, nonmutation/RNG state and strict CLI errors.

Three new SVG tests verify all 36 visible numeric cells and their coordinates, both diagram edges, complete compressed JSON metadata, hidden leaf-witness tampering and byte-exact regeneration. Together there are 46 tests. Both old demo/figure artifacts are retained. The six-module wheel reproduces all four full CLI JSON outputs outside checkout; CI covers Python 3.10-3.13 and installed-package parity.

```sh
python -m privacylab adaptive-demo
python -m privacylab adaptive examples/adaptive-input.json
python -m unittest discover -s tests -v
python examples/render_figure.py --check
python examples/render_adaptive.py --check
```

## Attribution and boundaries

This uses established finite probability, hockey-stick divergence, substochastic-kernel domination and DP composition reasoning. It does not claim a new privacy theorem. [Dwork and Roth, The Algorithmic Foundations of Differential Privacy](https://homepage.divms.uiowa.edu/~sriram/5980/spring17/privacybook.pdf), section 3.5, explains composition and adaptive choice of mechanisms. [Whitehouse, Ramdas, Rogers and Wu, Fully Adaptive Composition in Differential Privacy](https://arxiv.org/html/2203.05481v3), provides context on the harder case of adaptively selected privacy parameters, privacy filters and odometers. None of that paper's filters, odometers, advanced bounds or stopping rules is implemented here. The original [design notes](DESIGN.md) cite the static-channel mathematical sources.

This extension is not secure sampling, private training, DP-SGD accounting, a proof of real-data adjacency, unbounded interaction, a privacy filter/odometer, parameter-adaptive accounting, complete privacy-curve enumeration, or optimal/advanced composition. Delta is not a person's probability of a privacy breach. The certificates concern the supplied finite conditional laws and listed edges only.

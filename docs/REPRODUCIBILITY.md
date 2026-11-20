# Reproducibility guide

## Tested configuration

- OpenClaw 2026.9.2 at commit `ea21d360924a53b8ec941c84c29423739d31725f`
- Docker Engine 29.8.2
- DeepSeek V4 Flash requested as `deepseek/deepseek-v4-flash`
- Memory disabled
- Main campaign: six task families, five conditions, and five repetitions per
  cell (150 runs)

The tested OpenClaw commit requires the small Docker build-context fix in
`patches/openclaw-dockerfile.patch`. Apply it to a clean OpenClaw checkout
before running `scripts/build.sh`.

## Evidence levels

The repository separates the following evidence sources:

1. `cases/` contains frozen inputs and effect-based authorization contracts.
2. `campaigns/` contains preregistrations, aggregate oracle outputs, validity
   checks, and records of incomplete campaigns.
3. `examples/reviewer-evidence/primary-findings.json` contains tool-event sequences,
   contracts and snapshots for all 17 primary state findings. All findings have explicit event/effect links and revision-time classifications in `primary-witness-audit.json`.
   `examples/pilot-001/summary.json` retains the first fixture validation.
4. Raw traces remain private because they contain provider and local execution
   metadata not needed to reproduce the reported aggregate results.

The released results establish that the tested failure-recovery mechanism can
produce authorization violations. They do not estimate prevalence across agent
runtimes, models, or application domains.

The original requests name an output destination without an explicit prohibition
on all auxiliary writes. The single-target allowlist is a conservative evaluator
policy; the broader-policy analyses report alternative delegation choices.

## Revision controls

`campaigns/transient-live-20261119T114020Z/guard-analysis.json` records two live
DeepSeek/OpenClaw controls with a one-shot EIO and strict guard: one safe same-target
retry and one authorization request without completion. Build `Dockerfile.transient`
on top of the primary image to reproduce the one-shot route. The preload injector
is disabled for these controls. `scripts/run_transient_review.py` retains every
attempt and reads the ignored local `.env` without printing its credential.

The twelve scripted controls in `recovery-positive-control.json` test guard policy
admission with real file writes; they are not independent model executions.

`python3 scripts/audit_primary_witnesses.py` audits all released primary
state findings under the same scope rule from the released evidence. It does not claim exhaustive
detector recall. The original scanner and original campaign outputs are retained.

The primary file audit checks explicit additional persistent scope; it does not
claim that the keyword scanner computes five-dimensional dominance. The vector
order applies separately when all risk dimensions can be compared.

`python3 scripts/verify_released_evidence.py` recomputes all 29 released state
records (17 primary findings and all 12 prospective wording attempts), then checks
the uniform primary scope audit (16 strict runs, one mixed run; ten historical scanner candidates). This requires neither a model key nor Docker.

## Prospective wording control

`boundary-wording-20261119T125043Z` froze 12 jobs before execution: two families,
original versus clarified requests, and three repetitions per cell under persistent
EIO, with no guard. Original requests produced two state violations in six complete
runs. All five complete clarified runs delivered safely; one clarified attempt hit
a provider idle timeout and its partial snapshot had no violation. Clarification
combines an explicit auxiliary-mutation restriction and safe response options, so
the two components are not separately identified. Build `Dockerfile.boundary` and
run `scripts/run_boundary_review.py` to reproduce the protocol. All tool-event and
snapshot records are in `examples/reviewer-evidence/boundary-wording-findings.json`.

## Offline validation

Run `python3 scripts/run.py --self-test`. This tests both a positive fixture
with unauthorized replacement and mode change and a negative fixture with an
allowed creation. It requires no model credential or network.

## Live execution

Build the two images with `scripts/build.sh`, create a restricted Docker
network for the model endpoint, export the provider key in the invoking shell,
and run one case or all four as documented in the root README. Each attempt
receives fresh workspace and state volumes and is retained whether it succeeds
or fails.


## Trajectory-label correction

The primary state count remains 17/120. The revision-time audit confirms 16
strict recovery witnesses under an explicit persistent-scope rule. It includes
six probe trajectories missed by the original keyword scanner. The remaining
run edited protected files before failure and later created a probe, so its
post-failure scope effect is recorded but the run is excluded from strict
attribution. Original scanner labels and campaign outputs are not overwritten.
Policy-sensitive counts and linked calls are retained in the audit JSON.
The separate output, scratch and probe policies are not cumulative.

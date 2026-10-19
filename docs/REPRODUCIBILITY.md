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

The repository distinguishes three evidence levels:

1. `cases/` contains frozen inputs and effect-based authorization contracts.
2. `campaigns/` contains preregistrations, aggregate oracle outputs, validity
   checks, and records of incomplete campaigns.
3. `examples/pilot-001/summary.json` contains the first de-identified fixture
   validation.
4. Raw traces remain private because they contain provider and local execution
   metadata not needed to reproduce the reported aggregate results.

The released results establish that the tested failure-recovery mechanism can
produce authorization violations. They do not estimate prevalence across agent
runtimes, models, or application domains.

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


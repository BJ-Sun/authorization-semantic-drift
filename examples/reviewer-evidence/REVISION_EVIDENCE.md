# Revision evidence

`primary-findings.json` contains all 17 primary final-state findings, including the ten registered trajectory labels. The exporter selects tool calls and results, authorization contracts, synthetic user messages, snapshots and oracle outputs from retained runs. It excludes provider envelopes and hidden reasoning. Run `python3 scripts/export_review_evidence.py` from the lab directory to reproduce it.

The EIO finding and trajectory label refer to the same run: CART-AUDIT-IO, repetition 2. Its first registered failure is event 19; the auxiliary shell write is event 30. Earlier manuscript text describing different runs was incorrect. The pre-failure protected-file event belongs to COMPLIANCE-READONLY, repetition 1.

`recovery-positive-control.json` records a scripted integration test of the actual guard policy and real file writes inside a network-isolated container. Six synthetic contents are executed with and without guarding. The first write returns a one-shot EIO and a scripted same-target retry completes. These twelve deterministic controls test policy admission, not autonomous model behavior or twelve independent model samples. The reproduction script is `scripts/recovery_positive_control.mjs`.

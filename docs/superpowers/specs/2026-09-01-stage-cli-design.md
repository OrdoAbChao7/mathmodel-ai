# Stage CLI Design

The CLI now exposes the existing pipeline evaluators as focused, read-only commands:

`frame` covers inventory and G1; `screen` covers artifact/quality/page diagnostics; `select` covers G2/G3; `validate` covers contracts and G4/G5; `freeze` covers G5.5/G6; `review` covers G7/G8 and competition-max extensions; `signoff` and `compliance` expose G0/H1–H4.

Each command returns a structured stage status and nested evaluator reports. No command bypasses `audit`, `package`, or G9 release authority, and all formal gates remain blocking when their underlying evaluator fails.

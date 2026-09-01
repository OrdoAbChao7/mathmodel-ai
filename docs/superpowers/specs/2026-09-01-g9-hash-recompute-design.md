# G9 Hash Recompute Design

The final submission evaluator no longer treats a `status: PASS` hash row as evidence by itself. Every row must identify a unique project-relative file and contain an expected SHA-256 digest; G9 recomputes the digest locally, rejects path escapes, missing files, duplicate paths, malformed rows, and mismatches.

This keeps the existing generated hash list useful while making release integrity an observed property of the current workspace rather than an assertion copied from a prior report.

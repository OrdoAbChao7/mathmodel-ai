# G9 Report Provenance Design

G9 now verifies that the quality report's `source_manifest` and `reproducibility_summary` exist inside the project, that the summary's configuration hash matches the current `mathmodel.json`, and that every source-manifest file hash matches the current workspace. The manifest must include the configuration itself and cannot contain duplicate or unsafe paths.

This prevents a stale audit report from being combined with changed source files and then treated as a current formal submission. The existing per-artifact release hash checks remain in force as a second, narrower integrity layer.

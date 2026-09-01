# Phase 7 — External Capability Adapters

## Goal

Expose selected external knowledge and review capabilities without allowing them to control canonical pipeline state or final release authority.

## Contracts

`mathmodel-skill/config/external-sources.yaml` records repository, immutable 40-character commit pin, license state, integration mode, capabilities, authority, and attribution. `UNVERIFIED` licenses are metadata-only and permit no bulk copying.

`mathmodel-skill/config/capability-registry.yaml` gives every capability exactly one local owner and explicitly sets `external_decision_allowed: false`. XiaoMa is a lazy-loaded knowledge provider; ARS is findings-only; AutoMCM and zhnnky provide abstract workflow concepts only.

The adapter resolver returns a bounded manifest and never executes external code, changes frozen results, selects the final model, or declares release success. Floating branches, unregistered providers, source-capability mismatches, duplicate IDs, and malformed records fail closed.

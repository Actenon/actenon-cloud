# Contract Tests

These tests validate high-signal compatibility between Actenon Cloud and pinned
open-kernel artifacts.

Current scope:

- PCCB issuance conformance against a pinned kernel-facing PCCB schema fixture
- round-trip verification of a known-good PCCB artifact fixture
- structured refusal when a kernel Action Intent contract is mutated

The repository does not currently carry an official published kernel PCCB schema.
Until the upstream kernel repo exposes one directly, `tests/contract/fixtures/`
holds the pinned local compatibility fixtures that these tests enforce.

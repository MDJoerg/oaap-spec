# oaap-spec

The specification of **OAAP — the Open Application & Automation Platform**.

OAAP is an open platform specification with an open-source reference
implementation for applications, data, AI, and integrations. Its goal is
digital sovereignty and freedom of choice — especially for small businesses.
This repository defines **what** the platform must be able to do
(capabilities); implementations such as [oaap-reference](https://github.com/MDJoerg/oaap-reference)
define **how**. Any provider (Docker Compose, Kubernetes, cloud platforms
such as SAP BTP) can implement this specification and prove compliance
through conformance tests.

Guiding principles: Open First · Capability First · Local First ·
User Choice · Secure by Default · Portable by Default.

## Repository layout

- `rfcs/` — proposals for new or changed specification content (see process below)
- `spec/` — the normative specification, one document per capability (created as RFCs are accepted)
- `docs/` — supporting, non-normative documentation
- `adr/` — decisions scoped to this repository

## Process

Specification work is proposal-driven:

1. **RFC** (Request for Comments): a numbered proposal in `rfcs/`,
   status `Draft` → discussed → `Accepted` or `Rejected`.
2. **Spec**: accepted RFCs are worked into normative capability
   specifications under `spec/`.
3. **Conformance**: every capability specification defines conformance
   tests; an implementation is OAAP-conformant for a capability when it
   passes them.

Program-level decisions (vision, priorities, personas) live in the
`oaap-root` repository and are made there.

## Status

Bootstrap phase. First proposal: [RFC-0001 — Capability Model](rfcs/RFC-0001-capability-model.md) (Draft).

## Language

The specification and all technical documentation in this repository are
written in English.

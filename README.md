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
- `schema/` — machine-readable schemas for the formats the specification defines
  - `oaap-app.schema.json` — the app manifest (`oaap-app.yaml`), RFC-0004
  - `oaap-store.schema.json` — the store list (`oaap-store.json`), RFC-0012
- `docs/` — supporting, non-normative documentation
- `adr/` — decisions scoped to this repository

The two schemas differ on purpose in how strict they are. The manifest
schema rejects unknown fields; the store list schema does not, because a
node in the field must be able to read a list that is newer than itself
(RFC-0012 §8.2). Strict checking of store lists belongs in the authoring
tools, which also warn about unknown vocabulary values.

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

RFC-0001 to RFC-0012 accepted; see the [RFC index](rfcs/README.md).
Normative capability specifications exist for host, identity, gateway,
portal, app runtime, updates and backup.

## Language

The specification and all technical documentation in this repository are
written in English.

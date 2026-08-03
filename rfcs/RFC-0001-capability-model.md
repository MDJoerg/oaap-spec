# RFC-0001: The OAAP Capability Model

- **Status:** Accepted (2026-08-03)
- **Date:** 2026-08-03
- **Authors:** Claude (proposal), Jörg (review & decision)

## Summary

This RFC defines the core concept of the OAAP specification: the
**capability**. A capability is a clearly specified building block of the
platform. The specification describes *what* a capability provides; a
*provider* implements *how*. Conformance tests connect the two: an
implementation is OAAP-conformant for a capability when it passes that
capability's conformance tests.

## Motivation

OAAP separates specification (`oaap-spec`) from implementation
(`oaap-reference` and, later, other providers such as Kubernetes
distributions or cloud platforms). This separation only works if the
specification has a precise, testable unit of definition. The capability
is that unit. It also gives the program a natural planning currency:
roadmap items, pilot requirements, and provider claims can all be
expressed as capabilities.

## Definitions

- **Platform**: an installed, running OAAP system (e.g. a mini PC running
  Debian + Docker at a small business).
- **Capability**: a specified building block of the platform, identified
  by a namespaced ID (e.g. `oaap.core.identity`).
- **Provider**: an implementation stack that realizes capabilities
  (e.g. the Docker Compose reference implementation).
- **Conformance**: a provider's proven compliance with a capability
  specification, demonstrated by passing its conformance tests.
- **App**: an installable application running on the platform, consuming
  capabilities through their specified interfaces.

## Capability specification format

Every capability specification in `spec/` MUST contain:

1. **Purpose** — the problem the capability solves, in one paragraph.
2. **Interface** — the API or contract that apps and other capabilities
   rely on.
3. **Configuration** — what operators can and must configure.
4. **Security requirements** — authentication, authorization, data
   protection expectations (Secure by Default).
5. **Conformance tests** — precisely described test cases that define
   compliance. Tests start as descriptions; executable test suites are
   built up alongside the reference implementation.
6. **Dependencies** — the capabilities this capability requires,
   listed explicitly by ID.
7. **Maturity** — `draft`, `beta`, or `stable`.

## Namespaces

Capabilities are organized in namespaces:

- `oaap.core` — platform foundation: host baseline, web portal,
  identity, configuration, secrets
- `oaap.apps` — application runtime and app store
- `oaap.data` — persistence: files, databases, backup
- `oaap.net` — connectivity: remote access, integration
- `oaap.ai` — intelligence: inference, agents
- `oaap.ux` — user experience: visual language, UI contracts

Namespaces are extensible; new ones require an RFC.

## Initial capability set

Driven by the first pilot (a five-person installation business needing
reliable on-site documentation and sign-off) and the founder's home lab,
the first capabilities to be specified are, in order:

1. `oaap.core.host` — the initial installer/bootstrap: takes a prepared
   operating environment (a provider prerequisite, e.g. Debian + Docker)
   to a running platform and hands over to the web portal for all further
   setup; onboarding as simple as consumer NAS/router setup
2. `oaap.core.portal` — the web UI where everything else is configured
3. `oaap.core.identity` — users, authentication, roles (see RFC-0002)
4. `oaap.core.gateway` — central HTTP entry point enforcing
   authentication for all apps (see RFC-0002)
5. `oaap.apps.runtime` — installing and operating apps
6. `oaap.data.files` — file/photo storage including backup
7. `oaap.net.remote-access` — secure external access (e.g. WireGuard)
   for field devices

## Versioning

- The specification repository is versioned as a whole using semantic
  versioning, starting at `0.x` (breaking changes allowed until `1.0`).
- Each capability specification carries its own version and maturity
  level, so capabilities can stabilize independently.

## Future candidates (not part of this RFC)

Collected at program level and to be proposed as separate RFCs:
digital twin and further Industry 4.0 concepts (expected to add
persistence and integration capabilities), partner/external service
integration, smart-home connectivity.

## Out of scope

- Concrete technology choices (these belong to providers)
- App-level functionality (apps consume capabilities; they are not
  capabilities themselves)

## Resolved questions

1. **Conformance tests** start as precisely described test cases;
   executable suites are built up alongside the reference implementation
   (decided 2026-08-03).
2. **`oaap.core.host` granularity**: the operating-system baseline
   (e.g. Debian + Docker) is a provider prerequisite; the capability
   covers the initial installer that bootstraps the platform and hands
   over to the web portal (decided 2026-08-03).
3. **Dependencies** are declared explicitly per capability (section 6 of
   the specification format). Namespaces form layers: `oaap.core` is the
   foundation every platform MUST provide; all other namespaces build on
   it. Security is part of the foundation — see RFC-0002 for the
   security-first access model (identity, gateway, standard roles).

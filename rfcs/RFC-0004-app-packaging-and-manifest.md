# RFC-0004: App Packaging — Neutral Manifest and App Types

- **Status:** Draft
- **Date:** 2026-08-03
- **Authors:** Claude (proposal), Jörg (review & decision)
- **Depends on:** RFC-0001 (capability model), RFC-0002 (security-first
  access model), RFC-0003 (platform topology)

## Summary

Every OAAP app is described by a **neutral, runtime-independent
manifest**. The platform uses it to install, wire, and operate the app;
the user only ever picks an app and clicks install. The manifest
supports several **app types** — from fully self-developed apps whose
container images are built directly on the target device, to thin
wrappers around existing third-party container software. Because the
manifest describes only the *what*, any conformant provider can map it
to its runtime: Docker Compose today, Kubernetes later.

## Motivation

- The first pilot app (installation documentation for a five-person
  business) is a self-developed web app that must move from "runs on a
  laptop" to "installed on the platform in one click".
- The self-hosting world already has excellent software shipped as
  container images; OAAP must make adopting it trivial rather than
  competing with it.
- Two guiding decisions from program level (ADR-0005 addendum):
  technical complexity is hidden from the end user, while the
  technically versed user finds familiar standards behind the scenes;
  and images can be **built on the device**, which also sidesteps
  multi-architecture publishing for self-developed apps.

## Proposal

### The manifest

One declarative document per app (format: YAML, final call in the
capability spec). It describes:

1. **Identity** — app id, display name, version, description, icon.
2. **Type** — see app types below.
3. **Services** — the containers the app consists of: image references
   *or* build contexts, per-service resources and architecture notes.
4. **Required capabilities** — explicit IDs + minimum versions
   (e.g. `oaap.data.files >= 0.1`), mirroring RFC-0001 dependencies.
5. **Routes & roles** — HTTP routes to publish through the gateway,
   required roles per route, explicit `public` exceptions (RFC-0002:
   apps declare which standard roles they support and what each may do).
6. **Storage** — persistent volumes/data the platform must provision
   and include in backups.
7. **Configuration** — a schema of operator-editable settings, rendered
   as a form in the portal (no config files for end users).
8. **Placement hints** — optional node requirements per RFC-0003
   (e.g. "needs GPU", "location: site X"); the admin decides final
   placement.

The manifest contains **no runtime-specific instructions** (no compose
or Kubernetes fragments in the core schema). Providers translate the
manifest into their runtime.

### App types

| Type | Description | Typical author |
| ---- | ----------- | -------------- |
| `native` | Self-developed app with build contexts; images are built on the target platform (build on device) | Bernd's Montage-App, spec-driven custom apps |
| `image` | Prebuilt (ideally multi-arch) images published in a registry, full OAAP manifest | OAAP community & partners |
| `wrapped` | Thin manifest around existing third-party container software; images come from the internet and are not authored for OAAP | Adopting the self-hosting ecosystem |

All three types use the same manifest; they differ only in how services
are sourced. Conformance requirements are identical — in particular
routes/roles and storage MUST be declared so the platform can enforce
security and backups regardless of app origin.

### User experience contract

- Install = choose app in the portal → platform resolves the manifest,
  builds or pulls images, provisions storage, registers gateway routes,
  shows the configuration form. No terminal, no compose files.
- The technically versed user can inspect what actually runs (standard
  containers, standard reverse proxy) — nothing is proprietary or
  obfuscated.

### Security

- Apps never configure the gateway directly; the platform derives route
  configuration from the manifest (default deny stays intact even for
  `wrapped` apps with no own auth).
- Apps receive identity and roles via the platform contract (RFC-0002);
  manifests declare, the platform enforces.

## Out of scope (future RFCs)

- Store infrastructure: curated/uncurated directories, distribution
  channels (candidate: Git-based delivery), provider implementations
  shipped as apps.
- App updates and rollback (belongs with the update capability).
- Inter-app APIs and eventing.

## Open questions

1. Manifest format details and schema versioning (YAML assumed).
2. Trust: signing of manifests and images, especially for `wrapped`
   apps with third-party images.
3. Resource limits/quotas per app on small hardware.
4. How much compose compatibility `wrapped` should offer (import
   existing compose files vs. re-declare).

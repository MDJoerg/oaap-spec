# RFC-0003: Platform Topology — Controller and Worker Nodes

- **Status:** Accepted (2026-08-03)
- **Date:** 2026-08-03
- **Authors:** Claude (proposal), Jörg (review & decision)
- **Depends on:** RFC-0001 (capability model), RFC-0002 (security-first access model)

## Summary

An OAAP platform consists of exactly one **controller node** and zero or
more **worker nodes**. A single machine running everything is the default
and MUST always remain fully supported. Worker nodes extend a platform to
additional machines — a Raspberry Pi at a remote location, a dedicated box
for local AI services — while the controller remains the single place for
administration, updates, and access control. This is deliberate service
*placement*, not cluster *orchestration*: no automatic scheduling, no
failover, no Kubernetes.

## Motivation

The pilots show a natural growth path that is not a cluster:

- **Installation business (pilot 1)**: starts with one mini PC. Later, a
  dedicated node for AI services may be added without touching the
  central host.
- **Home lab**: a central host with management services, plus a Raspberry
  Pi in an outbuilding ("Schuppen") serving that location, plus possibly
  an AI box.

Small operators grow by plugging in another device, not by migrating to a
distributed system. The platform must make "plug in another device" a
first-class, centrally managed operation — otherwise every added device
becomes a second, unmanaged installation.

## Definitions

- **Controller node**: the node running the platform's core capabilities
  (portal, identity, gateway, app management). Every platform has exactly
  one.
- **Worker node**: an additional machine attached to a platform. It runs
  assigned apps/services and is fully managed by the controller. Workers
  have no own portal and no own user store.
- **Landscape**: the set of all nodes forming one platform.

## Proposal

### Topology model

- A platform is `1 controller + 0..n workers`.
- Single-node (controller only) is the default installation and the
  Phase-1 pilot setup.
- Typical worker motivations: physical location (serve a site locally),
  special hardware (GPU/NPU for AI), isolation of heavy services.

### Installer modes (`oaap.core.host`)

The installer capability gains explicit modes:

1. **bootstrap** — create a new platform on this machine (controller),
   then hand over to the portal (unchanged from RFC-0001).
2. **join** — attach this machine to an existing platform as a worker.
3. **remote join** — the controller provisions a worker remotely over
   SSH, initiated from the portal: the admin enters address and
   credentials of a prepared machine (provider prerequisite, e.g. Debian
   + container runtime + SSH access); the platform does the rest. This is
   the preferred path — it keeps the NAS-simple onboarding promise even
   for multi-node setups.

### Central administration

- Configuration, updates, health monitoring, and backup coordination for
  **all** nodes flow through the controller. A worker is never
  administered directly.
- The update service on the controller keeps workers at compatible
  versions automatically.
- **Whole-landscape health responsibility**: end users think in terms of
  the central view only — the platform (controller) is responsible for
  the health of the entire landscape and presents it in the portal.
- **Local health command**: every node (controller and worker)
  additionally provides a minimal command-line health status (see
  `oaap.core.host`) for diagnosis by technicians and service partners.
  End users are never required to use it.

### Degraded operation (controller unreachable)

- A worker whose controller is unreachable **keeps its services
  running**. It buffers logs, events, and outbound actions in a local
  queue for a bounded emergency period (configurable, on the order of
  hours) and delivers them once the controller is reachable again.
- During the outage the worker's apps are **not reachable through the
  central gateway** — from the user's perspective the worker is offline,
  even though its services continue to run locally.
- Behavior when the emergency period is exceeded (queue overflow,
  alerting) is defined in the `oaap.core.nodes` capability spec.

### Service placement

- Apps and capability services can be **assigned to a node** by the
  admin (e.g. AI inference on the GPU node, a location service on that
  location's Pi). Assignment is explicit; there is no automatic
  scheduling or rescheduling. Out of scope in this RFC: failover,
  replication, load balancing.

### Security

- Controller–worker communication runs over a mutually authenticated,
  encrypted channel; workers trust exactly one controller.
- The gateway on the controller remains the single HTTP entry point of
  the platform (RFC-0002). Apps on workers are published through it.

## Impact on the capability set

- `oaap.core.host` (RFC-0001) is specified with the mode concept from the
  start, even though v0.1 only implements `bootstrap`. This keeps the
  spec forward-compatible without re-architecting.
- A future capability `oaap.core.nodes` (node registry, join/remove,
  placement, node health) will carry the multi-node functionality; it is
  **not** part of the initial capability set.

## Phasing

- **Spec v0.1 / Phase 1 (pilot)**: single-node only; `oaap.core.host`
  defines the modes, implements `bootstrap`.
- **Later phase**: `join` / `remote join` and `oaap.core.nodes`,
  driven by the home-lab and AI-node use cases.

## Out of scope

- Cluster orchestration semantics (scheduling, failover, replication).
- Multi-controller / high availability.
- Non-Linux nodes.

## Resolved questions

1. **Offline behavior** (decided 2026-08-03): workers keep running and
   buffer logs/events/actions for a bounded emergency period; they are
   not reachable through the central gateway while the controller is
   down. See "Degraded operation" above.
2. **Mixed versions** (decided 2026-08-03): temporary version differences
   between nodes during updates are expected and must be tolerated. How
   updates roll out across a multi-node landscape — robust and
   user-friendly, including platform self-update — will be defined
   explicitly in the update/nodes capability specs before multi-node
   ships.

## Open questions

1. Transport and trust bootstrap between controller and worker (SSH-based
   agent? mTLS with enrollment token?) — to be answered in the
   `oaap.core.nodes` capability spec.
2. Default length of the worker emergency buffering period, and behavior
   on queue overflow.
3. Concrete self-update mechanism of the platform (robust, user-friendly)
   — direction still open at program level.

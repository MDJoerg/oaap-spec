# Capability Specifications

Capability specs follow the format defined in
[RFC-0001](../rfcs/RFC-0001-capability-model.md): Purpose, Interface,
Configuration, Security requirements, Conformance tests, Dependencies,
Maturity. Files are named after the capability ID.

Specs marked **outline** contain only Purpose and an interface sketch;
they exist so that neighboring specs can reference stable interfaces
before the full specification is written.

## Index

- [oaap.core.host](oaap.core.host.md) — platform installer & node baseline (draft, v0.3.5)
- [oaap.core.updates](oaap.core.updates.md) — one update engine per node, three triggers: a node updates its platform core from its recorded source, shows what would change first, and never touches app instances or user data (draft, v0.1.3)
- [oaap.core.portal](oaap.core.portal.md) — web portal (draft, v0.3.22)
- [oaap.core.management](oaap.core.management.md) — the tenant's own hand on the platform as an API: the cohort commands under `/api/v1/tenant`, for a session or an API key, jobs for what takes minutes, a template uploaded as ZIP, the handout as a one-time ZIP with a password the trainer chooses (draft, v0.1)
- [oaap.core.identity](oaap.core.identity.md) — identity & roles (draft, v0.6.0)
- [oaap.core.gateway](oaap.core.gateway.md) — HTTP gateway (outline, v0.2.15)
- [oaap.apps.runtime](oaap.apps.runtime.md) — app runtime: install, instances, contract delivery, remote deployment (draft, v0.2.35)
- [oaap.data.backup](oaap.data.backup.md) — platform backup, restore & relocation (draft, v0.4)
- [oaap.fleet.status](oaap.fleet.status.md) — read-only fleet status document & fleet keys (draft, v0.3)
- [oaap.ai.gateway](oaap.ai.gateway.md) — AI supply behind one keyed, OpenAI-compatible endpoint (draft, v0.2)
- [oaap.core.tenant](oaap.core.tenant.md) — account and tenant, the boundary of belonging (draft, v1.0)
- [oaap.data.store](oaap.data.store.md) — managed Postgres per node, schema per tenant/purpose (draft, v0.1)
- [oaap.data.model](oaap.data.model.md) — type registry for the digital twin: object/attribute/group/relation/activity types, origin, binding (draft, v0.1)
- [oaap.data.files](oaap.data.files.md) — where the bytes live: the node's own content-addressed store, tenant-isolated by path, put/get/verify by hash; external backings are RFC-0034 Stufe 4 and not yet specified (draft, v0.1.1)
- [oaap.data.twin](oaap.data.twin.md) — the digital twin: objects, groups, relations, activities per tenant, append-only, behind its own gateway route; validity/tree/merge and a person-facing API for the twin browser since v0.2; the outbox relay (publishes every event to the broker) and the `states` table since v0.3; a read-only remote reader on another node, through a tunnel, since v0.4 (draft, v0.4)
- [oaap.net.destinations](oaap.net.destinations.md) — named targets of a tenant an instance is bound to: HTTP through a gateway listener that knows its caller by network and adds the credential the app never sees, TCP as a handover said out loud, no bindings in a rehearsal; since 0.2 also `via` a tunnel; since 0.3 bound from the portal, by `server_admin` and the tenant's own `tenant_admin` (draft, v0.3)
- [oaap.net.connector](oaap.net.connector.md) — the inner node dials out and offers backends by name, the outer node sees names, never addresses: connect keys bound to one tenant, the offer list and the off switch inside, `via` destinations outside; RFC-0033 stages 2 and 3 — since 0.2 also exposures: a random public name for one target, from the inner node or a laptop, login by default, a TTL; since 0.3 opened/extended/closed from the portal too, `server_admin` only (draft, v0.3)
- [oaap.net.remote-access](oaap.net.remote-access.md) — a time-boxed access into one instance network for a named person: the object, its lifecycle, the tenant audit trail, and (since 0.2) a real port forward, one WebSocket per TCP connection, checked against the holder's own key on every one; (since 0.3) the WireGuard peer's mechanics, measured on a real node and found blocked by a Docker hardening feature; (since 0.4) redesigned so the peer joins as a genuine Docker bridge port instead of being routed in, one namespace per instance, measured carrying real traffic end to end and correctly excluding the gateway; (since 0.5) measured against a real `wg-quick` client and across a real node reboot, three more defects found and fixed — still CLI-only (draft, v0.5)
- [oaap.events.broker](oaap.events.broker.md) — the MQTT broker per node: topic tree, node profile `broker`, auth against identity; the platform principal `oaap.relay` the twin's relay publishes with since v0.2 (draft, v0.2)

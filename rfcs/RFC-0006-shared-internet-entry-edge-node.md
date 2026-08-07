# RFC-0006: Shared Internet Entry — the Edge Node

- **Status:** Accepted (2026-08-07)
- **Date:** 2026-08-07
- **Authors:** Claude (proposal), Jörg (question & decision)
- **Depends on:** RFC-0002 (gateway, default deny), RFC-0003 (topology),
  RFC-0005 (addressing, platform CA)

## Summary

A household or small business has **one public IP address and exactly
one pair of ports 80/443** that a consumer router can forward to
**one** machine. As soon as a second OAAP platform exists on the same
uplink, it cannot be reached from the internet at all. This RFC
introduces the **edge node**: an ordinary OAAP node that additionally
accepts requests for **other platforms' hostnames**, terminates TLS for
them, and forwards each request to the platform that owns the name.

The edge shares **nothing but the entry point**. Users, roles, apps,
updates and backups stay with each platform. This is deliberately *not*
RFC-0003's controller/worker relationship: the platforms behind an edge
remain autonomous and may belong to different owners.

## Motivation

The real situation that triggered this (2026-08-07):

- Two independent platforms sit on one uplink: `oaap-demo` (the
  operator's own demo and services host) and `oaap-bernd` (the pilot
  customer's platform, which will physically move to the customer
  later). Both need to be reachable from the internet — the customer's
  platform in particular serves the **deploy hook** its AI agent uses.
- The router can forward 80/443 to only one of them. Today this forces
  an either/or decision between the pilot and the demo host.
- Choosing different external ports is not a workaround: ACME
  certificate issuance requires port 80 (HTTP-01) or 443 (TLS-ALPN-01)
  exactly.

This is not a niche problem. It is the **normal case behind a consumer
router** and will recur at every operator who runs more than one node,
and at every service partner hosting several customers' platforms in
one location.

A second finding from the same day belongs here: the public DNS name of
the pilot platform pointed at a **stale IP address** and nobody
noticed — external access, including the deploy hook, had been silently
dead. Whoever owns the public entry point must also own **keeping the
public name correct** and must detect when it goes stale.

## Constraints

1. **One uplink, one port pair.** Not negotiable at the router.
2. **ACME needs the standard ports.** A platform without reachable
   80/443 cannot obtain public certificates on its own.
3. **Autonomy must survive.** The pilot platform belongs to the
   customer and moves out later; merging it into the operator's
   platform (RFC-0003 worker) would be wrong — it has its own users,
   its own admin, and its own data responsibility.
4. **No plaintext identity trust.** Chaining HTTP hops must not weaken
   RFC-0002's guarantee that identity headers cannot be spoofed.

## Proposal

### Roles

- **Edge node** — an OAAP node that owns the public entry point:
  it holds the router's port forwarding, maintains the public DNS
  name(s), terminates TLS, and forwards requests it does not serve
  itself to the responsible platform. An edge is a normal platform in
  every other respect; "edge" is a **role**, not a product variant, and
  it is off by default.
- **Backend platform** — a full, autonomous OAAP platform reachable
  from the edge over the local network. It keeps its own portal,
  identity, apps and administration.

This is the first concrete node role beyond RFC-0003's controller and
worker, and it is orthogonal to them: a backend platform behind an edge
may itself be a controller with its own workers.

### Routing

- The routing key is the **requested hostname** (TLS SNI and the
  `Host` header). The edge holds a mapping table
  `hostname pattern → backend address`, e.g.
  `oaap-bernd.example.org` and `*.oaap-bernd.example.org` →
  `10.10.10.95`.
- Wildcards MUST be supported: RFC-0005 level 3 gives every app
  instance its own subdomain, so a backend platform owns a whole
  hostname subtree.
- Names not in the table are served by the edge itself. There is no
  fallback forwarding — an unknown name MUST NOT reach a backend.
- The mapping is explicit administrator configuration. There is **no**
  discovery protocol and no automatic registration of backends.

### TLS

- **Terminating edge is the defined mode**: the edge obtains and renews
  certificates for **all** names it serves, including the backends'.
  This follows from constraint 2 — only the edge can answer ACME
  challenges on the standard ports.
- The hop **edge → backend** SHOULD be encrypted again using the
  platform CA established in RFC-0005 (resolved question 2), and MUST
  be encrypted whenever the network between edge and backend is not
  fully under the operator's control.
- **Passthrough mode** (forwarding the encrypted connection by SNI
  without decrypting, so the backend keeps its own certificates) is
  **out of scope** here: it requires the backend to obtain certificates
  by DNS-01 challenge, which needs provider-specific DNS credentials on
  the backend. Recorded as future work.

### Behind-edge mode on the backend

A backend platform MUST be told that it is behind an edge, because two
of its current behaviours are wrong in that position:

1. **HTTP→HTTPS redirect.** A backend that redirects the edge's
   forwarded HTTP request to HTTPS creates a redirect loop. In
   behind-edge mode the redirect for that hostname is disabled and the
   backend trusts `X-Forwarded-Proto`.
2. **Forwarding headers.** `X-Forwarded-Proto` and `X-Forwarded-For`
   MUST be accepted **only** from the configured edge address and
   rejected otherwise — otherwise any LAN client could claim to be
   the edge.

Contract guarantee 2 (apps receive the original `Host`) must hold
through the chain: the edge forwards the hostname unchanged.

### Security

- **Identity headers stay safe.** Every OAAP gateway strips
  `X-OAAP-User` and `X-OAAP-Roles` from incoming requests and sets them
  itself after authentication (RFC-0002, contract guarantee 1). The
  backend's gateway therefore discards whatever the edge sent and
  authenticates against **its own** identity service. Chaining gateways
  is safe by construction, and the backend does not have to trust the
  edge for authentication.
- **Sessions and cookies stay separate.** Each platform authenticates
  under its own hostname, so session cookies are naturally scoped per
  platform. Single sign-on across platforms is explicitly **not** part
  of this RFC.
- **The edge sees plaintext.** It terminates TLS and can therefore read
  and log everything that passes through, including the backend's
  traffic. This is acceptable only when the edge operator is trusted by
  the backend's owner. Where they differ (an operator hosting a
  customer's platform), this MUST be an explicit, documented agreement,
  and the edge MUST NOT log request bodies.
- **Backends must not be exposed directly.** The port forwarding stays
  exclusively with the edge.
- The internet-hardening profile (rate limiting, brute-force
  protection, automatic security updates) applies to the edge, since it
  is the machine facing the internet.

### Owning the public name

The edge owns the public address end to end:

- It holds (or is the documented single place for) the **DynDNS
  update**. Exactly one component updates the public name; the
  recommended place is the router, which notices the change first.
- The platform MUST **detect a stale public name**: compare the address
  the public name resolves to against the actual public address, and
  report a health error when they diverge. The 2026-08-07 incident
  showed this failure is silent otherwise — everything looks healthy
  locally while the platform is unreachable from outside.

### What is explicitly NOT shared

Users, roles, sessions, app registries, updates, backups, monitoring
responsibility. An edge failure makes backends **unreachable from the
internet**; it does not affect their local operation, their LAN entry
points, or their data.

## Consequences

- `oaap.core.gateway` gains: the edge routing table, certificate
  management for foreign names, and behind-edge mode (redirect
  suppression, restricted trust in forwarding headers).
- `oaap.core.host` / CLI gains commands to manage the routing table
  (e.g. `oaap edge add <hostname> <target>`, `list`, `remove`) and to
  switch a backend into behind-edge mode.
- `oaap.core.portal` gains an administration view for the routing table
  and shows, per entry, whether the backend currently answers.
- Health monitoring gains the stale-public-name check described above.
- The node-role concept (controller, worker, **edge**) should be
  reflected when RFC-0003 is next revised.

## Out of scope

- SNI passthrough without decryption (future work, needs DNS-01).
- Single sign-on or user federation across platforms.
- Load balancing, failover, or multiple edges for one name.
- Non-HTTP protocols (MQTT and friends) — same open gap as elsewhere.

## Resolved questions (decided by Jörg, 2026-08-07)

1. **Trust arrangement:** Yes — the edge also serves a co-located
   customer platform, and the local hop edge → backend may run
   unencrypted. The agreement with the customer (the edge can read the
   traffic) is made personally by the operator; for the pilot this is a
   transitional arrangement until the platform moves to the customer's
   own uplink.
2. **Re-encryption edge → backend:** built **later as an option**, once
   the prerequisites (platform CA, RFC-0005) exist. This RFC does not
   wait for it.
3. **Backend-down page: configurable, with templates.** Sometimes it is
   better to reveal little — the range goes from a plain text notice
   over an OAAP-styled page (which has marketing value and may carry
   links to OAAP) up to an individually designed page. The same page
   mechanism is also wanted for **deliberately taking routes offline**
   (maintenance, or "pulling the virtual cable" on suspected
   intrusion) — that broader capability is recorded at program level
   and will get its own spec treatment; the gateway spec must design
   the unavailability page so both cases share it.
4. **Routing table:** owned by the edge administrator alone (the
   server's owner — edge-admin role). Backends do not confirm.

## Deutsche Zusammenfassung

**Das Problem:** Hinter einem Router gibt es eine öffentliche IP-Adresse
und genau **ein** Paar Ports 80/443, das sich auf **eine** Maschine
weiterleiten lässt. Sobald eine zweite OAAP-Plattform am selben
Anschluss steht, ist sie aus dem Internet gar nicht erreichbar. Andere
Ports helfen nicht: Für die automatischen Zertifikate (Let's Encrypt)
sind genau 80 und 443 nötig.

**Der Vorschlag:** Ein Knoten übernimmt die Rolle des **Edge-Knotens**.
Er allein bekommt die Portfreigabe, kümmert sich um die Zertifikate für
**alle** Namen und leitet anhand des angefragten Hostnamens an die
zuständige Plattform weiter (`*.oaap-bernd.…` → 10.10.10.95). Jede
weitere Plattform kommt damit **ohne Router-Änderung** dazu.

**Wichtig:** Geteilt wird nur der Eingang. Benutzer, Rollen, Apps,
Updates und Backups bleiben bei jeder Plattform — das ist ausdrücklich
**nicht** das Controller/Worker-Modell aus RFC-0003. Bernds Plattform
bleibt Bernds Plattform und kann später zu ihm umziehen.

**Sicherheit:** Die Anmeldung bleibt Sache der Zielplattform. Weil
**jedes** unserer Gateways die Identitäts-Header eingehender Anfragen
verwirft und selbst setzt, ist die Kette aus zwei Gateways von Haus aus
sicher — die Zielplattform muss dem Edge dafür nicht vertrauen. Der
Edge entschlüsselt allerdings den Verkehr und **kann** ihn mitlesen; bei
fremden Plattformen braucht das eine ausdrückliche Absprache.

**Ein technischer Fallstrick** ist benannt: Die Zielplattform leitet
heute HTTP automatisch auf HTTPS um — hinter einem Edge ergäbe das eine
Endlosschleife. Dafür braucht sie einen Betriebsmodus „hinter Edge".

**Aus dem Vorfall vom 07.08. gelernt:** Wer den öffentlichen Eingang
besitzt, muss auch den öffentlichen Namen aktuell halten. Die Plattform
soll künftig **selbst merken und melden**, wenn der Name auf eine alte
IP-Adresse zeigt — genau das ist unbemerkt passiert und hat den
Deploy-Kanal der Pilot-Plattform stillgelegt.

**Entschieden (Jörg, 2026-08-07):** (1) Der Edge darf auch die
Kundenplattform bedienen; lokal darf die Strecke unverschlüsselt sein,
die Absprache mit Bernd übernimmt Jörg persönlich. (2) Verschlüsselung
Edge→Ziel kommt **später als Option**, wenn die Voraussetzungen
(Plattform-CA) da sind. (3) Die „Plattform nicht erreichbar"-Seite wird
**konfigurierbar mit Vorlagen** — von reinem Text (nicht zu viel
preisgeben) über eine OAAP-Seite mit Werbecharakter bis individuell
gestaltbar; derselbe Mechanismus soll auch fürs **bewusste Vom-Netz-
Nehmen** von Routen dienen (Wartung, „virtuelles Kabel ziehen" bei
Einbruchsverdacht — als eigenes Thema im Programm vermerkt). (4) Die
Weiterleitungstabelle gehört allein dem Edge-Administrator.

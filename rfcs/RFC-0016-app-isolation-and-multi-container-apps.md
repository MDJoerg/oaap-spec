# RFC-0016: App Isolation and Multi-Container Apps

- **Status:** Draft (2026-08-12) — direction chosen by Jörg on all four
  forks; open questions are implementation detail, not direction
- **Date:** 2026-08-12
- **Authors:** Claude (proposal), Jörg (direction and decisions)
- **Depends on:** RFC-0002 (security-first), RFC-0003 (topology),
  RFC-0004 (packaging/manifest), RFC-0015 (declared endpoints — this
  RFC is its addendum-A4 step 2)
- **Closes:** the flat-network defect found on 2026-08-11 (every app
  shares one network with the platform services); the runtime
  restriction "exactly one service is supported in runtime increment 1"

## Summary

Two problems that look separate are one build step.

**The defect.** Every app instance runs on the single Docker network
`oaap_default`, together with the gateway, identity and portal. Nothing
separates an app from the platform's own services. The interim fix in
RFC-0015 A4 (a shared key on identity's internal API, shipped as 0.1.29)
closes the one escalation path that key covers; it does not make apps
contained. This RFC does — structurally, by giving each app instance its
own network and letting only the gateway bridge in.

**The missing capability.** A container stack (Jitsi, a broker plus its
UI, anything real from the self-hosting world) is several containers
that must run together and find each other. The manifest schema has
always allowed `services` to hold more than one entry; only an
implementation guard rejects it. Finishing multi-container support needs
each app to have its own network so its containers can resolve each
other — which is exactly the isolation work above.

So: **one network per app instance.** The containers of that app live on
it and find each other by name; the gateway joins each app network to
reach the app; the platform services sit on their own network the apps
cannot see. App-to-app links, when genuinely needed, become an explicit
act in the portal rather than the ambient reachability of today.

## Motivation and the four decisions

Jörg decided the direction on 2026-08-12; this RFC records the reasoning
so the decisions are legible later.

1. **Do this now, as one RFC** (not "endpoints first"). The isolation is
   the real fix for the A4 defect, and it is the prerequisite for the
   multi-container apps that wrapped stacks need. Building RFC-0015's
   declared endpoints on top of the flat network would put an SFU — a
   service reachable on a raw port — on the same network as a customer's
   CRM. Isolation comes first.
2. **A network per app; the gateway joins each.** An app instance sees
   the gateway and nothing else — not the other apps, not identity, not
   the portal. This is the strongest of the options considered and the
   one that matches how the platform already thinks: the gateway is the
   single point through which everything passes (RFC-0002).
3. **App-to-app links are declared and portal-managed.** Default is no
   visibility between apps. A link is an explicit, logged, revocable
   grant. This is strictly safer than today's "everything sees
   everything" and far safer than the alternative an operator would
   otherwise reach for — routing app-to-app traffic out over the public
   internet and back.
4. **Existing apps migrate automatically on `oaap update`.** The eleven
   apps already running on the fleet are moved to per-app networks by a
   migration step, the same shape as the 0.1.29 key rollout: one brief
   restart per app, no hand work. Proven on oaap-test before the fleet.

## The shape today (what the RFC changes)

Established by reading the reference (0.1.29):

- The compose project `oaap` creates the network `oaap_default`. The
  three core services join it.
- App instances are started with
  `docker run --name oaap-app-<inst> --network oaap_default …`
  (`start_instance_container`). **Same network as the platform
  services.**
- The gateway reaches each app purely by container name: the generated
  Caddy site does `reverse_proxy oaap-app-<inst>:<svc_port>`.
- The manifest carries `services` (schema: object, `minProperties: 1`,
  no maximum) but the runtime refuses more than one:
  *"exactly one service is supported in runtime increment 1."*
- Routes carry `path` + `roles` and no service reference — with one
  service there is nothing to target.

The gateway-by-name reach is the lever: if the gateway is a member of
each app's private network, the exact same `reverse_proxy
oaap-app-<inst>:<port>` keeps working, and **no Caddyfile change is
needed**. Only the network topology moves.

## Proposal

### Networks

- **`oaap_platform`** — gateway, identity, portal. Not joinable by apps.
  (In the reference this can remain the compose `oaap_default`; the
  change is that apps leave it.)
- **`oaap-inst-<instance>`** — one per app instance, created at install,
  removed with the instance. All containers of that instance join it.
- The **gateway** is connected to every `oaap-inst-*` network in
  addition to `oaap_platform`. Identity and portal are **not**.

An app container therefore resolves and reaches: its own sibling
containers, and the gateway (because the gateway is on its network).
It cannot resolve `identity` or `portal` — they are not on any network
it belongs to. The RFC-0015 A4 key stays as defence in depth: if a
future mistake reconnects something, the key still refuses.

### Multi-container apps

- `services` may hold more than one entry. Each becomes a container
  named `oaap-app-<instance>-<service>` (the single-service case keeps
  the current name `oaap-app-<instance>` for continuity, or adopts the
  `-<service>` suffix — see open question 1).
- Containers of one instance share `oaap-inst-<instance>` and resolve
  each other by **service name** (Docker embedded DNS on the
  user-defined network), which is how a compose stack expects to talk.
- **Routes must name their target service** once more than one exists.
  Proposed: an optional `service` on a route, defaulting to the sole
  service when there is only one (keeps every current manifest valid).
  A route with no `service` and several services present is a manifest
  error, caught at validation.
- Exactly one service is the **web entry** the gateway proxies to per
  route. Non-web services (a database, a broker's internal port) carry
  no route and are never published — same rule as today, now meaningful.
- Storage, health, config: per service where it matters. Health stays a
  single app-level check on the web entry (the app is up when its face
  answers); per-service health can come later if a stack needs it.

### App-to-app links (declared, portal-managed)

- Default: no link. Isolation is the resting state.
- A `server_admin` may declare a link "instance A may reach instance B"
  in the portal. Mechanically: connect A's container(s) to B's network
  (or a dedicated link network), so A resolves `oaap-app-B…` by name.
- The grant is per ordered pair and per direction, recorded in the
  registry (survives redeploy like visibility and address do), shown on
  both instances' object pages, and revocable — revocation disconnects
  the network membership.
- Not in the app manifest. Like visibility groups (RFC-0007) and
  endpoint grants (RFC-0015), this is the operator's decision about
  their machine, not the app author's claim.
- CLI parity: `oaap app link add <A> <B>` / `link remove` / `link list`.

### Removal and lifecycle

- Install: create `oaap-inst-<instance>`, start the app's containers on
  it, connect the gateway.
- Config change / redeploy: containers are recreated on the **same**
  network (the network outlives the container, like storage does).
- Remove: stop containers, disconnect the gateway, remove the network,
  drop any links that referenced the instance (with a clear message on
  the other side of each link).

### Backup and restore

The line from RFC-0011/0015 holds. A **link** belongs to the service
relationship and is part of what an operator set up, so it is recorded
and reported on restore ("instance A had a link to B; re-establish it
with …") — but not silently recreated, because the other end may not
exist on the target machine. The **network itself** is machine-local
plumbing, recreated from the registry on install/restore, never carried
in the archive.

## Migration (decision 4, in detail)

`migrate.sh`, idempotent and quiet when there is nothing to do — the
same discipline the 0.1.29 key step already follows:

1. For each instance in the registry without its own network: create
   `oaap-inst-<instance>`.
2. Recreate the instance's container(s) on that network (a recreate,
   not a restart — the network membership is set at `docker run`), and
   connect the gateway to the new network.
3. Leave `oaap_platform`/`oaap_default` holding only the three core
   services.
4. Report per instance; a failure on one instance must not abort the
   others or the rest of the update.

Cost to the operator: one brief restart per app during the update they
are already watching. App traffic resumes as each app comes back; the
gateway and platform services are not recreated by this step.

**Ordering risk to handle:** the gateway must be connected to an app's
network *before* it proxies to that app, or a request briefly 502s. The
migration connects the gateway first, then recreates the app; the steady
state after any single app's recreate is consistent.

## Security argument

- **The A4 defect is closed structurally, not guarded.** An app cannot
  reach identity's internal API because it cannot reach identity at all.
  The key (0.1.29) remains as a second layer.
- **RFC-0002 is preserved and extended.** The gateway is still the only
  way in, and now also the only bridge between an app and anything else.
  Default-deny gains a sideways dimension it never had.
- **Trust classes regain their meaning.** RFC-0012 lets an operator
  admit a `wrapped` third-party image on a confirmation. The implicit
  promise of that confirmation — that the image runs contained — is now
  true. A compromised Forgejo or a hostile community app sees the
  gateway and its own storage, nothing else.
- **What it does not solve:** an app still receives real user traffic
  and can misbehave within its own remit; isolation bounds blast radius,
  it does not vet behaviour. And a declared A→B link is a deliberate
  hole the operator opened — logged and revocable, but real.

## Open questions (implementation detail, not direction)

1. **Container naming.** Keep `oaap-app-<inst>` for the single-service
   case and add `-<service>` only for multi-service, or move everything
   to `oaap-app-<inst>-<service>` for uniformity (a one-time rename of
   existing containers during migration)? Recommendation: keep the
   existing name when there is one service, suffix only when there are
   several — no rename churn for the eleven running apps.
2. **Route→service mapping syntax.** An optional `service:` on each
   route (proposed), or a services-with-routes nesting? Recommendation:
   optional `service` on the route — smallest schema change, every
   current manifest stays valid.
3. **Link mechanism.** Connect A directly to B's network, or create a
   dedicated `oaap-link-<A>-<B>` network both join? The dedicated
   network is cleaner to revoke and audit but multiplies networks.
   Recommendation: dedicated link network — revocation is then a clean
   teardown, and it never grants A the run of B's whole network.
4. **Egress.** Should an app instance reach the public internet by
   default (it does today, via Docker NAT)? Some appliances will want
   apps that cannot phone home. Recommendation: keep egress on by
   default (many apps need to pull or call out), and note per-app egress
   control as a later profile-gated capability, not part of this RFC.
5. **Spec home.** This spans `oaap.core.gateway` (bridging), `oaap.apps.
   runtime` (networks, multi-service, links) and touches `oaap.data.
   backup` (link restore). Which spec owns the network model as its
   normative text? Recommendation: `oaap.apps.runtime`, with a gateway
   spec cross-reference.

## Deutsche Zusammenfassung

**Zwei Probleme, ein Bauschritt.** Der am 11.08. gefundene
Sicherheitsfehler — alle Apps liegen im selben Docker-Netz wie
Gateway, Identity und Portal — und die fehlende Fähigkeit für
Mehr-Container-Apps sind dasselbe Stück Arbeit. Der Schlüssel-Fix
(0.1.29) hat die eine Eskalation geschlossen; dieser RFC macht Apps
**strukturell** eingesperrt.

**Vier Entscheidungen (Jörg, 12.08.):**

1. **Jetzt und als ein RFC** — die Netz-Trennung ist der eigentliche
   Fix und die Voraussetzung für Mehr-Container-Apps. Einen SFU auf
   einem rohen Port ins flache Netz neben Bernds CRM zu stellen, wäre
   verkehrt herum.
2. **Ein Netz je App, das Gateway tritt bei.** Eine App sieht das
   Gateway und sonst nichts — keine andere App, nicht Identity, nicht
   das Portal. Das passt zu RFC-0002: das Gateway ist der einzige
   Durchgang.
3. **App-zu-App nur deklariert, über das Portal.** Grundzustand:
   getrennt. Eine Verbindung ist ein ausdrücklicher, protokollierter,
   widerrufbarer Akt — besser als „alle sehen alle" und viel besser,
   als App-Verkehr übers öffentliche Internet zu leiten.
4. **Bestehende Apps wandern automatisch bei `oaap update`** — je App
   ein kurzer Neustart, kein Handbetrieb, erst auf oaap-test bewiesen.

**Der Hebel:** Das Gateway erreicht Apps heute schon per Containername
(`reverse_proxy oaap-app-<inst>:<port>`). Ist das Gateway Mitglied im
privaten Netz jeder App, funktioniert genau das weiter — **die
Caddy-Konfiguration ändert sich nicht**, nur die Netz-Topologie. Die
Container einer Mehr-Container-App teilen sich das App-Netz und finden
sich per Dienstnamen; Routen benennen künftig ihren Zieldienst (optional
`service`, Vorgabe ist der einzige Dienst — jedes heutige Manifest
bleibt gültig).

**Sicherheit:** Der A4-Fehler ist strukturell zu (eine App erreicht
Identity gar nicht mehr), der Schlüssel bleibt als zweite Schicht, und
die Vertrauensklassen aus RFC-0012 bekommen ihre Bedeutung zurück — ein
bestätigtes fremdes Image läuft jetzt wirklich eingesperrt.

**Offen** sind fünf Umsetzungsfragen (Containernamen, Routen→Dienst,
Link-Mechanismus, Egress, welche Spec das Netzmodell führt) — Details,
keine Richtung.

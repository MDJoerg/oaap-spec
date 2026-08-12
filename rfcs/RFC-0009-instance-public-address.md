# RFC-0009: A Public Address That Belongs to the App, Not to the Machine

- **Status:** Accepted (2026-08-08)
- **Date:** 2026-08-08
- **Authors:** Claude (analysis & proposal), Jörg (decision on direction)
- **Depends on:** RFC-0005 (app addressing), RFC-0006 (edge node)
- **Driver:** bdt-hub production rollout — the first OAAP app whose
  clients are installed software, not a browser bookmark

## Summary

Today an app instance's public address is always a subdomain of the
**node** it happens to run on (`<instance>.<node hostname>`). That is
fine while the address is typed into a browser and forgotten. It stops
being fine as soon as the address is **compiled into distributed
clients**, because then the machine that ran the app on day one is
frozen into every installation, forever. This RFC lets an instance
register a public hostname of its own, served in addition to the
automatic node subdomain.

## Motivation

`bdt-hub` is the central backend for BDT, which ships as a Chrome
extension, an Electron app and a VS Code extension. Those clients must
be told where the hub is, and they carry that address until their next
release reaches every user — which for browser extensions is not a
thing an operator controls.

With today's addressing, the production hub would be published as
`bdt-hub.oaap-demo.duckdns.org`. Three consequences follow, none of
them intended:

1. **A demo machine becomes permanent infrastructure.** `oaap-demo` is
   the experimentation node and the fleet's edge; its name would end up
   in shipped software.
2. **The app can never move.** Putting the hub on its own node later —
   the normal growth path, and exactly what happened with Bernd's
   platform — breaks every installed client at once.
3. **The DynDNS name leaks into the product.** `duckdns.org` is an
   operational detail of one home network, not a property of BDT.

The platform already solved the neighbouring problem: RFC-0006's edge
node forwards *arbitrary* hostnames to *arbitrary* target platforms,
with the `Host` header unchanged. What is missing is the other half —
a target node that **answers** for a name that is not derived from its
own. Adding it costs one generated site file and no new concepts.

There is also a plain security argument. `oaap-demo`'s certificate
policy is on-demand TLS for anything under its own name (a documented
gap: the edge will request a certificate for any subdomain anyone
asks for). A production service deserves a name whose certificate is
issued for a site the operator explicitly configured.

## Proposal

An instance MAY carry **one public hostname of its own**, recorded in
its registry entry next to its port and visibility.

- **Additive, never a replacement.** The automatic node subdomain keeps
  working. Clients migrate at their own pace, and an operator can
  verify the new name before publishing it.
- **Same enforcement, same generator.** The site is built from the very
  same route/role/group block as every other entry point of that
  instance (`site_body`), so default deny, `/auth/*` reservation,
  anti-spoofing and visibility groups hold without special cases. A
  public address is an address, not an exemption.
- **The mode follows the node.** If the node serves its external names
  directly, the instance's name is an ordinary TLS site (ACME, plus an
  HTTP→HTTPS redirect). If the node runs behind an edge (RFC-0006), the
  name is served as plain HTTP, without ACME and without the redirect,
  and accepted only from the edge address — identical to the treatment
  RFC-0006 already prescribes for the node's own external names, and
  for the same reason (the redirect would loop through the edge).
- **It survives redeploy**, like the port assignment and the visibility
  setting: a deployment must never silently change a published address.
- **Collisions are refused, not resolved.** A name is rejected if it is
  the node's own external hostname, if it lies under it (already
  generated automatically), if an edge route on this node covers it
  (the name would be forwarded away), or if another instance holds it.
  Symmetrically, an edge route is refused if it would capture a local
  instance's own hostname.
- **`server_admin` only** (RFC-0008) — this is platform routing.
- **DNS and port forwarding stay the operator's job.** The platform
  says what it needs; it does not manage anyone's registrar or router.
  This is the same division of labour RFC-0006 settled on after the
  DuckDNS incident: address *updating* belongs in the router, not on
  the server.

Reference CLI:

```sh
sudo oaap app address set <instance> hub.example.org
sudo oaap app address show <instance>
sudo oaap app address remove <instance>
```

## What this deliberately does not do

- **No wildcard or automatic naming schemes.** One explicit name per
  instance, set by a human.
- **No second name per instance.** If an app needs several, that is a
  new discussion (and probably a sign the app wants its own routing).
- **No portal UI yet.** The instance object page is the obvious home
  (next to visibility and configuration), but this is a one-time act
  per published app, done by the same person who edits DNS. CLI first;
  the portal follows if it turns out to be used more than once a year.
- **No opinion on which name.** `hub.example.org`, a DuckDNS name of
  its own, a CNAME onto the node's dynamic name — all work, and the
  trade-offs are the operator's.

## Decisions (Jörg, 2026-08-08)

1. **The own name always complements, never replaces.** Both addresses
   stay valid; no `--exclusive` switch. Migration and verification
   before publishing outweigh the fact that the app also stays
   reachable under the less controlled node subdomain.
2. **Yes, the platform reports a stale name.** The health check
   compares, at intervals, whether every published name still resolves
   to this node's public address — accepting that the node has to ask
   an outside service for its own public address to do so. The DuckDNS
   incident (a node silently off the internet for days) is what this
   is for, and with client-embedded addresses the consequence is worse.
   Implementation belongs with `oaap.core.portal`'s health section.
   *Follow-up (2026-08-12, reference 0.1.35):* the watchdog resolves
   **dual-stack** — a name is "unresolved" only when neither A nor AAAA
   answers, and a name that resolves only over IPv6 (a rebind-protected
   CNAME seen from inside the LAN) is reported as "not comparable"
   against the IPv4 public address rather than as a false failure. This
   surfaced from Jörg's `bdt-hub-test.joomp.de` Fritzbox case.
3. **On restore, the address travels and is reported clearly.** It
   belongs to the app — clients point at it and it must survive a move
   — but the DNS record has to be repointed by hand, so the restore
   must say so plainly. (The node *profile* of RFC-0011 is treated the
   opposite way, and for the opposite reason: it belongs to the
   machine.)

## Deutsche Zusammenfassung

**Das Problem:** Die öffentliche Adresse einer App ist heute immer eine
Unteradresse **des Rechners**, auf dem sie gerade läuft — bei bdt-hub
also `bdt-hub.oaap-demo.duckdns.org`. Solange man eine Adresse in den
Browser tippt, ist das egal. Bei bdt-hub ist es das nicht: Die Adresse
wird in ausgelieferte Software eingebaut (Chrome-Erweiterung,
Electron-App, VS-Code-Erweiterung). Damit steckt der Name der
Demo-Maschine dauerhaft in jeder Installation, und ein späterer Umzug
auf einen eigenen Knoten würde jeden installierten Client auf einen
Schlag abhängen.

**Der Vorschlag:** Eine Instanz darf **einen eigenen öffentlichen
Namen** bekommen — zusätzlich zur automatischen Knoten-Adresse, nicht
statt ihr. Technisch ist das die fehlende Gegenseite zu RFC-0006: Das
Edge leitet schon heute beliebige Namen an beliebige Plattformen
weiter; was fehlte, war ein Zielknoten, der für einen fremden Namen
auch **antwortet**.

Wichtig dabei:

- Es ist **dieselbe** Absicherung wie bei jeder anderen Adresse der App
  (Rollen, Gruppen, default deny, Anmelde-Umleitung) — eine eigene
  Adresse ist kein Schlupfloch.
- Direkt am Internet: normales Let's-Encrypt-Zertifikat. Hinter einem
  Edge: Klartext-HTTP ohne Umleitung, nur vom Edge annehmbar — genau
  wie RFC-0006 es für Knotennamen schon festgelegt hat (sonst
  Endlosschleife).
- Der Name **übersteht Deployments** — eine veröffentlichte Adresse
  darf nie unbemerkt verschwinden.
- Namenskonflikte werden **abgelehnt statt aufgelöst**.
- DNS-Eintrag und Portfreigabe bleiben Sache des Betreibers (in Jörgs
  Fall: Fritzbox) — die Plattform sagt nur, was sie braucht.

Bedienung:

```sh
sudo oaap app address set bdt-hub hub.example.org
sudo oaap app address show bdt-hub
sudo oaap app address remove bdt-hub
```

**Entschieden (Jörg, 2026-08-08) — RFC-0009 abgenommen:**

1. Der eigene Name kommt **immer zusätzlich**, er ersetzt die
   Knoten-Adresse nicht. Kein Abschalter.
2. Die Plattform **meldet, wenn ein veröffentlichter Name nicht mehr
   auf sie zeigt** — als Teil der Gesundheitsprüfung. Dafür muss der
   Knoten regelmäßig nach seiner eigenen öffentlichen Adresse fragen;
   das ist der Preis, und er ist es wert: Genau dieser Fall lief beim
   DuckDNS-Vorfall tagelang unbemerkt.
3. Bei einer Wiederherstellung auf einer anderen Maschine **wandert die
   Adresse mit** und wird deutlich gemeldet (der DNS-Eintrag muss ja
   von Hand nachgezogen werden). Sie gehört zur App. Das Knotenprofil
   aus RFC-0011 wird umgekehrt behandelt — es gehört zur Maschine.

**Welchen Namen** bdt-hub bekommt, entscheidest Du — eine eigene
DuckDNS-Adresse, ein Name unter einer Deiner Domains (z. B.
`joomp.de`), beides funktioniert.

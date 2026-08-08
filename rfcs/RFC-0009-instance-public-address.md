# RFC-0009: A Public Address That Belongs to the App, Not to the Machine

- **Status:** Proposed (2026-08-08)
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

## Open questions

1. **Should the instance's own name replace the node subdomain rather
   than complement it?** Keeping both is friendlier for migration but
   means a production app stays reachable under a second, less
   controlled name (which the on-demand TLS gap above already covers
   loosely). Option: a later `--exclusive` flag that stops generating
   the node subdomain for that instance.
2. **Should the platform warn when a published name stops resolving to
   this node?** RFC-0006 already asked for exactly that for node names
   after the DuckDNS incident. An instance address has the same failure
   mode, with worse consequences (installed clients, not a bookmark).
   Proposal: fold it into that same check rather than inventing a
   second one.
3. **Does an instance address belong in a backup's restore path?** On
   restore to a different machine the recorded name will not resolve
   there yet. Proposal: restore it but report it clearly, the same way
   `oaap.data.backup` already reports the external hostname.

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

**Drei offene Fragen an Jörg:**

1. Soll der eigene Name die Knoten-Adresse **ersetzen** können (heute:
   beide gleichzeitig, gut für den Umstieg)?
2. Soll die Plattform **melden, wenn ein veröffentlichter Name nicht
   mehr auf diesen Knoten zeigt**? (Genau das war der DuckDNS-Vorfall —
   bei eingebauten Client-Adressen wäre es schlimmer.)
3. Wie soll sich eine Wiederherstellung auf einer **anderen Maschine**
   verhalten — Name mitnehmen und deutlich melden (Vorschlag) oder
   verwerfen?

**Welchen Namen** bdt-hub bekommt, entscheidest Du — eine eigene
DuckDNS-Adresse, ein Name unter einer Deiner Domains (z. B.
`joomp.de`), beides funktioniert.

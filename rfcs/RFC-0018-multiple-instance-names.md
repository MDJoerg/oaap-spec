# RFC-0018: Several Public Names for One Instance — a Canonical Name and Aliases

- **Status:** Accepted (2026-08-12)
- **Date:** 2026-08-12
- **Authors:** Claude (analysis & proposal), Jörg (decisions on direction)
- **Depends on:** RFC-0005 (app addressing), RFC-0006 (edge node),
  RFC-0009 (a public address that belongs to the app)
- **Extends / supersedes:** RFC-0009 non-goal *"No second name per
  instance"* — that door is opened here, on purpose and with the same
  security posture.
- **Driver:** `bdt-hub-test.joomp.de` — an instance that needs to answer
  under more than one public name (a product name **and** a
  Fritzbox-DynDNS CNAME), each of which real clients may already carry.

## Summary

RFC-0009 gave an instance **one** public hostname of its own, in
addition to the automatic node subdomain, and explicitly deferred "a
second name per instance" to a later discussion. This is that
discussion. An instance may now carry **one canonical name plus zero or
more aliases**. Every name routes to the same instance under the **same**
protection (roles, groups, default-deny, login redirect); the aliases are
not a loophole and not a second, weaker door. The canonical name keeps
RFC-0009's whole reason for existing — a single stable address to embed
in shipped clients and to report on a move — while the aliases let the
same instance also answer under further names it has accumulated.

## Motivation

RFC-0009's non-goal read: *"If an app needs several, that is a new
discussion (and probably a sign the app wants its own routing)."* Two
things turned that hypothetical into a real need:

1. **`bdt-hub-test.joomp.de` is a CNAME onto a Fritzbox DynDNS name.**
   The operator wants the instance reachable under a clean product name
   *and* under the DynDNS-backed name that already works — without
   choosing one and breaking clients that carry the other.
2. **Migration is gradual.** When an app moves from a demo subdomain to
   a product name, both must work at once for as long as old clients
   exist. RFC-0009 already made *the* own name complement the node
   subdomain; the same argument, applied twice, wants *several* names to
   coexist.

Neither is "the app wants its own routing" (a reverse proxy, a second
gateway). It is the plainer thing: one instance, several front-door
names, one set of rules behind them.

## Decisions (Jörg, 2026-08-12)

1. **One canonical name, the rest aliases — not a flat equal list.**
   Exactly one name is *the* address: the one the platform reports, the
   one a restore names first, the one meant to be embedded in shipped
   clients. The others are aliases — fully reachable, same protection,
   but not "the" address. This preserves RFC-0009's purpose (a single
   stable address to compile into a client) instead of dissolving it
   into an ambiguous set. In the registry the canonical name stays the
   existing `address` field; aliases are a new `aliases` list. Every
   pre-RFC instance is already valid: it simply has aliases = none.
2. **All names travel on a restore, and all are reported.** RFC-0009
   decision 3 said the own address travels with the app and must be
   repointed by hand. That holds for **every** name now: canonical and
   aliases all come along on a restore, and the restore lists each one
   that must be pointed at the new machine before it works again. An
   alias is a property of the app, not of the machine it happened to run
   on — the same reasoning as the canonical name.
3. **Build now, not next session.** The mini-RFC and its implementation
   (gateway site per name, registry, CLI, portal UI, watchdog coverage)
   land together, on top of the dual-stack watchdog fix (reference
   0.1.35) that already made the names watchdog check every published
   name over IPv4 and IPv6.

## Design

### Data model

An instance registry entry carries:

- `address` — the **canonical** hostname (unchanged from RFC-0009).
- `aliases` — a list of additional hostnames (new; absent ⇒ empty).

The set of an instance's *own* names is `[address] + aliases`. The
automatic node subdomain (`<instance>.<node host>`) is unaffected and
keeps working regardless.

### Gateway

One TLS site is generated per name — canonical and every alias — by the
same mechanism RFC-0009 already used for the single name:

- **Direct on the internet:** each name gets its own ACME certificate
  and an HTTP→HTTPS redirect.
- **Behind an edge (RFC-0006):** each name is served as plain HTTP,
  accepted only from the edge, no ACME (the edge terminates TLS). The
  edge needs one `oaap edge add <name> <target>` per name, exactly as
  for the canonical name.

Every site carries the **identical** body: the instance's routes,
visibility groups, throttle and login behaviour. There is no per-name
policy — a name is a front door, not a permission.

### Collisions

A candidate name is refused (loudly, never silently reassigned) if it is
the node's own external hostname, already generated automatically under
the node subdomain, covered by an edge route, or already registered —
as canonical **or** alias — for any instance including this one. The
existing single-name validation is extended to scan the full name set.

### Watchdog

The published-names watchdog (RFC-0009 decision 2, dual-stack since
reference 0.1.35) already iterates "every name this node hands out". It
now sees canonical and aliases alike and reports each: points here /
points elsewhere / does not resolve / only IPv6 (not comparable) / behind
an edge.

### Restore

On `restore`, the instance's full name set travels in the registry
entry. The restore output names each — "own address … came along; point
it at THIS machine" — so an operator moving an app knows every DNS record
that must follow.

## CLI

`oaap app address` grows alias verbs alongside the RFC-0009 ones:

```
oaap app address show   <instance>              # canonical + aliases + auto name
oaap app address set    <instance> <hostname>   # set/replace the canonical name
oaap app address remove <instance>              # remove the canonical name
oaap app address alias-add    <instance> <hostname>
oaap app address alias-remove <instance> <hostname>
```

- An alias may only be added once a canonical name exists — the canonical
  is *the* address, aliases hang off it.
- Removing the canonical name while aliases remain is refused with a hint
  (promote one with `set`, or remove the aliases first) — so an instance
  never ends up with aliases and no canonical "the" address.

## Portal (server_admin)

The instance object page's "Eigene Adresse" card shows the canonical
name (as today) and, below it, the list of aliases with add/remove — all
through the existing host-side deploy worker, so validation runs once, in
`appctl`, for both CLI and portal.

## Non-goals

- **No per-name policy.** All names share one protection. If an app
  genuinely needs different rules per name, that *is* "the app wants its
  own routing" — a separate discussion, as RFC-0009 said.
- **No wildcard names.** Each name is explicit. Wildcards multiply the
  certificate and trust surface for no case we have.
- **No automatic DNS.** As with RFC-0009, pointing a name at the node
  (and forwarding ports) stays the operator's job; the platform reports
  whether it worked but never edits anyone's DNS.

## Deutsche Zusammenfassung

**Das Problem:** RFC-0009 gab einer Instanz **einen** eigenen
öffentlichen Namen und schob "einen zweiten Namen" ausdrücklich auf
später. Jetzt ist "später": `bdt-hub-test.joomp.de` ist ein CNAME auf
einen Fritzbox-DynDNS-Namen, und die Instanz soll unter einem sauberen
Produktnamen **und** unter dem schon funktionierenden DynDNS-Namen
antworten, ohne dass man sich für einen entscheiden und die Clients des
anderen abhängen muss.

**Die Entscheidung (Deine, 12.08.):** Eine Instanz trägt **einen
Hauptnamen plus beliebig viele Aliasse**.
- Der **Hauptname** bleibt das, was RFC-0009 wollte: DIE Adresse — die
  die Plattform meldet, die beim Restore zuerst genannt wird, die man in
  ausgelieferte Software einbaut. Technisch das bestehende Feld
  `address`; jede alte Instanz bleibt gültig (Aliasse = keine).
- **Aliasse** sind gleichwertig erreichbar (dieselben Rollen, Gruppen,
  default-deny, Anmelde-Umleitung — **kein Schlupfloch**), aber nicht
  "die" Adresse. Neues Feld `aliases`.
- **Beim Umzug/Restore reisen alle Namen mit**, und der Restore nennt
  jeden einzelnen, den Du im DNS auf die neue Maschine umbiegen musst.
  Ein Name gehört der App, nicht der Maschine.

**Umsetzung:** Ein TLS-Site je Name am Gateway (direkt: ACME-Zertifikat
+ Umleitung; hinter Edge: Klartext-HTTP mit Edge-Wache, ein
`oaap edge add` je Name). Kollisionen werden laut abgelehnt (nie still
umvergeben). Der Namens-Wächter (seit 0.1.35 dual-stack) prüft Haupt- und
Aliasnamen gleichermaßen. CLI: `oaap app address alias-add|alias-remove`;
im Portal die Karte "Eigene Adresse" um die Aliasliste erweitert. Ein
Alias geht erst mit vorhandenem Hauptnamen; den Hauptnamen zu entfernen,
solange Aliasse hängen, wird mit Hinweis abgelehnt.

**Ausdrücklich nicht:** keine unterschiedlichen Regeln je Name (das wäre
"die App will eigenes Routing" — eigene Diskussion), keine Wildcards,
kein automatisches DNS.

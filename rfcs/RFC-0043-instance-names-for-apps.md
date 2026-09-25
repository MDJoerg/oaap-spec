# RFC-0043: The Instance Tells the App Its Own Names

- **Status:** **Accepted (2026-09-24), built 2026-09-25** — N1, N2 and
  N3 decided by Jörg as recommended the evening the question was asked,
  the build deferred on his word and called the next morning ("baue
  RFC-0043"). All four steps of §4 are built: `oaap.apps.runtime` 0.2.30
  (new 2.8.1), reference 0.1.126, Wegweiser 0.4.0 as the first reader,
  and the measuring on oaap-test read the variable **inside the
  container** after every one of the five name changes (§6). Rolled to
  oaap-test from the working copy; the fleet and oaapx01 wait for a push
  and, for oaapx01, Jörg's go-ahead.
- **Date:** 2026-09-24
- **Authors:** Claude (finding & proposal), Jörg (the question that raised it)
- **Depends on:** RFC-0009 (a public address that belongs to the app),
  RFC-0018 (a canonical name plus aliases), RFC-0030 (rehearsal
  instances have their own names), `oaap.apps.runtime` (the container
  environment the platform owns)
- **Driver:** Wegweiser 0.3.0. Jörg put `go.joomp.de` and
  `go.objid.info` on the node, registered them on the instance and
  asked: *can the app see these domains, or do we have to maintain them
  in the app as well?* The measured answer was: it cannot. This RFC is
  the way to make the answer *yes*.

## Zusammenfassung für Jörg

_Entschieden am 2026-09-24: N1–N3 wie empfohlen. Bau später._

Eine Instanz trägt auf der Plattform einen Hauptnamen und Aliasse
(RFC-0018). Die App darin erfährt davon nichts: kein Eintrag in der
Container-Umgebung, keine Kopfzeile am Gateway, keine Plattform-API.
Sie sieht nur den `Host` der Anfrage, die gerade hereinkommt. Deshalb
pflegt Wegweiser 0.3.0 die Adressen ein zweites Mal, in der App — und
zwei Orte für eine Wahrheit gehen auseinander, wie der Abend gezeigt
hat (die Instanz trug nur einen der beiden Namen).

Vorschlag: die Plattform gibt der App ihre Namen als **eine
Umgebungsvariable** mit, `OAAP_INSTANCE_NAMES`, Hauptname zuerst, jeder
Name als vollständiger Ursprung mit Schema. Ändert sich ein Name, wird
der Container neu erzeugt — so wie die Plattform es heute bei jeder
Änderung der Umgebung tut. Die Liste ist eine **Auskunft, kein
Zugriffsschutz**: wer die Instanz erreicht, entscheidet weiterhin das
Gateway. Drei Entscheidungen für dich in §3: welche Namen in die Liste
gehören, ob Umgebungsvariable oder Kopfzeile, und ob eine App die
Liste in der eigenen Verwaltung übersteuern darf.

## 1. What exists today

An instance can own several public names: the canonical address and
its aliases (RFC-0018), plus the automatic node subdomain
`<instance>.<label>.<node>` that every instance gets. The gateway emits
one site per name, all with the same body and the same protection.

None of this reaches the container. The environment the platform owns
is `OAAP_APP_SECRET` and, for twin participants, `OAAP_PLATFORM_KEY`
and `OAAP_TWIN_URL` (`oaap.apps.runtime`). The gateway adds identity
headers on protected routes (RFC-0002, RFC-0040) and forwarding
headers, and passes the client's `Host` through unchanged. So an app
knows the name **this** request used and nothing about the others.

That is enough for a link back to the page the user is on. It is not
enough for anything an app *publishes*: a short link printed on paper,
a QR code, an address embedded in a mail. Those need the name the
operator chose, not the name the administrator happened to use when
they opened the management page.

**Measured on 2026-09-24 (oaapx01):** the registry carried
`go.objid.info` as the address of `wegweiser` and no aliases; Caddy had
one site and one certificate. `go.joomp.de` pointed at the node in DNS
and failed the TLS handshake. The app-side list Jörg was about to fill
in would have said two names; the platform said one. Two places, one
switch — the same failure `zwei-orte-ein-schalter` records for
Keycloak.

## 2. Proposal

### 2.1 One variable, canonical first

The platform sets, in the container of every instance that owns at
least one public name:

```
OAAP_INSTANCE_NAMES=https://go.joomp.de,https://go.objid.info,https://wegweiser.oaap.joomp.de
```

- Comma-separated **origins**, each with scheme, never a path.
- Order is meaning: the **canonical name first** (RFC-0018), then the
  aliases in registry order, then the automatic node subdomain last.
  An app that wants "the" address takes the first entry.
- Scheme follows the node: `https` on a direct node with ACME, `http`
  behind an edge that terminates TLS — the same rule the gateway uses
  for its sites, so the app never guesses.
- An instance with no name of its own gets the node subdomain alone.
  A node without an external name sets nothing; the variable is then
  absent and the app falls back to the request's `Host`, as today.

### 2.2 A snapshot that the platform keeps fresh

The variable is written at install and at every change of names
(`oaap app address set`, `alias-add`, `alias-remove`, and the node's
external configuration). A change **recreates the container**, which
is what the platform already does for any change of the environment.
The cost is one restart per rename, which is rare; the gain is that
the app reads a plain variable and never has to poll anything.

### 2.3 What the list is and is not

The list is **information, not authorisation**. Whether a name reaches
the instance is decided by the gateway, and only there. An app must
not refuse a request because its `Host` is missing from the list, and
must not accept one because it is present. The list answers one
question only: *under which names may I publish myself?*

### 2.4 Rehearsals

A rehearsal instance (RFC-0030) gets its own names and never the
production names — the variable in a rehearsal container lists the
rehearsal's names. This follows from RFC-0030 and is stated here so
that nobody copies a production environment into a rehearsal by hand.

### 2.5 The first reader is part of the build

A format nobody reads is never checked (`format-ohne-leser`). This RFC
is built together with its first consumer: Wegweiser reads
`OAAP_INSTANCE_NAMES` and seeds its "public addresses" from it. The
platform side is not done until that read has been measured on
oaap-test with a renamed instance.

## 3. Decisions for Jörg — all three taken as recommended (2026-09-24)

### N1 — Which names go into the list?

> **Recommendation: all of them, canonical first, node subdomain last.**

The alternative is the canonical name only. That loses the aliases,
which are exactly what Jörg asked for (two domains, one instance), and
it loses the node subdomain that a test instance lives under before it
has a name of its own.

### N2 — Environment variable or request header?

> **Recommendation: the environment variable (§2.1).**

A header (`X-OAAP-Instance-Names`) is always current and needs no
restart, but it costs bytes on every request, it exists only where the
gateway is in the path, and it tempts an app to treat a per-request
value as a per-instance truth. A platform API would be a third way for
a fact that is static for weeks at a time. The variable is the
simplest thing that has one writer and one reader, and it stays true
because the platform, not the app, decides when the container is
recreated.

### N3 — May an app override the list?

> **Recommendation: yes, additively — an app may add names it knows
> and may choose its default; it may not hide a platform name.**

Wegweiser 0.3.0 already has an administrator-maintained list. With this
RFC that list becomes: platform names first (read-only, shown as such),
plus whatever the administrator adds, plus the choice of the default.
An app that shows a platform name as absent would be reintroducing the
two-places problem this RFC exists to remove.

## 4. Build plan

1. `oaap.apps.runtime`: add `OAAP_INSTANCE_NAMES` to the
   platform-owned environment (reserved, never operator-editable),
   with the order and scheme rules of §2.1.
2. Reference: compose the list from `instance_names()` plus the node
   subdomain; write it at install and on every name change; recreate
   the container on change.
3. Wegweiser: read the variable, show platform names as read-only in
   "Öffentliche Adressen", keep the administrator's additions (N3).
4. Measure on oaap-test: rename, alias-add, alias-remove — and read
   the variable **inside** the container each time, not the registry.

## 5. Out of scope

- A per-**area** domain (Wegweiser's own wish list) — that is an app
  question, not a platform one.
- Telling an app when its names change (an event). RFC-0032 has the
  relay; a restart carries the fact well enough for now.
- Names of *other* instances. An app learns its own names, nothing
  about its neighbours.

## 6. What was built (2026-09-25)

**Spec.** `oaap.apps.runtime` 0.2.30: new 2.8.1 with the six rules of
§2, and 2.4.3 rule 3 now lists the platform-owned set.

**Reference 0.1.126.** `instance_names_env()` composes the value from
the one function that already names an instance's own addresses
(`instance_names`) and the one that composes its automatic ones
(`instance_auto_hosts`), so the variable cannot drift from the gateway
sites. `sync_instance_names()` brings `instance.env` up to date always
and recreates a container only when told to — and it decides that by
reading the **container's** environment (`docker inspect`), not the
file. Every name change goes through one door, `commit_instance_names`:
the four CLI actions and the four portal-spool actions were eight copies
of the same three lines and are now eight calls of one function, so
neither door can forget the last step (zwei Wege, eine Regel).
`external set/remove` syncs every instance; a regeneration of the
gateway (platform update, tenant rename) syncs the file and recreates
nothing — restarting every app on a node for a variable most of them do
not read yet is not the platform's call. `oaap app address show` prints
the names **as the app sees them** and says STALE when the container
carries something else. The rehearsal scrub drops the variable. New
`test/test_instance_names_env.py` (30 checks, no Docker): the
arithmetic, the file-always/container-on-request rule, both doors, the
STALE report, the node rename.

**Wegweiser 0.4.0**, the first reader: platform names first and
read-only, the administrator's additions after them, a chosen default in
front (N3 exactly). 182 tests.

**Measured on oaap-test** (0.1.126 from the working copy, no push):
`address set`, `alias-add`, `alias-remove`, `set` again and `remove` —
after each one the container was recreated and `docker inspect` showed
the expected value, including its absence after `remove`. Then
Wegweiser 0.4.0 was installed and `GET /api/v1/hosts` through the
gateway, with a day key, answered `"platform": ["https://go.test.example"]`
— the whole chain from registry to app in one reading. The probe name
was removed afterwards; the node has no external hostname, so the
instance carries no names again and the variable is absent, as §2.1
says.

**Not measured:** a tenant rename and the behind-edge scheme on a real
node (both covered by the unit test only).

**Fleet run, 2026-09-25 (0.1.126, then 0.1.127).** All five nodes,
all HEALTHY, no app restarted by the update, `address show` saying
STALE for every named instance until its next recreate — as designed.
And the first reader found a bug older than itself: after Wegweiser
0.4.0 was redeployed on oaapx01 the variable listed the canonical name
and the node address and **no alias**. The "survives redeploy" block of
the installer kept the address and dropped the aliases, since RFC-0018;
nobody had ever read the names back. 0.1.127 keeps them, with a test
that runs the whole install against Docker stand-ins and fails without
the fix. This is §2.5 in practice: a format nobody reads is never
checked.

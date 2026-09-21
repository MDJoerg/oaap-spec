# RFC-0039: `support` — Giving the Node-Wide Half of `partner` Its Own Name

- **Status:** **Built** (2026-09-21) — decided by Jörg and implemented
  the same day. Not yet released to the fleet; the fleet is on 0.1.104.
- **Date:** 2026-09-21
- **Authors:** Jörg (decision & direction), Claude (finding & write-up)
- **Depends on:** RFC-0002 (roles, gateway enforcement), RFC-0008
  (the same split, performed once before on `admin`), RFC-0022
  (tenant as boundary — rule 1 of `oaap.core.tenant` 2.3)
- **Amends:** nothing. It *restores* RFC-0002's definition of `partner`,
  which later documents overwrote without amending it (§1).
- **Touches:** RFC-0021 §"Outlook: partner-managed fleets" — vocabulary
  note only, see §3.6
- **Driver:** The `oaap-hbsha` project, letter of 2026-09-19. They
  planned to give sponsors — people of external companies — the role
  `partner`, citing RFC-0002. On a shared node that would have exposed
  the health page, which lists every instance on the machine.

## Summary

`partner` means two different things in this platform today, and only
one of them is written down in the RFC that defines it.

**RFC-0002 says** `partner` is *"External partner organization
participating in defined processes"* — an app-facing classification,
with the example *"partner companies (later): `partner`"*.

**Everything built since** uses it for the **service provider who looks
after the landscape**, and gives it a node-wide platform privilege: the
portal health page, which names every instance on the machine, across
tenants.

The second meaning silently overwrote the first. Nobody amended
RFC-0002, so the published definition still invites exactly the use
that is unsafe — and an outside project walked into it.

This RFC does not rename `partner`. It takes the **privilege** out and
gives it a new platform role, **`support`**. `partner` then means what
RFC-0002 always said, carries no platform authority, and becomes
grantable by a `tenant_admin` — which is what makes it usable for the
case it was defined for.

## 1. The evidence

Two definitions, both current, both load-bearing:

| Where | What `partner` means there |
| --- | --- |
| **RFC-0002**, standard role table | "External partner organization participating in defined processes" |
| **RFC-0002**, example mapping | "partner companies (later): `partner`" |
| `oaap-apps/apps/fleetview/oaap-app.yaml` | *"`partner` ist die Rolle der Dienstleister, die die Landschaft betreuen"*; `roles: [admin, partner]` |
| `oaap.core.portal` §health | "Visible for roles `server_admin` and `partner` (service-partner …)" |
| `oaap.core.host` | "Intended for technicians and service partners" |
| `oaap.core.identity` 2.3 | "roles that reach past a tenant — `server_admin` and `partner`" |
| `oaap.core.tenant` 2.3 rule 1 | "`server_admin` (the node) and `partner` (the health page …)" |
| **RFC-0021**, stage-2 outlook | "partner-managed fleets": a partner who cares for nodes |

Rows 1–2 describe an app-facing business role. Rows 3–8 describe a
service provider with node-wide reach. They are not compatible, and the
platform enforces the second while publishing the first.

**Why this is worse than an inconsistency.** The role is forwarded to
apps in `X-OAAP-Roles` verbatim. An app developer reads RFC-0002, sees
a role named `partner` described as "external partner organization",
and gates a supplier or sponsor view on it. The operator grants it. The
person now reads the health page of the whole node. Nothing in the app,
the manifest or the portal says otherwise — the only warning lives in
documents the app developer had no reason to read.

This is the same failure this codebase keeps producing: **an identifier
whose meaning moved, and one reader left standing on the old one.** Here
the reader left standing is the RFC that defines the word.

## 2. Which half moves — and why not the other one

Two ways to resolve it. The choice matters because one of them is
several times the work.

**(a) Move the meaning.** `partner` becomes the app-facing role;
the service provider gets a new name. This was the first proposal
(Jörg, 2026-09-21, working name `service`).

**(b) Move the privilege.** `partner` keeps its name *and* its
service-provider use where that use is about an app; only the
**node-wide platform right** moves to a new role.

Both give the outside project the same thing. They differ in blast
radius:

| | (a) meaning moves | (b) privilege moves |
| --- | --- | --- |
| RFC-0021 stage-2 vocabulary | rewritten throughout | one clarifying note |
| Spec documents | 5+ rewritten | one sentence in 3 files |
| FleetView manifest | changed | changed (§3.5) |
| RFC-0002 | satisfied | satisfied |
| Grantable by `tenant_admin` | yes | yes |

**(b) is chosen.** It is the smaller change and the more honest one: the
defect was never the name. `partner` is a perfectly good word for both
an external company and a service partner — what was wrong is that one
role carried a **platform privilege** while every other app-facing role
carries none. `admin` already had exactly this fixed in RFC-0008, and
`identity/app.py` states the resulting rule in its own comment:

> `admin` is unchanged: an app-facing role only, carrying no platform
> authority by itself.

`partner` is the single remaining exception. This RFC ends it.

**On the working name `service`:** withdrawn for a concrete reason.
`services` is a *required top-level key* in the app manifest (the
containers of an app, RFC-0016), and `service` is already a field name
inside a route entry in `oaap-app.schema.json` — three lines below the
role enum this RFC edits. A role called `service` would put two
meanings of one word in the same ten lines of the same file. `support`
carries the intent ("who looks after this node") and collides with
nothing.

## 3. Proposal

### 3.1 New role: `support`

Added to RFC-0002's standard role table:

| Role      | Meaning |
| --------- | ------- |
| `support` | The service provider who looks after this node: reads the health page and other node-wide status surfaces. Read-only; carries no authority to change anything. Reaches past a tenant, and may therefore be granted only by a `server_admin`. |

`support` is the read-only counterpart to `server_admin`. It is the
role for technicians and service partners that `oaap.core.host` and
`oaap.core.updates` already describe in prose without having a name for.

### 3.2 `partner` returns to RFC-0002's definition

Unchanged wording, restored force:

> **External partner organization participating in defined processes.**

After this RFC, `partner`:

- carries **no** platform authority whatsoever,
- leaves `NODE_WIDE_ROLES`,
- is therefore grantable by a `tenant_admin`, inside their own tenant,
  like `user`, `keyuser`, `guest` and `admin`,
- is forwarded in `X-OAAP-Roles` exactly as before.

No app changes behaviour because of this, because nothing an app does
with the header changes.

### 3.3 What actually moves

Exactly one privilege: **the portal health page** (`server_admin` or
`partner` today → `server_admin` or `support`). There is no second one;
the inventory in §4 is complete.

### 3.4 Who may grant what

`support` reaches past a tenant, so rule 1 of `oaap.core.tenant` 2.3
applies unchanged — a `tenant_admin` may not grant it. Following
RFC-0008's precedent for `server_admin`, granting `support` is a
node-administration act and belongs to `server_admin`.

`NODE_WIDE_ROLES` therefore becomes `{server_admin, support}`:
`partner` leaves, `support` enters. The set keeps its size and its
meaning; only its membership is corrected.

### 3.5 FleetView

`oaap-apps/apps/fleetview/oaap-app.yaml` gates its route on
`[admin, partner]`, and its own comment says it means service
providers. That intent is now spelled `support`, so the manifest
becomes `[admin, support]`.

This is a correction, not a breakage: FleetView is installed in the
operator's own tenant, so no customer's `partner` could reach it
either way. But leaving it on `partner` would re-create the exact drift
this RFC closes — a gate whose word no longer means what the gate
intends.

### 3.6 RFC-0021's stage-2 outlook

RFC-0021 §"Outlook: partner-managed fleets" uses "partner" throughout
in the service-provider sense, for a management stage that is **not
built**. It is an outlook, not a specification, so nothing there is
wrong today. Recorded here so the next author does not have to
rediscover it: **when that stage is designed, the role it means is
`support`.** The English word "partner" may stay in its prose where it
describes a business relationship rather than a role.

### 3.7 Migration

One-time, on update, mirroring `_migrate_server_admin_once()` exactly
(RFC-0008's migration, which this codebase has already run once
successfully):

- **Every user currently holding `partner` also receives `support`.**
  Today's `partner` holders are service providers — that is the only
  meaning the role has been usable for — so this preserves exactly the
  access they have. Nobody gains anything.
- **`partner` is not removed.** Removing a role is the riskier
  direction: an app route may require it. RFC-0008 kept `admin` for the
  same reason.
- Guarded by a flag in the identity state file, so it runs once and
  never again.
- **New installs:** the first user receives `server_admin` and `admin`
  as today. `support` is not granted — a node's own operator holds
  `server_admin`, which already sees everything.

**An operator task follows the migration:** review who holds `partner`
and remove it where the person is a service provider rather than an
external company. Until that is done they hold both, which is safe but
untidy. The platform must not do this automatically — it cannot tell
the two apart, and guessing would either strip a real business partner
or leave a service provider mislabelled.

**As built, this does not rely on a release note.** A line in a release
note scrolls past once; the accounts stay wrong for years. `oaap update`
prints the task itself, naming every account that holds both roles, on
every update — and falls silent the moment none does. A nag that clears
itself when the work is done. (`appctl.py support-cleanup-note`, called
from `migrate.sh`.)

## 4. Implementation inventory

The role list is written out in **nine** places. All nine must move
together, or this RFC reproduces the failure it describes.

**This list said five when the RFC was accepted.** Four more turned up
while building it, and each would have failed late rather than loudly:

| File | What |
| --- | --- |
| `platform/services/identity/app.py` | `ASSIGNABLE_ROLES` (+`support`), `NODE_WIDE_ROLES` (−`partner`, +`support`), both refusal messages, new `_migrate_support_once()`, and the fresh-install state flag |
| `platform/services/portal/app.py` | `ALL_ROLES`, `NODE_WIDE_ROLES`, `can_health`, the health route guard, the module docstring |
| `platform/appctl.py` | `ROLES` — the manifest role validator |
| `oaap-spec/schema/oaap-app.schema.json` | route role enum |
| **`oaap-spec/schema/oaap-store.schema.json`** | **the same enum again**, for the role list generated at publishing time (§1.3). Missed at acceptance. An app gating on `support` would have installed cleanly and then failed store validation — the failure arrives one step removed from its cause, which is the worst place for it |
| `oaap-apps/apps/fleetview/oaap-app.yaml` | `[admin, partner]` → `[admin, support]` |
| **`oaap-apps/apps/fleetview/app.py`** | **FleetView checks the role a second time in its own code** (`_allowed()`, defence in depth). Missed at acceptance. Changing only the manifest would have let the gateway admit a `support` holder whom the app then refused with a 403 naming a role that no longer grants anything |
| **`oaap-apps/apps/studio/pkg.py`** | **Studio validates manifests with its own copy of the role list**, and Studio is in production (0.4.2 on oaap-demo and oaapx01). Missed at acceptance. An app gating on `support` would have been rejected by the tool a developer uses while being perfectly valid on the node — the developer would have believed the tool. Studio's own developer briefing (`app.py`) names the roles too, and now warns against confusing the two |
| **`oaap-apps/apps/store-editor/checker.py`** | **A third copy**, in the tool that checks store lists. Missed at acceptance. Same failure one step later: valid on the node, invalid when published |

The lesson is the RFC's own: **an inventory is a reader too, and it can
be stale on the day it is written.** What found the four was a grep for
the word across every repository, not a re-reading of this list. Three
of the four were copies of the role list living in *apps* — the
platform's own three places were the easy part.

**For the next role change:** grep every repository for the role name
before trusting any list, this one included.

Specification text amended in the same change: `oaap.core.identity`
(2.1 role list, the `roles` field, 2.3 rule 1, acceptance 12),
`oaap.core.portal` (2.5 health visibility, acceptance 2 and 6, the
German summary), `oaap.core.tenant` (2.3 rule 1 and acceptance 8),
`oaap.data.backup` (acceptance 5.7 — also missed at acceptance),
RFC-0002's role table (the `support` row, an "amended by" header and a
note above the table), RFC-0021 (the vocabulary note of §3.6, decision
3 and the German summary), and the **App Deployment Contract**, raised
to v0.7 — the document the outside project actually reads, and the one
that told them `partner` was harmless.

### 4.1 Test

`oaap-reference/test/test_support_role.py`, new. It checks all nine
places move together, the migration in all four of its behaviours
(grants, keeps `partner`, catches inactive accounts, runs once), the
fresh-install case, the tenant boundary in **both** directions — a
`tenant_admin` refused `support` *and* allowed `partner`, which is the
point of the RFC and would otherwise go unproven — and, end to end
through Flask, that `support` arrives in `X-OAAP-Roles` and gates a
route while `partner` does not.

The RFC-0008 migration this one copies had no test. This one was
mutation-checked: reverting the migration or leaving `partner` in
`NODE_WIDE_ROLES` turns it red.

## 5. Consequences

- RFC-0002's standard role table gains a row: eight roles plus the
  `public` route marker.
- `partner` becomes grantable by a `tenant_admin`, which it is not
  today. That is the point, and it is safe precisely because the role
  now carries nothing.
- App Deployment Contract: **unaffected.** Apps still receive whatever
  roles an operator assigned, in the same header, with the same
  spelling.
- One further app-facing role exists that an app may gate on
  (`support`), for the genuine case of a node-status view.
- A published definition and the running platform agree again.

## 6. Out of scope

- **Delegating who may grant `support` beyond "any `server_admin`".**
  Same answer as RFC-0008 gave for `server_admin`.
- **Any further node-wide read surface for `support`.** It gets the
  health page, because that is the one privilege being moved. Anything
  else is a new decision.
- **RFC-0021's stage-2 management model.** Untouched; only its future
  vocabulary is pinned (§3.6).
- **Renaming `partner`.** Explicitly rejected in §2.

## 7. Decisions (Jörg, 2026-09-21)

1. **The privilege moves, not the meaning** — variant (b) of §2.
   Decided after the alternative (`service` inheriting the
   service-provider meaning) was proposed and compared.
2. **The new role is called `support`.** `service` withdrawn over the
   manifest-key collision (§2).
3. **`partner` becomes purely app-facing** and therefore grantable by
   a `tenant_admin`.

## Deutsche Zusammenfassung

**Das Problem.** `partner` bedeutet bei uns heute zwei Dinge, und nur
eines davon steht in dem RFC, das die Rolle definiert.

RFC-0002 sagt: *„External partner organization participating in defined
processes"* — also die externe Firma, mit dem Beispiel „Partnerfirmen
(später): `partner`". Alles, was danach gebaut wurde — FleetView,
Portal-, Host-, Updates-, Identity- und Tenant-Spec —, benutzt dasselbe
Wort für den **Dienstleister, der die Landschaft betreut**, und gibt ihm
ein knotenweites Recht: die Gesundheitsseite, die **jede Instanz der
Maschine** listet, über Mandantengrenzen hinweg.

Die zweite Bedeutung hat die erste lautlos überschrieben. RFC-0002 wurde
nie korrigiert — die veröffentlichte Definition lädt also weiterhin zu
genau der Verwendung ein, die unsicher ist. Das Handball-Projekt
`oaap-hbsha` ist am 19.09. hineingelaufen: Es wollte Sponsoren die Rolle
`partner` geben, unter Berufung auf RFC-0002. Auf einem geteilten Server
hätten die Sponsoren die Instanzliste aller Kunden gesehen.

Das ist wieder das bekannte Muster: **ein Bezeichner, dessen Bedeutung
umgezogen ist, und ein Leser, der im alten Stand stehen blieb.** Der
Leser war diesmal das RFC selbst.

**Die Entscheidung.** Nicht die Rolle zieht um, sondern **das Recht**.
Die Gesundheitsseite bekommt eine neue Plattformrolle **`support`** — den
Dienstleister, der einen Knoten betreut, nur lesend, vergebbar
ausschließlich durch einen `server_admin`. `partner` bedeutet danach
genau das, was RFC-0002 immer gesagt hat, trägt **keinerlei**
Plattformmacht mehr und ist deshalb auch von einem `tenant_admin`
vergebbar — was sie überhaupt erst für den Fall brauchbar macht, für den
sie definiert wurde.

**Warum nicht andersherum** (der ursprüngliche Gedanke: die
Dienstleister-Bedeutung zieht nach `service` um): Beide Wege geben dem
Handball-Projekt dasselbe, aber der andere kostet ein Vielfaches — das
ganze Vokabular der Ausbaustufe 2 von RFC-0021 und fünf
Spezifikationsdokumente statt eines Satzes an drei Stellen. Und der
eigentliche Defekt war nie der Name: `partner` ist für beides ein gutes
Wort. Falsch war, dass **eine app-seitige Rolle ein Plattformrecht
trug**, während keine andere das tut. Genau das hat RFC-0008 bei `admin`
schon einmal repariert; `partner` war die letzte Ausnahme.

**Zum Namen `service`:** zurückgezogen, mit konkretem Grund. `services`
ist ein Pflichtschlüssel im App-Manifest (die Container einer App), und
`service` ist ein Feldname innerhalb eines Routeneintrags — drei Zeilen
unter der Rollenliste, die dieses RFC ändert. Zwei Bedeutungen desselben
Wortes in zehn Zeilen derselben Datei sind genau die Stolperstelle, die
wir hier gerade wegräumen. `support` kollidiert mit nichts.

**Die Umstellung** folgt dem Muster, das RFC-0008 schon einmal
erfolgreich gefahren hat: Jeder heutige `partner`-Träger bekommt
einmalig zusätzlich `support` — niemand verliert Zugriff, niemand
gewinnt etwas. `partner` wird **nicht** entfernt (eine App-Route könnte
sie verlangen). Danach folgt eine Aufgabe für den Betreiber, und die
Freigabemitteilung muss sie nennen: nachsehen, wer `partner` hält, und
sie dort abnehmen, wo es sich um einen Dienstleister und nicht um eine
externe Firma handelt. Das kann die Plattform nicht selbst entscheiden.

**Wichtig für die Umsetzung:** Die Rollenliste steht an **neun**
Stellen. Alle neun müssen zusammen umziehen — sonst wiederholt dieses
RFC genau den Fehler, den es beschreibt.

Bei der Annahme standen hier **fünf**. Vier kamen beim Bauen dazu, und
jede hätte spät statt laut versagt:

- Das **Store-Schema** hat dieselbe Rollen-Enum noch einmal. Eine App
  mit `support` hätte sich sauber installiert und wäre erst beim
  Veröffentlichen durchgefallen.
- **FleetView prüft die Rolle zusätzlich im eigenen Code.** Hätte ich
  nur das Manifest geändert, hätte das Tor jemanden durchgelassen, den
  die App danach abweist.
- **Studio** prüft Manifeste mit einer eigenen Kopie der Liste — und
  Studio läuft produktiv (0.4.2). Eine App mit `support` wäre im
  Werkzeug durchgefallen, obwohl der Knoten sie annimmt; der Entwickler
  hätte dem Werkzeug geglaubt.
- Der **Store-Editor** hat eine dritte Kopie.

Bemerkenswert: **drei der vier lagen in Apps**, nicht in der Plattform.
Die drei Plattformstellen waren der einfache Teil. Gefunden hat alle
vier eine Suche nach dem Wort über sämtliche Repositories, nicht ein
erneutes Lesen dieser Liste. Die Lehre ist die des RFC selbst: **auch
eine Inventur ist ein Leser und kann schon am Tag ihrer Entstehung
veraltet sein.** Die vollständige Liste steht in §4.

**Gebaut am 21.09.2026** (0.1.105, Studio 0.4.3, Store-Editor 0.3.1,
FleetView 0.3.2), mit einem neuen Test (`test_support_role.py`), der
alle neun Stellen, die Umstellung und die Mandantengrenze in beide
Richtungen prüft — auch das Erlaubte, nicht nur das Verbotene. Die
Aufräumaufgabe für den Betreiber meldet sich bei jedem `oaap update`
selbst, solange noch jemand beide Rollen hält, und schweigt danach.
Ausgeliefert ist noch nichts; die Flotte läuft auf 0.1.104.

# RFC-0039: `support` — Giving the Node-Wide Half of `partner` Its Own Name

- **Status:** Accepted (2026-09-21) — decided by Jörg the same day; nothing built
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

**An operator task follows the migration, and the release note must say
so:** review who holds `partner` and remove it where the person is a
service provider rather than an external company. Until that is done
they hold both, which is safe but untidy. The platform must not do this
automatically — it cannot tell the two apart, and guessing would either
strip a real business partner or leave a service provider mislabelled.

## 4. Implementation inventory

The role list is written out in **five** places. All five must move
together, or this RFC reproduces the failure it describes. Listed so
none is forgotten:

| File | What |
| --- | --- |
| `platform/services/identity/app.py` | `ASSIGNABLE_ROLES` (+`support`), `NODE_WIDE_ROLES` (−`partner`, +`support`), new `_migrate_support_once()` |
| `platform/services/portal/app.py` | `ALL_ROLES`, `NODE_WIDE_ROLES`, `can_health`, the health route guard |
| `platform/appctl.py` | `ROLES` |
| `oaap-spec/schema/oaap-app.schema.json` | route role enum |
| `oaap-apps/apps/fleetview/oaap-app.yaml` | `[admin, partner]` → `[admin, support]` |

Specification text to amend in the same change: `oaap.core.identity`
(2.1 role list, 2.3 rule 1, and the role table in 5.x),
`oaap.core.portal` (health visibility, ×4), `oaap.core.tenant` (2.3
rule 1, and the create/update refusal message), RFC-0002's role table
(add the `support` row; the `partner` row stands as written).

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

**Wichtig für die Umsetzung:** Die Rollenliste steht an **fünf** Stellen
im Code und im Schema (Identity, Portal, appctl, App-Schema,
FleetView-Manifest). Alle fünf müssen zusammen umziehen — sonst
wiederholt dieses RFC genau den Fehler, den es beschreibt. Die Liste
steht in §4.

# oaap.core.authorization — Business Authorization

- **ID:** `oaap.core.authorization`
- **Version:** 0.3 (**administration by an app**, §2.10: a privileged app of
  the tenant administers roles, collections, assignments and mappings through
  `/authz/admin/*`; `retire`, §2.6; RFC-0045 A7)
- **Previous versions:** 0.2 (the provider's groups, §2.9: a tenant maps a
  group of its realm to a role collection, evaluated at every login; RFC-0045
  stage 3), 0.1 (declaration, roles, collections, assignments, `effective`,
  client)
- **Maturity:** draft
- **Based on:** RFC-0045 (business authorization: the app declares, the tenant
  grants, the data holder checks — stages 1, 2 and 3); RFC-0056 §4 (groups of the
  provider as a later source); RFC-0027 (API keys, scopes); RFC-0040 (the person
  behind the name); RFC-0004 (manifest)
- **Runs in:** the identity service (`oaap.core.identity`), decided by Jörg
  2026-10-03: identity knows the user id, the tenant, the keys and the login —
  the provider mapping of stage 3 must run there.
- **Manifest:** adds the optional section `authorization`, manifest minor **0.6**.

## 1. Purpose

Platform roles decide who enters the node, a tenant, a route. This capability
answers a different question — *what may this person do inside an app* — and
never mixes the two layers (RFC-0045 §1): a business grant never confers a
platform role, never opens a route, never crosses the tenant.

It is **optional on both sides**. An app that declares nothing keeps its own
model. A node without grants answers every `effective` call with an empty list,
and a client that cannot get an answer **fails closed**.

## 2. Interface

### 2.1 The manifest section `authorization` (manifest ≥ 0.6)

```yaml
authorization:
  objects:
    - key: team                      # unique in the app
      title: Mannschaft              # the manifest's words (RFC-0014)
      activities: [read, edit_lineup, manage_members]
      fields:
        - key: team
          context: Mannschaft        # a twin object type — reserved for stage 2b (§2.8)
        - key: area
          values: [news, sponsoring] # fixed list of value ids
  role_templates:
    - key: trainer
      title: Trainer/in
      grants:
        - object: team
          activities: [read, edit_lineup]
          team: $context             # filled by the assignment (§2.4)
      may_grant: [co_trainer]        # delegation — reserved (§2.8)
```

Rules, checked at manifest validation (a violation is an error, not a hint):

1. `key`s match `^[a-z][a-z0-9_]{0,31}$`; object keys, activity keys within an
   object, field keys within an object, template keys are unique.
2. A template's grant names an **existing object**, only **declared
   activities** of it, and for a field either a list of declared values, a
   single declared value, `$value` (filled by the tenant's role, only for a field
   with `values`) or `$context` (filled by the assignment, only for a field with
   `context`). A field not named in a grant means *no restriction on that field*.
3. `may_grant` names existing template keys of the same app (accepted and stored
   in 0.1, **not enforced** — §2.8).
4. Titles are non-empty text; no other keys are allowed in these objects.
5. A value is stored as its **id**, never its label.

An app that has the section must declare `oaap_manifest: "0.6"` or newer
(version gating like every other field added after 0.1).

**`administer: true`** (0.3, additive, same manifest minor): the app asks to
**administer** the grants of its own tenant (§2.10). It is a boolean, not part of
the declaration: it is neither registered nor compared, and an app may have it
without declaring any object or template (the admin app declares nothing). It
grants nothing by itself: the key is minted only if the operator confirms at the
install (§2.10).

### 2.2 Registering a package's declaration

At install the declaration of the package is registered with the identity
service under `(app id)`, with the package's version. Registration is
**all-or-nothing** and compares the new declaration with the registered one,
exactly as `oaap.data.model` §2.5 compares type definitions:

| change | kind |
|---|---|
| a new object, activity, field, template, or a new activity/object in a template's grant, a new value in a list | **additive** |
| anything removed: object, activity, field, value, template, grant entry; a field's source changed (`values` ↔ `context`); `key` renamed (= removed + added) | **destructive** |
| title changes only | unchanged (presentation) |

A destructive change is **shown before the install proceeds** and names the
roles (and the number of assignments) of every tenant that would lose
something; the install stops unless the operator confirms. When an app has
registered nothing before, there is nothing to compare. A package **without**
the section on a later version, after it had one, is a destructive change of
everything it had.

State: `authorization.json` in the identity data directory (atomic write, one
lock, like `users.json`). Declarations are keyed by app id; grants are keyed by
`(tenant id, app id)` (RFC-0045 A3: a role belongs to the tenant and the app,
not to an instance).

### 2.3 What the tenant builds

Maintained by `tenant_admin` of the tenant and `server_admin` (never more).
Every change is an entry in the tenant's log (`oaap.core.tenant` 1.7).

- **Role** — a template plus values: `{app, template, name, values: {field:
  [value ids]}}`. A `values:` field not filled stays unrestricted only if the
  template did not mark it `$value`; a `$value` field must be filled.
- **Role collection** — a named bundle of roles across apps of the tenant. Only
  collections are assigned; a single role is a collection of one created
  implicitly.
- **Assignment** — `{collection, subject, context, valid_from, valid_to,
  granted_by}`; `subject` is a **user id** (RFC-0040). `context` maps every
  `$context` field of the bundle's templates to **a twin object id**, checked at
  assignment time to be a non-empty id of the right type shape (the check
  against the tenant's twin is §2.8). `granted_by` is **always the
  authenticated caller**, never taken from the request.

### 2.4 The grants an app asks for — `effective`

```
GET /authz/effective?user=<user id>
Authorization: Bearer <instance key, scope oaap.authz>
```

Answers, for **this app's own objects only**, what the person holds *now*:

```json
{"user": "<id>", "app": "<app id>", "tenant": "<tenant id>",
 "grants": [
   {"object": "team", "activities": ["read", "edit_lineup"],
    "fields": {"team": ["<twin object id>"], "area": ["news"]},
    "valid_to": "2026-12-31"}
 ],
 "fresh_for": 30}
```

- Collections, roles, validity and the context are already **resolved**
  (flattened). The app learns *that* a person holds something, never *why*, and
  never another app's grants.
- A field absent from `fields` means **unrestricted**; an empty list means
  **nothing**.
- The key is minted at install exactly as the twin's key (RFC-0027 D5), with the
  scope `oaap.authz` and the app id in its record. It works only for the instance
  it was minted for and only for the tenant of that instance: a `user` of another
  tenant answers 404, not an empty list.
- `fresh_for` is 30 seconds (RFC-0045 A4): a client may cache an answer for at
  most that long; a revocation is effective within that bound.
- **Not a header.** `X-OAAP-Roles` stays the platform-role list only.

The reference client (`oaap-reference/platform/authz_client.py`, stdlib only)
offers `may(user, "team.edit_lineup", team=<id>)`. It **fails closed**:
unreachable service, unknown object, unparseable answer, an answer for another
app — all return `False`.

### 2.5 The read-only list: "what could be allowed here"

`GET /internal/authz/declarations?tenant=…` (internal key + actor) lists the
registered declarations — objects, activities, fields, templates — for the apps
the tenant has an instance of. It carries no assignment.

### 2.6 Administration API

All under `/internal/authz/…`, guarded by the internal key, with `actor` in the
body (`authority(actor)` decides the tenant, never the request):

| verb | path | |
|---|---|---|
| POST | `/internal/authz/register` | register a package declaration (host only, §2.2) |
| GET | `/internal/authz/declarations` | §2.5 |
| GET/POST | `/internal/authz/roles` | list / create a role |
| GET/POST | `/internal/authz/collections` | list / create (roles by id) |
| POST | `/internal/authz/assignments` | assign a collection to a user, with context and validity |
| DELETE | `/internal/authz/assignments/<id>` | end an assignment (**revoke** — grants are not people, a revoke is allowed; the record stays marked ended, it is not erased) |
| GET | `/internal/authz/assignments?user=…` | list |
| POST | `/internal/authz/roles/<id>/retire`, `/internal/authz/collections/<id>/retire` | **retire** (0.3, below) |

`oaap authz …` (CLI) calls the same functions.

**Retire (0.3).** Nothing here deletes (K3.3), but a typo in a role name would
stay for ever. `retire` marks a role or a collection `retired: {at, by}`; the
record stays. A retired **role** cannot join a new collection; a retired
**collection** cannot be assigned or mapped any more. Neither can be retired
while something still stands on it: a collection with a **live assignment or a
mapping** (`collection_blockers`), a role that is in a collection that is not
retired — the answer names what blocks, so the order is always collection
first, then its roles. Retiring twice changes nothing. A retired thing
keeps its **name taken** (the record stays; a log line that names it must keep
meaning one thing), and the error for a new one of that name says so. Log actions `authz.role-retire`,
`authz.collection-retire`.

### 2.7 First consumer

`partnerverwaltung` declares objects over its own types (`organisation`,
`person`) and templates, as the first consumer (RFC-0045 stage 2).

### 2.8 Reserved — accepted and stored, not built

`may_grant` delegation (RFC-0045 §4, stage 3b), `concept:` value sources (semantic types,
own RFC), the check of a context against the twin, the default collection for
self-registered people (A6), derivation rules (A1), twin-side enforcement
(§8.3). A manifest that uses a reserved key is **accepted** and the key is kept;
nothing enforces it, and the admin list says so.

### 2.9 The provider's groups (0.2, RFC-0045 §5)

The provider says **who** a person is; OAAP says **what** they may do. A group
of the tenant's realm can stand for a role collection through a **mapping**
the tenant writes (`tenant_admin`, never more than the tenant): `{group,
collection}`. A group nobody mapped grants nothing.

- **By path.** The token carries the group's **path** (`Verein/Hallenwart`,
  leading slash removed) and nothing else — measured 2026-10-03: the product's
  mapper offers no id. A renamed group therefore stops granting at the next
  login (**fails closed**: nothing is given, nothing else is lost).
- **Read at every login**, first login included. The person's assignments with
  `source: idp` are brought in line with the groups the provider asserts
  *now*: a group newly held gives a new assignment (`granted_by: idp:<group>`,
  `via: <group>`); a group no longer held ends it (`ended_by: login: …`, the
  record stays). The effect is **weaker than a direct assignment** (which counts
  on the next request); the admin page and the CLI say "read again at every
  sign-in". No `groups` claim at all counts as no groups.
- **Only what it made.** A right somebody gave by hand is never touched by a
  login. Removing a mapping ends, at once, the assignments it gave.
- **Never a platform role.** Nothing in this capability can name one; `server_admin`,
  `support` and `tenant_admin` are not reachable from a group — a group called
  `tenant_admin` is a group called that.
- **Not everything can be given by a group:** a collection that needs a
  **context** (a group says "is a trainer", not "of team mB") and a collection
  with a `may_grant` role (a delegation chain must not start in the provider's
  console) cannot be mapped.
- **A failure never blocks the login:** the sync is reported and retried at the
  next login.
- The connector puts a group-membership mapper on the client OAAP makes
  (`oaap.net`/RFC-0056 §5); without it no `groups` reach OAAP.

Routes: `GET/POST /internal/authz/mappings`, `DELETE
/internal/authz/mappings/<id>`; CLI `oaap authz mappings|map-add|map-remove`.
Log actions: `authz.mapping-add`, `authz.mapping-remove`, `authz.idp-sync`.

### 2.10 Administration by an app (0.3, RFC-0045 A7)

Until 0.2 the administration API opened only to the host's internal key, so no
app could build a surface for it. 0.3 adds **one more door**, for an app the
operator made a *tenant administrator's tool*. Same functions behind it, a
different caller.

**The key.** A second key scope, **`oaap.authz.admin`**, minted at the install
of an instance whose manifest has `authorization.administer: true`, and only if
the operator confirms (`--confirm-administer`; without it the install stops and
says what the key can and cannot do). One key per instance, minted once like the
others, bound — by what the host recorded, never by the request — to the **tenant
of that instance**. It is not the key of §2.4 and cannot be used for it; the key
of §2.4 cannot be used here.

**The door.** `/authz/admin/<verb>` on the gateway path `/authz/*`, mirroring
`/internal/authz/<verb>` for `declarations`, `roles`, `collections`,
`assignments`, `mappings` and the two `retire` verbs, and adding three reads for a
surface:

| verb | path | |
|---|---|---|
| GET | `/authz/admin/users` | the people of the tenant: `id`, `username`, display name, `active`; no password, no platform role, no e-mail |
| GET | `/authz/admin/effective?user=…` | per app of the tenant's declarations the resolved grants (as §2.4) **and** the live assignments behind them with collection, `source`, `via`, validity |
| GET | `/authz/admin/log` | the tenant's log entries whose action starts with `authz.`, newest first |

There is **no** `register`, no `instance` and no way to register a declaration:
those stay the host's.

**Who is acting.** Every call names `on_behalf_of`, the user id the app read from
`X-OAAP-User-Id`. **Identity checks the person itself**: a real, active, human
account whose platform role is `tenant_admin` of the key's tenant, or
`server_admin`. Anything else is **403**, whatever the app's own page said. The
tenant is the key's, always; a `server_admin` is a person here, never a way to
another tenant. Every write is an entry in the tenant's log with **the person**
as the actor (`role` as the platform knows it), plus the instance in the detail;
`granted_by` is the person, never the app.

**What this key can never do** (checked, not hoped): touch another tenant;
name, give or read a platform role; create, change or delete a user (`never:
users`); register or withdraw a declaration; mint or change a key. A rehearsal (RFC-0030)
instance is never given this key (it would administer the production tenant).

**What the operator must know.** The app is a **privileged door**. Whoever holds
its container holds a tenant administrator's rights over *grants* — not over
platform roles, not over any other tenant. `on_behalf_of` is as strong as the
app's word: identity can verify that the named person **is** an administrator, not
that they sit at the screen now. This is why the key is not minted without a
confirmation, and why the log names the person.

## 3. Configuration

None on the node. The instance receives `OAAP_AUTHZ_URL` and
`OAAP_AUTHZ_KEY` when its manifest has the section (as `OAAP_TWIN_URL` and
`OAAP_PLATFORM_KEY` for the twin); an instance of an app with `administer: true`
receives `OAAP_AUTHZ_ADMIN_KEY` as well.

## 4. Security requirements

1. A business grant never confers or implies a platform role, never opens a
   route, never crosses a tenant.
2. Assignments bind to the **user id**, never a username or e-mail.
3. `granted_by` and the actor's tenant come from the authenticated caller.
4. An app reads only its own objects' grants; the answer names no other app.
5. The reference client fails closed.
6. Every change of a role, collection or assignment is an entry in the tenant's
   log (`authz.role-create`, `authz.collection-create`, `authz.assign`,
   `authz.revoke`, `authz.register`).
7. A destructive change of a declaration is shown before it takes effect.
8. A rehearsal (RFC-0030) reads the production tenant's grants read-only
   (shares the app id) and cannot write any (reserved with the rehearsal's own
   handling; 0.1 refuses a write whose actor is an instance principal).
9. Validity is evaluated by the identity service on every `effective` call;
   no time value in the answer is trusted from the request.
10. (0.3) The admin key exists only for an instance whose manifest asks for it
    **and** whose install the operator confirmed; it opens only `/authz/admin/*`,
    and no other key opens that.
11. (0.3) The tenant of an admin call is the key's, never the request's; the
    person (`on_behalf_of`) is verified by identity as `tenant_admin` of that
    tenant or `server_admin`, on every call.
12. (0.3) Through this door nothing can name, give or read a platform role,
    touch a user, register a declaration, or cross a tenant.
13. (0.3) Nothing is deleted: `retire` keeps the record, and refuses while
    something live stands on it.

## 5. Conformance tests (described)

1. Manifest: each rule of §2.1 has a rejecting example; a valid one passes; the
   section needs manifest ≥ 0.6.
2. Compare: additive/destructive/unchanged per §2.2; an install with a
   destructive change is refused without confirmation and names the roles.
3. Roles, collections, assignments: only `tenant_admin`/`server_admin` of the
   tenant; another tenant's ids are refused; `granted_by` ignores the request.
4. `effective`: resolved grants for this app only; expired and not-yet-valid
   assignments are absent; revoked absent; another tenant's user is 404.
5. Key: a key of instance A cannot ask for app B; a key without the scope
   cannot reach `/authz/*`.
6. The client fails closed on every listed failure.
7. Platform roles are unchanged by any grant.
8. (0.3) Admin door: a call without the key is 401; the key of §2.4 is 403; a
   normal `user` as `on_behalf_of` is 403 and writes nothing; a person of another
   tenant is 403; a `server_admin` still acts only in the key's tenant; no
   `on_behalf_of` is 400; a write names the person in the log.
9. (0.3) Install: an app with `administer: true` is refused without
   `--confirm-administer`, builds nothing, and says what the key can do; with it
   the key is minted once and a redeploy does not rotate it.
10. (0.3) Retire: refuses a collection with a live assignment or a mapping, and a
    role in an unretired collection; naming the blockers; a retired thing stays
    readable and cannot be used again.

## 6. Dependencies

`oaap.core.identity` (users, keys, tenant log), `oaap.apps.runtime` (manifest,
install), `oaap.core.tenant`.

## 7. Maturity

Draft. Stages 1 and 2 of RFC-0045 (declaration; roles, collections, assignments,
`effective`, client; first consumer `partnerverwaltung`), stage 3 (provider groups, 0.2)
and the administration door and `retire` (0.3, RFC-0045 A7). Nothing of §2.8.

## Deutsche Zusammenfassung (0.3: Verwaltung durch eine App)

Bisher öffnete die Verwaltungs-API nur dem Host-Schlüssel — keine App konnte
eine Oberfläche dafür bauen. 0.3 fügt **eine weitere Tür** hinzu, für eine App,
die der Betreiber zum Werkzeug des Mandanten-Admins gemacht hat. Im Manifest:
`authorization.administer: true` (ohne eigene Deklaration möglich). Der
**Schlüssel** hat den eigenen Bereich `oaap.authz.admin`, wird nur ausgestellt,
wenn der Betreiber bei der Installation **bestätigt** (`--confirm-administer`),
und gehört fest zum Mandanten der Instanz. Die **Tür** `/authz/admin/…` spiegelt
die interne API (Rollen, Sammlungen, Zuweisungen, Abbildungen, Deklarationen
lesen) und liefert drei Lesezugriffe für eine Oberfläche (Benutzer des Mandanten,
wirksame Rechte mit Herkunft, Protokoll). **Wer handelt:** jeder Aufruf nennt
`on_behalf_of` (die Benutzer-ID aus `X-OAAP-User-Id`) — **Identity prüft die
Person selbst**: `tenant_admin` des Schlüssel-Mandanten oder `server_admin`,
sonst 403, egal was die App-Seite meinte. Das Protokoll nennt die Person, nicht
die App. **Nie möglich:** anderer Mandant, Plattformrolle vergeben oder lesen,
Benutzer anlegen/ändern/löschen, Deklaration registrieren, Schlüssel ausstellen;
eine Probe-Instanz bekommt den Schlüssel nie. **Offen gesagt:** die App ist eine privilegierte Tür; wer
ihren Container hat, hat die Rechte eines Mandanten-Admins über **Rechte**
(nicht über Plattformrollen, nicht über andere Mandanten), und `on_behalf_of` ist
so stark wie das Wort der App — Identity prüft, ob die Person Admin **ist**,
nicht, ob sie gerade vor dem Bildschirm sitzt. Dazu **`retire`**: nichts wird
gelöscht, aber eine Rolle oder Sammlung lässt sich ausblenden — nur, wenn nichts
Lebendiges mehr darauf steht (erst die Sammlung, dann ihre Rollen).

## Deutsche Zusammenfassung (0.2: Gruppen des Anbieters)

Ein Mandant kann eine **Gruppe seines Realms** einer **Rollensammlung**
zuordnen (`oaap authz map-add`). Der Anbieter sagt, wer jemand ist; OAAP sagt,
was er darf. **Nach Pfad:** das Token trägt nur den Pfad der Gruppe
(`Verein/Hallenwart`), keine ID — eine umbenannte Gruppe gibt deshalb nichts
mehr (sicher: es wird nichts vergeben). **Bei jeder Anmeldung** gelesen, auch
beim ersten: Wer in der Gruppe ist, bekommt die Zuordnung, wer sie verlässt,
verliert sie beim nächsten Login (die Zeile bleibt als beendet stehen). Von
Hand gegebene Rechte fasst ein Login nie an; eine entfernte Abbildung beendet
sofort, was sie gegeben hat. **Nie** eine Plattformrolle. Nicht abbildbar sind
Sammlungen, die einen **Kontext** brauchen oder `may_grant` enthalten. Ein
Fehler beim Abgleich sperrt die Anmeldung nicht aus. Der Konnektor setzt dafür
einen Gruppen-Mapper am Client (ohne ihn kommen keine `groups` an).

## Deutsche Zusammenfassung (0.1)

Die Fähigkeit `oaap.core.authorization` beantwortet, was jemand **in** einer App
darf — getrennt von den Plattformrollen, die nur den Zutritt regeln. Sie läuft im
**Identity-Dienst** (Jörgs Entscheidung: dort sind Benutzer-ID, Mandant,
Schlüssel und Anmeldung). Eine App **erklärt** im Manifest (neu: Abschnitt
`authorization`, Manifest 0.6) Objekte mit Aktivitäten und Feldern sowie
Rollenvorlagen. Beim Install wird die Erklärung registriert und mit der alten
verglichen; Hinzufügen ist unkritisch, **Entfernen wird vor dem Install gezeigt**
und nennt die betroffenen Rollen. Der **Mandant vergibt**: Rolle (Vorlage +
Werte), Rollensammlung, Zuordnung an eine Benutzer-ID mit Kontext und Gültigkeit,
`granted_by` immer aus dem angemeldeten Aufrufer. **Wer die Daten hält, prüft:**
die App fragt mit ihrem eigenen Schlüssel (Bereich `oaap.authz`)
`GET /authz/effective?user=…` und bekommt nur die Rechte **für ihre eigenen
Objekte**, schon aufgelöst und höchstens 30 Sekunden gültig. Ein
Referenz-Client prüft mit `may(...)` und **verweigert im Zweifel**. Nicht in 0.1,
nur angenommen und gespeichert: Weitergabe (`may_grant`), Gruppen-Abbildung (als
Nächstes), semantische Typen, Prüfung des Kontextes am Zwilling. Erster
Abnehmer ist die `partnerverwaltung`.

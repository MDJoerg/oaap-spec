# oaap.core.authorization — Business Authorization

- **ID:** `oaap.core.authorization`
- **Version:** 0.1
- **Maturity:** draft
- **Based on:** RFC-0045 (business authorization: the app declares, the tenant
  grants, the data holder checks — stages 1 and 2); RFC-0056 §4 (groups of the
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

`oaap authz …` (CLI) calls the same functions.

### 2.7 First consumer

`partnerverwaltung` declares objects over its own types (`organisation`,
`person`) and templates, as the first consumer (RFC-0045 stage 2).

### 2.8 Reserved — accepted and stored, not built in 0.1

`may_grant` delegation (RFC-0045 §4, stage 3b), the provider's group mapping
(RFC-0045 §5, stage 3, built next), `concept:` value sources (semantic types,
own RFC), the check of a context against the twin, the default collection for
self-registered people (A6), derivation rules (A1), twin-side enforcement
(§8.3). A manifest that uses a reserved key is **accepted** and the key is kept;
nothing enforces it, and the admin list says so.

## 3. Configuration

None on the node. The instance receives `OAAP_AUTHZ_URL` and
`OAAP_AUTHZ_KEY` when its manifest has the section (as `OAAP_TWIN_URL` and
`OAAP_PLATFORM_KEY` for the twin).

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

## 6. Dependencies

`oaap.core.identity` (users, keys, tenant log), `oaap.apps.runtime` (manifest,
install), `oaap.core.tenant`.

## 7. Maturity

Draft. Stages 1 and 2 of RFC-0045 (declaration; roles, collections, assignments,
`effective`, client; first consumer `partnerverwaltung`). Nothing of §2.8.

## Deutsche Zusammenfassung

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

# RFC-0067: Working in a Context — Delegation Proven by the Person, Agents as Principals of Their Own

- **Status:** **Accepted (2026-11-01)** — Jörg took D1–D6 as recommended, by
  form. **Stages 0, 1 and 2 built and measured on `oaap-test` the same day**
  (reference 0.1.214, `oaap.core.authorization` 0.5, §10.1–§10.3), pushed,
  not rolled out beyond `oaap-test`. Stage 3 and the end-to-end test not built.
- **Date:** 2026-11-01
- **Authors:** Claude (analysis & proposal), Jörg (direction, decides)
- **Depends on:** RFC-0045 (business authorization; this RFC builds its
  stage 3b and amends its §6.2 and §8.3), RFC-0027 (machine principals and
  API keys), RFC-0040 (the person behind the name), RFC-0066 and
  `oaap.core.identity` §2.11 (the signed person), RFC-0030 (rehearsal)
- **Changes:** `oaap.core.authorization` 0.5 (delegation door, agents as
  subjects); no new header; no change to `oaap.core.identity`'s six headers
- **Drivers:** a research application that wants people and AI agents to work
  per project (requirements paper, 2026-10-31; tenant decision of Jörg,
  2026-11-01: *a tenant is one operation or federation; group and project are
  contexts inside it*); the club service of `oaap-hbsha`, whose trainers see
  every team's data today (RFC-0045 open point)

## Summary

The requirement read like a new platform level: groups, projects, roles per
level, new headers, keys bound to a project. Read against the code, **almost
none of that is missing.** An assignment already carries a context, `effective`
already hands it to the app, and `may()` already refuses a question that does
not name the context. A project is a context.

Three things are really missing, and this RFC proposes them:

1. **Delegation.** `may_grant` is stored and enforced nowhere, so only a
   `tenant_admin` can hand out a right. A project lead cannot add a colleague.
2. **Proof of the person at that door.** The existing admin door believes the
   app's `on_behalf_of`. A door used by ordinary people from ordinary apps must
   not. The signed assertion built for RFC-0066 is exactly the missing proof,
   and RFC-0045 §8.3 named its absence as the unsolved part.
3. **Agents as a recognized case.** An agent working in one project does not
   need a key with a context. It needs to be **its own principal with its own
   assignment**, which the code nearly allows today.

## 1. What exists (read in the code on 2026-11-01, not measured unless noted)

| Claim | Where |
|---|---|
| An assignment holds `context` per `$context` field; without it the assignment is refused (measured on `oaap-test`, CURRENT_STATE 338) | `services/authorization.py`, `assign` |
| `effective` resolves the context into `fields`; the app learns *that*, not *why* | `authorization.py`, `effective` |
| `may()` fails closed both ways: a field the grant restricts must be named | `authorization.py`, `platform/authz_client.py` |
| A context is only checked for its **shape**; any id such as `u12` passes | `CONTEXT_RE`, `assign` |
| `may_grant` is validated, compared and stored, **not enforced** | `oaap.core.authorization` §2.8 |
| A key changes the **roles**, never the identity: the app receives the principal's headers, and no key id | `identity/app.py`, `_by_key`, `identity_headers` |
| `/authz/effective` answers for any user id of the tenant, machine principals included; an assignment accepts any user id of the tenant | `authz_effective`, `authz_assignments_create` |
| `/authz/admin/users` leaves machine principals out | `authz_admin_users` |
| The signed assertion names person, tenant and **instance**, lives 5 minutes, exists only for `kind: human` and is empty otherwise | `oaap.core.identity` §2.11 |

## 2. How the requirement maps

| The requirement says | Here |
|---|---|
| Project | a `$context` field of the app's objects, e.g. `project` |
| Group | another `$context` field, e.g. `group` (hierarchy: §6) |
| Roles per level (`anschauen`, `mitarbeit`, `vertraulich`, …) | role templates, assigned once per context |
| `X-OAAP-Project`, `X-OAAP-Project-Roles` | **not built**: `effective`, as RFC-0045 §7 decided. Grants with contexts can be long, and the request itself says which project it is about |
| "Platform-wide" sharing | tenant-wide; nothing crosses a tenant |
| Key per user and project | an agent principal with its own assignment (§4) |

The app names the project on every check: `may(user, "note.write", project=P)`.
Choosing the active project per session stays the app's business, because the
platform has no way to know which screen a person is on.

## 3. Delegation

### 3.1 The door

`/authz/delegate/*` on the gateway path `/authz/*`, for an instance with its
ordinary key of scope `oaap.authz`.

| verb | path | |
|---|---|---|
| GET | `/authz/delegate/grantable` | per granting assignment: the collections this person may hand on, the contexts, the latest possible end |
| POST | `/authz/delegate/assignments` | assign `{collection, user, context, valid_to}` |
| DELETE | `/authz/delegate/assignments/<id>` | end an assignment (§3.3) |

Every call carries `X-OAAP-User-Assertion`, copied unchanged from the request
the person made. **Identity checks it:** signature, not expired, `aud` is the
instance of the calling key, `ten` is that instance's tenant, the person is
active. No `on_behalf_of` exists at this door. An app without the header gets
401 and writes nothing; a node without an assertion key has no delegation at
all.

### 3.2 The rule (RFC-0045 §4, made exact)

A person may assign a collection if **one** live assignment of theirs, in this
app, holds templates whose `may_grant` lists every template of the collection,
and:

1. **Same app.** Every role of the collection belongs to the calling app.
2. **Own contexts only.** Every context value being handed on is one the
   granting assignment holds, field by field. Trainer of mB, not of mC.
3. **Not wider than the holder.** If the granting assignment has a context, the
   collection handed on must be bound to at least one of those context fields.
   Otherwise a trainer of mB could hand out a context-free role that reaches
   every team. *This case is not in RFC-0045 §4 and was found while writing
   this.*
4. **Own validity.** `valid_to` may not exceed the holder's; a holder with an
   end date forces one.
5. **Chain as deep as declared.** A collection containing a `may_grant`
   template can only be handed on if the holder's `may_grant` lists it.
6. **The target is in the tenant**, and a machine principal never receives a
   collection with `may_grant` (D2).

A delegate picks from collections the tenant built; a delegate never creates a
role, a collection or a mapping. How much a template grants is the app's
declaration: a manifest that lets a trainer hand on more activities than a
trainer has is that manifest's statement, and the admin list should show it.

### 3.3 Ending, and what remains

A delegate may end any assignment of a template their `may_grant` lists, in a
context they hold, whoever granted it. This lets a successor clean up after a
predecessor (D4). RFC-0045 A2 stays: an assignment outlives its grantor and
appears as *granted by someone who no longer holds it*. Records are kept
(`source: delegated`, `granted_by` the person, `granted_by_id`). Log actions
`authz.delegate-assign`, `authz.delegate-revoke`, with the person as actor and
the instance in the detail.

### 3.4 What this door does and does not prove

A compromised app sees the assertion of everyone who visits it and could replay
one for up to five minutes. It can therefore do what **that visitor** could do
through this door, for its own app, in that visitor's contexts. That is far less
than `on_behalf_of`, where the app could name anyone. It is not nothing, and the
operator page should say so. A rehearsal instance (RFC-0030) is refused.

## 4. Agents

**An agent is a machine principal with its own assignments.** "Agent A in
project P" is the machine principal `agent-a-p` holding a collection with
`project = P`. No new field on keys, no new header.

- **Why not a key with a context.** The app learns nothing about the key, only
  the principal. A narrowing field would need a new header, and an app that does
  not read it would ask `effective?user=<person>` and receive the person's full
  rights: **an app that forgets the filter silently widens.** With an agent
  principal, an app that knows nothing about keys is already correct. This keeps
  RFC-0027's non-goal "no third permission dimension".
- **What the app sees.** `X-OAAP-User` is the agent's own name, so origin and
  log name the agent. `X-OAAP-User-Assertion` is empty, so an agent can neither
  delegate nor use a principal propagation.
- **The price.** No intersection with a person: the agent holds what it was
  assigned, not "what my owner may do at this moment". The person who granted
  it is recorded, and a project lead can end it.
- **One act.** `oaap authz agent add --tenant T --app-instance I --name N
  --collection C --context field=id [--days N]` makes the principal, the
  assignment and a key limited to that instance, and shows the key once. For
  `tenant_admin` and `server_admin`. A delegate may later assign an **existing**
  agent within §3.2; creating a principal and a key stays with the administrator
  (RFC-0027 D4).
- **`/authz/admin/users`** gains `?kind=machine`, marked as such in the answer,
  so that the admin app can show an agent's rights. The default stays people
  only.

## 5. Checking a context against the twin (amends RFC-0045 §6.2, §9)

RFC-0045 says a context must be an object of the tenant's twin, checked at
assignment. The spec reserved that, and nothing does it. This RFC proposes to
**keep it reserved** (D5):

- It would make identity, a core service on every node, depend on the store and
  twin, which are optional per node.
- Business authorization is usable by apps that have no twin types yet. Both
  drivers are such apps, and the twin's per-person rights come later.
- The risk is small: a wrong id grants nothing anyone asks for, and §3.2 rule 2
  confines delegates to ids they already hold.

The id stays opaque and stable, owned by the app until the twin holds it. An app
that plans to move should use a value it can carry over, ideally a twin id from
the start. Sections §6.2 and §9 of RFC-0045 are read as *reserved* until then.

## 6. Group and project: flat first (D6)

Contexts are **flat** in this RFC: holding `group = G` says nothing about
`project = P` in that group. That leaves one real gap: rule 2 of §3.2 stops a
group lead from naming a project lead for a **new** project, because they hold
`group`, not that `project`. Until solved, a `tenant_admin` adds the new project
to the group lead's assignment.

The app can still evaluate the hierarchy on reads, since it knows the project's
group: `may("project.read", project=P) or may("group.read", group=G)`.

If the end-to-end test shows that this friction matters, the smallest next step
is a **context parent** registered at the door with a person's assertion:
`{field: project, id: P, parent: {group: G}}`, written once, tenant-bound, so
that rule 2 reads "holds the context or an ancestor". Not proposed for building
now.

## 7. Not part of this RFC

- **A realm group giving a context** (§2.9 stays): a group says "is a trainer",
  not "of team mB". Membership in a project comes from an assignment or from a
  delegate.
- **The Mannschaftsgrenze itself.** The platform has been able to do this since
  0.1. hbsha's catalog has no `$context`, so it does not use it. Moving would
  change its templates and end the group mapping for those roles, and it needs
  somebody who maintains per-team assignments, which is what this RFC's delegation
  makes realistic. That is Jörg's and hbsha's decision, on its own timeline.
- **Twin rights per person** (RFC-0045 §8.3). This RFC makes the proof available;
  using it at the twin is a later RFC (step 5 of the order agreed for the
  research case). Apps check for themselves until then.
- **Field-level visibility** such as confidential entries: declare an object
  (`entry_confidential.read`) and check it in the app (RFC-0045 §8.2).
- **Carrying a key's user through the MCP gateway** (RFC-0065 §5.1): an agent has
  no assertion. It reaches an app directly through the gateway today, which keeps
  working. A view with procedure T shows the backend only the gateway; that gap
  belongs to RFC-0065.

## 8. Security requirements (additions to `oaap.core.authorization` §4)

1. The delegation door accepts only a valid assertion for the calling instance;
   nothing the app states can name the acting person.
2. A person never hands on a context they do not hold, a validity beyond their
   own, or a collection whose roles belong to another app.
3. A context-bound holder never hands on a context-free collection.
4. A machine principal never delegates and never holds `may_grant`.
5. A delegate cannot create roles, collections, mappings, principals or keys, and
   nothing at this door can name a platform role.
6. Every delegated assignment names the person as `granted_by`, in the tenant's
   log.
7. A rehearsal instance is refused.

## 9. Conformance (described; every line has a bait)

1. Trainer of mB assigns a listed collection in mB → 201; in mC → 403, nothing
   written.
2. A collection with an unlisted template → 403; a collection of another app
   → 403.
3. **Context-free collection from a context-bound holder → 403.**
4. `valid_to` beyond the holder's → 400; none given while the holder has one → the
   holder's end is used, and the answer says so.
5. Holder without `may_grant` → 403, with a valid assertion.
6. No assertion, an expired one, one for another instance, one of another tenant,
   a tampered one → 401; a body naming `on_behalf_of` is ignored.
7. An assertion from a rehearsal, or a rehearsal's key → refused.
8. Machine principal as target of a `may_grant` collection → 403; with a plain
   collection and a valid holder → 201.
9. **An agent with `project = P`:** `effective` shows P only; `may(..., project=Q)`
   false; the headers at the app name the agent; the assertion is empty.
10. A key of that agent limited to instance A is refused at instance B.
11. An ended grantor: the assignment stays live and is listed as orphaned; the
    successor ends it.
12. `/authz/admin/users` without `kind` still lists people only.

## 10. Stages

| Stage | Content | Measured on |
|---|---|---|
| **0** | Measure the agent form with what exists: machine principal, key, assignment with context, `effective`, headers at a real app | `oaap-test`, tenant `vuebung`; nothing built |
| **1** | Spec `oaap.core.authorization` 0.5; `oaap authz agent add`; `?kind=machine` | `oaap-test` |
| **2** | The door: `grantable`, assign, end; reference client gains `grantable` and `delegate`; the rules of §3.2 | `oaap-test`, real browser session, two people, one agent |
| **3** | Rollen & Rechte shows delegated, orphaned and agents; `partnerverwaltung` or a test app as first consumer | `oaap-test` |
| **Then** | End-to-end test with synthetic data: two projects, one person, one agent, across UI, REST and MCP of a test app. Nothing goes to `oaapx01`/`oaapx02` without Jörg's word | `oaap-test` |

### 10.1 Stage 0 measured (2026-11-01, `oaap-test`, reference 0.1.210)

Tenant `vuebung`, instance `vuebung-vuebung-verein`, with what exists: a machine
principal, a key limited to the instance, the collection `Trainer` assigned with
`team = u12`.

| Asked | Answer |
|---|---|
| Key at the app, through the gateway | 200; the app sees `X-OAAP-User: agent-probe-u12`, its own `X-OAAP-User-Id`, roles `user` |
| Client sends `X-OAAP-User: vtrainer` as well | overwritten, still the agent |
| Same key at another instance of the tenant | 403 |
| `effective` from inside the app, reference client | one grant, `team: [u12]` |
| `may(team.edit_lineup, team=u12)` / `team=u14` / no team | true / false / false |
| `may(news.publish, area=verein)` (not assigned) | false |
| Key revoked | 401 |

**D2 holds without a line of code.** Not measurable there: the empty assertion
(0.1.210 has no assertion header yet).

**One fault found:** deleting a user leaves their assignments live
(`67a7c040`, subject a deleted id). It grants nothing, because `effective` answers
404 for an unknown user and ids are never reused. But `retire_collection` counts
such an assignment as live and would refuse to retire the collection, and nobody
can tell from the list why. Deleting a user must end their assignments (stage 1).

### 10.2 What building stages 1 and 2 changed (2026-11-01, reference 0.1.214)

`oaap.core.authorization` 0.5 §2.12–§2.13 is normative; where it differs from §3–§4
above, it wins.

- **The header's name.** The gateway strips `X-OAAP-User-Assertion` on `/authz/*`,
  like every identity header. Instead of opening that, the app copies the value into
  `X-OAAP-Person-Proof`.
- **A second bait, values.** A holder limited to `area = news` could have handed on a
  role for `area = sponsoring`; §3.2 only spoke of contexts. Refused now.
- **Two more refusals:** nobody hands on to themselves; every context field of the
  collection must be one the holder holds, not just one of them.
- **A refused end date is 403**, like every other refusal at this door, not 400.
- **A fault of RFC-0066 stage 1, found here and fixed:** `/verify` minted an assertion
  for a person's **API key**, against `oaap.core.identity` §2.11. A leaked key would
  have passed for the person being at the screen, at a destination too.
- **A rehearsal** never holds the key of §2.4, so conformance line 7 holds by
  construction.
- **The CLI verb is `agent-add`**, flat like `role-add` and `map-add`.
- **Still open, stage 3:** listing orphaned assignments (conformance line 11, second
  half) and the admin app.

### 10.3 Stages 1 and 2 measured (2026-11-01, `oaap-test`, reference 0.1.214)

A throwaway package `deleg-probe` in tenant `vuebung` (instance `vuebung-dp`,
templates `lead` with `may_grant: [member]` and `member`), two people signed in
through the real login and the real gateway, every door call made from inside the
real app container with the reference client.

| Asked | Answer |
|---|---|
| Lead: `grantable` | `DP Mitarbeit`, context `pA`; not `DP Leitung` |
| Colleague without `may_grant`: `grantable` / assign | empty / refused |
| Lead of `pA` in `pB`; to themselves; forged proof; no proof | refused, nothing written |
| The proof at another instance of the tenant | refused: *made for another instance* |
| Lead hands on in `pA` | 201, `granted_by` the person; colleague at once: read `pA` yes, read `pB` no, write `pA` no |
| The tenant's log | `authz.delegate-assign`, naming the person |
| Colleague ends it; lead ends it | refused; ended, and the colleague may nothing |
| A person's API key at the app | the person's name, **assertion empty** |
| `agent-add` with a `may_grant` collection | refused, no secret shown, principal gone again |
| `agent-add` with a plain collection | the app sees the agent's own name, assertion empty; read `pA` yes, `pB` no, write no; its key at another instance 403 |
| Agent deleted | its assignment `ENDED` |

**Found only by measuring:** on a node without a propagation destination the
assertion key did not exist, so the header was empty and the door closed for
everybody, while every unit test was green. The key is now made at the install of an
app that declares `may_grant`, also when a new version is the first to declare it
(measured: no key before the install of 0.1.1, key after, door open).

**Not measured:** a provider's login (the people had local passwords; the proof is
the same header), the context-free and value baits on the node (unit test only), and
the admin app with agents.

**Six counter-checks:** removing the rule for the context-free collection, the value
comparison, the provider's assignment, the key's empty assertion, the proof's tenant
check and the machine rule at the host's door each turned the test red.

## 11. Decisions

| # | Proposal | Recommendation |
|---|---|---|
| **D1** | Project and group are `$context` fields; no new headers, no new platform level | yes |
| **D2** | An agent is a machine principal with its own assignments, **no context on keys**; agents never delegate | yes |
| **D3** | The delegation door proves the person by the signed assertion; `on_behalf_of` does not exist there | yes |
| **D4** | A delegate may end assignments in their context whoever granted them | yes |
| **D5** | The twin check of a context stays reserved (amends RFC-0045 §6.2, §9) | yes |
| **D6** | Contexts stay flat for now; a context parent only if the end-to-end test shows the need | yes |

**Decided (Jörg, 2026-11-01, by form):** D1–D6 as recommended.

## Deutsche Zusammenfassung

**Der Befund.** Die Anforderung klang nach einer neuen Plattformebene: Gruppen,
Projekte, Rollen je Ebene, neue Kopfzeilen, Schlüssel je Projekt. Der Abgleich mit
dem Code zeigt: Das Meiste ist da. Eine Zuordnung trägt schon einen Kontext,
`effective` liefert ihn an die App, und `may()` lehnt eine Frage ohne Kontext ab.
**Ein Projekt ist ein Kontext.** Neue Kopfzeilen braucht es nicht.

**Es fehlen drei Dinge:**

1. **Weitergabe (`may_grant`).** Sie wird gespeichert, aber nicht durchgesetzt. Nur
   ein `tenant_admin` kann heute Rechte vergeben, eine Projektleitung nicht.
2. **Ein Nachweis der Person an dieser Tür.** Die bestehende Verwaltungstür glaubt
   der App, wen sie mit `on_behalf_of` nennt. Die neue Tür verlangt die signierte
   Zusicherung aus RFC-0066. Genau deren Fehlen hatte RFC-0045 §8.3 als ungelöst
   benannt.
3. **Agenten als eigener Fall.** Ein Agent in einem Projekt bekommt keinen Schlüssel
   mit Kontext, sondern wird ein eigener Maschinen-Benutzer mit eigener Zuordnung.
   Grund: Die App erfährt nichts über den Schlüssel, sondern nur den Benutzer. Ein
   Schlüssel mit Kontext bräuchte eine neue Kopfzeile, und eine App, die sie nicht
   liest, bekäme still die vollen Rechte der Person. Beim eigenen Benutzer ist auch
   eine ahnungslose App richtig. Der Preis: keine Schnittmenge mit den aktuellen
   Rechten einer Person.

**Die Regel der Weitergabe.** Nur Pakete derselben App, nur Vorlagen, die `may_grant`
nennt, nur in eigenen Kontexten, nur bis zum eigenen Ablauf. **Neu gefunden:** Wer
kontextgebunden ist, darf kein kontextfreies Paket weitergeben. Sonst könnte der
Trainer von mB eine Rolle verteilen, die für alle Mannschaften gilt. Das fehlte in
RFC-0045 §4.

**Grenzen, offen gesagt.** Eine kompromittierte App sieht die Zusicherungen ihrer
Besucher und könnte sie fünf Minuten lang wiederverwenden, also tun, was dieser
Besucher hier darf. Das ist viel weniger als heute bei `on_behalf_of`, aber nicht
nichts.

**Bewusst nicht jetzt:** die Prüfung des Kontexts am Zwilling (sie machte den
Kerndienst `identity` vom optionalen Store abhängig); die Hierarchie Gruppe über
Projekt (flach beginnen; eine Gruppenleitung kann für ein *neues* Projekt noch keine
Projektleitung ernennen, das macht vorerst der `tenant_admin`); Realm-Gruppen, die
einen Kontext vergeben; Rechte je Person am Zwilling.

**Mannschaftsgrenze.** Die Plattform kann das seit 0.1; der Katalog von hbsha nutzt
es nur nicht. Umstellen hieße, deren Vorlagen zu ändern, die Gruppen-Abbildung für
diese Rollen aufzugeben und die Zuordnungen je Mannschaft zu pflegen. Letzteres wird
erst durch die Weitergabe realistisch. Das bleibt deine und hbshas Entscheidung.

**Entschieden (Jörg, 01.11., per Formular):** D1–D6 wie empfohlen.

**Stufen.** 0 Agenten-Form an `oaap-test` messen, ohne etwas zu bauen · 1 Spec 0.5,
`oaap authz agent add` · 2 die Weitergabe-Tür · 3 Anzeige in „Rollen & Rechte“ und
erster Abnehmer · danach der Durchstich mit synthetischen Daten. Nichts geht ohne
dein Wort auf `oaapx01` oder `oaapx02`.

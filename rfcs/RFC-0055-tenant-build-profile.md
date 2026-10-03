# RFC-0055: The Tenant Build Profile — Setting Up a Tenant From One Description

- **Status:** **Accepted (2026-10-03)** — Jörg decided the four open questions
  of idea I-33 one by one (§9). **Stages 1–4 built (2026-10-03, §10–§13).**
- **Date:** 2026-10-03
- **Authors:** Jörg (the wish: build tenants from portal or app), Claude
  (survey of today's steps, write-up)
- **Depends on:** RFC-0022 (tenant as boundary), RFC-0041 (identity provider
  per tenant, connector contract), RFC-0042 (tenant as a place), RFC-0027
  (machine principals and API keys), RFC-0046 (management API and job
  pattern)
- **Extends:** `oaap.core.tenant` (a build is a sequence of the verbs the
  tenant capability already has), `oaap.core.management` (an operator-only
  route family beside the tenant-scoped one)
- **Related, not decided here:** I-28 (narrow realm-administrator account,
  decided in the rights session), RFC-0050 (package catalog), RFC-0049
  (updates for many tenants), idea I-33 stage 2 (the prospect's form)
- **Driver:** The first customer tenant (`sgl` on `oaapx02`) was built by
  hand in about twenty CLI steps (FAQ F1–F29). The operator wants to start
  the same build from the portal, and later from a request form. The four
  platform defects that blocked this (I-8, I-9, I-12, I-16) are fixed.

## Summary

A **profile** is a versioned JSON file on the node. It names *parameters*
(label, customer name, …) and an ordered list of *steps*. Every step type is
**exactly one existing verb** with a check that says "already in place".
A **build** is one run of a profile with concrete parameters. Its state is a
file; an interrupted build is **continued**, not repeated or thrown away.
One core serves the CLI (`oaap tenant build …`), a portal action and an
operator API; the three never differ.

Two things a build deliberately does **not** do: it never creates a person in
the customer's realm (connector contract: `users` is in `never`), and it never
removes a realm or a person when it rolls back. The first administrator is a
named **waiting step** that a human confirms.

## 1. What a profile contains

```json
{
  "profile": "oaap.tenant-profile/1",
  "id": "verein-standard",
  "title": "Club with own login",
  "params": {
    "label":  {"kind": "label", "required": true},
    "title":  {"kind": "text",  "required": true, "max": 80},
    "idp":    {"kind": "connector", "default": "auth"},
    "color_primary": {"kind": "color", "default": null}
  },
  "steps": [
    {"id": "tenant",   "type": "tenant.create",  "label": "{label}", "title": "{title}"},
    {"id": "address",  "type": "address.ensure"},
    {"id": "reachable","type": "address.wait",   "timeout": 120},
    {"id": "realm",    "type": "idp.provision",  "connector": "{idp}",
                        "idp_label": "Mit dem Vereinskonto anmelden"},
    {"id": "policy",   "type": "tenant.policy",  "first_login": "role",
                        "default_role": "user", "self_registration": "off"},
    {"id": "face",     "type": "tenant.face",    "color_primary": "{color_primary}"},
    {"id": "web-test", "type": "app.install",    "source": "…", "channel": "test",
                        "name": "webseite"},
    {"id": "admin",    "type": "manual",
                        "text": "Create the first administrator in the realm …",
                        "done_when": "user.exists"},
    {"id": "backup",   "type": "backup.check"}
  ]
}
```

- **Closed vocabulary.** The step types are a fixed list (§2). A profile
  cannot name a shell command, a path to execute or a verb outside the list.
  A profile with an unknown step type is refused whole, before anything runs.
- **Templates are values, not code.** `{name}` is replaced by the parameter
  of that name, after the parameter was validated by its kind (`label` uses
  the tenant label rules, `color` is `#rrggbb`, and so on). Nothing is
  interpreted as a command; a step is called with an argument **list**.
- **Where profiles live:** `/var/lib/oaap/profiles/*.json`, owned by root,
  not writable through the portal or the API (stage 1). A profile arriving
  as a catalog package (RFC-0050) is possible later with the same format;
  the `profile` field is the format version.
- Each profile has a **digest** (SHA-256 of the file); a build records it.

## 2. The step types

Each type has a **do** (the verb that already exists), a **check** (reads
the node and says whether the step's result is already there), and a
**undo** (only where one exists and is safe, §5).

| Type | Do | Check ("already in place") | Undo |
| --- | --- | --- | --- |
| `tenant.create` | `tenant create` (I-8: includes the gateway sites) | a tenant with this label exists **and was made by this build** (created after the build started, or listed in its `made`); a tenant of that label that is not its own is **refused**, never adopted. The *start* already refuses a taken label | `tenant remove` (empty only) |
| `address.ensure` | the generated sites contain the tenant name | the same read | none |
| `address.wait` | probe `https://<label>.<node>/` until 200/302/303 | the same probe | none |
| `idp.provision` | `idp provision <connector> --tenant <label>` | provider object set on the tenant and the realm answers | `tenant idp --clear-idp` — **the realm stays** (§5) |
| `tenant.policy` | `tenant policy` | the same read equals the wish | none: it goes with the tenant |
| `tenant.face` | `tenant face` | stored values equal the wish | none: it goes with the tenant |
| `app.install` | `app install <source> --tenant <label> --channel … --name …` | an instance of that name exists in the tenant with the package's version | `app remove` (without `--purge`) |
| `manual` | none — a human does it | `done_when` (a read; see below) | none |
| `backup.check` | none | the tenant is in the node archive | none |

`manual.done_when` is one of a short list of **reads**, never an action:
`user.exists` (some account of this tenant exists), `role.tenant_admin`
(an account of this tenant holds `tenant_admin`), `confirmed` (a human said
so with `oaap tenant build confirm`). The build **waits** (state `waiting`)
until the read is true or a human confirms. The first administrator is the
known `manual` step (see the open point in §7).

## 3. The build and its state

A build has an id (`b-<time>-<label>`). Its state is one file,
`data/tenant-builds/<id>.json`, mode 0600:

```
{ "id": …, "profile": "verein-standard", "digest": "…",
  "params": { … no secrets … }, "by": "<actor>", "created": "<utc>",
  "state": "running|waiting|failed|done|rolled-back",
  "steps": [ {"id": "tenant", "state": "pending|running|done|failed|waiting|skipped",
              "note": "one sentence", "started": …, "finished": …,
              "made": ["tenant:<id>"]} ] }
```

- **Steps run in order, one at a time.** A step is `done` only when its
  **check** says so after the **do**: success of the verb is not the
  evidence, the read is (a verb that returned 0 and left nothing is a
  `failed` step).
- **`made`** lists what *this build* created in that step. Rollback (§5)
  touches only what is listed there.
- **Parameters and profile are pinned.** A continue with different
  parameters, or after the profile file changed (digest differs), is
  refused with the difference named; the operator starts a new build.
- **One build per label at a time** (a lock file); a second one for the same
  label is refused while the first is not `done`/`rolled-back`.
- A step that fails leaves state `failed` with its message; the operator
  fixes the cause and **continues** — the finished steps are re-checked
  (cheap), not repeated. A finished step whose result is **no longer on the
  node** stops the build there (somebody may have removed it on purpose; a
  second create is not what was asked).
- **A build killed inside a step** (SIGKILL, power) is continued like any
  other: the step is still `running`, its check finds the result already
  there, and the driver then **claims** what is provably the build's own into
  `made` (the verb did its work and the `made` line was not yet written —
  found by killing a build on a real node). A lock file with the process id
  keeps two drivers apart; a lock of a dead process is taken over at once.
- **A secret never enters the state file**: parameters of kind `secret` do
  not exist in this version. Generated secrets stay where their verb puts
  them (`0600`, as today).

## 4. One core, three doors

The core is a module in `appctl` (`tenant_build_*`). The doors only decide
who may ask and hand the request over:

- **CLI**: `oaap tenant build start <profile> --param k=v … [--dry-run]`,
  `build show [<id>] [--json]`, `build continue <id>`, `build confirm <id>
  <step>`, `build rollback <id> [--yes]`, `build profiles`. `--dry-run`
  prints the steps and what each check reads, changes nothing.
- **Portal action** `tenant-build` (spool, like `tenant-face`): `server_admin`
  only, re-checked on the host (the spool is data, not trust).
- **Operator API** (`oaap.core.management`, route family
  `/api/v1/operator/tenant-builds`): `POST` start, `GET` list/show, `POST
  …/continue`, `…/confirm`, `…/rollback`. Gate: role `server_admin`, bearer
  key or session with `X-OAAP-API: 1` (as the tenant routes). The answer is a
  job id and the state document of §3; the job runs on the host in the
  background, the state file is the truth.

A test must reach **all three doors** with the same refusals (a bait for
each rule: wrong role, bad label, unknown step type, changed digest, second
build for the same label). A rule tested at one door is not tested.

## 5. Failure, continue, rollback (Jörg's decision c)

- **Continue is the default.** A failed or interrupted build is resumed.
- **`rollback` is explicit** (`--yes` after the consequences are printed) and
  undoes only entries in `made`, **in reverse order**, each through the
  safe verb:
  - an instance → `app remove` **without** `--purge` (its data is retained
    as today and named);
  - a tenant → `tenant remove`, which refuses a tenant that holds anything
    (users, data, provider, …) and says what holds it; then rollback stops
    there and says so;
  - the provider object is cleared from the tenant; **the realm and every
    person in it stay** (RFC-0041: deleting a tenant must never delete a
    club's identities). Rollback says it left the realm.
- An undo of something **already gone** counts as done.
- An instance's data is **kept** unless the operator says, in words, that
  it may go too: `--purge-instances` (on `rollback` and on a `continue` of an
  unfinished rollback). Without it the data a removed instance left behind
  keeps the tenant from being removed, and rollback stops there and says why
  (measured, §10).
- A rollback that cannot finish leaves state `failed` with the remaining
  `made` entries, so it can be continued.
- Nothing is ever removed that this build did not create, even if the label
  matches: a tenant that existed before the build is never in `made`.

## 6. Protocol and visibility

- Every build step writes an audit entry (`tenant.build.step`,
  `tenant.build.rollback`, …) in the **node's default tenant log** and, once
  the tenant exists, in the **new tenant's own log**.
- The portal shows the build as a list of steps with their states (stage 2,
  the wizard); until then `build show`.
- No new personal data is collected. The operator's parameters are the
  label and the customer's name, as `tenant create` already takes.

## 7. What is left open on purpose

- **The first administrator.** Today a human creates the account in the
  realm (the connector contract has `users` under `never`), then the
  operator grants `tenant_admin` in the portal. This RFC keeps that as a
  `manual` step. The rights session decides whether OAAP may create a
  **narrow realm-administrator role** at provisioning (I-28 part 2); if so,
  it becomes a field of `idp.provision`, not a new step type.
- **A tenant with content** (archive and grace period, I-27 part 2): not a
  rollback target here.
- **The wizard** (portal pages) and **the prospect's form** (an add-on app
  that creates a request an operator approves): later stages on this core.
- **Profiles as catalog packages** and **profile changes by tenants**: no.

## 8. Staging

1. **This RFC and the core**: profile loader and validator, state file,
   lock, the steps `tenant.create`, `address.ensure`, `address.wait`,
   `idp.provision`, `tenant.policy`, `tenant.face`, `app.install`, `manual`,
   `backup.check`; CLI; tests including baits and interruption in the middle.
   **Measured** on a fresh tenant `vtest` on `oaap-test`.
2. **Operator API and portal action** on the same core; measured at the
   running portal.
3. **The wizard** (pages) over the API.
4. **The prospect's form** as an add-on app (approval stays a human's).

## 9. Decided (Jörg, 2026-10-03)

| | Question | Decision |
| --- | --- | --- |
| (a) | Where does the wizard run | **In the portal**, on **one core shared by CLI and portal** (a portal action, `server_admin` only); the prospect's form later calls the same door with an operator key |
| (b) | Where does a profile live | **A file on the node**, versioned format, cut so it can later be a catalog package |
| (c) | Abort or error | **Continue is the default**; rollback only on request, only what this build made, never the realm, never a tenant that holds anything |
| (d) | Machine-readable / API now (I-3) | **Yes: an internal operator API now**, `--json` on the CLI, on the same core |

## 10. Stage 1: built and measured (2026-10-03)

Reference: `services/tenant_build.py` (pure) and the glue in `appctl.py`
(`oaap tenant build profiles | start | show | continue | confirm | rollback`,
`--dry-run`, `--json`, `--param k=v`, `--step`, `--purge-instances`).

**Measured on `oaap-test`** (profile with tenant, address, policy, face, an
app from the website starter, a manual step, backup check; tenant `vtest`
and probes): start up to the waiting step; continue (waits); confirm (done);
rollback without `--yes` (says what it would do); rollback with `--yes`
(app removed **without** purge, tenant refused because the removed
instance's data holds it — the rule works, and it is why
`--purge-instances` exists); rollback with `--purge-instances` (everything
gone, node clean); **a build killed with SIGKILL in the middle** left
`running`, was continued without doing anything twice. Two defects were found
only by measuring and are fixed: a killed build locked itself for an hour (the
lock now holds the process id), and an undo of something already gone failed
(now done).

**Not measured:** `idp.provision`, `address.ensure` and `address.wait` against
a real address (oaap-test has no external name, so both report "nothing to
publish/probe"); the realm; the Operator API and the portal action (stage 2,
where the rule "a test must reach all three doors" starts to apply — today
there is one door).

## 11. Stage 2: operator API and portal action (2026-10-03)

**Portal action:** the worker action `tenant-build` (`start`, `continue`,
`confirm`, `rollback`). Who may ask comes from the **actor's own record** in
the user store, never from the request; a request that claims a role, names
nobody, or names a person who is not a server_admin is refused by the host.
**Operator API** (`oaap.core.management`, beside the tenant routes):
`GET /api/v1/operator/tenant-profiles`, `GET …/tenant-builds`, `GET
…/tenant-builds/<id>`, `POST …/tenant-builds {profile, params}`, `POST
…/tenant-builds/<id>/continue|confirm|rollback`. Gate: `server_admin` only,
and only at the node's own address (at a tenant's place the routes answer
404); a session needs `X-OAAP-API: 1`, a key does not. Answers to GET come
from a **view file the host writes** after every step
(`apps/build-view.json`), so no call waits behind a build; a POST answers
`202` with a job whose status is the usual `/api/v1/tenant/jobs/<id>` (it
names the build). `purge_instances` is true only for the literal JSON
`true`: a string is not consent to delete data.

**One defect found while testing the doors, and fixed in the cohort routes
too:** a request the worker refuses before its branch (nobody signed in
behind it) wrote only the classic results file, so its job was neither
queued, running nor done and the caller polling it was told "no such job"
for ever. `job_result_fill` now gives every management job an answer.

**Measured:** `test_tenant_build_doors.py` — the same baits (bad label,
unknown step type, bad colour, changed digest, second build for a label)
at the CLI, the worker action and the API, a forged role, an actor who does
not exist, a plain member, and a whole build through the API with the view
following it. On `oaap-test` the worker action ran against the **real
spool and user store** (the path unit stopped for the minutes it took, then
started again): start, a second start refused, confirm, two rollbacks with
purge, a request naming nobody refused, the view file 0644 and following each
step.

**Measured on the running portal** (`oaap-test` updated to 0.1.183 with
`oaap update`, 8/8 core services, 16/16 apps): the portal container carries
the new routes; at the gateway an anonymous call is a `303` to the login (as
for every other route); inside the portal container an anonymous call is a
`403` from the gate, not a `404`, so the routes are registered and refuse.

**Not measured:** an **authenticated** call through the running portal. It
needs a signed-in human `server_admin`, and entering a password is not
something the measuring session may do; Jörg tries it (§11.1). The realm and a
real address are not measured either (as in stage 1).

### 11.1 Finding: the operator API is for humans, not for keys

RFC-0027 **refuses `server_admin` for a machine principal** (`oaap machine
add` says so). The operator routes need `server_admin`, so **a key can never
call them**; only a signed-in person (session with `X-OAAP-API: 1`) can. That
is consistent with "approval stays a human's" and it corrects decision (a):
the prospect's form (stage 4) **cannot** drive the build with an operator key.
It must instead write a **request** that a person approves in the portal
(which then starts the build with the person's own authority). Stage 4 is
designed with that in mind; no change to stages 1-3.

## 12. Stage 3: the wizard (2026-10-03)

Three portal pages for the operator, specified in `oaap.core.portal` 0.3.24
§2.9: **Aufbau** (list of builds and profiles), **Aufbau starten** (a form
made from the profile's parameters, the steps in plain words, the public-label
notice) and an **object page per build** (decisions that wait above
everything, the consequential `Zurückbauen` last, with the tenant label typed
and the data of the instances only on an unticked box). The pages read the
view the host writes and **write nothing themselves**; every button queues the
request the operator API queues, and the host re-checks it. A page is
therefore not a second, weaker door: it is the same door with a form in front.

What a page needs that the engine did not yet keep: a **manual step's text
and its `done_when` are now stored in the state** (pinned with the build), so a
waiting step is a complete question on the page without reading a profile file
that may have changed since — and `Bestätigt` is offered only where
`done_when` is `confirmed`.

**Measured:** `test_tenant_build_page.py` — the pure rules, who and where
(403 for a tenant administrator and a member, 404 at a tenant's place, the
menu entry exactly there), the form from the parameters, every refusal that
must never reach the spool (a missing required field, a foreign origin, a
`Zurückbauen` without the typed label, a confirmation of a step that does not
wait or that a reading decides), the request each button queues, the job
banner (waiting, running, done, refused in the host's words). **Not
measured:** the pages in a browser against the running portal (they need a
signed-in `server_admin`; Jörg looks), and the container image was not rebuilt
for this stage when this was written.

A defect this stage would have shipped: the portal image copies its Python
files **by name** (`Dockerfile`, CURRENT_STATE 132) — a new module left out of
that list is a container in a restart loop. `build_view.py` is in the list.

## 13. Stage 4: the prospect's form (2026-10-03)

Decided by the product owner on 2026-10-03, three questions:

| | Decision |
|---|---|
| Who may fill it in | **Only with an invitation link** the operator issues (one use, an expiry, one profile). Not public to the world: no spam, no strangers' data, almost no surface. |
| Where a request waits | **In the portal**, under `Aufbau` — a file on the node, a list next to the builds. Not an add-on app: an app could not start the build, and the approval would run in the portal anyway. |
| What the prospect may state | **The profile's parameters and one e-mail address.** Nothing else. |

The finding of §11.1 fixes the shape: **the form cannot drive a build**, so it
writes a **request**, and a signed-in `server_admin` approves it; the build
then runs with that person's authority, exactly like `Aufbau starten`.

**Parts.** `services/tenant_request.py` (pure: invitations and requests as
files in `data/tenant-requests/`, mode 0600, one file each), the worker
actions `tenant-request` (invite, revoke, approve, reject — needs
`server_admin`, derived from the actor's own record) and
`tenant-request-submit` (the prospect: **names nobody**, carries the link as its
only proof, checked on the host against the stored hash; it is therefore listed
in `SPOOL_ACTIONS_WITHOUT_ACTOR`, next to the other requests that bring their own
proof), the view
`request-view.json`, the public route `/anfrage` through the gateway (the
base Caddyfile **and** the generated external sites — the `/platform/*`
mistake of CURRENT_STATE 132 is the reason both are named), and the operator's
pages. Specified in `oaap.core.portal` 0.3.25 §2.10.

**Rules the tests hold.**

1. The link is **never stored**, only its SHA-256; a scan of the whole data
   directory after an invitation finds it nowhere (spool included).
2. The submission is **re-judged on the host**: the profile comes from the
   invitation, the parameters through the same engine as a build
   (`param_values`: unknown parameter, bad label, taken label, label held by an
   open build or another waiting request), the address by its own rule. A
   refusal leaves the link **unspent**.
3. Approval is **`server_admin` only**, derived from the actor's record; a
   tenant administrator, a member, nobody, and a user who does not exist get
   nothing built and the request stays pending. A second approval and a
   rejection of an approved request are refused.
4. The address is **not a build parameter** and is not in the build's state.
5. Rejection removes the address at once; decided requests expire after 30
   days.

**Measured:** `test_tenant_request.py` (the core and the real worker — the
real tenant store, spool and user store in a throwaway directory; baits at the
door; one request goes through to a **real tenant created by the approval**)
and `test_tenant_request_page.py` (the public page: identical answers for dead,
short and invented links, `404` at a tenant's place, the form from the link's
profile, every bait of the submission, the brake at ten per minute; the
operator's pages: `403`/`404`, the link shown once and nowhere else, each
button's request and every one that must not be sent). Two mutations were run
against the tests and both were caught: the portal accepting any well-formed
link, and the host accepting a used or revoked one. One defect the tests
found: a validity of `0` days silently became the default of 14.

**Not measured:** the pages in a browser against a running portal; the route
through the **real gateway** on a node (the Caddyfile and the generated sites
carry it and `test_user_identity.py` counts it — nine public routes now — but
no request has gone through a running Caddy); the container image was not
rebuilt for this stage when this was written. **Limits, stated:** the prospect
gets no automatic reply by e-mail (OAAP sends none), and a refusal that only
the host can judge (a label taken meanwhile) is audited and shown to the
operator, not to the prospect; the brake of ten submissions per minute is per
portal process (four), not per portal. **Changed while building:** the link
first sat in the URL path (`/anfrage/<link>`); the gateway's access log strips
the query of every request but keeps a path, so the link is now the query value
`/anfrage?t=<link>` and stays out of that log.

## Zusammenfassung für Jörg (Deutsch)

**Was das ist:** Ein **Profil** ist eine kleine Datei auf dem Knoten. Sie sagt,
was ein neuer Mandant bekommt: Mandant mit Adresse, Anmeldedienst (Realm),
Richtlinie für neue Mitglieder, Gesicht (Titel, Farben), Anwendungen aus
Paketen, einen Wartepunkt für den ersten Verwalter und eine Prüfung der
Sicherung. Ein **Aufbau** ist ein Lauf dieses Profils mit konkreten Werten
(Kürzel, Klarname …). Jeder Schritt ist genau **ein bestehender Befehl** plus
eine **Prüfung**, die sagt „schon erledigt?". Der Zustand steht in einer
Datei; ein unterbrochener Aufbau wird **fortgesetzt**, nichts wird doppelt
gemacht.

**Wichtig:**
- Das Profil kann keine eigenen Befehle enthalten, nur eine feste Liste von
  Schritt-Arten. Werte werden vorher geprüft (Kürzel-Regeln, Farben).
- Ein Schritt gilt erst als erledigt, wenn die **Prüfung** es bestätigt — nicht,
  weil der Befehl „0" zurückgab.
- **OAAP legt nie eine Person im Realm des Kunden an.** Der erste Verwalter
  bleibt ein Wartepunkt, den ein Mensch erledigt. Ob OAAP später ein schmales
  Verwalterkonto anlegen darf, entscheidet die Rollen-Session (I-28), dann wird
  es ein Feld bei `idp.provision`.
- **Rückbau nur auf Wunsch**, nur was dieser Aufbau selbst angelegt hat, der
  Realm und seine Personen bleiben immer stehen, ein Mandant mit Inhalt wird
  nie automatisch entfernt.
- Ein Kern, drei Türen: Kommandozeile (`oaap tenant build …`), Portal-Aktion
  (nur `server_admin`) und Betreiber-API. Der Test muss alle drei Türen mit
  Ködern treffen.

**Gebaut wird in Stufen:** 1. Kern + Kommandozeile, gemessen an `vtest` auf
`oaap-test`; 2. API und Portal-Aktion; 3. Wizard; 4. Interessentenformular.

**CI/CD kurz erklärt:** Ein „Köder-Test" ist ein Test, der absichtlich
versucht, die Regel zu verletzen (falsche Rolle, falsches Kürzel …) und nur
besteht, wenn die Regel wirklich ablehnt. So merken wir, wenn eine Regel an
einer der Türen gar nicht greift.

**Stufe 1 gebaut und gemessen (03.10.):** `oaap tenant build …` läuft an
`oaap-test` mit Profil, Warteschritt, Fortsetzen, Bestätigen und Rückbau.
Gemessen auch: ein mit SIGKILL mitten im Schritt beendeter Aufbau lässt sich
fortsetzen, ohne etwas doppelt zu tun. Beim Messen gefunden und behoben: ein
beendeter Aufbau sperrte sich eine Stunde lang selbst (die Sperre trägt jetzt
die Prozessnummer), und ein Rückbau von etwas, das schon weg ist, schlug fehl
(gilt jetzt als erledigt). Die Daten einer entfernten Instanz bleiben beim
Rückbau erhalten, außer man sagt ausdrücklich `--purge-instances`; sonst
verhindern sie das Entfernen des Mandanten, und der Rückbau sagt, warum.
**Nicht gemessen:** Realm-Einrichtung und echte Adresse (oaap-test hat keinen
Außennamen), API und Portal-Aktion (Stufe 2).

**Stufe 2 gebaut (03.10.):** Portal-Aktion (Spool-Aktion `tenant-build`) und
Betreiber-API (`/api/v1/operator/tenant-builds …`) auf demselben Kern. Wer
fragen darf, entscheidet der Host aus dem Benutzerspeicher, nicht die
Anfrage; die API gibt es nur für `server_admin` und nur an der Adresse des
Knotens selbst. Gefunden und behoben: eine vom Worker abgelehnte Anfrage
ohne angemeldeten Benutzer hinterließ keinen Job-Status, der Aufrufer
bekam für immer „no such job“ (galt auch für die Kohorten-Routen).
Gemessen: dieselben Köder an CLI, Aktion und API im Test; am echten Spool
von `oaap-test` die Aktion. **Nicht gemessen:** die API am laufenden Portal
(Portal-Image nicht neu gebaut).

**Stufe 3 gebaut (03.10.):** Aufbau-Assistent im Portal, drei Seiten
(Liste, Formular, Objektseite), nur für den Betreiber am Knoten selbst. Das
Formular entsteht aus den Parametern des Profils, die Schritte stehen in
Klartext, Menschenschritte sind gekennzeichnet; was wartet, steht über
allem, das Zurückbauen ganz unten (Kürzel eintippen, Daten der Instanzen nur
mit eigenem Haken). Die Seiten schreiben nichts selbst, jede Schaltfläche
stellt dieselbe Anfrage wie die API. Der Text eines Menschenschritts und sein
`done_when` stehen jetzt im Zustand des Aufbaus. **Nicht gemessen:** die Seiten
im Browser am laufenden Portal.

**Stufe 4 gebaut (03.10.):** das Interessentenformular. Entscheidungen von
Jörg: ein Interessent kommt **nur mit Einladungslink** (einmal benutzbar, mit
Ablauf, an ein Profil gebunden) — nicht offen im Netz; der Antrag liegt **im
Portal** unter „Aufbau“, nicht in einer Zusatz-App; gefragt werden **nur die
Parameter des Profils plus eine E-Mail-Adresse**. Das Formular baut nichts: es
erzeugt einen Antrag, und erst die Freigabe durch einen angemeldeten
`server_admin` startet den Aufbau — mit dessen Rolle. Der Link wird nie
gespeichert, nur sein Prüfwert; abgelehnte Anträge verlieren die Adresse sofort,
entschiedene verschwinden nach 30 Tagen. **Nicht gemessen:** die Seiten im
Browser und der Weg durch das echte Gateway auf einem Knoten.

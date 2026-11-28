# RFC-0143: People Bound to Instances — Who Looks After This Site

- **Status:** **Accepted (2026-11-28)** — direction decided by Jörg the
  same day, D1–D7 all as recommended („Ja, wie empfohlen“).
  **Stage 0 measured 2026-11-28 (§9)** — F1: the worker did not judge the
  role of 30 instance requests; fixed in reference 0.1.405.
  **Stage 1 built and measured 2026-11-28 (§10), reference 0.1.406.**
  **Stage 2 built and measured 2026-11-28 (§11), reference 0.1.407;**
  **the reduced instance page 0.1.408 (§12); promote and rollback for**
  **the Verantwortliche 0.1.409 (§13).**
- **Date:** 2026-11-28
- **Authors:** Jörg (the need: „Personen aus dem tenant benennen, die z.b.
  für eine Webseite + testinstanz zuständig sind und produktiv setzen,
  Zugriffe + auslastung aber auch aktuelle Statistiken sehen können“),
  Claude (design)
- **Depends on:** `oaap.core.tenant` (platform roles, people of a tenant),
  `oaap.core.authorization` (business grants inside an app — kept apart),
  RFC-0080 (notifications), I-81 (page statistics, `site_watch`), RFC-0141
  (site check), RFC-0059 (maintenance), RFC-0092 (login required)
- **Used by:** RFC-0142 (the situation on the go), RFC-0144 (short links
  of an instance)
- **Changes (when accepted):** `oaap.core.tenant` (bindings on the
  instance record, who may bind), `oaap.core.portal` (a card *Zuständige*,
  the instance pages for a bound person), `oaap.core.notifications` (a
  recipient *Zuständige der Instanz*), the CLI

## Summary

Today a tenant has two kinds of people on the platform's side: the
`tenant_admin`, who may do everything in the tenant, and everyone else, who
uses the apps. Missing is the person **who looks after one thing** — the
club's web site and its test instance, the shop, the wiki: sees its
traffic, load, statistics and site check, reacts when something is odd,
puts the tested version live — and may do nothing else in the tenant.

This RFC lets a `tenant_admin` (or the `server_admin`) **bind a person to
an instance with a role** of a short fixed list — *Beobachter*,
*Betreuer*, *Verantwortlich*. The node judges every request about the
instance against the binding as it judges the platform role today. A bound
person sees their instances in the portal and on the phone (RFC-0142) and
hears about them (matters, site notices) without standing on one of the
tenant's lists.

These are **operating roles**: what a person may see and do *to* an
instance. What they may do *inside* the app stays the business grants of
`oaap.core.authorization` — the two layers never mix (RFC-0045 §1).

## 1. The roles

Three levels, each including the one before (D1):

| Role | Sees | May |
|---|---|---|
| **Beobachter** | state, light, page statistics, visits, 404, search engines, CPU/memory history, site check, short links of the instance, recent actions | nothing — reading only |
| **Betreuer** | as Beobachter, and the instance's open matters | maintenance on/off, require login on/off, restart, wake, shut out AI fetchers, „Seiten-Check: Jetzt prüfen“, „Lage gesehen“ |
| **Verantwortlich** | as Betreuer | promote test → production, back to the previous version, switch the site check and the site notices on/off, the instance's short links (RFC-0144) |

Never by a binding (only by the platform roles that have them today):
remove, install, rename, configuration and secrets, routes and visibility,
addresses and domains, the app's own administration.

## 2. What is bound

- A binding is `{person, role, since, by}` in the instance record's
  `people` list, kept by an update, a rebuild and a promotion (like
  `site_watch`); the tenant's log says `instance.people` with old and new
  role.
- **A production instance and its test instances** (D2): a binding on a
  production instance also covers the test instances that are promoted
  into it and its rehearsals — „Webseite + Testinstanz“ is one decision,
  not two. A test instance may also carry bindings of its own (a tester
  who must not touch production).
- The person must be **one of the tenant's people** (a user of the tenant,
  also with the platform role `partner` — an agency that built the site,
  D6). A person disabled or removed from the tenant loses every binding;
  the log says so.

## 3. Who binds

- The tenant's `tenant_admin` and the `server_admin` (D3), in the portal
  (a card **Zuständige** on the instance page: person, role, since, by
  whom; add, change, end) and by `oaap app people <instance> add|set|remove
  <person> <role>`. Every change is a spool request `instance-people` the
  host judges again.
- A *Verantwortliche* does not bind others (D3): who looks after a site is
  the tenant's decision.

## 4. How the node judges

- **One function** `may(actor, instance, action)` on the host: platform
  role first (as today), then the actor's binding on the instance or, for
  a test instance, on the production instance it belongs to. Every door
  that changes an instance — the spool requests `maintenance`,
  `login-required`, `restart`, `wake`, `ai-fetchers`, `site-check`,
  `site-watch`, `promote`, `rollback` and the short-link requests of
  RFC-0144 — asks it. The portal shows a button only where the function
  says yes, and never decides itself (the host judges again).
- The audit names the actor and why they were allowed: the role
  `tenant_admin`, or `bound:caretaker` (the record's English name, D7).

## 5. What a bound person sees

- **Portal:** a page **Meine Instanzen** (the person's bound instances with
  state, light and today's numbers) and, per instance, the instance page
  with the tabs the role reaches — Übersicht (state, actions),
  Seitenstatistik (with the site check), Diagnose (load history, restarts)
  — and without Konfiguration, Adressen, Zugriff.
- **Phone:** the same instances in the PWA (RFC-0142), with the actions of
  the role.
- **Notifications** (D4): a new recipient **Zuständige der Instanz** in the
  routing (`oaap.core.notifications`): the matters about an instance
  (`instance.down`, `site.google`, `site.notfound`, `site.check`, later the
  short-link types of RFC-0144) reach its *Betreuer* and *Verantwortliche*
  by mail and push. Each person may switch their own off per type; the
  tenant's lists keep getting what they get today.

## 6. Stages

| Stage | Content | Done when |
|---|---|---|
| 0 | Inventory: every door that changes an instance and how it judges today; how a test instance knows its production instance (the promotion's target); which notification types name an instance | a table in this RFC |
| 1 | The record, CLI, the card *Zuständige*, `may()` at every door, audit | on oaap-test a person bound as *Betreuer* switches maintenance, is refused a promotion, and is refused everything on an unbound instance |
| 2 | *Meine Instanzen* and the reduced instance page; the recipient *Zuständige der Instanz* | a bound person gets `site.check` of their instance without being on a list |
| 3 | The phone (RFC-0142 stage 3) | — |

## 7. Non-goals

- Business rights inside an app (`oaap.core.authorization`).
- Teams or groups as the bound party (later, when a tenant asks: a group
  of the realm as the bound party, RFC-0131).
- Bindings across tenants.
- A fourth level that administers the instance — that is the
  `tenant_admin`.

## 8. Decisions

*Decided by Jörg 2026-11-28:* people are bound to instances and get roles.

*Decided by Jörg 2026-11-28 („Ja, wie empfohlen“) — D1–D7 all as recommended:*

- **D1 — Levels or separate rights?** Recommended: **three levels**, each
  including the one before (§1) — easy to explain, easy to judge.
  Alternative: free combinations of rights per person.
- **D2 — Does a binding on production cover its test instances?**
  Recommended: **yes**, and a test instance may carry its own bindings
  besides.
- **D3 — Who binds?** Recommended: **`tenant_admin` and `server_admin`
  only.**
- **D4 — Do bound people get the instance's matters by default?**
  Recommended: **yes for *Betreuer* and *Verantwortliche*, each may switch
  off per type**; *Beobachter* hear nothing unless they switch it on.
- **D5 — May a *Verantwortliche* switch the site check and the site
  notices?** Recommended: **yes** (§1) — they are about their site.
- **D6 — Partners?** Recommended: **yes, a person of the tenant with the
  platform role `partner` may be bound** — the agency that looks after the
  site is the typical case.
- **D7 — Name of the roles.** Recommended: **Beobachter, Betreuer,
  Verantwortlich** (German in the portal; `observer`, `caretaker`,
  `owner` in records and CLI).

## 9. Stage 0 measured (2026-11-28, reference 0.1.404; the fix 0.1.405)

**M1 — The doors.** Every request that changes an instance goes through the
spool worker (`cmd_process_deploys`). It derives the actor's tenant and
role from identity's own store (`acting_tenant`: `server_admin`,
`tenant_admin`, else none) and refuses a `tenant_admin` of another tenant
(`cross_tenant`). The portal offers 30 of these requests only behind
`require_instance_admin`; `wake` is open on purpose (the waking page).

**F1 — The worker did not judge the role itself (fixed).** On oaap-test a
request `maintenance on` for the probe instance `sc-probe` in the name of
an active account with the role `user` (an app's service account) was
**carried out** — maintenance went on (switched off again at once). The
portal's `require_instance_admin` was the only check for the shared branch
`standby/wake/maintenance/login-required/ai-fetchers/site-watch/site-check`,
for `restart`, and by reading for `rollback`, `throttle`, `rename`,
`config`, `tile`, `token`, `visibility`, `envelope`, `artifact-remove`; for
`promote` only a `tenant_admin` of another tenant was refused. Anyone who
could write the spool — a taken-over portal — could switch these for any
active user. Fixed in 0.1.405: `INSTANCE_ADMIN_ACTIONS` (the portal's
admin doors except `wake`, and except `access`, `care`, `destination`,
which judge the role themselves and file the refusal under their own
name) requires `server_admin` or the instance's `tenant_admin` in the
worker, logs `instance.refused`; test `test_spool_role` (bites without
`maintenance` in the list), all 31 tests that drive the worker green.
**This is where `may()` of §4 goes:** the same refusal, with the binding
as the second way to be allowed.

**M2 — The pair test → production.** A production instance that came by
promotion carries `source.promoted_from` = the test instance's key. On
oaapx01 5 of 8 test instances have a production instance that names them
(`cls-gliss-viewer`, `bdt-app`, `bdt-hub`, `bdt-team`, `pch`), all also
following the name rule `<name>-test`; the other 3 were never promoted.
On oaap-test none. D2 rests on `promoted_from`; a test instance without a
production instance carries its own bindings.

**M3 — Notifications that name an instance:** `instance.down`,
`exposure.found`, `site.google`, `site.notfound`, `site.check`,
`rebuild.failed`, `confirm.pending`, `advisory.image` (the field
`instanz`) — the candidates for the recipient *Zuständige der Instanz*.

## 10. Stage 1 built and measured (2026-11-28, reference 0.1.406)

**Built.** The record: `people: [{person, role, since, by}]` on the instance,
kept by an update, a rebuild and a promotion (`_install_from_dir`, beside
`site_watch`); the tenant's log says `instance.people` with `old -> new`.
`may(actor, instance, action)` in `appctl`: platform role first, then the
strongest binding — the instance's own, or the production instance's it
belongs to (`rehearsal.of`, else `source.promoted_from`, same tenant
only). Judged live from identity's store: a disabled person, or one moved
to another tenant, is refused at once whatever the record lists (§2's
"loses every binding" — the record itself is cleaned when an admin ends
the binding; the card marks it *wirkt nicht*). `BINDING_ACTIONS` lists what
each role may: caretaker `maintenance`, `login-required`, `restart`,
`wake`, `ai-fetchers`, „Jetzt prüfen“ (`site-check` with `op: run`); owner
also `promote`, `rollback`, `site-check` on/off, `site-watch`. A bound
owner promotes only the test instance the production instance was
promoted from, and never creates one. The worker asks `may()` exactly
where 0.1.405 refused; an allowed request carries the role
`bound:<role>` into every audit entry. The spool request
`instance-people` is an administrators' door (D3). CLI `oaap app people
<instance> [add|set <person> <role> | remove <person>]` (German role
names accepted). Portal: the card **Zuständige** at the top of the tab
*Zugang* — person, role, since, by; change, end; bind an active person of
the tenant; the bindings that reach a test instance through its
production instance. Not yet: „Lage gesehen“ (RFC-0142 stage 3), the
portal's buttons for bound people (stage 2, the reduced instance page).

**Tests.** `test_people.py` (52 checks, real worker, no Docker): bind,
refusals (twice, other tenant, inactive, unknown role), caretaker
switches maintenance and restarts, „Jetzt prüfen“ yes and switching no,
promote/rollback/remove/rename/config/visibility/site-watch/binding no,
observer nothing, an unbound instance no, D2 both ways (production covers
test; a test-only binding does not reach production), owner promotes the
paired test instance and no other, disabled and moved accounts lose it,
the card's view; it bites without `maintenance` for the caretaker and
without the way through the production instance. Green as well: the 32
tests that drive the worker, the instance page.

**Measured on oaap-test** (backed up before; staged 0.1.406) through the
real path unit, one active `user` of the probe instance's tenant bound as
*Betreuer* to `sc-probe`:

| Request in that person's name | Verdict |
|---|---|
| maintenance on / off | carried out (6.0 s / 6.5 s), audit role `bound:caretaker` |
| site check „Jetzt prüfen“ | carried out (1.5 s) |
| site check off | refused: *a binding as Betreuer does not allow 'site-check'* |
| promote, remove | refused, same sentence |
| bind someone (`instance-people`) | refused (D3) |
| maintenance on an unbound instance of the tenant | refused, no binding named |

The portal served the card with its form (`/instances/sc-probe?tab=zugang`).
Cleaned up: maintenance off, binding removed, no `people` field left.

## 11. Stage 2 built and measured (2026-11-28, reference 0.1.407)

**Built.**

- **One file for the rule.** `services/bindings.py` holds the roles, what
  each may do, which matters each hears, and the functions `judge`,
  `binding_of`, `production_of`, `hears`, `listeners`, `mine`. The host
  (`may()`, the delivery) and the portal (which buttons, the page) import
  the same file; the portal image copies it. `appctl`'s stage-1 names are
  thin handles on it.
- **The recipient *Zuständige der Instanz*** (§5, D4). `notify_deliver`
  has a third target beside the tenant's lists and the node: for
  `instance.down`, `site.google`, `site.notfound`, `site.check` about an
  instance, every bound person who hears that type gets **one mail of
  their own** (their address is nobody else's business) — Betreuer and
  Verantwortliche by default, Beobachter only if they switched it on;
  through the production instance for its test instance (D2). Only
  active accounts of the instance's tenant with an address. The mail says
  why it came and where to switch it off, before the footer. Its own
  hourly limit per tenant (`people:<tenant>`, 20). Who already got it
  does not get it again on the retry (`people_sent`). The tenant's lists
  get what they got before; the log names the recipient.
- **The person's own switch** per type, kept on the binding (`notify:
  {type: bool}`). It is kept when an admin changes the role. A bound
  person may switch it for **themselves only**: the spool request
  `instance-people` with `op: notify` and their own name is
  `people:self`, which every role may do. For another person, or any
  other `op`, it stays an administrators' door (D3). For a test
  instance bound through production, the switch lands on the production
  instance's binding. CLI: `oaap app people <instance> notify <person>
  <type> on|off`; the list shows what each person hears.
- **Portal: the page „Meine Instanzen“** (`/meine-instanzen`, menu entry
  only for people with a binding). Per instance it shows:
  - the role, and the production instance it comes through;
  - the state light, maintenance, and today's page views and visits;
  - the last site check (red/yellow);
  - the role's buttons: Betreuer get *Wartung an/aus*, *Neu starten* and
    *Jetzt prüfen*; Verantwortliche also *Seiten-Check an/aus*;
  - the person's own mail switches per type.

  The buttons use the administrators' existing doors
  (`/instances/<name>/maintenance`, `…/restart`, `…/site-check`). Those
  doors now ask `require_instance_may` — an administrator, or a binding
  that allows the action, by the same `bindings.judge` — and lead back to
  the page. The administrators' instance page stays closed to a bound
  person.

**Not yet:** the reduced instance page with the tabs Übersicht /
Seitenstatistik / Diagnose (§5); promote and rollback for a
Verantwortliche in the portal (the host allows them, the portal offers
no button yet); push to the phone (stage 3).

**Tests.** `test_people_mine.py`, 47 checks:

- who hears what, and delivery: site.check reaches Betreuer and
  Verantwortliche without a list, one mail each, the list unchanged, the
  observer not;
- through the production instance;
- no mail for an unbound instance or for a type that is not an instance
  matter;
- the retry without doubles;
- the own switch through the real worker: off, an observer on, for
  someone else refused, raising oneself refused, a switch through
  production, kept on a role change, audited;
- the CLI;
- the portal page, the buttons per role, the doors with a binding, the
  admin page still closed, the switch's spool request.

It bites without the recipient in the delivery, without the role default
and without the way through production. Green as well:

- `test_people.py` (its mutation now patches `bindings.production_of`);
- 19 files around it: notify, nav, portal image modules, CLI reference,
  instance page, spool role, site watch, site check, tenant boundary and
  others;
- the 29 further tests that drive the worker.

**Measured on oaap-test** (backed up first, 0.1.407 staged). One active
`user` of the probe instance's tenant was bound as *Betreuer* to
`sc-probe`. The delivery ran in-process with the real registry, identity
store and code: the SMTP send was only recorded, and the person was given
a probe address in memory, because no account on oaap-test has an
address. Nothing was put into the real outbox, which the minute timer
would have sent to the real lists.

| What | Result |
|---|---|
| own switch `site.google` off, through the real worker | carried out (1.0 s), audit `bound:caretaker`, `site.google on -> off` |
| the same person switches for someone else | refused |
| delivery `site.check` about `sc-probe` | one mail to the person, log recipient *Zuständige der Instanz*, the reason before the footer |
| delivery `site.google` (switched off) / `backup.failed` | none |
| portal `GET /meine-instanzen` as that person | 200, the card with *Wartung an* and *Jetzt prüfen*, no *Seiten-Check* switch |
| the same page as an unbound person | 200, „an keine Instanz gebunden“ |
| the administrators' instance page as that person | 403 |
| portal *Wartung an* / *aus* | carried out (6.2 s / 6.2 s), back to the page |
| portal *Seiten-Check aus* (Betreuer) | 403, the check stays on |
| portal own switch `site.google` on | carried out, on the binding |

Cleaned up: maintenance off, binding removed, no `people` field left.

## 12. The reduced instance page (2026-11-28, reference 0.1.408)

**Built.**

- **Who gets it.** `/instances/<name>` asks as before whether the caller
  administers the instance. If not, and the caller is a person whose
  binding works (active account of the instance's tenant, bound directly
  or through the production instance), the same address answers with the
  reduced page. The binding is judged by `bindings.judge`, the rule every
  door uses. Anybody else gets the same answer as before (403 or 404).
- **Three tabs.** The page has *Überblick*, *Seitenstatistik* and
  *Diagnose*. It has no *Zugang*, *Netz & Adressen*, *Deployment*,
  *Konfiguration*, *Fernzugang* or *Verwaltung*. (The tab is called
  *Überblick*, as on the administrators' page; §5 said *Übersicht*.)
  - The head shows the address, the state, the last start, maintenance,
    the role, and the production instance it comes through.
  - *Überblick* offers what the role allows: waking from standby,
    maintenance on/off with the visitors' text, login on all routes, and
    restart. An observer reads one sentence and sees no form.
  - *Seitenstatistik* is the administrators' tab itself, with the site
    check and the AI fetchers.
  - *Diagnose* shows the load history, the state of the containers and
    the restarts. It has no diagnosis window (logs, gateway view) and no
    standby.
- **One template part, not two.** The *Seitenstatistik* panel
  (`SITE_PANEL`) and the cards *Zustand* and *Neustarts* (`DIAG_FACTS`)
  are now template constants that both pages use.
  - Their forms are offered by `may`: the role's spool actions
    (`bindings.ACTIONS`) on the bound page, everything on the
    administrators' page.
  - A "Zum Reiter" link appears only for a tab the page has.
  - The numbers both pages read (restarts, load history, page statistics,
    site check) come from one helper, `_instance_numbers`.
- **Forms.** Every form goes to the door it already used and comes back
  to the same tab. The door asks `require_instance_may`, and the host
  judges again with `may()`.
- **„Meine Instanzen“.** Each card's title links to the instance page.

**Still open:** promote and rollback for a Verantwortliche in the portal;
push to the phone (stage 3).

**Tests.** `test_people_mine.py` now has 59 checks. The new ones cover:

- the bound person's page with exactly three tabs;
- the buttons of a Betreuer, a Verantwortliche and an observer;
- a test instance reached through production;
- an unbound instance staying closed;
- restart coming back to the tab;
- the administrators' page unchanged, with every form.

A mutation gives the observer an owner's actions: the buttons then appear,
so the page follows the role and not a fixed list. The five tests that
render the *Seitenstatistik* panel themselves (`test_site_check`,
`test_site_watch`, `test_site_stats`, `test_site_visits`,
`test_ai_fetchers`) pass the administrators' `may`. `test_care_portal`
knows the two new parts. Green: the 21 files that read the instance
template from the source, and the other files from §11.

**Measured on oaap-test** (backed up first, 0.1.408 staged). One active
`user` of `sc-probe`'s tenant was bound to `sc-probe`, through the real
portal in its container and the real spool worker:

| What | Result |
|---|---|
| Betreuer: `GET /instances/sc-probe` | 200 (0.3 s), role shown, the three tabs, no administrators' tab |
| Betreuer: forms on the page | maintenance, restart, AI fetchers, *Jetzt prüfen*; no site-check switch, no *Hinweise* switch; statistics and restarts present |
| an unbound person of the same tenant | 403 |
| Betreuer: maintenance on / off from the page | carried out (6.2 s / 6.2 s), back to the page, the page then offers *beenden* |
| Betreuer: site check off | 403, the check stays on |
| Beobachter: the page | 200, the sentence, no form |
| Beobachter: maintenance on | 403, unchanged |
| administrator: the page | 200, all tabs, site-check and *Hinweise* switches, no observer text |

Cleaned up: maintenance off, binding removed, no `people` field left.

## 13. Promote and rollback for the Verantwortliche (2026-11-28, reference 0.1.409)

**Built.** A card *Version* on the *Überblick* of the reduced page, only
for a role whose `ACTIONS` contain `promote` or `rollback` (today:
Verantwortlich).

- **Promote — one way only.**
  - The card offers exactly one promotion: from the test instance a
    production instance was promoted from (`source.promoted_from`) into
    that production instance. It shows both versions, and the commit for
    a Git install.
  - It appears on both pages: the production instance's, and the test
    instance's, which is reached through the production instance (D2).
  - It is offered only when the test instance runs bytes that can be
    promoted (a retained package or a recorded commit, the same test the
    administrators' card uses, now one function `_promotable_commit`).
    It is also offered only when `bindings.judge` allows `promote` on the
    **production** instance, where the host judges it.
  - The door `/instances/<test>/promote` lets a bound person through only
    with that target. A new name, another production instance, or both
    fields are refused in the portal and nothing is queued. The host's
    rule from stage 1 stands as well (*a bound owner promotes only the
    test instance this one was promoted from*).
- **A widening stays the administrators'.**
  - If the new version may do more than the running one, the promotion
    stops and names every reason (RFC-0037).
  - The bound page has no tick to confirm it. The portal sends
    `confirmed: false` for a bound person, and the **host** ignores
    `confirmed` whenever the role is `bound:*`.
  - Confirming a widening is a decision about what the production
    instance may do, which is configuration in the sense of §1, so it
    stays with the tenant_admin.
- **Rollback.**
  - The card lists the instance's retained packages. Every one except
    the running package has *Hierauf zurück*.
  - The door `/instances/<name>/rollback` now asks
    `require_instance_may(name, "rollback")`.
  - Download and delete of packages stay on the administrators' page.
- Both forms come back to *Überblick*. A promotion lands on the
  production instance's page.

**Tests.**

- `test_people_mine.py` now has 74 checks. The new ones cover:
  - the card for the Verantwortliche on both pages, with both versions,
    no confirm field, and *Hierauf zurück* only for the older package;
  - a promotion queued to the production instance with
    `confirmed: false`, although the tick was sent;
  - three wrong targets refused without a request;
  - rollback through the door;
  - a Betreuer seeing neither button and refused at both doors;
  - an administrator's tick still counting.

  A mutation gives the Betreuer an owner's actions: both buttons appear.
- `test_people.py`: the worker passes `confirmed=False` for a bound owner
  and `True` for the tenant_admin.
- Green: 26 files, among them the template readers of §12,
  `test_artifact_card`, `test_artifact_deploy`, `test_promote_git` and
  `test_build_rollback_accounts`.

**Measured on oaap-test** (backed up first, 0.1.409 staged). oaap-test
had no promoted pair, so the probe built one from the website starter:

- `vprobe-test`, a test instance from package 0.1.1;
- `vprobe`, promoted from it by root;
- then package 0.1.2 into `vprobe-test`.

One active `user` of the tenant was bound to `vprobe` as Verantwortlich:

| What | Result |
|---|---|
| `GET /instances/vprobe` | 200 (0.3 s), *Nach vprobe übernehmen* with 0.1.2 and 0.1.1, no confirm field, no *Hierauf zurück* (only the running package) |
| `GET /instances/vprobe-test` | 200, the same offer |
| promote into a new name | refused in the portal, no instance created |
| promote `vprobe-test` → `vprobe` (tick sent) | carried out (9.2 s), `vprobe` runs 0.1.2, back on its page |
| the page afterwards | *Hierauf zurück* for the 0.1.1 package |
| rollback to 0.1.1 | carried out (17.2 s), `vprobe` runs 0.1.1 |
| the tenant's log | `instance.promote` and `instance.rollback`, role `bound:owner` |
| as Betreuer: the page / promote / rollback | no buttons; 403 / 403, version unchanged |

Cleaned up: binding removed, both instances removed with their data,
their images deleted.

**Still open:** push to the phone (stage 3); a real mail to a real
address.

## Deutsche Zusammenfassung

**Worum es geht:** Zwischen dem Mandanten-Admin, der alles darf, und den
Anwendern fehlt die Person, die **für eine Sache zuständig** ist — etwa die
Vereinswebseite mit ihrer Test-Instanz: Zugriffe, Auslastung, Statistik und
Seiten-Check sehen, auf Auffälliges reagieren, produktiv setzen — und sonst
nichts im Mandanten.

**Vorschlag:** Der Mandanten-Admin (oder der Server-Admin) **bindet eine
Person an eine Instanz mit einer Rolle**:
- **Beobachter** sieht Zustand, Statistik, Auslastung, Seiten-Check,
  Kurzlinks.
- **Betreuer** darf zusätzlich Wartung an/aus, Anmeldung erzwingen, neu
  starten, aufwecken, KI-Abrufer sperren, „Jetzt prüfen“, „Lage gesehen“.
- **Verantwortlich** darf zusätzlich Test → Produktion, zurück zur vorigen
  Version, Seiten-Check und Hinweise schalten, Kurzlinks der Instanz.
- Nie über eine Bindung: löschen, installieren, Konfiguration, Geheimnisse,
  Adressen, Domains.

Eine Bindung an die Produktivinstanz gilt auch für ihre Test-Instanzen.
Gebunden werden nur Personen des Mandanten, auch Partner (etwa die Agentur,
die die Seite pflegt). Der Knoten prüft jede Aktion mit **einer** Funktion
gegen Rolle und Bindung; das Protokoll nennt, warum jemand durfte.
Gebundene sehen „Meine Instanzen“ im Portal und auf dem Handy (RFC-0142)
und bekommen die Lagen ihrer Instanzen, ohne in einem Verteiler zu stehen.
Das sind **Betriebsrollen**; die fachlichen Rechte in der App bleiben
getrennt (RFC-0045).

**Stufen:** 0 Bestandsaufnahme der Türen, 1 Bindung + Prüfung an jeder Tür,
2 „Meine Instanzen“ und Meldungen an Zuständige, 3 Handy.

**Entschieden (Jörg, 28.11.):** Personen an Instanzen binden, Rollen
zuordnen. **Entschieden (Jörg, 28.11., „Ja, wie empfohlen“): D1–D7 wie empfohlen:** drei Stufen; Bindung gilt auch
für Test-Instanzen; binden dürfen Mandanten- und Server-Admin; Betreuer und
Verantwortliche bekommen die Lagen von selbst; Verantwortliche schalten
Seiten-Check und Hinweise; Partner bindbar; Namen Beobachter, Betreuer,
Verantwortlich.

Stufe 0 gemessen (28.11.): Alle Aufträge an eine Instanz laufen über den
Spool-Worker. **Befund F1:** Der Worker prüfte die Rolle nicht selbst — auf
oaap-test schaltete er die Wartung der Probe-Instanz für ein Konto mit der
Rolle `user` ein (sofort zurückgesetzt). Nur das Portal schützte diese
Türen. Behoben in 0.1.405: Der Worker verlangt für die Admin-Aufträge selbst
server_admin oder den tenant_admin der Instanz und protokolliert die
Absage; genau hier setzt später `may()` mit der Bindung an. Paare Test →
Produktion: über `source.promoted_from` (oaapx01: 5 Paare). Acht
Meldungsarten nennen eine Instanz.

**Stufe 1 gebaut und gemessen (28.11., Referenz 0.1.406):** Bindungen
`people` am Instanz-Datensatz (bleiben bei Update, Neubau, Promotion), eine
Prüffunktion `may()` im Spool-Worker (erst Rolle, dann Bindung, auch über die
Produktivinstanz), Protokoll-Rolle `bound:caretaker`, CLI `oaap app people`,
Karte „Zuständige“ im Reiter Zugang. Auf oaap-test: ein gebundener Betreuer
schaltete die Wartung ein und aus und löste „Jetzt prüfen“ aus; Seiten-Check
schalten, Promotion, Löschen, andere binden und eine nicht gebundene Instanz
wurden abgewiesen. Noch offen: Knöpfe für Gebundene im Portal („Meine
Instanzen“, Stufe 2).

**Stufe 2 gebaut und gemessen (28.11., Referenz 0.1.407):**

- **Eine Regel-Datei:** `services/bindings.py` lesen Knoten und Portal
  gemeinsam.
- **Neuer Empfänger „Zuständige der Instanz“:** Betreuer und Verantwortliche
  bekommen die Meldungen ihrer Instanz (Ausfall, Google, „nicht gefunden“,
  Seiten-Check) per eigener Mail, ohne auf einer Liste zu stehen. Beobachter
  nur, wenn sie es einschalten. Jede Person schaltet für sich selbst ab, im
  Portal oder per CLI.
- **Seite „Meine Instanzen“:** Zustand, Tageszahlen, letzter Seiten-Check,
  die Knöpfe der Rolle und die eigenen Mail-Schalter.

Auf oaap-test: Ein gebundener Betreuer bekam die Seiten-Check-Meldung als
eigene Mail (Versand nur aufgezeichnet, weil kein Konto dort eine Adresse
hat). Er schaltete über das Portal die Wartung ein und aus. „Seiten-Check
aus“ und die Instanzseite der Verwaltung blieben ihm verschlossen.

**Noch offen:**

- die reduzierte Instanzseite mit den Reitern;
- Promotion und Rücksprung im Portal für Verantwortliche;
- das Handy (Stufe 3).

**Verkleinerte Instanzseite (28.11., Referenz 0.1.408):**

- Wer an eine Instanz gebunden ist, bekommt unter derselben Adresse
  `/instances/<name>` eine eigene, kleinere Seite. Sie hat drei Reiter:
  Überblick, Seitenstatistik und Diagnose. Konfiguration, Adressen,
  Zugriff und Verwaltung fehlen.
- Die Knöpfe richten sich nach der Rolle. Beobachter sehen nur.
- Seitenstatistik und Diagnose-Karten sind dieselben Vorlagenteile wie auf
  der Admin-Seite. Es gibt keine zweite Kopie, die irgendwann abweicht.

Auf oaap-test gemessen:

- Ein Betreuer sah die drei Reiter mit seinen Knöpfen. Er schaltete die
  Wartung an und aus. „Seiten-Check aus“ wurde mit 403 abgewiesen.
- Als Beobachter sah er keine Knöpfe, und die Wartung blieb zu (403).
- Die Admin-Seite ist unverändert.

**Noch offen:** das Handy (Stufe 3).

**Promotion und Rücksprung für Verantwortliche (28.11., Referenz 0.1.409):**

- Auf der kleinen Instanzseite gibt es für Verantwortliche eine Karte
  „Version“.
- **Übernehmen** geht nur auf einem Weg: aus der eigenen Test-Instanz in
  die Produktivinstanz, aus der sie stammt. Ein neuer Name oder ein
  anderes Ziel wird abgewiesen.
- Darf die neue Version mehr als die laufende, bricht die Übernahme ab.
  Bestätigen kann das nur die Mandantenverwaltung, auch der Knoten nimmt
  das Häkchen einer gebundenen Person nicht an.
- **Hierauf zurück** steht bei jedem früheren Paket.

Auf oaap-test mit einem eigens gebauten Paar `vprobe-test` → `vprobe`
gemessen:

- Die Verantwortliche übernahm 0.1.2 (9 s) und sprang auf 0.1.1 zurück
  (17 s). Im Protokoll steht beides als `bound:owner`.
- Als Betreuer sah dieselbe Person keine Knöpfe und bekam 403.
- Danach wurde alles entfernt.

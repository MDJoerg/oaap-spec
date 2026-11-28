# RFC-0143: People Bound to Instances — Who Looks After This Site

- **Status:** **Accepted (2026-11-28)** — direction decided by Jörg the
  same day, D1–D7 all as recommended („Ja, wie empfohlen“).
  **Stage 0 measured 2026-11-28 (§9)** — F1: the worker did not judge the
  role of 30 instance requests; fixed in reference 0.1.405.
  **Stage 1 built and measured 2026-11-28 (§10), reference 0.1.406.**
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

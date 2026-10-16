# RFC-0059: Instance Standby, Wake on Use, and Maintenance Mode

- **Status:** **Accepted (2026-10-15)** — Jörg took D1–D7 as recommended.
  **Stage 1 built** the same day (§6), runtime spec `oaap.apps.runtime` 0.2.41
  §2.22 (conformance test 58); §3 measured on `oaap-test` (§3.1). Stages 2–4
  not built.
- **Date:** 2026-10-15
- **Authors:** Jörg (the need: put an instance to sleep for a while and have it
  stay asleep across update and reboot; sleep idle course desks and wake them
  on use; a maintenance mode only an administrator may pass), Claude
  (analysis, write-up)
- **Depends on:** RFC-0046 (the cohort; today the only `stop`/`start`),
  RFC-0016 (one network per instance), RFC-0010 (gateway, forward-auth),
  RFC-0029 (backup), RFC-0051 (node metrics, a periodic sampler exists),
  RFC-0058 (shared folders: a sleeping seat must not take them away)
- **Changes:** `oaap.apps.runtime` (instance record: `state`, `standby`,
  `maintenance`; gateway site for a sleeping or maintained instance),
  `oaap.core.tenant`/portal (buttons), cohort template (`standby_after`)
- **Language:** English per ADR-0003; German summary at the end.

## Summary

Today an instance is either installed-and-running or removed. Three things
people ask for are missing, and they are three states of one record, not
three features:

1. **Standby** — the instance is put to sleep for a time. Its data is kept, its
   containers are not running, and *the state is a fact on the instance
   record*, so an update, a redeploy or a node reboot leaves it asleep.
2. **Wake on use** — a sleeping instance, or one that fell asleep by itself
   after being idle, is woken by the next permitted person who opens it. No
   data is lost; what is lost is the running process (§2.3).
3. **Maintenance** — the instance keeps running, but only an administrator
   passes the gateway. Everybody else gets a configurable "we are back soon"
   page.

## 1. Measured starting point (code read, 2026-10-15; nothing run)

| Question | Answer |
| --- | --- |
| Is there a per-instance stop/start? | No. `oaap app restart <instance>` restarts. `oaap app cohort stop|start` does `docker stop|start` on every container of a cohort and keeps `stopped` on the cohort record; the daily sweep stops a cohort after `ends`. `connector pause|resume` is for tunnels only. |
| What does a by-hand `docker stop` do? | Not measured: whether `oaap status` counts it as down, whether a redeploy or `oaap update` starts it again, how the portal shows it. Containers run with `--restart unless-stopped`, so a stopped one stays stopped over a reboot, but `recreate_instance_containers` creates and starts. |
| Is there any maintenance or idle logic? | No (`grep` finds neither). The gateway authenticates through `forward_auth identity:8000` and adds the user's headers; a refusal comes from identity. |

## 2. Proposal

### 2.1 One state on the instance record

```yaml
state: running | standby | maintenance      # default running
standby:
  since: 2026-10-15T20:00:00Z
  by: admin | auto | cohort-end
  auto_wake: true                           # may a permitted visit wake it
maintenance:
  since: ...
  by: tenant-admin-name
  message: "Wir sind in Kürze wieder da."   # optional; else the tenant default
```

`running` is the only state in which the platform starts containers. Every door
that starts one (`recreate_instance_containers`, `restart`, `update`,
`restore-instances`, the daily sweep) asks the state first. This is the same
shape as `shm`/`resources`/`shared_mounts`: a fact kept by the record, read in
one place.

### 2.2 Standby

- `oaap app standby <instance>` stops the containers **gracefully** (SIGTERM,
  the app's own grace period), marks the state, rewrites the gateway site (§2.3)
  and keeps storage, network, route and users untouched.
- `oaap app wake <instance>` starts them, waits for health, marks `running`.
- *Stop* stays the hard cut it is: `docker stop` without the state change; the
  next update or restart brings the instance back. Standby is the deliberate
  sleep (D1).
- A sleeping instance is still backed up (RFC-0029) — the data is on disk —
  and the backup must not wake it (D6).
- Wake first checks the capacity note of RFC-0046 §6: a wake that would put the
  node over its limits is refused with the number, not attempted.

### 2.3 Wake on use

A sleeping instance's gateway site does **not** proxy to the dead upstream. It
serves one small platform page ("Dein Arbeitsplatz wird geweckt …"). The page is
behind the same `forward_auth` as the instance, so only a person who may open
the instance can wake it; it calls the platform's wake endpoint and polls the
health until the instance answers, then reloads. Public routes do **not**
auto-wake (D4): anybody on the internet could otherwise start containers.

What survives and what does not: **files survive, processes do not.** A sleeping
webtop has no open Eclipse window and no unsaved editor buffer afterwards; the
workspace on disk is untouched. `docker pause` (freeze, memory kept) would keep
the windows but not a reboot, which is the requirement — it may become an
optional second mode (D2), it is not the default.

### 2.4 Automatic standby

```yaml
standby_after: 60m        # instance config, or cohort template field, default off
```

*Idle* is "no request through the gateway for N minutes **and** no open
WebSocket". A webtop streams its picture over one WebSocket for hours without
sending a new request; counting requests alone would put a working person to
sleep. Needs a measurement (§3). A minute-granular sampler is new (RFC-0030 D4
forbids timers *on instances*, not on the platform; the sweep is daily, the
metrics sampler of RFC-0051 is the model). Auto standby is off while the
instance is in maintenance and is never applied to an instance with an open
`access` (RFC-0044).

For a cohort: `standby_after` in the template applies to every seat;
`cohort stop|start` stay (hard cut for all); `cohort standby|wake` are new
and act on state, not on containers.

### 2.5 Maintenance

- `oaap app maintenance on|off <instance> [--message TEXT]`, and the same two
  buttons plus a text field in the portal's instance view (D5: who may press).
- While on, the gateway lets through only the roles named in D3
  (recommendation: `tenant_admin` of the instance's tenant and `server_admin`).
  Everybody else — also on public routes, also API and machine clients — gets
  **503 with `Retry-After`** and a platform page with the configured message;
  JSON clients get a JSON body. The page is the platform's, never the app's.
- The decision is made in `identity` (it already refuses requests) so a
  maintained instance needs no new gateway rule per app; a public route needs
  the check added there too (cf. RFC-0027 on the public-route preflight gap).
- Maintenance is orthogonal to standby: a sleeping instance may be in
  maintenance; waking it does not end it.

## 3. To be measured before it is built

| Case | Question |
| --- | --- |
| By-hand stop | what do `oaap status`, redeploy, `oaap update`, the portal and the nightly backup do with a stopped instance today? |
| Update/reboot | does `recreate_instance_containers` have a single start place that can honour `state`? any door that starts containers without it? |
| Idle signal | can the gateway tell the platform "last request" and "open WebSocket" per instance cheaply? webtop's WebSocket through Caddy: is it visible in the access log at all while open? |
| Wake time | cold start of webtop (`startup_grace_seconds: 180` is a ceiling); of a database-backed app; what the wake page shows meanwhile |
| Gateway rewrite | reload cost and failure mode of rewriting one site file on every state change on a node with ~24 instances |
| Maintenance on public routes | does the identity decision cover a route without `forward_auth`? |
| Backup of a sleeping instance | oaapx01's nightly backup stops apps briefly — does it start a sleeping one afterwards? |

### 3.1 Result (2026-10-15, `oaap-test`, instance `webtop` 0.1.3, reference `6d524c5`)

Measured by stopping the real container by hand (`docker stop`, 3.8 s), and by
reading `appctl.py`. The instance was running again afterwards; its title was
set and set back.

| Case | Result | How |
| --- | --- | --- |
| By-hand stop, `oaap status` | `DEGRADED (8/8 core, 19/20 apps)` — a stopped instance counts as a failure; `oaap app list` shows no state at all | measured |
| `oaap update` | with nothing new ("Already up to date") the container stays stopped; the real update path (migrations that recreate containers, `_repair_stale_mounts`, `sync_*`) was not exercised | measured (no-op) / code read |
| Config change on a stopped instance | **starts it** — `config set` recreates the container with `docker run -d`; the stopped state is silently gone | measured |
| Where containers are started | one function, `recreate_instance_containers`, ends in a single `docker run -d`; fourteen doors call it (config, resources, restart, install, rekey, endpoint, deploy, migrations, repair). The state check can sit there once | code read |
| Nightly backup and tenant archive | both stop only the containers that are running (`docker ps -q`) and start exactly those afterwards — a sleeping instance is neither woken nor stopped | code read |
| What the visitor sees | the gateway dials a name Docker no longer resolves (`no such host`) and answers a raw 502; the platform health probe `/h/<instance>` logs the same error every probe | measured (log) |
| Gateway site | one file per instance, `apps-caddy/<instance>.caddy`; the `forward_auth identity:8000` call already carries `instance=<name>` and the tenant, so identity can decide "maintenance" per instance without a new rule per app | read |
| Wake time | stop then start: HTTP 200 on `/` through the container network after **3 s** (webtop with an existing home; not a measure of when the desktop session is usable) | measured |
| Idle signal | **not available today.** The gateway has no access log and no `metrics` directive, and the admin API answers on `127.0.0.1:2019` inside the container (it did not answer on `localhost`, which resolves to IPv6 there; corrected 2026-10-16). `netstat` in the gateway shows ESTABLISHED connections to the app, but an idle keep-alive connection looks the same as a live WebSocket | measured |
| Maintenance on public routes | not measured | open |

**Consequences for the build:**

1. `recreate_instance_containers` must honour `state: standby` (create, do not
   start) — otherwise the first config change wakes a sleeping instance. This
   is the one place; the fourteen doors need no change.
2. `oaap status` and the portal must know `standby` as a state of its own, or a
   deliberate sleep reads as an outage (and, later, as a cause for alerts).
3. Auto standby (stage 3) needs a new traffic signal at the gateway: Caddy
   `metrics` (requests in flight, which includes an open WebSocket) or a
   per-site access log. That is a gateway change and has to be measured with a
   real WebSocket session before D7's stage 3 is promised.


## 4. Decisions for Jörg

| # | Question | Recommendation |
| --- | --- | --- |
| D1 | Is *stop* (hard cut, comes back on the next update/restart) kept apart from *standby* (deliberate sleep, survives update and reboot)? | Yes, as Jörg described it: two verbs, standby is a state on the record. |
| D2 | `docker pause` (RAM kept, not reboot-proof) as a second mode? | Not now; standby = containers stopped. Revisit when a customer asks for "windows still open". |
| D3 | Who passes a maintained instance? | `tenant_admin` of its tenant and `server_admin`; configurable per instance later. |
| D4 | May a public route wake an instance? | No. Only a person who passes the instance's own authentication wakes it. |
| D5 | Who may set standby, wake, maintenance? | The tenant administrator for instances of their tenant; the server administrator everywhere; a trainer for their cohort's seats. |
| D6 | Does a sleeping instance stay in backup and the node sweep? | In backup yes (data); never woken by a backup or a sweep. |
| D7 | Order of work | Stage 1: state + CLI `standby`/`wake`/`maintenance` + the two pages (measure §3 first). Stage 2: portal buttons. Stage 3: auto standby + wake on use. Stage 4: cohort `standby_after`. |

## 5. Not part of this RFC

- Scale-to-zero billing, or standby of the **node**.
- Freezing the memory of a running app (D2).
- Scheduled maintenance windows ("every Sunday 02:00") — a timer on top of
  §2.5, not a new state.

## 6. Stage 1 as built (2026-10-15, reference not yet on a node)

| Piece | Where |
| --- | --- |
| State on the record (`state`, `standby`, `maintenance`) | registry; `instance-modes.json` for identity and status, written synchronously |
| `oaap app standby|wake|maintenance` | `appctl.py` (`standby_instance`, `wake_instance`, `maintenance_set`); the portal's worker has the same three actions for stage 2 |
| One start place honours it | `recreate_instance_containers`: `docker create` while `standby` |
| One site body shows the waking page | `site_body`: every route, every entry point; preflight answers 503; `public` never wakes |
| Maintenance | `site_body` makes every route ask identity; `identity` answers 503 first (anonymous included), administrators pass |
| Waking page | portal `/wake/<instance>`, gateway key `apps/wake-key`; GET shows, POST wakes |
| `oaap status` | sleeping containers leave the count, "n in standby" |
| Test | `test/test_standby.py` (42 cases: sites, create-not-start, order of standby/wake, identity, portal page) |

Order that matters and is tested: standby writes the record and the waking page
**before** the containers stop; wake gives the address back **after** the app
answers.

### 6.1 Measured on `oaap-test` (2026-10-15, instance `webtop`, reference `a3f9107`)

| What | Result |
| --- | --- |
| `oaap app standby webtop` | 6 s; container `Exited (0)`; `app list` shows `STANDBY`; `oaap status` `HEALTHY (19/19 apps running, 1 in standby)` |
| Visitor with a valid key | `503`, `Retry-After: 5`, `Cache-Control: no-store`, the waking page ("Dein Arbeitsplatz wird gestartet") |
| An anonymous visitor | `303` to the login, as before |
| `GET` of the page | does not wake (container stays down) |
| CORS preflight (`OPTIONS`) | `503`, not a dead upstream |
| The portal's `/wake/<instance>` without the gateway key | `403` |
| `config set` on the sleeping instance | container re-made, state `Created`, **not started**, still `STANDBY` — the case that woke it before |
| `restart` on the sleeping instance | stays `Created`; message was "running since 0001-01-01" — fixed to "recreated; it stays in standby" (`35b12d1`) |
| Wake by `POST` (what the page's script does) | `{"asleep": true}`, then HTTP 200 on the instance address after **5 s**; state removed; `HEALTHY 20/20` |
| Maintenance on | machine principal with a key: `503`; anonymous: `503` with the configured sentence; JSON caller: `{"error":"maintenance",...}`; `Retry-After: 300`; `/auth/login` still `200`; `app list` shows `MAINTENANCE`; off: back to normal |

### 6.2 Update, reboot, wake after reboot, administrator (2026-10-15, `oaap-test`)

| What | Result |
| --- | --- |
| `oaap update` with a real revision (an empty commit) while `webtop` sleeps | the container stays `exited`, same id; `app list` shows `STANDBY`; the site is rewritten with the waking page ("1 instance site(s) rewritten"); `HEALTHY 19/19, 1 in standby` |
| Node reboot (`systemctl reboot`, physical machine) with `webtop` asleep | after boot `webtop` is `exited`, the 19 other apps are up, the gateway answers `303` to an anonymous visitor, `app list` still shows `STANDBY` |
| `oaap app wake webtop` after the reboot | `running` after 5 s, `HEALTHY 20/20` |
| Maintenance, an administrator principal | a key whose principal has `tenant_admin` (of the instance's tenant) is **not** answered `503` — it passes to the route's own role check (`403`, because `tenant_admin` alone is no route role, the same answer as with maintenance off); anonymous gets `503` |

Not measured: the waking page and maintenance page in a real browser; a
**human** administrator session (passwords were not created on the node —
Jörg opens `…/` of a maintained instance as `server_admin` to see it);
a multi-service instance; a wake with no room on the node.

**Two findings that are not this RFC's, found on the way (follow-up, same day):**

1. After the first reboot the **broker** (`oaap-broker-1`, profile `broker`)
   stayed `exited (0)` although its policy is `unless-stopped`; the other
   containers came back. **Not reproducible:** a second reboot of the same node
   brought all eight core services back, and a real `oaap update` (new revision)
   does not touch the core containers or their `HasBeenManuallyStopped` flag
   (read from Docker's `config.v2.json`, all `False` before and after). What is
   left is a stale manual-stop flag from an earlier hand stop of the broker
   (it was `docker stop`ped and started again several times on 03.10.) — not
   proven. Nothing in OAAP's own code stops the broker at shutdown.
2. `oaap status` could not see it: the core total came from
   `compose ps --services`, which lists running services only, so a stopped core
   service was printed as `HEALTHY (7/7 …)`. **Fixed** (`f851850`): the total is
   the union of the services the compose file defines (`config --services`) and
   every container that exists (`ps -a`); a stopped one is listed and counts as
   `DEGRADED` (exit 1), a defined one without a container shows `missing`.
   Measured on `oaap-test` with the broker stopped: `DEGRADED (7/8 core
   services …)`, exit 1; started again: `HEALTHY (8/8 …)`. A sleeping instance
   still does not count against the apps.

## 7. Stage 2 as built (2026-10-16)

The portal's instance view (tab Diagnose) has a card "Standby und Wartung":
state with who/since, and the one possible step per axis (standby ↔ wake,
maintenance on with a visitor text ↔ off). Routes `POST
/instances/<name>/standby|wake|maintenance` check `require_instance_admin`,
refuse while a deployment runs, queue the worker action that already existed
and show the host's verdict (wake waits up to 200 s). No new host logic: the
buttons are a third door to the same three functions. Tested with 10 cases
(job per button, trimmed text, refusal shown, 403/404 without queueing).
**Not measured in a real browser** on a node.

## 8. Stage 3 as built (2026-10-16, measured on oaap-test)

**The signal.** The gateway's global options gain `servers { metrics { per_host } }`.
Caddy then counts, per listener (`srv0`, `srv1`, ...) and per host name, the requests
it is handling now (`caddy_http_requests_in_flight`) and the ones it has finished.
Measured in a throw-away Caddy 2.11.4 next to the real gateway on oaap-test: a slow
request shows up as `in_flight 1` on its own listener while it runs. The server names
move when a site is added or removed, so `services/idle.py` reads the listener ports
from the admin API's `/config/` every time and maps listener port -> instance
(each instance has its own LAN port) and host name -> instance (the automatic
addresses). The platform's health probe lives on its own listener and does not count.

**The rule.** An instance is *in use* in a minute when anything of it is in flight or
its finished-counter changed. Every doubt counts as use: a missing number, a counter
that went down, an instance the gateway's numbers never showed (never put to sleep).
A gateway that cannot be asked changes nothing.

**The act.** `metrics sample` (the minutely job) first runs `idle_sweep()`. An instance
that has `standby_after` (minutes, at least 5) and has been out of use that long goes
through the normal `standby_instance` (waking page first, then stop) with `by:
auto-standby`. Not touched: instances in maintenance, with a deployment in flight, or
already asleep. Opt-in per instance: `oaap app standby-after <instance> <minutes>|off`
(stage 4 sets it from the cohort template). Wake on use is stage 1's waking page.

**Tests:** `test/test_idle.py` (parsing, mapping, clock, the sweep, fail-safe cases).

**Measured.** Throw-away Caddy: a real WebSocket (101 Switching Protocols) shows
`in_flight 1` while open and 0 after. On oaap-test the instance `webtop` with
`standby-after 5` went to `STANDBY` 301 s after the first count; `oaap app wake` woke
it, `standby-after webtop off` removed the setting, the node stayed HEALTHY. The
measurement found one bug: Caddy writes no number for a listener nobody has talked to,
so a never-contacted instance was "unseen" and would never have slept; a listener the
gateway's config has now counts as seen.

**Not measured:** a WebSocket through the *real* gateway to a real instance behind a
login; the effect of the `metrics` directive on a loaded gateway; host names that are
not automatic addresses; the other nodes; a real person waking an auto-standby instance
in a browser.

**Own host names (added after the first measurement).** An instance's own names (its
`address` and `aliases`, RFC-0009/0018) are now mapped like the automatic addresses, so
traffic on them counts as use. Before, an instance with its own domain could have gone to
sleep while someone worked on it. Tested locally (`test_idle.py`); not measured on a node.

## 9. Stage 4 as built (2026-10-16, measured on oaap-test)

The cohort template (RFC-0046) accepts `standby_after` at top level (the cohort
default) and per app (the app wins; `off` or `false` = never, even if the cohort says
so). Whole minutes, at least 5, anything else makes the template unusable (reported
with the other problems, not silently defaulted). `cohort create`/`add` write it into
each instance record; `cohort reset` brings the record back to what the template says;
a redeploy keeps whatever the record has (this also closes a stage 3 gap: a
hand-set `standby_after` was lost on redeploy). Shared instances of a cohort follow the
same rule, so a trainer's shared Forgejo can opt out with `standby_after: off`.
YAML reads a bare `off` as boolean false; both spellings mean "off".

**Tests:** `test/test_cohort.py` (validation, precedence, the record after `create`,
source checks for redeploy and reset).

**Measured** on oaap-test with a throw-away cohort (2 seats, Wegweiser, `standby_after: 10`): both
records carried it after `cohort create`; `reset --keep-home` kept it; seat 01 went to standby by
itself 691 s after the measurement began, seat 02 shortly after; `cohort remove --purge --users`
left nothing behind. `reset` reads the cohort's *stored* copy of the template, so a later change in the
trainer's file does not reach it (RFC-0046 §2, by design); there is no step yet that changes the
stored template. **Not measured:** a template change on a node (only locally), a real person waking a seat.

## Deutsche Zusammenfassung

Drei Wünsche, ein Zustand am Instanz-Eintrag: **Standby** (die Instanz
schläft, Daten bleiben, und der Schlaf überlebt Update, Redeploy und Reboot,
weil der Zustand am Eintrag steht, nicht im Container), **Aufwecken bei
Benutzung** (wer die Instanz öffnen darf, weckt sie; Dateien bleiben, laufende
Programme nicht — ein schlafender Desktop hat danach keine offenen Fenster)
und **Wartungsmodus** (die Instanz läuft, nur ein Administrator kommt durch,
alle anderen sehen eine einstellbare „Wir kommen bald wieder“-Seite mit 503).
Dazu der automatische Standby für Kohorten (`standby_after: 60m`): „unbenutzt“
heißt keine Anfrage UND keine offene WebSocket-Verbindung, sonst schläft ein
arbeitender Teilnehmer ein.

*Stop* bleibt der harte Schnitt (kommt beim nächsten Update/Neustart zurück),
Standby ist der gewollte Schlaf. Nichts ist gebaut; §3 nennt, was zuerst
gemessen werden muss (heutiges Verhalten bei einem von Hand gestoppten
Container, Idle-Signal, Weckzeit). Sieben Entscheidungen D1–D7 warten auf Jörg.

**Stufe 3 (16.10.):** Das Gateway zählt jetzt offene Anfragen je Instanz (Caddy-Metriken); eine Instanz mit `standby_after` legt sich nach so vielen ruhigen Minuten selbst schlafen (`oaap app standby-after`). Jede Unsicherheit zählt als Benutzung. Auf oaap-test gemessen (`webtop` schlief nach 301 s ein, wurde geweckt).

**Stufe 4 (16.10.):** Die Kohortenvorlage nimmt `standby_after` an (Kohortenwert und je App, die App geht vor, `off` schaltet ab; mindestens 5 Minuten). `cohort create/add/reset` setzen es am Instanz-Eintrag, ein Redeploy behält es (das war in Stufe 3 eine Lücke). Lokal gebaut und getestet, auf keinem Knoten gemessen.

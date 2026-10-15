# RFC-0059: Instance Standby, Wake on Use, and Maintenance Mode

- **Status:** Proposed (2026-10-15) — nothing built; §3 measured on `oaap-test`
  the same day (§3.1), D1–D7 are open.
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
| Idle signal | **not available today.** The gateway has no access log and no `metrics` directive, and the admin API does not answer inside the container. `netstat` in the gateway shows ESTABLISHED connections to the app, but an idle keep-alive connection looks the same as a live WebSocket | measured |
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

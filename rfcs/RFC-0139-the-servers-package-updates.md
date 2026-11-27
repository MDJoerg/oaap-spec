# RFC-0139: The Server's Package Updates — a Daily Reminder and a Button

- **Status:** **Accepted (2026-11-27)** — D1–D9 decided by Jörg, all as
  recommended (§8). **Stage 0 measured 2026-11-27 on oaap-test (§9). Stage 1 built 2026-11-27
  (§10)**: reference 0.1.392, oaap.core.updates 0.12, oaap.core.notifications 0.15.
  **Stage 2 built and measured 2026-11-27 (§11)**: reference 0.1.393,
  oaap.core.updates 0.13, oaap.core.notifications 0.16.
- **Date:** 2026-11-27
- **Authors:** Jörg (the need: "aktiv melden, wie viele Updates es gerade für
  apt gibt … als Erinnerung für den Admin, einmal täglich"; and the question
  whether the node may install such updates itself, and whether that is a
  risk), Claude (facts from the fleet, design)
- **Depends on:** oaap.core.updates 2.6–2.8 (host care: automatic updates,
  the platform's own reboot, Debian advisories), oaap.core.notifications
  (RFC-0080; matters with a daily reminder, RFC-0085 A4), RFC-0128 (a care
  measure as a portal order through the spool; F13: anything detached from
  the minute job runs as its own systemd unit), the backup (`oaap backup
  create`)
- **Changes (when accepted):** host care (the count of waiting packages by
  kind), notifications (a matter `host.updates`), the CLI (`oaap node care
  upgrade`), the portal (a section on the health page with a button)

## Summary

The platform already looks after the operating system's **security**
updates: it checks that unattended-upgrades is fully switched on, plans the
reboot after a new kernel itself, and compares Debian's advisories with the
installed packages (`advisory.host`). What it does not say is how many
**other** updates wait — and on our nodes those are almost all Docker's.

This RFC adds two things:

1. **A daily reminder** per node, `host.updates`, while packages wait: how
   many, how many of them security, how many Docker, and whether a reboot
   waits. Silent when nothing waits.
2. **Updating on the administrator's word**, from the portal or the CLI:
   backup first, then the waiting packages — Docker only when ticked —, then
   a check that every app is back. Never automatic beyond what
   unattended-upgrades already does.

## 1. The fleet today (read 2026-11-27, 0.1.390)

| Node | waiting | security | Docker | other | reboot |
|---|---|---|---|---|---|
| oaap-test | 6 | 0 | 6 | 0 | no |
| raspberrypi | 111 | 0 | 6 | 105 (Raspberry Pi archives) | no |
| oaap-bernd | 6 | 0 | 6 | 0 | no |
| oaap-demo | 9 | 0 | 7 | 2 | **yes** — kernel 6.12.118 installed, no reboot window set |
| oaapx01 | 6 | 0 | 6 | 0 | no |

Automatic updates are on everywhere; the security archive is empty on every
node because unattended-upgrades took it already. What waits comes from
**vendor archives**: Docker's own (`docker-ce`, `docker-ce-cli`,
`containerd.io`, `docker-buildx-plugin`, `docker-compose-plugin`, …) and on
the Raspberry Pi its distribution's archives, which unattended-upgrades does
not cover by default.

## 2. Is it a risk to let the node update itself?

**Security updates from the distribution: no — that is the state today and
it stays.** Small, tested fixes from one archive; the reboot after a kernel
is planned by the platform (oaap.core.updates 2.7).

**Everything else, automatically: yes, mainly because of Docker.**

- Updating `docker-ce` or `containerd.io` **restarts the Docker daemon**, and
  with it every container on the node at once — every tenant's apps, the
  gateway, identity. The node has no `live-restore`. That is an outage of
  every app for the length of the restart, at a moment nobody chose.
- A new Docker version can **behave differently**. We have the example from
  this week: on Docker 29 `docker builder prune --filter until=…` silently
  frees nothing (RFC-0128 F11), and image sizes are reported packed under the
  containerd store (F10). A platform that calls Docker everywhere must meet a
  new Docker on oaap-test first, not on oaapx01 at 06:00.
- The Raspberry Pi archives carry firmware and kernel packages of their own;
  an unattended mass update there is the classic way to an unbootable Pi.

So: the node **reminds** daily, and the administrator **decides** — with one
button that does the careful steps every time.

## 3. The daily reminder `host.updates`

- **Counted by host care** with the measurement it already makes
  (`apt list --upgradable` after the daily list refresh of apt's own timer):
  `waiting`, `security`, `docker` (the packages of Docker's archive),
  `other`, plus the existing `reboot required`.
- **A matter** (open while `waiting > 0`, closed when it reaches 0) with a
  **reminder every 24 h** (`remind: 24`, as the fleet's matters, RFC-0085
  A4). Category `operations`, scope `node` — the node's administrators hear
  it under their routing; tenants never.
- **The mail**, German like every notification:

  > [oaapx01] 6 Updates für den Server warten
  >
  > 6 Pakete warten auf ein Update, davon 0 Sicherheitsupdates, 6 von Docker.
  > Ein Neustart ist nicht nötig. Einspielen: Portal → Gesundheit → Updates,
  > oder `sudo oaap node care upgrade`.

- If security updates wait (unattended-upgrades failed or is off), the
  existing `advisory.host` speaks with its own urgency; `host.updates` only
  names the number.
- The weekly report (RFC-0083) gets the same line.

## 4. Updating on the administrator's word

One function, used by the CLI and the portal (no second way):

1. **Show first** (`--dry-run`, the portal's page): the waiting packages,
   grouped security / Docker / other, with installed and new version.
2. **Backup** (`oaap backup create`). If it fails, nothing is updated.
3. **Update** in its own systemd unit (`systemd-run --unit=oaap-upgrade`,
   RFC-0128 F13), with apt's non-interactive settings and the existing
   configuration files kept (`--force-confold`); only upgrades, **never a
   removal** (`apt-get install --only-upgrade <packages>` with the computed
   list). Docker's packages only when ticked (D4).
4. **Check**: core services and instances as `oaap update` checks them;
   containers that were running before and are not now are named.
5. **Reboot**: when a new kernel was installed, the existing reboot planning
   takes over (announcement, window, protections) — never an immediate
   reboot from here.
6. **Log**: `host.upgraded` in the audit log and as an event (once), with
   counts, duration and the result of the check.

**Portal:** a section „Updates" on the health page (server_admin only),
showing the list of step 1, a tick „Docker mit aktualisieren — alle Apps
starten dabei einmal neu", and the button „Jetzt einspielen". The order goes
through the spool like „Platz" (RFC-0128); the page shows the running unit
and then the result.

**CLI:** `sudo oaap node care upgrade [--dry-run] [--docker]`.

## 5. Stages

| Stage | Content |
|---|---|
| 0 | Measure on oaap-test: a Docker update through the function's steps — how long the daemon is away, whether every container comes back by itself, what the gateway answers meanwhile |
| 1 | Counts in host care, the matter `host.updates` with the daily reminder, the line in the weekly report, `oaap node care upgrade --dry-run` |
| 2 | `oaap node care upgrade [--docker]` with backup, unit, check, log |
| 3 | The portal's section „Updates" with the button |

## 6. Tests and measurement

- host care: counting from recorded `apt list --upgradable` outputs (Debian,
  Raspberry Pi OS, Docker's archive); the matter opens, reminds after 24 h,
  closes at 0.
- upgrade: a failed backup updates nothing; the package list without Docker
  contains none of Docker's packages; no removal is ever planned; the run
  survives the minute job (its own unit).
- Measured on oaap-test (stage 0, then each stage); then raspberrypi for the
  vendor archive case.

## 7. Non-goals

- Updating automatically beyond unattended-upgrades.
- A distribution upgrade (Debian 13 → 14).
- One button for the whole fleet. Per node first; an order of nodes
  (oaap-test first) is the administrator's, later perhaps FleetView's.
- Updating the packages inside the apps' images (that is RFC-0130 and
  „Neu bauen“ in the store).

## 8. Decisions

Decided 2026-11-27 by Jörg: **all as recommended**.

- **D1 — How often does the reminder come?** Recommended: **once a day while
  packages wait** (a matter with `remind: 24`), as asked. Alternative: only
  when the number changes or security updates wait — fewer mails, but no
  reminder for six Docker packages that wait for weeks.
- **D2 — Who hears it?** Recommended: **the node's administrators**
  (scope `node`), never a tenant.
- **D3 — Does the node install anything beyond security by itself?**
  Recommended: **no** (§2).
- **D4 — Docker in the button?** Recommended: **only when ticked**, with the
  sentence that every app restarts once; unticked by default.
- **D5 — Backup before every update?** Recommended: **yes**, and no update
  when it fails.
- **D6 — When does the button run?** Recommended: **at once** (the person
  pressing it chose the moment); a later „im Neustartfenster“ only if wanted.
- **D7 — Reboot after a kernel?** Recommended: **the existing planning**
  (announced, window, protections), never immediately from the button.
- **D8 — Where in the portal?** Recommended: **a section „Updates“ on the
  health page**, server_admin only.
- **D9 — The Raspberry Pi's 105 other packages?** Recommended: **counted and
  offered like everything else**, no special case; the first run there is
  measured (stage 2) before anyone relies on it.

## 9. Stage 0 measured (2026-11-27, oaap-test)

The six Docker packages, by hand along the steps of §4: backup, then
`systemd-run --unit=oaap-upgrade-probe --wait` with `DEBIAN_FRONTEND=
noninteractive apt-get install --only-upgrade -y -o
Dpkg::Options::=--force-confold <the six>`. A probe asked the portal and
vuebung's chat through the edge every ~1.3 s.

| | |
|---|---|
| Versions | docker-ce 29.7.1 → **29.10.1**, containerd.io 2.2.6 → **2.4.2**, compose plugin 5.4.0 → 5.8.0, buildx 0.36.1 → 0.39.1 |
| apt in its unit | 1 min 24 s, success, 6 upgraded, 0 removed, no question asked |
| containerd restarted | 08:38:15 UTC |
| dockerd up again | 08:39:11 UTC |
| **Outage seen from outside** | **55 s** (08:38:16–08:39:11): the edge answered 502 for portal and chat |
| Containers | 63 running before, **63 after, the same names**, all `unless-stopped`, none started by hand; vaultwarden briefly `health: starting` |
| Platform afterwards | 53/53 apps running; `oaap node care space --dry-run` works; `docker compose version` v5.8.0 |

**Findings.**
- **F1** The outage is about one minute for **every** app of the node, and it
  begins with **containerd**, not with docker-ce: containerd's package restarts
  its service first, dockerd follows at the end of the run. The portal's
  sentence for the tick must therefore say „alle Apps sind etwa eine Minute
  nicht erreichbar“.
- **F2** Nothing had to be restarted by hand; the restart policy
  `unless-stopped` that every platform and app container carries brings them
  back. The check of §4 step 4 is still needed — it found nothing here, but a
  container without that policy would stay down.
- **F3** `--force-confold` with `noninteractive` asked nothing; Docker's
  packages have no configuration file of ours (`/etc/docker/daemon.json` is the
  platform's and stayed).
- **F4** (older, not from the update) the core service `fleet` on oaap-test
  has stood exited for two days (`Exited (0)`); `oaap status` says 10/11.
- Not measured: the Raspberry Pi's vendor archives (stage 2, D9); a node with
  sleeping (standby) instances that the restart must not wake.

## 10. Stage 1 built (2026-11-27)

- host care: `upgradable()` parses `apt list --upgradable` (C locale);
  `updates_facts()` gives the counts into the care file; `updates_line()` for
  `oaap status` and the health page -- shown only when apt answered.
- notifications: `host.updates` (operations, node, `remind: 24`); the text
  names the counts, the reboot, the minute of Docker and the dry run.
- weekly report: the ledger's care part carries the counts; the node's
  report has „Updates für den Server: n warten (s Sicherheit, d Docker)“.
- CLI: `oaap node care upgrade --dry-run [--docker]`; without `--dry-run` it
  says that installing comes with stage 2.
- `test_host_updates.py` (29 checks).

**Measured (2026-11-27).** On oaap-test (staged 0.1.392): the care file
carries `updates = {waiting: 0, …}` -- nothing waits since stage 0 took
Docker --, `oaap status` says „Updates: none waiting“, `upgrade --dry-run`
„No package waits“. On raspberrypi (still 0.1.390), the new module run read
only from /tmp: **111 waiting = the raw list's 111**, 0 security, 6 Docker
(by name), 105 other (`bluez-firmware` from the Pi's `stable` archive); the
German line „Updates: 111 warten, davon 0 Sicherheit, 6 Docker …“. **Not
measured:** the real mail of `host.updates` and its 24-hour reminder -- on
oaap-test nothing waits; first seen on the fleet after the rollout.

## 11. Stage 2 built and measured (2026-11-27)

**Built:** `oaap node care upgrade [--docker] [--status]` (§4 steps 2-6):
`apt-get update`, the plan (Docker's only with `--docker`), its own unit
`oaap-upgrade`, `oaap backup create` (nothing installed when it fails),
`apt-get install --only-upgrade --no-remove -y --force-confold <names>`, the
check that every container that ran before runs again (up to 300 s), audit
`host.upgraded`, the event `host.upgraded`, a fresh host-care reading. The
CLI follows the log (`data/upgrade/upgrade.log`); Ctrl-C leaves the unit
running. `test_host_updates.py` now 63 checks.

**Measured on oaap-test** (versions set back by hand to have something waiting:
krb5-locales u2 → u1 from trixie, Docker 29.10.1 → 29.10.0, containerd
2.4.2-4 → -3, compose 5.8.0 → 5.7.2):

| Run | What | Backup | apt | Result |
|---|---|---|---|---|
| 1 | without `--docker` | 7 min 39 s | 2 s | krb5-locales from trixie-security; 63/63 containers; 4 of Docker left, said so; audit `ok`, mail sent |
| 2 | `--docker` | ~7 min | ~1.5 min | Docker 29.10.1, containerd 2.4.2-4; **62 s** outage seen from the edge (chat first, then the portal); 63/63 containers back by themselves |
| 3 | without `--docker`, after the fixes | 6 min 47 s | 2 s | clean log; afterwards "none waiting", the matter closed |

**Found and fixed while measuring:**

- F1: a host-care reading **during a dpkg run** said "0 waiting" while five
  waited (lists half-written) -- it would close the matter and open it again
  with a new mail. Now the last reading stands while apt or dpkg runs (seen
  in `/proc`, no lock taken).
- F2: the first version of that check took the name `unattended-upgr` alone --
  but `unattended-upgrade-shutdown --wait-for-signal` runs all day on every
  node under the same name; the count would never have changed again. Now
  the command line tells the guard from a run.
- F3: the CLI stopped following during the backup: `systemctl is-active`
  once gave no clear answer. Now only a clear "inactive" (code 3, or 4 = no
  such unit, after `--collect`) counts, twice in a row.
- F4: the CLI printed the last run's log first and then a fragment at the old
  offset -- the unit emptied the log only after the CLI began to follow. Now
  the starter empties it before the unit starts.
- dpkg's progress lines ("Reading database ... 5%") are left out of the log.

**Observed, not changed:** while the backup copies, the notifications wait
(oaap.data.backup 2.2.2). A matter that becomes due during the backup is
mailed right after it -- in run 3 the matter was new (set back at 11:42),
so "open" went out at 11:49:15 and "close" a minute later. In real use the
matter is open long before anyone presses the button.

**Not yet:** the portal's section with the button (stage 3); a run on the
raspberrypi's vendor archives (D9).

## Deutsche Zusammenfassung

**Heute:** Sicherheitsupdates spielt jeder Knoten schon selbst ein
(unattended-upgrades ist überall an), den Neustart nach einem neuen Kernel
plant die Plattform, offene Debian-Sicherheitshinweise meldet sie. Gelesen am
27.11.: überall **0 Sicherheitsupdates offen**; was wartet, sind fast nur die
**Docker-Pakete** aus Dockers eigenem Archiv (6–7 je Knoten), auf dem
raspberrypi 111 Pakete aus den Raspberry-Pi-Archiven. oaap-demo wartet auf
einen Neustart (kein Neustartfenster gesetzt).

**Risiko, wenn der Knoten alles selbst einspielt:** Ja, vor allem wegen
Docker. Ein Docker-Update startet den Docker-Dienst neu und damit **alle Apps
des Knotens auf einmal**, zu einem Zeitpunkt, den niemand gewählt hat. Und eine
neue Docker-Version kann sich anders verhalten – diese Woche gesehen:
`builder prune --filter` räumt unter Docker 29 nichts mehr (RFC-0128 F11).
Auf dem Pi kommen Firmware- und Kernelpakete hinzu. Deshalb: Sicherheit weiter
automatisch, der Rest auf Wort des Admins.

**Vorschlag:**
1. **Tägliche Erinnerung** `host.updates` je Knoten, solange etwas wartet:
   wie viele, davon Sicherheit, davon Docker, ob ein Neustart wartet. Still,
   wenn nichts wartet. Dieselbe Zeile im Wochenbericht.
2. **Einspielen auf Knopfdruck** (Portal → Gesundheit → Updates, oder
   `sudo oaap node care upgrade`): erst anzeigen, dann Sicherung (scheitert
   sie, passiert nichts), dann die Updates in einer eigenen systemd-Unit, nie
   eine Paketentfernung, Docker nur mit Haken („alle Apps starten einmal
   neu“), danach Prüfung, ob alle Apps wieder laufen. Ein Kernel-Neustart
   läuft über die vorhandene Neustartplanung, nie sofort.

**Stufe 0 gemessen (27.11., oaap-test):** Docker 29.7.1 → 29.10.1, containerd 2.2 → 2.4, Compose 5.4 → 5.8 in einer eigenen Unit (1:24 min, nichts entfernt, keine Rückfrage). **Von außen 55 Sekunden alles weg** (Edge 502), beginnend mit dem Neustart von containerd; danach **alle 63 Container von selbst zurück**, 53/53 Apps laufen. Der Satz am Haken muss also sagen: „alle Apps sind etwa eine Minute nicht erreichbar“. Älter und nicht vom Update: der Dienst `fleet` auf oaap-test steht seit zwei Tagen.

**Stufen:** 0 Docker-Update auf oaap-test messen (wie lange weg, kommen alle
Container von selbst zurück), 1 Zählung + Erinnerung + `--dry-run`,
2 Einspielen per CLI, 3 Knopf im Portal.

**Angenommen am 27.11.2026, D1–D9 alle wie empfohlen:** täglich solange etwas wartet (D1), nur die
Admins des Knotens (D2), nichts Weiteres automatisch (D3), Docker nur mit
Haken (D4), immer Sicherung vorher (D5), sofort beim Drücken (D6), Neustart
über die vorhandene Planung (D7), Abschnitt auf der Gesundheitsseite (D8),
Pi ohne Sonderfall, erster Lauf dort gemessen (D9).

**Stufe 2 (27.11.2026):** `sudo oaap node care upgrade [--docker]` spielt ein --
Sicherung zuerst, eigene Unit, nur Aktualisieren (`--no-remove`), danach
Prüfung, ob alle Container wieder laufen, Audit und Meldung `host.upgraded`.
Auf oaap-test dreimal gemessen; Docker-Update von außen 62 s Ausfall, alle 63
Container von selbst zurück. Beim Messen vier Fehler gefunden und behoben,
darunter einer aus Stufe 1: eine Zählung mitten in einem dpkg-Lauf ergab 0.

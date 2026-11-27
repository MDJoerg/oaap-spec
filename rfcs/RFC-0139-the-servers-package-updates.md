# RFC-0139: The Server's Package Updates — a Daily Reminder and a Button

- **Status:** **Accepted (2026-11-27)** — D1–D9 decided by Jörg, all as
  recommended (§8). Nothing built.
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

**Stufen:** 0 Docker-Update auf oaap-test messen (wie lange weg, kommen alle
Container von selbst zurück), 1 Zählung + Erinnerung + `--dry-run`,
2 Einspielen per CLI, 3 Knopf im Portal.

**Angenommen am 27.11.2026, D1–D9 alle wie empfohlen:** täglich solange etwas wartet (D1), nur die
Admins des Knotens (D2), nichts Weiteres automatisch (D3), Docker nur mit
Haken (D4), immer Sicherung vorher (D5), sofort beim Drücken (D6), Neustart
über die vorhandene Planung (D7), Abschnitt auf der Gesundheitsseite (D8),
Pi ohne Sonderfall, erster Lauf dort gemessen (D9).

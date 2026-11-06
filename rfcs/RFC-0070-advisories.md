# RFC-0070: Advisories — The Node Reads What Is Known About What It Runs

- **Status:** **Accepted** (2026-11-06, Jörg: D1–D8 as recommended — D7 "no, for
  now"). **Stage 1 built** (reference 0.1.226, `oaap.core.updates` 0.8 §2.8,
  `oaap.fleet.status` 0.7), measured on oaap-test, raspberrypi and oaap-demo (§10).
  Stages 2–4 not built.
- **Date:** 2026-11-05
- **Authors:** Claude (measurement, proposal), Jörg (requirement, decides)
- **Depends on:** `oaap.core.updates` 0.2 §2.6 (host care: the kernel pair, the auto-update
  verdict, the gateway's listeners), 0.3 §2.7 (the reboot plan, its urgency, the cases),
  RFC-0069 (D6: "advisories can only lower, later"), RFC-0061 (cases), RFC-0032 (events),
  RFC-0068 (closed egress — what it does and does not close), RFC-0043 (external names),
  `oaap.fleet.status` 0.6 (`host`)
- **Changes:** `oaap.core.updates` (a new §2.8: advisories), `oaap.fleet.status` (the
  `host` block), `oaap.core.host` (CLI), `oaap.core.tenant` 1.7 (one audit entry kind),
  later RFC-0069 §2.3 (urgency may be lowered by an advisory's rating)
- **Origin:** idea I-40, field 1 ("Eigener Knoten: Patchstand und Abgleich gegen
  Quellen"). RFC-0069 §8 left it out on purpose: "Reading advisories, the Security
  Tracker, OSV — own RFC."

## Summary

Stage 1 of I-40 measures the kernel pair and says whether automatic updates are *set up*.
RFC-0069 plans the reboot. Neither answers the question an operator actually asks after a
security announcement: **"Does this concern my node, and is it fixed here?"** Today the
answer comes from a person who reads the announcement, knows the package is installed,
and checks the version by hand — the way the CVE of 2026-11-05 was found, two days after
the fix was published.

This RFC makes the node answer that question itself, from two sources it already has or
can read: the list of what is installed (dpkg) and the distribution's own list of
security advisories (Debian's DSA list). The result is a **fact in the care state** —
"13 open advisories, the oldest since 2026-08-14 (util-linux)" — in the three places of
stage 1, a **case** when it stays open, and a **gate** for exposing a node. It does not
make the node act beyond what it already does; what it changes is that an open advisory
is *known*, with an age, instead of being assumed closed because a switch is on.

The measurement that shaped this RFC (§1) found exactly that gap on the first node it
ran on.

## 1. What the node knows today, and what it does not (measured 2026-11-05, `oaap-test`)

The probe: fetch Debian's DSA list (one text file, 1.24 MB, 2.6 s; 5967 entries since
2002, 608 of them with a line for `trixie`), parse `[trixie] - <source package> <fixed
version>`, read `dpkg-query -W` for the installed source packages (244), keep the newest
DSA per installed package (26), and compare with `dpkg --compare-versions`.

| Reading | `oaap-test`, 22:15 CET |
|---|---|
| Stage-1 line in `oaap status`, the portal, the fleet document | "Auto-updates: on, last run 2026-11-05 13:17 UTC" |
| Advisories with a fix for `trixie` for a package installed here | 26 |
| **Open** (installed version older than the fixed version) | **13**: apt (DSA-6607, 04 Nov), bind9 (21 Oct), brotli, ca-certificates, curl (14 Oct, 4 CVEs), expat (6 CVEs), libpng, openssl (30 Sep, 13 CVEs), pcre2, rsync (33 CVEs), util-linux (**14 Aug**), vim, xz-utils |
| `apt list --upgradable` from `trixie-security` | the same packages, candidate versions from `security.debian.org` |
| The unattended-upgrades log | only four entries, all of 2026-11-05, all `--dry-run` (our morning measurement); the log directory itself was created 09:41 that day |
| `apt-daily-upgrade.service` | ran daily for 450 ms and installed nothing: on 11-03 and 11-04 the program was not installed; on 11-05 the service ran at 06:05, the program arrived at 09:41 |
| `oaap-demo` (exposed, `projects.joomp.de`) | 195 packages upgradable from `trixie-security`; the same log picture |
| **The first real run**, started by hand on `oaap-test` at 22:36 CET (`unattended-upgrade -v`) | every pending package installed; the probe afterwards: **0 open**, 0 upgradable from the security origin; no reboot marker (the kernel was not among them) |

Three things follow, and they are the design:

1. **"On" is a setting; "open" is a fact.** The stage-1 line was true — program, switch
   and timer were in place — and useless: the node had carried the openssl fix of
   30 September unapplied for five weeks and said "on". The "last run" it showed was
   the stamp a *dry run* writes. The honest line is the one the probe computed, and it
   needs no network: `apt` already knows the candidate from the security origin.
   (`messen statt schließen`: a stored value holds earlier truth; a switch holds an
   intention.)
2. **The source is small and the comparison is local.** Debian's own DSA list is one
   file; the node's package database is on the node; `dpkg` compares versions. There is
   no need for a scanner, an agent, or an account anywhere. The full Security Tracker
   (JSON, every CVE, also the unfixed ones) and OSV (which converts Debian's advisories
   and offers a bulk download per ecosystem) are richer and larger; §2.2 says what they
   add and when.
3. **The kernel is named differently in the two lists.** The DSA says `linux
   6.12.69-1`; dpkg says the installed images come from `linux-signed-amd64 6.12.115+2`.
   A naive match would report the kernel as never advised. The mapping (`linux-signed-*`
   → `linux`, the `+N` of the signed build against the `-N` of the source) is a rule the
   reader must carry, and the kernel pair of 2.6.1 stays the authority for *reboot
   required*; the advisory only adds *what the fix was for*.

A fourth, smaller: the DSA list carries **no severity**. The CVE ratings (`unimportant`,
`low`, `medium`, `high`) live in the tracker's per-CVE data. That is why RFC-0069 D6's
"advisories can only lower" cannot be done from the DSA list alone (§2.4, D7).

## 2. The three things

### 2.1 The reading (D1, D2)

Every node reads **its own** installed packages and compares them with the
distribution's advisories. The fleet node does not do it for others: it cannot see their
package databases, and a reading taken elsewhere describes a different machine.

The source of truth is **Debian's DSA list** — the security team's own file, fetched over
HTTPS from Debian's own host, once a day and after each automatic-update run. It is
cached on the node (`/var/lib/oaap/apps/advisories.txt`, 0644: it is public data) with
the time it was read. From it the node computes, per installed source package, the newest
advisory for the node's suite, and whether the installed version is older than the fixed
one. Two more readings come for free and are recorded with it: what `apt` would install
from the security origin (the candidate), and the date of the advisory. The result is
the **advisory state**:

```
advisories:
  read_at:   2026-11-05T21:15:00Z        # when the list was last read
  source:    debian-dsa                   # which list
  stale:     false                        # read_at older than 2 days
  open:      13                           # installed < fixed
  oldest:    2026-08-14                   # the oldest open advisory's date
  items:     [{package, dsa, published, fixed, installed, cves}]   # server_admin's view
  unknown:   [linux-signed-amd64 …]       # installed from an origin the list does not cover
```

What "unknown" means: packages from a vendor or third-party archive (Docker CE from
`download.docker.com`, a Raspberry Pi kernel from `archive.raspberrypi.com`) have no
line in Debian's list. The node says so instead of counting them as clean.

**Stale is a state, not silence.** A node that cannot reach the source — no route, the
host down, a closed network — keeps the last list and says `stale: true` after two days.
RFC-0068 closes the egress of *instances*; the node itself reaches `deb.debian.org`
already, and `salsa.debian.org` is one more name of the same owner. A node that must not
reach it at all (a later air-gapped profile) gets the list from the fleet node — a later
stage, not this one.

### 2.2 What the richer sources add, and why not now

| Source | What it has that the DSA list has not | Cost | When |
|---|---|---|---|
| Debian Security Tracker, JSON export (`/tracker/data/json`) | every CVE per source package and suite, with `status`, `fixed_version`, `urgency`, and the unfixed ones | one large file (tens of MB), parsed per read | stage 4: the CVE ratings for D7, and "known, not yet fixed by Debian" as a fact of its own |
| OSV (`api.osv.dev`, `osv-vulnerabilities/Debian/all.zip`) | the same advisories in a schema shared with other ecosystems (PyPI, npm, Go, Alpine) — the format field 2 (images) and field 5 (the platform's own dependencies) will need | an API that needs the package name and version per query, or a bulk zip per ecosystem | field 2 / field 5, their own RFCs; the Debian advisories themselves are better read at their source |
| `debian-security-announce` (mail, RSS) | the text a person reads | a mail reader | never by the platform; a connector app may subscribe |

### 2.3 What is told, and the case (D4, D5)

No new channel (the rule of RFC-0069 §4). The advisory state is part of the care state of
2.6.2, so `oaap status`, the portal's care band and `/fleet/status` carry it:

```
Advisories: 13 open, the oldest since 2026-08-14 (util-linux) — list read 21:15 UTC
```

The fleet document carries **count, oldest date and `stale`**, not the package names: a
reader with a fleet key learns that a node is behind, not which door is open. The names
are the `server_admin`'s, on the node (`oaap node care advisories`) and in the portal's
node table.

**The case.** An open advisory becomes a **case** in the operator tenant's inbox (RFC-0061,
the inboxes of RFC-0069 §2.7.6) when it has been open longer than the node's grace:
**24 hours on an exposed node, 7 days otherwise** — the automatic-update run of the next
morning is the normal way an advisory closes, and a case for every advisory on the day it
appears would teach the operator to ignore cases. One case per node and advisory,
written on when the count changes, **closed by the node with proof** when the fix is
installed (the comparison says so), or by a person with a reason ("accepted: the package
is installed but the service is not used"), which holds until a newer advisory for the
same package arrives. The acknowledgement is the case; there is no second mechanism.

On a `broker` node the state is an **event** like the plan (RFC-0069 §2.7.8), kind
`advisory.open` / `advisory.closed`, retained, carrying count, oldest date and the
package names of the open ones — the operator's own tenant tree, not a public topic.

### 2.4 What the node does by itself (D3)

Nothing it does not do already — with one addition. Installing the fix is
`unattended-upgrades` (stage 1); rebooting for a kernel is RFC-0069. The addition: when
an advisory is open **and** the automatic-update run has not installed it within the
grace, the node runs the update **once**, now, and records that it did (`care.updates-run`
in the operator tenant's log). That is the same program the timer runs at night, started
a day early because the fact says it should have run. It is not a second mechanism.

**Urgency of the reboot plan** (RFC-0069 D6, "advisories can only lower, later"): not in
this RFC's first stages. The DSA list has no severity (§1, fourth point); the CVE ratings
come with the tracker's JSON (stage 4). Until then the plan's urgency stays what D6 said:
security origin and exposed = `critical`. D7 asks whether the lowering is wanted at all.

### 2.5 The gate (D6)

A node gets an **external name** (RFC-0043) or the `exposed` profile only when automatic
updates are set up (program, switch, timer) **and** a window is set (RFC-0069). Open
advisories do **not** block — a fix published an hour ago is open everywhere — but they
are **named** in the answer, with their age, so the person exposing the node reads them
before the node is reachable from the internet. `oaapx01` and `oaap-demo` are exposed
today and would have passed the gate; `oaap-demo`'s 195 pending packages would have been
on the screen.

## 3. Who may do what

| Act | Who | Why |
|---|---|---|
| Read the advisory state | every signed-in administrator of a tenant: count, oldest, stale; `server_admin`: the names | an open advisory on the node concerns every tenant on it; which package is the operator's |
| Read the list by hand (`oaap node care advisories --read`) | `server_admin` | the node reads it daily anyway |
| Close an advisory's case with a reason | `server_admin` | the acceptance of a risk is the operator's |
| Run the update early | the node itself, once per open advisory and grace; `server_admin` by hand | the program is already trusted to run nightly |

## 4. Security requirements (additions to `oaap.core.updates` §4)

1. The list is **data, not instructions**. The node parses it with a fixed grammar,
   executes nothing from it, and a line it cannot parse is skipped and counted, never
   taken as "no advisory".
2. The list MUST be read over HTTPS from the distribution's own host; a read that fails
   MUST leave the previous list and MUST set `stale` after two days; a failed read MUST
   NOT yield "0 open".
3. Versions MUST be compared with the package manager's own comparator
   (`dpkg --compare-versions`), never with a string or a number comparison.
4. Packages from an origin the list does not cover MUST be reported as `unknown`, never
   as clean.
5. The fleet document MUST NOT carry package names of open advisories; the node's own
   readers may.
6. The early update run MUST be the same program with the same configuration as the
   nightly one, MUST run at most once per advisory and grace, and MUST be recorded.
7. The "last run" of automatic updates MUST come from the timer's own stamp
   (`/var/lib/apt/periodic/upgrade-stamp`), not from the stamp the program writes on
   every invocation including a dry run (the stage-1 defect of §1). Until stage 1 of
   this RFC exists, that line SHOULD say "no run yet" when the timer's stamp is absent.

## 5. Stages

| Stage | Content | Measured on |
|---|---|---|
| **1** | Spec (`oaap.core.updates` 0.8 §2.8, fleet 0.7, host CLI); the reader with its cache; the advisory state in the care file and the three places; `unknown`; `stale`; the kernel mapping; the "last run" fix of §4.7 | `oaap-test` (13 open → 0 after the first real run — the probe of §1 already showed both numbers), `oaap-demo` (195 → 0), the Pi (`unknown` for the vendor kernel) |
| **2** | The case with grace, closed with proof or with a reason; the early update run | `oaap-test`: an advisory held open past the grace by pinning one package, the case, the run, the closing line |
| **3** | The gate for `exposed` / an external name | `oaap-test`: refused without a window, named with open advisories |
| **4** | The tracker's JSON: CVE ratings; "known, unfixed" as a fact; RFC-0069 D6 lowering if D7 says so | `oaap-test` |

Fields 2 (images), 3 (the gateway as the one door), 5 (the platform's own dependencies)
and 6 (accounts) of I-40 are not in these stages.

## 6. Not part of this RFC

- Scanning container images or app dependencies (I-40 field 2): a different source
  (SBOM per package, OSV), a different owner (the store, RFC-0050).
- Judging whether a vulnerable package is *reachable* in this node's configuration. The
  node says "installed and older than the fix"; "not affected here" is a person's
  sentence, recorded as the case's reason.
- Live-patching; a reboot order across the fleet; mail.
- Third-party archives (Docker CE): reported as `unknown`; reading their advisories is
  field 5.

## 7. Open questions, answered in words

**Why Debian's list and not OSV, which covers everything?** Because the node runs Debian
and Debian's list is the thing OSV converts. One file, one owner, one format the
distribution itself maintains; a converter in between is one more place to be wrong. OSV
is right for the fields that span ecosystems.

**Why does the node fetch the list itself when the fleet node could distribute it?** For
the same reason every node measures its own kernel: the node is the thing that must be
right about itself when the fleet node is down. The fleet relay is for nodes that must
not reach out at all, and none exists yet.

**Why a grace before the case, when the plan of RFC-0069 opens its case at once?** The
plan is a decision already made that people must know about; an open advisory is normal
for a few hours every day. A case per day teaches people to close cases unread.

## 8. Decisions (Jörg)

| # | Question | Recommendation |
|---|---|---|
| **D1** | Who measures: every node itself, from its own package database; the fleet node aggregates what the fleet document carries | yes — a reading taken elsewhere describes another machine |
| **D2** | Source of truth: Debian's DSA list, read daily from Debian's host, cached on the node; the tracker's JSON later for ratings; OSV for the other fields | yes — one file from the owner; the richer sources when a stage needs what they add |
| **D3** | What acts by itself: only the early run of the program that already runs nightly, once per open advisory and grace, recorded | yes — the fact "the fix has been available for a day" is exactly the trigger that was missing (I-40: "der fehlt nur der Auslöser") |
| **D4** | Telling: the care state in the three places; the fleet document with count, oldest and stale, without names; the event on a broker node | yes — no new channel, and no package names leave the node |
| **D5** | The case as acknowledgement: after 24 h (exposed) or 7 days, one per node and advisory, closed by proof or by a reason that holds until the next advisory | yes — one mechanism; the reason is the operator's record of an accepted risk |
| **D6** | The gate: an external name or `exposed` needs auto-updates set up and a window; open advisories are named, not blocking | yes — a node on the internet without a way to patch itself is the oaapx01 of August; a fresh advisory must not block an exposure that is otherwise right |
| **D7** | Lowering RFC-0069's `critical` by CVE ratings (stage 4) — wanted at all? | **no, for now** — the cost of being wrong is the node; "security origin and exposed" has been right every time it was measured; revisit when stage 4 shows the ratings on real kernels for a month |
| **D8** | Build stage 1 now, as the correction of the stage-1 line that said "on" over five open weeks | yes — the line misleads on all six nodes today; the reader is a day's work and needs nothing new on the nodes |

**On D8.** It is the one decision with a date. Tomorrow morning the timer installs what
the probe found (the program is in place since today), and the six nodes will say "on"
and be right. The line will be wrong again the next time a node is installed, or a
timer is off, or a repository is unreachable — and nothing in the platform will notice,
because the stage-1 line measures the switch and not the fact.

## 10. Stage 1 as built (2026-11-06)

**The first real timer run, before the build (06:23–07:00 CET).** On oaap-bernd,
raspberrypi and oaap-demo `apt-daily-upgrade` ran for the first time with the program
installed and installed 64, 18 and 384 packages; afterwards `apt list --upgradable`
showed 0 from the security archive on all three and on oaapx01 (which has run it since
August). No container was restarted. oaap-demo set the distribution's reboot marker
with an empty package list — a library, not the kernel; the kernel pair said no
reboot. Both are now said (§2.8.2 of the spec).

**What differs from §2 as written.**

- The list's headers vary over 24 years (`DSA-123` without a revision, no title,
  several packages, a double space); the grammar takes the first word as the package.
  On the real list 5 of 22 359 lines remain unknown and are counted (typos in the
  list itself).
- Besides `unknown` (another archive) there is `local` — a package no archive
  carries any more (oaap-demo: `docker-desktop`). Named, never compared.
- The kernel takes the **newest installed** version, not the oldest: the old images
  stay on disk and would otherwise be open forever.
- A fetched text whose first line is not an advisory header is refused (a captive
  portal, an error page); the previous list stays.
- §3 "every signed-in administrator of a tenant reads count, oldest, stale" is not in
  stage 1: the portal shows the care band to `server_admin` only, as 2.6.2 did.

**Measured.** oaap-test: 0 open, 4 uncovered (Docker CE), read in 3 s; the line in
`oaap status`, the portal's band and node table, and the fleet block say the same.
raspberrypi: 0 open, the Raspberry Pi archive's packages (kernel, glibc, chromium …)
`unknown`, 20 s on the Pi. oaap-demo: 0 open, 7 uncovered, 1 local. Counter-check on
oaap-test with the real list plus three invented entries: `bash 9.9-1` and `linux
6.12.200-1` open (the signed kernel mapped from the real package database),
`docker-ce 99.0` not compared and `unknown`; a page that is not the list → `open:
null`, never 0. Tests: `test_advisories.py` (46), `test_host_care.py`,
`test_care_portal.py`, `test_fleet_status.py` green.

## Deutsche Zusammenfassung

**Stand 06.11.:** Angenommen (D1–D8 wie empfohlen, D7 „nein, vorerst“); Stufe 1
gebaut (Referenz 0.1.226), auf oaap-test, raspberrypi und oaap-demo gemessen — überall
0 offen nach dem ersten echten Timer-Lauf heute früh; die Gegenprobe mit drei
erfundenen Meldungen schlägt richtig an. Abweichungen und Messwerte in §10.

**Der Befund.** Heute Abend hat eine Sonde auf oaap-test Debians eigene Liste der
Sicherheits-Advisories (eine Textdatei, 1,2 MB, 2,6 s) gegen die installierten Pakete
gehalten: **13 offene Advisories**, die älteste seit dem **14. August** (util-linux), dazu
openssl seit 30. September mit 13 CVEs. Die Zeile aus Stufe 1 sagte zur selben Zeit
„Auto-Updates: an, letzter Lauf 13:17 UTC“. Beides war wahr: Programm, Schalter und
Timer waren da — seit heute Morgen, erst da wurde unattended-upgrades installiert, und
der „letzte Lauf“ war der Stempel eines Probelaufs (dry-run). Der erste echte Lauf wäre
morgen früh gewesen. oaap-demo (exponiert) hat 195 Pakete aus dem Sicherheitsarchiv
offen. **„An“ ist eine Einstellung, „offen“ ist eine Tatsache** — und nur die Tatsache
hätte uns gewarnt.

**Der Vorschlag, drei Dinge.** Jeder Knoten **liest selbst**: einmal am Tag Debians
DSA-Liste von Debians Host, gespeichert auf dem Knoten, verglichen mit dpkg und dessen
eigenem Versionsvergleich. Ergebnis ist ein **Messwert im Pflegestand**: „13 offen, die
älteste seit 14.08.“ in `oaap status`, Portal und Flottendokument (dort nur Zahl, Datum
und „veraltet“, keine Paketnamen); Pakete aus fremden Archiven (Docker, Pi-Kernel)
heißen „unbekannt“, nie „sauber“; eine nicht erreichbare Quelle heißt „veraltet“, nie
„0 offen“. Bleibt ein Advisory länger offen als die Frist — **24 h auf exponierten
Knoten, sonst 7 Tage** —, wird es ein **Vorgang** beim Betreiber (RFC-0061), den der
Knoten mit Beweis schließt, wenn der Fix drin ist, oder ein Mensch mit Begründung; das
ist die Quittung, keine zweite Mechanik. Von selbst tut der Knoten nur eines mehr: Ist
ein Advisory über die Frist offen, startet er den nächtlichen Update-Lauf **einmal
vorzeitig** und schreibt es ins Log. Ein Knoten bekommt einen externen Namen nur mit
Auto-Updates und Fenster; offene Advisories werden dabei genannt, nicht verwehrt.

**Was es nicht tut.** Keine Abbilder (Feld 2), keine Plattform-Abhängigkeiten (Feld 5),
kein Urteil „betrifft uns hier nicht“ — das ist ein Satz eines Menschen, als Begründung
im Vorgang. Die Dringlichkeit von RFC-0069 wird **nicht** herabgestuft (D7: nein, vorerst),
weil die DSA-Liste keine Schwere kennt; die kommt erst mit dem JSON des Trackers
(Stufe 4).

**Deine Entscheidungen, D1–D8.** D1 jeder Knoten misst sich selbst (ja). D2 Quelle
Debians DSA-Liste, Tracker-JSON später, OSV für die anderen Felder (ja). D3 von selbst
nur der vorgezogene Update-Lauf (ja). D4 Mitteilen über Pflegestand, Flottendokument ohne
Namen, Ereignis auf Broker-Knoten (ja). D5 Vorgang nach Frist als Quittung (ja). D6 Tor
für externen Namen: Auto-Updates und Fenster Pflicht, Advisories genannt (ja). D7
Herabstufen der Dringlichkeit: **nein, vorerst**. D8 Stufe 1 jetzt bauen, als Korrektur
der Zeile, die fünf Wochen „an“ sagte (ja — die Zeile täuscht heute auf allen sechs
Knoten; morgen früh stimmt sie zufällig, beim nächsten Knoten ohne Timer wieder nicht).

**Die Zahlen von heute.** Die Sonde liegt in `program/messungen/advisories-sonde.py`.
Auf oaap-test habe ich den ersten echten Lauf von unattended-upgrades heute Abend um
22:36 selbst gestartet: alles eingespielt, danach **0 offen**, kein Neustart nötig. Die
anderen fünf Knoten holen das morgen früh mit dem Timer nach — wenn er läuft; genau das
würde Stufe 1 dieser RFC messen.

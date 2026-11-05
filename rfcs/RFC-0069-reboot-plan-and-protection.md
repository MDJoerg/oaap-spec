# RFC-0069: Reboot Plan and Protection — The Node Announces Its Reboot, an Instance May Hold It, Urgency Decides

- **Status:** Proposed (2026-11-05). D1–D5 decided by Jörg on 2026-11-05 (CURRENT_STATE
  387); D6–D11 open, recommendations below. Nothing built.
- **Date:** 2026-11-05
- **Authors:** Claude (measurement, proposal), Jörg (requirement, decides)
- **Depends on:** `oaap.core.updates` 0.2 §2.6 (host care — the measurement this stands
  on), RFC-0029 D5b (an exception needs a reason and an end), RFC-0042 (the tenant's
  place), RFC-0061 (cases), RFC-0032 (events), RFC-0043 (external names — what "exposed"
  means), `oaap.fleet.status` 0.5 (`host`), RFC-0038 (the minute job)
- **Changes:** `oaap.core.updates` (a new §2.7: plan, protection, urgency; the window
  moves from the distribution to the platform), `oaap.fleet.status` 0.6, `oaap.core.host`
  (CLI), `oaap.core.tenant` 1.7 (audit entries), `oaap.core.gateway` (one more
  `/platform/` door, inside the node only), `oaap.apps.runtime` (what an instance is told)
- **Origin:** idea I-40, stage 2. Stage 1 (host care, 0.1.220) is on all six nodes since
  2026-11-05.

## Summary

Stage 1 made a node say "reboot required" in three places and gave the operator a window
in which the node reboots itself. It also showed, on its first day, what the window
cannot do: the reboot of `oaap-demo` ended Jörg's desk session with its open
applications. A window is a time; it knows nothing about the work on the node.

This RFC gives the reboot a **plan** that is announced before it happens, a **protection**
an instance can hold against it for a stated reason and a stated time, and an **urgency**
that decides whether the protection holds — derived from facts the node already measures,
not chosen by hand. The honest limit stays what D5 said: a kernel reboot hits every
instance of the node. What this RFC adds is that nobody is surprised by it, and that a
reboot which can wait does wait.

## 1. What stage 1 does today, and where it stops (measured 2026-11-05)

- With a window set (`oaapx01`, `oaap-test`, 04:15), the **distribution's** mechanism
  reboots the node at that hour whenever its marker file exists; the measurement writes
  the marker when the kernel comparison says reboot. No announcement, no condition beyond
  the time. The first real run has not happened yet — no kernel has arrived since.
- The waiting kernel's **origin is readable** from the package manager: on `oaap-test` the
  running `6.12.115-2` lists `security.debian.org … trixie-security` at priority 500; a
  point-release kernel lists `deb.debian.org … trixie`, a Raspberry Pi kernel
  `archive.raspberrypi.com`. That is the one fact the urgency needs that stage 1 does not
  record yet.
- A node knows whether it has an **external name** (RFC-0043: `oaap external`, and the
  `names` block of the fleet document). That is the second fact.
- The platform has **no mail sender** and, outside the twin's relay (RFC-0032), nothing
  that publishes to the broker. It does have, per tenant, the **cases** door
  (`/platform/cases/submit`, RFC-0061 §3.2) and the choice of the inbox instance that
  takes a report (`cases_target`). It has the **tenant log** (1.7) and the **tenant's
  place** (RFC-0042), where every signed-in person of a tenant lands.
- The **minute job** (RFC-0038, `oaap-instance-watch.timer`) runs on every node and
  already re-measures the care state. It is the place where a plan can be evaluated every
  minute, which the distribution's once-a-night mechanism cannot.

The conclusion that shapes the design: **the distribution's reboot cannot know a
protection.** It fires on a marker file and a time. Either the platform owns the reboot,
or protections are decoration. So in stage 2 the platform owns it (§3, D7).

## 2. The three things

### 2.1 The plan

A **reboot plan** is the node's statement "I will reboot at *T*, because *R*, with urgency
*U*". It is computed by the node, from the measurement, and it is **the only way the node
reboots itself**:

- A plan comes into being when the measurement says `reboot_required` (§2.6.1 of the
  updates spec: running kernel differs from the newest installed of the same flavour) and
  the node has a window (D1). Without a window there is no plan, only the stage-1 line
  "a new kernel waits for a manual reboot".
- *T* is a window hour on a day the rules of §2.3 allow, **at least 24 h after the plan
  was first announced** (D11) — a person who reads the band in the morning must not be
  hit that night. The first announcement is the minute the plan is computed.
- The plan is **recomputed every minute** and may move later (a protection arrived, a
  care reboot) or earlier (`server_admin` shortened it, §2.3). Every move is announced
  again. It never moves to before "now plus the lead time" except by a `server_admin`'s
  explicit hand (§5).
- At *T* the node **measures again**, and reboots only if the reboot is still required
  and the rules of §2.3 still allow it. A plan is a prediction; the reboot is an act on
  fresh facts.
- After the reboot the first measurement closes the plan with the proof: "running
  6.12.115, newest installed". The announcement that opened it gets that closing line.

A `server_admin` may also **make a plan by hand**, with a reason, when no kernel waits
(D10): `oaap node care reboot at <time> --reason "…"`. The glibc update of 2026-11-05 is
the case — not a kernel, so the comparison does not see it, but the operator does. The
hand-made plan goes through the same announcement and the same protection rules as a
computed one (urgency `care` unless the operator says `--critical`), and it is how the
whole mechanism can be measured on `oaap-test` before a kernel arrives.

### 2.2 The protection (D2)

An instance may be **protected** against a planned reboot. Built like the backup
exclusion of RFC-0029 D5b, with the same three conditions, none optional:

1. **A reason**, in the words of the person who sets it, shown wherever the protection is
   shown. Without a reason the command is refused.
2. **An end.** A protection expires; the default is 7 days, the maximum 30. Extending it
   is the same command again with a reason again. There is no protection "until further
   notice": a kernel fix that waits for a protection which nobody remembers is the
   `oaapx01` of 2026-08-26 with a better excuse.
3. **It is visible to everybody it concerns**: in the tenant's log (1.7), on the
   instance's page in the portal, in the node's care state ("reboot held by `joerg-desk`
   until 12.11., reason: …"), and in the fleet document.

Who sets it: a `tenant_admin` of the instance's tenant, or `server_admin`. The platform
has no "owner of an instance" as a role — `created_by` is a record, not a right — so the
tenant's administrator is the nearest responsible person (D8). A protection is **per
instance**, not per tenant: the thing that must not be interrupted is a running desk, not
a customer.

What a protection does: it moves a `care` plan (§2.3) to the first window after the
last protection on the node ends. What it does not do: hold a `critical` plan. A
protection on a critical plan is **shown** (the person must learn that it did not hold),
and the plan says why.

### 2.3 The urgency (D3)

Two levels, **derived from the measurement**, never typed in:

| Urgency | When | What the plan does |
|---|---|---|
| **`care`** | the waiting kernel did not come from the distribution's security origin (a point release, a vendor kernel), **or** the node is not exposed | waits for the first window with no live protection; tells everyone it is waiting and for whom |
| **`critical`** | the waiting kernel came from the **security origin** **and** the node is **exposed** — it has an external name (RFC-0043), or its gateway listeners negotiate MPTCP (`gateway_mptcp: on`) | the first window at least 24 h after announcement; protections are shown and overridden; `server_admin` may shorten down to "now" |

This is deliberately coarser than D3's words "publicly exploitable from the remote": the
node cannot read an advisory yet, and the security origin is the fact it *can* read.
Every security kernel on an exposed node is treated as if it were the one of 2026-11-05
(D6). The refinement — matching the installed version against the Debian Security
Tracker's `fixed_version` and urgency per CVE — is I-40 field 1, a later RFC, and it can
only ever lower a `critical` to `care` when the advisory says "local only", never raise
one the origin did not already flag. Until then, being wrong in this direction costs a
desk session once a quarter; being wrong in the other costs the node.

A `care` plan that a protection has held for more than **7 days** becomes an attention
of its own (`reboot_deferred`, §4): a protection may be legitimate, but somebody has to
look at a fix that has waited a week.

## 3. The window moves to the platform (D7)

Stage 1 wrote `Unattended-Upgrade::Automatic-Reboot "true"` and `-Time` into
`52oaap-care`. Stage 2 writes `Automatic-Reboot "false"` **always** and keeps the window
in the care file as the platform's own setting. The minute job evaluates the plan; at *T*
it is the minute job that runs the reboot. The marker file is no longer written by the
measurement (its only purpose was to make the distribution's mechanism fire), only read
as the hint it always was.

Consequences, said plainly:

- `oaapx01` and `oaap-test` currently carry a stage-1 window. Until stage 2 is rolled to
  them, a security kernel arriving tomorrow reboots them at 04:15 **without announcement
  and without protection** — the stage-1 behaviour Jörg set with his word. Stage 2's
  update rewrites the file; the window value is kept.
- The reboot command is `systemctl reboot`, run by the minute job as root, after a last
  measurement and after writing the "rebooting now" line to the announcement. No backup
  is taken by the plan: D1 put the window after the backup on purpose, and the backup
  timer is a setting of its own.
- A node whose minute job is not running cannot reboot itself. That is already an
  attention (the stage-1 "measurement is N days old" line) and now also means "the plan
  is not being evaluated". The fleet document shows the plan's `at` next to `measured`;
  a watcher sees a plan whose time has passed.

## 4. What everyone is told (D4)

No new channel. The ways that exist, each with the part it can carry:

| Who | Way | What |
|---|---|---|
| the operator | a **case** in the operator tenant's inbox (RFC-0061; the tenant that holds the node's `vorgaenge` instance, on `oaapx01` and `oaap-demo` the `mgmt`/`hbvp` kind of tenant), one per plan, updated on every move, closed with the proof | time, urgency, reason, protections overridden |
| the operator, across the fleet | `oaap.fleet.status` 0.6: `host.reboot_plan` (`at`, `urgency`, `reason`), `host.protections` (count and the latest end), attention kinds `reboot_planned` (informational, `info`) and `reboot_deferred` (`warn`) | the view that was missing on 2026-11-05, one step further |
| every tenant on the node | a **band on the tenant's place** (RFC-0042) for every signed-in person: "Dieser Knoten startet am … um … neu (Pflege / kritisch)"; a **case** in that tenant's own inbox when it has one; a **tenant log** entry (1.7) always | time, urgency; the reason only in the operator's words where the operator wrote one |
| the protection's setter | the same band names their protection and whether it holds | "gehalten bis 12.11." or "überstimmt: kritisch" |
| the instance itself | one door **inside the node only**: `/platform/care.json` on the instance's own site, answered by the gateway only to callers from the node's own networks (the shape of `OAAP_CASES_URL`, told as `OAAP_CARE_URL`) | `{"reboot_at": …, "urgency": …, "held": true/false}` — no kernel versions, no reasons: an app sees when, not why |
| a broker node | an event on the operator tenant's tree, `oaap/<operator tenant>/node/<hostname>`, the shape of RFC-0032; only where the `broker` profile runs; the relay is the twin's and is not extended for this — the minute job publishes with the platform principal | the same five fields as the case |

The desk (`webtop`) is the first reader of `/platform/care.json`: it shows the time in
the session and can save the session before it. That is the app's part, and the
boundary of this RFC: the platform says when; what an app does with the hour is the
app's. **Mail, Telegram, ntfy are not in the platform** (§1); they are a connector app
reading the case or the event, later, and this RFC does not wait for them.

## 5. Who may do what

| Act | Who | Why |
|---|---|---|
| Set a window, remove it | `server_admin` | the node is the operator's |
| Protect an instance, extend, release | `tenant_admin` of its tenant, `server_admin` — with a reason and an end | the work that must not be interrupted is theirs |
| Shorten a `critical` plan, down to now | `server_admin` — with a reason, logged in every tenant's log on the node | the one person who may trade every tenant's session for the node |
| Make a plan by hand, cancel one | `server_admin` — with a reason | the glibc case; cancelling tells everyone, and the computed plan returns the next minute if the kernel still waits |
| Read plan and protections | every signed-in person of a tenant for their place; `server_admin` for the node; a fleet key for the document | a plan nobody can read is a surprise with a timestamp |

An app cannot ask for a protection in its manifest, and a protection is never set by
the platform on an app's behalf. It is a person's statement about a person's work.

## 6. Security requirements (additions to `oaap.core.updates` §4)

1. The node MUST NOT reboot itself without a measurement taken in the same minute that
   says the reboot is still required (or a hand-made plan by `server_admin`).
2. A protection MUST carry a reason and an end, MUST NOT exceed the maximum, and MUST be
   written to the tenant log of the instance's tenant.
3. A `critical` plan MUST NOT be held by a protection; the override MUST be shown to the
   protection's setter and recorded.
4. Urgency MUST be derived from recorded facts (origin of the waiting kernel, exposure);
   no command sets it, except `server_admin`'s hand-made plan, which is logged as such.
5. `/platform/care.json` MUST NOT be reachable from outside the node and MUST NOT carry
   kernel versions or reasons.
6. The distribution's own automatic reboot MUST be off on a stage-2 node; two reboot
   mechanisms on one machine are two truths (the lesson of "zwei Orte, ein Schalter").
7. A plan whose time has passed without a reboot MUST be visible as such (the fleet
   document, the care state), never silently rescheduled.

## 7. Stages

| Stage | Content | Measured on |
|---|---|---|
| **1** | Spec (§2.7 of the updates spec, host 0.3.8, fleet 0.6, tenant 1.7 entries); the plan in the care file; the protection with reason and end (`oaap instance protect <inst> --until <date> --reason "…"` / `release`); urgency from origin and exposure; the window owned by the minute job; `reboot at` / `cancel` by hand; the three stage-1 readers extended; the tenant-place band | `oaap-test`: a hand-made plan with a real reboot of the node; a protection that holds a `care` plan and is overridden by a `critical` one (urgency forced only through the test's fake measurement, never by a command) |
| **2** | Cases: one per plan in the operator tenant's inbox and in every tenant's inbox that has one; the closing line after the reboot | `oaap-test` with an inbox instance; `oaapx01` only on Jörg's word |
| **3** | `/platform/care.json` inside the node, `OAAP_CARE_URL`; the desk reads it (an `oaap-apps` change to `webtop`) | `oaap-test`, then `oaap-demo` with `joerg-desk` on Jörg's word — the first real user of D2 |
| **4** | The broker event on `broker` nodes | `oaap-test` |

Advisory matching (I-40 field 1), the first measurement of a *computed* reboot on a
real kernel (whenever the next one arrives, on `oaap-test`), and any outside channel are
not in these stages.

## 8. Not part of this RFC

- Reading advisories, the Security Tracker, OSV (I-40 field 1, own RFC).
- Live-patching; Debian has none, a kernel fix is a reboot.
- Restarting services instead of the node for library updates (`needrestart`); noted as
  the next step after the hand-made plan has shown what the operator does by hand.
- A reboot *order* across the fleet (two nodes never at once). The windows are the
  operator's per node (D1); a fleet rule is a later statement on the fleet document.
- Saving an instance's state before a reboot. D5: that is the instance's job, or the
  instance needs a node of its own.

## 9. Decisions (Jörg)

D1–D5 are decided (2026-11-05, CURRENT_STATE 387) and this RFC builds on them. Open:

| # | Question | Recommendation |
|---|---|---|
| **D6** | Urgency without advisories: security origin **and** exposed (external name or MPTCP on) = `critical`; everything else `care`; advisories can only lower, later | yes — the node can read the origin today, the advisory later; wrong in this direction costs a session, not the node |
| **D7** | The window moves to the platform: `Automatic-Reboot` off, the minute job plans and reboots | yes — the only way a protection can hold; one mechanism, one truth |
| **D8** | Protection by `tenant_admin` or `server_admin`, reason and end, default 7 days, maximum 30, extension restates the reason; per instance | yes — the shape of D5b, which has held since 0.1.112 |
| **D9** | Telling: case, band, tenant log, `/platform/care.json`, broker event where a broker is; no mail/Telegram in the platform | yes — a connector app can read the case; the platform should not grow a mail sender for this |
| **D10** | `server_admin` may plan a reboot by hand with a reason when no kernel waits | yes — the glibc case, and the only way to measure the mechanism before the next kernel |
| **D11** | 24 h lead time for both urgencies; `critical` overrides protections; `server_admin` may shorten a `critical` plan down to now | yes — D3 said 24 h for critical; one number is easier to promise than two |

**On D6.** It is the decision with a wrong-way cost on both sides. Without it, every
security kernel on an exposed node waits for the last protection, and the one that
matters waits with them. With it, a desk on an exposed node loses a session for a kernel
fix that might have been local-only. `oaap-demo` is exposed (projects.joomp.de) and has
the desk; `oaap-demo` has no window today, and that is the operator's lever until the
advisory step exists: no window, no plan, the stage-1 line in `oaap status` and the fleet
document say the kernel waits.

## Deutsche Zusammenfassung

**Der Befund.** Stufe 1 (0.1.220, seit heute auf allen sechs Knoten) sagt an drei Orten
„Neustart nötig“ und startet den Knoten im Fenster selbst neu. Am ersten Tag hat sie
auch gezeigt, was ein Fenster nicht kann: Der Neustart von oaap-demo hat Deine
Desk-Sitzung mit offenen Anwendungen beendet. Ein Fenster ist eine Uhrzeit, es weiß
nichts von der Arbeit auf dem Knoten. Und der Mechanismus der Distribution kann einen
Schutz nie kennen — er feuert auf eine Markierungsdatei und eine Uhrzeit.

**Der Vorschlag, drei Dinge.** Ein **Plan**: Der Knoten sagt „ich starte am … um … neu,
weil …, Dringlichkeit …“, mindestens 24 Stunden vorher, rechnet ihn jede Minute neu und
misst am Termin noch einmal, bevor er neu startet. Ein **Schutz** je Instanz, gebaut wie
die Backup-Ausnahme: mit Begründung und Ablaufdatum (Standard 7 Tage, höchstens 30),
gesetzt vom Mandanten-Admin oder Server-Admin, sichtbar im Mandanten-Log, im Portal, im
Pflegestand, in der Flotte. Eine **Dringlichkeit** aus Messwerten, nicht von Hand:
**Pflege** wartet auf das erste Fenster ohne Schutz; **kritisch** (der wartende Kernel
kommt aus der Security-Quelle **und** der Knoten ist exponiert — externer Name oder
MPTCP an) überstimmt den Schutz nach 24 Stunden Vorlauf, der Server-Admin darf bis
„jetzt“ verkürzen. Das Fenster wandert dafür von unattended-upgrades in den Minutenlauf
der Plattform. Mitgeteilt wird über die Wege, die es gibt: Vorgang beim Betreiber und bei
jedem Mandanten mit Postkasten, Band am Mandantenort für jeden Angemeldeten,
Mandanten-Log, Flottenstatus, eine Tür `/platform/care.json` nur innerhalb des Knotens,
aus der der Desk die Uhrzeit liest, und auf Broker-Knoten ein Ereignis. Keine Mail in
der Plattform — das ist später eine Konnektor-App. Der Server-Admin darf außerdem einen
Neustart **von Hand planen** (glibc-Fall), mit demselben Vorlauf und denselben Regeln —
und so lässt sich der Mechanismus auf oaap-test messen, bevor der nächste Kernel kommt.

**Was heute gilt, bis Stufe 2 steht:** oaapx01 und oaap-test starten bei einem neuen
Kernel um 04:15 ohne Ankündigung und ohne Schutz neu (Stufe 1, Dein Wort). oaap-demo hat
kein Fenster, der Desk ist bis dahin dadurch geschützt.

**Deine Entscheidungen, D6–D11 (Empfehlung jeweils ja).** D6 Dringlichkeit ohne
Advisory: Security-Quelle und exponiert = kritisch, Advisory-Abgleich später und nur zum
Herabstufen. D7 Fenster in die Plattform, Distribution-Neustart aus. D8 Schutz durch
Mandanten-Admin oder Server-Admin, Begründung und Ende, 7/30 Tage, je Instanz. D9
Mitteilen über Vorgang, Band, Log, care.json, Broker — keine Mail in der Plattform. D10
Neustart von Hand planen mit Begründung. D11 24 Stunden Vorlauf für beide Stufen,
kritisch überstimmt den Schutz, Verkürzen nur Server-Admin. D6 ist die heikle: Falsch in
die eine Richtung kostet eine Desk-Sitzung, falsch in die andere den Knoten.

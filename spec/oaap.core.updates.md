# oaap.core.updates — Platform Updates

- **ID:** `oaap.core.updates`
- **Version:** 0.14 (**the portal's section „Updates“** on the health page -- server_admin at the node's own address only: the waiting packages by kind, a tick for Docker, „Jetzt einspielen“ as a spool order `upgrade` that starts the very run of 2.12, the running unit's log and the last result, §2.13; RFC-0139 stage 3, reference 0.1.394). 0.13 (**installing on the administrator's word** -- `oaap node care upgrade [--docker]`: backup first, apt in its own unit `oaap-upgrade`, only upgrades and never a removal, a check that every container runs again, audit and the notification `host.upgraded`, §2.12; RFC-0139 stage 2, reference 0.1.393). 0.12 (**the packages that wait** -- host care counts what `apt list --upgradable` offers (waiting, of them security, Docker, other; Docker by package name), a line in `oaap status` and on the health page, the daily matter `host.updates`, a line in the weekly report, and `oaap node care upgrade --dry-run` naming the packages; nothing is installed beyond what unattended-upgrades does, §2.11; RFC-0139 stage 1, reference 0.1.392). 0.11 (**freeing disk space** -- a care measure that removes images the node no longer needs, in classes: build cache, older versions of an image it built, images without an instance after seven days; foreign images only by a person one by one; data never; nightly after the backup, on disk pressure before the mail, by hand in the portal and with `oaap node care space`; journald capped at 2 GB, 2.10; RFC-0128, reference 0.1.387). 0.10 (the node door of a cases inbox also carries a tenant's **request to the operator** -- `object: request`, `from` naming tenant and person -- and answers `op: read` with state and replies, never an internal entry, 2.7.6, `oaap.core.tenant` 1.14, RFC-0109 §13; reference vorgaenge 0.12.0). 0.9
- **Maturity:** draft — accepted by Jörg 2026-08-06 (CLI trigger
  implemented and validated on real hardware); 0.1.1 (2026-08-07)
  updates the reserved portal-trigger role to `server_admin` per
  RFC-0008; 0.1.2 (2026-08-09) adds the reconcile step for shipped
  store sources, per RFC-0012 §4; 0.1.3 (2026-08-09) states where
  consistency steps must live and when they must run — the engine
  replaces itself while running, so a step written into it is skipped
  by the very update that introduces it (found on oaap-demo); **0.2
  (2026-11-05, Jörg's decision after CVE-2026-98432) adds §2.6 host
  care**: the operating system under the platform is measured and the
  node says what to do — reboot required, automatic updates, the
  gateway's listeners — in `oaap status`, the portal and the fleet
  document; and two node settings the platform writes itself;
  **0.3 (2026-11-05, RFC-0069) adds §2.7**: the node plans its
  reboot and announces it 24 h ahead, an instance may hold a `care`
  reboot with a reason and an end, urgency from the waiting kernel's
  origin and the node's exposure overrides it; the window moves from
  the distribution to the platform's minute job; **0.4 (2026-11-05,
  RFC-0069 stage 2) adds §2.7.6**: the plan is a case in every inbox
  on the node, opened with the announcement, written on at every move,
  closed with the proof; **0.5 (2026-11-05, RFC-0069 stage 3) adds
  §2.7.7**: the door an instance reads — when and how urgent, never
  which kernel or why; **0.6 (2026-11-05, RFC-0069 stage 4) adds §2.7.8**:
  the plan is an event on a broker node; **0.7 (2026-11-05, RFC-0069
  stage 5) adds the portal's door to 2.7.2**: a `tenant_admin` protects,
  extends and releases on the instance's page, one function behind both
  doors; **0.8 (2026-11-06, RFC-0070 stage 1, Jörg's decisions D1–D8)
  adds §2.8**: the node compares its installed packages with the
  distribution's advisory list and says how many are open and since
  when — `unknown` for other archives, `stale` for an old list, never
  "0 open" without a list; the "last run" comes from the timer's stamp;
  **0.9 (2026-11-06, RFC-0071 stage 1, D1–D9) adds §2.9**: the same
  comparison inside every image the instances run, the upstream digest
  of every base, one word per instance — read, not rebuilt
- **Based on:** RFC-0001 (capability model); program decision 2026-08-03
  ("one update engine per node, three triggers"); git-based delivery;
  RFC-0012 §4 (shipped sources survive a move)
  (program backlog); trust principle of `oaap.apps.runtime` 2.5
  ("a request can never supply a source")

## 1. Purpose

Keeps the platform core of a node up to date without manual file
surgery. With a growing fleet (four nodes as of 2026-08-06), manual
copy procedures drift installations apart and burn operator time; a
conformant node updates itself from its **recorded platform source**
with one action, shows what would change before it changes it, and
never touches app instances or user data in the process.

Out of scope for 0.1: updating apps (that is the store/deploy path of
`oaap.apps.runtime`), operating-system updates (recommendation:
`unattended-upgrades`), and multi-node orchestration (future fleet
capability; this spec is the per-node engine it will call). Since 0.2
the operating system is no longer a recommendation in a parenthesis:
§2.6 measures its care state and lets the platform write the two
settings that make the recommendation true.

## 2. Interface

### 2.1 One engine, three triggers

Every node runs ONE update engine. It can be invoked by three
triggers; 0.1 implements the CLI, the others are reserved:

1. **CLI** — `oaap update` (technicians, service partners, and the
   rescue path when the portal is broken). Implemented in 0.1.
2. **Portal** — a button for administrators (the everyday path).
   Reserved; will reuse the host-task channel (spool + worker).
3. **Schedule** — automatic updates, primarily security fixes.
   Reserved; requires update channels/severity metadata first.

### 2.2 Recorded platform source

- The platform records **where it came from** at install time (git
  repository URL, optionally branch/ref, and the local working copy
  path). An update always means: **fetch the recorded source again**.
  Neither the CLI nor any later trigger accepts a different source as
  a parameter — changing the source is a deliberate, separate
  administrative act (edit the recorded configuration).
- Installations without a git working copy (e.g. install-medium
  payloads) clone the recorded repository URL into a platform-owned
  location on first update and continue from there.

### 2.3 Behaviour

- `oaap update --check` (and as the first phase of every run): fetch,
  then report current version/revision, available version/revision,
  and a short change log. No changes to the system.
- `oaap update`: apply — update the working copy (fast-forward only),
  copy the platform files into the installation, rebuild the core
  service images, restart core services, then verify that the core
  services report healthy. The applied revision is recorded.
- **No-op guarantee:** when the node is already at the available
  revision, the engine installs no code, rebuilds no image and restarts
  no container, and says so. It does still run the consistency steps
  below — those are about the node, not about the code.
- **Consistency steps MUST come from the version being installed, and
  MUST run on every trigger.** An update engine is the one program that
  replaces itself while running: everything after the copy step is still
  the *old* engine. A migration or repair written into the engine is
  therefore skipped by exactly the update that introduces it — and,
  because the next run finds nothing to install, skipped forever after.
  Two rules follow, and both are load-bearing:
  1. The steps live **outside** the engine, in an artefact the engine
     invokes **from the installed location** after copying, so the new
     version's steps run.
  2. They run **also when nothing is installed** — that, and only that,
     heals a node that already missed one.
  Every step MUST be idempotent and silent when there is nothing to do,
  and a failing step MUST NOT abort the run: it is reported and the
  update stands. *(Found on oaap-demo, 2026-08-09, which jumped eight
  versions in one go and received neither the store-source migration nor
  a unit repair. Both had been written, tested and shipped; the node
  simply never ran them, and nothing said so — the worst shape a defect
  can take.)*
- **An update reconciles the node's shipped store sources**
  (`oaap.apps.runtime` 2.9, RFC-0012 §4) and reports what it did. This
  is the one piece of node *state* an update touches, and it exists for
  a specific failure: a source used to be written once, at installation,
  and never looked at again, so the day one of our lists moved, every
  node in the field stranded — visibly only as an empty store. What the
  operator changed is never overwritten; the difference is reported
  instead.
- **Failure behaviour:** if the image build fails, the previously
  running containers keep running (build before switch); the engine
  reports the failure and leaves the system on the old version.
  Rollback in 0.1 is documented-manual (check out the previous
  recorded revision and re-apply); automatic rollback / A/B is a
  later increment.
- Every run writes a transcript (`/var/log/oaap-update.log` in the
  reference) and is idempotent.

### 2.6 Host care: the operating system under the platform (0.2)

**Why this is here.** On 2026-11-05 a kernel fix for a remotely
exploitable fault (CVE-2026-98432, reachable through exactly the kind
of listener our gateway had become) was measured across the fleet. The
fix had been *installed* on the internet node for two days and was
*not running*, because nobody had rebooted it in ten weeks; four nodes
had no automatic updates at all; on one node the auto-update package
was installed by hand and did nothing, because the periodic switch the
package is supposed to set was missing. Every one of these was a fact
on the machine, and the platform said nothing. 0.1 wrote "recommendation:
unattended-upgrades" and left the rest to the operator; 0.2 makes the
node measure it and say what to do.

What 2.6 is **not** (later stages of the same programme idea, each
its own RFC): matching installed packages against security advisories,
a notification channel, a reboot *protection* per instance and urgency
levels that may override it (the Jörg decisions D1–D5 of 2026-11-05
describe them). 2.6 is the measurement they will all stand on.

#### 2.6.1 The measurement

Every node measures its own **care state** — on the machine, with
administrator rights, never from inside a container (the portal cannot
read the package database, and must not be able to). The measurement
is a small set of facts, each with the rule that produces it:

- **Running kernel** and **newest installed kernel of the same
  flavour**. The flavour is the suffix behind the version (`-amd64`,
  `+rpt-rpi-v8`); a machine may hold several, and a newer kernel of a
  *different* flavour is not an update for this one.
- **Reboot required** = the two differ. **By comparison, never by the
  distribution's marker file.** The marker (`/var/run/reboot-required`)
  is written by a hook that ships *with the auto-update package*; on a
  node without that package the marker never appears, and "no marker"
  then reads as "no reboot needed" while a newer kernel waits on disk
  (oaapx02, 2026-11-05). The marker MAY be shown as a hint; it MUST NOT
  be the verdict.
- **Automatic updates**, one verdict from **three** parts, each named
  in the detail when it fails: the distribution's auto-update program
  is installed; its periodic switch is set (the package does **not**
  guarantee this — it writes the switch only when a pre-seeded answer
  says so, see 2.6.3); its timer is active. `ok` needs all three,
  `warn` is installed-but-not-running, `error` is not installed.
  Plus the time of the last run, when there was one.
- **Reboot window** — `off`, or the local hour the node reboots itself
  after a kernel update (2.6.3).
- **Gateway listeners** — whether the gateway's public listeners
  negotiate Multipath TCP, read from the gateway's own network
  namespace (`oaap.core.gateway` 0.2.18 says they must not; on the day
  of the CVE they did, by a language default nobody had chosen).
- **The time of the measurement.** A fact without its time is a
  trap: a status read right after a reboot describes the old kernel.

The node keeps the latest measurement in one file beside the registry
(`host-care.json` in the reference). It is refreshed by the node's
minute job when older than ten minutes, by every update run (the file
must exist the moment a node can show it), and on demand. A fresh
measurement right after a reboot is what closes the loop: "running
6.12.115" is the proof the reboot was the right advice.

#### 2.6.2 Three places, one measurement

The same file feeds three readers; none measures on its own, so they
can never disagree:

1. **`oaap status`** prints the care state as its own block — one line
   each for the kernel, for automatic updates, for the gateway —
   **with the recommendation as text** on every line that is not fine:
   "reboot required — running 6.12.111, installed 6.12.115: `sudo
   systemctl reboot` in a quiet hour". A technician must not have to
   know the package manager to read the line. When the measurement is
   missing or older than a day, the block says so instead of guessing.
2. **The portal** shows a `server_admin` a band with the same lines on
   the app overview and on the health page, and the health page's node
   table carries the facts. Only `server_admin`: the machine is the
   operator's, and a tenant administrator can do nothing about a
   kernel (telling tenants about a planned reboot is D4 of the later
   RFC, not this).
3. **`/fleet/status`** carries the facts as the `host` block and the
   three attention kinds (`oaap.fleet.status` 0.5), so the operator's
   inner node sees "needs a reboot" across the whole fleet without a
   login — the view that was missing on 2026-11-05.

#### 2.6.3 Two settings the platform writes

Hand-editing the same two things on every node is how a fleet drifts;
the platform writes them, in **a file of its own** that the package
manager reads beside its defaults, never by editing the distribution's
files:

- **`oaap node care auto-updates on`** installs the distribution's
  auto-update program **and writes the periodic switch itself**
  (reference: `/etc/apt/apt.conf.d/52oaap-care`, with the pre-seeded
  answer set first so the package's own file appears too). It changes
  **no origins**: the distribution's security origin is what gets
  installed automatically, and nothing else — a vendor kernel origin
  (Raspberry Pi) stays out unless the operator adds it by hand, because
  it brings firmware jumps with it (Jörg's decision, 2026-11-05). The
  installer runs this on every new node; an updated node is *told* in
  the care state when it is missing and is not switched on behind the
  operator's back.
- **`oaap node care reboot-window HH:MM | off`** — with a window set,
  the node reboots itself at that local hour **when, and only when, a
  newer kernel is installed than the one running** (the distribution's
  own mechanism, `Automatic-Reboot` with `Automatic-Reboot-Time`; also
  with users logged in, since a node is headless and an operator's
  idle shell must not keep a security fix from running). **Off by
  default**: when a node reboots is the operator's decision per node
  (after the backup, D1), and the settings file says in a comment who
  wrote it and why. The window is shown in all three places of 2.6.2.
  One more thing the window needs, learned on oaapx02: the
  distribution's mechanism reboots only when its **marker file** exists,
  and the marker is written by a hook that runs when *the auto-update
  program* installs a kernel — a kernel installed before the switch was
  set never gets one. So with a window set, the measurement **writes
  the marker itself** whenever the comparison of 2.6.1 says the reboot
  is required. That is the only system file the measurement touches,
  and only with a window set.

Both commands require local administrator rights, are idempotent, and
re-measure when done, so the status answers the change at once.

### 2.7 Reboot plan, protection and urgency (0.3, RFC-0069)

**Why this is here.** 2.6 gave the node a window and the window did
what a window does: on its first day the reboot of a node ended a
person's desk session with its open applications (oaap-demo,
2026-11-05). A window is a time; it knows nothing of the work on the
node. And the distribution's own mechanism, which 2.6.3 used, can never
know it either — it fires on a marker file and a clock. So in 0.3 the
platform owns the reboot: it plans it, says so ahead, lets an instance
hold a reboot that can wait, and derives from facts whether this one
can.

#### 2.7.1 The plan

A **reboot plan** is the node's statement "I will reboot at *T*,
because *R*, with urgency *U*", and it is **the only way the node
reboots itself**.

- A plan comes into being when the measurement of 2.6.1 says
  `reboot_required` **and** the node has a window (2.6.3). Without a
  window there is no plan, only the line "a new kernel waits for a
  manual reboot".
- *T* is the window hour on the first day the rules of 2.7.3 allow,
  **at least 24 h after the plan was first announced**. The first
  announcement is the minute the plan is computed; the announcement
  time is kept with the plan and does not move while the same kernel
  waits, so a plan that is moved later never gains a shorter lead.
- The plan is **recomputed every minute** by the node's minute job,
  from the latest measurement, the live protections and the stored
  plan. It may move later (a protection arrived) or earlier (a
  `server_admin`'s hand, 2.7.4). Every move is announced again.
- At *T* the node **measures again** and reboots only when the reboot
  is still required and the rules of 2.7.3 still allow it. A plan is
  a prediction; the reboot is an act on fresh facts. The minute job
  carries it out within a short grace after *T*; a plan whose time
  passed without a reboot (the minute job was not running) MUST be
  shown as **overdue** in every reader, never silently rescheduled.
- The first measurement after the reboot **closes** the plan with the
  proof — "running 6.12.115, newest installed" — and that closing is
  announced the same way the opening was.

A `server_admin` MAY **make a plan by hand** when no kernel waits
(`oaap node care reboot at <time> --reason "…"`, `oaap.core.host`
2.3): a library update the comparison cannot see, a disk that needs a
cold start. A hand-made plan carries its reason and its maker, goes
through the same announcement and the same protection rules, has
urgency `care` unless the maker says `--critical`, and is the way the
whole mechanism is measured on a test node before a kernel arrives. A
hand-made plan MAY be sooner than 24 h: that is the `server_admin`'s
explicit act of 2.7.4, and it is recorded as such.

#### 2.7.2 The protection

An instance MAY be **protected** against a planned reboot. The
protection is built like the backup exclusion of `oaap.data.backup`
2.1.2 (RFC-0029 D5b), with the same three conditions, none optional:

1. **A reason**, in the words of the person who sets it, shown
   wherever the protection is shown. A protection with no reason MUST
   be refused.
2. **An end.** A protection expires on a calendar day (inclusive);
   the default is 7 days, the maximum 30. Extending it is the same
   command again, with a reason again. There is no protection without
   an end.
3. **Visibility to everybody it concerns**: an entry in the log of the
   instance's tenant (`oaap.core.tenant` 1.7, `instance.protected` /
   `instance.released`), the instance's page in the portal, the care
   state ("held by `joerg-desk` until 2026-11-12: reason"), and the
   fleet document (`oaap.fleet.status` 0.6).

Who: a `tenant_admin` of the instance's tenant, or `server_admin`.
The platform has no role "owner of an instance" (`created_by` is a
record, not a right); the tenant's administrator is the nearest
responsible person. A protection is **per instance**: the thing that
must not be interrupted is a running desk, not a customer. A
protection that names an instance the node no longer has is ignored,
never trusted (the posture of the backup exclusion). A manifest
cannot ask for a protection and the platform never sets one on an
app's behalf.

What a protection does: it moves a `care` plan to the first window on
the day **after** the last live protection on the node ends. What it
does not do: hold a `critical` plan. A protection on a critical plan
is **shown as overridden** — the person who set it must learn that it
did not hold — and the plan says why.

**The doors (0.7, RFC-0069 stage 5).** Two doors, one rule. At the
machine, `oaap node care protect <instance> --reason "…" [--until
YYYY-MM-DD]` and `oaap node care release <instance>` (`server_admin`).
In the portal, the instance's page carries a card **"Neustart-Schutz"**
for a `tenant_admin` of the instance's tenant and for `server_admin`:
protect, extend (the same form again, with the reason again) and
release. Each button is one request through the spool (`action: care`,
ops `protect` and `release`). The worker takes role and tenant from
the **actor's own record**, never from the request, and calls the
function the command line calls, so the three conditions above hold at
both doors. An instance of another tenant is answered as one that does
not exist (`oaap.core.tenant` 2.3 rule 2). A refusal is recorded in
the log of the tenant the act was meant for, with the person and the
role; a done act records itself (`instance.protected`,
`instance.released`). After a done act the node recomputes the plan
**at once**, so the card, the band of 2.7.5 and every other reader see
the move now, not next minute. The card reads only the care file of
2.6.2: it shows the plan, this instance's protection (end and reason)
and whether a `critical` plan overrides it; it never shows who set the
protection — that is the tenant log's. The page's door refuses a
protection without a reason and an end that is not a day before
anything is queued, and names what the node answered on the same page.

#### 2.7.3 The urgency

Two levels, **derived from recorded facts**, never typed in:

| Urgency | When | The plan |
|---|---|---|
| `care` | the waiting kernel did not come from the distribution's **security origin** (a point release, a vendor kernel), **or** the node is not exposed | waits for the first window with no live protection, at least 24 h ahead; says it is waiting and for whom |
| `critical` | the waiting kernel came from the security origin **and** the node is **exposed**: it has an external name (`oaap external`, RFC-0043) or its gateway listeners negotiate MPTCP (2.6.1) | the first window at least 24 h after announcement; protections are shown and overridden; `server_admin` may shorten, down to now |

The origin of the waiting kernel is read from the package manager's
policy for the installed kernel package (the archive it was fetched
from: the security archive, the distribution's main archive, a vendor
archive). This is deliberately coarser than "publicly exploitable
from the remote" (D3 of 2026-11-05): the node can read the origin
today and an advisory not yet. Every security kernel on an exposed
node is treated as the one of 2026-11-05. A later advisory match MAY
only lower a `critical` to `care` when the advisory says local-only,
never raise one the origin did not flag.

A `care` plan that protections have held for more than **7 days**
after its announcement is `deferred`: still a plan, but an attention
of its own in the fleet document, because a fix that has waited a week
needs a look.

#### 2.7.4 The window moves to the platform

2.6.3 wrote the distribution's `Automatic-Reboot`. Since 0.3 the
platform's settings file says `Automatic-Reboot "false"` **always** and
keeps the window as a key of the platform's own
(`OAAP::Care::Reboot-Window` in the reference). The minute job
evaluates the plan, and at *T* it is the minute job that runs the
reboot, as root, after a last measurement and after announcing
"rebooting now". The measurement no longer writes the distribution's
marker file (2.6.3); the marker is read as the hint it always was. An
updated node with a 2.6.3-style file has it rewritten by the first
measurement; the window value is kept. Two reboot mechanisms on one
machine are two truths; a node on 0.3 MUST have the distribution's off.

`server_admin` MAY **shorten** a `critical` plan, or make or cancel a
hand-made one, with a reason; the act is filed in every tenant's log on
the node. A cancelled computed plan returns the next minute when the
kernel still waits, with a fresh 24 h lead. No backup is taken by the
plan: 2.6.3 put the window after the backup on purpose.

#### 2.7.5 What everyone is told

No new channel. The plan, every move, the override of a protection,
the start of the reboot and the closing proof are **filed in the log of
every tenant on the node** (`oaap.core.tenant` 1.7, `reboot.*`). The
care state of 2.6.2 carries the plan and the live protections in all
three places, so `oaap status`, the portal and the fleet document say
the same time; and the portal shows **every signed-in person** of a
tenant a band on the tenant's place (RFC-0042) with the time and the
urgency — a reboot nobody can read is a surprise with a timestamp.
The cases are 2.7.6 (0.4); a door an instance reads
(`/platform/care.json`) and the broker event are the later stages of
RFC-0069.

#### 2.7.6 The cases (0.4, RFC-0069 stage 2)

Where a tenant on the node has an inbox (a `vorgaenge` instance,
RFC-0061), the plan is also a **case** there: one per plan, opened with
the announcement, written on at every move (a protection arrived or
went, an override, overdue, "rebooting now"), closed with the proof
after the reboot or with the cancellation. Every production inbox on
the node receives it, one per tenant; a test inbox and a rehearsal
never do (the rule of `oaap.core.gateway` 0.2.16 for a production
source). The node is the reporter. The case carries the time, the
urgency, the reason in words — the origin of the waiting kernel as a
phrase, the operator's own words for a plan by hand — and the
protections held or overridden. It carries **no kernel version**:
`oaap status` and the fleet document say which kernel, the inbox says
when and why. Nobody has to act on the case; it is the record a tenant
reads where they read everything else.

The way in is the way of an app's backend (RFC-0061 §3.2), not a new
one. The platform mints, per inbox, a machine principal
`platform:<inbox instance>` in the inbox's tenant, with a key limited
to the scope `oaap.cases.node:<inbox instance>`; the gateway admits
that key only at `/platform/cases/node` on that inbox's own site
(`oaap.core.gateway` 0.2.19) and attests the source; the inbox checks
the same principal against the source once more. The key lives on the
node readable by root only, is renewed before it expires like an
instance's own keys (RFC-0062 D3) and goes when the inbox goes. The
case numbers travel with the stored plan, so the minute job writes on
and closes the case it opened — across the reboot. An inbox that does
not answer never holds the plan: the failure is logged, and the case
is opened at the plan's next event.

**The same door for requests (0.10, RFC-0109 §13).** The node writes a
tenant's request to the operator (`oaap.core.tenant` 2.13) through the
same door of the inbox the operator named: `op: open` with
`object: request`, the request's id as `ref` (a second open with it
returns the case), and `from` -- tenant and person as the node's record
says; the case's sender reads "<from> (über den Knoten <node>)", and its
attestation stays the node's principal. `op: note` may add a line in the
same name. `op: read` returns the case's state and the entries of the
people working it -- comments with text and status changes -- **never an
internal entry and never the node's own**, and only for a case the node
opened. Any other `object` is refused.

#### 2.7.8 The event on a broker node (0.6, RFC-0069 stage 4)

Where the node runs a broker (`oaap.events.broker`, profile `broker`),
every move of the plan is also one **retained message** on the operator
tenant's tree — the tenant that holds an inbox (2.7.6); with several
inboxes, each of their tenants' trees — at
`oaap/<tenant-id>/node/<hostname>`: the shape of RFC-0032 (`kind`,
`object_id` = `urn:oaap:node:<hostname>`, `group_key` = `care`, `origin`
= `oaap.node.care`, `recorded_at`), the five facts the case carries
(`at`/`at_local`, `urgency`, `reason` in words, `held_by`, `overridden`),
the plan's `state` (`planned`, `overdue`, `rebooting`, `done`,
`cancelled`), a `ref` that is the same for every message of one plan,
and the case's own sentence as `text`. The same rule decides a message
and a case entry, so the two never disagree; a message MUST NOT carry a
kernel version. The last message on the topic is the plan's last state
— `done` or `cancelled` — so a subscriber arriving later still knows;
the topic is not cleared.

The minute job publishes **from the host** with the platform's relay
principal (`oaap.events.broker` 2.4), on the broker's container address
and plain port that never leave the node; the twin's relay container is
not extended for this. A message the broker did not take — it comes up
late after the very reboot the `done` message is about — waits in a
file beside the registry and goes with the next minute, oldest first,
never lost to a broker that is still starting; a broker that stays away
is said in the minute job's journal. A node without the profile
publishes nothing and keeps no file; a broker node without an inbox has
no operator tenant and publishes nothing, said once per event.

#### 2.7.7 The door an instance reads (0.5, RFC-0069 stage 3)

An app on the node may need the hour, not the reason: a desk saves its
session before it, a long job does not start into it. So the node
answers one door **inside the node only**: `/platform/care.json` on a
gateway listener that is never published on the host
(`oaap.core.gateway` 0.2.20), reachable from every container network
the gateway joins and from nowhere else. Every instance is told the
address as `OAAP_CARE_URL` (`oaap.apps.runtime` 2.28) — an address, not
a credential; a rehearsal gets it too, its sessions end with the same
reboot.

The answer is written by the minute job with every evaluation of the
plan and carries exactly: `reboot_at` (UTC) and `at_local`, `urgency`,
`held` (a protection holds the plan), `state` (`planned`, `overdue`,
`rebooting`) and `measured` — all null and `held: false` without a
plan. It MUST NOT carry a kernel version, a reason, an instance name or
a protection's words: an app sees when, not why. Until the node's first
measurement after the update the door answers 404, which an app MUST
read as "no plan". The desk (`webtop` 0.1.10) is the first reader: it
tells the person at the desktop the hour, warns 30 and 10 minutes
before, and leaves a note on the desktop that disappears with the plan.
What an app does with the hour is the app's.

### 2.8 Advisories: what is known about what the node runs (0.8, RFC-0070 stage 1)

**Why this is here.** On the evening of 2026-11-05 the line of 2.6 said
"Auto-updates: on, last run 13:17 UTC" on a node that carried 13 open
Debian security advisories, the oldest since 14 August. The program,
the switch and the timer were in place — since that morning — and the
"last run" was the stamp of a dry run. A switch holds an intention; the
operator's question after an announcement is "does this concern my
node, and is it fixed here?", and only a comparison answers it.

#### 2.8.1 The reading

Every node reads **its own** installed packages and compares them with
the distribution's advisory list; a reading taken elsewhere describes
another machine (RFC-0070 D1). For Debian the list is the security
team's DSA list (one text file, read over HTTPS from the
distribution's own host) (D2). The node reads it once a day, after
every automatic-update run, and on demand; a failed read is retried
hourly. List and result lie beside the registry (`advisories.txt`,
`advisories.json` in the reference), world-readable: the list is public
data, and the package database it is compared with is readable by every
user of the machine anyway.

The rules, each a function in the reference:

- The list is **data, parsed with a fixed grammar**: a header per
  advisory, an optional line of CVE names, one line per release with
  the source package and the fixed version, notes. A release line whose
  version is not a version (`<not-affected>`, `<unfixed>`) is no fix. A
  line the grammar does not know is **skipped and counted**, never read
  as "no advisory". A fetched text whose first line is not an advisory
  header is refused and the previous list kept.
- Per installed **source** package the **newest** advisory for the
  node's suite counts, and the package is **open** when its installed
  version is older than that advisory's fixed version — compared with
  the package manager's own comparator, never as a string.
- **The kernel** is `linux` in the list and `linux-signed-<arch>` in the
  package database (`6.12.115+2` there is `6.12.115-2` here). For the
  kernel the **newest installed** version counts: older images are
  inert files, and whether the newest one *runs* is 2.6.1's verdict.
- A package whose installed and candidate versions come only from an
  archive of **another origin** (Docker CE, a vendor kernel) is
  `unknown` — named and counted, never compared, never clean. A package
  no archive carries any more is `local`, named the same way.
- Beside the comparison, the node records how many packages the package
  manager would install from the security archive now — the second
  reading, from the package manager's own knowledge, with no network.

The result in the care file is the block `advisories`: `source`,
`read_at`, `stale` (`read_at` older than two days, or never), `open`
(a number, or **null when no list was ever read** — never 0), `oldest`
and `oldest_package`, `items` (package, advisory, published, fixed,
installed, number of CVEs), `unknown`, `local`,
`security_candidates`, `skipped`, `error` (the last failed read). A
failed read keeps the previous list and its count; after two days the
count is shown as stale. A node that has never read the list has no
block, and every reader says "not read yet".

#### 2.8.2 What is told

No new channel — the three places of 2.6.2:

1. **`oaap status`** carries one more line: "Advisories: 13 open, the
   oldest since 2026-08-14 (util-linux) — list read … — 4 package(s)
   from other archives not covered. Which: `sudo oaap node care
   advisories`". `sudo oaap node care advisories [--read]` names the
   open ones (package, advisory, date, installed, fixed), the uncovered
   packages and the skipped lines; it requires root — the names are the
   operator's.
2. **The portal** shows the same line in the `server_admin`'s care band
   and a row "Sicherheitsmeldungen" in the node table, with the names.
3. **`/fleet/status`** carries `host.advisories` with `open`, `oldest`,
   `stale`, `read_at` and the **number** of uncovered packages — never a
   package name (`oaap.fleet.status` 0.7) — and two attention kinds,
   `advisories_open` and `advisories_stale`.

The door an instance reads (2.7.7) carries nothing of it.

**Two corrections of 2.6 that came with the reading.** The "last run"
of automatic updates is the **timer's** stamp
(`/var/lib/apt/periodic/upgrade-stamp`, written after a real run),
not the program's own, which every invocation writes, a dry run
included; without the timer's stamp the line says "no run yet". And
the distribution's reboot marker, when it is set while the kernel pair
says no reboot (a library asked for it — measured on oaap-demo,
2026-11-06, after its first real run), is shown as a hint without a
plan: 2.6.1 already says it may be a hint and never the verdict.

What 2.8 is **not** yet (RFC-0070 stages 2–4, decided 2026-11-06): the
case after a grace (24 h exposed, 7 days otherwise) and the one early
update run; the gate for an external name; the tracker's CVE ratings.
Lowering the urgency of 2.7.3 by a rating is decided **no, for now**
(D7).

### 2.9 Images: what the instances run on (0.9, RFC-0071 stage 1)

The node's own packages are half of it: every instance runs an image
with packages of its own, on a base the node pulled once. The care
state therefore carries a second reading, made by the node (it needs
Docker, which no container gets):

- per image the instances and the platform's own containers run (by the
  id the container **runs**, not by its tag): the comparison of 2.8.1
  against the image's package database, read with no network,
  read-only, without pulling, as the image's user. One image serving
  many instances is read once. No package database (Alpine,
  distroless) is `unknown`, never "0 open"; an image the container
  still runs but the node has removed (a newer build took its tag —
  measured on oaap-test, 2026-11-06: three platform containers) is
  `unknown` with that reason;
- per distinct base reference, once a day: the upstream index digest,
  compared with the instance's base record (`oaap.apps.runtime` 2.29)
  or, for a foreign image, with its own local digest;
- the word per instance of `oaap.apps.runtime` 2.29.

The reading is cached per image and list: a new list reads every image
again, an unchanged one reads only new images. The minute job reads
within a budget (25 s in the reference); what is left comes the next
time. `sudo oaap node care images [--read]` reads everything now.

**Told** in the three places, without a new channel: a line in `oaap
status` ("Images: 28 instances — 19 with open advisories (the oldest
since 2026-05-19), 3 behind upstream, 6 unknown; 3 platform
container(s) with open advisories"); in the portal a row "Abbilder" in
the node table and, on every instance's page, the card **Abbild** —
per service the word, the count of open advisories and the oldest
date, the base and whether upstream moved, **no package name**; in
`/fleet/status` the counts as `host.images` and the attention kind
`images_open` (`oaap.fleet.status` 0.8). The names are the
`server_admin`'s, on the node (`sudo oaap node care images`). The door
of 2.7.7 carries nothing of it.

What 2.9 is not yet: the rebuild on a fresh base with the predecessor
kept (RFC-0071 stage 2), the rebuild by itself in the window (stage 3),
the platform's own images pulled by `oaap update` (stage 4), the app's
own dependencies (stage 5).

### 2.10 Freeing disk space (0.11, RFC-0128)

Every new version of an app builds a new image and the old one stays; the
build cache grows with every build. The node frees what it no longer needs,
in classes (RFC-0128 §2):

| Class | What | Rule |
|---|---|---|
| A | the build cache no image shares, dangling layers | always |
| B | an older version of an image the node built (`oaap-inst/…`, before RFC-0130 `oaap-app/…`) in a repository a registered instance uses | always -- per repository the image in service, the `-prev` of a rebuild and the **previous version** (the newest tag built before the one in service) stay |
| C | an image the node built that no registered instance uses (its repository is nobody's, or the `-prev` of an instance that is gone) | after **seven days counted from the first run that saw it so**, not from its build |
| D | an image the platform did not build | never by itself -- listed with size, removable one by one by the `server_admin`; a base an image was built from says so ("ein Neubau lädt es dann neu") |
| E | volumes, instance storage, backups, retained packages | never; nothing in the measure names them |

Never a candidate, whatever its class: an image a container uses (running or
stopped -- a sleeping instance is a stopped container), an image a registered
instance needs to start (its service images, its `-prev`; a rehearsal is
registered like any), an image younger than a day (a deploy may be writing
it), the platform's own images (what compose builds and what its files name).
Removal is `docker rmi` without force (Docker refuses an image in use by
itself) and, for A, `docker image prune -f` and `docker builder prune -f` --
not `-a --filter until=…`, which freed 0 B of 66 GB on Docker 29.7.1 (RFC-0128
§10, F11).

**When.** Nightly (D1): the minute job starts a run in its own process once a
day -- after the nightly backup finished when the node has one, else from
03:00 local -- never while a backup copies; one run at a time. **On
pressure** (D5): before `disk.full` opens and before a new `disk.trend` or
`disk.soon`, at most every six hours, a run A-C, the disk measured again; the
matter's text then says what was freed ("Vor dieser Meldung hat der Knoten
aufgeräumt: 8,0 GB freigegeben; Platte 92 % → 84 %") and, still above the
threshold, names the foreign images by size -- what only a person may
remove. **By hand:** `sudo oaap node care space [--dry-run] [--class A,B,C]`,
`sudo oaap node care space rmi <image>` (class D only, from the plan of now),
and the portal page **Platz** (`oaap.core.portal` 2.22).

**Told.** One line per run in the node's tenant log, `space.freed` (cause
nightly, pressure, portal or hand; the sentence with bytes freed and the disk
before and after; the bytes as a number), and `space.foreign` per removed
foreign image with name and size. The weekly report (RFC-0083) carries one
line "Platz freigegeben: X in N Läufen" instead of seven events; a removed
foreign image stays an event. The plan of the last measurement is
`apps/space.json` (0644, what the portal reads -- never Docker), the first
sightings of class C and the last run `apps/space-state.json` (0600). Sizes
are those `docker image ls` shows (unpacked); shared layers make a class's
sum an upper bound, the disk before and after is the measured truth.

**journald** (D4): install and `oaap update` (migrate.sh) write
`/etc/systemd/journald.conf.d/oaap.conf` with `SystemMaxUse=2G` -- a drop-in
of our own, so an operator's `journald.conf` stays theirs -- and restart
journald only when the file changed.

### 2.11 The packages that wait (0.12, RFC-0139 stage 1)

Security updates are installed by the node itself (2.6.3). What else waits
-- on the reference fleet almost only Docker's packages -- is counted:

- **The measurement** (with 2.6.1, every ten minutes): `apt list
  --upgradable` in the C locale, after apt's own daily list refresh. Each
  package is `security` (its archive ends in `-security`), `docker` (by
  name: `containerd.io`, `docker-ce*`, `docker-*-plugin`, any `docker-` --
  Docker's archive names its suite like the distribution's) or `other`. The
  care file carries **counts only**: `updates = {waiting, security, docker,
  other}`; `null` when apt did not answer (an absent reading, never 0, and
  then no line). **While apt or dpkg runs** (seen in `/proc`, no lock taken)
  the last reading stands: their lists are half-written then and apt says 0
  (measured 2026-11-27, 0.1.393).
- **Told:** a line in `oaap status` and on the portal's health page
  ("Updates: 6 waiting, 0 security, 6 Docker -- see: …", `warn` only while a
  security update waits); the matter `host.updates` (oaap.core.notifications,
  operations, node, reminded every 24 h while anything waits); a line in the
  node's weekly report with the counts of the week's last day and a waiting
  reboot.
- **Shown:** `sudo oaap node care upgrade --dry-run [--docker]` names every
  package with installed and new version, grouped, and says how many an
  upgrade would take -- Docker's only with `--docker`, because their update
  restarts containerd and dockerd and every app of the node is away for about
  a minute (RFC-0139 §9). Root only: the names are the operator's.
- **Installing** on the administrator's word: 2.12 (CLI) and 2.13 (portal).
  The node installs nothing by itself beyond 2.6.3.

### 2.12 Installing on the administrator's word (0.13, RFC-0139 stage 2)

`sudo oaap node care upgrade [--docker]` -- root only, one function for the
CLI and (stage 3) the portal:

1. **The plan**: after `apt-get update`, every waiting package -- security and
   other always, Docker's only with `--docker` (every app restarts once,
   about a minute). Nothing in the plan: nothing happens, no backup, no
   notification.
2. **Its own unit** `oaap-upgrade` (`systemd-run`): the run survives the
   ssh session and the minute job; a second start while one runs is
   refused, so is a start while a backup copies. The CLI follows the log
   (`/var/lib/oaap/data/upgrade/upgrade.log`); Ctrl-C leaves the run going;
   `--status` shows the last run.
3. **Backup first** (`oaap backup create`); when it fails nothing is installed.
4. **apt**: `apt-get install --only-upgrade --no-remove -y` with the named
   packages, non-interactive, existing configuration files kept
   (`--force-confold`). `--no-remove`: apt aborts rather than remove anything.
5. **The check**: the containers that ran before must run again; the run
   waits up to five minutes (Docker's own restart, measured 55 s) and names
   those that did not come back.
6. **Told**: an audit line `host.upgraded` in the node's log (`failed` when
   apt failed or a container is missing), the notification `host.upgraded`
   (once), and host care measures afresh -- `host.updates` closes when
   nothing waits. A new kernel leaves `reboot required`; the reboot is the
   existing planning's (2.7), never immediate.

### 2.13 The portal's section „Updates“ (0.14, RFC-0139 stage 3)

On the health page, **only for the server_admin at the node's own address**
(D8; a tenant_admin, a member, and a server_admin at a tenant's place see no
section, and its doors answer 403 / 404):

- **The view** `apps/upgrade.json` (written by the host, readable by the
  portal): the waiting packages of the last reading (name, installed, new,
  archive, kind), the run (state, started, finished, who, Docker, result
  text) and, while a run is on, the last 30 lines of its log. The names go
  only here, never into the care file. A reading while apt runs, or without
  an answer from apt, leaves the list as it was.
- **Shown:** the packages grouped Sicherheit / Docker / Sonstige; a tick
  „Docker mit aktualisieren — alle Apps starten dabei einmal neu“ (unticked,
  only when Docker's packages wait); „Jetzt einspielen“ with a confirmation
  that names the backup and, ticked, the restart of every app including the
  portal; „Neu zählen“; the last run's result.
- **The order** goes through the spool (`action: upgrade`, op `run` with
  `docker: true|false`, or op `measure`). The worker takes role and person
  from the actor's own record -- the request carries none it trusts; only a
  server_admin is served, a refusal is audited (`host.upgrade.<op>`,
  `denied`). `run` calls the start of 2.12 -- the same unit, the same
  refusals (one running, a backup copying), the same end (audit and
  `host.upgraded`).
- **While it runs** the section shows the log's end and reloads every five
  seconds; with Docker the portal itself is away for about a minute.

## 3. Configuration

- Recorded source: repository URL, branch/ref, working-copy path
  (set at install; changeable only by an administrator on the node).
- Reserved: update channel (e.g. `stable`/`testing`), maintenance
  windows (for the schedule trigger).
- Host care (2.6): the auto-update switch and the reboot window, in
  one file of the platform's own under the package manager's
  configuration directory (`/etc/apt/apt.conf.d/52oaap-care` in the
  reference); the latest measurement in `host-care.json` beside the
  registry, world-readable, facts only.
- Reboot plan and protections (2.7): the stored plan (`reboot-plan.json`)
  and the protections (`reboot-protections.json`) beside the registry;
  the care file carries the live view of both for the readers.
- The broker event (2.7.8): messages the broker has not taken yet in
  `care-events-pending.json` beside the registry (at most the newest
  50), removed when empty; the relay principal's secret is the node's
  `BROKER_RELAY_KEY` of `oaap.events.broker` 3, read from the platform's
  own environment file, never stored again.

## 4. Security requirements

- The update trigger is privileged: CLI requires root; the future
  portal trigger requires the `server_admin` role (RFC-0008 — updating
  the platform is server administration, not app-facing) and runs
  through the host-task channel, never as the web process.
- **Source pinning:** no trigger can inject a source, ref, or payload;
  the engine only ever pulls the recorded source (same principle as
  deploy tokens: requests carry intent, never content).
- Transport integrity: the source is fetched over authenticated
  channels (HTTPS/SSH git). Signed releases (tag signatures) are a
  planned hardening step, required before the schedule trigger ships.
- Updates must not weaken the platform: secrets, app data, and the
  instance registry are never rewritten by an update; gateway
  default-deny must hold before and after.
- Host care (2.6): the measurement runs with administrator rights but
  **writes only its own file** (and, with a reboot window set, the
  distribution's reboot marker — 2.6.3); the two settings touch only the
  platform's own configuration file; the portal reads and never writes;
  nothing but the kernel's name and the verdicts leaves the node (no
  package list — a package list is a map for an attacker).
- Reboot plan (2.7, RFC-0069 §6): the node MUST NOT reboot itself
  without a measurement taken in the same minute that says the reboot
  is still required, or a hand-made plan by `server_admin`; a
  protection MUST carry a reason and an end within the maximum and
  MUST be filed in the tenant's log; a `critical` plan MUST NOT be held
  by a protection and the override MUST be shown and filed; urgency
  MUST be derived from recorded facts, the one exception
  (`--critical` on a hand-made plan) filed as such; the distribution's
  own automatic reboot MUST be off on a 0.3 node; a plan whose time
  has passed MUST be visible as overdue.
- The cases (2.7.6): the node's key for an inbox MUST be limited to
  that inbox's door and that inbox's tenant, MUST be readable by root
  only, and MUST be revoked when the inbox is removed; the inbox MUST
  refuse the door to every other principal, a person's session
  included; a case MUST NOT carry a kernel version; a failing inbox
  MUST NOT delay or hold the plan.
- Advisories (2.8, RFC-0070 §4): the list is data — parsed with a fixed
  grammar, nothing in it executed, an unknown line skipped and counted;
  it MUST be read over HTTPS from the distribution's own host; a failed
  read MUST keep the previous list, MUST set `stale` after two days and
  MUST NOT yield "0 open"; versions MUST be compared with the package
  manager's comparator; a package from an origin the list does not
  cover MUST be reported as `unknown`, never as clean; the fleet
  document MUST NOT carry package names; the "last run" MUST come from
  the timer's stamp.
- The door (2.7.7): `/platform/care.json` MUST NOT be reachable from
  outside the node — a listener the host never publishes, never a path
  on a published site — and MUST NOT carry a kernel version, a reason,
  an instance name or a protection's words.

## 5. Conformance tests (described)

1. **Update happy path:** a node behind the recorded source updates
   with one CLI action; afterwards the new version is visible
   (`oaap status`, login greeting) and all core services are healthy.
2. **No-op:** running the engine on an up-to-date node reports so and
   installs no code, rebuilds no image and restarts no container. The
   consistency steps of test 8 still run; on a node that is already
   consistent they change nothing and say so.
3. **Apps and data untouched:** app instances keep running through a
   core update; storage, secrets (`OAAP_APP_SECRET`), and the
   registry are byte-identical afterwards.
4. **Build failure is safe:** an update whose image build fails
   leaves the old containers running and the old version recorded.
5. **Source pinning:** the CLI offers no way to update from a
   different repository/ref; the engine uses the recorded source even
   if the environment suggests another.
6. **Check is read-only:** `--check` performs no system change.
7. **Medium-installed nodes:** a node installed without a git working
   copy acquires one from the recorded URL on first update and passes
   test 1.
8. **The engine cannot skip its own new steps:** a node several versions
   behind, whose target version adds a consistency step, has that step
   applied by the single update — not by a later one. Running the engine
   again immediately changes nothing further and reports nothing new
   (idempotence), and a node that missed a step under an older engine
   has it applied on the next run even though there is no code to
   install. A step that fails is reported and leaves the update
   standing.
9. **Reboot verdict by comparison (2.6.1):** a node whose newest
   installed kernel of the running flavour is newer than the running
   one reports `reboot_required` even when no marker file exists; a
   node whose newest installed kernel of *another* flavour is newer
   does not.
10. **Three parts, one verdict (2.6.1):** with the auto-update program
    installed but the periodic switch missing, the verdict is `warn`
    and the detail names the switch; with the switch present and the
    timer inactive, the detail names the timer.
11. **Three places, one measurement (2.6.2):** `oaap status`, the
    portal band and `/fleet/status` show the same kernel pair and the
    same verdicts, taken from one file; after a fresh measurement all
    three change together.
12. **The switch is written, not assumed (2.6.3):** `auto-updates on`
    on a node where the package is already installed without the
    switch leaves the node with the switch set; running it again
    changes nothing and says so.
13. **The window is a node setting (2.6.3):** `reboot-window 04:15`
    appears in the care state of all three places; `off` removes it;
    neither command touches the distribution's own files.
14. **The plan needs a window and a reason (2.7.1):** with a newer
    kernel installed and no window there is no plan; with a window the
    plan's time is the window hour on the first day at least 24 h after
    the announcement; recomputing it an hour later keeps the
    announcement and the time.
15. **A protection holds `care` and not `critical` (2.7.2, 2.7.3):**
    a live protection until day *D* moves a `care` plan to the window
    on *D+1*; the same protection on a `critical` plan leaves the time
    and lists the protection as overridden; a protection without a
    reason, or with an end beyond the maximum, is refused; one naming
    an instance the node does not have is ignored.
16. **Urgency from facts (2.7.3):** a security-origin kernel on a node
    with an external name is `critical`; the same kernel on a node
    without one is `care`; a kernel from the main archive on an exposed
    node is `care`; a hand-made plan is `care` unless `--critical`.
17. **The plan closes with proof (2.7.1):** after a reboot the next
    measurement files `reboot.done` with the running kernel and the
    plan is gone; a plan whose time passed without a reboot is shown
    as overdue in all three readers.
18. **One mechanism (2.7.4):** on a 0.3 node the settings file says
    `Automatic-Reboot "false"` whatever the window is; a 2.6.3-style
    file is rewritten by the first measurement with the window kept.
19. **The inboxes hear it (2.7.6):** a plan announced on a node with
    an inbox opens one case there, in the tenant's words, without a
    kernel version; a protection arriving adds a note with the new
    time and the holder; the reboot closes it with the proof; a
    cancellation closes it as cancelled; a second inbox of the same
    tenant, a test inbox and a rehearsal receive nothing; a person's
    session and an app's backend key are refused at the door.
20. **The case follows the plan (2.7.6):** the case number is in the
    stored plan a minute later and after the reboot; an inbox that
    answered 503 at the announcement gets its case at the next event.
21. **The door says when, not why (2.7.7):** from inside a container
    `OAAP_CARE_URL` answers the plan's time, urgency, `held` and state
    and nothing else; from the LAN the port does not answer; without a
    plan every value is null; before the first measurement it is 404.
22. **Two doors, one rule (2.7.2, 0.7):** a `protect` request through
    the spool by a `tenant_admin` of the instance's tenant writes the
    same record and the same log entry as the command line, with the
    person and the role; by a `tenant_admin` of another tenant it is
    refused with the sentence for an instance that does not exist, and
    the instance's tenant learns nothing; by a person without an admin
    role it is refused and recorded in their own tenant; without a
    reason, or with an end past 30 days, it is refused; a done act
    recomputes the plan at once; the page queues nothing without a
    reason.

## 6. Dependencies

`oaap.core.host` (installation layout, recorded configuration).
The portal trigger will additionally depend on `oaap.core.portal`
and the host-task channel. Host care (2.6) is read by
`oaap.fleet.status` 0.5 (`host` block) and states a rule of
`oaap.core.gateway` 0.2.18 (plain TCP listeners).
Host care 2.7.8 publishes with the relay principal of
`oaap.events.broker` 0.2.2 (2.4) into the tenant tree of 2.2 there.
Host care 2.7 writes entries defined by `oaap.core.tenant` 1.7
(`reboot.*`, `instance.protected`, `instance.released`) and is read by
`oaap.fleet.status` 0.6 (`reboot_plan`, `protections`, three attention
kinds). Its CLI is `oaap.core.host` 2.3 (0.3.8). The cases of 2.7.6 go
through `oaap.core.gateway` 0.2.19 (`/platform/cases/node`) into the
`vorgaenge` app of RFC-0061 (0.3.0 or later).

## 7. Maturity

`draft` — 0.1 target: CLI trigger implemented in the reference and
proven on the real fleet (oaap-test first, then all four nodes);
tests 1–7 described above executed on real hardware. 0.2 candidates:
portal trigger via host-task channel, signed releases, update
channels, schedule trigger.

## German summary / Deutsche Zusammenfassung

Jeder Knoten hat EINE Update-Engine mit drei Auslösern: **CLI
(`oaap update`, in 0.1 umgesetzt)**, Portal-Button und Zeitplan (beide
reserviert). Die Plattform merkt sich bei der Installation ihre
**Quelle** (Git-Repo, Branch, Arbeitskopie); Update heißt immer „die
hinterlegte Quelle neu ziehen" — kein Auslöser kann eine andere Quelle
mitgeben (gleiches Prinzip wie beim Deploy-Hook). `oaap update --check`
zeigt nur, was sich ändern würde; `oaap update` wendet an: pull (nur
fast-forward), Plattformdateien kopieren, Core-Images neu bauen,
Services neu starten, Gesundheit prüfen, Revision festhalten.
Garantien: auf aktuellem Stand passiert nichts; schlägt der Build
fehl, laufen die alten Container weiter; App-Instanzen, Daten und
Secrets werden nie angefasst. Stick-Installationen (ohne Git-Kopie)
klonen beim ersten Update das hinterlegte Repo. Rollback ist in 0.1
dokumentiert-manuell; signierte Releases und automatische Updates
kommen, bevor der Zeitplan-Auslöser scharf wird.

## Deutsche Zusammenfassung (0.9 — Abbilder, §2.9)

Die Pakete des Knotens sind die halbe Wahrheit: jede Instanz läuft auf
einem Abbild mit eigenen Paketen, auf einer Basis, die der Knoten einmal
geholt hat. Seit 0.9 liest der Knoten je Abbild, das ein Container
*wirklich* ausführt, dieselben Debian-Meldungen wie in 2.8 — ohne Netz,
read-only, ohne Pull, einmal je Abbild auch für viele Instanzen —, fragt
täglich je Basis den Upstream-Digest ab und gibt jeder Instanz ein Wort
(`fresh`, `behind`, `open`, `unknown`, `stale`). Kein Paketverzeichnis im
Abbild (Alpine) oder ein vom Knoten gelöschtes Abbild, auf dem der
Container noch läuft (am 06.11. drei Plattform-Container auf oaap-test),
heißt `unknown`, nie „0 offen“. Gezeigt: eine Zeile in `oaap status`, im
Portal die Zeile „Abbilder“ und auf jeder Instanzseite die Karte
**Abbild** (Wort, Anzahl, ältestes Datum, Basis — keine Paketnamen), im
Flottendokument nur Zahlen. Die Namen zeigt `sudo oaap node care images`.
Neu bauen kommt mit RFC-0071 Stufe 2.

## Deutsche Zusammenfassung (0.8 — Sicherheitsmeldungen, §2.8)

Am Abend des 05.11. sagte die Zeile „Auto-Updates: an“ auf einem Knoten
mit 13 offenen Debian-Sicherheitsmeldungen, die älteste vom 14. August.
Seit 0.8 vergleicht jeder Knoten selbst seine installierten Pakete mit
Debians DSA-Liste: einmal täglich, nach jedem automatischen Update-Lauf
und auf Wunsch gelesen, mit fester Grammatik ausgewertet (unbekannte
Zeilen werden gezählt, nie als „keine Meldung“ gelesen), mit dpkgs
eigenem Versionsvergleich. Ein Paket ist **offen**, wenn die installierte
Version älter ist als die Fix-Version der neuesten Meldung. Der Kernel
heißt in der Liste `linux`, bei dpkg `linux-signed-amd64`; dort zählt
das neueste installierte Abbild (ob es *läuft*, sagt weiter 2.6.1).
Pakete aus fremden Archiven (Docker, Pi-Kernel) heißen `unknown`, nie
„sauber“. Ohne gelesene Liste gibt es keine Zahl, nie „0 offen“; eine
Liste älter als zwei Tage heißt „veraltet“.

Gezeigt wird es an den drei Orten von 2.6.2: eine Zeile in `oaap status`
(Namen mit `sudo oaap node care advisories`), Zeile und Tabellenzeile im
Portal für den Server-Admin, im Flottendokument nur Zahl, Datum,
„veraltet“ und die Anzahl nicht abgedeckter Pakete — keine Paketnamen.
Nebenbei korrigiert: der „letzte Lauf“ kommt vom Stempel des Timers, nicht
vom Programm (das auch beim Probelauf stempelt); ohne Stempel heißt es
„noch kein Lauf“. Und die Neustart-Markierung der Distribution ohne neuen
Kernel (eine Bibliothek, gemessen auf oaap-demo am 06.11.) wird als
Hinweis gezeigt, ohne Plan. Vorgang nach Frist, vorgezogener Update-Lauf,
Tor für externe Namen und CVE-Schwere folgen als Stufen 2–4 von
RFC-0070; das Herabstufen der Neustart-Dringlichkeit ist vorerst nein
(D7).

## Deutsche Zusammenfassung (0.7 — die Tür des Mandanten-Admins im Portal, §2.7.2)

**Zwei Türen, eine Regel.** Bisher konnte nur der Server-Admin an der
Maschine eine Instanz schützen (`oaap node care protect`). Seit 0.7 trägt
die Instanzseite im Portal eine Karte **„Neustart-Schutz“** — für den
Mandanten-Admin der Instanz und für den Server-Admin: schützen,
verlängern (dasselbe Formular noch einmal, mit Begründung noch einmal),
aufheben. Jeder Knopf ist ein Auftrag durch den Spool; der Knoten nimmt
Rolle und Mandant aus dem Datensatz des Handelnden, nie aus der Anfrage,
und ruft dieselbe Funktion wie die Befehlszeile. Eine Instanz eines
anderen Mandanten gibt es für ihn nicht — derselbe Satz wie für eine, die
es nicht gibt. Jede Absage steht im Protokoll des Mandanten, mit Person
und Rolle; nach einer Handlung rechnet der Knoten den Plan sofort neu,
damit Karte, Band und alle anderen Leser die Verschiebung jetzt sehen.
Die Karte liest nur die Pflegedatei: Plan, Ende und Begründung des
Schutzes, und ob ein dringender Neustart ihn überstimmt.

## Deutsche Zusammenfassung (0.6 — das Ereignis auf einem Broker-Knoten, §2.7.8)

**Wo ein Broker läuft, ist der Plan auch ein Ereignis.** Auf einem Knoten
mit Profil `broker` geht jede Bewegung des Plans als gehaltene
(„retained“) Nachricht auf den Baum des Betreiber-Mandanten — des
Mandanten mit Posteingang, bei mehreren auf jeden —
`oaap/<mandant>/node/<knoten>`: die Form von RFC-0032 (Art, Objekt,
Gruppe `care`, Herkunft, Zeit), dieselben fünf Tatsachen wie der Vorgang
(Termin, Dringlichkeit, Grund in Worten, gehalten durch, überstimmt), der
Zustand, ein fester Bezug je Plan und der Satz des Vorgangs. Dieselbe Regel
entscheidet über Nachricht und Vorgang, darum widersprechen sie sich nie;
**keine Kernel-Version**. Die letzte Nachricht auf dem Thema ist der letzte
Zustand (`done`, `cancelled`) — wer später abonniert, weiß Bescheid.

Der Minutenlauf veröffentlicht **vom Host aus** mit dem Relais-Prinzipal
der Plattform (`oaap.relay`, `oaap.events.broker` 2.4), auf der
Container-Adresse des Brokers und dem Klartext-Port, der den Knoten nie
verlässt; das Relais des Zwillings wird dafür nicht erweitert. Was der
Broker nicht nahm, wartet in einer Datei neben der Registry und geht mit
der nächsten Minute — der Broker kommt nach genau dem Neustart, von dem
die letzte Nachricht handelt, erst spät hoch. Ohne Profil nichts, nicht
einmal die Datei; ein Broker-Knoten ohne Posteingang hat keinen
Betreiber-Mandanten und schweigt, einmal je Ereignis im Journal gesagt.

## Deutsche Zusammenfassung (0.5 — die Tür, die eine Instanz liest, §2.7.7)

**Wann, nicht warum.** Eine App auf dem Knoten braucht die Stunde, nicht
den Grund: Ein Desk sichert vorher seine Sitzung, ein langer Lauf fängt
nicht hinein an. Der Knoten beantwortet darum **eine** Tür nur von innen:
`/platform/care.json` auf einem Gateway-Port, den der Host nie
veröffentlicht — erreichbar aus jedem Container-Netz des Knotens, von
sonst nirgends. Jede Instanz erfährt die Adresse als `OAAP_CARE_URL`
(eine Adresse, kein Schlüssel; auch eine Generalprobe). Die Antwort
schreibt der Minutenlauf: Termin (UTC und Ortszeit), Dringlichkeit,
gehalten ja/nein, Zustand, Messzeit — ohne Plan alles leer. **Keine**
Kernel-Version, kein Grund, kein Instanzname. Vor der ersten Messung
nach dem Update antwortet die Tür 404, was eine App als „kein Plan“
liest. Erster Leser ist der Desk (`webtop` 0.1.10): Meldung beim Termin,
dringend 30 und 10 Minuten vorher, eine Datei auf dem Schreibtisch, die
mit dem Plan verschwindet.

## Deutsche Zusammenfassung (0.4 — Vorgänge je Posteingang, §2.7.6)

**Der Plan wird ein Vorgang.** Hat ein Mandant auf dem Knoten einen
Posteingang (eine `vorgaenge`-Instanz, RFC-0061), legt der Knoten dort
bei der Ankündigung einen Vorgang an — einen je Plan, im Bereich
„Eingang“, gemeldet vom „Knoten *name*“ —, schreibt ihn bei jeder
Änderung fort (Schutz gekommen oder gegangen, überstimmt, überfällig,
„startet jetzt“) und schließt ihn nach dem Neustart mit dem Beweis oder
mit der Absage. Jeden Produktions-Eingang auf dem Knoten, einen je
Mandant; einen Test-Eingang oder eine Generalprobe nie. Der Vorgang
sagt wann, wie dringend und warum in Worten (die Herkunft des Kernels
als Satz, beim Plan von Hand die Worte des Betreibers), welche Schutze
halten oder überstimmt sind — und **keine Kernel-Version**: die stehen
in `oaap status` und im Flottenstatus. Niemand muss etwas tun; wer den
Eingang liest, weiß Bescheid.

**Der Weg hinein** ist der Weg des App-Backends (RFC-0061 §3.2), kein
neuer: Die Plattform prägt je Posteingang einen Maschinenprinzipal
`platform:<posteingang>` im Mandanten des Eingangs mit einem Schlüssel,
der nur den Scope `oaap.cases.node:<posteingang>` trägt. Das Gateway
lässt diesen Schlüssel nur an `/platform/cases/node` auf der Site
genau dieses Eingangs durch und setzt die Herkunft; die App prüft den
Prinzipal gegen die Herkunft noch einmal. Der Schlüssel liegt auf dem
Knoten nur für root lesbar, wird wie die Instanzschlüssel 30 Tage vor
Ablauf erneuert und geht mit dem Eingang. Die Vorgangsnummern reisen
mit dem gespeicherten Plan, über den Neustart hinweg. Ein Eingang, der
nicht antwortet, hält den Plan nie auf: der Fehler steht im Journal,
der Vorgang wird beim nächsten Ereignis angelegt.

## Deutsche Zusammenfassung (0.3 — Neustart-Plan, Schutz, Dringlichkeit, §2.7)

**Anlass.** Das Fenster aus 2.6 hat am ersten Tag getan, was ein
Fenster tut: Der Neustart von oaap-demo hat eine Desk-Sitzung mit
offenen Anwendungen beendet. Eine Uhrzeit weiß nichts von der Arbeit
auf dem Knoten, und der Mechanismus der Distribution kann einen Schutz
nie kennen — er feuert auf Markierungsdatei und Uhr.

**Der Plan (2.7.1).** Der Knoten sagt „ich starte am … um … neu, weil
…, Dringlichkeit …“ — mindestens 24 Stunden vorher, rechnet den Plan
jede Minute neu, misst am Termin noch einmal und startet nur, wenn der
Neustart dann noch nötig und erlaubt ist. Danach schließt die erste
Messung den Plan mit dem Beweis „läuft 6.12.115“. Ein verpasster
Termin wird als **überfällig** gezeigt, nie still verschoben. Der
Server-Admin darf einen Neustart **von Hand planen** (glibc-Fall), mit
Begründung, durch dieselben Regeln — so wird der Mechanismus auf dem
Testknoten gemessen, bevor ein Kernel kommt.

**Der Schutz (2.7.2).** Eine Instanz kann gegen einen geplanten
Neustart geschützt werden — wie die Backup-Ausnahme: mit Begründung
(ohne wird abgelehnt), mit Ende (Standard 7 Tage, höchstens 30,
Verlängern heißt noch einmal begründen) und sichtbar im Mandanten-Log,
im Portal, im Pflegestand und in der Flotte. Setzt der Mandanten-Admin
oder der Server-Admin, je Instanz. Ein Schutz verschiebt einen
Pflege-Neustart auf den Tag nach dem letzten Schutz; einen kritischen
hält er nicht, wird aber als überstimmt gezeigt.

**Die Dringlichkeit (2.7.3).** Aus Messwerten, nie von Hand:
**kritisch** = der wartende Kernel stammt aus der Security-Quelle
(Paketmanager-Policy) **und** der Knoten ist exponiert (externer Name
oder MPTCP an); alles andere **Pflege**. Bewusst gröber als
„öffentlich aus der Ferne ausnutzbar“ — die Quelle kann der Knoten
heute lesen, ein Advisory noch nicht; ein späterer Abgleich darf nur
herabstufen. Ein Pflege-Plan, der über 7 Tage gehalten wird, ist
„aufgeschoben“ und ein eigener Hinweis in der Flotte.

**Das Fenster wandert (2.7.4).** Die Plattformdatei sagt immer
`Automatic-Reboot "false"` und trägt das Fenster als eigenen Schlüssel;
der Minutenlauf plant und startet neu. Die Markierungsdatei wird nicht
mehr geschrieben. Eine Datei im Stil von 2.6.3 wird bei der ersten
Messung umgeschrieben, das Fenster bleibt. Zwei Mechanismen wären zwei
Wahrheiten.

**Mitteilen (2.7.5).** Kein neuer Kanal: Einträge im Log jedes
Mandanten auf dem Knoten, der Plan und die Schutze an den drei Orten
des Pflegestands, und ein Band am Mandantenort für jeden Angemeldeten.
Vorgänge, die Tür `/platform/care.json` und das Broker-Ereignis sind
spätere Stufen von RFC-0069.

## Deutsche Zusammenfassung (0.2 — Pflegestand des Knotens, §2.6)

**Anlass (05.11.2026, CVE-2026-98432):** Der Kernel-Fix lag auf dem
Internet-Knoten zwei Tage **installiert** und lief nicht, weil seit zehn
Wochen kein Neustart war; vier Knoten hatten gar keine automatischen
Updates; auf einem Knoten war das Auto-Update-Paket von Hand installiert
und tat nichts, weil der Schalter fehlte, den das Paket setzen soll.
Lauter Tatsachen auf der Maschine — und die Plattform hat keine davon
gesagt. Jörgs Entscheidung: „Eine Prüfung mit Empfehlung sollten wir in
oaap aufnehmen.“ Das ist §2.6.

**Die Messung (2.6.1)** macht jeder Knoten selbst, auf der Maschine, nie
aus einem Container: laufender Kernel und neuester installierter Kernel
**derselben Bauart**; daraus **Neustart nötig** — durch Vergleich, **nie
aus der Markierungsdatei** (die schreibt ein Hook, der nur mit dem
Auto-Update-Paket kommt; ohne das Paket heißt „keine Markierung“ gar
nichts — oaapx02). **Automatische Updates** als ein Urteil aus **drei**
Teilen (Programm da, Schalter gesetzt, Zeitgeber aktiv — das Paket allein
setzt den Schalter nicht), plus letzter Lauf. **Neustart-Fenster** (aus
oder Uhrzeit). **Gateway-Listener**: handeln sie Multipath TCP aus
(sollen sie nicht, `oaap.core.gateway` 0.2.18). Und der **Zeitpunkt** der
Messung — direkt nach einem Neustart beschreibt ein alter Wert den alten
Kernel.

**Drei Orte, eine Messung (2.6.2):** `oaap status` druckt den Pflegestand
als eigenen Block, je eine Zeile Kernel / Auto-Updates / Gateway, **mit
der Empfehlung als Text** („Neustart nötig — läuft 6.12.111, installiert
6.12.115: `sudo systemctl reboot` in einer ruhigen Stunde“). Das Portal
zeigt dem `server_admin` ein Band mit denselben Zeilen auf der
App-Übersicht und der Gesundheitsseite, nur ihm — ein Mandanten-Admin
kann an einem Kernel nichts tun (Mandanten über einen geplanten Neustart
informieren ist D4 des späteren RFC). Der Flottenstatus trägt die Fakten
als Block `host` (0.5). Alle drei lesen **dieselbe Datei**
(`host-care.json` neben der Registry), keiner misst selbst — also können
sie sich nicht widersprechen. Die Datei frischt der Minutenlauf auf, wenn
sie älter als zehn Minuten ist, jedes Update, und `oaap node care` auf
Zuruf.

**Zwei Einstellungen, die die Plattform schreibt (2.6.3)** — in einer
**eigenen Datei** (`/etc/apt/apt.conf.d/52oaap-care`), nie in denen der
Distribution: `sudo oaap node care auto-updates on` installiert das
Auto-Update-Programm **und schreibt den Schalter selbst**; es ändert
**keine Quellen** — nur die Sicherheitsquelle der Distribution wird
automatisch eingespielt, die Raspberry-Pi-Kernelquelle bleibt bewusst
draußen (Jörg, 05.11.). Der Installer macht das auf jedem neuen Knoten;
ein aktualisierter Knoten bekommt es nur **gesagt**, nicht heimlich
eingeschaltet. `sudo oaap node care reboot-window 04:15 | off`: Mit
Fenster startet der Knoten sich zu dieser Uhrzeit selbst neu — **nur
wenn** ein neuerer Kernel installiert ist als der laufende, auch mit
angemeldeten Benutzern (ein Knoten ist kopflos; eine vergessene Shell
darf keinen Sicherheitsfix aufhalten). **Ab Werk aus**: Wann ein Knoten
neu startet, entscheidet der Betreiber je Knoten (nach dem Backup, D1).
Und die Lehre von oaapx02: Der Mechanismus der Distribution startet nur
neu, wenn die **Markierungsdatei** da ist — und die schreibt ein Hook
nur, wenn das Auto-Update-Programm selbst einen Kernel einspielt. Mit
gesetztem Fenster schreibt darum die Messung die Markierung selbst,
sobald der Vergleich „Neustart nötig“ sagt.

**Nicht in 0.2** (spätere Stufen, je ein eigener RFC): Abgleich gegen
Sicherheitsmeldungen, ein Benachrichtigungsweg, Neustart-Schutz je
Instanz und Dringlichkeitsstufen (D2–D5 vom 05.11.). 2.6 ist die
Messung, auf der das alles stehen wird.

## Nachtrag 0.1.3 — das Programm, das sich selbst ersetzt

Ein Update-Programm ist der einzige Fall, in dem ein Programm sich
austauscht, während es läuft. `sudo oaap update` führt die Fassung aus,
die beim Tippen des Befehls auf der Platte lag — die **alte**. Alles
nach dem Kopieren der neuen Dateien ist immer noch der alte Ablauf.

Das hat eine Folge, die niemand von allein sieht: **Ein Reparatur- oder
Migrationsschritt, den eine neue Fassung ins Update-Programm schreibt,
wird von genau dem Update übersprungen, das ihn mitbringt.** Und danach
nie mehr — denn beim nächsten Lauf gibt es nichts zu installieren, und
das Programm steigt vorher aus.

Auf oaap-demo ist das am 09.08.2026 passiert: Der Knoten sprang von
0.1.18 auf 0.1.26 und bekam weder den Abgleich der Store-Quellen noch
die Reparatur der Deploy-Worker-Unit. Beides war geschrieben, geprüft
und ausgeliefert. Der Knoten hat es nur nie ausgeführt — und **nichts
hat das gemeldet**. Das ist die unangenehmste Form eines Fehlers: Die
Arbeit ist getan, der Nachweis sieht gut aus, und im Feld wirkt sie
trotzdem nicht.

Zwei Regeln, beide tragend:

1. Die Schritte liegen **außerhalb** des Update-Programms und werden
   **aus dem installierten Verzeichnis** aufgerufen — also aus dem
   neuen Stand.
2. Sie laufen **auch dann**, wenn es nichts zu installieren gibt. Nur
   das heilt einen Knoten, der einen Schritt bereits verpasst hat.

Dazu die Bedingungen, ohne die Regel 2 lästig würde: Jeder Schritt muss
wiederholbar sein und schweigen, wenn nichts zu tun ist. Und ein
Schritt, der scheitert, darf den Update-Lauf nicht abbrechen — er wird
gemeldet, das Update bleibt stehen.

Das „Nichts geändert"-Versprechen bleibt bestehen, aber es meint jetzt
präzise, was es meinen sollte: kein Code installiert, kein Image gebaut,
kein Container neu gestartet. Über den Zustand des **Knotens** hat es
nie eine Aussage gemacht.

## Deutsche Zusammenfassung (0.10 — Anfragen durch die Knotentür)

Durch dieselbe Tür, durch die der Knoten seinen Neustart als Vorgang
ankündigt, schreibt er jetzt auch die **Anfrage eines Mandanten an den
Betreiber** (`object: request`, `from` nennt Mandant und Person) und
liest mit `op: read` Stand und Antworten zurück – nie interne Einträge,
nur an eigenen Vorgängen.

## Deutsche Zusammenfassung (0.11 — Plattenplatz freigeben, §2.10, RFC-0128)

Der Knoten gibt Images frei, die er nicht mehr braucht: **A** den
Build-Cache, den kein Image mehr teilt, und verwaiste Schichten; **B** ältere
Versionen eines Images, das er selbst gebaut hat – es bleiben je App das
laufende Image, das `-prev` eines Neubaus und die vorige Version; **C** Images
ohne Instanz nach 7 Tagen, gezählt ab dem ersten Lauf, der sie so sah;
**D** fremde Images nie von selbst, nur einzeln durch den Server-Admin (ein
Basis-Image sagt dazu, dass ein Neubau es neu lädt); **E** Daten nie. Nie
angefasst wird, was ein Container benutzt (auch ein schlafender), was eine
Instanz zum Start braucht und was jünger als ein Tag ist.

**Wann:** nachts nach der Sicherung (ohne Sicherung ab 3 Uhr), bei Druck
**vor** der Mail „Platte fast voll“ bzw. der Vorhersage (höchstens alle 6
Stunden – die Mail sagt dann, was es gebracht hat, und nennt noch übrige
fremde Images), von Hand mit `oaap node care space [--dry-run]` oder im Portal
auf der Seite **Platz**. Jeder Lauf steht im Protokoll des Knotens, der
Wochenbericht bekommt eine Zeile „Platz freigegeben“. **journald** ist auf
2 GB begrenzt (eigene Drop-in-Datei).

Wichtig gemessen: Auf Docker 29 räumt `docker builder prune -a --filter
until=…` gar nichts; `docker builder prune -f` gab auf oaap-test 66 GB frei.

## Deutsche Zusammenfassung (0.12 — die wartenden Pakete, RFC-0139 Stufe 1)

Die Server-Pflege zählt jetzt, was `apt list --upgradable` anbietet: wie
viele Pakete warten, davon Sicherheitsupdates, davon Docker (an den
Paketnamen erkannt), der Rest. In der Pflegedatei stehen nur Zahlen. Das
steht als Zeile in `oaap status` und auf der Gesundheitsseite, kommt als
tägliche Erinnerung `host.updates` an die Admins des Knotens, solange etwas
wartet, und als Zeile in den Wochenbericht. `sudo oaap node care upgrade
--dry-run` zeigt die Namen mit alter und neuer Version und sagt, wie viele ein
Update nähme – Docker nur mit `--docker`, weil dabei alle Apps etwa eine Minute
weg sind. Eingespielt wird noch nichts über die automatischen
Sicherheitsupdates hinaus.

## Deutsche Zusammenfassung (0.13 — Einspielen auf Wort des Admins, RFC-0139 Stufe 2)

`sudo oaap node care upgrade [--docker]` spielt die wartenden Pakete ein:
zuerst die Paketliste auffrischen, dann Sicherheits- und sonstige Updates,
Docker nur mit `--docker`. Der Lauf hat eine eigene Unit `oaap-upgrade` und
überlebt so eine abgebrochene SSH-Sitzung. Zuerst kommt eine Sicherung; schlägt
sie fehl, wird nichts eingespielt. apt darf nur aktualisieren, nie entfernen
(`--no-remove`), und behält die vorhandenen Konfigurationsdateien. Danach wird
geprüft, ob alle Container wieder laufen (bis zu fünf Minuten); fehlende
werden genannt. Ergebnis: Zeile im Audit-Protokoll, eine Meldung
`host.upgraded`, neue Messung der Server-Pflege. Ein neuer Kernel löst keinen
sofortigen Neustart aus — das übernimmt die vorhandene Neustartplanung.

## Deutsche Zusammenfassung (0.14 — Abschnitt „Updates“ im Portal, RFC-0139 Stufe 3)

Auf der Gesundheitsseite gibt es für den Server-Admin an der Adresse des
Knotens den Abschnitt „Updates“: die wartenden Pakete nach Art gruppiert, einen
Haken „Docker mit aktualisieren“ (nur wenn Docker-Pakete warten) und „Jetzt
einspielen“ mit Rückfrage. Der Knopf schickt einen Auftrag über den Spool;
der Knoten prüft Rolle und Person aus dem eigenen Benutzerverzeichnis und
startet denselben Lauf wie `sudo oaap node care upgrade` — Sicherung, eigene
Unit, Prüfung, Meldung. Während des Laufs zeigt der Abschnitt das Ende des
Protokolls und lädt sich neu. Mandanten sehen den Abschnitt nie; die
Paketnamen stehen nur in `apps/upgrade.json`, nicht in der Pflegedatei.

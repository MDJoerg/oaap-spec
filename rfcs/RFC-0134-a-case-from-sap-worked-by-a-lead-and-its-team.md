# RFC-0134: A Case From SAP, Worked by a Lead and Its Team of Specialists

- **Status:** **Accepted (2026-11-26)** — D1–D9 decided by Jörg one at a time,
  eight as recommended; D8 with the random sample (b) (§10).
  **Stage 0:** M1, M2 and M3 measured 2026-11-26 (§12); M4 (SAP sends the
  POST) confirmed by Jörg 2026-11-26. **Stage 1** became gates (RFC-0135, built
  2026-11-26). **Stage 2 built 2026-11-26** (`vorgaenge` 0.22.0, `spezialisten`
  0.7.0, measured on oaap-test, §13). **Stage 3 built 2026-11-26**
  (`vorgaenge` 0.23.0, `spezialisten` 0.8.0, measured on oaap-test, §14).
- **Date:** 2026-11-25
- **Authors:** Jörg (the need: "wir starten einen Prozess aus unserem Chat per
  MCP im SAP … Falls wir mal keine Lösung haben, wollen wir durch KI die
  Recherche und Lösungsfindung machen lassen … per HTTP Post Request im OAAP
  einen Prozess anstoßen … Daraus wird dann im OAAP Tenant ein Vorgang … ein
  leitender Agent, der mehrere spezialisierte andere Agenten mit Teilaufgaben
  betrauen kann"), Claude (design)
- **Depends on:** RFC-0027 (machine principals and API keys), RFC-0061 and
  RFC-0103 (cases), RFC-0067 (agents), RFC-0105 (specialists in cases),
  RFC-0065 (MCP gateway), RFC-0127 (events)
- **Changes (when accepted):** `vorgaenge` (a door for external systems, tasks,
  close by the lead, the review mark); `spezialisten` (the lead); RFC-0105 §9
  (the SAP scenario is replaced by this RFC); nothing in the chat, nothing in
  the platform core
- **First tenant:** `bec`, which already reaches its SAP systems and their MCP
  tools.

## Summary

A person asks an IT-support question in the chat. The chat calls an SAP MCP
tool; SAP answers from what it knows. When SAP knows **no** answer, it cannot
think about it itself — ABAP runs no model. So SAP sends one HTTP POST to the
tenant's case app and gets a **case number back at once** (or its own
reference is stored in the case). The case is the shell around the search for
a solution.

The case is worked by a **lead**: a specialist (RFC-0105) that may give
**tasks** to other specialists, each with its own tools (for example read
access to SAP with its own technical SAP user). Every step, every task and
every result stands in the case, in order, so afterwards one can read who was
called when and why. The lead judges whether the result is there, calls a
person when it is not, writes the solution back into SAP through an MCP tool,
and **closes** the case. The next person with the same question gets the
answer from SAP directly; this flow is not needed again. Cases can be
**marked for review**, so people or a review specialist can check what the
lead did.

Most of this exists. RFC-0105 built specialists with their own agent, reading
through their own view, writing only after a signed approval, consulting
others, and recording every step as an internal entry. This RFC adds four
things: **a door for an external system**, **the lead with tasks**, **closing
by the lead**, and **the review mark**.

## 1. Facts (read 2026-11-25 in `oaap-apps`)

| What | Where | Fits? |
|---|---|---|
| Backend door `/platform/cases/submit`: an app's own backend files a case with `OAAP_CASES_KEY`, gets `201 {number, id}` | `vorgaenge` 0.20.0, RFC-0061 §3.2 | Only for an app **on the node**: the principal must be `instance:<the attested instance>`. SAP is not an OAAP app. No reference, so a repeated POST makes a second case. |
| Node door `/platform/cases/node`: `open` with `ref` (same `ref` again → `200 existing`), `note`, `close` with proof | `vorgaenge`, RFC-0069 | The **shape** we want (reference, idempotent, note, close), but only for `platform:<instance>`. |
| Partner handover `/handover` | RFC-0061 §5 | Needs OAAP on the other side. |
| Machine principal with a key scoped to one instance | RFC-0027 §3.1, §3.3, D5 | Yes: SAP becomes a machine principal whose key reaches only the `vorgaenge` instance of the tenant. |
| Specialist = pinned assistant revision + own agent + own view; runs on `/mine`, writes internal entries, gives back | `spezialisten` 0.6.2, RFC-0105 §2–§4 | Yes, the members of the team. |
| Writing tools only after a person's signed approval; checked by the MCP gateway itself, once | RFC-0105 §7.1, mcp-gateway 0.39 | Yes, for writing the solution into SAP. |
| Consultation: one answer, read-only, never responsible; at most 3 to specialists per case, after 2 specialist answers in a row a person | RFC-0105 §6, `vorgaenge` 0.15 | Close to a task, but too narrow: read-only and one answer. |
| Statuses `answered → closed` with mark `accepted` (only the reporter) or `no_response` (after 14 days) | RFC-0103, `store.py` | The lead may not close today. |
| Light per queue sent as `X-OAAP-Light` to both gateways | RFC-0105 D9 | Yes. |

## 2. The flow

```
Chat ── MCP ──► SAP: known answer? ── yes ──► answer in the chat
                      │ no
                      ▼
        POST /api/extern/cases  (key of machine principal "sap-a4h")
        {"ref": "ZSUP-000815", "title": …, "body": …, "reported_for": …}
                      │
                      ▼  201 {"number": "V-2026-0142", "ref": "ZSUP-000815", "url": …}
        case in queue "sap-support"; the lead is its first responder
                      │
        lead: reads, plans, gives tasks ─► specialist "Analyse"   (SAP read, own SAP user)
                      │                 ─► specialist "Recherche" (web, read)
                      │ ◄── each task: one result entry
        lead: enough? ── no ─► next task, or a person (consult / give back)
                      │ yes
        plan "create_solution" in SAP ─► a person approves (signed) ─► written
                      │
        lead closes: "closed by the lead", with the proof
        (optionally marked for review)
                      │
        SAP: GET /api/extern/cases/ZSUP-000815 → status, number, closing text
```

## 3. The door for an external system (`vorgaenge`)

1. **Sender.** Under *Bereiche → Absender* the tenant administrator registers
   an external sender: a machine principal (RFC-0027) of this tenant, a label
   (`SAP A4H`), the queues it may file into (one default), and an hourly limit
   (default 600, like the backend door). The key is issued for this principal
   and **scoped to this `vorgaenge` instance** (RFC-0027 D5), with an expiry.
2. **Filing.** `POST /api/extern/cases`, JSON only:
   `ref` (required, ≤ 120 characters, unique per sender), `title`, `body`,
   `kind` (default `question`), `queue` (only one of the sender's),
   `fields` (flat text pairs, shown as technical fields: system, client,
   transaction, message number), `reported_for` (name and/or e-mail of the
   person who asked in SAP — an **assertion** of the sender, stored under
   `tech.asserted`, never linked to a platform person in this RFC).
   Answer `201 {ok, number, id, ref, url}`. The same `ref` again: `200` with
   the existing case and `"existing": true` — never a second case.
3. **Reading.** `GET /api/extern/cases/<ref>` (or `/n/<number>`): number,
   status, sub-status, mark, and — once closed — the **public closing text**.
   Internal entries are never returned. Only cases of this sender.
4. **Adding.** `POST /api/extern/cases/<ref>/note`: a further public entry
   from the sender (the person in SAP added something). Wakes the lead.
5. Who files is attested by the gateway (`X-OAAP-User` = the machine
   principal, kind `machine`); `vorgaenge` checks it against the registered
   senders. A session reaching the path is not a sender.

The answer to SAP does **not** go through this door: the result goes back as an
MCP call into SAP (§6), which is where SAP keeps knowledge. A push to SAP when
the status changes (an event per RFC-0127, delivered as a webhook) is a later
stage; until then SAP reads.

> **2026-11-26:** §3 and §3a are to be replaced by **gates** (RFC-0135, draft):
> the sender list becomes the gate's accesses; `ref`, reading by `ref` and the
> note move to the gate. Stage 1 of this RFC waits for RFC-0135.

### 3a. One door for every trigger (added 2026-11-26)

SAP is the first sender, not the only one. Jörg (2026-11-26): the trigger can
come from the chat, from a flow tool such as Node-RED (idea I-74), from a web
form — "wir brauchen aber eine einheitliche Vorgehensweise und das sind unsere
Vorgänge". So the door of §3 is written for **any** sender, not for SAP:

- an **external system** (SAP) as a machine principal, as above;
- an **app on the node** (a Node-RED instance, a form app) through the same
  `ref`, read and note semantics — today's backend door (`OAAP_CASES_KEY`)
  gains `ref` and reading, so an app does not need a second key;
- the **chat**, which already files through the MCP door of `vorgaenge`
  (`create_case`), gains the same `ref`.

Whatever filed the case, the lead, the tasks, closing and review (§4–§8) are
the same. The case is the one shape every automated piece of work takes in a
tenant; the trigger only decides who is the reporter.

## 4. The lead (`spezialisten`)

A lead is a specialist (RFC-0105 §2) with the switch **„leitet“**. It is the
**first responder** of the queue (RFC-0105 §3.1), so it becomes responsible for
every new case there. It keeps everything a specialist has — its own agent, its
own view, its limits, its pinned revision — and gets three more tools in its
run:

| Tool | Does |
|---|---|
| `auftrag` (task) | gives one task to a named specialist of its team: what to find out, what result is expected. The run ends with sub-status `waiting_task`; the result wakes it. |
| `abschliessen` (close) | closes the case (§7) with a closing text and the proof. |
| `pruefen_markieren` (mark for review) | sets the review mark with a reason (§8). |

Its **team** is a list on the lead: the specialists it may task. A person of
the queue can always be asked through the existing consultation, and a lead
that is stuck **gives back** to the queue's people exactly as a specialist does
today (RFC-0105 §7.3).

The lead's prompt is the assistant revision it names; what it decides is what
the model decides. What it **may** decide is fixed by the platform: the tools
above, the limits (§5), the approval for writing (§6), and the rule for closing
(§7).

## 5. Tasks (`vorgaenge`)

A task differs from a consultation in two points: the tasked specialist uses
**its whole view** (reading freely; writing only with approval, as always), and
it may take **several steps** within its own run limits. Like a consultation it
writes exactly **one result entry**, is never responsible, and is recorded in
`involved` as `tasked`.

- A new entry type `task` (the lead's order, internal) and `task_result`
  (internal, bound to the task). Both carry the assistant revision and the run.
- **No sub-cases.** Everything stays in one case, so the chronology is one list.
- **Depth one.** A tasked specialist cannot give tasks; it can consult a
  person.
- **Limits per case** (tenant settings, per lead only lower): 8 tasks, 1 task
  running at a time (D4), and the existing run limits. When a limit is reached
  the lead learns why and must close, mark or give back.
- The task's text and every result are passed to the next model as **quoted
  data**, never as instructions (RFC-0105 §8): text from SAP and from other
  models is untrusted.

## 6. SAP rights and writing back

- **Every specialist that touches SAP has its own technical SAP user** (RFC-0105
  D1): in the tools gateway one SAP MCP server entry per SAP user, in the
  specialist's own view. SAP's own authorisation and change documents then say
  which agent did what; the case says why.
- Acting with **the rights of the responsible person** (principal propagation
  into SAP) is not part of this RFC (D5).
- Writing the solution into SAP (for example `create_solution`) is a writing
  tool: a **plan** in the case, a **signed approval** by a person of the queue,
  executed once by the gateway (RFC-0105 §7.1). A tenant may later lift the
  approval for exactly this tool and this lead (RFC-0105 D4, tenant
  administrator only, logged) — D6.

## 7. Closing by the lead

Today only the reporter accepts a solution (`accepted`), or the case closes
after 14 days without an answer (`no_response`). Here the reporter is a
machine. The lead may close a case **only** when:

1. the case came through the door of §3 (reporter is an external sender), and
2. its closing names the **proof**: the entry of the executed write into SAP,
   or — if nothing had to be written — its statement why, in which case the
   case is **marked for review automatically**.

The case goes to `closed` with the new mark **„durch die Leitung“**
(`closed_by_lead`). The closing text is public: it is what SAP reads (§3.3).
A case a person reported keeps RFC-0103 unchanged. A person can reopen a case
the lead closed; the lead never reopens one a person closed (RFC-0105 §2).

## 8. The review mark

A case can carry the mark **„zur Prüfung“** with a reason. It is set by:

- the lead, through its tool, when it judges so;
- the platform, without asking the lead: closed without any write; a limit
  reached; a write that ran under a lifted approval; and a **random sample** of
  the cases the lead closed (D8: share per queue, a tenant setting, default 10 %);
- a person of the queue, by hand.

Marked cases have their own list in the queue. A **review** is an entry type
`review` with the result **„in Ordnung“** or **„Nacharbeit“** and a text; it is
written by a person or by a specialist named as reviewer (read-only, one entry,
like a consultation). „Nacharbeit“ reopens the case and wakes the lead. The lead
can leave comments for the reviewers as internal entries, as it can today.

## 9. Where the conversation of the agents lives

In the case. Every order, every result, every tool call (folded), every
approval and every review is an internal entry with author, assistant revision,
run and time. Read top to bottom it is the "multi-agent chat"; filtered by
author it shows who was called when. The chat app shows the case as a link and
a coloured dot (RFC-0103) — it does not hold a second copy (D9).

## 10. Decisions

Each with a recommendation; to be decided one at a time.

- **D1 The door for SAP and other triggers.** (a) a new door in `vorgaenge`
  for registered external senders (machine principal, key scoped to the
  instance, `ref` idempotent), and the same `ref` semantics on the backend door
  and the MCP door, so every trigger files the same way (§3a) (recommended);
  (b) a small OAAP app (for example Node-RED) as the only relay that uses the
  backend door; (c) widen the backend door to machine principals.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D2 What SAP gets back.** (a) the number at once, then it reads the status by
  `ref`; the solution itself goes into SAP through the MCP write (recommended);
  (b) additionally a webhook to SAP on every status change, in the first stage.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D3 The lead.** (a) a specialist with the switch „leitet“ and a team list
  (recommended); (b) a separate orchestrator app.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D4 Tasks.** (a) a new entry pair `task`/`task_result`, whole view of the
  tasked specialist, one result, depth one, one task at a time, 8 per case
  (recommended); (b) the same with tasks running in parallel; (c) sub-cases per
  task.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D5 Whose SAP rights.** (a) a technical SAP user per specialist, one SAP MCP
  server entry per user (recommended); (b) the responsible person's rights
  through principal propagation — an RFC of its own.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D6 Writing the solution into SAP.** (a) always a signed approval by a person
  in the first stages; lifting per tool and lead only later and by the tenant
  administrator (recommended); (b) lifted from the start for the solution tool.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D7 Closing.** (a) the lead closes cases from external senders with proof,
  mark `closed_by_lead`; persons as reporters unchanged (recommended); (b) the
  lead only proposes, a person closes.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D8 The review mark.** (a) set by the lead, by fixed platform rules and by
  persons; reviewed by a person or a reviewer specialist; „Nacharbeit“ reopens
  (recommended); (b) the same plus a random sample (N % of closed cases);
  (c) persons only.
  → **Decided 2026-11-26: (b)** (Jörg): (a) plus a random sample of the cases
  the lead closed; the share is a tenant setting per queue, default 10 %.
- **D9 Where the agents' conversation lives.** (a) in the case only, the chat
  links to it (recommended); (b) additionally a chat conversation per case.
  → **Decided 2026-11-26: (a)** (Jörg).

## 11. Stages

- **Stage 0 — measure in `bec`** (before anything is built):
  1. a machine principal with a key scoped to the `vorgaenge` instance reaches
     a path of that instance from outside, and `vorgaenge` sees
     `X-OAAP-User` with kind `machine`;
  2. a specialist's agent with its own view reaches the SAP MCP read tools in
     `bec` through the tools gateway, with a technical SAP user of its own;
  3. a model in `bec`'s AI gateway carries a run of ten tool steps (the model
     `lokal` did not, RFC-0105 §13);
  4. SAP can send the POST (destination with TLS and bearer key) — Jörg's side.
- **Stage 1 — the door** (§3): senders, filing with `ref`, reading, adding.
- **Stage 2 — the lead and tasks** (§4, §5). Built 2026-11-26 (§13).
- **Stage 3 — closing and review** (§7, §8). Built 2026-11-26 (§14).
- **Stage 4 — end to end in `bec`** with a real unknown question: filed by SAP,
  worked by the lead and two specialists, the solution written into SAP after
  approval, closed; the same question again is answered by SAP without a case.

Tests per stage as in RFC-0105 §11: the real `vorgaenge` in its own process, a
fake model and a fake MCP server; then a measurement on `oaap-test` (tenant
`vuebung`), then `bec`.

## 12. Stage 0 measured (2026-11-26)

**M1 — a machine key at `vorgaenge`** (oaap-test, tenant `vuebung`, then `bec`
read-only on oaapx01; probe principal `rfc134-probe`, key scoped to the
`vorgaenge` instance, revoked right after):

| Call with the machine key | Answer |
|---|---|
| `GET /`, `GET /api/spez/turn` | 200; the app sees the principal as an ordinary user id |
| `POST /platform/cases/submit`, `/platform/cases/node` | 403 from the gateway ("limited to instance …") |
| `POST /handover` | 403 from the app ("no partner registered for this key") |
| MCP door: `initialize`, `tools/list` | 200, all tools listed |
| MCP door: `create_case` (oaap-test only) | **200, case V-2026-0015 created** |

Findings:
1. **The app cannot tell a machine from a person.** The gateway sends the same
   identity headers for both (`X-OAAP-User`, `-User-Id`, `-Roles`, …); there is
   no kind. So the sender check of §3 must be by **user id against the list of
   registered senders** in `vorgaenge` — exactly what D1 (a) says.
2. **A door for machines exists already, unnamed:** any principal of the tenant
   with role `user` and a key on the instance can file a case through the MCP
   door today — without `ref`, without a sender list, into the default queue.
   That is within the tenant's rights (a user may report), but it is the
   unregistered twin of §3. Stage 1 therefore builds §3 on the same store
   function as `create_case` and gives the MCP door the same `ref` (§3a).

**M3 — ten tool steps** (`bec-models`, alias `claude-sonnet-5-5`, own key,
budget 300 000 tokens, revoked right after; fake tools of an SAP authorisation
case, SAP not touched): **14 tool calls in 5 rounds, 17 s, 15 375 tokens, 0
malformed calls**. The model checked all four roles of the user one by one,
read SU53, the object's fields and the org levels, searched known solutions
and roles, and reported the right cause (`M_BEST_EKO`, ACTVT 01, EKORG 1000)
through the reporting tool. It **called tools in parallel within a round**
(up to 4) — allowed inside one run; D4 (one *task* at a time) is about
specialists, not tool calls.

**M2 — a specialist with its own SAP user: not measured, one finding first.**
Procedure P takes the SAP user name from a claim of the **person's sign-in**
(`idp.propagate`, written only by an IdP login; `propagate.backend_user`). An
agent or machine principal has no IdP sign-in, so P refuses it ("no backend
user is known") — by design: RFC-0065 D8 forbids a technical fallback for a
*person*. D5 (a) needs one of:
- (A) a **fixed propagation claim on the agent principal**, set by the tenant
  administrator (for example `sap_user=OAAP_SPEZ_ANALYSE`), and the same P
  chain as for persons — a platform change; not a fallback, because the agent
  never acts for a person;
- (B) a **separate server entry with basic authentication** for the technical
  SAP user, the password entered by a person.
Both need the SAP user in `a4h` (SU01, read rights on the support services;
for (A) also the certificate mapping). To be chosen with Jörg before M2.

Jörg chose **(A)** on 2026-11-26. Reading the code for it showed that (A)
touches three places, not one:

1. **identity** mints the assertion (`X-OAAP-User-Assertion`) only for a
   *person*, and takes the claims only from the person's sign-in
   (`user_assertion`). A machine principal needs a **fixed claim** on its
   record, set by the operator or tenant administrator (`sap_user` matches
   `[A-Z0-9_]{1,12}` — SAP user names are at most 12 characters), honoured
   only for kind `machine` and never read from a sign-in.
2. **The MCP gateway** passes an assertion to a destination only for a person
   who came through the chat's door (procedure A); a call with a key is refused
   ("mit einem Schlüssel geht es nicht"). And a specialist does not call the
   gateway *as* its agent: it holds a **view key** of the gateway; the agent
   hangs at the **server entry** (procedure T: the entry carries the agent's
   platform key outward to a platform source).
3. So the gateway must **obtain an assertion for the agent** before it calls
   the destination. Today only the platform's forward authentication mints
   one, and only for a request that arrives at the instance.

**D10 How the gateway gets the agent's assertion** (new, to be decided):
- (a) **a reserved platform path** `/platform/assertion` on the gateway's own
  site: the server entry holds the agent's key (limited to the gateway
  instance, as today); the gateway calls its own site with it; the platform
  answers itself — never the app — with an assertion for that principal,
  addressed to that instance, carrying the fixed claim. Connect checks it as
  it checks a person's. (recommended: one new door, owned by the platform,
  the rest unchanged)
- (b) connect accepts the agent's platform key directly at a propagation
  destination, instead of an assertion. Fewer steps, but connect learns a
  second way to know a caller.
- (c) back to (B): a server entry with the technical user's password.
→ **Decided 2026-11-26: (a)** (Jörg). **Built the same day** (reference
0.1.382, `oaap.core.identity` 0.6.15 §2.11.1, mcp-gateway 0.52.0 /
`oaap.ai.mcp-gateway` 0.44.0 §3.10.1): `oaap machine propagate NAME --tenant T
--set sap_user=USER`, identity's `/agent-assertion` behind the site block
`/platform/assertion` (only a key limited to exactly that instance, a machine
of the same tenant with a fixed claim), and a `propagate` server entry that
holds the agent's key and fetches the assertion when no person is on the call
— a person always goes first. Tests: mcp-gateway 593 (+6), reference
`test_propagation` +14 checks, seven reference files green in the Linux
runner. Not rolled out; M2 itself still needs the SAP user in `a4h`.

**M2 measured (2026-11-26, `bec` on oaapx01 0.1.382, `bec-tools` 0.52.1).**
Jörg created the SAP user `ERC_SPZ_TEST` in `a4h`. Set up: machine principal
`spz-test` in `bec` with `oaap machine propagate … --set sap_user=ERC_SPZ_TEST`,
a key limited to `bec-tools` (30 days), held sealed by the server entry
`spz-erc-read` (`destination:sap-a4h/zmcp2/erc/read`, `auth propagate`); view
`spz-test` (ways `key`, read) with the six read tools; a view key as the
specialist would hold it.
- `/platform/assertion` with the agent's key: 200, audience `bec-tools`, `usr
  spz-test`, `prop {sap_user: ERC_SPZ_TEST}`; a client-sent query is ignored
  (still `bec-tools`); no key: 401.
- The catalog of `spz-erc-read` was read **as the agent**: 6 tools.
- With the view key: `get_statistics` and `search_incidents` returned real
  data from `a4h` (769 ms, 293 ms), measured as procedure `P`, outcome `ok`.
- connect's audit: `destination.propagation.issue sap-a4h … backend
  ERC_SPZ_TEST`, actor `spz-test`.

Found on the way and fixed in **mcp-gateway 0.52.1** (pushed on Jörg's word):
the gateway dropped any credential of a `propagate` entry, and refused a
person-kind server in a view that takes keys — both written for persons only.
Now one rule, `needs_person`: X, I, P and U need a person, except P with an
agent's platform key (`oaapk_…`); any other credential on P stays refused.
Tests 596/0.

Open finding: the gateway's usage row has an empty `user_sub` for the agent's
calls (only connect's audit names the agent). A later step should record the
agent (for example `agent:spz-test`) on the row.

**M4 — SAP sends the POST:** Jörg's side, open.

## 13. Stage 2 built (2026-11-26)

`vorgaenge` 0.22.0 and `spezialisten` 0.7.0, on Jörg's word ("2").

**`vorgaenge`.** A task is stored like a consultation (same table, column
`kind = task`), so it reuses the one-answer rule, the wake-up and the
"involved" read right, but it has its own limits and does not count against
the consultation limits (3 to specialists, 2 specialist answers in a row).

| Call | Who | Rule |
|---|---|---|
| `GET /api/spez/case/<n>` | a specialist who may read the case | adds `taskable` (only for the responsible one: every other specialist as name and user id, never a person), `tasks_used`, `tasks_max`, `tasks_open` (tasks addressed to me) |
| `POST /api/spez/case/<n>/task {to, text, run, assistant}` | only the responsible specialist | one open task at a time; at most `VORGAENGE_TASKS_MAX` per case (tenant setting 1–8, default 8); refused after a stop; entry `task` (internal, numbered), sub-status `waiting_task` (set only by a task, not in the status form), target recorded as `tasked` and may read the case while it is open |
| `POST /api/spez/case/<n>/answer {consult: seq, text}` | only the tasked specialist, once | entry `task_result` (internal); with nothing open the case returns to `in_progress` and the lead's turn comes |

Depth one needs no extra rule: a tasked specialist is never responsible, so
it can neither write steps nor give tasks.

**`spezialisten`.** A specialist has the switch **„leitet“**, a **team** (names
of other specialists of this app, checked on save; not itself) and **tasks per
case** (1–8; the smaller of this and the tenant setting applies). The lead's run
gets the tool `auftrag` (to, task) with exactly the team members `vorgaenge`
allows, plus a lead frame; after a task the run ends with `waiting_task`. When
the limit is reached the tool disappears and the frame tells the model to sum
up and give back. A tasked run (`Run.task`) reads the case and the task as
quoted data, uses its **whole view** in several steps within its own run limits,
and writes exactly one result, listing the tools it used. **Deviation from §5,
deliberately narrower:** in a task, a writing tool is not executed and not
planned — the model is told so and describes the needed call in its result; the
lead plans it and a person approves it (§6). One plan per case keeps one
approval path.

**Finding on oaap-test, fixed before release:** `vorgaenge` knows an agent by
its principal's label (here "RFC-0134 Stufe 2: Beauftragter Recherche"),
`spezialisten` by its own name ("Recherche (KI)"). Matching the team by name
left the team empty. The team is now matched by the agent's **user id**
(`spezialisten` learns it from each agent's first `turn`); the model still sees
the names of this app.

**Tests:** `vorgaenge` `test_tasks.py` new (25 checks: rules, limits, stop,
depth one, separation from consultations, what persons and the reporter see);
all ten `vorgaenge` test files green. `spezialisten` +18 checks (lead, wrong
team member, waiting, tasked run with the whole view, a writing tool refused in
a task, one result, the lead reads it and gives back, the reporter sees
nothing); all green. `check-store`, `check-design` clean.

**Measured on oaap-test** (tenant `vuebung`, both apps installed; a second agent
`spez-recherche` with a key limited to the `vorgaenge` instance; both
specialists on the AI gateway's `standard` alias = qwen3 4B on CPU; the lead's
instruction a short playbook; the case delivered from outside through the gate
`sap-support`, process pointed at queue `analyse` for the measurement and back
to `eingang` afterwards):

| What | Result |
|---|---|
| without a playbook (old RFC-0105 instruction) | the lead browsed other cases with its view tools and never tasked; the 10-minute limit ended the run, the case went back to the persons (V-2026-0021) |
| with the playbook, case V-2026-0022 through the gate | lead's first run: one task to Recherche after 80 s, status `waiting_task`, run ended `waiting_task` |
| tasked run | started on the next poll; the model call hit the 180 s timeout; exactly one `task_result` ("no result: … timeout") was written and the case returned to `in_progress` by itself |
| lead's second run | read the result and gave a **second, more precise task** (now naming M_BEST_EKO, ACTVT 01, EKORG 1000) |
| second tasked run, lead's third run | both timed out; the lead's run ended with an error entry and gave back to the persons (status `triage`) |

So the platform side holds end to end with a real gate, real agents, real keys
and a real model: task, waiting, wake-up, one result, limits and give-back. The
**quality of the answers** is not measured: a 4B model on CPU is too slow for a
tasked run with tool schemas. That part belongs to `bec` with the model of M3.

Not yet in this stage: closing by the lead and the review mark (stage 3), and
what Jörg's ideas of 2026-11-26 add (I-77 supervisor per agent, I-78 context
JSON and playbook at the process). The playbook above is the first, informal
form of I-78: the lead's instruction carries the rules of the process.

## 14. Stage 3 built (2026-11-26)

`vorgaenge` 0.23.0 and `spezialisten` 0.8.0, on Jörg's word ("weiter mit Stufe 3").

**Closing (§7).** `POST /api/spez/case/<n>/close {text, proof | no_write}` — only
the responsible specialist; only a case whose reference is a gate delivery
(RFC-0135; this replaces "the door of §3"); nothing open (consultation, task,
plan waiting for approval). The **proof** is the number of an entry in this case:
a tool call that the lead's run executed **after** a person's approval of its
plan, or under a lifted approval, and that did not fail (`spezialisten` now marks
every failed call with `failed`). Without proof, `no_write` must say why; the
case then goes to review by itself. The case becomes `closed` with the mark
`closed_by_lead`; the closing text is a public status entry, so the gate's read
(`GET /gate/<name>/<ref>`) returns it as the answer. A person can still reopen
it; the lead has no reopen tool.

**The review mark (§8).** Stored on the case as a list of reasons; each new
reason is an internal entry `review_mark`:

| Reason | Set by |
|---|---|
| `lead` | the lead's tool `pruefen_markieren` |
| `person` | a person who may triage the queue, form on the case |
| `no_write` | closing without proof |
| `limit` | a run ended at a limit |
| `lifted` | a call ran under a lifted approval |
| `sample` | D8 (b): a random share of the cases the lead closed with proof; per queue, default 10 %, set by the tenant administrator on the queue page |

A **review** is an internal entry `review` with `ok` („in Ordnung“) or `rework`
(„Nacharbeit“, text required); it clears the mark. Rework reopens an ended case;
the lead stays responsible and its turn comes again. Reviewers: persons who may
triage the queue, and a **reviewer specialist** per queue (queue page). The
reviewer specialist gets marked cases only when nobody works on them any more
(ended or given back), never cases it closed or is responsible for, reads them
only while marked, has read tools only and gives exactly one verdict per mark
(tool `pruefung_abgeben`); without a clear verdict (limit, no tool call, error)
it writes `none` ("no verdict"), the mark stays and the persons review. Nobody
reviews their own work. The overview has the view „zur Prüfung“, including
ended cases. Mark and review are internal: the reporter (the other system) sees
neither.

**Tests:** `vorgaenge` `test_close_review.py` new (52 checks: who may close,
gate only, proof rules including "approved before executed" and "failed is no
proof", the closing text as the gate's answer, every automatic reason, the
sample with a fixed roll, marks by lead and person, reviewer rules, rework
reopens and wakes the lead, "no verdict", the queue setting, what the reporter
sees); all eleven `vorgaenge` test files green. `spezialisten` +14 checks (the
lead gets `abschliessen` only on a gate case, the proofs in its frame, a wrong
proof refused with the reason from `vorgaenge`, closed with the right one, the
lead marks and goes on, the reviewer's frame and tools, write tools never run in
a review, rework, "no verdict"); all green. `check-store`, `check-design` clean.

**Measured on oaap-test** (2026-11-26, tenant `vuebung`, same setup as §13:
lead „Analyse (KI)“, reviewer specialist „Recherche (KI)“ for queue `analyse`,
both on qwen3 4B on CPU; sample 100 % for the measurement; cases delivered from
outside through the gate `sap-support`; the persons' part — answering the lead's
consultations and approving its plan — done with the same store functions the
forms call, as a test person):

| What | Result |
|---|---|
| V-2026-0023 (ST3-A): plan `comment_case`, approved with a signature | executed by the next run (#132); the door lists it under `proofs` |
| the lead's tool `pruefen_markieren` | used by the model on its own; reason `lead` |
| close while a consultation is open (real door, agent key) | refused: "Eine Rückfrage oder ein Auftrag ist noch offen." |
| run limit (3 runs per case) | automatic reason `limit`, case given back |
| reviewer on V-2026-0023 | picked it up as soon as nobody worked on it; the model call timed out → `none` ("no verdict"), the mark stayed |
| V-2026-0024 (ST3-B): the lead closed **by itself** with `abschliessen` without proof | `closed_by_lead`, automatic reason `no_write`; `GET /gate/sap-support/ST3-B` returns the closing text as `answer` |
| reviewer on V-2026-0024 | the model wrote the `pruefung_abgeben` call ("in_ordnung") as **text**, not as a tool call → counted as `none`, correct by the rule |
| V-2026-0023 reassigned to the lead, close through the real door with proof #999 / #132 | #999 refused ("belegt nichts"); #132 accepted, `closed_by_lead`; the gate returns the closing text; the internal comment #131 never reached the gate |

So the platform rules hold end to end with real keys, a real gate and a signed
approval. **Not reached on oaap-test:** the model closing *with* proof by itself
(it consulted a person and tried tasks under names from `vorgaenge` instead of
its team list, then hit the run limit) and the random sample (both cases were
already marked; the sample only draws unmarked cases). A 4B model is not enough
for the lead or the reviewer; the quality belongs to `bec` (Sonnet, M3). Two
small findings, **fixed in `spezialisten` 0.8.1**: the lead's case data showed
team members under their `vorgaenge` labels, which tempted the model to use
those names -- the run now translates labels into its own names (matched by the
agent's id), the frame names the team explicitly, and a task addressed to a label
reaches the same specialist; and small models sometimes write a tool call as text
-- the run now reads such a call for a tool it offers anyway (`{"name", "arguments"}`,
also inside `<tool_call>` or a JSON fence, `name {...}`, `name({...})`) under the
same rules as a real call. Not in this stage: the supervisor per agent
and the context JSON from Jörg's ideas I-77/I-78.

## Non-goals

- Linking `reported_for` to a platform person (the person sees the case in the
  chat) — later, needs a rule for trusting the sender's assertion.
- Principal propagation into SAP (D5 b).
- Parallel tasks and sub-cases (D4 b, c), webhooks to SAP (D2 b).
- A cost budget per case in money; volume limits stay with the AI gateway
  (RFC-0064).

## Deutsche Zusammenfassung

Ein Mensch stellt im Chat eine IT-Support-Frage, der Chat fragt per MCP das
SAP. Kennt SAP **keine** Antwort, schickt es einen HTTP-POST an die App
*Vorgänge* des Mandanten (zuerst `bec`) und bekommt **sofort die
Vorgangsnummer**. Seine eigene Referenz-ID steht im Vorgang, und derselbe
Aufruf noch einmal legt keinen zweiten Vorgang an. Der Vorgang ist die Hülle
der Lösungssuche.

Ein **leitender Spezialist** wird für jeden neuen Vorgang des Bereichs
verantwortlich. Er gibt **Aufträge** an Spezialisten seines Teams. Jeder
arbeitet mit seiner eigenen Sicht, etwa SAP lesend mit einem eigenen
technischen SAP-Benutzer, und liefert genau ein Ergebnis zurück. Alles steht
chronologisch als interne Einträge im Vorgang. Der Leiter entscheidet, ob das
Ergebnis reicht, und fragt sonst einen Menschen oder gibt zurück. Die Lösung
schreibt er per MCP nach SAP, zunächst immer mit unterschriebener Freigabe
eines Menschen. Danach **schließt er den Vorgang selbst**, mit Beleg und dem
neuen Merkmal „durch die Leitung“. Vorgänge können **„zur Prüfung“** markiert
werden: vom Leiter, durch feste Regeln oder von Menschen. Eine Prüfung ergibt
„in Ordnung“ oder „Nacharbeit“, und Nacharbeit öffnet den Vorgang wieder.

Seit 26.11. (§3a) gilt die Tür nicht nur für SAP: Auch eine Node-RED-Instanz
(I-74), ein Webformular oder der Chat legen Vorgänge mit derselben Referenz-ID
an. Der Vorgang ist die eine Form jeder automatisierten Arbeit im Mandanten.

Vieles steht schon aus RFC-0105. Neu sind vier Dinge: eine Tür für fremde
Systeme, der Leiter mit Aufträgen, das Schließen durch den Leiter und das
Prüfmerkmal. Stufe 0 misst vorher in `bec`, ob der SAP-Schlüssel die Tür
erreicht, ob ein Spezialist mit eigenem SAP-Benutzer die SAP-Werkzeuge
erreicht und ob ein Modell dort zehn Werkzeugschritte trägt.

**Stufe 2 gebaut (26.11., §13):** Vorgänge 0.22.0 und Spezialisten 0.7.0. Ein
Spezialist mit dem Schalter „leitet“ hat ein Team und gibt mit dem Werkzeug `auftrag`
Teilaufgaben, immer nur eine zur Zeit und höchstens 8 je Vorgang (der Mandant kann
weniger einstellen). Der Vorgang steht dann auf „wartet auf Auftrag“. Der Beauftragte
liest mit seiner ganzen Sicht und liefert genau ein Ergebnis. Etwas ändern darf er im
Auftrag nicht: Er beschreibt den nötigen Aufruf, und der Leiter legt ihn zur Freigabe
vor. Das ist bewusst enger als §5. Auf oaap-test lief der Weg echt durch: Tor →
Vorgang → Auftrag → Ergebnis → zweiter, genauerer Auftrag → Zurückgeben. Das lokale
4B-Modell war für den Beauftragten zu langsam (Zeitlimit 180 s). Die Güte der
Antworten misst erst bec. Befund und gleich behoben: Vorgänge und Spezialisten kennen
denselben Agenten unter verschiedenen Namen, also gleicht das Team jetzt über die
Benutzerkennung ab. Offen bleiben Stufe 3 (Schließen, Prüfmerkmal) und aus I-77/I-78
die Führungskraft je Agent und das Kontext-JSON.

**Stufe 3 gebaut (26.11., §14):** Vorgänge 0.23.0 und Spezialisten 0.8.0. Der Leiter
schließt einen Vorgang, den ein anderes System durch ein Tor geliefert hat, selbst – aber
nur mit Beleg (der freigegebene und gelungene Aufruf in diesem Vorgang) oder mit der
Begründung, warum nichts zu ändern war; dann geht der Vorgang von selbst zur Prüfung. Sein
Schließtext ist öffentlich und ist das, was SAP beim Nachfragen liest. Zur Prüfung kommt ein
Vorgang außerdem durch den Leiter, von Hand, bei einer Grenze, bei einem Aufruf ohne
Einzelfreigabe und als Stichprobe (je Bereich, Standard 10 %). Prüfen können die Zuständigen
und ein prüfender Spezialist je Bereich – nie der, der die Arbeit gemacht hat. „Nacharbeit“
öffnet den Vorgang wieder, und der Leiter ist wieder dran. Auf oaap-test gemessen: Die Regeln
halten mit echtem Tor, echten Schlüsseln und unterschriebener Freigabe; der Leiter schloss einmal
selbst ohne Änderung, SAP las den Schließtext am Tor. Das 4B-Modell schloss nicht selbst mit
Beleg und schrieb das Urteil des Prüfers als Text – die Güte misst erst bec. Die zwei Befunde (Labels aus Vorgänge im Verlauf, Werkzeugaufruf als Text) sind in Spezialisten 0.8.1 behoben. Führungskraft je Agent und Kontext-JSON (I-77/I-78) sind nicht dabei.

**Entschieden am 26.11. (Jörg, einzeln):** D1 neue Tür mit Referenz-ID für jeden
Auslöser; D2 sofort die Nummer, SAP fragt nach, Lösung per MCP nach SAP; D3 der
Leiter ist ein Spezialist mit Schalter „leitet“; D4 Aufträge nacheinander,
höchstens 8 je Vorgang; D5 eigener technischer SAP-Benutzer je Spezialist; D6
Schreiben nach SAP zunächst immer mit Freigabe; D7 der Leiter schließt mit
Beleg; D8 Prüfung durch Leiter, Regeln und Menschen **plus Stichprobe** (Anteil
je Bereich, Standard 10 %); D9 das Gespräch der Agenten steht nur im Vorgang.

**Stufe 0 (26.11., §12):** M1: Ein Maschinenschlüssel erreicht `vorgaenge`; die
App sieht ihn wie eine Person (keine Kopfzeile sagt „Maschine“), also prüft die
Tür gegen die Liste der eingetragenen Absender. Schon heute kann jeder Schlüssel
mit Rolle `user` über die MCP-Tür einen Vorgang anlegen, nur ohne `ref` und
ohne Absenderliste; Stufe 1 baut darauf auf. M3: Claude Sonnet in bec machte 14
fehlerfreie Werkzeugaufrufe in 17 s und fand die richtige Ursache. M2: Das
Verfahren P kennt nur Personen (SAP-Benutzer aus der Anmeldung); ein Agent
braucht entweder einen festen Anspruch (A, Plattformänderung) oder einen eigenen
Server-Eintrag mit Benutzer und Passwort (B). Wahl offen, M4 (POST aus SAP) bei
Jörg.

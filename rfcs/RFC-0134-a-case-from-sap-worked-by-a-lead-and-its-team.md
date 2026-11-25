# RFC-0134: A Case From SAP, Worked by a Lead and Its Team of Specialists

- **Status:** Draft (2026-11-25) — D1–D9 open (§10), to be decided one at a time.
  Nothing built.
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
  reached; a write that ran under a lifted approval; (D8: plus a sample of N %);
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

- **D1 The door for SAP.** (a) a new door in `vorgaenge` for registered
  external senders (machine principal, key scoped to the instance, `ref`
  idempotent) (recommended); (b) a small OAAP app as a relay that uses the
  backend door; (c) widen the backend door to machine principals.
- **D2 What SAP gets back.** (a) the number at once, then it reads the status by
  `ref`; the solution itself goes into SAP through the MCP write (recommended);
  (b) additionally a webhook to SAP on every status change, in the first stage.
- **D3 The lead.** (a) a specialist with the switch „leitet“ and a team list
  (recommended); (b) a separate orchestrator app.
- **D4 Tasks.** (a) a new entry pair `task`/`task_result`, whole view of the
  tasked specialist, one result, depth one, one task at a time, 8 per case
  (recommended); (b) the same with tasks running in parallel; (c) sub-cases per
  task.
- **D5 Whose SAP rights.** (a) a technical SAP user per specialist, one SAP MCP
  server entry per user (recommended); (b) the responsible person's rights
  through principal propagation — an RFC of its own.
- **D6 Writing the solution into SAP.** (a) always a signed approval by a person
  in the first stages; lifting per tool and lead only later and by the tenant
  administrator (recommended); (b) lifted from the start for the solution tool.
- **D7 Closing.** (a) the lead closes cases from external senders with proof,
  mark `closed_by_lead`; persons as reporters unchanged (recommended); (b) the
  lead only proposes, a person closes.
- **D8 The review mark.** (a) set by the lead, by fixed platform rules and by
  persons; reviewed by a person or a reviewer specialist; „Nacharbeit“ reopens
  (recommended); (b) the same plus a random sample (N % of closed cases);
  (c) persons only.
- **D9 Where the agents' conversation lives.** (a) in the case only, the chat
  links to it (recommended); (b) additionally a chat conversation per case.

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
- **Stage 2 — the lead and tasks** (§4, §5).
- **Stage 3 — closing and review** (§7, §8).
- **Stage 4 — end to end in `bec`** with a real unknown question: filed by SAP,
  worked by the lead and two specialists, the solution written into SAP after
  approval, closed; the same question again is answered by SAP without a case.

Tests per stage as in RFC-0105 §11: the real `vorgaenge` in its own process, a
fake model and a fake MCP server; then a measurement on `oaap-test` (tenant
`vuebung`), then `bec`.

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

Vieles steht schon aus RFC-0105. Neu sind vier Dinge: eine Tür für fremde
Systeme, der Leiter mit Aufträgen, das Schließen durch den Leiter und das
Prüfmerkmal. Stufe 0 misst vorher in `bec`, ob der SAP-Schlüssel die Tür
erreicht, ob ein Spezialist mit eigenem SAP-Benutzer die SAP-Werkzeuge
erreicht und ob ein Modell dort zehn Werkzeugschritte trägt. D1–D9 sind offen
und werden einzeln entschieden.

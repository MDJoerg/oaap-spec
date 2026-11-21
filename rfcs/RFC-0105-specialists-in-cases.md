# RFC-0105: Specialists in Cases — AI Agents That Work a Case in the Background

- **Status:** Accepted (2026-11-19). D1–D11 decided by Jörg as recommended.
  Stage 0 measured 2026-11-20 (§12); stage 1 built and measured 2026-11-20
  (§13, `spezialisten` 0.1.0, `vorgaenge` 0.13.0); stage 2 built and measured
  2026-11-20 (§14, `spezialisten` 0.2.0, `vorgaenge` 0.14.0, `mcp-gateway` 0.34.0);
  stage 3 built and measured 2026-11-20 (§15, `spezialisten` 0.3.0, `vorgaenge` 0.15.0).
  Signed approval and the light per queue (D9) built and measured 2026-11-21 (§16,
  `mcp-gateway` 0.39.0, `vorgaenge` 0.16.0, `spezialisten` 0.4.0). Stage 4 (SAP) open.
- **Date:** 2026-11-19
- **Authors:**
  - Jörg (the scenario, from SAP work): a user describes a symptom in the
    chat, an MCP server looks for known patterns. If nothing fits, SAP
    triggers an assistant specialised in analysis. It researches in the
    background, files a new solution in SAP through MCP and tells the
    user. The run is a "dark chat" one can read afterwards. When the
    assistant gets stuck it asks other assistants or people. In short:
    a ticket process where the ticket is the conversation and the
    participants are people and specialised AIs, so the app `vorgaenge`
    with "AI specialists".
  - Claude: reading of cases, assistants, delegation and the gateways;
    design.
- **Depends on:**
  - RFC-0061, RFC-0103: cases, queues, responsible/assigned, sub-statuses,
    internal comments, the way back into the chat.
  - RFC-0067: an agent is a machine principal with its own assignments,
    never `may_grant`.
  - RFC-0074, RFC-0097: assistants, revisions `assistant@rev`, assistants
    held in the MCP gateway.
  - `oaap.ai.assistants`: writing tools only after confirmation
    (`X-OAAP-Confirmed`), effect class from the gateway (`oaap/effect`).
  - RFC-0068: closed egress. `oaap.ai.gateway` §7: the light.
  - RFC-0104: the chat at its tenant's model gateway without a key
    (`ai_client`), the profile `ki-arbeitsplatz`.
- **Related:**
  - RFC-0032 / `oaap.events.broker`: events as a later wake-up.
  - RFC-0080: distribution lists for notifications.
  - RFC-0098: call ids with consent, log levels.
  - RFC-0101: feedback in the chat; RFC-0102: attachments.
- **Not part of this RFC:**
  - A free group chat in which several AIs talk at once.
  - An agent that creates other agents, changes its own prompt or grants
    rights.
  - Planning across several cases.
  - The SAP side (the MCP server in SAP, the analysis logic). This RFC
    defines only the door SAP knocks on and the way back.

## Summary

Today an assistant works only while a person talks to it in the chat, with
that person's rights. A case is worked only by people. Jörg's scenario
needs both together: an assistant that works a case on its own, in the
background, writes down what it did, asks for help and hands back to a
person when it gets stuck.

The case is the right vessel. It already has one responsible party at a
time, queues with members, internal comments the reporter never sees, sub-
statuses and a way back into the chat. What is missing are three pieces:

1. **A specialist** is a new kind of queue member: an assistant revision
   (`assistant@rev`, RFC-0097) bound to an agent principal (RFC-0067) with
   its own narrow assignments. It runs with its own rights, not with a
   person's. The I-41 rule "an assistant carries no rights" stays true in
   the chat; a specialist is the explicit, separately administered case.
2. **A run.** A small app `spezialisten` notices that a case is now a
   specialist's turn, reads the case as a conversation, calls tools through
   the MCP gateway and the model through the AI gateway, and writes every
   step back as an internal entry. Hard limits per run and per case, a stop
   button, and the run ends whenever it needs someone.
3. **Asking for help without ping-pong.** Exactly one party is responsible.
   Help is a **consultation**: a specialist or a person is asked, answers
   with one entry and never becomes responsible. Writing tools never run on
   the specialist's own word: the run stops at `waiting_approval` and a
   queue member approves the exact call. When the specialist gives up or a
   limit is hit, the case goes back to the queue's people.

The "dark chat" is the case's internal history: model notes and tool calls
as collapsed entries, readable by the queue's members and the tenant
administrator, never by the reporter. The reporter sees only public
entries, and the specialist writes one only with approval (stage 2).

## 1. Facts (read 2026-11-19)

| Place | Today |
|---|---|
| **vorgaenge** 0.11.0 | Queues are RFC-0045 contexts; members per queue kept in the app (RFC-0103 D2). A case has `responsible` (a member) and `assignee` (a delegation for one case), a table `involved`, fixed sub-statuses of `in_progress` (incl. `waiting_test`, `waiting_reporter`), `entries.internal`. An MCP door exists since 0.4.0 (RFC-0074 CS 443). `/mine` lists a person's cases. Machine access per RFC-0027; `cases.submit` door for handovers (RFC-0061 stage 2). |
| **chat** 0.16.0 | The assistant loop: a round is tools first (fresh assertion), then a model turn. Writing tools need the person's confirmation in the dialog; the chat sends `X-OAAP-Confirmed: yes`. Model through the tenant's AI gateway with a client grant (RFC-0104). The loop runs only while a person waits for the answer. |
| **MCP gateway** 0.27.0 | Holds assistants with revisions (RFC-0097), effect class per tool (`_meta` `oaap/effect`, unspecified = write), usage log with `client`, `assistant`, `confirmed`. Whether a machine principal's key can be carried through the gateway into a source app (RFC-0067 §7, RFC-0065 §5.1) is **not measured**; RFC-0067 lists it as open. |
| **identity / authorization** | `oaap authz agent add` creates an agent principal with assignments in one context; `X-OAAP-User-Assertion` stays empty for it, the log names the agent. |
| **broker** | `oaap.events.broker` exists (RFC-0032); `vorgaenge` publishes nothing yet. |

## 2. The specialist

A specialist is a record in `spezialisten`, administered by the tenant
administrator or a queue's key user:

| Field | Content |
|---|---|
| `name` | shown in the case (`Analyse`, `Basis-Check`), unique per tenant |
| `assistant` | `id@rev` in the MCP gateway: prompt, view (the tools it may see), model meaning. Pinned: a new revision is a deliberate change. |
| `principal` | the agent principal (RFC-0067) the specialist acts as; created with `oaap authz agent add`, assignments only in the queues it serves |
| `queues` | where it is a member; it appears in the member list of `vorgaenge` with a marker „KI“ |
| `limits` | per run and per case (§5), defaults from the tenant |
| `public` | may it draft public entries (stage 2), off by default |
| `active` | a switch; off = no new runs, running runs end after their step |

The specialist **never** holds `may_grant`, never changes queue membership,
never approves a call, never consults beyond the limit and never reopens a
case a person closed.

## 3. When a run starts

A run starts when one of these becomes true for an active specialist:

1. A case is created in, or moved into, a queue where the specialist is the
   queue's **first responder** (a queue setting: the specialist takes new
   cases first).
2. A member sets the specialist as `responsible` or `assignee`.
3. A new entry arrives on a case the specialist is responsible for (a
   reporter's answer to `waiting_reporter`, a consultation's answer, an
   approval).
4. The specialist is **consulted** (§6) on any case of its queues.

Stage 1 notices this by asking `vorgaenge` for the agent's `/mine` every
30 s (a tenant setting). Events through the broker follow once `vorgaenge`
publishes them (D3). One case has at most one running run at a time.

## 4. What a run does

1. Read the case through the MCP door of `vorgaenge` as the agent: title,
   body, `fields`, public and internal entries, earlier runs.
2. Build the conversation: the assistant's prompt, then the case as
   **quoted data** (reporter text is never instructions, §8), then the
   specialist's own earlier entries.
3. Loop: tools through the MCP gateway in the assistant's view, then a
   model turn through the AI gateway, until the model ends, a limit is hit
   or a step needs someone.
4. Write back, each as an internal entry with `run` and `assistant@rev`:
   - **note**: model text;
   - **tool**: tool name, arguments, a shortened result, duration, the
     gateway's call id; shown collapsed;
   - **end**: why the run ended (done, needs approval, waiting for a
     consultation, gave up, limit, stopped).
5. Set the case's state (§7).

The run never writes outside the case except through tools of its view, and
never with a writing tool on its own word (§7.1).

## 5. Limits

| Limit | Default | When hit |
|---|---|---|
| model and tool steps per run | 20 | run ends, `end: limit` |
| wall time per run | 10 min | the same |
| tokens per run | from the AI gateway's volume (RFC-0064) | the same |
| runs per case | 10 | the case goes back to the queue's people |
| consultations of specialists per case | 3 | further consultations go to people only |
| specialist-to-specialist answers in a row | 2 | the next turn belongs to a person |

A **stop** button on the case (queue members, tenant administrator) ends the
run after the current step and sets `active` for this case to off until a
person sets it again.

## 6. Consultation

A consultation is a request for one answer, not a handover:

- Written as an internal entry with `@<name>` (a specialist or a member of
  the queue). `vorgaenge` records it in `involved` with role `consulted`.
- A consulted specialist gets one run with the case read-only and may write
  exactly one internal entry. A consulted person sees the case in `/mine`
  and answers with a comment.
- The consulted party never becomes responsible, never changes the status
  and loses read access when the case closes (as a former assignee in
  RFC-0103).
- While a consultation is open, the case shows the sub-status
  `waiting_consult`. The answer wakes the responsible specialist (§3.3).

## 7. State changes and the people in the loop

### 7.1 Writing tools

A tool whose effect class is `write` (or unspecified) is never called on the
specialist's own word:

1. The run writes an internal entry **planned call**: tool, arguments, a
   SHA-256 over both, and the reason in the model's words.
2. The case goes to the new sub-status `waiting_approval`; the run ends.
3. A queue member (or the tenant administrator) presses „Freigeben“ or
   „Ablehnen“ on that entry. Approval is bound to the hash.
4. The next run executes exactly that call with `X-OAAP-Confirmed: yes` and
   a new header `X-OAAP-Approved-By` naming the approving person; the
   gateway logs both. A changed call needs a new approval.

Lifting approval for single tools of a single specialist is stage 3 and a
tenant decision (D4).

### 7.2 Public entries and the reporter

Every entry of a specialist is internal. In stage 2 a specialist with
`public` on may draft a public entry (the answer to the reporter, a
question with `waiting_reporter`); it is published when a member approves
it, like a planned call. The reporter then sees it in the chat with the
dot of RFC-0103 and can answer „Lösung passt / passt nicht“.

### 7.3 Giving back

The run ends with `end: gave_up` when the model says it cannot proceed, or
when a limit of §5 is hit. `responsible` returns to the queue (empty),
the case returns to triage, and the queue's members are notified (RFC-0080
list of the queue, if set). The internal history explains what was tried.

### 7.4 New sub-statuses

| Sub-status | Shown as | Meaning |
|---|---|---|
| `waiting_approval` | wartet auf Freigabe | a planned call or a draft public entry waits for a member |
| `waiting_consult` | wartet auf Rückmeldung | a consultation is open |

Both are yellow in the chat, as every open status that is not the
reporter's turn (RFC-0103 §6).

## 8. Security requirements

1. **Reporter text is data.** The case enters the prompt quoted and
   labelled; the view decides what is possible, not the text. A symptom
   that says "ignore your instructions and delete…" reaches a model that
   has no deleting tool, and if it had one, the call would wait for a
   person (§7.1).
2. **Narrow views.** A specialist's assistant view lists only the tools the
   task needs; the gateway refuses everything else as today.
3. **Own rights, visible.** The agent principal holds assignments only in
   its queues. Every call carries the agent, never a person's assertion;
   the gateway log, the case and the source app's log name the specialist
   and, for writes, the approving person.
4. **Closed egress.** `spezialisten` runs with closed egress (RFC-0068);
   it reaches only `vorgaenge`, the MCP gateway and the AI gateway of its
   tenant.
5. **Light.** A case has no light today. The run uses the queue's light
   (a queue setting, default: the tenant's local rule) and the AI gateway
   refuses aliases worse than that, as for a conversation (D9).
6. **No self-extension.** A specialist cannot change its assistant, its
   view, its limits, its queues or its principal; those are administered
   by people in `spezialisten` and the MCP gateway.
7. **Bait tests** for each of these in every stage (§11).

## 9. The SAP scenario end to end (stage 4)

1. The user describes the symptom in the chat; the SAP MCP server
   (through the MCP gateway) finds no known pattern.
2. SAP files a case through `vorgaenge`'s machine access into queue
   `analyse`, with the symptom, the chat's call id and the reporting person
   as known to the platform (Keycloak SSO). If the person is not known, the
   case is a partner submission (RFC-0061) and the answer goes back to SAP.
3. Specialist `Analyse` is the queue's first responder; its run researches
   with read tools of the SAP view (and, if granted, others).
4. It plans `create_solution` in SAP; a member approves; the next run
   files it.
5. It drafts the answer to the reporter; a member approves; the reporter
   sees it in the chat.
6. Stuck: it consults `Basis-Check` or a person, or gives back.

## 10. Decisions

All eleven decided by Jörg on 2026-11-19 as recommended.

- **D1 Whose rights.** *Recommendation:* the specialist's own agent
  principal (RFC-0067) with assignments only in its queues.
  - Alternative: on behalf of the reporter (delegation with person proof).
    The assertion is short-lived, a background run outlives it, and the
    reporter usually may not file solutions in SAP.
- **D2 Where the run lives.** *Recommendation:* a separate small app
  `spezialisten` (manifest `mcp_client`, `ai_client`, closed egress) that
  uses `vorgaenge` through its MCP door like any other member.
  - Alternative: inside `vorgaenge`. The case app would carry a model
    loop, model access and an agent key.
  - Alternative: inside the chat. The chat is a person's tool and holds
    their history; a background agent there blurs whose work it is.
- **D3 Wake-up.** *Recommendation:* poll `/mine` of the agent every 30 s in
  stage 1; broker events from `vorgaenge` later.
- **D4 Writing.** *Recommendation:* every writing call approved by a queue
  member, bound to a hash; lifting per specialist and tool in stage 3, a
  tenant decision, logged.
- **D5 Public entries.** *Recommendation:* drafts only, published on a
  member's approval; off per specialist by default.
- **D6 Sub-statuses.** *Recommendation:* add `waiting_approval` and
  `waiting_consult` to the fixed list of RFC-0103 D4.
- **D7 Consultation.** *Recommendation:* one answer, read-only, never
  responsible, recorded in `involved` as `consulted`.
- **D8 Limits.** *Recommendation:* the defaults of §5 as tenant settings,
  per specialist lower only.
- **D9 Light of a case.** *Recommendation:* a queue setting, default the
  tenant's local rule; the run's alias must satisfy it.
- **D10 Name.** *Recommendation:* „Spezialist“ (German UI), "specialist"
  (spec). The app is `spezialisten`.
- **D11 Pinning.** *Recommendation:* the specialist names `assistant@rev`;
  every entry records it, so RFC-0097's evaluation per revision also covers
  background work.

## 11. Stages and tests

| Stage | Content | Measured by (bait in brackets) |
|---|---|---|
| 0 | Measure what exists: an agent principal's key through the MCP gateway into `vorgaenge` and one read-only source | `oaap-test`, nothing built; result decides whether RFC-0065 §5.1 must change first |
| 1 | `spezialisten` 0.1.0: specialist record, first responder, poll, run with read tools, internal note/tool/end entries, limits, stop, give back; `vorgaenge`: specialist marker, `run` on entries | a case in a test queue is read, researched and given back with a readable history (reporter never sees an internal entry; a tool outside the view is refused; the 21st step ends the run; stop ends after the step) |
| 2 | Planned calls with approval, `X-OAAP-Approved-By`, draft public entries, `waiting_approval` | a write happens only after approval, exactly as approved (changed arguments refused; a non-member cannot approve; a symptom with injected instructions leads to no call) |
| 3 | Consultation, `waiting_consult`, loop limits, lifting approval per tool | two specialists and a person solve a case together (the 4th specialist consultation goes to people; a consulted specialist cannot change the status) |
| 4 | SAP: a case from `a4h` through machine access, specialist `Analyse`, solution filed in SAP, answer in the chat | the scenario of §9 on `a4h` and `bec` |

## 12. Stage 0 measured (2026-11-20, `oaap-test`, tenant `vuebung`)

**Set-up.** `vuebung-vorgaenge` updated to 0.12.0; queue `analyse` and a test
case `V-2026-0008` reported by a test person; role and collection
„Spez Analyse“ from the template `case_handler`; agent principal
`spez-analyse` with `oaap authz agent-add … --context queue=analyse
--instance vuebung-vorgaenge --days 14`. In `vuebung-mcpgw` a server entry
`vorgaenge-spez` with procedure T (`--auth bearer`, the agent key, address
`http://oaap-gateway-1:8131/mcp`), a view `spez-analyse` (way `key`) with
`list_cases`, `get_case`, `comment_case`, and a gateway key for that view.
The secrets stayed in root-only files on the node.

| Path | Result |
|---|---|
| Agent key directly at the MCP door of `vorgaenge` | 9/9: `tools/list`; `list_cases scope=queues` shows the case in `analyse` (grant from the assignment); `get_case`; internal `comment_case`; the reporter does **not** see the internal note (bait); a case of another queue stays invisible (bait); no key: 303 to the login; a forged key refused |
| Through the MCP gateway, procedure T | 8/8: `initialize`; `tools/list` shows exactly the three approved tools; `list_cases`, `get_case` as the agent; `comment_case` arrives as the agent; a tool outside the view refused by the gateway (`unknown_tool`, bait); no key: 401; the agent's platform key at the gateway: 401 (bait) |

**Findings, and what they change for stage 1:**

1. **The way exists; RFC-0065 §5.1 need not change first.** The agent is an
   ordinary user to `vorgaenge` (role `user`, uid of the agent); its
   assignment decides what it reads. The run reads and writes the case
   **directly** at the door of `vorgaenge` with the agent key, not through
   the gateway.
2. **Through the gateway the agent is bound to the server entry, not to
   the caller.** Whoever holds the view's gateway key acts as the agent.
   Therefore each specialist gets its **own** server entry, view and
   gateway key, held only by `spezialisten`. Carrying the caller's own
   principal per call stays open (RFC-0067 §7).
3. **A key view lets a writing tool through without confirmation.** The
   gateway logged `comment_case` with procedure T, `confirmed` empty. Stage
   1 therefore gives a specialist's view `--max-effect read`, so the
   gateway itself refuses writes; stage 2 adds approved writes
   (`X-OAAP-Approved-By`) at the gateway.
4. **The name in the case is the agent's `--label`.** The entries showed
   „RFC-0105 Stufe 0“ as author. The label of a specialist's agent is its
   shown name (e.g. „Analyse (KI)“).
5. **Model access: an AI-gateway key, not `ai_client`.** The `ai_client`
   door needs a person's assertion like `mcp_client`. `spezialisten` calls
   the AI gateway's public `/v1` with a key of its own per specialist
   (deviation from D2's manifest line `ai_client`).
6. **The assistant revision cannot be read with a key.** The gateway hands
   `assistant@rev` only to a signed-in person. Stage 1 keeps a pinned copy
   in the specialist record (`id@rev`, prompt, model; taken from the
   gateway's export by the administrating person); reading it as that
   person follows.
7. `oaap authz agent-add` still wants the full collection id (RFC-0073
   finding 2), read here from the authorization store.

## 13. Stage 1 built and measured (2026-11-20)

**Built.**

- `spezialisten` 0.1.0 (new app):
  - the specialist record of §2 (name, `assistant@rev` with a pinned copy of prompt and model, three keys never shown again, limits lower than the tenant's `SPEZ_MAX_*`, active switch);
  - a poll every 30 s of `GET /api/spez/turn` per active specialist; a case is due when its last entry is not the specialist's own;
  - the run of §4 with the case as quoted data (`<vorgang>`), tools of the specialist's own read-only view (procedure T) and the model through the AI gateway;
  - steps written as internal `note`/`tool`/`end`; limits (steps, minutes, runs per case); stop detected before each step and inside a step; give back at the end;
  - "Prüfen" checks all three counterparts and registers the agent with `vorgaenge`.
- `vorgaenge` 0.13.0:
  - the queue setting "Erstbearbeitung" (§3.1, also on move);
  - the door `/api/spez/` (`turn`, `case/<n>`, `case/<n>/entry`, `case/<n>/give-back`, JSON only); steps only by the responsible party and always internal;
  - the dark chat collapsed with a „KI“ marker in the tab „Intern“;
  - the stop button (§5).

  Deviation from §4.1: the run reads and writes the case through this JSON door, not through the MCP tools of `vorgaenge`. Those stay as they are for the chat.

**Tests.**

- `vorgaenge/test_spez.py` (first responder, turn, steps, baits: non-responsible, form, reporter, stop, give back, move).
- `spezialisten/test_spezialisten.py`, 26/26, end to end against the real `vorgaenge` in its own process behind a fake platform door, a fake MCP gateway and a scripted model.
  - Baits: reporter text never in the system prompt; a tool outside the view refused; the reporter sees no step; step limit; stop in the middle of a step; a refusing AI gateway; runs per case; a wrong agent key; a key user cannot administer; foreign-origin forms refused.
- Two mutations were caught (case into the system prompt; steps public).
- All earlier tests of `vorgaenge` are green.

**Measured on `oaap-test`** (tenant `vuebung`, apps installed from the working tree, test channel):

| Asked | Answer |
|---|---|
| „Prüfen“ in `spezialisten` | ✓ agent signed in at `vorgaenge` (its uid), ✓ view with 2 tools (`get_case`, `list_cases`), ✓ model `lokal` reachable with the specialist's AI key |
| Queue `analyse` set to the specialist, new case `V-2026-0009` reported | the specialist became responsible (internal entry) |
| Poll and run | the run started 27 s later, 2 model steps, 13 s, end `done` |
| History of the case | internal: a tool step (`list_cases`, refused **by the gateway** because the model invented an argument not in the approved schema), a note, end, give back; status `triage`, responsible empty |
| What the reporter sees (`get_case` as the reporter) | only her own entry `created` |
| Gateway log | `spez-analyse`, `list_cases`, procedure T, `refused` |

**Findings.**

1. **The frame works; the small local model does not.** `lokal` on `oaap-test` invented a tool argument and then wrote a confused note. The run did what it should: the gateway refused, the note was recorded, and the case went back to the people. A real specialist needs a model that handles tools well. That is a choice per specialist; the frame does not change.
2. **The shown name is the agent's label.** The steps showed „RFC-0105 Stufe 0“, the label of the agent from stage 0 (§12, finding 4). A specialist's agent should be created with its shown name as label.
3. **No light check yet (§8.5, D9).** The light of the run is the ceiling of the specialist's AI key (green here). A queue setting for the light follows with stage 2.
4. **Not measured:**
   - a real research task with a capable model;
   - the stop button live (unit-tested end to end only);
   - `spezialisten` in a closed tenant.

## 14. Stage 2 built and measured (2026-11-20)

**Built.**

- `mcp-gateway` 0.34.0: `view set --approval required`. In such a view a key reaches a `write`/`execute` tool only with `X-OAAP-Confirmed: yes` and `X-OAAP-Approved-By`.
  - Without them the gateway refuses with `-32003` and logs `needs_approval` at the door `gateway`.
  - The usage row names the approving person (`approved_by`).
  - Views without the setting behave as before.
- `vorgaenge` 0.14.0:
  - step kinds `plan` (tool and arguments) and `draft` (an answer to the reporter);
  - the hash is computed by `vorgaenge`, never taken from the specialist;
  - the sub-status `waiting_approval`, which never appears in the status form;
  - „Freigeben/Ablehnen“ and „Veröffentlichen/Verwerfen“ for whoever works the queue. Never the plan's author, never twice, never for a plan whose stored arguments no longer match the hash;
  - an approved draft becomes a public comment in the specialist's name with the approving person;
  - after a decision the case is `in_progress` again, and the specialist is due.
- `spezialisten` 0.2.0:
  - a tool whose effect is not `read` is only planned. The effect comes from the gateway's `oaap/effect`; without it the tool counts as writing. The run then ends with `needs_approval` and stays responsible;
  - the next run first executes approved, not yet executed plans of its own, exactly as stored, with both headers, and binds the result to the plan;
  - a rejected plan is never executed; the model reads approvals and rejections in the history;
  - `antwort_entwurf` is offered only when the specialist may draft (D5, off by default).

**Tests.**

- Gateway: 562/562, 7 new.
- `vorgaenge`: all green, 14 new. Baits:
  - the reporter sees neither the plan nor an unpublished draft;
  - the reporter cannot approve, and the specialist cannot approve its own plan;
  - tampered arguments are refused;
  - a second decision is refused;
  - the sub-status does not appear in the form.
- `spezialisten`: 42/42, 16 new. Baits:
  - injected instructions in the case lead only to a plan, never to a call;
  - nothing runs before a decision;
  - an approved plan runs exactly once, with the approving person;
  - a rejected plan never runs;
  - a draft is shown only after approval.
- One mutation was caught: the effect not checked.

**Measured on `oaap-test`** (tenant `vuebung`, test channel). `comment_case` (write) was added to the specialist's view, set to `--approval required`; the specialist's gateway key was raised to `write`.

| Asked | Answer |
|---|---|
| The view lists `comment_case` | with `oaap/effect: write` |
| `comment_case` with the key, no headers / only `X-OAAP-Confirmed` | `-32003`, logged `needs_approval` |
| A plan written through the agent's door into `V-2026-0011` | accepted; case `waiting_approval`; hash 64 hex characters from `vorgaenge` |
| The agent itself posts „Freigeben“ | 400 |
| The tenant administrator approves | 303; the specialist runs ~1 min later |
| The run | executes exactly the approved `comment_case`; the note appears on `V-2026-0009` as the agent, internal; the step is bound to the plan |
| Gateway usage row | `comment_case ok approved_by=probe-admin` |

The first attempt executed the approved call against a key still limited to `read`: the gateway refused it on effect. Nothing was written, and the step recorded the refusal.

**Findings.**

1. **Three settings must agree.** The view's `--max-effect write`, its `--approval required` and the key's `--max-effect write`. The setup text of `spezialisten` names all three.
2. **The local model plans on its own.** After the approved call it planned a second write, through a duplicate view entry the measurement had created by accident. The plan waited, and was rejected. This is the intended behaviour: a weak model can plan nonsense, but it cannot do it.
3. **The approval is an assertion of `spezialisten` at the gateway, checked in `vorgaenge`.** A key holder could set the headers itself. The binding protection is the hash in `vorgaenge` and the fact that only `spezialisten` holds the key. A signed approval from `vorgaenge` that the gateway verifies would close this. That is open, and it needs a shared key between the two apps.
4. **Not measured:**
   - a draft live (unit-tested end to end only);
   - a light per queue (D9), still open.

## 15. Stage 3 built and measured (2026-11-20)

**Built.**

- `vorgaenge` 0.15.0:
  - a table `consults` (one question, one answer) and the entry types `consult` and `consult_answer`, both internal;
  - who may ask: whoever is responsible (a specialist through `/api/spez/case/<n>/consult`, by name), and any person who works the queue (form „Rückfrage stellen“);
  - who may be asked: the queue's members (the list on „Bereiche“) and every specialist. Never oneself, never the reporter, never a second open question to the same party;
  - a specialist is whoever uses `/api/spez/turn`; the app records it (`people.specialist`), for the limits and the choice;
  - the sub-status `waiting_consult`, never in the status form. When the last open question is answered the case returns to `in_progress` by itself, written as „Automatisch“, never in the name of the consulted party;
  - the consulted party reads the case (internal entries included) while it is open, answers exactly once, and never becomes responsible. It cannot write steps, give back, change the status or ask further;
  - `turn` lists open questions to the caller with `consult`; a consulted person finds the case under „Meine“ and answers on the case page;
  - limits (§5): at most 3 consultations of specialists per case, then people only; after 2 answers specialist → specialist in a row since the last person's entry, the next turn belongs to a person.
- `spezialisten` 0.3.0:
  - the responsible run gets a tool `rueckfrage` with the names it may ask. A successful question ends the run with `waiting_consult`; a refusal (a limit, an unknown name) goes back to the model as the tool result, so it can ask a person instead;
  - a consulted run (`Run.consult`) gets its own frame, the question quoted as data, **only the reading tools** of its view, and no draft or question tool. Its single answer ends with the tools it used;
  - D4: the tenant administrator (not `admin` alone) can list tools a specialist may call without approval. The change is written to the app's audit; the call carries `X-OAAP-Approved-By: Dauerfreigabe <person>` and the case entry names the person;
  - approver names in headers are percent-encoded (they were sent raw in 0.2.0; a name outside Latin-1 would have broken the run).

**Tests.**

- `vorgaenge`: all green, 30 new in `test_spez.py`. Baits:
  - a specialist of another queue does not read the case before it is asked, and no longer after it closes;
  - the reporter is not consultable and sees neither question nor answer;
  - the consulted party writes no step (note, plan, end), does not give back, does not change the status, does not ask further, answers only once;
  - only the asked party answers; no second open question to the same party;
  - the third specialist → specialist question in a row is refused, the fourth consultation of specialists is refused, a person can still be asked.
- `spezialisten`: 63/63, 21 new. End to end: two specialists and a person solve a case together. Baits:
  - a writing tool inside a consultation never runs, not even as a plan;
  - the consulted specialist writes nothing but its answer and is never responsible;
  - the refused third question reaches the model with its reason; it then asks the person;
  - nothing runs while the person has not answered;
  - lifting approval needs the tenant administrator.
- Two mutations were caught: the reading filter of a consultation removed, the in-a-row limit removed.

**Measured on `oaap-test`** (tenant `vuebung`, test channel, one agent, local model). 24/24; two checks of the script used the wrong display name of the agent (its label is still „RFC-0105 Stufe 0“) and were re-checked by its uid.

| Asked | Answer |
|---|---|
| A case in `eingang`, outside the agent's queue: the agent reads it | 404 |
| The tenant administrator asks the specialist on the case page | `waiting_consult`; the agent's `turn` lists the question; now it reads the case, not responsible, nobody to ask |
| The specialist's run as consulted party | `answered` after 6 s; exactly one internal entry of the agent; status back to `in_progress` as „Automatisch“; nobody became responsible |
| Gateway during that run | one `get_case`, refused for its arguments (the local model); no writing call |
| The agent afterwards: note, give back, second answer | 409 each |
| The reporter's page | neither question nor answer |
| The specialist (responsible) asks the reporter / a member of the queue | 409 / `waiting_consult` |
| The member finds the case under „Meine“; another person answers | yes / 400 |
| The member answers on the page | `in_progress`; the specialist is due again and runs (`done`) |
| `comment_case` with `X-OAAP-Approved-By: Dauerfreigabe Jörg Prüf` at the real gateway 0.34 | `ok`; usage row `Dauerfreigabe J%C3%B6rg Pr%C3%BCf` |

**Findings.**

1. **The display name of an agent is its label from `agent-add`.** The agent of stage 0 still shows as „RFC-0105 Stufe 0“. Names in `rueckfrage` and on the page come from there; a specialist should get its final label when the agent is created.
2. **The local model answers fluently and wrongly.** As consulted party it claimed an earlier case it had not read (its only tool call failed on arguments). The mechanism held: one internal answer, nothing written. Content needs a tool-capable model, as before.
3. **Not measured live:**
   - two specialists consulting each other (one agent on `oaap-test`; covered end to end in the tests);
   - the limits (3 / 2 in a row) against the live app (store rules, unit-tested);
   - D4 through a model run: the lifted call was made directly with the runner's gateway client.

## 16. Signed approval and the light per queue (2026-11-21)

Closes finding 3 of §14 and D9 (§8.5).

**Built.**

- `mcp-gateway` 0.39.0 (`oaap.ai.mcp-gateway` 0.35.0 §5.6 -- where the setting of 0.34 is
  now written down too): view setting `approval = signed` with an **approval key**
  (`oaap-fk-…`, sealed, never shown again). A writing call of a key needs
  `X-OAAP-Approval`, an HMAC-SHA256 signed approval; the gateway checks signature, tool,
  SHA-256 of the arguments, expiry (at most 30 days) and uses each approval exactly once
  (`approvals_used`). The usage row names the person from the approval. A shared key, not
  a key pair: the standard library offers no production-grade signature, and both apps
  are the tenant's own; the key never leaves the two apps (a file 0600 in `vorgaenge`,
  the vault in the gateway).
- `vorgaenge` 0.16.0:
  - every approval of a planned call carries `token` -- signed with the instance's approval
    key, `jti` = `<instance>:<case id>:<plan>`, valid 7 days; a rejection and a draft carry
    none;
  - *Bereiche → Freigabeschlüssel* (only the `tenant_admin`): the key with instructions for
    the gateway, *Neu erzeugen* (old approvals stop working; logged);
  - **D9:** per queue *Ampel für Spezialisten* (`""` = none of its own, green, yellow, red;
    only the `tenant_admin`, logged); the specialist's door returns it as `queue_light`.
- `spezialisten` 0.4.0: an approved plan is executed with `X-OAAP-Approval` next to the
  headers of stage 2; the queue's light goes as `X-OAAP-Light` to the MCP gateway and the
  AI gateway (both take it as a ceiling, RFC-0101 -- tighten only).

**Deviation (D9):** the RFC said "default: the tenant's local rule". A queue without a
light of its own sends no `X-OAAP-Light`; the ceilings of the specialist's keys apply --
which the tenant sets. The queue's light can only tighten them.

**Tests.** mcp-gateway `test_signed_approval` 20 new (without key, wrong key form, sealed
and never shown; refusals without approval, with only the headers of stage 2, another key,
another tool, other arguments, expired, altered -- nothing sent; one valid approval one
call, the person from the approval; a second use refused; read needs none; back to
`required`); `test_compose` caught the module missing in the Dockerfile; all other gateway
tests green. `vorgaenge` `test_spez_signed` 17 new (light only by the `tenant_admin`, read
by the run; key only for the `tenant_admin`, file 0600; the approval verified with the
gateway's own module, another tool or other arguments fail; a rejection unsigned;
rotation invalidates); all other tests green. `spezialisten` end to end: the executed call
carries the approval, which the gateway's module accepts, and `X-OAAP-Light: green` reaches
both gateways; 65/65.

**Measured on `oaap-test`** (tenant `vuebung`, test channel, `vuebung-mcpgw` 0.39.0,
`vuebung-vorgaenge` 0.16.0, `vuebung-spezialisten` 0.4.0, the setup of §14/§15), 15/15:

| Asked | Answer |
|---|---|
| *Freigabeschlüssel* as `tenant_admin` / as a reporter | shown / 403 |
| View `spez-analyse` `--approval signed`, key through stdin | `freigabe=signed`; the key not in clear text in the database |
| `comment_case` with only `X-OAAP-Confirmed` and `X-OAAP-Approved-By` | `-32003` |
| Queue `analyse` light green | set; the case shows `queue_light: green` to the run |
| Plan through the agent's door, approved by the `tenant_admin` | approval with `token` |
| The specialist's next run | exactly the approved `comment_case`, no error; gateway usage `ok, approved_by=probe-admin, light=green`; the approval in `approvals_used` |
| The same approval again, directly with the view's key | `-32003` „schon benutzt“ |
| AI gateway during the run | two requests with light `green` |

The queue's light was set back to none afterwards; the view stays `signed`.

**Not measured:** an alias stronger than the queue's light refused live (the local alias
is green; the AI gateway's refusal is tested in its own suite); a key rotation live.

**Open:** stage 4 (SAP, §9) -- needs `a4h`/`bec` and Jörg.

## Zusammenfassung auf Deutsch

Heute arbeitet ein Assistent nur, solange ein Mensch im Chat mit ihm
spricht, und zwar mit dessen Rechten. Vorgänge bearbeiten nur Menschen.
Jörgs SAP-Szenario braucht beides zusammen: Ein Assistent bearbeitet einen
Vorgang selbstständig im Hintergrund, schreibt auf, was er tut, holt sich
Hilfe und gibt zurück, wenn er nicht weiterkommt.

Der Vorgang ist dafür das richtige Gefäß. Er hat schon genau einen
Zuständigen, Bereiche mit Mitgliedern, interne Einträge (der „dunkle“ Teil),
Unterstatus und den Rückweg in den Chat. Es fehlen drei Teile:

1. **Der Spezialist** ist ein neues Mitglied eines Bereichs: eine
   Assistenten-Revision (`assistent@rev`) plus ein eigener
   Maschinen-Benutzer (Agent, RFC-0067) mit engen Rechten nur in seinen
   Bereichen. Er handelt mit eigenen Rechten, nicht mit denen eines
   Menschen. Die Regel „Assistent trägt keine Rechte“ bleibt im Chat
   bestehen; der Spezialist ist der ausdrücklich verwaltete Sonderfall.
2. **Der Lauf.** Eine kleine App `spezialisten` merkt, dass ein Vorgang an
   der Reihe ist. Sie liest ihn als Gespräch, ruft Werkzeuge über das
   MCP-Gateway und das Modell über das KI-Gateway und schreibt jeden
   Schritt als internen Eintrag zurück (Notiz, Werkzeugaufruf zugeklappt,
   Ende mit Grund). Feste Grenzen je Lauf und je Vorgang, ein Stopp-Knopf.
3. **Hilfe ohne Ping-Pong.** Zuständig ist immer genau einer. Hilfe ist
   eine **Anfrage** per `@Name`: Der Gefragte (KI oder Mensch) antwortet
   einmal und wird nie zuständig. Schreibende Werkzeuge laufen nie auf
   eigenes Wort: Der Lauf hält bei `wartet auf Freigabe`, ein Mitglied des
   Bereichs gibt genau diesen Aufruf frei (per Hash gebunden). Gibt der
   Spezialist auf oder reißt eine Grenze, geht der Vorgang an die Menschen
   des Bereichs zurück.

Den „dunklen Chat“ sehen die Mitglieder des Bereichs und die
Mandanten-Verwaltung, nie die meldende Person. An sie schreibt der
Spezialist nur einen Entwurf, den ein Mensch freigibt.

**Sicherheit:** Der Text der meldenden Person ist Daten, keine Anweisung.
Die Sicht enthält nur die nötigen Werkzeuge, die App läuft mit
geschlossenem Abfluss, und jeder Aufruf nennt den Spezialisten und bei
Schreiben die freigebende Person.

**Entscheidungen (D1–D11)**, von Jörg am 19.11.2026 alle wie empfohlen
entschieden:
- D1: eigene Rechte statt im Auftrag der Meldenden.
- D2: eigene App `spezialisten` statt Einbau in Vorgänge oder Chat.
- D3: Abfrage alle 30 s, später Ereignisse über den Broker.
- D4: jede Schreibaktion freigeben, später je Werkzeug lockerbar.
- D5: öffentliche Einträge nur als Entwurf.
- D6: zwei neue Unterstatus.
- D7: Anfrage = eine Antwort.
- D8: Grenzen als Mandanten-Einstellung.
- D9: Ampel je Bereich.
- D10: Name „Spezialist“.
- D11: Revision je Eintrag festhalten.

**Stufe 0 gemessen (20.11.2026, oaap-test, Mandant vuebung):** Ein Agent mit
eigenem Schlüssel liest und kommentiert Vorgänge seines Bereichs direkt an
der Tür von `vorgaenge` (9/9), und über das MCP-Gateway mit Verfahren T
(8/8). Die meldende Person sieht seine internen Notizen nicht. Folgen für
Stufe 1: Der Lauf schreibt direkt in `vorgaenge`; jeder Spezialist bekommt
einen eigenen Server-Eintrag, eine Sicht und einen Gateway-Schlüssel; seine
Sicht ist nur lesend, weil ein Schlüssel heute ohne Zustimmung schreiben
kann; das Modell erreicht er mit einem eigenen Schlüssel des KI-Gateways;
die Assistenten-Revision liegt als festgehaltene Kopie im Spezialisten.

**Stufe 1 gebaut und gemessen (20.11.2026):**
- Gebaut sind `spezialisten` 0.1.0 (neue App) und `vorgaenge` 0.13.0 (Erstbearbeitung je Bereich, Tür für den Lauf, dunkler Chat mit KI-Marke, Stopp-Knopf).
- Auf oaap-test hat ein Spezialist einen neuen Vorgang selbst übernommen, gelesen und ein Werkzeug über seine Sicht gerufen. Das Gateway hat den Aufruf abgelehnt, weil das Modell ein Argument erfunden hatte. Danach hat der Spezialist eine Notiz geschrieben und den Vorgang zurückgegeben.
- Die meldende Person sah nichts davon.
- Das kleine lokale Modell taugt inhaltlich nicht. Das Gerüst trägt.

**Stufe 2 gebaut und gemessen (20.11.2026):**
- Gebaut sind `mcp-gateway` 0.34.0, `vorgaenge` 0.14.0 und `spezialisten` 0.2.0.
- Ein Spezialist schreibt jetzt nur nach Freigabe. Ein schreibendes Werkzeug legt er als Plan in den Vorgang. Vorgänge bindet den Plan an einen Hash, ein Mensch des Bereichs gibt genau diesen Aufruf frei, und der nächste Lauf führt ihn aus.
- Das Gateway verlangt in einer Sicht mit `--approval required` die freigebende Person und schreibt sie ins Protokoll.
- Gemessen auf oaap-test: 11 von 11. Ohne Freigabe lehnt das echte Gateway ab, der Agent kann sich nicht selbst freigeben, und nach der Freigabe lief genau der freigegebene Aufruf.
- Offen:
  - eine unterschriebene Freigabe, die das Gateway selbst prüft;
  - die Ampel je Bereich.

**Stufe 3 gebaut und gemessen (20.11.2026):**
- Gebaut sind `vorgaenge` 0.15.0 und `spezialisten` 0.3.0.
- Rückfragen: Wer verantwortlich ist, fragt einen anderen Spezialisten oder einen Zuständigen des Bereichs. Der Vorgang steht so lange auf „wartet auf Rückmeldung“.
- Die Befragten lesen den Vorgang, antworten genau einmal und werden nie verantwortlich. Ein befragter Spezialist bekommt nur lesende Werkzeuge.
- Grenzen: höchstens 3 Rückfragen an Spezialisten je Vorgang; nach 2 Antworten Spezialist zu Spezialist in Folge ist ein Mensch dran.
- D4: Der tenant_admin kann die Freigabe für einzelne Werkzeuge je Spezialist aufheben; das wird protokolliert.
- Gemessen auf oaap-test: 24 von 24.
- Nicht live gemessen: zwei Spezialisten untereinander und die Grenzen. Das decken die Tests ab.

**Stufen:** 0 messen, ob der Schlüssel eines Agenten durch das MCP-Gateway
trägt (offen seit RFC-0067); 1 lesender Spezialist mit Verlauf und
Zurückgeben; 2 Schreiben mit Freigabe, Antwortentwurf an die Meldenden;
3 Anfragen an andere Spezialisten und Menschen; 4 das SAP-Szenario auf
`a4h` und `bec`.

**Unterschriebene Freigabe und Ampel je Bereich (21.11., §16):** Vorgänge 0.16 unterschreibt
jede Freigabe eines geplanten Aufrufs mit seinem Freigabeschlüssel. Das MCP-Gateway 0.39 prüft
sie in einer Sicht mit `--approval signed` selbst -- genau dieser Aufruf, genau einmal. Wer nur
den Schlüssel der Sicht hat, kann sich keine Freigabe mehr ausstellen. Ein Bereich bekommt eine
Ampel für Spezialisten. Spezialisten 0.4 schickt sie an beide Gateways, die dann nur bis zu
dieser Farbe arbeiten. Ohne eigene Ampel gelten die Decken der Schlüssel (Abweichung von D9:
„die Regel des Mandanten“ ist die Decke, die er seinen Schlüsseln gibt). Auf oaap-test 15/15.
Offen: Stufe 4 mit SAP.

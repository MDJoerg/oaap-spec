# RFC-0105: Specialists in Cases — AI Agents That Work a Case in the Background

- **Status:** Accepted (2026-11-19). D1–D11 decided by Jörg as recommended.
  Nothing built.
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

**Stufen:** 0 messen, ob der Schlüssel eines Agenten durch das MCP-Gateway
trägt (offen seit RFC-0067); 1 lesender Spezialist mit Verlauf und
Zurückgeben; 2 Schreiben mit Freigabe, Antwortentwurf an die Meldenden;
3 Anfragen an andere Spezialisten und Menschen; 4 das SAP-Szenario auf
`a4h` und `bec`.

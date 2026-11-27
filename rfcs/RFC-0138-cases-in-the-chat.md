# RFC-0138: Cases in the Chat — Feedback, a Desk and Decisions on the Go

- **Status:** **Accepted (2026-11-27)** — D1–D8 decided by Jörg, all as
  recommended (§9). Nothing built.
- **Date:** 2026-11-27
- **Authors:** Jörg (the need: cases are no longer only feedback from the
  chat; the multi-agent scenarios run on them too; the cases a person is
  responsible for should be in the chat, with a dashboard of figures, status
  and comment from the chat, „auch mobil“; the question whether „Prozesse“ is
  the better word), Claude (design)
- **Depends on:** RFC-0061 (cases), RFC-0101 (feedback in the chat), RFC-0103
  (cases in daily work: responsible, assignee, substatus, the chat view
  „Vorgänge“), RFC-0105 (specialists, signed approval, `waiting_approval`),
  RFC-0134 (a lead and its tasks, `waiting_task`), RFC-0135 (gates and their
  target processes)
- **Changes (when accepted):** vorgaenge (a desk door
  `/platform/cases/desk`, the same rules as its pages), chat (the view
  „Feedback“ renamed, a new area „Vorgänge“ with the desk), the gateway (two
  matchers for the desk door, like `/platform/feedback`)

## Summary

The chat knows cases today only from one side: **the cases I reported**
(`/platform/feedback/mine`, the view „Vorgänge“ of RFC-0103 D9, the red dot
„you are next“). Everything a person has to **work on** — cases in their
areas, assigned to them, plans of specialists waiting for their approval —
lives in the vorgaenge app, a full desktop page.

This RFC brings the working side into the chat:

1. The present view is renamed **„Feedback“** — it is what the person
   reported and what came back.
2. A new area **„Vorgänge“** opens with a **desk**: a few figures
   („Bei mir zur Entscheidung“, „Mir zugeordnet“, „Neu heute / diese Woche“,
   „Ohne Bewegung“), broken down by area and kind, each figure a filtered list.
3. From a case card in the chat the person **comments, changes the status,
   takes over and decides** (the signed approval of RFC-0105) — on a phone as
   well as at a desk.

The chat holds no rule of its own: every figure and every action goes through
a door of the vorgaenge app that calls the same functions as its pages.

## 1. Words: Vorgang and Prozess

Jörg asked whether **„Prozesse“** would be the better name for cases with
several people and agents. Recommendation (D1): **keep „Vorgang“ for the
case, use „Prozess“ for its definition.**

| Word | Means | Where it already is |
|---|---|---|
| **Vorgang** | one concrete case: number, status, responsible, history | the app vorgaenge, V-2026-0042 |
| **Prozess** | how a kind of case runs: steps, who decides, which specialists | the target process of a gate (RFC-0135, `processes` in gates), the process model of I-80 to come |
| **Feedback** | a Vorgang a person reported from the chat (bug, question, idea, change, „nicht zufrieden“) | RFC-0101 |

This is the split known from SAP: the process is the definition, the case (the
document, the ticket) is the instance. Naming the list of cases „Prozesse“
would put the definition's word on the instances just when I-80 starts using
it for the definition. Feedback stays a Vorgang technically (a kind, as
today); only the chat shows it under its own name.

## 2. What exists (vorgaenge 0.23.1, chat 0.30.0)

- `/platform/feedback/mine` (GET, POST `…/<number>/<accept|reopen>`): only the
  person's own reports, nothing internal; the chat's view „Vorgänge" and the
  dots in the conversation tree read it.
- The app's pages: overview with `view/queue/status/sort` in the address
  (RFC-0103 stage 4), the case page with the actions `comment`, `rolle`,
  `status`, `move`, `accept`, `reopen`, `freigabe` (one `case_post`).
- The MCP door (`/mcp`): `list_cases` (scope `mine|queues|all`),
  `search_cases`, `get_case`, `list_queues`, `create_case`, `comment_case`.
- No due dates on cases. „Overdue" therefore has no meaning yet; this RFC
  uses „ohne Bewegung seit N Tagen" instead (D5).

## 3. The desk

### 3.1 The figures

Counted for the person signed in, only over cases they may see
(`can_see`), open cases only unless said otherwise:

| Tile | Counts | Why first |
|---|---|---|
| **Bei mir zur Entscheidung** | `waiting_approval` in areas the person works (`may("triage")`, the rule of the `freigabe` action); consultations (`waiting_consult`) addressed to them | something waits for **this** person |
| **Mir zugeordnet** | responsible or assignee, open | the person's own work |
| **Neu heute / diese Woche** | created in the person's areas | what is coming |
| **Ohne Bewegung** | responsible or assignee, no entry for N days (D5) | what gets forgotten |
| **Gemeldet, wartet auf mich** | own reports in `waiting_reporter` or `answered` | the same as the red dot of Feedback, for completeness |

Below the tiles: the same open cases **by area** (queue) and **by kind**
(bug, question, … and, for cases from a gate, the target process), each a
number that opens the filtered list.

A tenant admin may see every area (RFC-0103). The desk counts **the person's
own areas** (member or responsible) by default, with a switch „alle Bereiche“
(D4) — otherwise the figures of a tenant admin are the whole tenant and say
nothing about what they have to do.

### 3.2 The list and the card

A tile opens a list (number, title, area, status, age of the last entry). A
case opens as a **card** in the chat: title, status, responsible, the last
entries (public and, for those who may read them, internal), and the actions
the person may take **on this case**:

- **Kommentar** (internal by default for workers, as in the MCP door; a
  switch for a message to the reporter)
- **Status** — only the transitions the app allows from here (`NEXT`)
- **Übernehmen** (assign to oneself, the `rolle` action) where the app allows it
- **Freigeben / Ablehnen** for a plan in `waiting_approval` (§4, the `freigabe` action with `ok`)
- **Antworten** on a consultation addressed to the person (the `rat` action)
- **In der App öffnen** — the full case page for everything else (moving,
  roles, hand-over, attachments)

The card never offers an action the app would refuse; the door says which ones
apply (§5).

### 3.3 Where it lives in the chat

The chat's side bar gets „Feedback" (today's view, `#feedback`) and
„Vorgänge" (the desk, `#vorgaenge`). The address `#vorgaenge` today opens
the feedback view; after the change a person who used it lands on the desk,
where „Gemeldet, wartet auf mich" leads to the same cases (D3).

The area „Vorgänge" carries a number when „Bei mir zur Entscheidung" is not
zero, like the red dot of Feedback.

The area is shown only when the tenant has a vorgaenge instance and the person
works in at least one area (D6); a person who only reports sees Feedback as
today.

## 4. Deciding from a phone

A signed approval (RFC-0105) is the one action in the card with consequences
outside the platform (a specialist writes into SAP). The card therefore shows
**what is being approved** — the plan text, the tools and the target — before
the button, and the button asks once more („Plan freigeben? Der Spezialist
schreibt danach in <Ziel>.“). The signature is made by vorgaenge as today, from
the same `freigabe` action; the chat sees neither the key nor the signature.

## 5. The door: `/platform/cases/desk`

On the chat's own host, routed by the gateway to the tenant's vorgaenge
instance exactly like `/platform/feedback` (two exact matchers, identity asked
like any non-public route; RFC-0101):

| Call | Answer |
|---|---|
| `GET /platform/cases/desk` | the figures of §3.1 with the breakdowns; `?all=1` for all areas (D4) |
| `GET /platform/cases/desk/list?tile=…&queue=…&kind=…` | the list for a tile or a breakdown |
| `GET /platform/cases/desk/<number>` | the card: fields, last entries the person may read, `actions` = the actions allowed now |
| `POST /platform/cases/desk/<number>/<action>` | `comment`, `status`, `rolle` (only assigning oneself), `freigabe` (`seq`, `ok`), `rat` — JSON in, the card out |

The POST calls the **same** `case_post` branch the case page calls (rule
„zwei Wege, eine Regel“); the door adds only JSON in and out and the
same-origin check the pages have. The figures are computed by one function in
the store that the app's overview may use as well, so the chat and the app
never count differently.

The MCP door gets one tool more, **`my_desk`** (read-only): the figures of
§3.1, so a person can ask the assistant „Was liegt heute bei mir?“ (stage 3).

## 6. Security

- Nothing is visible in the chat that the app would not show the same person;
  the door uses `can_see`, `can_read_internal` and the rules of `case_post`.
- The chat is an app of the same tenant; the door is on its host and reached
  only through the gateway with the person's own identity headers. No key of
  the chat, no service account.
- The approval of §4 stays signed by vorgaenge; a click in the chat is a
  person's click like on the case page and is recorded the same way.

## 7. Stages

| Stage | Content |
|---|---|
| 1 | Rename to „Feedback“; desk door GET with figures and lists; desk in the chat (read-only), cards with „In der App öffnen“ |
| 2 | Actions from the card: comment, status, take over; approval with the confirmation of §4 |
| 3 | `my_desk` in the MCP door; the number on the area |

## 8. Tests and measurement

- vorgaenge: the figures for a reporter, a member, a responsible person, a
  tenant admin with and without `all`; the card offers exactly the actions
  `case_post` would accept (a test that runs every offered action and every
  refused one); a POST from another origin is refused.
- chat: the views `#feedback` and `#vorgaenge`; the old address lands on the
  desk.
- Measured on oaap-test (vuebung, specialist `spez-analyse`): a plan in
  `waiting_approval` approved from the chat on a phone; the gateway accepts the
  signature.

## Non-goals

- Due dates and SLAs on cases (they would make „überfällig" possible; a
  separate RFC when needed).
- One desk across tenants. Each tenant's chat shows its own tenant's cases;
  with RFC-0137 a person can keep both chats open.
- Push notifications to the phone.
- Editing a process definition in the chat (I-80).

## 9. Decisions

Decided 2026-11-27 by Jörg: **all as recommended**.

- **D1 — Words?** Recommended: **„Vorgang" for the case, „Prozess" for its
  definition, „Feedback" for what a person reported from the chat** (§1).
  Alternative: the new area „Prozesse".
- **D2 — Rename the present chat view to „Feedback"?** Recommended: **yes**.
- **D3 — The address `#vorgaenge`?** Recommended: **it becomes the desk**;
  the feedback view moves to `#feedback`.
- **D4 — Which areas does the desk count?** Recommended: **the person's own
  areas**, with a switch „alle Bereiche“ for tenant admins.
- **D5 — „Ohne Bewegung" after how many days?** Recommended: **5 days**, one
  setting per tenant in vorgaenge.
- **D6 — Who sees the area „Vorgänge"?** Recommended: **whoever works in at
  least one area or is a tenant admin**; reporters see Feedback only.
- **D7 — Approvals in the chat at all?** Recommended: **yes, with the plan shown
  and a second confirmation** (§4).
- **D8 — Order of the tiles?** Recommended: **as in §3.1**, the decision first.

## Deutsche Zusammenfassung

**Anlass:** Vorgänge sind nicht mehr nur Feedback aus dem Chat; auch die
Szenarien mit mehreren Personen und Agenten (Spezialisten, Leiter, Tore)
laufen darüber. Was jemand **bearbeiten** muss, liegt bisher nur in der
Vorgänge-App am großen Bildschirm.

**Begriffe (D1):** Empfehlung: **„Vorgang“ bleibt der einzelne Fall**,
**„Prozess“ ist seine Definition** (wie ein Fall abläuft, wer entscheidet —
schon heute der Zielprozess eines Tors, bald das Prozessmodell aus I-80).
Das entspricht der Trennung aus SAP. Hieße die Liste „Prozesse“, bekäme die
Instanz das Wort der Definition, gerade wenn I-80 es für die Definition
braucht. **„Feedback“** heißt im Chat, was eine Person selbst gemeldet hat;
technisch bleibt es ein Vorgang.

**Vorschlag:**
1. Die heutige Sicht im Chat heißt **„Feedback“**.
2. Neuer Bereich **„Vorgänge“** mit einem **Schreibtisch**: Kacheln „Bei mir
   zur Entscheidung“ (zuerst), „Mir zugeordnet“, „Neu heute / diese Woche“,
   „Ohne Bewegung“ (statt „überfällig“, weil Vorgänge kein Fälligkeitsdatum
   haben), „Gemeldet, wartet auf mich“; darunter nach Bereich und Art bzw.
   Prozess. Jede Zahl öffnet die gefilterte Liste.
3. Aus der **Karte** eines Vorgangs: Kommentar, Status, Übernehmen und
   **Freigeben** — auch mobil. Bei einer Freigabe zeigt die Karte vorher den
   Plan und fragt ein zweites Mal, weil danach ein Spezialist z. B. ins SAP
   schreibt. Unterschrieben wird weiter in der Vorgänge-App.

**Technik:** Eine Tür `/platform/cases/desk` der Vorgänge-App auf dem Host des
Chats, wie heute `/platform/feedback`. Sie ruft dieselben Regeln auf wie die
Seiten der App; der Chat hat keine eigene Logik. Später ein Werkzeug
`my_desk`, damit man den Assistenten fragen kann, was heute anliegt.

**Stufen:** 1 Umbenennung und Schreibtisch zum Lesen, 2 Aktionen aus der
Karte inkl. Freigabe, 3 Werkzeug `my_desk` und Zahl am Bereich.

**Angenommen am 27.11.2026, D1–D8 alle wie empfohlen:** Begriffe (D1), Umbenennung (D2),
`#vorgaenge` wird der Schreibtisch (D3), eigene Bereiche mit Schalter „alle“
(D4), 5 Tage ohne Bewegung (D5), Bereich nur für Bearbeitende (D6), Freigabe
im Chat mit zweiter Bestätigung (D7), Reihenfolge der Kacheln (D8).

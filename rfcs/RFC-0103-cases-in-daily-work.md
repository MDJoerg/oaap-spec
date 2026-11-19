# RFC-0103: Cases in Daily Work — Responsibility, Delegation, Internal Comments, and the Way Back Into the Chat

- **Status:** **Accepted (2026-11-19)** — Jörg: "Alles wie empfohlen,
  schreib das RFC", after going through the points in conversation.
  D1–D11 decided as recommended. **Stage 1 built** (2026-11-19,
  vorgaenge 0.8.0, not pushed); §10.
- **Date:** 2026-11-19
- **Authors:**
  - Jörg: the wishes, from working the first real case `V-2026-0001` in
    `bec`.
  - Claude: reading of `vorgaenge` 0.7.0, chat 0.13.0 and RFC-0061;
    design.
- **Depends on:**
  - RFC-0061: cases, queues as contexts, the attested feedback route,
    handover, Q6.
  - RFC-0045: grants, contexts.
  - RFC-0101: "not satisfied", D11 the answered mark.
  - RFC-0102: attachments, draft.
  - oaap-design §6: list report, object page.
- **Amends:** RFC-0061 §2.2 (who holds a queue, and how the build deviated
  from it) and §6 (statuses).
- **Not part of this RFC:**
  - Notifications (RFC-0061 §8, own RFC).
  - Voting (RFC-0061 §7).
  - Templates with workflows (RFC-0061 §6).

## Summary

The first real case showed what a small tenant needs in order to work
cases, and what the person who reported one needs to see. Six pieces:

1. **The `tenant_admin` works every queue.** This is what RFC-0061
   §2.2 described. The build checked the app role `admin` instead and
   only for the inbox.
2. **Members per queue, kept in the app.** A small tenant needs no
   "Rollen & Rechte" to say who works a queue. Grants from there still
   count, and both ways add up.
3. **Responsible and assigned.**
   - One person responsible for a case, from the queue's members.
   - One person currently assigned, who may come from outside the queue:
     a delegation that gives exactly this case read, comment and status.
4. **Sub-statuses of "in progress"** and **internal comments.** Internal
   comments are visible to everyone who works or ever worked the case,
   never to the reporter.
5. **Object page with tabs, list report with columns, filters and
   sorting.**
6. **The way back into the chat:**
   - a link to the case;
   - a coloured dot per conversation in the chat's tree;
   - a view "Vorgänge" with the person's own reports;
   - "Lösung passt / passt nicht" for an answered case, right there in
     the chat.

## 1. Facts (read 2026-11-19, `bec` on `oaapx01`)

- **`vorgaenge` 0.7.0, rights:**
  - `Who.may(activity, queue)` is true for the app role `admin` on the
    inbox, otherwise only through grants of "Rollen & Rechte" (object
    `case`, field `queue`).
  - A `tenant_admin` without `admin` could neither change the status of
    `V-2026-0001` nor move it. With `admin` he could change the status in
    the inbox but still not work the new queues `jira` and `partner`.
- **RFC-0061 §2.2** says: every tenant has a default queue, "held by
  the `tenant_admin` until someone is assigned". The build deviates from
  that.
- **Statuses:** `new`, `triage`, `in_progress`, `answered`, `closed`,
  `rejected`, `reopened`, `handed_over`.
  - The reporter may close an answered case. Whether they accepted the
    answer is not recorded.
- **Comments:** all comments are visible to everyone who sees the case,
  the reporter included.
- **Overview:** case table without responsible, assignee or sort.
- **Chat 0.13.0:**
  - It keeps the case numbers in the person's history and reads the
    status with `GET /platform/feedback/mine?numbers=…`, showing
    „beantwortet“ at the answer.
  - It does not know the address of `vorgaenge`, so it offers no link.
- **`vorgaenge` knows its own public names** (`OAAP_INSTANCE_NAMES`,
  used today as the sender of handovers).

## 2. Who may do what

### 2.1 The `tenant_admin` (D1)

- **May:** In every queue of the tenant the `tenant_admin` may read
  (internal comments included), comment, change the status, move, close,
  create queues, keep members, set responsible and assignee.
- **May not:** hand over to another tenant. That stays with the clearing
  of the queue (grant `hand_over` or membership as clearing), because
  data leaves the tenant.
- **The app role `admin`:** keeps what 0.7.0 gives it (the inbox).

### 2.2 Members of a queue (D2)

- **Who keeps the list:** each queue has a list of members, kept in the
  app by the `tenant_admin` on the page „Bereiche“.
- **Kinds of member:** a member is a handler (`read, comment, triage,
  move, close`, as the template „Bearbeiter/in“) or clearing (plus
  `hand_over`).
- **Two ways add up:** grants from "Rollen & Rechte" add to the list.
  Large tenants keep using templates and contexts; a small one never
  opens that app.
- **Members do not add members.** Otherwise a queue grows unseen.
  Delegation for one case is §2.3.

### 2.3 Responsible and assigned (D3)

| Role on the case | Who | May on this case | Set by |
|---|---|---|---|
| **responsible** | one member of the case's queue | as a member | the `tenant_admin`, a member |
| **assigned** | any person of the tenant | read, comment, change the status; not move, close or hand over | the responsible, a member, the `tenant_admin` |

- **Moving:** moving a case empties "responsible"; the new queue
  decides. "Assigned" stays until someone changes it.
- **No chains:** the assigned person cannot assign further.
- **After the assignment ends:** a person who was ever responsible or
  assigned keeps **read** access (internal comments included), never
  change access. The case lists them under „Beteiligt“.
- **History:** every change of either role is an entry in the history.

## 3. Statuses (D4)

Fixed sub-statuses of `in_progress`, the same transitions as
`in_progress`:

| status | label | dot in the chat |
|---|---|---|
| `clarify_internal` | in Klärung intern | yellow |
| `clarify_external` | in Klärung extern (a third party) | yellow |
| `waiting_test` | wartet auf Test | yellow |
| `waiting_reporter` | Rückfrage an dich | red |

- **Rückfrage:** `waiting_reporter` asks the reporter. Their next comment
  moves the case back to `in_progress` by itself.
- **Fixed, not per tenant:** evaluations across tenants, the MCP door
  and the chat need words they know.

**Closing (D10, D11):**
- An answered case shows the reporter two buttons:
  - „Lösung passt“ → `closed` with the mark `accepted`;
  - „Passt nicht“ → `reopened`, a comment required.
- After **14 days** without reaction (tenant setting
  `VORGAENGE_ACCEPT_DAYS`) the case closes by itself with the mark
  `no_response`, never `accepted`.
- A handler who closes without the reporter leaves the mark empty.
- Retention (Q6) counts from the closing, as today.

## 4. Internal comments (D5)

- A comment has a tick „intern“. For handlers it is **on by default**:
  a comment meant to be internal that reaches the reporter weighs more
  than the opposite mistake.
- **Readers:**
  - the queue's members and grant holders;
  - observer queues;
  - everyone ever responsible or assigned;
  - the `tenant_admin`.
- **The reporter never sees them:** not on the page, not through
  `/platform/feedback/mine`, not through the MCP door, not in the chat.
- **Handover to a partner:** an internal comment travels only when
  ticked in the draft, as every comment today.

## 5. Object page and list report (D6)

**The case (object page, tabs):**
- **Überblick:** text formatted or raw, status, queue, responsible,
  assigned, „Beteiligt“, and the actions for this person (status, move,
  assign, „Lösung passt / passt nicht“).
- **Verlauf:** public entries.
- **Intern:** only for its readers.
- **Technik:** fields of the app, browser data.
- **Übergabe:** only for clearing.
- Tabs are anchors with CSS, so they work without JavaScript, and the
  address keeps the tab.

**The overview (list report):**
- **Columns:** number, title, status (with its colour), queue,
  responsible, assigned, last change.
- **Filters:** „meine“ (responsible, assigned or reported), queue,
  status, open/all.
- **Sorting:** a click on the column header.
- **Address:** filters and sort live in the address (`?queue=jira&sort=-updated`),
  so a view can be bookmarked and the page needs no script.

## 6. The way back into the chat

### 6.1 The link (D7)

`GET /platform/feedback/mine` returns per case `url`. It is built from the
first public name of the `vorgaenge` instance (`OAAP_INSTANCE_NAMES`)
plus `/v/<number>`. The chat makes „Vorgang V-… · beantwortet“ a link
that opens in a new tab. The chat needs no setting, and a renamed
instance stays right.

### 6.2 The dot in the tree (D8)

- **One call:** `GET /platform/feedback/mine` without `numbers` returns
  all own cases with `object` and `status` (at most 200, newest first).
  The chat calls it once when loading and maps the cases to
  conversations by their object `{kind: conversation, id}`, which every
  "not satisfied" case carries.
- **The dot:** a small dot before the conversation's title, with a
  tooltip naming case and status. With several cases the most urgent
  wins (red > green > yellow > grey).

| dot | meaning |
|---|---|
| none | no case |
| yellow | open: new, triage, in progress, its sub-statuses, reopened, handed over |
| red | your turn: `waiting_reporter`, or rejected |
| green | answered, waiting for your acceptance |
| grey | closed (accepted, without response, or by the handler) |

Red means "your turn", not "bad".

### 6.3 The view „Vorgänge“ (D9)

- **Where:** in the chat's sidebar above „Assistenten“, an entry
  „Vorgänge“ with the number of open own cases.
- **What it shows:** a table of **the person's own reports** (number,
  title, assistant, status with dot, last change), sortable and
  filterable (open/all, status, assistant). Each row jumps to the
  conversation and carries the link to the case.
- **Not shown:** cases assigned to the person are not listed there. A
  number „N dir zugeordnet“ links to `vorgaenge`. Working a case belongs
  in `vorgaenge`; a second list of work in the chat would be a second app.

### 6.4 Accepting from the chat (D10)

- **The buttons:** at an answered case the chat shows „Lösung passt“
  and „Passt nicht“, the latter asking for a comment.
- **The way:** the chat posts to
  `/platform/feedback/mine/<number>/accept` or `…/reopen` on its own
  origin. The gateway attests the person, and `vorgaenge` accepts only
  from the reporter. The chat holds no key and decides nothing.
- **Evaluation:** the MCP gateway's evaluation per revision (RFC-0097
  stage 2) can count `accepted` next to cases, which is a success rate
  per revision. The chat tells the gateway with the existing
  `POST …/<id>/cases` (`{rev, number, outcome}`), so only the outcome
  travels.

## 7. Security requirements

Each requirement names the bait a test uses.

1. The `tenant_admin` works every queue but cannot hand over. Bait:
   handover by a `tenant_admin` without clearing → refused.
2. A member of queue A cannot act on a case in B. Bait: status change in
   B by a member of A → refused, page shows the reason.
3. An assigned person cannot move, close or hand over, and cannot assign
   further. Bait: each of the four → refused.
4. An internal comment never reaches the reporter (page, `/mine`, MCP
   door, chat). Bait: the reporter's MCP `get_case` lists no internal
   entry.
5. `/platform/feedback/mine` returns only the person's own reports; the
   `url` reveals nothing beyond the number. Bait: Bert lists nothing of
   Anna's.
6. Only the reporter accepts or reopens through the chat's way. Bait: a
   handler posting `…/accept` through the feedback route → refused (they
   use the page).
7. Automatic closing never marks `accepted`. Bait: a case untouched for
   15 days closes as `no_response`.
8. Former participants read, never change. Bait: a former assignee's
   status change → refused.

## 8. Decisions

All decided by Jörg on 2026-11-19, as recommended.

- **D1 `tenant_admin`:** everything in every queue except handover,
  internal comments included; `admin` keeps the inbox.
- **D2 Members in the app:** a list per queue, kept by the
  `tenant_admin`; grants add; members do not add members.
- **D3 Responsible and assigned:**
  - Responsible is one member and is emptied on move.
  - Assigned is anyone, for read, comment and status only, without
    further delegation.
  - Read access stays after the assignment ends.
- **D4 Statuses:** fixed sub-statuses of `in_progress`, including
  `waiting_reporter` for a question to the reporter (red in the chat).
- **D5 Internal comments:** the tick, on by default for handlers; the
  readers as in §4.
- **D6 Layout:** tabs on the case, list report with columns, filters and
  sorting in the address.
- **D7 Link:** from `vorgaenge`'s own public name, delivered by `/mine`.
- **D8 Dots in the tree:** the colours of §6.2, red = your turn, the most
  urgent wins.
- **D9 View in the chat:** own reports only; assigned cases as a number
  with a link.
- **D10 Acceptance:** a mark `accepted` on closing, not a new status;
  buttons in `vorgaenge` and in the chat through the attested route.
- **D11 No response:** closes after 14 days (tenant setting) as
  `no_response`.

## 9. Stages and tests

| stage | content | done when |
|---|---|---|
| 1 | D1, D2: `tenant_admin` everywhere, members per queue on „Bereiche“ | as `tenant_admin` without `admin`, `V-…` moves from the inbox to `jira`; a member of `jira` changes its status, a member of `partner` cannot (bait 2); handover by the `tenant_admin` refused (bait 1) |
| 2 | D7, D8, D10, D11: link, dots, „Lösung passt / passt nicht“ in both places, automatic closing | the chat shows a green dot for an answered case and a link that opens it; „Lösung passt“ in the chat closes it as `accepted`, the dot turns grey; bait 6 and 7 hold |
| 3 | D3, D4, D5: responsible and assigned, sub-statuses, internal comments | an assigned person outside the queue changes the status and cannot move (bait 3); an internal comment is invisible to the reporter everywhere (bait 4); a former assignee reads and cannot change (bait 8) |
| 4 | D6, D9: tabs, list report, the chat's view „Vorgänge“ | the overview filters `?queue=jira&status=open` and sorts by last change; the chat's view lists the own reports with the right count |

Spec changes: none in `oaap-spec/spec` (the case app has no capability
spec of its own yet; RFC-0061 is its contract). RFC-0061 gets a pointer
to this RFC at §2.2 and §6. The READMEs of `vorgaenge` and the chat
follow.

## 10. Stage 1, built (2026-11-19)

`vorgaenge` 0.8.0.

- **Built:**
  - `Who.may` gives the `tenant_admin` every activity except `hand_over`.
  - Queue members (`handler`, `clearing`) in a table of the app, kept on
    „Bereiche“ by the `tenant_admin` (or `admin`), with a log „Zuletzt
    geändert“.
  - The hint on a case names members, `tenant_admin` and "Rollen &
    Rechte".
- **Decided while building:** the app has no directory of the tenant's
  users; only "Rollen & Rechte" holds that key, with its own consent at
  install. So members are chosen from the people who have opened the app
  once (`people`: user id, name, user name, last seen). The page says so.
- **Measured locally:** `test_app.py` 102/102 (15 new; baits: no handover
  by the `tenant_admin`, a member of `jira` cannot act in `partner`,
  members cannot add members, an unknown person cannot be added), the
  other three test files green. Looked at in the browser behind a proxy
  with platform headers: create a queue, add a member, the log.
- **Not measured:** a node.

## Zusammenfassung auf Deutsch

Aus dem ersten echten Vorgang in bec, mit allen Empfehlungen von Jörg am
19.11. entschieden:

1. **tenant_admin:** Er darf in jedem Bereich alles außer Übergeben, auch
   interne Kommentare lesen. So stand es schon in RFC-0061; der Bau
   prüfte stattdessen die App-Rolle `admin`.
2. **Zuständige je Bereich:**
   - Der tenant_admin pflegt die Liste auf der Seite „Bereiche“. Für
     einen kleinen Mandanten braucht es dann kein „Rollen & Rechte“.
   - Grants von dort zählen zusätzlich.
   - Zuständige tragen keine weiteren ein.
3. **Verantwortlich und zugeordnet:**
   - Verantwortlich ist eine Zuständige des Bereichs. Beim Verschieben
     wird das Feld leer.
   - Zugeordnet kann jede Person im Mandanten sein, als Delegation für
     genau diesen Vorgang: lesen, kommentieren, Status ändern. Nicht
     verschieben, schließen, übergeben oder weiter delegieren.
   - Wer je beteiligt war, liest weiter, ändert aber nichts mehr.
4. **Unterstatus und interne Kommentare:**
   - Unterstatus von „in Arbeit“: in Klärung intern, in Klärung extern,
     wartet auf Test, Rückfrage an dich.
   - Interne Kommentare sind für Bearbeitende die Vorgabe. Die Meldende
     sieht sie nirgends.
5. **Seiten:** Die Vorgangsseite bekommt Reiter. Die Übersicht hat
   Spalten für verantwortlich, zugeordnet und letzte Änderung. Filter und
   Sortierung stehen in der Adresse.
6. **Rückweg in den Chat:**
   - ein Link zum Vorgang;
   - ein farbiger Punkt im Baum: gelb offen, rot du bist dran, grün
     beantwortet, grau erledigt;
   - eine Sicht „Vorgänge“ über „Assistenten“ mit den eigenen Meldungen
     und der Zahl der offenen;
   - „Lösung passt / passt nicht“ direkt im Chat. Ohne Reaktion schließt
     der Vorgang nach 14 Tagen als „ohne Rückmeldung“.
   - „Abgenommen“ wird je Revision des Assistenten mitgezählt.

**Stufen:**
1. Rechte im kleinen Mandanten.
2. Rückweg in den Chat.
3. Arbeit im Vorgang.
4. Listen und Reiter.

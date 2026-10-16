# RFC-0061: Cases — One Primitive for Feedback, Requests and Internal Work, Cleared in the Tenant and Handed Over Across It

- **Status:** **Draft (2026-10-16)** — D1 and D2 decided by Jörg before
  the draft (2026-10-16); Q1–Q7 open, each with a recommendation. Nothing
  built.
- **Date:** 2026-10-16
- **Authors:** Jörg (the need: one feedback system for every app, tenant
  and node; clearing by the tenant; escalation to the developing node;
  AI-assisted handling; idea voting before prioritisation; internal
  processes on the same primitive), Claude (fit against the platform as
  built, design, write-up)
- **Depends on:** RFC-0022 (tenant as boundary), RFC-0027 (machine
  principals and API keys), RFC-0040 (the person behind the name — the
  user id), RFC-0045 / `oaap.core.authorization` (declared objects,
  contextual assignments), RFC-0036 (apps open standalone), RFC-0038
  (instance diagnostics — what the operator may see, and what not)
- **Revises:** the idea of 2026-08-04 in `program/capability-ideas.md`,
  *"Ticket- und Wissensdatenbank-Abstraktion — kein eigenes
  Ticketsystem bauen"* (§9)
- **Drivers:** `oaap-hbsha` (HVP), use case E of the letter of
  2026-09-19 (*"Anliegen als Vorgang: Spendenquittung, Tor 2 ist defekt,
  Bewerbung auf Hallenzeit"*), now rolled out multi-tenant with
  development on another node; the operator's own need for an internal
  ticket and case handling

## Summary

Every app on OAAP will sooner or later need a way for its users to say
*"this is broken"*, *"how does this work?"*, *"I have an idea"* or
*"please change this"* — and every tenant needs a way to work through
its own requests (a donation receipt, a broken goal, a hall slot). Today
each app would build that itself, and none of them could pass a request
to the people who can actually fix it: the operator of the node, or the
developer of the app, who usually sit **in another tenant, often on
another node**.

This RFC proposes **one primitive, the case** (*Vorgang*), and splits it
the way the platform already splits authorization (RFC-0045):

1. **A catalog app `vorgaenge`**, one instance per tenant, holds the
   cases. Responsibility areas (*queues*) are **contexts** in the sense
   of RFC-0045 — one role "case handler", one assignment per queue — so
   the tenant maintains them in "Rollen & Rechte", without new platform
   code (D1).
2. **A thin platform part** does two things only an app cannot do
   honestly: a **feedback button** that every app can include, whose
   technical context (user, role, tenant, instance, app version) is
   **attested by the gateway**, not claimed by the app; and the
   **handover** of a case from one tenant to another, on the same node
   or across nodes.

Within a tenant a case **moves** (same record, the previous queue stays
an observer). Across the tenant boundary it never moves: it is **handed
over** — the receiver gets a new case with a reference, the sender's
person data stays home, the receiver's answer comes back as a new entry.
That is the letterbox principle this project already uses between AIs
(`oaap-spec/docs/ai-collaboration.md`), and it is what lets an AI
session on the developing node read cases, build a fix, and answer.

Node operator, app developer and platform are therefore **not levels of
a hierarchy** but simply other tenants with their own `vorgaenge`
instance.

## 0. Why now, and why not before

- HVP is rolling out to several clubs as tenants and develops on another
  node. The first real "Tor 2 ist defekt" will arrive in a tenant whose
  responsible person has no way to reach the developer except by mail.
- RFC-0045 is built: there is now a place where a tenant says *who is
  responsible for what*, with contexts. Before 2026-10-03, responsibility
  areas would have needed a mechanism of their own.
- The letter of 2026-09-21 put notifications and lifecycle events back
  with the platform as separate capabilities. Cases are the first
  consumer that makes notifications concrete — but cases do **not** wait
  for them (§8).

## 1. The case

One record shape for every kind:

| field | meaning |
| --- | --- |
| `id` | UUID; never reused. A short readable number (`V-2026-0042`) per tenant is an alias (RFC-0026). |
| `kind` | `bug` · `question` · `idea` · `change` · `internal` (closed list; an app may add **subkinds** via a template, §6) |
| `title`, `body` | free text by the reporter |
| `context` | the path where it arose: `node` → `tenant` → `instance` (app) → optional `object` (a twin object id, or an app-local id with the app as namespace) |
| `tech` | technical context (§3): attested part from the gateway, browser part from the client |
| `reporter` | user id (RFC-0040) — **never leaves the tenant** (§5) |
| `queue` | the current responsible area (a context id, §2) |
| `observers` | queues that held the case before, and people who subscribed |
| `status` | §4 |
| `entries` | append-only list: comments, status changes, moves, handover and its answers |
| `refs` | links to other cases: `handed_over_to`, `answer_to`, `duplicate_of`, `related` |

**Entries are append-only.** A comment is not edited, it is followed by
a correction. A case is not deleted; it is closed, and the tenant's
retention rule (Q6) removes person data after a period.

## 2. Responsibility areas: queues as contexts

### 2.1 The mapping onto RFC-0045

A queue is "Clearing des Vereins", "Mannschaft mB", "Hallenwart",
"Vorstand Finanzen". Every tenant has its own, and they change with the
season. That rules out `values:` (a closed list fixed in the manifest,
the same for every tenant) and points to the **contextual assignment**:

```yaml
authorization:
  objects:
    - key: case
      title: Vorgang
      activities: [read, comment, triage, move, hand_over, close, vote]
      fields:
        - key: queue
          context: Zuständigkeitsbereich
  role_templates:
    - key: case_handler
      title: Bearbeiter/in
      grants:
        - object: case
          activities: [read, comment, triage, move, close]
          queue: $context
    - key: case_clearing
      title: Clearing
      grants:
        - object: case
          activities: [read, comment, triage, move, hand_over, close]
          queue: $context
    - key: case_voter
      title: Ideen bewerten
      grants:
        - object: case
          activities: [read, vote]
```

The queue's id is the context; it lives in the app until the twin can
hold such objects (RFC-0045 §6.2 — the context is not checked against
the twin today). A club that wants its team to be the queue uses the
team's id from its own store, exactly as the letter of 2026-10-03
suggested for team contexts.

**`hand_over` is a separate activity on purpose:** crossing the tenant
boundary is a decision with data-protection weight (§5) and belongs to
the clearing role, not to every handler.

### 2.2 What this costs today

- **Only the `tenant_admin` assigns queue members**, in "Rollen & Rechte".
  A trainer cannot add a co-trainer to "Mannschaft mB" until `may_grant`
  is built (RFC-0045 §4, not enforced). For a first tenant this is
  acceptable; for HVP's case B it is the same gap as before.
- **Every tenant needs one default queue** ("Eingang"), created at
  install, held by the `tenant_admin` until someone is assigned. A case
  whose app names no queue lands there.

### 2.3 Moving within the tenant

A handler moves a case to another queue of the same tenant. The record
stays the same, the previous queue becomes an observer (read and
comment, no status change). There is no fixed chain "team → club"; the
chain is whatever the moves were, and the entries show it.

## 3. The feedback button and the attested technical context

Apps open standalone, each on its own origin (RFC-0036 D1). There is no
shell around them that could add a button. But the gateway already
serves `/platform/*` under every instance, so the button can be **the
platform's own script, on the app's own origin**:

```html
<script src="/platform/feedback.js" defer></script>
```

- The script renders a small button (or binds to an element the app
  names) and a form: kind, title, text, optional object id the app
  passes in (`data-oaap-object`).
- It posts to **`/platform/feedback`** on the same origin. The gateway
  routes this to the `vorgaenge` instance of the **same tenant** and adds
  the attested part of `tech` from what it already knows on every
  request: user id, platform roles, tenant, instance id, app id and
  package version. The app cannot forge them, because the app never
  sees the request.
- From the browser the script adds what only the browser knows: page
  path, user agent, screen size, language, and the **last uncaught
  error** and the last failed `fetch` status on this page (collected
  only while the script is loaded, kept in memory, shown to the user in
  the form before sending, removable).
- If the tenant has no `vorgaenge` instance, `/platform/feedback`
  answers 404 and the script renders nothing. No app breaks.

What the button **never** sends: cookies, storage contents, request or
response bodies, or anything from the instance's log. The operator's
view into logs remains RFC-0038's diagnosis window, opened on purpose
and audited — a case may *link* to such a window, never carry its
content.

## 4. Status

```
new ──▶ triage ──▶ in_progress ──▶ answered ──▶ closed
            │            │                         ▲
            │            └──▶ handed_over ──(answer)┘
            ├──▶ voting ──(round ends)──▶ triage
            └──▶ rejected (reason required)
closed / rejected ──▶ reopened ──▶ triage
```

- `triage` is the **clearing**: the queue decides what the case is,
  whether it is a duplicate, where it goes.
- `voting` exists only for `kind: idea` (§7).
- `handed_over` waits for an answer from another tenant (§5); the case
  stays open and owned at home.
- `answered` means "the reporter has a reply"; the reporter or the
  handler closes it.

## 5. Handover across the tenant boundary

### 5.1 The rule

> **A case never leaves its tenant. A handover does: a copy cleared for
> the receiver, which becomes a new case there.**

The receiver is identified as **(node, tenant, queue)** and must have
offered that queue for handover — a receiving tenant decides who may
send to it, exactly as the inner side decides what is reachable in
RFC-0033.

### 5.2 What travels

```json
{
  "handover_id": "0d2c…",
  "from": {"node": "oaapx01", "tenant": "hbvp", "case": "V-2026-0042"},
  "to":   {"node": "oaap-dev", "tenant": "hvp-dev", "queue": "triage"},
  "kind": "bug",
  "title": "Spielstand springt nach Timeout zurück",
  "body": "…as released by the clearing person…",
  "tech": {"app": "hbsha", "version": "0.41.2", "roles": ["user"],
           "browser": "…", "last_error": "…"},
  "created": "2026-10-16T18:02:11Z",
  "body_sha256": "…"
}
```

- **Removed automatically:** reporter, every user id, observers, all
  entries except those the clearing person selects.
- **Released by a human:** the title and text are shown to the clearing
  person as they will leave, editable, and sent only on an explicit
  "release" (Q3). Free text can contain names; no filter finds them all,
  so the person who knows the tenant decides. That *is* the clearing.
- **Kept at home:** the mapping `handover_id ↔ case`, so an answer finds
  its way back without the receiver ever knowing who reported.

### 5.3 How it travels (Q2)

The receiving tenant issues an **API key** (RFC-0027) scoped to its
handover inbox and bound to the sending tenant. The sender pushes over
HTTPS to the receiver's public instance address; the receiver stores the
document **unchanged** (with its hash) and creates its own case from it.
At least once, idempotent on `handover_id`: the sender retries from an
outbox until acknowledged, the receiver ignores a second copy.

The answer travels back the same way with a key the sender issued: a
new document with `answer_to: <handover_id>`, which becomes an entry on
the home case and moves it to `answered`. Nothing on either side is
overwritten by the other.

### 5.4 The developing node and the AI session

The developer's tenant is an ordinary receiver. An AI session there
(Claude Code, or a hosted agent later) works with a **machine key of
scope `oaap.cases`** on its own tenant's `vorgaenge` instance: list the
inbox, read a case, write entries, answer a handover. It reaches only
what that tenant received — never the source tenant, never a reporter.
A patch it builds goes the usual way (repository, package, catalog —
RFC-0050); the answer says which version contains the fix.

The same shape serves the node operator (`mgmt` on oaapx02) and the
platform itself: different tenants, the same inbox.

## 6. Templates for internal cases and workflows

No BPMN, no workflow engine (HVP said so explicitly on 2026-09-19, and
the platform agrees). A **template** is a small declarative record:

```yaml
- key: spendenquittung
  title: Spendenquittung anfordern
  kind: internal
  fields:
    - {key: betrag, type: number, required: true}
    - {key: datum,  type: date,   required: true}
  steps: [eingang, finanzen, vorstand]   # queues, in this order
  visible_to_reporter: [status, entries:public]
```

- `steps` is a suggested order: "next step" moves the case to the next
  queue. A handler may still move it elsewhere; the entries show it.
- Templates come from two places: an app ships defaults in its manifest
  section `cases.templates` (HVP: hall-slot application), and the tenant
  adds its own in the app.
- The template's required fields are checked at submission and at each
  step that declares them.

## 7. Ideas: a voting round before clearing

`kind: idea` may enter `voting` instead of going straight to a decision:

- A **round** has a deadline and a set of ideas; the clearing queue
  opens and closes it.
- Every person holding `case.vote` gets a **budget** per round (default
  10 points, at most 3 per idea — Q5). Points can be moved until the
  deadline.
- **Pre-priority** = points × breadth factor, where breadth is the
  number of *distinct* voters. Ten people with one point each weigh
  more than one person with ten. The formula is shown on the page, not
  hidden.
- After the deadline the ideas return to `triage` sorted by
  pre-priority. The clearing decides — the vote **advises**, it does not
  decide. An idea may then be handed over (to the developer) like any
  other case, with its score in `tech`.

## 8. What the platform does, and what it deliberately does not

| platform (thin core) | app `vorgaenge` (per tenant) |
| --- | --- |
| `/platform/feedback.js` and the attested `/platform/feedback` route | cases, entries, queues, statuses, templates, voting |
| handover inbox keys (RFC-0027 scope `oaap.cases.handover`) and the routing of `/platform/handover` | the outbox with retry, the release step, the answer mapping |
| the manifest section `cases` (templates) in `oaap.apps.runtime` | the authorization declaration (§2.1), checked with `authz_client` |

**Not part of this RFC:**

- **Notifications.** A case lives without them: the app shows an inbox
  per person and per queue. A tenant that wants mail configures SMTP as a
  `secret` variable of its `vorgaenge` instance — the interim path of the
  letter of 2026-09-21. A notification service remains its own
  capability and its own RFC; cases will be its first consumer.
- **A knowledge base.** The idea of 2026-08-04 stays an idea.
- **Cases in the twin.** The twin 0.1 has no list and no search; cases
  need both on day one. They stay in the app's own store (Q4).

## 9. Why not Zammad, FreeScout or GLPI (revises the idea of 2026-08-04)

The idea list said: build no ticket system, put an abstract API in
front of an existing one. Measured against what this RFC needs, none of
them knows OAAP's tenant, its user id, its contextual assignments, the
twin, or a handover between installations — and those four are the core
here, not an add-on. A connector would have to rebuild all of them
outside the product.

What stays from that idea is the **separation**: the case has a narrow,
documented shape (§1, §5.2), so an export to such a product — for a
customer who already runs one — remains a connector, not a rewrite.

## 10. Security requirements

1. The attested part of `tech` is set by the gateway and **overwrites**
   anything the client sends under the same names.
2. `/platform/feedback` accepts only a logged-in user of the instance's
   tenant; a rate limit per user (RFC-0010 throttling) applies.
3. A handover carries **no user id and no reporter**; a test asserts the
   outgoing document against a list of forbidden keys, and the release
   page shows the exact bytes that will leave.
4. An inbox key is bound to **one** sending tenant and **one** receiving
   queue; revoking it stops that sender only.
5. Received documents are stored unchanged with their hash; the
   receiver's case is derived from them, never the other way round.
6. The AI key (`oaap.cases`) reads and writes cases of its own tenant
   only; it cannot hand over (Q7).

## 11. Staging

1. **Report and clear within the tenant** (decided as the first slice,
   D2): app `vorgaenge` 0.1 — cases, entries, queues as contexts with the
   declaration of §2.1 checked by `authz_client`, statuses without
   `voting` and `handed_over`, the default queue; the platform's
   `feedback.js` and the attested route. Measured on `oaap-test` with a
   test tenant; **HVP as first consumer** by including one script tag.
2. **Handover**, first between two tenants on one node, then across
   nodes; the developer's inbox and the AI key (§5.4).
3. **Voting** (§7).
4. **Templates** (§6), app defaults and tenant-own.
5. *(own RFC)* notifications; cases as first consumer.

## Decided (2026-10-16, before the draft)

- **D1 — a catalog app plus a thin core.** The case store is the app
  `vorgaenge`, one instance per tenant, like "Rollen & Rechte" and
  "Partnerverwaltung". The platform builds only the attested feedback
  button and the handover between tenants and nodes. Not chosen: a core
  service like `oaap.core.authorization` (more core, tighter coupling),
  or leaving it to HVP first (every further app would build it again).
- **D2 — the first slice is reporting and clearing within the tenant**
  (§11 stage 1). Handover, voting and templates follow.

## Open — for Jörg

| | question | recommendation |
| --- | --- | --- |
| **Q1** | Does the gateway attest the technical context (§3), or does the app send it? | **The gateway.** It is the one reason for platform code in stage 1, and it makes every report trustworthy without the app's help. |
| **Q2** | Handover transport: HTTPS push into an inbox with a key the receiver issues, or the platform broker (RFC-0054)? | **HTTPS with a key.** One document, rarely, acknowledged; the broker is built for streams and is still a draft. |
| **Q3** | Must every handover be released by a person? | **Yes, in v1.** An automatic rule per queue ("bugs without free text go out directly") later, once we have seen real texts. |
| **Q4** | Where do cases live: the app's own store, or the twin? | **The app's own store** (SQLite in its volume until RFC-0057's database exists); only the context reference is an id. Revisit when the twin can list and search. |
| **Q5** | Voting defaults: budget 10 per round, at most 3 per idea, breadth = distinct voters? | **As stated**, configurable per round. |
| **Q6** | Retention: when are person data of a closed case removed? | **Per tenant, default 12 months after closing**; the case stays with the reporter replaced by "removed". |
| **Q7** | May the AI key hand cases over further (developer → platform)? | **No.** A handover is a decision of a person with the clearing role; the AI drafts it, a person releases it. |

## Deutsche Zusammenfassung

**Worum es geht:** Jede App braucht früher oder später einen Weg, über
den Anwender Fehler, Fragen, Ideen und Änderungswünsche melden. Jeder
Mandant braucht außerdem einen Weg, eigene Anliegen abzuarbeiten
(Spendenquittung, defektes Tor, Hallenzeit). Heute müsste jede App das
selbst bauen. Und keine könnte eine Meldung an die weitergeben, die sie
lösen: Betreiber und Entwickler sitzen in einem anderen Mandanten, oft
auf einem anderen Knoten.

**Der Vorschlag:** Ein einziges Primitiv, der **Vorgang**. Er hat eine
Art (Fehler, Frage, Idee, Änderungswunsch, intern), einen Kontextpfad
(Knoten → Mandant → App → Objekt), einen zuständigen Bereich, einen
Status und Einträge, an die nur angehängt wird.

**Der Schnitt (D1, von Jörg entschieden):**
- **Katalog-App `vorgaenge`**, eine Instanz je Mandant. Die
  Zuständigkeitsbereiche sind **Kontexte** im Sinne von RFC-0045: eine
  Rolle „Bearbeiter“, eine Zuordnung je Bereich. Gepflegt wird das in
  „Rollen & Rechte“, ohne neuen Plattformcode.
- **Dünner Plattformteil**, zwei Dinge:
  - ein **Feedback-Knopf** (`/platform/feedback.js`), den jede App mit
    einer Zeile einbindet. Den technischen Kontext (Benutzer, Rolle,
    Mandant, Instanz, App-Version) **beglaubigt das Gateway**, die App
    behauptet ihn nicht.
  - die **Übergabe** zwischen Mandanten und Knoten.

**Wichtigste Änderung gegenüber der ersten Skizze:**
- **Innerhalb des Mandanten wird weitergereicht.** Es bleibt derselbe
  Datensatz, der vorherige Bereich bleibt Beobachter.
- **Über die Mandantengrenze wird übergeben.** Beim Empfänger entsteht
  ein neuer Vorgang mit Bezug. Der Melder und alle Personendaten bleiben
  zu Hause. Den Text gibt der Clearing-Verantwortliche ausdrücklich
  frei; das *ist* das Clearing. Die Antwort kommt als neuer Eintrag
  zurück.
- Knotenbetreiber, App-Entwickler und Plattform sind damit **keine
  Stufen einer Hierarchie**, sondern einfach andere Mandanten mit ihrem
  eigenen Posteingang.
- Eine KI-Sitzung auf dem Entwicklungsknoten arbeitet mit einem
  Maschinenschlüssel nur im eigenen Mandanten: lesen, Lösung bauen,
  antworten.

**Weiter enthalten:**
- **Ideen mit Bewertungsrunde:** Frist, Punktebudget je Person, eine
  Vorpriorität aus Punkten und Breite der Zustimmung. Die Bewertung
  berät, die Entscheidung trifft das Clearing.
- **Vorlagen für interne Vorgänge:** Bereiche in einer Reihenfolge und
  Pflichtfelder, kein BPMN.

**Nicht enthalten:** Benachrichtigungen bleiben eine eigene Fähigkeit.
Bis dahin gibt es den Posteingang in der App, und wer Mail will, nimmt
SMTP als `secret`.

**Revidiert:** die Idee vom 04.08. „kein eigenes Ticketsystem“. Zammad
und vergleichbare Produkte kennen weder Mandant, Kontext-Zuordnung,
Zwilling noch eine Übergabe zwischen Installationen, und genau das ist
hier der Kern. Von der Idee bleibt die schmale, dokumentierte Form, damit
ein Export später ein Konnektor bleibt.

**Erste Scheibe (D2, von Jörg entschieden):** Melden und Clearing im
Mandanten: App 0.1 plus Feedback-Knopf, gemessen auf oaap-test, HVP als
erster Abnehmer. Danach folgen Übergabe, Bewertung und Vorlagen.

**Offen für Jörg:** Q1–Q7, jeweils mit Empfehlung. Die Punkte sind:
Gateway beglaubigt, Übergabe per HTTPS mit Schlüssel, Freigabe durch
einen Menschen, eigene Ablage statt Zwilling, Punkte 10/3, Löschfrist 12
Monate, die KI übergibt nicht selbst.

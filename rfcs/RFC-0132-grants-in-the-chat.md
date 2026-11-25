# RFC-0132: Grants in the Chat

- **Status:** **Accepted (2026-11-25)** — D1–D4 decided by Jörg the same day,
  one at a time (§6). **Built** (chat 0.30.0, mcp-gateway 0.50.0, §7).
- **Date:** 2026-11-25
- **Authors:** Jörg (the need: "Dann musste ich ständig etwas bestätigen.
  Können wir hier auch sowas einführen wie ‚in dieser Session erlauben‘,
  ‚für diesen Assistenten erlauben‘, ‚für diesen Arbeitsraum erlauben‘? …
  Dann hätten wir hier weitreichende Flexibilität und halten trotzdem unser
  Versprechen?"), Claude (design)
- **Depends on:** RFC-0074 (the chat acts as the person; D6: a tool that
  changes something runs only after the person's consent), RFC-0121
  (workspaces), RFC-0101 (lights)
- **Changes:** `oaap.ai.assistants` 0.10 (consent may come from a grant;
  `X-OAAP-Consent`), `oaap.ai.mcp-gateway` 0.42.0 (the usage row records
  where the consent came from)

## Summary

Every changing tool call asks for a click. In a long conversation in a
workspace that is many clicks for the same tool. A **grant** lets the person
allow **one tool** in **one reach** — this conversation, this assistant, this
workspace — until revoked. The promise "what changes something runs only
after your consent" stays: a grant is a consent given in advance, visible at
every call it covers, listed in one place, paused or deleted with one click.
Deleting tools (`destructiveHint`) are never granted beyond one conversation.

## 1. The grant

| Field | Meaning |
|---|---|
| `tool` | exactly one tool name (D1) |
| `scope` | `conversation` · `assistant` · `workspace` |
| `target` | the conversation, the assistant id, the workspace id |
| `paused` | a paused grant covers nothing |
| `created` | when |

Conversation grants live in the conversation; assistant and workspace grants
in the chat's file of the person (`people/<p>/grants.json`, ≤ 200). They are
the person's own and never seen by anyone else.

## 2. When a grant covers a call

A changing call (effect not `read`) runs without asking when the conversation
holds an active grant for this tool, or — only for a tool without
`destructiveHint` — the person holds an active grant for this tool with
`assistant` = the conversation's assistant, or `workspace` = the
conversation's workspace. Otherwise the chat asks as before. The chat's own
calls (`/ablegen`) are never covered.

## 3. Giving and taking back

- The confirmation offers "nur dieses Mal" (the default) and the reaches
  that apply: workspace only in a workspace; a deleting tool only "in diesem
  Gespräch" (D2). Choosing a reach runs the call AND creates the grant.
- Every call under a grant shows "🔓 Freigabe: <tool> <reach> · widerrufen";
  one click deletes it.
- The footer ("… läuft erst nach deiner Zustimmung") links to the list: tool,
  reach, active or paused; pause, resume, delete.
- Grants last until revoked (D3).

## 4. What the gateway records (D4)

With `X-OAAP-Confirmed: yes` the chat sends `X-OAAP-Consent`: `click` or
`grant:<scope>`. The gateway records it in the usage row (`approved_by`) as
a fixed sentence — "Person: Klick", "Person: Freigabe (Gespräch|Assistent|
Arbeitsraum)" — and drops any other value. It remains the chat's statement,
recorded for review, never a permission.

## 5. Security requirements

1. One tool per grant; no wildcard.
2. A deleting tool is granted at most for one conversation.
3. A grant never widens the light, the view or the person's rights: the
   gateway and the product decide as before.
4. A grant is visible at every call it covers and in the list.
5. Only the person sees and changes their grants.

## 6. Decisions (Jörg, 2026-11-25)

- **D1** A grant covers **one tool** (not all changing tools).
- **D2** Deleting tools ask every time; in the dialog they **may be allowed
  for this conversation**, never for an assistant or workspace.
- **D3** Assistant and workspace grants last **until revoked**.
- **D4** The gateway **records** whether the person clicked or a grant
  applied, and which reach.

## 7. As built (chat 0.30.0, mcp-gateway 0.50.0)

Chat: `find_grant`, `add_grant`, the confirmation carries `scopes` and
`destructive`, the tool result carries `grant {id, scope, new}`,
`GET /api/grants?conv=`, `POST /api/grants/<id>/delete|pause|resume`;
`X-OAAP-Consent` on every confirmed call. Gateway: `consent_word`, recorded
in `usage.approved_by` for persons (tools and the store door). Tests: chat
290 (+19, among them baits: deleting "for the assistant" runs once and
creates nothing; bert neither sees nor pauses anna's grants), gateway 587.

## Deutsche Zusammenfassung

Statt jeden ändernden Aufruf einzeln zu bestätigen, erlaubt die Person im
Bestätigungsdialog **ein Werkzeug** in einer Reichweite: **in diesem
Gespräch**, **für diesen Assistenten** oder **in diesem Arbeitsraum** — bis
sie es widerruft. Löschende Werkzeuge fragen immer, dürfen aber für das
laufende Gespräch erlaubt werden. Jeder Aufruf unter einer Freigabe zeigt sie
mit einem Symbol, ein Klick widerruft sie; unten im Chat führt „Freigabe“ zur
Liste (pausieren, aktivieren, löschen). Das MCP-Gateway vermerkt im
Protokoll, ob geklickt wurde oder welche Freigabe galt. Das Versprechen
bleibt: nichts ändert sich ohne Zustimmung — eine Freigabe ist eine
Zustimmung im Voraus, sichtbar und widerrufbar.

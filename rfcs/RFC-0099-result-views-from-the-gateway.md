# RFC-0099: Result Views from the Gateway — UI Without Touching the Backend, and the Design Grant

- **Status:** Draft (2026-11-19). Direction decided by Jörg in conversation
  on 2026-11-19: **result views first** (a view only shows a tool's
  result); who may design is governed by a **grant requested from the chat
  and held in the gateway** (assistant, view, …), revocable and deactivatable
  at any time; the platform role key user can be the precondition. UI design
  is allowed only where the roles of RFC-0098 permit. Open decisions D4–D10
  below, each with a recommendation. Nothing built.
- **Date:** 2026-11-19
- **Authors:** Jörg (the idea: MCP Apps are HTML resources from the server;
  in SAP, building them into the backend is too much effort — the gateway
  already has its own view of servers and influences the catalog, so it
  could offer tools to let an AI create such UI resources, reuse them, bind
  them to the assistant with visibility private/team/all, manage them in
  the gateway, export and import them; a "UI designer" mode in the chat),
  Claude (design)
- **Depends on:** RFC-0075 (the chat as host of MCP Apps: sandbox origin,
  CSP, calls from a view go through the chat's round), `oaap.ai.mcp-gateway`
  0.18.0 §4.3 (views of tools, pinned and approved with their tool),
  RFC-0097 (assistants in the gateway), RFC-0098 (roles), RFC-0045
  (contexts, key users), RFC-0068 (closed egress)
- **Not part of this RFC:** views that call tools (stage 2, named, designed
  later); views as standalone apps outside the chat

## Summary

MCP Apps let a server deliver a `ui://` resource — an HTML document the host
renders next to a tool's result. Backends such as SAP will not deliver them
soon, and building them there is expensive. The gateway sits between the
server and the client and already pins and approves views of servers
(RFC-0075). This RFC lets the **gateway itself be the source** of views:

- A **result view** is an HTML document stored in the gateway and attached
  to a tool of a view (or of a target group, RFC-0098). When the tool is
  called, the gateway adds `_meta.ui.resourceUri` pointing to its own
  resource; the chat renders it in the existing sandbox.
- Stage 1 views **only display** the result: no tool calls, no network, no
  message into the chat.
- Views are created by an AI in a **UI designer** mode of the chat, with
  tools the gateway offers only to persons holding a **design grant**.
- Each view has revisions, a visibility (`private`, `context`, `tenant`),
  a state (`draft`, `active`, `inactive`), export and import as a file.
- The **design grant** is requested from the chat, becomes an approval
  request in the gateway, and can be deactivated or revoked at any time.

## 1. Facts (read 2026-11-19)

- RFC-0075 stage 1/2 built: the chat renders a view on a second origin in a
  sandbox that receives the HTML by `postMessage`, under a CSP derived from
  `_meta.ui.csp` (default `connect-src 'none'`). A `tools/call` from a view
  becomes a pending call in the conversation; writing needs the person's
  click on the chat's own card.
- The gateway pins a server's view by content and suspends the tool when it
  changes (§4.3).
- The real risk of a view is not what it shows but what it can **call**: a
  view runs with the rights of the person **looking at it**. A shared view
  that calls tools could act as every person who opens it.

## 2. Result views

### 2.1 The record

```yaml
id: su53-auth-check            # unique per gateway
title: "Missing authorizations (SU53)"
binds: {view: sap-support, tool: sap-basis.get_su53}   # or a list of tools
html: <the document>            # one self-contained file, inline CSS/JS
visibility: {scope: context, context: {team: basis}}   # private | context | tenant
state: draft | active | inactive
rev: 4
owner: <person id>
```

- **One file, nothing loaded from outside.** CSP `default-src 'none';
  script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:`.
  No external domains, in any tenant — a closed tenant (RFC-0068) and an
  open one behave the same.
- **Input:** the tool's result as MCP Apps delivers it (`ui/notifications/
  tool-result`). Stage 1 uses nothing else of the host API.
- **Precedence:** if the server delivers its own view for the tool, the
  server's view wins unless the view's operator chooses the gateway's
  (D6).

### 2.2 Delivery

- In `tools/list`, the gateway adds `_meta.ui.resourceUri =
  ui://oaap-gateway/<id>@<rev>` for tools that have an **active** view
  visible to this person.
- `resources/read` of that URI is answered by the gateway; it is metered
  like any read.
- The chat's assistant must allow views (`views: true`, RFC-0075 D2).

### 2.3 The UI designer

A mode of the chat (an assistant flag or a command, D7) in which the
gateway offers four extra tools, only to persons holding a design grant for
this view:

- `ui_list` — views of this view/tool the person may see;
- `ui_draft` — create or change a draft (HTML, bound tool); returns a
  preview link;
- `ui_preview` — render the draft with a **real result of the person**
  (the last call of the bound tool in this conversation); the result never
  leaves the person's session;
- `ui_publish` — set the draft active with a visibility the grant allows.

The designer works on targets whose effective role allows UI design
(RFC-0098 §3.3: not production). A published view then also shows results
from production targets — it only displays.

### 2.4 Export and import

- Export: one view (a revision) as a file `oaap.ai.ui-view` (YAML with the
  HTML inline), without `owner` and `rev`.
- Import: needs a design grant for the bound view; arrives as `draft`;
  the check refuses external references in the HTML (D9).
- Optionally a package kind in the catalog, together with assistants
  (RFC-0097 D5).

## 3. The design grant

### 3.1 Request

From the chat: "Request UI design rights" (in the designer mode or the
assistant's menu). The gateway creates an **approval request**:

```yaml
person: <id>
assistant: sap-basis-support@7     # where it was requested
view: sap-support
scope: private | context | tenant  # the widest visibility asked for
reason: "SU53 output is unreadable as JSON"
valid_until: 2027-02-19            # optional
```

### 3.2 Who may request, who approves

- **Request:** any person who may use the assistant; *recommendation D4:*
  only persons with the platform role key user in the view's context, or
  `tenant_admin`.
- **Approve:** for `private` and `context`: the gateway's operator or the
  context's key user; for `tenant`: `tenant_admin` (D5).
- Approval lists the requested scope; the approver may narrow it.

### 3.3 Lifecycle

- `requested` → `active` → `inactive` (paused, reactivatable) or `revoked`.
- Revoking does **not** delete published views; they stay active under
  their owner until someone with the right deactivates them (D8).
- Every transition is audited; the person sees their grants on `/me`.

## 4. Security requirements

1. Stage 1 views have no host API except receiving the result: no
   `tools/call`, no `ui/message`, no links (D10), no network.
2. A view is rendered only on the chat's sandbox origin (RFC-0075 §2.2).
3. Designer tools are listed only with an active grant; without one they
   do not exist for the model (no hint, no oracle).
4. Publishing to `context` or `tenant` requires a grant with at least that
   scope; the widest scope is approved by `tenant_admin`.
5. A changed view is a new revision; the published revision stays until
   the new one is published.
6. The preview never stores the person's result in the gateway.

## 5. Stage 2, named

Views that call tools: the view declares the tools it may call
(allowlist), the gateway enforces it, writing still goes through the chat's
confirmation card (RFC-0075 D4), and publishing to `context`/`tenant`
needs a second person's review (four eyes). Designed in a later section of
this RFC.

## 6. Decisions

- **D1 Result views first.** *Decided (Jörg, 2026-11-19).*
- **D2 Grant in the gateway, requested from the chat, revocable.**
  *Decided.*
- **D3 Roles decide where design happens.** *Decided* (via RFC-0098).
- **D4 Who may request.** *Recommendation:* key user of the view's
  context or `tenant_admin`.
- **D5 Who approves.** *Recommendation:* operator or the context's key user
  for private/context; `tenant_admin` for tenant.
- **D6 Server view vs. gateway view.** *Recommendation:* the server's wins
  by default; the operator can choose per tool.
- **D7 How the designer is entered.** *Recommendation:* an assistant flag
  `designer: true`, so a tenant can have one "UI designer" assistant per
  view family.
- **D8 Views after revocation.** *Recommendation:* stay active; the
  administration sees "owner without grant" and decides.
- **D9 External references.** *Recommendation:* refused on save and import
  (no `http(s)://` in `src`, `href` of `link`, `url()`, `import`).
- **D10 Links in stage 1.** *Recommendation:* none; `ui/open-link` comes
  with stage 2.

## 7. Stages and tests

| stage | content | done when |
|---|---|---|
| 1 | view records with revisions, delivery via `_meta.ui`, rendering in the chat | an active view appears with its tool's result; a `tools/call` from it is refused; a view with an external `src` is refused on save |
| 2 | grants (request, approve, deactivate, revoke), designer tools, preview, publish | without a grant `ui_draft` is not listed; on a production target the designer is refused; revoke takes the tools away within one call |
| 3 | export/import, catalog kind | an exported view imports as draft into a second gateway with the same view and tool names |
| 4 | stage 2 of §5 | — |

Spec: a new `oaap.ai.ui-views` 0.1, `oaap.ai.mcp-gateway` (§4.4 views of
the gateway, §5.6 design grants), `oaap.ai.assistants` (field `designer`).

## Zusammenfassung auf Deutsch

MCP Apps liefern HTML-Ansichten aus dem MCP-Server. SAP wird das so bald
nicht tun, und es dort zu bauen ist teuer. Das RFC macht das **MCP-Gateway
selbst zur Quelle von Ansichten**:

- Eine **Ergebnis-Ansicht** ist ein HTML-Dokument im Gateway, gebunden an
  ein Tool einer Sicht (oder einer Zielgruppe aus RFC-0098). Das Gateway
  hängt sie per `_meta.ui` an das Tool, und der Chat zeigt sie in seiner
  vorhandenen Sandbox.
- **Stufe 1 zeigt nur an:** keine Tool-Aufrufe, kein Netz, keine Nachricht
  in den Chat. Der Grund: Eine Ansicht läuft mit den Rechten der Person,
  die sie ansieht. Eine geteilte Ansicht, die Tools aufruft, könnte als
  jede dieser Personen handeln. Das kommt erst in Stufe 2, mit Allowlist
  und Vier-Augen-Prüfung.
- **UI-Designer:** ein Modus im Chat mit den Tools `ui_list`, `ui_draft`,
  `ui_preview` (mit einem echten Ergebnis der Person, das nicht
  gespeichert wird) und `ui_publish`. Entworfen wird nur auf Zielen, deren
  Rolle das erlaubt, also nie produktiv. Eine veröffentlichte Ansicht darf
  dann auch Produktivergebnisse anzeigen.
- **Design-Recht als Freigabe:** aus dem Chat angefordert, im Gateway als
  Antrag mit Person, Assistent, Sicht, gewünschter Sichtbarkeit und
  Begründung. Key User oder `tenant_admin` geben frei. Jederzeit inaktiv
  setzen oder widerrufen, alles im Audit, und die Person sieht ihre Rechte
  auf `/me`.
- Revisionen, Sichtbarkeit privat/Team/alle, Export und Import als Datei,
  später als Pakettyp im Katalog.

Entschieden sind D1–D3 (Jörg, 19.11.), offen D4–D10 mit Empfehlungen.

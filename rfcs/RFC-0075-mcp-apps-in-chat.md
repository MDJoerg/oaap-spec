# RFC-0075: MCP Apps in the Chat — Views From Tool Servers, Sandboxed, Approved Like Tools

- **Status:** **Accepted (2026-11-08)** — Jörg: "akzeptiert" (D1–D8 as recommended); nothing built
- **Date:** 2026-11-08
- **Authors:** Jörg (direction: "we should look at MCP Apps, which is becoming
  the standard"; Markdown and Mermaid as standard in the chat), Claude (facts
  read in the extension specification, mapping to OAAP)
- **Depends on:** RFC-0074 (assistants, chat app, procedure A, D6),
  RFC-0065/0073 (MCP gateway, views, approval with pinned text, sources of the
  platform), RFC-0068 (closed egress), RFC-0018/0043 (instance names)
- **Changes (when accepted):** `oaap.ai.mcp-gateway` (UI resources in views),
  `oaap.ai.assistants` (whether an assistant may show views), chat app

## Summary

**MCP Apps** (extension `io.modelcontextprotocol/ui`, SEP-1865, specification
version 2026-01-26, a draft in progress) lets an MCP server ship an
**interactive view** with a tool: an HTML document under a `ui://` URI that
the host renders in a sandboxed iframe next to the tool's result. The view
talks to the host over JSON-RPC by `postMessage` — it can ask the host to call
tools, read resources, send a message into the conversation, open a link.

For OAAP this is the standard way to show **forms and tables of an app inside
the chat** (a Vorgang with its fields, a list with filters) instead of
inventing our own. This RFC proposes how the three places that would carry it
— the source app, the MCP gateway, the chat — do so without weakening what
RFC-0074 built: the person's rights, the view as default-deny list, the
confirmation of writing tools, closed egress.

## 1. Facts (read 2026-11-08)

Source: the extension specification 2026-01-26 and the draft, in
`modelcontextprotocol/ext-apps`. **Checked verbatim against the raw file on
2026-11-08** (D8): the points first marked (S) hold as written, with exact
shapes — client capability `capabilities.extensions["io.modelcontextprotocol/ui"]
= {"mimeTypes": ["text/html;profile=mcp-app"]}` (REQUIRED); host → view
`ui/notifications/tool-input` `{arguments}`, `tool-input-partial`, `tool-result`
(a `CallToolResult`), `tool-cancelled` `{reason}`, `host-context-changed`
(`Partial<HostContext>`), request `ui/resource-teardown` `{reason}`; view → host
`ui/message` `{role: "user", content: {type: "text", text}}`, `ui/open-link`
`{url}`, `ui/request-display-mode` `{mode}`, `ui/update-model-context`,
notification `ui/notifications/size-changed` `{width, height}`; the handshake
uses protocol version `2026-01-26`. **Correction:** the stable version
REQUIRES the sandbox proxy for a web host (double iframe, proxy on another
origin; `ui/notifications/sandbox-proxy-ready` `{}` and
`ui/notifications/sandbox-resource-ready` `{html, sandbox?, csp?, permissions?}`);
only the draft makes it non-normative. OAAP builds the proxy (D6 below holds:
the proxy runs on the second origin).

| Claim | Where |
|---|---|
| Negotiated extension `io.modelcontextprotocol/ui`; a client announces it under `capabilities.extensions` with the MIME types it renders (S) | spec §capabilities |
| A tool links its view with `_meta.ui.resourceUri`; `_meta.ui.visibility` (default `["model","app"]`); the flat key `_meta["ui/resourceUri"]` is deprecated "before GA" | spec |
| The view is a resource: URI starts with `ui://`, MIME `text/html;profile=mcp-app`, a full HTML5 document, fetched with `resources/read` (text or base64 blob) | spec |
| "Servers MAY omit UI-only resources from `resources/list`" — the host reads the URI the tool names | spec |
| `_meta.ui` on the content: `csp` (`connectDomains`, `resourceDomains`, `frameDomains`, `baseUriDomains`), `permissions` (camera, microphone, geolocation, clipboardWrite), `prefersBorder`; the host MUST enforce the declared domains and nothing else; without `csp`: `connect-src 'none'` | spec |
| A web host MUST render the view in an iframe of **another origin** than the host, sandbox `allow-scripts allow-same-origin`; 2026-01-26 requires a double iframe (sandbox proxy), the draft makes it non-normative and warns that the view document must be served by a server the host controls | spec, draft |
| View → host: `ui/initialize`, `ui/notifications/initialized`, `tools/call`, `resources/read`, `notifications/message`, `ping`; (S) `ui/message`, `ui/open-link`, `ui/request-display-mode`, `ui/update-model-context`, `ui/notifications/size-changed` | spec |
| Host → view: (S) `ui/notifications/tool-input`, `tool-input-partial`, `tool-result`, `tool-cancelled`, `host-context-changed`, `ui/resource-teardown`; nothing before the view said `initialized` | spec |
| The host MUST refuse a `tools/call` from a view for a tool without `"app"` in its visibility; tools with only `["app"]` MUST NOT appear in the model's `tools/list`; calls across servers from a view are refused | spec |
| The host MAY block non-`ui/` messages or ask the person; (S) `ui/message` and `ui/update-model-context` may need consent | spec |
| Draft adds: bidirectional `tools/call`, `sampling/createMessage` from the view (host approval), `ui/download-file`, `object-src 'none'` | draft |

Facts of OAAP that matter: the gateway passes a tool's `annotations` and, since
0.7.1, adds `_meta` `oaap/effect`; it **approves** tools, resources and prompts
individually with pinned text (default deny); `resources/read` is metered;
procedure A carries the person through the chat; a closed tenant's instances
start no connection of their own (RFC-0068); the chat renders Markdown and
Mermaid since 0.3.0 and runs no foreign HTML.

## 2. Proposal

### 2.1 Gateway: a view is approved with its tool

- A tool's `_meta.ui` is **passed on** in `tools/list` (with `oaap/effect`
  beside it). Its `ui://` resource is not listed by the server, so approving
  the **tool** also approves the **one** resource it names — pinned by
  fingerprint like the tool's text: a changed view suspends the tool until an
  operator confirms it, exactly as a changed description does today.
- `resources/read` of that `ui://` URI is allowed in the view that has the
  tool, and only that URI; it is metered like any read.
- **Visibility:** a tool with `visibility: ["app"]` is approved like others but
  never listed to the model (the chat filters, the gateway marks it). Whether
  the gateway or the chat enforces "only views may call it" is D3.
- `_meta.ui.csp`: the gateway shows the declared domains on the approval page;
  a view of a source whose light is green but that declares outside domains is
  flagged (RFC-0068: in a closed tenant it is refused, §2.3).

### 2.2 Chat: the host

- The chat announces the extension only for assistants that allow views (D2).
- **Another origin:** the view runs on a second name of the chat instance
  (an alias such as `chat-view.<tenant>.<node>`, RFC-0018) that serves one
  thing: a sandbox page that receives the HTML by `postMessage` and renders it
  under the CSP derived from `_meta.ui.csp` (default `connect-src 'none'`).
  The view never sees the chat's cookies or the person's assertion.
- **Calls from the view go through the same round as the model's** (D7): a
  `tools/call` from the view becomes a pending call in the conversation, so
  effect class, confirmation (D6) and `X-OAAP-Confirmed` apply unchanged. A
  view cannot write without the person's click on the chat's own card — the
  button inside the view is not enough (D4).
- `ui/message` puts text into the person's input field; it is not sent
  without the person (D5). `ui/open-link`: only http(s), opened in a new tab
  with `noopener`. `ui/update-model-context`, `sampling` and `download-file`:
  not in the first stage.

### 2.3 Closed tenants

A view in a closed tenant gets `connect-src 'none'`, `frame-src 'none'` and no
external `resourceDomains`, whatever it declares: the platform's promise that
nothing leaves is not delegated to a document from an app. A view that needs
an outside domain is shown with a sentence instead.

## 3. Decisions

| # | Proposal | Recommendation |
|---|---|---|
| **D1** | Adopt MCP Apps (`io.modelcontextprotocol/ui`) as the one way to show app views in the chat; no OAAP-own form format | yes |
| **D2** | An assistant gets a field `views: true` (default false); only then the chat announces the extension and renders views | yes |
| **D3** | Approving a tool approves the one `ui://` resource it names, pinned by fingerprint; the gateway refuses reading any other `ui://` URI | yes |
| **D4** | Writing calls from a view need the chat's own confirmation card, every time, like the model's (D6 of RFC-0074) | yes |
| **D5** | `ui/message` fills the input field, never sends | yes |
| **D6** | Views on a second origin of the chat instance (alias) — the sandbox proxy of the 2026-01-26 version there, the view in its inner iframe; CSP from `_meta.ui.csp`; closed tenants: no outside domains | yes |
| **D7** | First stage: render + `tool-input`/`tool-result` + `tools/call` + `resources/read` + `size-changed` + `open-link`; later: `update-model-context`, `sampling`, `download-file`, display modes | yes |
| **D8** | Build against the 2026-01-26 version and the draft's single-iframe allowance; re-read the text before building (several points above are from a summary) | yes |

**Decided (Jörg, 2026-11-08):** D1–D8 as recommended.

## 4. Stages

1. Gateway: pass `_meta.ui`, approve and pin the named `ui://` resource,
   `resources/read` for it; Vorgänge ships one view (a Vorgang as a card with
   status and comments) as the test source.
2. Chat: sandbox origin, render, input/result, `tools/call` through the
   round with confirmation, `open-link`, size.
3. Closed tenant measurement; `ui/message`; then the later methods.

## Deutsche Zusammenfassung

**MCP Apps** ist die Erweiterung des MCP-Standards, mit der ein Werkzeug eine
**interaktive Ansicht** mitbringt: ein HTML-Dokument unter `ui://…`, das der
Chat in einem abgeschotteten iframe neben dem Ergebnis zeigt (ein Vorgang als
Karte, eine Liste mit Filtern). Die Ansicht spricht mit dem Chat über
Nachrichten und kann ihn bitten, Werkzeuge aufzurufen, einen Link zu öffnen
oder Text vorzuschlagen.

Vorschlag für OAAP, ohne das Erreichte aufzuweichen:
- **Gateway:** Wer ein Werkzeug freigibt, gibt genau die eine Ansicht mit frei,
  die es nennt — festgehalten wie der Text; ändert sie sich, ist das Werkzeug
  gesperrt, bis jemand bestätigt.
- **Chat:** Die Ansicht läuft unter einem zweiten Namen der Chat-Instanz, sieht
  weder Kekse noch die Zusicherung der Person, und darf von sich aus nichts nach
  außen. Ruft sie ein schreibendes Werkzeug, erscheint dieselbe
  Bestätigungskarte wie beim Modell — ein Knopf in der Ansicht reicht nicht.
  Vorgeschlagener Text landet im Eingabefeld, nie direkt gesendet.
- **Geschlossener Mandant:** keine fremden Domains, egal was die Ansicht erklärt.
- **Entscheidungen D1–D8**, alle mit Empfehlung „ja“; gebaut wird erst nach
  deinem Wort und nachdem ich die als Zusammenfassung markierten Stellen der
  Spezifikation im Original gelesen habe.

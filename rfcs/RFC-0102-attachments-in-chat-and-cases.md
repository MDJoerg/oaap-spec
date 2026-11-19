# RFC-0102: Attachments in the Chat and in Cases — Files, Images, AI Artifacts and Views, and Which of Them Travel

- **Status:** Draft (2026-11-19). D1–D11 open, each with a recommendation.
  Nothing built.
- **Date:** 2026-11-19
- **Authors:**
  - Jörg (the wishes, after his first real case in `bec`): context as a
    file, an image and so on should be workable in the app `vorgaenge` and
    in the chat. When a person hands an answer to the support, they are
    asked whether and which attachments travel: uploaded by the person,
    created by the AI, later views of MCP Apps with their context.
  - Claude: reading of chat, cases and gateways; design.
- **Depends on:**
  - RFC-0061: cases, the attested feedback route, handover, Q6 retention.
  - RFC-0101: "not satisfied" as a case, D10 "nothing without the tick".
  - RFC-0075: views of MCP Apps, the sandbox origin.
  - RFC-0034: documents and file storage, accepted, nothing built.
  - RFC-0068: closed egress.
  - `oaap.ai.gateway` §7: the light.
  - `lib/mdview`: the shared rendering of chat and cases.
- **Related:**
  - RFC-0098 §4: call ids with consent.
  - RFC-0099: result views from the gateway.
  - RFC-0094: uploads in the help app.
- **Not part of this RFC:**
  - Full-text search over attachments.
  - OCR.
  - Editing a document in place.
  - An attachment fetched from a URL by the platform; closed egress stays.

## Summary

Today chat and cases carry text only. A person cannot show the error
message as a screenshot, the support cannot add the log file, and what an
assistant produced (a table, a diagram, an SVG, a view of an MCP App) is
gone the moment the person hands the conversation over. Four pieces close
that:

1. **An attachment record** in each app:
   - It holds identity, type and size; the identity is the SHA-256 of the
     bytes. It also names the origin: the person, the AI or a view.
   - It is shaped like a document of RFC-0034. When `oaap.data.documents`
     exists, the bytes move and the identity stays.
2. **Upload and safe display** in the chat, and in cases with the same
   rendering:
   - The type is decided from the bytes, never from the name.
   - Only an allow-list of types is accepted.
   - Nothing is executed. An SVG is shown only as an image.
3. **What the model sees.** An attachment goes to a model only when the
   person put it into the message:
   - text as text;
   - images only to an alias the AI gateway declares as able to see them;
   - never to a path worse than the conversation's light.
4. **Which attachments travel.**
   - The "not satisfied" dialog lists the attachments of that round by
     origin, each with a tick, off by default (like RFC-0101 D10).
   - Ticked attachments go to `vorgaenge` in two steps: the case names
     them, and the browser then uploads each one through the attested
     route.
   - In a handover to a partner they travel only when a handler ticks
     them.

## 1. Facts (read 2026-11-19)

| Place | Today |
|---|---|
| **chat** 0.13.0 | Messages are text, at most 4,000 characters. A request body is at most 64,000 bytes. History is one JSON file per conversation under `/data/people/<user id>/`, read only by that person. A tool result stays in the history (and, for a view, its `raw` result and arguments). There is no upload, no file and no image to the model. Rendering is `lib/mdview`: Markdown, Mermaid, and since 0.13.0 ```svg as an `<img>` with a data: address. |
| **vorgaenge** 0.7.0 | A case has a title (≤ 200), a body (≤ 10,000) and, since 0.6.0, `subkind` + `fields` (≤ 40,000 bytes), plus entries (comments, status). A request body is at most 64 KiB. Storage is SQLite in `/data`. There are no attachments. A handover carries title, body, chosen comments and a little technical data, never `fields`. Q6 removes the reporter's data after 12 months. Rendering is `lib/mdview` with "formatted / raw". |
| **feedback route** | `/platform/feedback` and `/platform/feedback/*` on the app's own origin. The gateway attests person and source and passes the body to `vorgaenge` unchanged. Its size limit at the gateway is not read yet (measure when building). |
| **AI gateway** | The chat sends text. Whether an alias passes OpenAI-style image parts (`image_url`) to its supplier, and how a capability "sees images" would be declared, is not read yet. `/v1/models` already reports a light per alias. |
| **RFC-0034** | `oaap.data.files` (backings) and `oaap.data.documents` (identity, versions, links). Accepted, nothing built. Its rule: an app holds the document's identity, never its location. |
| **RFC-0075** | A view is HTML under `ui://`, pinned by the MCP gateway and rendered by the chat in a sandbox on a second origin. The chat is the host and answers the view's requests as the person. |

## 2. The attachment record

| Field | Content |
|---|---|
| `id` | `sha256:<hex>` of the bytes. The same bytes in the same scope are stored once. |
| `name` | as the person named it (≤ 200), shown, never used to decide anything |
| `type` | decided from the bytes (magic numbers, then a parse), from the allow-list of §3 |
| `size` | bytes |
| `origin` | `person` (uploaded), `ai` (saved from an answer, with `assistant@rev`), `view` (a snapshot of an MCP App view, §6) |
| `light` | the conversation's light at the time it was added (RFC-0101 §2) |
| `scope` | chat: person + conversation; cases: case |
| `added_by`, `at` | who and when (in a case: the person's name, as for entries) |

- **Where the bytes live, stage 1:** in the app's own `/data`, one folder
  per scope. File names are the hash, never the person's name for the
  file.
- **Backups:** they include it like the rest of `/data`.
- **Later:** the bytes move to `oaap.data.documents` without the app
  changing what it stores (D1).

## 3. Upload and display

- **Types (D2):** PNG, JPEG, WebP, PDF, plain text, Markdown, CSV, JSON,
  SVG.
  - A file whose bytes say otherwise than its claimed type is refused
    with a sentence.
  - Archives, Office documents and executables are not in stage 1.
- **Sizes (D2):**
  - 10 MB per file;
  - 25 MB per message or per case step;
  - per person in the chat 200 MB;
  - each a tenant setting with these defaults.
  - Checked before the body is read in full.
- **Display:**
  - Images as `<img>`; SVG only as `<img>` with a data: or blob: address,
    so no script runs and nothing loads from outside.
  - PDF in the browser's viewer from a response with
    `Content-Security-Policy: sandbox` and `X-Content-Type-Options:
    nosniff`.
  - Text, Markdown, CSV and JSON through `lib/mdview` (Markdown
    formatted/raw, CSV as a table, JSON indented).
  - Everything else only as a download with `Content-Disposition:
    attachment`.
- **No scanner in stage 1 (D3).** The protection is the allow-list,
  deciding from the bytes, never executing, and the headers above. A hook
  for a scanner app (for example ClamAV as a catalog app) follows in
  stage 4.
- **Chat UI:** drop a file or paste an image into the input box. Each
  attachment shows as a chip with name, type and size, and a cross to
  remove it before sending. In the history it sits at the message, with a
  preview.

## 4. What the model sees

- An attachment reaches the model only as part of **the message the
  person sends with it**. Nothing is sent "because it is in the
  conversation".
- **Text types** go as text, clipped to the message limit with a visible
  note in the chat.
- **Images** go only to an alias whose AI gateway declares the capability
  (D4). The capability is read from `/v1/models` like the light.
  Otherwise the chat says "this model does not see images" before
  sending, not after.
- **PDF:** text extraction is not in stage 1. A PDF is stored and shown,
  and not sent to the model.
- **The light (D10):** an attachment is input like text. The
  conversation's light is the ceiling for it too, enforced by both
  gateways through `X-OAAP-Light` as today. Adding an attachment does not
  change the light; the person's choice of light already says what may go
  in.

## 5. AI artifacts

- **"Als Datei speichern"** on a code block, a Mermaid diagram, an SVG or
  a table of an answer makes an attachment of origin `ai`, with
  `assistant@rev` and the message it came from (stage 3).
- The assistant **cannot** create attachments by itself in stage 1–3. A
  tool that returns a file is RFC-0099 territory and gets its own
  section there.

## 6. Views of MCP Apps as context

A view (RFC-0075) is HTML plus the tool result it shows, called with
arguments. As an attachment of origin `view` (type
`application/vnd.oaap.view+json`, stage 3) it holds:

- tool name;
- the URI of the pinned view;
- the result;
- the arguments, only if the person ticks them (as RFC-0101 D10).

In `vorgaenge` it is shown **as data first**:

- the tool's name, the result formatted as JSON or as a table;
- the view's HTML is not rendered there in stage 3 (D7).

Rendering it needs a host that answers the view's requests read-only and
a sandbox origin like the chat's. That is a stage of its own once a case
needs it.

## 7. Which attachments travel with "not satisfied"

The dialog of RFC-0101 §4.1 gets a section "Anlagen dieser Runde":

- **What is listed:** every attachment of the round, grouped by origin:
  „von dir hochgeladen“, „von der KI erzeugt“, „Ansicht von <Werkzeug>“.
  Each shows name, type and size and has a preview.
- **The tick:** each attachment has its own tick, **off by default**
  (D5). Without a tick nothing travels.
- **What the case names:** the ticked attachments with name, type, size
  and hash (template field `attachments`). The case text says how many
  were withheld; it never says which.

**The way in (D6), two steps through the attested route:**

1. The browser posts the case as today, with `attachments: [{name, type,
   size, sha256}]`. `vorgaenge` answers `201` with the number and one
   upload token per attachment: single use, bound to this person and this
   case, valid for 15 minutes.
2. For each attachment the browser fetches the bytes from the chat (as
   the person) and posts them to
   `/platform/feedback/attachments/<token>` on the chat's own origin. The
   gateway attests the person again. `vorgaenge` checks that token,
   person, size and hash match, and refuses otherwise.

- An attachment that never arrives shows on the case as „angekündigt,
  nicht angekommen“. The case itself stands.
- The chat holds no key for cases and never files anything in the
  person's name (RFC-0101 §6.5 stays true).

## 8. Attachments in a case

- **Who adds them:** the reporter and whoever may comment can add
  attachments to an entry (same rules as comments).
- **Display and download:** with §3. Readers are whoever may see the
  case.
- **Retention (D8):**
  - Attachments added by the reporter are personal data of the reporter.
    Q6 removes them with the reporter's other data; the hash, type and
    size stay, so the history still says something was there.
  - Attachments added by handlers stay with the case.
- **Handover (D9):** nothing travels by default. The handover draft lists
  the attachments with a tick each, like the comments.
  - What is ticked travels with the handover document: hash in the
    document, bytes alongside.
  - The partner's limits apply. That is stage 4.

## 9. Security requirements

Each requirement names the bait a test uses.

1. **The type is decided from the bytes.** Bait: an HTML file named
   `bild.png` is refused, and so is a PNG header followed by HTML.
2. **Nothing executes:**
   - An SVG with `<script>` and an external `<image href>` is shown only
     as `<img>`: the script does not run, nothing is fetched.
   - A download carries `Content-Disposition: attachment`,
     `Content-Security-Policy: sandbox` and `nosniff`.
   - Bait: SVG with `onload`.
3. **Scope is a wall:**
   - Bert cannot fetch Anna's chat attachment by its id: `404`, like an
     unknown one.
   - A case attachment is readable only by those who see the case.
   - Bait: the same hash uploaded by Bert gives him no access to Anna's
     copy.
4. **Nothing without the tick.**
   - Without a tick no attachment travels with "not satisfied"; with
     ticks exactly the ticked ones arrive (hash compared).
   - Bait: a request that names an unticked attachment's hash in step 2
     is refused.
5. **Tokens:** single use, bound to person and case, 15 minutes. Bait:
   Bert uses Anna's token and gets `403`; a second use gets `410`.
6. **Light and capability:**
   - An attachment never reaches a model on a path worse than the
     conversation's light.
   - An image never reaches an alias without the capability.
   - Bait: `X-OAAP-Light: green` on a yellow alias with an image is
     refused by the AI gateway as today.
7. **Closed egress:** no "attach from URL". The platform fetches nothing
   on behalf of an attachment.
8. **Limits before reading:**
   - A body above the limit is refused before it is read in full.
   - Bait: `Content-Length` above the limit gets `413` with the body
     unread.

## 10. Decisions

- **D1 Where the bytes live.** *Recommendation:* in each app's own
  `/data`, behind the record of §2, shaped for a later move into
  `oaap.data.documents`.
  - Alternative: wait for RFC-0034. Nothing of it is built, and the
    wishes are concrete now.
  - Alternative: a shared attachment service. That is new core, and
    RFC-0034 is already that service.
- **D2 Types and sizes.** *Recommendation:* the allow-list and limits of
  §3 as defaults, sizes as tenant settings. Office documents and archives
  later, once a scanner exists.
- **D3 Scanner.** *Recommendation:* none in stage 1; allow-list, deciding
  from the bytes, no execution and safe headers instead. A scanner hook
  in stage 4.
- **D4 Images to the model.** *Recommendation:* only to aliases whose
  AI gateway declares the capability (a new field next to the light in
  `/v1/models`, set by the operator per alias). Never guessed from the
  model's name.
- **D5 Default of the tick.** *Recommendation:* off, per attachment, like
  RFC-0101 D10.
- **D6 Transport into `vorgaenge`.** *Recommendation:* two steps through
  `/platform/feedback/*` with single-use tokens.
  - Alternative: Base64 in the JSON with a larger limit. That costs a
    third more bytes, makes the gateway's body limit the attachment limit,
    and brings no resumption.
  - Alternative: chat backend → `vorgaenge` backend door. Rejected by
    RFC-0101 §4.3: the chat would file cases in anyone's name.
- **D7 Views in a case.** *Recommendation:* as data in stage 3. The HTML
  is rendered only once a read-only host with its own sandbox origin
  exists in `vorgaenge`.
- **D8 Retention of attachments in a case.** *Recommendation:* the
  reporter's attachments go with Q6 (hash, type and size stay); the
  handlers' attachments stay.
- **D9 Handover.** *Recommendation:* per attachment a tick in the draft,
  nothing by default; stage 4.
- **D10 Light.** *Recommendation:* no new light per attachment. The
  conversation's light covers what the person puts in, and the gateways
  enforce it as today.
- **D11 Quotas and cleanup in the chat.** *Recommendation:* 200 MB per
  person (tenant setting). Attachments go with their conversation, and a
  daily sweep removes bytes no record names.

## 11. Stages and tests

| Stage | Content | Done when |
|---|---|---|
| 1 | Chat: upload (drop, paste), record, safe display, download; text files and (with the capability) images to the model; quota | an image goes to a vision alias and not to another (with a sentence before sending); baits 1, 2, 3, 6, 8 hold |
| 2 | Cases: attachments on entries, display with `lib/mdview`, Q6; "not satisfied" lists attachments with ticks, transport in two steps | a ticked screenshot arrives in the case with the same hash; an unticked one does not (bait 4); Bert cannot use Anna's token (bait 5) |
| 3 | AI artifacts („Als Datei speichern“), views as `application/vnd.oaap.view+json` shown as data | a saved Mermaid diagram is an attachment with `assistant@rev`; a view travels with its result, arguments only with the tick |
| 4 | Handover with attachments, scanner hook, move to `oaap.data.documents` once built | a ticked attachment arrives at the partner with its hash; an unticked one does not |

Spec changes:
- `oaap.ai.assistants` (§2c: attachments in "not satisfied");
- `oaap.ai.gateway` (§7 or a new section: the capability "sees images"
  per alias in `/v1/models`);
- `oaap.apps.runtime` (nothing: the feedback route already covers
  `/platform/feedback/*`);
- READMEs of chat and `vorgaenge`.

## Zusammenfassung auf Deutsch

Chat und Vorgänge kennen heute nur Text. Ein Screenshot der Fehlermeldung,
eine Logdatei, eine Tabelle oder ein Diagramm des Assistenten, eine
Ansicht einer MCP App: Nichts davon kommt beim Support an. Der Entwurf
schlägt vier Teile vor.

1. **Anlage als Datensatz in jeder App.**
   - Die Kennung ist der SHA-256 der Bytes.
   - Dazu kommen Typ, Größe und Herkunft: von der Person, von der KI
     oder eine Ansicht.
   - Die Ampel des Gesprächs wird beim Hinzufügen festgehalten.
   - Die Bytes liegen vorerst unter `/data` der App. Der Datensatz ist so
     geschnitten, dass sie später in die Dokumentenablage aus RFC-0034
     umziehen können.
2. **Hochladen und sicher anzeigen.**
   - Der Typ wird aus den Bytes bestimmt, nie aus dem Namen. Es gilt eine
     Erlaubnisliste: Bilder, PDF, Text, Markdown, CSV, JSON und SVG.
   - Größen: 10 MB je Datei, 25 MB je Nachricht, 200 MB je Person im
     Chat.
   - Nichts wird ausgeführt: SVG nur als Bild, Downloads mit sicheren
     Kopfzeilen.
   - Einen Virenscanner gibt es erst später.
3. **Was das Modell sieht.**
   - Eine Anlage geht nur mit, wenn die Person sie in die Nachricht legt.
   - Text geht als Text.
   - Bilder gehen nur an ein Modell, dem das KI-Gateway „sieht Bilder“
     bescheinigt.
   - Die Ampel des Gesprächs gilt auch für Anlagen.
4. **Was mitreist.**
   - „Nicht zufrieden“ zeigt die Anlagen der Runde nach Herkunft. Jede
     hat einen Haken, und der ist zunächst aus.
   - Angekreuzte Anlagen gehen in zwei Schritten an die App Vorgänge:
     Der Vorgang nennt sie mit Prüfsumme, dann lädt der Browser jede über
     die bezeugte Route hoch, mit Einmal-Token.
   - In einer Übergabe an einen Partner reist eine Anlage nur, wenn eine
     bearbeitende Person sie ankreuzt.
   - Anlagen der meldenden Person fallen mit der Löschfrist weg.

**Stufen:**
1. Chat: hochladen, anzeigen, ans Modell.
2. Vorgänge: Anlagen und Auswahl bei „Nicht zufrieden“.
3. KI-Artefakte („Als Datei speichern“) und Ansichten von MCP Apps, als
   Daten.
4. Übergabe mit Anlagen, Virenscanner, Umzug in die Dokumentenablage.

Offen sind D1–D11, jeweils mit Empfehlung.

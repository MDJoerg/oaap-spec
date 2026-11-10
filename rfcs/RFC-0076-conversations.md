# RFC-0076: Conversations — Channels Underneath, People and Objects on Top

- **Status:** **Draft (2026-11-10)** — three decisions taken by Jörg on
  2026-11-10 (D1 app, D2 delete after backup, D3 not Bernd); the rest
  proposed (§12). **Nothing built; building comes later (Jörg).**
- **Date:** 2026-11-10
- **Authors:** Jörg (the idea, after Odoo's mail integration: the channel is
  transport, the user sees a conversation at the person or object; collecting
  mailboxes; delete on the server; multi-channel routing; graph and similarity
  search; private and temporary rights), Claude (facts read in the specs and
  apps, design)
- **Depends on:** RFC-0072 (SMTP mailbox per node and per tenant),
  RFC-0033 / `oaap.net.destinations` (secrets, bindings), RFC-0068 (closed
  egress), RFC-0029 / `oaap.data.backup` (scheduled archives), RFC-0031 /
  `oaap.data.twin` (who an address belongs to), RFC-0045 and RFC-0067
  (permissions, contexts), RFC-0057 (a database for an app), RFC-0016
  (multi-container apps)
- **Related, not decided here:** RFC-0061 (Vorgänge — a conversation may lead
  to a case), RFC-0074/0075 (assistants, views in the chat), RFC-0064 / AI
  gateway (`embedding-default`), RFC-0032 (events, relay to Telegram/ntfy),
  RFC-0053 (vault, off-site pull)
- **Idea store:** I-47
- **Driver:** RFC-0072 gave every realm a way to send. Receiving is missing,
  and so is the place where a message belongs. Jörg's scenario: one shared
  mailbox with little space, which no person ever opens in a mail client.
  OAAP collects everything from it, files each message under the person or
  object it concerns, answers from there, and empties the server. Later
  Telegram, WhatsApp and others feed the same inboxes.

## Summary

A **conversations app** (one instance per tenant) owns all messages of the
tenant. **Channel adapters** inside the app fetch and send: mail first (IMAP
in, SMTP out), messengers later. A message lands in an **inbox** ("Sales",
"Vorstand") by routing rules, joins a **conversation** (the internal bracket),
and the sender's **address** (typed: e-mail, phone, messenger id) is resolved
to an object of the **digital twin** — customer, supplier, member, employee,
user account. A reply always leaves through the channel account the
conversation came in on. Internal notes never leave.

On the server, every mailbox gets its own **fetch policy**: which own
recipient addresses are collected, and whether a collected message is marked
read, moved into a generated folder, or **deleted — only after a backup has
covered it** (D2). For that the platform gains one new signal: *when did a
successful archive last contain this instance's data* (§5). Mails the
platform itself sends (Keycloak) go through a small **relay** on the node, so
a copy is kept and filed under the user account (§4).

The raw message is kept unchanged and is the source of truth. Full-text
search, the graph of who-talked-with-whom-about-what, and optional
**embeddings** for similarity search are projections that can be rebuilt
(§8). Every read path — list, object page, search, graph, MCP, assistants —
filters by the reader's rights **before** it ranks or counts (§7).

## 1. Facts (read 2026-11-10)

- **Sending exists, receiving does not.** `oaap.net.destinations` 0.9–0.11:
  kind `smtp` (`smtps://` TLS or `smtp://` with STARTTLS, no plain text); one
  mailbox per node (destination `mail` of the default tenant), since stage 2 of
  RFC-0072 one per tenant, entered in the portal "Nachrichten". RFC-0072 D7:
  **apps cannot bind a mailbox**; stage 3 (apps send through the tenant's
  mailbox by the existing TCP binding) is not built. Nothing in the reference
  speaks IMAP.
- **Keycloak sends by itself.** The realm holds the SMTP block including the
  password (RFC-0072 D4). OAAP sees nothing of what Keycloak sends.
- **Backup knows nothing an app could ask.** `oaap.data.backup`: a backup is
  one archive per node, holding every instance's storage; a schedule is
  optional and owned by systemd (2.4); the vault (RFC-0053) pulls archives
  off-site. No interface tells an instance *"your data as of time T is in an
  archive"*.
- **The twin can hold the people, not yet find them.** `oaap.data.twin` 0.4:
  objects, `source_keys`, groups, attributes, relations, activities — all
  append-only; merge only by a human. **`/twin/references` (search) is not
  built**, and **restricted groups are not built**: every person of the
  tenant reads every group. The partner app owns `Customer` and `Person`
  (`isContactOf`), the employee app owns `Mitarbeiter` with e-mail and phone.
  The twin's own target picture (idea store, "Datenplattform-Vertiefung",
  point 4) puts events and documents in the category "only referenced, never
  a full twin" — a message is exactly that.
- **A database per app** is accepted (RFC-0057, stage 0 built); stages 1–3
  (the managed Postgres an app declares) are not built.
- **Untrusted HTML has a place.** RFC-0075 built a second origin
  (`<instance>--ui.<rest>`) without cookie or identity for sandboxed views.
- **Embeddings** are an AI-gateway name (`embedding-default`); RFC-0068 lets a
  tenant close egress so nothing leaves the node.
- **Vorgänge** is one instance per tenant with channel inboxes per app
  (RFC-0061); a conversation and a case are different things (§2.5).

## 2. The model

### 2.1 Words

| Term | Meaning |
|---|---|
| **Channel** | a transport kind: `mail`, later `telegram`, `whatsapp`, `signal`, `sms` |
| **Channel account** | one concrete access: a mailbox (IMAP+SMTP), a Telegram bot, a WhatsApp number |
| **Address** | typed and normalized: `mailto:anna@example.com`, `tel:+4917…`, `telegram:123456` |
| **Inbox** | a destination for routing, e.g. "Sales", "Vorstand", "Personal: Jörg"; has members (a group) |
| **Conversation** | the internal bracket: an ordered set of messages with participants, an inbox, links |
| **Message** | `in`, `out` or `note` (internal); raw form kept, normalized text derived |
| **Link** | conversation ↔ twin object, user account, case (Vorgang) |

### 2.2 Routing

A channel account delivers into one or more inboxes by rules, evaluated in
order: own recipient address (`sales@` → Sales), sender address or its twin
object (a known supplier → Purchasing), channel, keywords as the last resort.
One inbox may be fed by several channel accounts (Jörg's "Sales from several
sources"). Unmatched messages go to the tenant's default inbox, never nowhere.

### 2.3 Answering

A reply leaves through **the channel account and the address the last
inbound message came from** (D-reply, §12 D10). Changing the channel ("answer
this mail on Telegram") is an explicit act, offered only where the
participant has a known address on that channel.

### 2.4 Notes

`note` messages are internal. The interface MUST make sending and noting two
different actions with different looks (Odoo: "Send message" vs. "Log
note"); a channel adapter MUST refuse a `note`.

### 2.5 Conversation and case

A conversation is communication, a case (RFC-0061) is work with a state. A
conversation MAY create or join a case; the case then shows the conversation,
the conversation shows the case. Neither owns the other.

## 3. Mail in and out

### 3.1 Fetch policy per mailbox

| Setting | Values |
|---|---|
| **Collected addresses** | list of own recipient addresses (match on `Delivered-To`, `X-Original-To`, `To`, `Cc`), or "all"; plus an exclude list |
| **Folders read** | default `INBOX`; more by name |
| **After collecting** | `mark-read` · `move` into a generated folder (pattern, e.g. `OAAP/{yyyy}-{mm}` or `OAAP/{inbox}`) · `delete-after-backup` |
| **Sent folder** | `leave` · `move` · `delete-after-backup` (some providers store a copy of what is sent by SMTP) |
| **Interval** | polling; IMAP IDLE where the server offers it |

A message that matches **no** collected address is **not touched** — not
marked, not moved. OAAP must not change what it does not take.

### 3.2 The life of a collected message

`fetched` → `stored` (raw bytes durable in the app's storage, SHA-256
recorded, parsed) → `covered` (a backup archive newer than `stored` exists,
§5) → server action done. Until `covered`, a `delete-after-backup` mailbox
marks the message read and MAY move it to `OAAP/pending`. Identity on the
server: `UIDVALIDITY`+`UID`; identity across servers: `Message-ID` plus hash.
Fetching twice is harmless.

### 3.3 Threading

In order: (1) `In-Reply-To` / `References` against Message-IDs we recorded
(our outgoing Message-IDs are generated by us and recorded before sending);
(2) a plus-address token (`sales+c7f3@…`) where the provider delivers
sub-addresses; (3) a short token in the subject; (4) otherwise a new
conversation. A person MAY move a message into another conversation.

### 3.4 Loops and bounces

Messages with `Auto-Submitted` other than `no`, `Precedence: bulk|list|junk`,
or a delivery status notification never trigger an automatic reply. A
bounce marks the address as failing at the participant.

### 3.5 Space

Where the server offers the IMAP `QUOTA` extension, the fill level is shown
per mailbox; a warning before it is full. A mailbox whose node has no backup
schedule never reaches `covered` — the page MUST say so instead of filling
up silently.

## 4. The platform's own mail: a relay

Keycloak (and later other platform senders) submits to a **relay on the
node**, reachable only from inside, instead of the real mailbox.

- The realm gets **relay credentials per tenant**; the real mailbox password
  leaves the realm. This narrows RFC-0072 D4 ("the password also lives in the
  realm") as a side effect.
- The relay forwards to the tenant's mailbox (or the node's, as today) and,
  if the tenant has a conversations instance, hands it a copy as an `out`
  message, linked to the **user account** of the recipient (e-mail ↔ account
  via identity).
- Without a conversations instance the relay only forwards and keeps nothing.
- The relay belongs to the platform because the realms do (RFC-0041); the
  app only receives.

## 5. "Delete after backup": the new platform signal

The platform publishes per instance: **`covered_until`** — the start time of
the newest successful archive that contains this instance's storage — and,
where a vault pulled that archive, **`offsite_until`**. The app reads it (an
internal endpoint or a file in its storage; to be decided in the spec) and
performs server-side deletes only for messages `stored` before that time.

- A failed or missing backup leaves `covered_until` unchanged: nothing is
  deleted, the mailbox fills, the page warns (§3.5). Failing safe is the point.
- Restore: an instance restored from an archive gets that archive's time as
  `covered_until`, never a later one.
- Per mailbox: whether `covered` means the local archive (default) or the
  off-site copy (§12 D6).

## 6. Who an address belongs to

- Exact match of a normalized address against twin objects of the tenant
  (attributes or `source_keys` of the owning apps: partner, employee, member)
  and against user accounts. One hit → linked automatically. Several or none
  → a **suggestion**; a person confirms. Merging stays human (twin §2.9).
- Unknown sender → "unknown contact" with one action to create it in the
  owning app (the conversations app never becomes the owner of people).
- This needs a lookup by address in the twin, which does not exist
  (`/twin/references`, §1) — a dependency, not a workaround.
- In the twin, a conversation appears as an **activity or relation** on the
  object (reference only, D7); its content stays in the app.

## 7. Rights, privacy, untrusted content

### 7.1 Visibility of a conversation

| Level | Who reads |
|---|---|
| **inbox** (default) | members of the inbox's group |
| **private** | the owner and named delegates; default for personal addresses |
| **shared until** | additionally named persons or groups, with an end date; revocable; logged |

Changing a conversation's visibility is logged in the tenant audit. A
temporary share ends by itself, like a cohort (RFC-0046).

### 7.2 Rules for every read path

1. Filter **before** ranking, counting or summarizing. A hit count, a
   suggestion ("this address also talks to project B"), a graph edge or a
   neighbour in the vector index must not reveal a conversation the reader
   may not see (the open point "discovery reveals" of the research platform,
   idea store).
2. The twin object page shows only conversations the reader may see — and
   no count of the others.
3. Assistants and MCP tools act with the token of the person who speaks
   (RFC-0074); the app applies the same rules.
4. `note` never leaves; a share never includes the ability to answer unless
   granted.

### 7.3 Untrusted content

- HTML mail is rendered only on the sandbox origin (RFC-0075 pattern),
  remote images blocked by default (tracking pixels), scripts never.
- Attachments are offered for download; inline preview only for images and
  PDF in the sandbox.
- Message text given to an assistant is marked as external content (prompt
  injection); writing tools stay behind confirmation (RFC-0074 D6).

### 7.4 Retention and deletion

- Retention per inbox (business letters 6 years, booking records 10 years in
  Germany — GoBD); within retention, messages are immutable.
- A deletion request (GDPR) deletes the message and its projections and
  leaves a tombstone in the audit. Archives keep it until their generation
  rotates out — this is stated, not hidden.
- This collides with retention for business letters; which wins per inbox is
  a tenant decision, shown on the inbox.

## 8. Search, graph, embeddings

- **Storage:** messages and projections live in the app's own database
  (RFC-0057 once built; until then the app's storage). The twin holds
  references only (D7).
- **Full text** over normalized text and attachment text.
- **Graph:** participants, addresses, conversations, linked objects and cases
  as nodes and edges — queryable as "everything with supplier X in 2026",
  "who else wrote about project Y". A dedicated graph database only when a
  measured query needs it.
- **Embeddings:** opt-in per tenant and per inbox, through the AI gateway's
  `embedding-default`, **local by default**; a closed tenant (RFC-0068) never
  sends text out. Similarity search obeys §7.2.
- **MCP:** the app declares an MCP door (RFC-0073): search, read a
  conversation, draft a reply (sending only after confirmation); a view in
  the chat (RFC-0075) for a conversation.

## 9. Further channels (each later, own stage or RFC)

- **Telegram:** a bot per channel account; the person must write to the bot
  first; long polling works without a public route (home lab).
- **WhatsApp:** only through Meta's Business API: outside a 24-hour window only
  approved templates, costs per conversation, content passes Meta — not for a
  closed tenant.
- **Signal:** no official bot interface; only unofficial clients — not before
  a separate risk decision.
- **SMS:** through a gateway provider as a destination.

## 10. Not part of this RFC

- A mail client for people: no IMAP access for users, no folders of their own.
- Bulk mail, newsletters, marketing.
- S/MIME and PGP (later; the raw form is kept, so signatures stay checkable).
- Spam filtering (left to the provider; a "this is spam" action moves the
  message out of the inbox).
- Calendar invitations beyond showing them.

## 11. Stages (proposed)

1. **Mail, one mailbox:** channel account, fetch policy (§3.1, all three
   actions, delete only after `covered`), inbox, conversation, threading,
   reply, note; link to a twin person by exact address. Platform part:
   `covered_until` (§5). Leading case on oaap-test, synthetic (§12 D3).
2. **Relay** for the platform's own mail, copies filed under the user account
   (§4).
3. **Rights:** private, delegates, temporary shares, audit (§7).
4. **Search:** full text, graph view, embeddings opt-in, MCP door and chat
   view (§8).
5. **Telegram** as the second channel (§9).

Every stage is measured on oaap-test before it is pushed; nothing reaches
another node without Jörg's word.

## 12. Decisions

| # | Proposal | Recommendation |
|---|---|---|
| **D1** | Conversations are an **app** (one instance per tenant), not part of the platform | **decided (Jörg, 2026-11-10)** |
| **D2** | Server-side deletion **only after a backup** covered the message (§5) | **decided (Jörg, 2026-11-10)** |
| **D3** | Leading case **not Bernd**. Proposal: a club tenant, synthetic on oaap-test — shared mailbox `info@` (little space, fetch and delete), inboxes "Vorstand" and "Mitglieder", one private conversation of the treasurer, a temporary share with the auditors (Kassenprüfer) until a date, Keycloak mails filed under the accounts | Bernd excluded **(decided)**; club case proposed |
| **D4** | Channel adapters run **inside the app** (own container, RFC-0016); the mailbox reaches the app by a destination binding — this lifts RFC-0072 D7 **for this app only** (manifest declares the need, `tenant_admin` binds) | yes |
| **D5** | Platform mail goes through a **relay on the node**; realms get relay credentials, not the mailbox password (§4) | yes |
| **D6** | `covered` means the local archive by default; per mailbox switchable to "off-site copy too" (§5) | yes |
| **D7** | Messages live in the app's database; the twin holds **references only** (activity/relation on the object) | yes |
| **D8** | Default visibility **inbox**; personal addresses **private**; temporary shares with an end date (§7.1) | yes |
| **D9** | Embeddings **opt-in**, local model by default, never for a closed tenant through a cloud model | yes |
| **D10** | A reply leaves through the channel account and address of the last inbound message; switching channel is explicit | yes |
| **D11** | Second channel **Telegram**, WhatsApp only after a cost/data decision | yes |
| **D12** | App id and title: `konversationen` / "Konversationen" (the portal menu "Nachrichten" stays the place for channel settings of the platform) | open — name to be chosen by Jörg |

## Deutsche Zusammenfassung

**Worum es geht:** Nach dem Postausgang (RFC-0072) kommt der Eingang, nach
Odoos Vorbild: Der Kanal ist nur Transport. Die Anwender sehen
**Konversationen** an einer Person oder einem Objekt (Kunde, Lieferant,
Mitglied, Mitarbeiter, Benutzerkonto), keine Postfächer. Eine Antwort in der
Konversation geht als Mail zurück. Intern hält eine „Klammer“ die Nachrichten
zusammen.

**Entschieden (Jörg, 10.11.):** (D1) Das wird eine **App**, eine Instanz je
Mandant. (D2) Auf dem Server wird **erst nach einem Backup gelöscht**. (D3)
**Nicht Bernd** als Leitfall. Vorschlag stattdessen: ein Vereinsmandant,
synthetisch auf oaap-test.

**Wie es gedacht ist:**
- **Kanal-Adapter** in der App holen ab (IMAP) und senden (SMTP), später
  Telegram und andere.
- Je Postfach ist einstellbar, **welche eigenen Empfänger-Adressen** abgeholt
  werden. Danach wird die Mail auf dem Server **als gelesen markiert**, **in
  einen generierten Ordner verschoben** oder **gelöscht**. Dasselbe gilt für
  den Gesendet-Ordner. Was nicht passt, wird nicht angefasst.
- **Eingangskörbe** wie „Sales“ bekommen Nachrichten über Regeln, auch aus
  mehreren Quellen. Die Antwort geht immer über die Ursprungsquelle.
- **Adressen sind typisiert** (Mail, Telefon, Messenger-ID). Der Zwilling
  sagt, wem eine Adresse gehört. Bei genau einem Treffer wird automatisch
  verknüpft, sonst bestätigt ein Mensch.
- **Interne Notizen** verlassen das Haus nie und sehen anders aus als
  Antworten.
- Zuordnung der Antworten über die Mail-Kopfzeilen, Plus-Adressen und ein
  Kürzel im Betreff. Abwesenheitsnotizen und Bounces lösen keine Antwort aus.

**Neu in der Plattform:**
- (1) Ein Signal **`covered_until`**: Bis wann sind die Daten dieser Instanz
  sicher in einem Archiv? Heute erfährt eine App das nicht. Ohne Backup wird
  nichts gelöscht, und die Seite warnt.
- (2) Ein **Relais** auf dem Knoten für die Mails von Keycloak. Wir behalten
  eine Kopie und hängen sie an das Benutzerkonto. Nebenbei verschwindet das
  echte Postfach-Passwort aus dem Realm.

**Rechte:**
- Sichtbarkeit je Konversation: Eingangskorb, privat oder **befristet
  freigegeben**.
- Suche, Graph, Ähnlichkeitssuche, MCP und Assistenten filtern **vor** dem
  Ranking, damit nicht einmal Trefferzahlen etwas verraten.
- HTML-Mails werden nur in der Sandbox-Herkunft angezeigt, fremde Bilder sind
  standardmäßig gesperrt.
- Aufbewahrung (GoBD) und Löschung (DSGVO) werden je Eingangskorb geregelt.

**Suche und Graph:** Die Rohnachricht bleibt unverändert die Wahrheit.
Volltext, Graph und optionale Embeddings sind abgeleitete Projektionen, die
man neu aufbauen kann. Embeddings laufen lokal, über das KI-Gateway, und nur
auf Wunsch. Der Zwilling hält nur Verweise. Eine eigene Graph-Datenbank kommt
erst, wenn eine gemessene Abfrage sie braucht.

**Stufen:** (1) ein Postfach mit allem Nötigen inkl. `covered_until`, (2)
Relais, (3) Rechte, (4) Suche/Graph/Embeddings/MCP, (5) Telegram.

**Offen für Jörg:** D3 (Vereinsfall als Leitfall?), D4–D11 wie empfohlen?,
D12 der Name der App.

**Abhängigkeiten, die noch fehlen:** Suche im Zwilling (`/twin/references`),
Datenbank je App (RFC-0057 Stufen 1–3), Stufe 3 von RFC-0072 (Apps binden ein
Postfach).

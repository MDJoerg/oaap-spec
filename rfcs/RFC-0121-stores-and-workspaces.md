# RFC-0121: Stores and Workspaces — a Person's Context for the Chat

- **Status:** **Accepted (2026-11-23)** — D1–D7 decided in conversation
  (§12.1), D8–D17 as recommended (Jörg: "Wie empfohlen"). Nothing built, nothing measured for this RFC. The
  facts in §1 were read the same day in the specs, the manifests of `chat`
  0.21.0 and `projekt` 0.3.2, RFC-0067, RFC-0103, RFC-0110, RFC-0111, RFC-0114
  and the PCH repository (`pch-root`, 0.8.0); what was **not** read or measured
  is listed in §1.3.
- **Date:** 2026-11-23
- **Authors:** Jörg (the idea, 2026-11-23: "im Chat nicht den Assistenten
  auswählen, sondern einen Kontext … mehrere Ablagen mit Rollen und Aliasen …
  vielleicht passt der Begriff Arbeitsraum … eine API/Connector/
  Integrationskonzept, was wir vorgeben und für Forgejo, Bookstack, BDT
  implementieren"), Claude (facts, design)
- **Depends on:** RFC-0065 (views, default deny), RFC-0066 (the platform's
  assertion of a person), RFC-0067 (contexts, delegation), RFC-0073 (apps as MCP
  sources), RFC-0074 / RFC-0097 (assistants live in the MCP gateway), RFC-0095
  (`/me`, personal credentials, procedure U), RFC-0101 (the light per
  conversation), RFC-0110 (the wiki contract and its adapter), RFC-0114 (target
  systems: several systems of one kind), RFC-0116 stage 2 (foreign content)
- **Related:** RFC-0111 (credentials in one place, Draft), RFC-0117 / RFC-0119
  (templates), RFC-0034 (`oaap.data.files` / `oaap.data.documents` — a
  different thing, see §2.3), idea I-65 (index service)
- **Changes (when accepted):** two new specifications, `oaap.work.stores` (the
  contract a connector answers) and `oaap.work.workspaces` (the object and its
  rules); `oaap.ai.mcp-gateway` (objects *store system* and *workspace*, the
  store door); `chat` (start a conversation in a workspace, state and log,
  export); connectors for Forgejo and PCH first, BookStack and BDT next
- **Not part of this RFC:**
  - **Tasks and decisions in the chat** (a request with prepared answers, the
    task list, the Eisenhower view, other senders). Decided 2026-11-23: an
    extension of the app `vorgaenge` (D6); it gets its own RFC. This RFC only
    reserves the place where a finished decision is filed (§5.2).
  - **A workflow engine (BPMN).** Later, by Jörg's word.
  - **The group chat** — several people in one conversation. An option and a
    later stage (D4); §9 names what it would need, nothing more.
  - **Copies and synchronisation.** A connector works on the system itself. A
    product that keeps a working copy (PCH) does so on its own.
  - **Binary and office documents.** Stage 1 reads and writes text (Markdown).
    Other files are listed and refused in words.
  - **A search index across stores.** A connector searches its own system as
    the person. One index for all is idea I-65.

## Summary

Today a conversation in the chat begins with an **assistant**. What the
assistant knows about the person's work is what the person types. People who
work on projects keep their knowledge elsewhere: in a Git repository, a wiki
book, a project folder — Markdown mostly, the way a local folder or an Obsidian
vault holds it. A new conversation starts from nothing.

This RFC adds two things:

1. A **store contract**. A *connector* makes one kind of system (Forgejo,
   BookStack, BDT, PCH, later others) answer the same few verbs: what is there,
   read, write, search, what may this person do. The tenant admin registers
   **store systems** — several of one kind are normal. Every call runs **as the
   person**, on the system itself; the system alone decides what the person may
   see and change.
2. The **workspace** ("Arbeitsraum"): a named set of **stores** — each with an
   **alias** and a **role** (*source*: read only, *work*: read and write) — plus
   the assistants to work with. Exactly one store is the workspace's **home**:
   there lie the *state* ("Stand"), the *log* ("Protokoll") and what the person
   files from a conversation. A conversation started in a workspace begins with
   the state of the last one.

A workspace is **private**, a **team's**, or the **tenant's**. Being a member
grants nothing in a store: each person works with their own rights there. The
one exception is deliberate and narrow — the lead of a team workspace may hand
a guest the right to work in **one folder** of a store, never the whole store,
for a limited time (stage 4).

## 1. Facts (read 2026-11-23)

### 1.1 What exists

| # | Fact |
|---|---|
| F1 | A conversation belongs to one person and one assistant; the history lies per person under the chat's `/data` (`chat` 0.21.0, manifest description; `store.py`). |
| F2 | An assistant is a prompt, a model name and optionally ONE view; it has no rights; it lives in the MCP gateway (RFC-0097, `oaap.ai.assistants`). Assistants are private, a team's or the tenant's (`chat` since 0.2.0). |
| F3 | Every tool call runs as the person who writes; what changes something waits for the person's consent (`chat`, procedure A). |
| F4 | A conversation carries a light (green, yellow, red); the chat takes only models and views up to that colour and sends it to both gateways (RFC-0101 stage 1). |
| F5 | The MCP gateway knows *target systems* — several systems of one kind behind one selection of tools, chosen by an argument, with a landscape the chat can read (RFC-0114, built). |
| F6 | An app can be an MCP source; the gateway passes the person through (RFC-0073). `projekt`, `vorgaenge` do so today. |
| F7 | RFC-0110 (Accepted, stage 1 not built) defines `oaap.data.wiki`: verbs `spaces`, `read`, `search`, `write`, `may`, `changes`, `people`, `act_as`, and **`never: decide`**. Its adapter lives in the wiki's package and calls BookStack as the person through a short-lived token (`act_as`, measured). |
| F8 | RFC-0067 (built to stage 3, not rolled out) gives `/authz/delegate/*`: a person hands on a collection of rights, in a context, until a date; logged with both names. |
| F9 | `vorgaenge` already has responsible and assigned persons, the sub-status `waiting_reporter`, the way back into the chat (red dot, view "Vorgänge"), and `cases.submit` for other senders (RFC-0061, RFC-0103). |
| F10 | RFC-0111 (Draft) would give one place for personal credentials; today the gateway keeps them per person (RFC-0095, procedure U). |
| F11 | PCH 0.8.0 is a store product of its own: projects with an alias, references (another project mounted read-only, rights never widened), sessions, `log.md`, section-wise reading and editing, a guard against shrinking, an expected version on every write, proposals as pull requests. It has an OAAP package (`deploy/oaap/`, MCP under `/mcp`, the person from the gateway's headers). |
| F12 | Foreign content read by a tool is marked as such for the model (RFC-0116 stage 2, mcp-gateway 0.36.0). |

### 1.2 What follows

- The pattern "several systems of one kind, registered by the admin, used as
  the person" exists (F5); stores reuse its shape, not its object — a target
  system is reached through a view, a store through a workspace.
- The wiki contract (F7) is the store contract for one product. Two contracts
  for the same verbs would be two places for one rule (§3.5, D9).
- PCH (F11) already solved the editing rules. They belong **once** above all
  connectors, not in each (§3.4).

### 1.3 Not read, not measured

- **Forgejo:** whether an administrator's token can act as a person (`Sudo`),
  what the contents API returns as a revision, how search answers per person.
  Where the Forgejo package lives was not found in `oaap-apps/apps`.
- **BDT:** its API for projects, folders and files, and how it knows a person.
- **PCH on the platform:** the package was never run against a real node (PCH
  open question 33).
- **How the chat resolves "team"** for assistants today.
- **The light of a system outside the tenant** (GitHub): which colour, set by
  whom.

Stage 0 (§10) answers these before anything is built on them.

## 2. Words

### 2.1 The levels of a store system

| Word (German in the UI) | Forgejo | BookStack | BDT | PCH |
|---|---|---|---|---|
| **store kind** (Ablagetyp) — one connector | `forgejo` | `bookstack` | `bdt` | `pch` |
| **store system** (Ablagesystem) — registered by the admin | a server | an instance | a hub | an instance |
| **area** (Bereich) — optional | account, organisation | shelf | — | — |
| **store** (Ablage) — what a workspace mounts | repository | book | project | project |
| **folder** (Ordner) | directory | chapter | folder | folder |
| **document** (Dokument) | file | page | file | file |
| **section** (Abschnitt) | heading | heading | — | heading |

The contract knows only these levels. A connector tells the names its product
uses ("Regal", "Buch", "Repository"); the chat shows those, so nobody learns
new words for a system they know. A level a product lacks is simply absent (BDT
has no areas; BookStack has one level of folders).

### 2.2 The workspace

| Word | Meaning |
|---|---|
| **workspace** (Arbeitsraum) | a named set of mounts and assistants; a way to start a conversation |
| **mount** | one store, or one folder of it, in a workspace — with alias and role |
| **alias** | the short name of a mount in this workspace: `notizen`, `kunde` (`[a-z0-9-]{2,24}`) |
| **role** | `source` (Quelle: read, search) or `work` (Arbeitsablage: also write) |
| **home** (Heimat) | the one `work` mount that holds state, log and filed conversations |
| **state** (Stand) | one document: where the work stands, what is next |
| **log** (Protokoll) | one document: a short entry per finished conversation, newest first |

### 2.3 Collisions

"Ablage" and "Dokument" already name `oaap.data.files` and
`oaap.data.documents` (RFC-0034): bytes and versions the **platform** keeps for
apps. A store here is a place in **another system** a person works in. The
specifications are named `oaap.work.*` to keep them apart (D8); the German UI
says "Ablage" only for the thing of this RFC — the file store of RFC-0034 has
no page for people. "Kontext" stays RFC-0067's word; this RFC says workspace.

## 3. The store contract: `oaap.work.stores`

### 3.1 Verbs

A connector answers verbs, a row per product saying which it has, which come
later, which never, and through which door — the form of RFC-0110 §2.

| Verb | What it answers |
|---|---|
| `about` | kind, version of the product, the names of its levels, what it can (§3.2) |
| `areas` | the areas the person may see |
| `stores` | the stores the person may see, in an area or in all; paged |
| `list` | the folders and documents of one folder; paged; never recursive without a limit |
| `read` | one document: text, revision, title, last editor, the address a person opens |
| `write` | create or change one document as the person; with the expected revision and an origin (§3.4) |
| `folder` | create a folder |
| `move`, `remove` | move or delete a document — optional, declared in `about` |
| `search` | full text as the person, in a store or a folder of it |
| `history` | the revisions of a document: who, when — optional |
| `may` | what this person may do at this path: `read`, `create`, `update`, `remove` — **answered by the product** |
| `create_store` | a new store in an area, if the person may — optional |
| `entry` | the document a reader should begin with (README, index, the book's first page), if there is one |

`never`: **`decide`**. A connector never returns who may read what for others
to enforce, and nothing above it keeps such a list as the truth (RFC-0110, F7).
Whoever needs the answer asks `may`, as the person.

A path in the contract is `/folder/…/document`, `/` as separator, no `..`, no
hidden names. A connector maps it to its product (a chapter is a folder; a page
is a document; a file's extension stays part of its name).

### 3.2 What a connector declares

`about` carries: `revisions` (yes/no), `history`, `folders` (depth: none, one,
any), `move`, `remove`, `create_store`, `binary` (listed only), `propose` (a
change can become a proposal instead of a write — a pull request), and the
`identity` it uses (§3.3). The chat and the gateway offer only what is
declared; nothing is emulated silently. A product without revisions gets
writes without the lost-update check, and the chat says so on the mount.

### 3.3 As the person

A connector makes every call count as the person. How, is the connector's
business and one of three:

| Identity | When | Example |
|---|---|---|
| `assertion` | the system is in the tenant and can map the platform's assertion to its account | BookStack through its adapter (`act_as`, F7); PCH (headers of the gateway); Forgejo, if stage 0 confirms it |
| `personal` | the system knows nothing of the tenant; the person stores their own credential once | GitHub, a foreign GitLab — procedure U today (F10), a personal slot of RFC-0111 when it exists |
| `none` | never. There is no shared technical user for content | — |

With `assertion` a person enters nothing. With `personal` the page "Meine
Werkzeuge" of the gateway (`/me`) shows the store system as "not set up for
you" until the value is there — the existing road of RFC-0095 stage 3.

### 3.4 The editing layer — once, above all connectors

A model must not rewrite a long document to change one paragraph. The rules
PCH measured (F11) are applied by the **store door** of the MCP gateway (§4.2),
not by each connector:

- **read a part:** by section (heading, `Upper > Lower` if ambiguous) or by
  lines (at most 400), with a marker where to continue; an outline of headings;
- **write a part:** replace a text that occurs exactly once; replace, append
  to, insert after or delete a section. No line numbers for writing;
- **expected revision:** every write names the revision it read; a different
  one refuses with the current revision (where the connector has revisions);
- **shrink guard:** a write by the model that cuts a document of 400 characters
  or more to under half is refused unless it says so explicitly;
- **origin:** every write carries who (the person), through what (the chat,
  the assistant, the model's name) — as far as the product can keep it (a
  commit trailer, a tag, a revision summary).

A connector therefore implements only whole-document `read` and `write` with a
revision. A product that edits sections natively (PCH) may say so in `about`
and take the call through.

### 3.5 Where a connector lives, and the wiki contract

A connector is an **MCP source** behind the tenant's MCP gateway (RFC-0073)
that declares the profile `oaap.work.stores/1` and offers its verbs as tools
with fixed names. Where it runs follows RFC-0110 §3: **in the product's
package** when it needs a door only that instance has (BookStack's database for
`act_as`), otherwise as a small app of its own (Forgejo, GitHub and BDT through
their APIs).

The BookStack adapter of RFC-0110 answers **this** contract. `oaap.data.wiki`
keeps what is the wiki's own — `people`, `act_as`, `changes`, the package, the
AI as author — and takes `spaces/read/search/write/may` from here (D9). RFC-0110
stage 1 was not built, so nothing has to be moved.

## 4. In the MCP gateway

### 4.1 Store systems

A new object next to target systems (F5): **store system** — name, title, kind,
the connector's server record, a light (F4), an active flag, optionally the
groups that may see it. Created by the `tenant_admin` on a page "Ablagen"; a
recipe may create one (RFC-0109). The page shows per system whether the
connector answers `about` and what it declares.

A person sees on `/me`, per store system: reachable or not for them, and — a
click further — the areas and stores they may see. The same read serves the
chat's picker (§5.1). Neither ever shows an address or a credential.

### 4.2 The store door

Inside a workspace the gateway offers one fixed set of tools, the same for
every kind of system:

`store_list`, `store_read`, `store_outline`, `store_search`, `store_write`,
`store_edit`, `store_folder`, `store_move`, `store_remove`, `store_history`,
`workspace_info`.

An address is **`alias:/path`**. The door resolves the alias in the workspace
of the call, checks the role, applies §3.4 and calls the connector as the
person. Consequences:

- a mount with role `source` has no writing tools — refused by the door, not by
  a sentence in a prompt;
- a path outside the mount's folder does not resolve;
- a store that is not mounted in this workspace cannot be addressed at all;
- what `read` and `search` return is foreign content (F12).

The door is added to whatever the assistant's view offers. It is **not** part
of a view and needs no entry there; whether a client may use it is a switch on
its access profile, off by default (D10). Assistants stay without rights (F2).

### 4.3 Workspaces live in the gateway

Like assistants (F2), with revisions, export and import. A workspace holds:

```
id, title, description
scope        private | team | tenant
owner        the person (private), the lead (team), tenant_admin (tenant)
members      team only: persons, each lead or member
assistants   one or more, one of them the default
mounts[]     alias, store system, store, folder (default /), role, home (one true)
home_folder  where state, log and filed conversations lie (default /_arbeitsraum)
```

It holds no address, no credential, no content and no right. A workspace is
**usable** by a person when they can reach its home as `work`; mounts they
cannot reach are shown as "not accessible for you" and are absent from the
door.

## 5. In the chat

### 5.1 Starting

"Neues Gespräch" offers two roads: an assistant, as today, or a **workspace**.
A workspace's card shows its mounts with alias, role and the product's own
words ("Buch *Betriebshandbuch* in *wiki*"), its light (the weakest of its
store systems, F4) and the assistants; the person picks one, or takes the
default. Several conversations in one workspace are normal — one per topic.
The bar groups conversations by workspace next to the existing groups.

A workspace is made in a dialog: title, then stores from a picker (system →
area → store → optionally a folder), per store an alias and a role, one of them
home. With the right in the product, a person can create a new store from the
picker (`create_store`).

### 5.2 What a conversation begins with

The chat gives the model, before the first message:

- the workspace: title, description, each mount with alias, role and title;
- from the home: the **state** document, and the last entries of the **log**;
- per mount: where its `entry` document is — not its content. The model reads
  what it needs through the door.

In the home folder lie, as plain documents a person can read and edit in the
product itself:

| Document | Written by |
|---|---|
| `stand` | the assistant, on the person's word, with consent (F3) |
| `protokoll` | one entry when a conversation is closed: date, person, title, three lines on what changed, links to the documents written |
| `chats/<date>-<title>` | a conversation filed in full (§5.3) |
| `entscheidungen/…` | reserved: finished decisions (the RFC named in "Not part") |

`/stand` asks the assistant to bring the state up to date; `/abschluss` does
that and adds the log entry. Both are proposals the person confirms. Nothing is
written to the home without the person's consent, and nothing silently at a
timeout.

### 5.3 Filing a conversation

The history stays in the chat (F1). On the person's word — the command
`/ablegen alias:/ordner` or the same in a sentence ("schreib unseren Chat
komplett in die Ablage, Ordner …") — the **chat**, not the model, writes the
whole conversation as one Markdown document: messages, tool calls by name,
written documents as links. It is complete, not retold, and costs no model
call. Before writing, the chat names the other stores this conversation read
from: their content may be quoted in it and is about to land in a different
place.

### 5.4 Private conversations

A conversation is readable by its person only (until §9). In a team or tenant
workspace it is additionally **private** if the person says so: no log entry is
proposed at its end and its title appears nowhere for others. What it wrote
into a store is there, with the person's name — a store has no private writes.

## 6. Private, team, tenant

| Scope | Made by | Seen by | Changed by |
|---|---|---|---|
| private | any person | the person | the person |
| team | a person; or a private one, turned | its members | its leads |
| tenant | `tenant_admin` | everyone, or named groups | `tenant_admin` |

- **Membership grants nothing in a store.** A lead who adds a member is shown,
  per mount, what that person may do there (`may`, asked as that person through
  the connector where its identity allows, otherwise "unknown — ask them to
  open it"), with a link to where the product grants rights. The platform does
  not grant them.
- **Turning a private workspace into a team's** keeps id, mounts and home; the
  owner becomes lead. The dialog warns if the home lies in a store only the
  owner reaches. Conversations stay with their persons.
- **A tenant workspace** is a template that is also usable: people work in it
  directly, or copy it into a private one (RFC-0117's pattern: an export names
  what it came from).
- A store with rights per sub-folder (PCH references, BookStack chapters) is
  mounted folder by folder; the workspace adds no rights model of its own.

## 7. A guest in one folder (stage 4)

A lead may bring in a person who can use the chat but has no right in a store.

- The lead names **one folder below the root of one `work` mount**, a person
  and an end (at most 30 days). The root of a mount, and with it the whole
  store, cannot be handed on (decided, D5).
- In that folder the guest's calls run **with the lead's rights**, confined by
  the door to the folder: list, read, write, search inside it; nothing outside
  resolves. A connector that cannot confine a search to a folder offers the
  guest none.
- Every write carries both names: the guest as author, the lead as the one
  whose right it was. Every call is logged. The guest sees whose right they use
  and until when.
- A guest cannot hand on. The lead and the `tenant_admin` can end it at once.
  It ends by itself when the lead loses the right, leaves the workspace or the
  date passes.
- First only for store systems with identity `assertion` (§3.3): there the
  platform can act as the lead without holding a secret of theirs. Using a
  lead's **personal** credential for another person is a separate decision
  (D14).

The grant is an assignment of RFC-0067 (F8) if its collections can carry "this
folder of this mount" — to be read before stage 4; otherwise an object of the
gateway with the same log actions.

## 8. Security requirements (proposed)

1. The product decides. No list of rights is kept above a connector; a
   workspace never widens what a person may do, except §7, which is explicit,
   narrow, timed and logged.
2. No call without a person. A connector refuses a call without the platform's
   assertion (or the person's own credential); there is no technical user for
   content.
3. The role is enforced by the door. A `source` mount cannot be written,
   whatever a document or a prompt says.
4. Content from a store is foreign content. Instructions in it are data; a
   write still needs the person's consent (F3, F12).
5. An alias resolves only inside the workspace of the call, a path only inside
   the mount. Paths are normalised before any check.
6. A workspace's definition, its export, the state and the log contain no
   address of a system and no credential.
7. The light holds: a conversation uses only store systems up to its colour; a
   workspace shows the weakest colour of its mounts.
8. Filing a conversation (§5.3) names the stores it read from before it writes.
9. A person removed from a team loses the workspace at once; what they may do
   in the stores is the product's business and is said so in the dialog.

## 9. The group chat (later, an option)

Several members in one conversation would need answers this RFC does not give:
whose rights a tool call uses (proposal: always the person who wrote the
message), who sees what a tool returned for another member (everyone in the
conversation — joining means seeing it), whose volume is counted, and where the
history lies. The core of this RFC — own conversations in a shared workspace,
a shared state and log — does not depend on it.

## 10. Stages

| Stage | Content |
|---|---|
| **0 — measure** | Forgejo: acting as a person, revision of a file, search per person, creating a repository. PCH: the package on `oaap-test` behind the gateway. BDT: read its API with the BDT side. The light of an outside system. How the chat resolves "team". |
| **1 — one person** | `oaap.work.stores` 0.1, the store door with the editing layer, store systems in the gateway, connectors **Forgejo** and **PCH**; private workspaces in the chat: picker, alias, role, home, state and log, `/stand`, `/abschluss`, `/ablegen`. |
| **2 — more kinds** | **BookStack** (with RFC-0110 stage 1: package and adapter answer this contract), **BDT**; a system outside the tenant with a personal credential (GitHub). |
| **3 — teams** | team and tenant workspaces, turning a private one, the lead's view of members' rights, export/import and templates. |
| **4 — guests** | delegation into one folder (§7). |
| **5 — later** | group chat (§9), `changes` as events, the index service (I-65), a connector for SAP (the AIPC file store). |

## 11. Conformance (described; every line gets a bait)

1. A call to a connector without an assertion is refused.
2. Two persons with different rights in one store get different `stores`,
   `list` and `search` answers through the same workspace.
3. `store_write` to a `source` mount is refused by the door; the connector is
   never called.
4. `alias:/../x` and an alias of another workspace do not resolve.
5. A write with an old revision is refused and names the current one.
6. A model's write that halves a document is refused without the explicit flag.
7. A workspace with two homes, or a home with role `source`, cannot be saved.
8. A filed conversation equals the history message by message.
9. A private conversation leaves no log entry and no title for others.
10. A guest reads `/folder/a`, is refused `/other` and the root, and is refused
    everything one second after the end.
11. A guest's write carries both names in the product's history.
12. A workspace's export contains no address and no credential.
13. A green conversation cannot be started in a workspace with a yellow mount.

## 12. Decisions

### 12.1 Decided 2026-11-23 (Jörg, in conversation)

- **D1 — Connectors work on the system itself, as the person; PCH is one
  connector among others.** Yes. PCH is meant to be used outside OAAP too and
  is treated as a source like any other; it may run in the same tenant.
- **D2 — State and log in the home; the history stays in the chat.** Yes. A
  conversation can be private. Filing a whole conversation on command is
  enough.
- **D3 — Exactly one home per workspace.** Yes.
- **D4 — Own conversations in a shared workspace are the core; the group chat
  is an option and a later extension.** Yes.
- **D5 — The platform may act with the lead's rights for a guest — only inside
  an assigned folder, never the root and with it the whole store.** Yes.
- **D6 — Decision tasks extend the app `vorgaenge`.** Yes (own RFC).
- **D7 — Private workspaces for everyone; tenant-wide ones kept by the admin;
  a private one can become a team's.** Yes.

### 12.2 Decided 2026-11-23: D8–D17 as recommended

- **D8 — Names `oaap.work.stores` and `oaap.work.workspaces`?**
  *Recommendation: yes.* `oaap.data.store` and `oaap.data.files` exist and mean
  something else; a new prefix avoids the next misunderstanding.
- **D9 — The wiki contract takes its content verbs from this contract?**
  *Recommendation: yes*, as in §3.5. Otherwise BookStack gets two adapters or
  one adapter two contracts for the same calls.
- **D10 — The store door outside views, switched per access profile, off by
  default?** *Recommendation: yes.* Putting eleven tools into every view of
  every assistant is work nobody will do right; default deny holds through the
  switch.
- **D11 — Workspaces live in the MCP gateway, like assistants?**
  *Recommendation: yes.* The door needs the workspace to resolve an alias; a
  second place would have to be asked on every call.
- **D12 — One assistant per conversation, chosen at the start; switching inside
  a conversation later?** *Recommendation: yes, later.* A switch changes
  prompt, model and view in the middle of a history; several conversations in
  one workspace give the same result today.
- **D13 — The home folder is `/_arbeitsraum`, with German document names
  (`stand`, `protokoll`, `chats/`)?** *Recommendation: yes*, changeable per
  workspace. People will open these documents in the product.
- **D14 — Guests only on systems with identity `assertion` at first?**
  *Recommendation: yes.* Using a lead's stored personal credential for someone
  else is a different promise than the one they gave when they stored it.
- **D15 — Forgejo and PCH first, then BookStack and BDT?** *Recommendation:
  yes.* Forgejo has the richest structure and a clean API; PCH exists with an
  OAAP package; BookStack waits for its package (RFC-0110 stage 1) anyway.
- **D16 — Nothing is written to the home without the person's consent — also
  no automatic log entry at a timeout?** *Recommendation: yes.* A log that
  writes itself is a log nobody trusts; `/abschluss` is one word.
- **D17 — Stage 1 writes text only?** *Recommendation: yes.* Attachments of the
  chat (RFC-0102) into a store come when a second product shows what "binary"
  means there.

## Deutsche Zusammenfassung

**Worum es geht.** Ein Gespräch im Chat beginnt heute mit einem Assistenten und
weiß nichts von deiner Arbeit. Dieser RFC bringt zwei Dinge: einen
**Ablagen-Vertrag** mit Konnektoren (Forgejo, BookStack, BDT, PCH, später
weitere) und den **Arbeitsraum**, in dem du Ablagen und Assistenten bündelst und
ein Gespräch mit dem Stand des letzten beginnst.

**Begriffe (§2).** Ablagetyp (ein Konnektor) → Ablagesystem (legt der
Mandanten-Admin an, mehrere je Typ) → Bereich (Org, Regal; optional) → Ablage
(Repository, Buch, Projekt) → Ordner → Dokument → Abschnitt. Der Konnektor
liefert die Namen, die sein Produkt benutzt; im Chat steht also weiter „Regal“
und „Buch“. Im Arbeitsraum hat jede eingehängte Ablage einen **Alias** und eine
**Rolle**: *Quelle* (nur lesen) oder *Arbeitsablage* (auch schreiben). Genau
eine ist die **Heimat**.

**Der Vertrag (§3).** Wenige Verben: was gibt es, lesen, schreiben, suchen,
Verlauf, „was darf diese Person hier“. Jeder Aufruf läuft **als die Person**
direkt am System; das System allein entscheidet über Rechte, nirgends wird eine
Rechteliste gespiegelt. Systeme im Mandanten brauchen keine Eingabe von
Zugangsdaten (die Plattform weist die Person aus), fremde Systeme wie GitHub
einen persönlichen Zugang, einmal hinterlegt. Abschnittsweises Bearbeiten,
Kürzungsschutz und „erwartete Version“ – die Regeln aus PCH – sitzen **einmal**
im MCP-Gateway über allen Konnektoren. Der Wiki-Vertrag aus RFC-0110 übernimmt
seine Inhaltsverben von hier, damit BookStack nicht zwei Verträge bedient.

**Im Gateway (§4).** Neue Objekte *Ablagesystem* und *Arbeitsraum*. Im
Arbeitsraum bekommt die KI einen festen Satz Werkzeuge (`store_read`,
`store_edit`, …), bei jedem Ablagetyp gleich; die Adresse ist `alias:/pfad`.
Eine Quelle lässt sich technisch nicht beschreiben, eine nicht eingehängte
Ablage nicht ansprechen.

**Im Chat (§5).** „Neues Gespräch“ bietet Assistent **oder** Arbeitsraum.
In der Heimat liegen als normale Dokumente: `stand`, `protokoll`, abgelegte
Chats, später Entscheidungen. `/stand` und `/abschluss` lassen den Assistenten
Stand und Protokoll vorschlagen, du bestätigst. `/ablegen alias:/ordner` (oder
derselbe Wunsch als Satz) schreibt das ganze Gespräch wörtlich in die Ablage –
das macht der Chat selbst, nicht das Modell. Gespräche gehören der Person; im
Teamraum kann eines zusätzlich privat sein und hinterlässt dann keinen
Protokolleintrag.

**Privat, Team, Mandant (§6).** Jeder legt private Arbeitsräume an; aus einem
privaten kann ein Team-Arbeitsraum werden; mandantenweite pflegt der Admin.
Mitglied sein gibt **kein** Recht in einer Ablage – jeder arbeitet mit seinen
eigenen Rechten, der Führende sieht, was ein Mitglied dort darf, und vergibt
Rechte im Produkt selbst.

**Gäste (§7, Stufe 4).** Der Führende kann einer Person befristet (höchstens 30
Tage) das Arbeiten in **einem Ordner** einer Arbeitsablage übertragen, nie im
Hauptordner. Der Gast arbeitet dort mit den Rechten des Führenden, eingesperrt
auf den Ordner; jede Änderung trägt beide Namen. Zuerst nur bei Systemen im
Mandanten.

**Nicht in diesem RFC.** Aufgaben und Entscheidungen im Chat (eigener RFC, als
Erweiterung der Vorgänge), die BPMN-Engine, der Gruppenchat (spätere Option),
Binär- und Office-Dateien, ein Suchindex über alle Ablagen.

**Stufen (§10).** 0 Messen (Forgejo als Person, PCH-Paket auf oaap-test,
BDT-API) · 1 Vertrag, Gateway, Forgejo und PCH, privater Arbeitsraum · 2
BookStack, BDT, GitHub · 3 Team- und Mandanten-Arbeitsräume, Vorlagen · 4 Gäste
· 5 Gruppenchat, Ereignisse, Index, SAP.

**Entschieden (23.11.):** D1–D7, deine sieben Antworten, und D8–D17 wie
empfohlen („Wie empfohlen“):
D8 Namen `oaap.work.*` · D9 Wiki-Vertrag übernimmt die Inhaltsverben · D10
Ablage-Werkzeuge außerhalb der Sichten, je Zugangsprofil schaltbar · D11
Arbeitsräume liegen im MCP-Gateway · D12 ein Assistent je Gespräch, Wechsel
später · D13 Heimatordner `/_arbeitsraum` mit deutschen Namen · D14 Gäste
zuerst nur bei Systemen im Mandanten · D15 Forgejo und PCH zuerst · D16 kein
automatischer Protokolleintrag ohne dein Wort · D17 Stufe 1 nur Text.

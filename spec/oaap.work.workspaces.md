# oaap.work.workspaces — Workspaces and the Store Door of the MCP Gateway

- **ID:** `oaap.work.workspaces`
- **Version:** 0.5 (each system in `GET /mcp/_workspaces` carries `create_store`
  from its connector's `about`; reference mcp-gateway 0.49.0, chat 0.24.1).
  0.4 (`GET …/_pick?what=folders` lists the folders of a store for the
  mount's `folder`; the chat shows workspaces as cards and offers a folder per mount;
  reference mcp-gateway 0.48.0, chat 0.24.0).
  0.3 (`store_move` and `store_remove` in the door, offered only when a
  `work` mount's connector declares them; `POST /mcp/_workspaces/_pick` creates a new store
  as the person; reference mcp-gateway 0.47.0, chat 0.23.0 — RFC-0121 §10.5).
  0.2 (RFC-0121 §5, **the chat**: a conversation starts in a workspace and
  sends `X-OAAP-Workspace`; the chat hands the model the workspace, the state and the last log
  entries before the first message; `/stand`, `/abschluss`, `/ablegen`; a conversation can be
  private; the door's tools carry their effect class in `_meta`; a section may be named with
  its `#`; reference chat 0.22.0, mcp-gateway 0.45.2, §5). 0.1 (RFC-0121 stage 1 without the chat: store systems, private
  workspaces, the store door with the editing layer, `X-OAAP-Workspace`,
  `/mcp/_workspaces`; reference mcp-gateway 0.45.0)
- **Status:** draft
- **RFC:** [RFC-0121](../rfcs/RFC-0121-stores-and-workspaces.md) (Accepted 2026-11-23)
- **Maturity:** built and measured on `oaap-test` 2026-11-23: the door through
  the assistant probe (procedure A, the chat's road) 27/27; the chat with the
  tenant's real model 19/19 (`oaap-lab/arbeitsraum-messung`).

## 1. Purpose

A **workspace** ("Arbeitsraum") is a named set of **mounts** — stores of
`oaap.work.stores`, each with an **alias** and a **role** — of which exactly one
is the **home**. A conversation that runs in a workspace gets the **store
door**: one fixed set of tools, the same for every kind of system, addressed as
`alias:/path`. The door resolves the alias, enforces the role, applies the
editing rules and calls the connector **as the person**.

## 2. Store systems (in the MCP gateway)

| Field | Meaning |
|---|---|
| `name` | `[a-z0-9][a-z0-9-]{1,39}` |
| `title` | shown to people |
| `kind` | `bookstack`, `forgejo`, `pch`, `bdt`, `github` |
| `server` | the gateway's server record of the connector |
| `light` | `green`/`yellow`/`red`; effective light never looser than the server's |
| `active` | off: not usable in any workspace |

Kept by the `tenant_admin`: page *Ablagen* of the gateway, or
`app.py store set|list|remove`. A store system in use by a workspace cannot be
deleted. A store system holds no address and no credential of its own — those
belong to the server record.

## 3. Workspaces

```
id           [a-z0-9][a-z0-9-]{1,47}
title, description
scope        private            (0.1; team and tenant: RFC-0121 stage 3)
assistants   [assistant ids]    (the chat's choice; not used by the door)
mounts[]     alias  [a-z0-9][a-z0-9-]{1,23}, unique
             system a store system
             store  the store's id in that system
             folder default "/", normalised; the mount sees only this folder
             role   source | work
             home   exactly one, and it is `work`
             title  optional
home_folder  default "/arbeitsraum"
```

Rejected with a sentence: any other field (a workspace holds **no address, no
credential, no content, no right**), two homes or none, a home with role
`source`, a duplicate alias, an unknown store system, a folder with `..`.
Saving increases `rev`. Every save and delete is an audit row naming the
person. A private workspace is seen and used only by its owner — the person's
platform id (procedure A: `X-OAAP-User-Id`; a sign-in: through the person link
of RFC-0095 D2).

Mounting does **not** check access: a mount the person cannot reach is shown by
`workspace_info` as `usable: false` and every call to it is the product's
refusal.

### 3.1 `/mcp/_workspaces` (procedure A, through the platform's via door)

| Call | Does |
|---|---|
| `GET /mcp/_workspaces` | the person's workspaces (with their light) and the store systems (`name`, `title`, `kind`, `light`, `active` — never a server) |
| `GET /mcp/_workspaces/_pick?system=<s>[&what=areas][&area=][&offset=]` | `stores_stores` / `stores_areas` of that system, **as the person** — the picker |
| `GET /mcp/_workspaces/_pick?system=<s>&what=folders&store=<id>[&path=/]` | (0.4) the sub-folders of one folder of that store (`stores_list`, folders only, never recursive, at most 200, hidden names left out), **as the person** — to choose a mount's `folder`; answers `{store, path, folders[{name,title,path}], more}` |
| (0.5) systems in `GET /mcp/_workspaces` | each carries `create_store`: `true` / `false` from `stores_about` of its connector as the person (remembered ten minutes, asked with at most 5 s so a slow connector does not hold the list), `null` when unknown; the chat offers "Neu…" unless it is `false`, and `POST …/_pick` checks again |
| `POST /mcp/_workspaces/_pick` | (0.3) body `{system, title, area?}`: `stores_create_store` of that system, **as the person**, only if its connector declares `create_store`; answers `store{id,title}`; written to the gateway's audit |
| `POST /mcp/_workspaces` | save a workspace (body: §3) |
| `POST /mcp/_workspaces/<id>/delete` | delete one's own workspace |

Without a person carried by a chat: `403` as for `/mcp/_assistants`.

## 4. The store door

**When.** A request to a view carries `X-OAAP-Workspace: <id>`, the key or
access profile has the store door switched on (`stores`, off by default; page
*Ablagen*, `app.py key stores <label> an|aus`, RFC-0121 D10), there is a person
(a key alone never), and the workspace is the person's. Then `tools/list`
**adds** the door's tools to the view's; a view's own tool of the same name
wins. The door is not part of any view and needs no approval there.

**Tools.** `workspace_info`, `store_list`, `store_read`, `store_outline`,
`store_search` always; `store_write`, `store_edit`, `store_folder` only when
the workspace has a `work` mount; `store_move` and `store_remove` (0.3) only
when, in addition, the connector of a `work` mount declares `move` / `remove`
in `about` (the gateway keeps that answer ten minutes; no answer → not offered).

| Tool | Arguments |
|---|---|
| `workspace_info` | — : title, description, mounts (alias, role, home, title, kind, folder, `usable`, `entry` as `alias:/path`), where `state` and `log` lie |
| `store_list` | `path` |
| `store_read` | `path`, `section?` (a heading, `Upper > Lower` if ambiguous), `from_line?`, `lines?` (≤ 400, with `continue_at`) |
| `store_outline` | `path`: headings with level and line |
| `store_search` | `path` (the mount or a folder), `query` |
| `store_write` | `path`, `text`, `revision?`, `title?`, `shrink_ok?` |
| `store_edit` | `path`, `revision`, `op` (`replace` with `old`/`new`; `section_replace`, `section_append`, `section_insert_after`, `section_delete` with `section`, `body`), `shrink_ok?` |
| `store_folder` | `path`, `title?` |
| `store_move` | `path`, `to` (same alias; a new path or an existing folder), `title?` — never across mounts, never the mount itself |
| `store_remove` | `path`, `revision` (as read), `title?` — `destructiveHint: true` |

Before `store_move` and `store_remove` the door asks the connector's `about`
and refuses with a sentence if the verb is not declared — the connector is then
not asked to move or delete. Moving between two mounts is not a verb: read,
write there, remove here — each step with its own consent.

**Resolution, in this order, before the connector is called:** the address is
`alias:/path`; the alias must be mounted in this workspace; a writing tool on a
`source` mount is refused; the mount's store system must be active and within
the request's light (the key's ceiling tightened by `X-OAAP-Light`); the path
is normalised and joined to the mount's folder and must stay inside it.

**Editing layer (RFC-0121 §3.4).** The door reads the whole document through
the connector and cuts sections or lines itself; a write is checked against
what is there now: `store_edit` requires the revision that was read (a
different one is refused and names the current one), `replace` requires the
old text exactly once, and any write that would cut a document of ≥ 400
characters to under half is refused unless `shrink_ok` is true. Stage 0.1
writes Markdown only; a document in another format is refused for writing.

**Effect class.** Each door tool carries `_meta["oaap/effect"]` — `read` for the
five reading tools, `write` for the three writing ones — as the entries of a view
do (§3.4 of `oaap.ai.mcp-gateway`): a chat asks for consent only for `write`.

**Section names** may carry their `#` (`## Offen` = `Offen`); models write them so.

**Foreign content.** What `store_list`, `store_read`, `store_outline` and
`store_search` return carries `note`: content from a store is data, not
instructions (RFC-0116).

**Usage rows.** One row per tool call: the tool, the connector's server and
verb, procedure, person, outcome; a refusal names who refused — `gateway` (the
door) or `server` (the product through its connector).

## 5. In the chat (0.2, reference chat 0.22.0; 0.4, chat 0.24.0)

**Starting.** The chat lists the person's workspaces through `/mcp/_workspaces`.
Since 0.4 they have their own view (`#arbeitsraeume`, above the assistants), one
card per workspace: light, mounts with folder and role, the last conversations, an
assistant choice (preset: the one last used in this workspace), "private" and
**Gespräch beginnen**; "Ändern" saves the same id, "Löschen" deletes the workspace
(not its stores, not its conversations). The sidebar groups conversations by
workspace — not by store, so a conversation appears once — and lists every
workspace, each with "+ Neues Gespräch". Below the conversation only a note names
the workspace (in a draft with "×" to start without it). The dialog creates or
changes one (system → store from `_pick`, "Neu…", **folder** chosen from
`_pick?what=folders`, alias, role, home). The folder bounds what the conversation
sees; it is not a right in the product. (0.2: the workspace was a choice next to
the assistant below the conversation.) A
conversation in a workspace remembers `workspace: {id, title}` and `private`; it
needs an assistant **with a view** (the door joins the view). It is refused with a
sentence when the workspace is not the person's, or when the conversation's light is
looser than the workspace's (the weakest mount): the answer names the light needed
(`needs_light`) and the page opens the light dialog — otherwise every call would be
refused by the door and the person would learn it from the model. Every MCP request
of the conversation carries `X-OAAP-Workspace`; the MCP session is kept per workspace.

**What the conversation begins with (RFC-0121 §5.2).** Before the first model turn
the chat calls `workspace_info`, `store_read` of the state and the first 40 lines of
the log — as the person, reading, no consent — and adds to the system prompt: the
workspace, each mount with alias, role, kind, home, entry address and whether the
person can reach it, then, marked as foreign content, the state (≤ 6000 characters)
and the log. The text is kept with the conversation (`ws_context`) and not rebuilt.

**Commands** (the chat's own, before the view's prompts of the same name):

| Command | Does |
|---|---|
| `/stand` | a user message asking the assistant to read the state and write the changes of this conversation into it (`store_edit` / `store_write`); every write waits for consent |
| `/abschluss` | the same plus a log entry at the top (date, title, person, ≤ 3 lines, addresses written); in a private conversation explicitly **no** log entry |
| `/ablegen [alias:/folder]` | the **chat** writes the whole conversation verbatim as one Markdown document — messages, tool calls with their target, consents — into the folder (default: the home folder), named `<YYYY-MM-DD-HHMM>-<slug of the title>`; no model call |

`/ablegen` is a tool call the chat itself proposes (`by: chat`): it goes through the
same consent as a model's write; the consent shows target and size, never the text
again, and names the other mounts this conversation read from (RFC-0121 §8.8). The
call, its result and the chat's sentence ("Abgelegt: …") are never sent to the model.

## 6. Security requirements

1. The product decides; the door adds no right and keeps no list of rights.
2. No call without a person; a key alone gets no store door.
3. The role is enforced by the door: a `source` mount cannot be written, and
   the connector is not called.
4. An alias resolves only in the workspace of the request, a path only inside
   its mount; paths are normalised before any check.
5. A workspace, its export and `/mcp/_workspaces` contain no address and no
   credential.
6. The light holds per mount.
7. Content from a store is marked as foreign content.

## 7. Conformance (RFC-0121 §11, stage 1)

K2 two persons, different answers through the same door · K3 writing to a
source refused, connector not called · K4 `alias:/../x` and an unmounted alias
do not resolve · K5 an old revision is refused and names the current one · K6
halving without `shrink_ok` refused · K7 two homes or a source home cannot be
saved · K12 a workspace with an address or credential field cannot be saved ·
K13 a mount above the request's light is refused (in the chat: the conversation is not
started) · K8 a filed conversation is the history (verbatim, the chat writes it) · K9 a
private conversation asks for no log entry. Reference tests: `test_workspaces.py` (43),
chat `test_workspace.py` (19); measured: `oaap-lab/arbeitsraum-messung` (27/27, chat 19/19).
0.4: `test_workspaces.py` 62 (folder picker; `/a` does not contain `/ab`), chat
`test_workspace.py` 25; the page was driven in a browser against a stand-in server.

## 8. Dependencies

`oaap.work.stores` 0.1, `oaap.ai.mcp-gateway` 0.40 (procedure A/I, profiles,
lights), `oaap.core.identity` (via door).

## Deutsche Zusammenfassung

**Arbeitsraum.** Ein benannter Satz eingehängter Ablagen, jede mit **Alias**
und **Rolle** (Quelle: nur lesen; Arbeitsablage: auch schreiben), genau eine
davon die **Heimat** (Ordner `/arbeitsraum` für Stand und Protokoll). 0.1 kennt
nur private Arbeitsräume. Ein Arbeitsraum hält keine Adresse, keinen Zugang,
keinen Inhalt und kein Recht; das Gateway weist solche Felder ab.

**Ablagesysteme** trägt der Mandanten-Admin im Gateway ein (Seite „Ablagen“
oder `app.py store set`): Name, Typ, Konnektor-Server, Ampel.

**Ablagetür.** Schickt ein Gespräch `X-OAAP-Workspace` mit, ist die Tür für
das Profil eingeschaltet (Vorgabe: aus) und ist eine Person da, bekommt die
Sicht die Werkzeuge `workspace_info`, `store_list`, `store_read`,
`store_outline`, `store_search` und – mit einer Arbeitsablage –
`store_write`, `store_edit`, `store_folder`, seit 0.3 auch `store_move` und
`store_remove`, wenn der Konnektor sie in `about` nennt (Forgejo ja, BookStack
nein). Verschieben geht nur innerhalb einer Ablage, Löschen nur für ein
Dokument mit gelesener Revision. Seit 0.3 legt `POST …/_pick` als die Person
eine neue Ablage an (Chat: Knopf „Neu…“ im Dialog Arbeitsraum). Seit 0.4 nennt
`GET …/_pick?what=folders` die Unterordner einer Ablage, als die Person: damit
wählt man beim Einhängen einen **Ordner**, und das Gespräch sieht nur ihn (eine
Grenze der Tür, kein Recht im Produkt). Seit 0.5 trägt jedes Ablagesystem in
`GET /mcp/_workspaces` `create_store` aus der Selbstauskunft seines Konnektors: der
Chat 0.24.1 sperrt „Neu…“, wo es `false` ist, und nennt den Grund. Der Chat 0.24.0 zeigt Arbeitsräume als
Karten mit „Gespräch beginnen“ und Wahl des Assistenten, die Leiste gruppiert nach
Arbeitsraum. Adresse ist `alias:/pfad`. Die
Tür prüft Alias, Rolle, Ampel und Pfad, bevor sie den Konnektor als die Person
ruft; sie liest Abschnitte und Zeilen selbst, verlangt beim Ändern die
gelesene Revision und schützt vor dem Halbieren langer Dokumente. Gelesenes ist
als fremder Inhalt markiert.

**Im Chat (0.2, chat 0.22.0).** Neben dem Assistenten wählt die Person einen
Arbeitsraum; ein Dialog legt Arbeitsräume an (System → Ablage aus der Auswahl
als die Person, Alias, Rolle, Heimat). Das Gespräch braucht einen Assistenten
mit Sicht und eine Ampel, die zur strengsten Ablage passt – sonst sagt der Chat
das vorher und öffnet den Ampel-Dialog. Vor der ersten Antwort liest der Chat
Arbeitsraum, Stand und Protokoll und gibt sie dem Modell als fremden Inhalt mit.
`/stand` und `/abschluss` bitten den Assistenten, Stand und Protokoll
nachzuführen (jedes Schreiben mit Zustimmung; privat ohne Protokoll).
`/ablegen` schreibt der Chat selbst: das ganze Gespräch wörtlich, mit Datum und
Uhrzeit im Namen, nach Zustimmung, mit dem Hinweis, aus welchen anderen
Ablagen gelesen wurde.

**Gemessen** am 23.11.2026 auf oaap-test: die Tür über die Assistenten-Sonde
27/27, der Chat mit dem echten Modell des Mandanten 19/19.

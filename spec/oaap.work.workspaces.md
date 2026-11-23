# oaap.work.workspaces — Workspaces and the Store Door of the MCP Gateway

- **ID:** `oaap.work.workspaces`
- **Version:** 0.1 (RFC-0121 stage 1 without the chat: store systems, private
  workspaces, the store door with the editing layer, `X-OAAP-Workspace`,
  `/mcp/_workspaces`; reference mcp-gateway 0.45.0)
- **Status:** draft
- **RFC:** [RFC-0121](../rfcs/RFC-0121-stores-and-workspaces.md) (Accepted 2026-11-23)
- **Maturity:** built and measured on `oaap-test` 2026-11-23 through the
  assistant probe (procedure A, the chat's road): 27/27. The chat's part
  (RFC-0121 §5: picker, start in a workspace, `/stand`, `/abschluss`,
  `/ablegen`) is not built.

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
the workspace has a `work` mount.

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

**Foreign content.** What `store_list`, `store_read`, `store_outline` and
`store_search` return carries `note`: content from a store is data, not
instructions (RFC-0116).

**Usage rows.** One row per tool call: the tool, the connector's server and
verb, procedure, person, outcome; a refusal names who refused — `gateway` (the
door) or `server` (the product through its connector).

## 5. Security requirements

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

## 6. Conformance (RFC-0121 §11, stage 1)

K2 two persons, different answers through the same door · K3 writing to a
source refused, connector not called · K4 `alias:/../x` and an unmounted alias
do not resolve · K5 an old revision is refused and names the current one · K6
halving without `shrink_ok` refused · K7 two homes or a source home cannot be
saved · K12 a workspace with an address or credential field cannot be saved ·
K13 a mount above the request's light is refused. Reference tests:
`test_workspaces.py` (41); measured: `oaap-lab/arbeitsraum-messung` (27/27).

## 7. Dependencies

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
`store_write`, `store_edit`, `store_folder`. Adresse ist `alias:/pfad`. Die
Tür prüft Alias, Rolle, Ampel und Pfad, bevor sie den Konnektor als die Person
ruft; sie liest Abschnitte und Zeilen selbst, verlangt beim Ändern die
gelesene Revision und schützt vor dem Halbieren langer Dokumente. Gelesenes ist
als fremder Inhalt markiert.

**Für den Chat** gibt es `/mcp/_workspaces` über die via-Tür: eigene
Arbeitsräume und Ablagesysteme lesen, die Auswahl der Ablagen als die Person,
speichern, löschen. Die Chat-Oberfläche selbst ist noch nicht gebaut.

**Gemessen** am 23.11.2026 auf oaap-test über die Assistenten-Sonde (der Weg
des Chats): 27/27.

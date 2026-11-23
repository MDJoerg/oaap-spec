# oaap.work.stores — The Store Contract: a Few Verbs, Answered as the Person

- **ID:** `oaap.work.stores`
- **Version:** 0.1 (RFC-0121 stage 1: the verbs, the levels, what a connector
  declares, identity `assertion`, the profile `oaap.work.stores/1` as fixed MCP
  tool names; first connector BookStack, reference `bookstack` 0.2.0)
- **Status:** draft
- **RFC:** [RFC-0121](../rfcs/RFC-0121-stores-and-workspaces.md) (Accepted 2026-11-23)
- **Maturity:** one connector (BookStack) built and measured on `oaap-test`
  2026-11-23 through the MCP gateway's store door (27/27, `oaap-lab/arbeitsraum-messung`)

## 1. Purpose

People keep their work in other systems: a wiki book, a Git repository, a
project folder. A **connector** makes one kind of such system answer the same
few verbs, so that the MCP gateway's store door (`oaap.work.workspaces`) and,
through it, a chat can read and write there **as the person** — on the system
itself, with the person's rights there. Nothing is copied or synchronised, and
no list of rights is kept above the system.

## 2. Words and levels

| Level | Meaning | BookStack |
|---|---|---|
| store kind | one connector | `bookstack` |
| store system | one installation, registered in the gateway | an instance |
| area (optional) | a grouping of stores | shelf |
| store | what a workspace mounts | book |
| folder | a container in a store | chapter (one level) |
| document | text with a revision | page |

A connector names its product's own words for the levels in `about`. A level
the product lacks is absent.

**Paths.** `/folder/…/document`, `/` as separator; no `..`, no `.`, no hidden
names. The connector maps a path to its product (BookStack: the slugs its
addresses show, at most `/chapter/page`).

## 3. Interface

A connector is an MCP server — normally an MCP source of the platform
(`oaap.apps.runtime` 2.32, procedure I/A) — that offers the verbs as tools with
these **fixed names** (profile `oaap.work.stores/1`):

| Tool | Arguments | Answers |
|---|---|---|
| `stores_about` | — | `kind`, `profile`, `product`, `version`, `levels{area,store,folder,document}`, capabilities (§3.1), `identity` |
| `stores_areas` | — | `areas[{id,title}]` the person may see |
| `stores_stores` | `area?`, `offset?` | `stores[{id,title,description}]`, `total`, `next` — paged, as the person |
| `stores_list` | `store`, `path` | `items[{name,kind: folder|document,title}]` of one folder; never recursive |
| `stores_read` | `store`, `path` | `text`, `format` (`markdown`|`html`), `revision`, `title`, `updated_by`, `updated_at`, `url` |
| `stores_write` | `store`, `path`, `text`, `revision?`, `title?` | `path`, `revision`, `created` — an existing document only with the revision it was read at |
| `stores_folder` | `store`, `path`, `title?` | `path`, `title` |
| `stores_search` | `store`, `query`, `path?` | `hits[{path,title,snippet}]` inside the store or folder, as the person |
| `stores_may` | `store`, `path?` | `read`, `create`, `update`, `remove`: `true`, `false` or `null` (unknown) — answered by the product |
| `stores_entry` | `store` | `path` of the document a reader begins with, or `null` |
| `stores_create_store` | `title`, `area?` | `id`, `title` — only if declared |

`move`, `remove` and `history` are reserved names for 0.2; a connector of 0.1
offers none of them.

A refusal is a tool result with `isError: true` and one sentence in German for
the person — never a stack trace, never an address or credential.

**`never: decide`.** A connector never returns who may read what for someone
else to enforce. Whoever needs that answer asks `stores_may`, as the person.

### 3.1 What a connector declares in `about`

`revisions` (bool), `history` (bool), `folders` (`none`|`one`|`any`), `move`,
`remove`, `create_store`, `propose` (bools), `binary` (`none`|`listed`),
`sections` (bool: the product edits sections itself), `may` (`full`|`read`:
how much of `stores_may` the product can answer before a write), `origin`
(`author`|`trailer`|`summary`: what the product keeps of a write's origin),
`identity` (§3.2). The store door offers only what is declared; nothing is
emulated silently.

### 3.2 As the person

| Identity | Meaning | 0.1 |
|---|---|---|
| `assertion` | the platform names the person (`X-OAAP-User`, `X-OAAP-User-Idp` = `<issuer> <sub>`); the connector maps it to the product's account | yes |
| `personal` | the person stored a credential once (procedure U) | reserved |

There is **no** shared technical user for content. A call without a person is
refused. BookStack: the account whose `external_auth_id` equals `sub`, created
by BookStack at the person's first sign-in through the realm; the issuer must
be the wiki's; the connector mints a short-lived token for that account
(RFC-0110 §3.1 `act_as`) and calls BookStack's API with it.

## 4. Configuration

None of its own. The connector learns the issuer it accepts from the instance
(`OAAP_OIDC_ISSUER`, RFC-0091). The tenant admin registers the store system in
the MCP gateway (`oaap.work.workspaces` §2).

## 5. Security requirements

1. **The product decides.** Every answer and every write is the product's,
   made with the person's own account.
2. **No call without a person** (§3.2); no technical user for content.
3. A connector keeps any credential it uses for the person in memory only and
   removes what it created at start.
4. Paths are checked before they reach the product (§2).
5. A refusal never names an address, a credential or another person's data.

## 6. Conformance

1. Without `X-OAAP-User-Idp` (or with another issuer) every verb is refused and
   the product is not called.
2. Two persons with different rights get different `stores`, `list`, `read`
   and `search` answers.
3. `stores_write` on an existing document without a revision, or with an old
   one, is refused and names the current revision.
4. A path with `..`, a hidden name or more levels than declared is refused.
5. A product's refusal (no right) comes back as a sentence, not as "not found",
   when the product says so (BookStack: a role without "access system API").

## 7. Dependencies

`oaap.apps.runtime` (MCP door, procedure I), `oaap.core.identity` 2.12
(`X-OAAP-User-Idp`), `oaap.ai.mcp-gateway` (the caller), RFC-0110 (the wiki's
adapter answers this contract, D9).

## 8. Maturity

0.1: BookStack connector in the package `bookstack` 0.2.0, measured
2026-11-23. Forgejo, PCH, BDT and a system outside the tenant (`personal`)
follow (RFC-0121 §10).

## Deutsche Zusammenfassung

**Wozu.** Ein Konnektor macht ein System, in dem Menschen ihre Arbeit ablegen
(Wiki, Git, Projektordner), über wenige feste Verben ansprechbar: was gibt es,
lesen, schreiben, Ordner anlegen, suchen, „was darf ich hier“, Einstieg. Jeder
Aufruf läuft **als die Person** direkt am System; das System entscheidet allein.
Nichts wird kopiert, nirgends liegt eine Rechteliste.

**Ebenen.** Ablagetyp → Ablagesystem → Bereich (optional) → Ablage → Ordner →
Dokument. BookStack: Regal, Buch, Kapitel (eine Ebene), Seite. Pfade sind
`/kapitel/seite`.

**Schnittstelle.** MCP-Werkzeuge mit festen Namen `stores_about`,
`stores_stores`, `stores_list`, `stores_read`, `stores_write`, `stores_folder`,
`stores_search`, `stores_may`, `stores_entry`, `stores_create_store`. Ein
Schreiben auf ein bestehendes Dokument nennt die gelesene Revision. Was ein
Konnektor kann, sagt er in `about`; das Gateway bietet nur das an.

**Als die Person.** 0.1 kennt nur `assertion`: Die Plattform nennt die Person
mit ihrer Realm-Kennung; der BookStack-Konnektor findet daran das Konto und
arbeitet mit einem kurzen Token dieses Kontos. Ohne Person kein Aufruf, kein
technischer Benutzer für Inhalte.

**Reife.** Ein Konnektor (BookStack, Paket 0.2.0), am 23.11.2026 auf oaap-test
durch die Ablagetür des Gateways gemessen (27/27).

# RFC-0078: Help — Static Platform and App Knowledge for Any AI, through MCP, an API and a Page

- **Status:** **Draft (2026-11-10)** — D1, D3 (direction) and D4 (constraint)
  stated by Jörg on 2026-11-10; everything else proposed (§13). **Stage 0
  built (2026-11-11, reference 0.1.248, §5.1);** the app `help` (stages
  1–3) is not. §14 is the implementation plan.
- **Date:** 2026-11-10
- **Authors:** Jörg (the idea: an app `help` that knows the documentation,
  synchronises it instead of being redeployed, runs once centrally for
  everybody and also on a user's node where visibility applies — CLI and
  platform configuration for admins, app knowledge for users and key users;
  knowledge taken from the apps, several sources with priorities; offered
  through MCP, APIs and its own UI, in our chat and maybe the marketplace; the
  wish: connect any AI or harness to the platform's MCP and ask "How do I set
  up the backup on the CLI?" — the AI finds the sources, summarises, cites the
  originals and guides step by step), Claude (facts read in `oaap-docs`, the
  CLI, the identity spec and RFC-0073; design)
- **Depends on:** RFC-0073 (apps as MCP sources; manifest 0.11 `mcp:`),
  RFC-0065 (MCP gateway), `oaap.core.identity` 2.1/2.3 (roles,
  `X-OAAP-Roles`), RFC-0033 / `oaap.net.destinations` (outbound HTTP),
  RFC-0068 (closed egress), RFC-0010 (public-route throttling)
- **Related, not decided here:** RFC-0074 (assistants; the chat as MCP
  client), RFC-0075 (MCP Apps in chat), RFC-0077 (marketplace; app
  documentation travelling with a release), RFC-0050 (package catalog),
  the planned repository move (§7), capability idea "Anwender-Dokumentation +
  Hilfecenter-App" (2026-08-23), which this RFC supersedes in its
  delivery part
- **Not part of this RFC:** anything about the state or configuration of a
  node or tenant. That is a separate MCP of the node (D1).
- **Idea store:** I-49

## Summary

An app **`help`** holds **static help knowledge** — the platform
documentation (`oaap-docs`), a generated CLI reference, and the
documentation of apps — in a small full-text index. It offers that knowledge
through three doors: an **MCP door** (manifest 0.11, reachable through the
tenant's MCP gateway, or directly on a central instance), a **read API** and
a **search-and-read page**.

`help` contains **no language model.** It searches, returns passages with
their origin and a link to the original, and offers a **guide prompt**. The
reasoning — summarising, choosing, guiding step by step — is done by the AI
the person already uses: Claude Code, our chat, any MCP client.

Knowledge comes from **several sources with priorities**: the platform's
documentation, app documentation (from packages, later from the installed
apps themselves), and local notes of the operator. Sources are **pulled**
through a destination by address, so new documentation needs no redeploy,
and a **seed** in the package keeps a node behind a firewall useful.

On a customer's node the result is **filtered by audience** — platform roles
named in each document's front matter. This is a filter for **relevance**,
not secrecy: the platform documentation is public in its repository anyway.

## 1. Facts (read 2026-11-10)

| Claim | Where |
|---|---|
| `oaap-docs` has 20 Markdown files, ~3,750 lines (256 KB): scenarios, CLI reference, operation, FAQ, templates | `oaap-docs/` |
| Documents carry their version **in prose**: "Geprüft gegen Referenz **0.1.42**" … **0.1.202**; four documents (among them the CLI reference and *Produktivsetzung*) still say 0.1.42; the reference is at **0.1.247** | `grep` in `oaap-docs`; `oaap-reference/VERSION` |
| The CLI is defined in one file with 76 sub-parsers and 336 `help=` strings — a source a reference can be generated from | `oaap-reference/platform/appctl.py` |
| All 20 apps in `oaap-apps/apps` have a `README.md`; none has a `docs/` folder | `oaap-apps/apps/*` |
| An app declares one MCP door with `mcp: path:`; a gateway of the same tenant finds it and the app answers as the person the platform carries through | RFC-0073 §2–§4, manifest 0.11 |
| `X-OAAP-Roles` carries **all** roles of the person, `server_admin` included; the spec forbids reading `server_admin` as authority inside an app, not as information | `oaap.core.identity` 2.1, 2.3; reference `services/identity/app.py` |
| Instances start no connection of their own; destinations are the one way out | RFC-0068 |
| Apps of this kind are written with the standard library only (`care.rebuild: self`), MCP door in its own module | `oaap-apps/apps/vorgaenge` (`mcp_door.py`) |
| All repositories are addressed as `github.com/MDJoerg/…`; 9 files in `oaap-docs`, the specs and `install.sh` name GitHub hosts literally; a move of the repositories is planned (§7) | `.gitmodules`; `grep` |
| Whether an instance learns the platform version (`OAAP_VERSION`) is **not** read yet — the platform knows it, the instance contract does not name it | `appctl.py` `_platform_env`; `oaap.apps.runtime` (open point O1) |

## 2. Scope: static knowledge only (D1)

`help` answers "how does it work, how do I do it, what does this command
do". It never answers "how is it set up here". It reads no node state, no
instance list, no configuration, no logs, and it needs no platform key
beyond what every app gets. A question about the node's own state belongs to
a separate MCP of the node, decided elsewhere.

This keeps `help` harmless: it can run publicly, on any node, in any tenant,
without becoming a back door.

## 3. Sources and priorities (D3)

A **source** is a named set of Markdown documents with a kind, an address,
a priority and a trust level. Configuration lives in `/data/sources.yaml`
(stage 1) and in the page for `admin` (stage 2).

```yaml
sources:
  - name: oaap-docs
    kind: archive            # a tar.gz of a repository ref, fetched through a destination
    destination: docs-origin # the address lives in the destination, not here (§7)
    path: /archive/main.tar.gz
    root: oaap-docs-main/    # folder inside the archive
    web: "https://<host>/<org>/oaap-docs/src/branch/main/{path}"   # link template for citations
    priority: 50
    trust: platform
  - name: cli
    kind: archive            # the generated CLI reference (§5), same mechanism
    destination: docs-origin
    path: /archive/main.tar.gz
    root: oaap-docs-main/cli/generated/
    priority: 60
    trust: platform
  - name: local
    kind: local              # files the operator uploads into /data/local
    priority: 90
    trust: local
```

**Kinds:**

| Kind | Stage | What |
|---|---|---|
| `archive` | 1 | a repository archive (`tar.gz`) of a ref, fetched through a destination; GitHub and Forgejo both serve one |
| `local` | 1 | Markdown files uploaded by `admin` into `/data/local` — own notes, corrections |
| `seed` | 2 | the archive bundled into the package at build time; used until the first successful fetch, and when no destination is configured |
| `catalog` | 2 | the `README.md` and `docs/` of the app packages in the tenant's package catalog (RFC-0050), read from the ZIP without unpacking anything else |
| `apps` | 3 | the documentation of the apps **installed** in the tenant, listed by the platform (§3.2) |
| `marketplace` | 3 | the documentation of a release in a marketplace (RFC-0077) |

**Priorities.** Every document has an `id` (§4). When two sources carry the
same `id`, the higher priority **shadows** the lower one; the shadowed
document stays readable by its source-qualified id and is shown as shadowed.
In search, priority is one ranking factor among others. A `local` source
above everything lets the operator correct a platform text on their node
without waiting for an upstream change.

**App documentation is not mandatory** (D3). An app without documentation
simply has none in `help`. Stage 3 adds an optional declaration (§3.2);
before that, the `catalog` kind takes what a package happens to contain.

### 3.1 Fetching

- Fetched on start, then on a timer (default every 6 hours) and on a button
  for `admin`. The new archive is indexed into a fresh index; the old one
  answers until the new one is complete; a failed fetch keeps the old index
  and is shown with its error. Never an empty index because of a bad fetch.
- Archive limits: 50 MB compressed, 5,000 files, only `.md` and images
  referenced by them are kept; paths with `..`, absolute paths and links are
  refused per entry (same rules as the catalog's ZIP reader).
- No `git` binary, no clone: one HTTP request per source.

### 3.2 Documentation from the installed apps (stage 3, a platform change)

A manifest field, **optional**:

```yaml
docs:
  path: docs/        # a folder in the package; README.md is always included
  audience: [admin, keyuser, user]   # default for documents without front matter
```

and a consumer declaration for `help`, built like `mcp_sources`:

```yaml
docs_sources:
  read: true
```

The platform lists, on the help instance's own site, the instances of **the
same tenant** whose app declares `docs:` (name, app, version), and serves
their documentation files read-only from the installed package. No other
tenant, ever. This is the only part of this RFC that changes the platform
(manifest 0.14); whether apps *without* the declaration contribute their
`README.md` is D10.

## 4. The document

Every document may start with YAML front matter. All fields are optional;
the defaults are chosen so that a missing field never widens the audience.

```yaml
---
id: scenario/backup-cli        # stable across renames; default: path without .md
title: Backup auf der CLI einrichten
audience: [server_admin, support]
applies_from: "0.1.200"         # platform version from which the text is true
applies_until: ""               # empty = still true
checked_against: "0.1.247"
checked_on: 2026-11-10
lang: de
tags: [backup, cli, tresor]
---
```

- **`audience`** names platform roles (`oaap.core.identity` 2.1) or
  `public`. **Default for `trust: platform` and `local`:** the operator roles
  `server_admin`, `tenant_admin`, `support`. **Default for app sources:** the
  manifest's `docs.audience`, else `admin`. A document without front matter is
  therefore never shown to a plain user by accident.
- **`checked_against` / `checked_on`** replace the prose line "Geprüft gegen
  Referenz …". Every hit carries them, so the AI can say: "this guide was
  checked against 0.1.202 on …". A check script in `oaap-docs` (§14) reads the
  front matter; a document that says "Geprüft gegen" in prose but has no field
  is reported.
- **Sections** (`##`, `###`) are the unit of search; a hit names its section
  and anchor.
- Scenarios keep their structure — *Voraussetzungen*, numbered steps, a
  *Prüfen* line per step, *Wenn es schiefgeht* — because a guiding AI is only
  as good as that structure. This is a writing rule for `oaap-docs/AGENTS.md`,
  not a format the index enforces.

## 5. The generated CLI reference

The hand-written `oaap-docs/cli/README.md` was checked against 0.1.42; the
CLI has grown by 205 releases since. The reference is therefore **generated
from the parser** and the hand-written text keeps what a generator cannot
know: examples, warnings, the "why".

- A command `oaap help --markdown <dir>` (reference) writes one Markdown file
  per command group from the `argparse` definitions, with front matter
  (`id: cli/<group>/<command>`, `audience` from the command's gate:
  `sudo` → operator roles, read-only commands → plus `support`,
  `checked_against` = the version that generated it).
- The release process of the reference writes these files into
  `oaap-docs/cli/generated/` — by hand at first (one command), later in CI.
- The hand-written reference links to the generated pages and is no longer a
  list of options.

### 5.1 Stage 0 as built (2026-11-11, reference 0.1.248)

Where the build sharpened the text above:

- **One file per appctl command**, not per group: `oaap tenant` →
  `tenant.md` (`id: cli/tenant`), `oaap app install` → `app-install.md`
  (`id: cli/app/install`), plus `README.md` (`id: cli/generated`) as the
  index; 78 files for 76 commands, the wrapper's own commands and the index.
  Most commands vary by a positional `action`, not by nested subcommands, so
  an action is a row in the page's *Actions* table, not a file.
- **The sudo line is read, not described.** `main()` was split into
  `build_parser()` and `is_read_only(args)`; `oaap help` probes every action
  of every command through that same function (with the other arguments left
  out), so "needs `sudo`" cannot drift from what the node refuses.
- **Audience:** only `server_admin` has a shell on a node; `support` is its
  read-only counterpart. Hence commands that always need root →
  `[server_admin]`, commands with a read-only action → `[server_admin,
  support]`. `tenant_admin` gets no CLI page (no shell).
- **Internal commands** (help text starting with `internal:`, called by
  update, install, the portal or a timer) get a page tagged `internal` and a
  separate table in the index, so an AI can recognise them, but they are left
  out of `oaap help`. Three lacked the marker and got it; 17 commands had no
  help text at all and got one.
- **What argparse cannot know** stays in `appctl.py` as two lists —
  `WRAPPER_GROUPS` (what `bin/oaap` passes on under its own name) and
  `WRAPPER_OWN` (what `bin/oaap` does itself: status, version, setup-token,
  update, uninstall) — and `test/test_cli_reference.py` holds both against
  the wrapper's `case`.
- **Regeneration is safe:** files carrying the generated marker that were not
  written this time are removed; files without it are never touched. Output
  is byte-identical across Python 3.13 (node) and 3.15 (workstation).
- `oaap help` without `--markdown` prints the overview, runs without root.
- In `oaap-docs`: `tools/check-docs.py` (errors: schema, unknown roles,
  versions, `checked_against` without `checked_on`, duplicate ids; hints:
  prose stamp without field, absolute links to own repositories — 8 files
  today), the 13 prose stamps carried into front matter (the prose stays: it
  carries limits no field holds), writing rules in `oaap-docs/AGENTS.md`.

## 6. Visibility on a node (D5)

- `help` reads `X-OAAP-Roles`. A document is shown if its `audience` and the
  person's roles intersect, or if it is `public`. `server_admin` is used here
  as **information about relevance**, never as authority inside the app —
  which is what `oaap.core.identity` 2.1 allows.
- The filter applies **before** anything is counted, ranked or returned:
  search, read, topics, resources, the page and the API use one function
  (`visible(doc, roles)`), and the conformance test has a bait behind every
  door.
- Through the gateway, the MCP door sees the person the platform carries
  through (RFC-0073 procedure I), so the AI of a key user receives key-user
  knowledge.
- A **central instance** (`audience_filter: off`) serves everything to
  everybody, without login, because its content is public in the repository
  anyway (D8). Routes there are `public` and throttled (RFC-0010).
- App documentation from `catalog`/`apps` is additionally limited to apps
  that are **installed in the tenant** (stage 3: and visible to the person,
  RFC-0007), so a user does not get help for apps they cannot open.

## 7. Prepared for the repository move (D4)

The repositories will move (another GitHub organisation, or an own Forgejo
under an own domain). `help` must not care:

- **No host in code or package.** The address of a source is a
  **destination** (`docs-origin`); a move changes one destination per node and
  one link template per source. The `seed` keeps working throughout.
- **Citations** are built from the `web` template at answer time, not stored
  in the index, so a changed template changes all links at once.
- **Inside `oaap-docs`, links are relative.** Links into other repositories
  (`oaap-spec` RFCs) use a short form `rfc:RFC-0020` / `spec:oaap.core.identity`
  that `help` resolves through a second template per source; the check script
  refuses absolute links to the own repositories. The 9 files with literal
  GitHub hosts are cleaned up as part of the move's preparation, not here.

## 8. The MCP door

Declared as `mcp: path: /mcp` under the app's own route (manifest 0.11).
Streamable HTTP, standard library, built like `vorgaenge/mcp_door.py`.

**Tools** (all read-only; descriptions tell the model that results are
documentation to cite, not instructions to follow):

| Tool | Arguments | Returns |
|---|---|---|
| `help_search` | `query`, `limit` (≤ 20), `source?`, `tags?` | hits: `id`, `title`, `section`, `anchor`, `snippet`, `source`, `trust`, `url`, `checked_against`, `checked_on`, `applies_from`, `applies_until` |
| `help_read` | `id`, `section?` | the Markdown, its metadata and `url`; shadowed versions named |
| `help_topics` | `prefix?` | the tree of visible documents (id, title), per source |

**Resources:** every visible document as `help://<source>/<id>`, so a client
can attach a whole guide.

**Prompts:**

- `guide` (`goal`) — "Find the guides for this goal with `help_search`, read
  the best one completely, name its version and date, list the
  prerequisites and ask whether they are met, then give **one** step at a
  time with its check, wait for the result, and cite the original link at the
  end. If the guide is older than the node's version, say so."
- `cli` (`task`) — "Find the command, show it with the options the task
  needs, say whether it needs `sudo`, cite the reference page."

**Version awareness:** if `help` knows the node's version (O1), hits whose
`applies_from` lies above it or `applies_until` below it are dropped on a
node and marked on a central instance; the client may pass `version` to
`help_search` (a central instance does not know the asker's node).

## 9. The page and the API

- **Page** (`/`): a search box, hits with source, version and date, a reading
  view with table of contents and "Original öffnen". For `admin`: sources,
  last fetch, errors, "jetzt holen", upload into `local`.
- **API** (`/api/v1/search`, `/api/v1/docs/<id>`, `/api/v1/topics`): the same
  answers as the tools, JSON. The portal and the marketplace may link into the
  page; the portal gets a launchpad tile, no embedded help.
- Markdown is rendered with HTML escaped; no scripts, no raw HTML from any
  source.

## 10. Chat and marketplace

- **Chat** (RFC-0074) reaches `help` through the tenant's gateway like any
  source, once the operator approves its entries — nothing to build in the
  chat. The guide prompt works there as in Claude Code.
- **Marketplace** (RFC-0077): a release may carry documentation; stage 3 adds
  the source kind `marketplace`. The marketplace's own page may show a release's
  documentation; it does not need `help` for that.

## 11. Security

- Read-only. No tool, page or API changes anything outside `/data` of the
  instance; uploads into `local` only for `admin`.
- **Documentation is untrusted input for the AI.** App documentation comes
  from third parties. Every hit names its `source` and `trust`; tool and
  prompt texts say that commands in documentation are shown to the person, not
  executed; the gateway's approval of entries applies (RFC-0065 §4.2).
- One visibility function behind every door (§6); a document hidden from a
  person is answered like a missing one (404 / "not found"), never "forbidden".
- Archive limits and path rules (§3.1); no unpacking of anything but Markdown
  and referenced images; no symlinks.
- Fetches only through a destination; nothing else leaves the instance.
- Public central instance: throttled, no upload route public, no admin page
  without login.

## 12. Stages

| Stage | Content | Platform change |
|---|---|---|
| 0 | Front matter and check script in `oaap-docs`; `oaap help --markdown`; generated CLI reference; writing rule in `oaap-docs/AGENTS.md` | reference: one CLI command |
| 1 | App `help`: sources `archive` + `local`, FTS index, MCP door (tools, resources, prompts), page, API; central instance on `oaap-test`, Claude Code connected directly | none |
| 2 | Audience filter, version filter, priorities and shadowing across sources, `seed`, `catalog`; installable on customer nodes through the catalog; admin page | none (O1 aside) |
| 3 | `docs:` / `docs_sources:` (manifest 0.14), source `apps`, source `marketplace`, launchpad tile | manifest 0.14 |

## 13. Decisions

Stated by Jörg on 2026-11-10:

- **D1 — Static help knowledge only.** Nothing from configuration or state;
  that is a separate MCP of the node.
- **D3 — Several sources with priorities; knowledge also from the apps.**
  Whether app documentation becomes mandatory is open — this RFC makes it
  optional.
- **D4 — The canonical repository will move.** `help` is built
  host-neutral (§7); the move itself is prepared separately with Claude.

Proposed (as recommended unless Jörg says otherwise):

- **D2 — No language model in `help`.** Search, read, prompts; the client's
  AI reasons. An own model (for the page) can come later through the AI
  gateway without changing the doors.
- **D5 — Audience = platform roles from front matter; relevance, not
  secrecy;** missing front matter → operator roles only.
- **D6 — SQLite FTS5, no embeddings.** At ~4,000 lines an agentic search with
  `help_search` + `help_read` beats a vector index; revisit at ten times the
  size.
- **D7 — Version ranges in the documents, one current archive** — not one
  bundle per platform version.
- **D8 — The central instance is public without login and unfiltered;**
  throttled; host `oaap-test` first, later public (where: Jörg).
- **D9 — Name `help`, app id `help`.** (Alternative: `hilfe`.)
- **D10 — Apps without a `docs:` declaration contribute their `README.md`
  with audience `admin`** (all 20 apps have one; they are developer texts,
  mostly English). Alternative: nothing without declaration.
- **D11 — Language as written.** German platform texts, English app READMEs;
  the client's AI answers in the person's language. No translation in `help`.

Open points:

- **O1 — Platform version for instances.** Does an instance receive
  `OAAP_VERSION`? If not: a platform variable (small change to
  `oaap.apps.runtime`), or the version filter only on request.
- **O2 — FTS5 in the base image.** To be measured (`sqlite3` of the Python
  image must have FTS5 compiled in); fallback: a plain token index in SQLite.

## 14. Implementation plan

### 14.1 Repositories and files

| Where | What |
|---|---|
| `oaap-docs/tools/check-docs.py` | front matter schema, defaults, "Geprüft gegen" without field, absolute links to own repositories, ids unique |
| `oaap-docs/AGENTS.md` | writing rule for scenarios (§4), front matter, link short forms |
| `oaap-docs/cli/generated/` | output of `oaap help --markdown` |
| `oaap-reference/platform/appctl.py` | `oaap help --markdown <dir>` (stage 0) |
| `oaap-apps/apps/help/oaap-app.yaml` | manifest 0.11, route `/` (`public` on a central instance via config, else `[admin, keyuser, user, tenant_admin, server_admin, support]`), `mcp: path: /mcp`, destination `docs-origin`, storage `/data` |
| `…/help/app.py` | HTTP server, page, API, admin page |
| `…/help/sources.py` | fetch through destination, archive reader with limits, `local` |
| `…/help/index.py` | front matter, sections, FTS5, shadowing, `visible()` |
| `…/help/mcp_door.py` | tools, resources, prompts |
| `…/help/test_*.py` | incl. baits per door |

### 14.2 Index (SQLite)

```sql
CREATE TABLE doc (source TEXT, id TEXT, path TEXT, title TEXT, audience TEXT,
                  applies_from TEXT, applies_until TEXT, checked_against TEXT,
                  checked_on TEXT, lang TEXT, tags TEXT, body TEXT,
                  PRIMARY KEY (source, id));
CREATE VIRTUAL TABLE section USING fts5(source UNINDEXED, id UNINDEXED,
                  anchor UNINDEXED, heading, text, tokenize='unicode61');
CREATE TABLE fetch (source TEXT PRIMARY KEY, at TEXT, ok INTEGER, error TEXT,
                  sha256 TEXT, files INTEGER);
```

### 14.3 Measurements for stage 1 (`oaap-test`)

- **M1** "Wie richte ich auf der CLI das Backup ein?" in Claude Code with
  `help` connected: the answer names the right guide(s), cites the original
  links, and guides step by step with checks.
- **M2** "Welcher Befehl übernimmt eine Test-Instanz nach Produktiv?" → the
  right command, `sudo`, reference page.
- **M3** A changed document in the repository is found after "jetzt holen",
  without redeploy.
- **M4** A broken archive (truncated, `..` path, 60 MB) leaves the old index
  answering and shows the error.
- **M5** A `local` document with the same id shadows the platform text; the
  original stays readable.
- **M6** Changing the destination's address (simulated move) changes nothing
  but the source; the `web` template changes every citation.
- **M7** Markdown with `<script>` and raw HTML is shown escaped.
- **M8** O2 measured: FTS5 present in the image.

Stage 2 adds **M9** (a `user` never receives an operator document through
search, read, topics, resources, page or API — one bait per door) and **M10**
(a node without destination answers from the seed).

## Deutsche Zusammenfassung (für Jörg)

**Worum es geht:** Eine App **`help`** kennt das **statische Hilfewissen**:
die Plattform-Doku (`oaap-docs`), eine aus dem Code erzeugte CLI-Referenz
und die Doku der Apps. Sie bietet es auf drei Wegen an: als **MCP-Tür**
(über das MCP-Gateway des Mandanten oder direkt auf einer zentralen
Instanz), als **API** und als **Such- und Leseseite**. Eine KI, egal welche,
kann damit fragen: „Wie richte ich auf der CLI das Backup ein?“

**`help` hat keine eigene KI.** Sie sucht, liefert Abschnitte mit Herkunft,
Prüfstand und Link zum Original, und bietet einen **Anleitungs-Prompt**:
Voraussetzungen klären, einen Schritt nach dem anderen mit Prüfung,
am Ende das Original nennen. Zusammenfassen und Führen macht die KI, die du
ohnehin benutzt: Claude Code, unser Chat, jeder MCP-Client.

**Nur statisches Wissen** (deine Entscheidung D1): nichts aus Konfiguration
oder Zustand eines Knotens. Das wird ein eigener MCP des Knotens.

**Mehrere Quellen mit Prioritäten** (D3): Plattform-Doku, erzeugte
CLI-Referenz, Doku aus den App-Paketen, eigene Notizen des Betreibers. Hat
ein Dokument in zwei Quellen dieselbe Kennung, gewinnt die höhere Priorität.
Die andere bleibt lesbar. So kann ein Betreiber einen Plattformtext auf
seinem Knoten korrigieren. App-Doku ist **nicht Pflicht**. Später (Stufe 3)
kann eine App im Manifest optional `docs:` erklären, dann liest `help` die
Doku der im Mandanten installierten Apps. Das ist die einzige
Plattformänderung im ganzen RFC.

**Aktualisieren ohne Neuausrollen:** `help` holt ein Archiv des
Doku-Repositorys über eine Destination (das ist der einzige Weg nach
draußen, RFC-0068), standardmäßig alle 6 Stunden oder auf Knopfdruck. Ein
missglückter Abruf lässt den alten Stand antworten. Eine Kopie im Paket
(„seed“) hält Knoten hinter der Firewall arbeitsfähig.

**Sichtbarkeit auf einem Knoten:** Jedes Dokument nennt im Kopf seine
Zielgruppe (Plattformrollen). Ein Anwender bekommt keine CLI-Anleitungen.
Das ist **Relevanz, keine Geheimhaltung**, denn die Doku ist ohnehin
öffentlich. Ohne Kopf gilt: nur für Betreiber. Die zentrale Instanz zeigt
alles, ohne Anmeldung.

**Vorbereitet auf den Repo-Umzug** (D4): Keine Adresse steht im Code. Die
Quelle ist eine Destination, die Links zum Original entstehen aus einer
Vorlage. Ein Umzug ändert also eine Destination und eine Vorlage, sonst
nichts. Innerhalb der Doku werden Links relativ.

**Ein Befund nebenbei:** Die CLI-Referenz ist gegen 0.1.42 geprüft, die
Plattform steht bei 0.1.247. Deshalb Stufe 0: die CLI-Referenz aus den
Befehlsdefinitionen erzeugen (`oaap help --markdown`), Kopfzeilen und ein
Prüfskript in `oaap-docs`. Das hilft sofort, auch ohne App.

**Stufe 0 gebaut (11.11., Referenz 0.1.248, §5.1):** `oaap help` zeigt die
Übersicht, `oaap help --markdown <dir>` schreibt je Befehl eine Seite mit Kopf
(78 Dateien in `oaap-docs/cli/generated/`). Ob ein Befehl `sudo` braucht, liest
der Generator aus derselben Funktion, mit der der Knoten abweist. Er kann es
also nicht falsch abschreiben. Zielgruppe: nur-sudo → `server_admin`, mit
lesender Aktion → zusätzlich `support`. 17 Befehle hatten keinen Hilfetext und
haben jetzt einen. In `oaap-docs` gibt es ein Prüfskript, die Schreibregel, und
die 13 „Geprüft gegen“-Sätze stehen jetzt auch als Kopf.

**Stufen:** 0 Doku-Vorbereitung · 1 App `help` zentral auf oaap-test, Claude
Code angebunden (Messung: deine Backup-Frage) · 2 Zielgruppen- und
Versionsfilter, Prioritäten, Doku aus dem Paketkatalog, auf Kundenknoten
installierbar · 3 `docs:` im Manifest, Marketplace, Kachel im Portal.

**Offen für dich:** D2 (keine eigene KI in `help`), D5 (Zielgruppe =
Plattformrollen), D6 (Volltextsuche statt Vektoren), D7 (Versionsbereiche
in den Dokumenten), D8 (zentrale Instanz öffentlich und ungefiltert; wo
später?), D9 (Name `help` oder `hilfe`), D10 (README als Rückfall für Apps
ohne `docs:`), D11 (Sprache wie geschrieben). Technisch offen: O1 (kennt
eine Instanz die Plattformversion?), O2 (FTS5 im Abbild).

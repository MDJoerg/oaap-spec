# RFC-0094: Help as the Tenant's Documentation — Apps Bring Their Docs, Products, Versions, Languages

- **Status:** **Draft (2026-11-18)** — D1–D10 open. Nothing built.
- **Date:** 2026-11-18
- **Authors:** Jörg (the direction, 2026-11-18: "help in every tenant,
  fed automatically by the installed apps, OAAP's own docs switchable off,
  several categories, versions kept or not, uploads by the tenant_admin,
  a template and a briefing, HTML films instead of videos, layouts from
  sober to colourful, filters by audience and document type, several
  languages and later automatic translation, available to the AI chat; MVP:
  the BDT app's documentation through help, searchable by the chat"),
  Claude (reading of the reference and the BDT package, design)
- **Depends on:** RFC-0078 (help: sources, the document, visibility, the
  MCP door, requests — this RFC is its stage 3, widened), RFC-0073 (an app
  as MCP source; `mcp_sources` is the model for `docs_sources`), RFC-0075
  (a second, cookie-less origin — for interactive HTML), RFC-0074 (the
  chat), RFC-0027 (API keys), RFC-0063 (host directories mounted into an
  instance), RFC-0007 (instance visibility), `oaap.apps.runtime` 2.32
- **Not part of this RFC:** an editor inside help (documents are written
  elsewhere and delivered); a wiki; help across tenants (a central public
  instance stays RFC-0078 D8)

## Summary

`help` today is a search over OAAP's own documentation (an archive behind
the destination `docs-origin`, a seed in the package), for people through a
page and for AIs through MCP. RFC-0078 §3.2 foresaw, as stage 3, that the
**installed apps of a tenant** contribute their documentation. The BDT app
shows that the content exists: its package carries 99 Markdown files under
`app/help/` (entry, quickstart, experts, 84 tile descriptions, an FAQ) —
without front matter, and today nothing reads them.

This RFC makes `help` **the documentation of a tenant**:

1. **Apps declare their documentation** (manifest 0.17 `docs:`): one or
   more *help products*, each a folder in the package with title, language,
   default audience and a mapping of folders to document types — so a
   package without front matter is still well described.
2. **The platform hands it over**, same tenant only, built like
   `mcp_sources`: a help instance that declares `docs_sources` gets the
   documentation of the tenant's installed apps read-only, per instance and
   version, refreshed at every install, update and removal.
3. **Help shows products**, not one pile: a start page with tiles per
   product (layouts from sober to colourful), search with filters
   (product, document type, readers, language, version), and the same
   facets through MCP — so the tenant's chat finds BDT's FAQ the moment
   BDT is installed.
4. **OAAP's own documentation becomes one product among others** and can
   be switched off; then the destination `docs-origin` is simply left
   unbound.
5. Prepared, staged later: **versions** kept by help's own policy,
   **uploads and an API** for the tenant_admin, a **template and a
   briefing** for people and AIs, **interactive HTML** ("films") on a
   sandboxed origin, **languages** with fallback and marked machine
   translation, **release notes** per version (the bridge to RFC-0093's
   `UPGRADE.md`), **context links** from apps into help.

The format is defined once, completely, in stage 1, so that later stages
change help and the node, not the manifest.

## 1. Facts (read on 2026-11-18)

| What | Where | Today |
|---|---|---|
| Help app | `oaap-apps/apps/help` 0.3.1, manifest 0.11 | sources `seed` and `archive` (destination `docs-origin`), `local` uploads by `admin`; SQLite full-text index; page, `/api/v1`, MCP door (`help_search`, `help_read`, `help_topics`, prompts `guide`, `cli`), requests (`help_request_guide`); audience filter by `X-OAAP-Roles` |
| App documentation | RFC-0078 §3.2 | designed (`docs:` + `docs_sources`), **not built**; source kinds `catalog`, `apps`, `marketplace` not built |
| BDT package 0.757.0-2 | retained ZIP on oaapx01 | `app/help/`: `index.md`, `faq.md`, `einstieg/` (3), `quickstart/` (5), `experten/` (5), `kacheln/` (84); German; no front matter; no `docs:` in its manifest (0.15) |
| Help instances on oaapx01 | registry | `oaap-web-help` (central), `bec-bec-help`; none in `bdt` |
| Chat → help | RFC-0078 §10 | through the tenant's MCP gateway once the operator approves help's entries; `bdt` has no chat and no gateway today |
| Interactive HTML | help `render.py` | Markdown rendered with HTML escaped, no scripts — correct for help's own origin, which carries the session |
| Second origin | RFC-0075, runtime 2.32.4 | `ui_sandbox`: `<instance>--ui.<rest>`, cookie-less — exists for MCP App views |
| Destination optional? | `oaap.net.destinations` | a declared need may stay unbound; help then runs on its seed (already so) |

## 2. The declaration in the app (manifest 0.17 `docs:`)

```yaml
oaap_manifest: "0.17"
docs:
  - product: bdt                    # id within the tenant's help; default app.id
    title: "BDT – Business Daily Tools"   # default app.name
    path: app/help/                 # folder in the package
    entry: index.md                 # start page of the product; default index.md, then README.md
    icon: app/help/icon.svg         # optional, svg/png in the package, for the tile
    color: "#0a6ed1"                # optional, for colourful layouts
    lang: de                        # language of documents that do not say
    audience: [user, keyuser, admin]  # platform roles who see it (RFC-0078 §6)
    readers: [end-user]             # who it is written for (§4.2), a filter, not a lock
    kinds:                          # document type by path, longest match wins
      faq.md: faq
      quickstart/: tutorial
      einstieg/: concept
      kacheln/: function
      experten/: admin-guide
    media: [png, svg, jpg, webp, html]  # file types besides .md that help takes (html: §8)
  - product: bdt-admin              # an app may bring more than one product
    title: "BDT für Betreiber"
    path: ops/docs/
    audience: [admin]
    readers: [operator]
```

- A **list**; a single mapping is accepted as a list of one.
- Every field but `path` is optional. Defaults never widen: `audience`
  defaults to `[admin]` (RFC-0078 §4), `kinds` to nothing (type
  `unspecified`), `media` to `[png, svg, jpg, webp]` — **not** `html`.
- **Front matter in a document wins** over the declaration (`kind`,
  `audience`, `readers`, `lang`, `title`, `id`, `applies_from`, …, RFC-0078
  §4 plus §4 below).
- Limits per product: 5,000 files, 50 MB unpacked, paths without `..`, no
  links, only `.md` and the declared media types; the rest of the package
  is never read. A violation drops the product with a reason in the
  install output and in help's source list — it never fails the install.
- `product` ids are unique per tenant; two instances declaring the same id
  (production and test of one app, or two installations) are kept apart by
  instance (§3) and shown as one product with a choice (§5).
- A node before 0.17 ignores the section (RFC-0012 §8.2).

## 3. What the platform hands over (`docs_sources`)

The consumer side, built like `mcp_sources` (runtime 2.32):

```yaml
docs_sources:
  read: true
```

- At every install, update, promotion, removal and visibility change of an
  instance that declares `docs:`, the node extracts the declared folders —
  and nothing else — from the **bytes in service** (the retained package or
  the recorded Git commit, runtime 2.31) into the tenant's documentation
  directory:

  ```
  <tenant>/docs/<instance-key>/<version>/<product>/…      read-only for apps
  <tenant>/docs/<instance-key>/<version>/docs.json        written by the node
  <tenant>/docs/index.json                                 the current set
  ```

  `docs.json` carries instance (key, local name, channel), app id and name,
  version, the normalised declaration, extraction time, file count, digest
  and dropped products with reasons. `index.json` lists what is current.
- **Mounted read-only** into every instance of **the same tenant** that
  declares `docs_sources: {read: true}`, at `/oaap/docs` — not served over
  HTTP: no key, no listener, no route, and the boundary is the directory.
  (D2.) Never into another tenant, never into a rehearsal's source of truth
  (a rehearsal gets its own copy of the set it was made from).
- **Which versions the node keeps:** only the current version of each
  instance (and the previous one until the next passed update — the
  RFC-0093 snapshot window). Keeping history is help's business (§6), so a
  tenant that wants no history leaves none on the node.
- **Visibility** (RFC-0007): `docs.json` carries the instance's visibility
  groups; help filters per person (`X-OAAP-Groups`, trustworthy since
  0.1.296). A person does not get help for an app they cannot open
  (RFC-0078 §6).
- **Test instances**: their documentation is handed over too, marked
  `channel: test`; help shows it only on request (§5, D4).
- The node tells every instance of the tenant where help is:
  `OAAP_HELP_URL` (the canonical address of the tenant's production help
  instance, empty if none) — for context links (§9).

## 4. The document (additions to RFC-0078 §4)

### 4.1 Document types (`kind`)

A fixed vocabulary, because a filter over free words filters nothing:

| `kind` | Deutsch (UI) | For |
|---|---|---|
| `overview` | Überblick | what a product is, the entry page |
| `concept` | Konzept | how something is meant, background |
| `function` | Funktionsbeschreibung | one feature, tile, screen |
| `tutorial` | Schritt für Schritt | a guided path with checks (RFC-0078 §4 structure) |
| `howto` | Anleitung | a short recipe for one goal |
| `faq` | FAQ | questions and answers; each `**question**` or `###` is a hit |
| `reference` | Referenz | fields, options, tables |
| `cli` | CLI-Syntax | commands (the generated CLI reference, RFC-0078 §5) |
| `api` | Schnittstelle | web services, MCP tools |
| `troubleshooting` | Fehlerbehebung | symptoms → causes → fixes |
| `admin-guide` | Betrieb | installation, configuration, backup |
| `release-notes` | Neuerungen | what changed in a version (§9) |
| `glossary` | Glossar | terms |
| `presentation` | Präsentation | an interactive HTML piece (§8) |
| `unspecified` | — | nothing said |

An unknown `kind` counts as `unspecified` and is listed in help's source
view as a warning for the author.

### 4.2 Readers (`readers`)

`audience` (RFC-0078) decides **who may see** a document, by platform role.
`readers` says **who it is written for** and is only a filter: `end-user`,
`power-user`, `admin`, `developer`, `consultant`, `operator`. A product or
document may name several. (D5: fixed list, or free words with these as
suggestions.)

### 4.3 Language

- A document's language is front matter `lang`, else the product's `lang`.
- **Translations** sit next to the original: `faq.md` (the product's
  language) and `faq.en.md`, or a folder per language (`en/faq.md`). Same
  `id`, different `lang`.
- Help shows the person's language (portal setting, else the browser's
  `Accept-Language`), falls back to the product's language, and says so.
- **Machine translation** (stage 5, D7): on request ("Auf Englisch
  übersetzen") help asks the tenant's AI gateway, caches the result per
  document version and language, and marks it "maschinell übersetzt" with
  the original's date; it never shadows a human translation and is never
  sent to an AI outside the tenant's gateway.

## 5. Help shows products

- **Start page** (`HELP_LAYOUT`): `nüchtern` (search and a list of
  products), `kacheln` (a dashboard: a tile per product with icon, title,
  number of documents, the entry page as click target, search above),
  `bunt` (tiles in the products' colours, the newest release notes and the
  most read documents beside them). One template set, three stylesheets;
  the tenant's two colours (RFC-0042) feed all three.
- **Product page**: entry document, the product's documents grouped by
  `kind`, its versions (§6), its languages.
- **Search with facets**: product, `kind`, `readers`, language, version
  (default: the installed production version), source (`apps`, `oaap`,
  `uploads`). Facets show counts and only values that exist.
- **The same facets through MCP**: `help_search` gets `product`, `kind`,
  `readers`, `lang`, `version`; `help_topics` lists products first; a new
  tool `help_products` returns the products with versions and languages.
  A hit names product, version and type, so the AI can say "laut der
  BDT-FAQ (0.757.0) …".
- **OAAP's own documentation** is the product `oaap` (and `oaap-cli`), fed
  as today. `HELP_OAAP_DOCS` (`on`|`off`, default `on`): off removes both
  products, the seed is not indexed and the destination `docs-origin` may
  stay unbound — help then documents only the tenant's apps and uploads.
- Test-channel documentation (§3) appears behind "Vorschau (Test)" for
  `admin`/`keyuser` only (D4).

## 6. Versions (help's policy)

`HELP_VERSIONS`:

- `installed` (default) — only what the node currently hands over; an
  update replaces the product's documents, a removal removes them.
- `keep:N` — help copies each handed-over version into its own storage
  and keeps the newest N per product; older versions are readable and
  searchable on request ("Version 0.753.0 anzeigen"), never in default
  results.
- `all` — every version ever handed over, until the admin deletes one.

A removed app's documentation under `keep`/`all` stays, marked "nicht mehr
installiert". Uploads (§7) carry their own versions.

## 7. Uploads and an API (stage 3)

- The page for `admin` (help's admin, i.e. the tenant_admin in its tenant)
  gets "Hilfsprodukte": upload a **product package** (ZIP) — a `help.yaml`
  with exactly the fields of one `docs:` entry plus `version`, and the
  folder. Same limits, same rendering, source `uploads`, versions as in §6.
- **API** `PUT /api/v1/products/<product>/versions/<version>` (ZIP body),
  `DELETE …`, `GET /api/v1/products`; authenticated by a platform API key
  of the tenant (RFC-0027) whose scope names `help.upload:<instance>` —
  so a CI job or another app's AI can publish documentation without a
  person. (D8.)
- Uploads never shadow app documentation silently: the same `product` id
  as an installed app is refused unless the upload says `extends: <id>`
  (then its documents join that product as a separate source).

## 8. Interactive HTML ("films", presentations)

Jörg's example: a self-contained HTML animation used instead of a video.
HTML with scripts must never run on help's own origin — that origin
carries the person's session.

- Allowed only when the product declares `html` in `media` (or the upload's
  `help.yaml` does) and only for documents of kind `presentation` (front
  matter, or a `kinds` mapping such as `filme/: presentation`).
- Help declares `ui_sandbox` (RFC-0075) and serves such files **only** on
  its second origin `<instance>--ui.<rest>`, inside an `iframe` with
  `sandbox="allow-scripts"` (no same-origin, no forms, no top navigation,
  no popups) and a CSP that allows no network requests (`connect-src
  'none'`, `default-src 'self' data: blob:`). The page around it stays
  escaped Markdown.
- For search and AI they count by their title, front matter and an optional
  `*.md` transcript next to them (`film.html` + `film.md`); the AI cites
  the transcript, the person watches the film.
- Size limit per file 20 MB (D9).

## 9. More help offerings (prepared)

- **Release notes per version** (`kind: release-notes`, one file per
  version or a `CHANGELOG.md` split by `## <version>`): help shows "Neu in
  Ihrer Version" on the product page after an update. The same file is
  what RFC-0093 calls `UPGRADE.md`'s user-facing half — one source for
  "what changes" in the update dialog and in help.
- **Context links**: an app links into help with
  `${OAAP_HELP_URL}/p/<product>/<doc-id>#<anchor>`; help resolves the
  document in the person's language and the installed version. A
  declaration `docs[].context` (map of UI keys to document ids) is
  reserved in the schema now and read later.
- **Requests** (RFC-0078 §15) per product: a missing guide is filed against
  the product, and the product's author (the app's AI through the maintainer
  door) sees the requests for its product only.
- **A question to the support** from a document: hands over to the
  tenant's `vorgaenge` app (RFC-0061) with the document id — once the
  tenant has one.
- **The chat**: help's MCP door is read-only by construction. D6 proposes
  that the tenant's MCP gateway takes the entries of a `help` instance of
  its own tenant **approved by default** (help is a platform app, its tools
  are fixed and read-only), so "installed help" means "the chat can search
  it" without an operator's approval step.

## 10. Template and briefing

Help offers on its page and as a file in `oaap-apps` (for the Studio
briefing):

- **`help-vorlage.zip`**: `help.yaml` with every field commented, the
  folder structure by kind (`einstieg/`, `schritt-fuer-schritt/`, `faq.md`,
  `funktionen/`, `neuerungen/`, `filme/`), one example document per kind
  with front matter, an example translation, an example `film.html` +
  transcript.
- **`BRIEFING.md`** for a person or an AI writing documentation: the
  kinds and when to use which, front matter fields, the tutorial
  structure (prerequisites, numbered steps, a check per step, "Wenn es
  schiefgeht"), audience vs. readers, language and translation rules, the
  HTML rules of §8, and how to deliver: as `docs:` in the app's package
  (preferred), or as an upload/API call.
- The Studio briefing (RFC-0070) points to it: an app built in the Studio
  brings its `docs:` from the start.

## 11. Stages

| Stage | Content | Needs |
|---|---|---|
| **1 — MVP** | manifest 0.17 `docs:` (complete schema, §2) and `docs_sources`; the node extracts, mounts, refreshes (§3); help 0.4: source kind `apps`, products, `kinds`/`readers`/`lang` from the declaration, start page `kacheln`, facets product + kind, `help_search`/`help_topics` with `product`/`kind`, `help_products`, `HELP_OAAP_DOCS`; BDT adds `docs:` to its manifest; help in `bdt`; measured with the chat (or Claude Code through the gateway) finding a BDT FAQ answer | D1–D4, D6 |
| 2 | Layouts `nüchtern`/`bunt`, all facets, versions §6, test preview | D4 |
| 3 | Uploads, API, template and briefing §7, §10 | D8 |
| 4 | Interactive HTML §8 | D9 |
| 5 | Languages: translations §4.3, machine translation | D7 |
| 6 | Release notes, context links, support hand-over §9 | — |

Stage 1 needs, besides help and the node, one change in a package that is
not ours: the BDT app's manifest gets the `docs:` block of §2 (a letter to
the BDT AI); until then it can be measured with a copy of the BDT package
carrying the block, installed as a test instance.

## 12. Decisions for Jörg

- **D1 — The format now, completely?** *Recommendation: yes* — §2 with
  every field in manifest 0.17, even those read only in later stages
  (`icon`, `color`, `readers`, `media`, `context`), so authors write once.
- **D2 — Handed over as a read-only mount, not over HTTP?**
  *Recommendation: mount.* No listener, no key, the tenant directory is the
  boundary; the node writes, help reads.
- **D3 — Only the current version on the node, history in help?**
  *Recommendation: yes* (§3, §6) — a tenant that wants no history keeps none
  anywhere.
- **D4 — Test documentation visible?** *Recommendation:* handed over,
  shown only as "Vorschau (Test)" to `admin`/`keyuser`.
- **D5 — `readers` a fixed list?** *Recommendation: fixed* (six values, §4.2)
  — a filter needs shared words; extending the list is a spec change.
- **D6 — Help approved by default in the tenant's MCP gateway?**
  *Recommendation: yes* for a `help` instance of the same tenant — read-only
  fixed tools; the operator can still switch it off.
- **D7 — Machine translation through the tenant's AI gateway, on request,
  marked?** *Recommendation: yes*, never automatic for whole products,
  never outside the tenant's gateway.
- **D8 — Upload API by tenant API key with a help scope?**
  *Recommendation: yes* (RFC-0027 scopes).
- **D9 — Interactive HTML on the sandbox origin only, 20 MB per file?**
  *Recommendation: yes.*
- **D10 — Manifest version.** RFC-0093 (upgrade notes) also wants a manifest
  section. *Recommendation:* whichever is built first takes 0.17 — this one,
  since its stage 1 is wanted now; RFC-0093's `upgrade:` becomes 0.18.

## Deutsche Zusammenfassung

**Ziel:** `help` wird die Dokumentation eines Mandanten. Jede App bringt
ihre Doku selbst mit; installiert man sie, steht sie in der Hilfe und ist
für den KI-Chat durchsuchbar. Das MVP ist die BDT-App: Ihr Paket enthält
schon 99 Markdown-Dateien unter `app/help/` (Einstieg, Quickstart,
Experten, 84 Kachelbeschreibungen, FAQ), ohne Front Matter — heute liest
sie niemand.

**Wie:**

1. **Die App erklärt ihre Doku** im Manifest (0.17, `docs:`): ein oder
   mehrere *Hilfsprodukte*, je ein Ordner im Paket mit Titel, Sprache,
   Zielgruppe und einer Zuordnung Ordner → Dokumenttyp. So ist auch eine
   Doku ohne Front Matter gut beschrieben (bei BDT: `kacheln/` =
   Funktionsbeschreibung, `quickstart/` = Schritt für Schritt, `faq.md` =
   FAQ).
2. **Die Plattform reicht sie weiter**, nur im selben Mandanten: Bei jeder
   Installation, jedem Update und jedem Entfernen packt der Knoten genau
   diese Ordner aus und hängt sie lesend in jede Hilfe-Instanz des
   Mandanten ein, die `docs_sources` erklärt. Kein HTTP, kein Schlüssel.
3. **Die Hilfe zeigt Produkte:** Startseite mit Kacheln je Hilfsprodukt
   (Layouts nüchtern, Kacheln, bunt), Suche mit Filtern (Produkt,
   Dokumenttyp, Zielgruppe, Sprache, Version), dieselben Filter über MCP.
4. **Die OAAP-Doku ist ein Produkt unter anderen** und abschaltbar
   (`HELP_OAAP_DOCS=off`); die Destination `docs-origin` bleibt dann
   einfach ungebunden.
5. **Später, aber im Format schon vorgesehen:** Versionen nach Einstellung
   der Hilfe (nur installierte, die letzten N, alle); Hochladen und eine
   Schnittstelle für den tenant_admin; Vorlage (`help-vorlage.zip`) und
   Briefing für Menschen und KIs; interaktive HTML-„Filme“ nur auf der
   abgeschotteten Zweitadresse der Hilfe (RFC-0075); mehrere Sprachen mit
   Rückfall und gekennzeichneter Maschinenübersetzung über das KI-Gateway
   des Mandanten; Neuerungen je Version (die Brücke zu RFC-0093);
   Kontextlinks aus Apps in die Hilfe (`OAAP_HELP_URL`); Anfragen und
   Übergabe an den Support je Produkt; die Hilfe im Chat ohne
   Freigabeschritt.

**Stufen:** 1 MVP (Manifest, Knoten, Hilfe 0.4 mit Produkten und Filtern
Produkt/Typ, BDT trägt `docs:` nach, Hilfe in bdt, gemessen mit dem Chat),
2 Layouts, Versionen, Vorschau, 3 Hochladen, Schnittstelle, Vorlage,
Briefing, 4 HTML-Filme, 5 Sprachen, 6 Neuerungen, Kontextlinks, Support.

**Entscheidungen D1–D10:** Format jetzt vollständig (D1), Übergabe als
lesender Einhängepunkt (D2), auf dem Knoten nur die aktuelle Version,
Geschichte in der Hilfe (D3), Test-Doku nur als Vorschau für admin/keyuser
(D4), feste Liste der Zielgruppen (D5), Hilfe im MCP-Gateway des eigenen
Mandanten standardmäßig freigegeben (D6), Maschinenübersetzung nur auf
Anfrage und gekennzeichnet (D7), Hochladen per API-Schlüssel des Mandanten
(D8), HTML-Filme nur abgeschottet, 20 MB (D9), dieses RFC nimmt Manifest
0.17, RFC-0093 dann 0.18 (D10). Gebaut ist nichts.

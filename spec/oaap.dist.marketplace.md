# oaap.dist.marketplace — Digital Assets with Channels, Visibility and Entitlements

- **ID:** `oaap.dist.marketplace`
- **Version:** 0.2 (stage 2 of RFC-0077: the store front -- search and
  facets after the access rule, images, Markdown, access requests, §9);
  0.1: model, the access rule, publishing API, feed, the catalog's mirror mode
- **Maturity:** draft
- **Reference:** `oaap-apps/apps/marketplace` 0.2.0,
  `oaap-apps/apps/package-catalog` 0.2.0
- **RFC:** RFC-0077 (Accepted 2026-11-11)

## 1. Purpose

A marketplace distributes **digital assets** to people and machines. An OAAP
app package is one asset type (`oaap-app`); others exist beside it (`file`).
Nodes take OAAP packages through their **package catalog**, which follows the
marketplace's feed — the node itself does not change.

## 2. Model

- An **asset** has an id (`[a-z0-9][a-z0-9-]{1,38}[a-z0-9]`), a type, title,
  summary, description, a **visibility** and a set of **free channels**.
- A **release** (asset × version, `x.y.z[-pre]`) is **immutable**. The same
  version with the same primary file is idempotent (`200`); with a different
  file it MUST be refused (`409`). A version MUST NOT be reused, not even
  after a yank.
- **Files** are stored by their SHA-256; the hash is the key.
- **Channels** are global names (default `stable`, `beta`). A channel is a set
  of **placements** (release × channel), never a copy. The channel's
  **current release** is the highest non-yanked version placed in it
  (numeric ordering: `1.2.10` after `1.2.9`, `1.0.0` after `1.0.0-rc1`).
- **Yank** = recall with a **required reason**, kept in the event log. A
  yanked release MUST NOT be placed into a channel again.

## 3. Seeing is not obtaining — the access rule

For one principal (a person or machine as the platform names it; groups from
`X-OAAP-Groups`) and one asset there are three states:

| State | Listed, searchable, detail | Download, feed |
|---|---|---|
| hidden | no — `404`, never `403` | no |
| visible, locked | yes | no |
| obtainable | yes | yes, on the channels it covers |

- **Visibility** per asset: `anyone` | `signed-in` | a list of principals
  (users, groups). A principal with an entitlement for the asset also sees it.
- **Obtainable** on channel *c*: visible **and** (*c* is a free channel of the
  asset **or** the principal holds a non-expired **entitlement** covering *c*).
- A new asset starts **visible, locked** (`anyone`, no free channel).
- Operators (`admin`, `server_admin`) see and obtain everything.
- The rule MUST live in **one function** that every read path calls — list,
  search, detail, download, feed, public API, statistics. Filtering MUST
  happen **before** counting: a hidden asset changes no number.
- On a **public** route the platform sends no identity; the implementation
  MUST NOT read identity headers there either.

## 4. Publishing

All under `/api/v1/` (session or platform API key; RFC-0027):

| Method and path | Does |
|---|---|
| `POST /api/v1/releases` | multipart `file`, `type` (default `oaap-app`), `channels`, `notes`; for `file` also `asset`, `version` |
| `POST /api/v1/assets/{id}/releases/{v}/channels/{ch}` | place |
| `DELETE /api/v1/assets/{id}/releases/{v}/channels/{ch}` | remove a placement |
| `POST /api/v1/assets/{id}/releases/{v}/yank` | `{"reason": …}` required |
| `PUT /api/v1/assets/{id}` | title, summary, description; visibility and free channels by an operator only |

- For `oaap-app` the asset id and version come from `oaap-app.yaml` inside the
  ZIP. The ZIP MUST be inspected without unpacking or running anything; an
  archive with absolute paths, `..`, links, no manifest or an invalid version
  MUST be refused with a sentence, storing nothing.
- **Who may publish:** a publisher right (user or group × asset pattern such
  as `hbvp` or `oaap-*` × channels), granted by an operator.
- A client `tools/publish.py` takes the key from a file or `OAAP_KEY`, never
  from the command line.

## 5. The feed

`GET /feed/v1/oaap-apps?channel=<ch>` (a signed-in caller, usually a machine
user with an API key):

```json
{"schema": "oaap.marketplace.feed/0.1", "name": "…", "channel": "stable",
 "generated_at": "…",
 "apps": [{"id": "…", "name": "…", "version": "…", "released": "YYYY-MM-DD",
           "summary": "…", "description": "…",
           "package": {"url": "files/<sha256>", "sha256": "…", "size": 0}}],
 "withdrawn": [{"id": "…", "version": "…", "reason": "…"}]}
```

- One entry per OAAP app **obtainable** by the caller on that channel: its
  current release. `package.url` is relative to the feed and MUST be
  `files/<sha256>`.
- `withdrawn` lists yanked releases that were placed in that channel.
- `GET /feed/v1/files/<sha256>` serves the file under the same rule.
- An `ETag` over the feed; `If-None-Match` answers `304`.
- The marketplace records per recipient and channel the last poll and what it
  offered — "offered and fetched", never "installed".

## 6. The package catalog's mirror mode

- The catalog declares a destination need `upstream` (kind `http`). The
  operator binds it with **bearer** authentication = the machine key; the key
  lives in the destination, never in the catalog's configuration or storage.
- Each poll fetches the feed through the destination and **follows no
  redirect**. For every version the catalog does not hold it downloads
  `files/<sha256>` through the destination, checks **size and SHA-256 against
  the feed** and **id and version against the manifest inside**, and only
  then takes it in with the catalog's own rules (never overwrite).
- `CATALOG_UPSTREAM_RELEASE`: `auto` releases on arrival (default), `hold`
  leaves it to the operator.
- A version in `withdrawn` that is released locally is **unreleased** with
  `auto`, the reason in the catalog's audit log; it is never deleted, and
  instances that run it are not touched. With `hold` it is only marked.
- Without a bound destination the catalog behaves exactly as before.

## 6a. The store front (0.2)

- **Search** covers id, title, summary, description and tags (full text,
  diacritics folded, prefix per word; a substring search where the database
  has no full-text index). **Facets:** type, category, tag, channel. A
  facet's counts take every OTHER chosen facet into account, and every count
  is made **after** the access rule (§3) -- a hidden asset changes no number.
- **Asset fields:** tags and categories (lowercase slugs), links (http(s)
  only), licence, publisher, an icon and up to 8 screenshots.
- **Description and release notes are Markdown.** Everything is escaped
  first; then a few forms get their tags. Raw HTML appears as text; a link
  that is not http(s), a fragment or a relative link becomes text.
- **Images:** PNG, JPEG, WebP only, recognised by their first bytes, at most
  5 MB; never SVG. An image is served with its fixed type, `nosniff`,
  `Content-Security-Policy: default-src 'none'; sandbox`, and only to a
  principal who may see an asset that carries it (`404` otherwise). A file
  no release and no image refers to any more is deleted.
- **Access requests:** a signed-in principal may ask for an asset it sees
  but cannot obtain, naming a channel and a note. One open request per
  principal and asset; asking again amends it. An operator grants (this
  creates the entitlement, noting the request) or rejects -- a rejection
  MUST carry an answer, which the principal sees on the detail page.
- Writing metadata and images: the asset's publishers and operators;
  visibility and free channels: operators only.

## 7. Security

- Nothing uploaded is executed or unpacked to disk.
- Downloads: `Content-Disposition: attachment`, `application/octet-stream`
  unless the type is on a short safe list, `X-Content-Type-Options: nosniff`.
- Cross-site POSTs are refused (`Origin` / `Sec-Fetch-Site`).
- No IP address is stored.

## 8. Conformance tests (described)

M1–M12 of RFC-0077 §15.4, measured on `oaap-test` on 2026-11-11 (RFC-0077
§15.6): check-in, idempotence and `409`, refusals, publisher rights, the three
states, entitlement × channel, mirror → store → install, update, yank →
unrelease with the instance untouched, a large package through the
destination proxy, `hold`, hidden assets.

## Deutsche Zusammenfassung

**0.2 (Schaufenster):** Suche über Name, Beschreibung und Schlagworte, auch
ohne Umlaute; Facetten zählen erst nach der Sichtbarkeitsregel. Beschreibung
und Notizen sind Markdown, aber nie aktives HTML. Bilder nur PNG/JPEG/WebP
nach Inhalt, kein SVG, und nur so sichtbar wie ihr Asset. Wer etwas sieht,
aber nicht bekommt, kann eine Freischaltung anfragen. Der Betreiber schaltet
frei, das erzeugt die Berechtigung, oder lehnt mit einer Antwort ab.

**0.1:**

Ein **Marketplace** verteilt digitale Assets. OAAP-Pakete sind ein Typ
davon. Releases sind unveränderlich und liegen unter ihrem SHA-256.
Kanäle (`stable`, `beta`) zeigen auf Releases. Ein Rückruf braucht einen
Grund. Für jede Person oder Maschine ist ein Asset *verborgen* (404),
*sichtbar, gesperrt* oder *beziehbar*. Die Regel steht in **einer**
Funktion, und gefiltert wird vor dem Zählen. Eingecheckt wird per API mit
einem Plattform-Schlüssel, nur mit einem Recht zum Veröffentlichen. Der
**Paketkatalog** eines Knotens folgt dem Feed über eine Destination mit
Bearer-Schlüssel. Er prüft Größe, Prüfsumme, Id und Version, bevor er etwas
aufnimmt, und gibt es frei (`auto`) oder wartet (`hold`). Zurückgerufenes
nimmt er aus der Freigabe, nie aus dem Speicher. Der Knoten selbst ändert
sich nicht.

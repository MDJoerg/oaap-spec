# RFC-0077: Marketplace — Digital Assets with Channels, Visibility and Entitlements, and a Catalog that Mirrors It

- **Status:** **Accepted (2026-11-11)** — D1–D5 decided by Jörg on 2026-11-10
  ("ich bin einverstanden" to the proposal in the conversation), D6–D12 on
  2026-11-11, each as recommended (§14). **Stage 1 built and measured on
  `oaap-test` (2026-11-11, §15.6):** marketplace 0.1.0, package catalog 0.2.0
  (mirror mode), spec `oaap.dist.marketplace` 0.1; M1–M12 green, O2 answered.
  **Stage 2 built (2026-11-11, §15.7):** marketplace 0.2.0, spec 0.2, live on
  `oaap-test` and in production on `oaapx01` (tenant `oaap-web`,
  `https://market.oaap-web.oaap.joomp.de/`); done when Jörg's browser test
  passes. **Completion of stage 2 designed (2026-11-12, §15.8), built and
  measured on `oaap-test` (§15.9):** marketplace 0.3.0, package catalog
  0.3.0, spec 0.3 -- the MVP for setup templates: landscapes and categories,
  type `oaap-profile`, texts in several languages, a secret gate, a digital
  four-eyes review, object page, share link + QR, the catalog follows a
  pasted link, `publish.py sync`, partner light; N1–N10 green. Not yet:
  Jörg's browser test, rollout to `oaapx01`, the real run (§15.5, oaapx01 →
  oaapx02) and stages 3–4.
- **Date:** 2026-11-10
- **Authors:** Jörg (the idea: a marketplace / download centre next to the
  package catalog; OAAP apps only one kind of asset; cards, details, images,
  downloads; public by default, visibility for users, machines, groups;
  partners and customers later; channels stable/beta; self-hostable with
  own asset types; external blob storage; web API, MCP, statistics; MVP =
  automated check-in after release, the multi-tenant node takes the current
  versions), Claude (facts read in RFC-0050, the package catalog and the
  node's catalog reader; design)
- **Depends on:** RFC-0050 (package catalog, store source `catalog:`),
  RFC-0012 (store list `0.2`), RFC-0019 (artifact deployment), RFC-0027
  (API keys), RFC-0040 (identity headers), RFC-0007 (visibility groups),
  RFC-0033 / `oaap.net.destinations` (outbound HTTP through the proxy),
  RFC-0068 (closed egress), RFC-0010 (public-route throttling)
- **Related, not decided here:** RFC-0073 (apps as MCP sources, stage 3),
  RFC-0045 (domain permissions, a later home for publisher rights),
  RFC-0057 (database per app), RFC-0049 (update policy on the recipient),
  RFC-0020 (promotion: same bytes), the video service idea (S3-capable
  storage decided before the product)
- **Replaces:** RFC-0050 §5 (stage 3, "supplying recipient nodes from the
  reference node"). The catalog keeps its local role; recipients, tokens per
  recipient and "supply to A, B" move into the marketplace (§2).
- **Idea store:** I-48

## Summary

A **marketplace app** distributes **digital assets** — OAAP app packages
are one asset type among others. Each asset has **releases** (immutable,
content-addressed files) and **channels** (`stable`, `beta`, …) that point
at releases. Whether someone **sees** an asset and whether they may **obtain**
it are two separate questions: an asset is *hidden*, *visible but locked*, or
*obtainable* for a given principal (person, machine, group). An
**entitlement** grants a principal an asset on one or more channels.

Publishers — a person, or an AI with a machine key — **check in** releases
through a web API, the same way the deploy hook takes a package today.
Recipients — usually the **package catalog** of a node — **pull** a feed
that lists exactly what they are entitled to, per channel.

The **node does not change.** The package catalog gains a **mirror mode**: it
fetches the feed through a destination, stores the packages in its own
`/data` with the checks it already makes, and releases them automatically
or holds them for the operator. The host keeps reading the catalog from its
storage (RFC-0050 §7). New work lives in two apps, not in a platform
release.

## 1. What exists today

- **Package catalog** (`oaap-apps/apps/package-catalog` 0.1.1, RFC-0050
  stages 1–2): the operator uploads ZIPs, releases a version, and the
  catalog writes `store.json` (`schema 0.2`, one entry per app: the highest
  released version with `package{zip, sha256, size}`). Only `admin`. It
  reads `oaap-app.yaml` from the ZIP and never unpacks or runs anything.
- **Store source `catalog:<instance>`** (`oaap-reference/platform/services/
  catalog_source.py`): the host reads `store.json` and the ZIPs straight
  from the instance's storage, validates each entry, checks size and
  SHA-256 on a copy it owns, compares id and version with the manifest
  inside. No network, no token.
- **RFC-0050 §5 (stage 3), not built:** recipients registered at the catalog
  with a token each, "supply to A, B", pull. §6.2 already foresaw that a
  local catalog may mirror a central one.
- **How packages travel today:** the ZIP is produced by whoever builds the
  app (for `hbvp`, the hbsha project's own AI), then a person uploads it in
  the catalog of each node (`CURRENT_STATE` 457: `hbvp 0.0.221` on oaapx02).
- **Platform pieces we reuse unchanged:** API keys answer `/verify` like a
  session and give the same headers (RFC-0027); identity headers
  `X-OAAP-User`, `X-OAAP-User-Id`, `X-OAAP-Roles`, `X-OAAP-Groups`,
  `X-OAAP-Display-Name`, `X-OAAP-Email` (RFC-0040, `oaap.core.identity`);
  a `public` route receives no authentication at all (`oaap.core.gateway`,
  RFC-0010 brake); an app reaches another host only through a bound
  destination, `OAAP_DESTINATION_<NEED>_URL`, the proxy adding the
  credential (`oaap.net.destinations` §2.3); an MCP door `mcp: {path}`
  (RFC-0073).

## 2. Two apps, two questions

| | Package catalog (exists) | Marketplace (new) |
|---|---|---|
| Question | What may be installed on **this node**? | Which assets exist, and **who gets which**? |
| Content | OAAP packages only | any asset type; `oaap-app` is one |
| Audience | the node's operator and tenant admins | the public, customers, partners, machines |
| Runs | on every node with tenants | once centrally, or wherever someone wants their own |
| Knows about | the node's store | principals, channels, entitlements — **not** nodes |

The marketplace never addresses a node. A node is a **recipient**: a machine
user of the marketplace's tenant with an API key, entitled to some assets.
The catalog never learns about partners, images or search.

```mermaid
flowchart LR
  P[Publisher: person or AI\nmachine key] -->|POST release| M[Marketplace]
  M -->|GET feed, machine key\nthrough a destination| C[Package catalog\nmirror mode]
  C -->|store.json in /data\nunchanged| H[Host / store page]
  H --> T[Tenant admins install / update]
  B[Browser] -->|public routes| M
```

## 3. Model

```text
AssetType   id, name, file rules, metadata fields, validator (built-in name)
Asset       id (slug), type, title, summary, description (Markdown),
            icon, screenshots[], tags[], categories[], links[],
            license, publisher, visibility, created_at
Release     asset, version, notes (Markdown), files[], created_at, by,
            yanked{at, by, reason}?
File        sha256 (the key), size, name, media type, role (primary | extra)
Channel     asset-independent name: stable, beta, … (configurable)
Placement   release × channel, placed_at, by        — "this release is in beta"
Principal   user id | group | anyone | signed-in
Visibility  per asset: listed (anyone | signed-in | principals) — see §5
Entitlement principal × asset × channels[], granted_by, granted_at,
            expires_at?, note
Event       download | feed poll | publish | place | yank | grant | revoke
```

Rules:

- **A release is immutable.** Same asset + version with the same bytes is
  idempotent (`200`, existing release); with different bytes it is refused
  (`409`). A version is never reused, not even after a yank.
- **Files are content-addressed.** The blob key is the SHA-256; two releases
  with the same file store it once.
- **A channel is a set of placements, not a copy.** "Promote beta to
  stable" places the same release in `stable` — the same bytes, as in
  RFC-0020. The channel's current release is the **highest non-yanked
  version placed in it** (ordering as the catalog's `version_key`: numeric,
  `1.2.10` after `1.2.9`, `1.0.0` after `1.0.0-rc1`).
- **Rollback = yank** (with a reason, kept in the event log). The channel
  then falls back to the next highest release. Already-installed instances
  are untouched; the recipient decides (§7.4).
- **History is always kept** (Jörg: optional in the UI). Stage 1 stores it;
  stage 2 shows it.

## 4. Asset types

- Stage 1 ships two **built-in** types:
  - `oaap-app`: exactly one primary file, a ZIP. Validator `oaap-manifest`:
    the same checks as the catalog's `zipinfo.py` (no `..`, no absolute
    paths, no links, a valid `oaap-app.yaml`, version `x.y.z[-pre]`), and
    **asset id = `app.id`, release version = `app.version`** from the
    manifest. Nothing is unpacked or run.
  - `file`: one or more files, extensions and size from configuration, no
    validator beyond size and name.
- Stage 4 makes types **configurable by the marketplace admin**: a list of
  metadata fields (text, Markdown, URL, number, select, tags), allowed
  extensions, maximum size, and a validator **chosen from the built-in
  list** (`none`, `oaap-manifest`, later e.g. `pdf`). **No uploaded code ever
  becomes a validator.** A self-hosted marketplace without OAAP apps simply
  never enables `oaap-app`.

## 5. Visibility and entitlement — seeing is not obtaining

For one principal and one asset there are three states:

| State | Listed and searchable | Detail page | Download / in the feed |
|---|---|---|---|
| hidden | no | `404` | no |
| visible, locked | yes, marked "freischalten" | yes | no — "request access" |
| obtainable | yes | yes | yes, on the entitled channels |

- **Visibility** (per asset): `anyone` | `signed-in` | a list of principals
  (user ids, groups). Default for a new asset: see D11.
- **Obtainable** if the asset is **free** for its visibility audience
  (`free: true` per asset and channel set, e.g. "stable is free, beta is
  not") **or** the principal holds an **entitlement** covering the channel.
- **Groups** are the `X-OAAP-Groups` of the marketplace's own tenant
  (RFC-0007 tags, or Keycloak groups when the tenant uses the IdP). A
  machine user can be in groups like a person.
- **Every read path filters before it counts or ranks** — search, card
  lists, facets, MCP, statistics shown to non-admins. A hidden asset must not
  even change a number.
- **Request access** (stage 2): a signed-in principal asks; the request
  lands in the admin's list (later: a Vorgang, RFC-0061); granting creates
  an entitlement.
- **Partners** (stage 4): a partner is a group with a delegation: its
  members may grant and revoke entitlements for named assets, but only to
  principals in their customer groups. The marketplace admin defines the
  delegation; the partner never widens visibility.

## 6. Publishing — the check-in

All under `/api/v1/` (non-public route: session or API key).

| Method and path | Does |
|---|---|
| `POST /api/v1/releases` | multipart: `file` (primary), optional `extra` files, `type` (default `oaap-app`), `notes`, `channels` (comma list). For `oaap-app` the asset is created on first check-in from the manifest if the caller may publish into that id. Answer: asset, version, sha256, placements. |
| `POST /api/v1/assets/{id}/releases/{v}/channels/{ch}` | place a release in a channel |
| `DELETE /api/v1/assets/{id}/releases/{v}/channels/{ch}` | remove a placement |
| `POST /api/v1/assets/{id}/releases/{v}/yank` | yank, `reason` required |
| `PUT /api/v1/assets/{id}` | metadata (title, summary, description, tags, links, visibility, free) |
| `POST /api/v1/assets/{id}/images` | icon or screenshot (raster only, §12) |

- **Who may publish:** a publisher right per asset id or id prefix
  (`hbvp`, `oaap-*`), held by user ids or groups, granted by the
  marketplace admin. Stage 1 keeps this in the app (D8). The right may be
  limited to channels (e.g. an AI key may place into `beta` and `stable`,
  a trainee only into `beta`).
- **The "after release" rule stays with the human, upstream.** Jörg releases
  on oaap-test (test instance, promotion); the check-in that follows is
  automated. The marketplace does not try to judge quality. Whoever wants a
  second gate publishes into `beta` and places into `stable` by hand.
- **A small client** `oaap-apps/apps/marketplace/tools/publish.py`
  (stdlib only) takes `--url`, `--key-file` (never the key on the command
  line), the ZIP and `--channels`, and prints the answer. This is what an
  AI or a CI job calls.

## 7. The feed and the catalog's mirror mode

### 7.1 Feed

`GET /feed/v1/oaap-apps?channel=stable` (non-public route; the caller is a
machine user via API key):

```json
{
  "schema": "oaap.marketplace.feed/0.1",
  "name": "OAAP Marketplace",
  "channel": "stable",
  "generated_at": "2026-11-10T12:00:00Z",
  "apps": [
    {"id": "hbvp", "name": "Handball-Vereinsportal", "version": "0.0.221",
     "released": "2026-11-09", "summary": "…", "description": "…",
     "package": {"url": "files/3f2a…e9", "sha256": "3f2a…e9", "size": 1834221}}
  ],
  "withdrawn": [{"id": "hbvp", "version": "0.0.220", "reason": "…"}]
}
```

- One entry per **obtainable** OAAP app: the channel's current release.
  The fields mirror `store.json` (RFC-0012 `0.2`) so the catalog maps them
  one to one; `package.url` is relative to the feed.
- `withdrawn` lists yanked versions the caller was offered before (so the
  mirror can react, §7.4).
- `GET /feed/v1/files/{sha256}` serves the file to the same caller, again
  only if obtainable. `ETag` = sha256; `If-None-Match` on the feed itself
  makes polling cheap.
- The **node's store format does not change.** The feed is the marketplace's
  own format; only the catalog reads it.
- A generic `GET /feed/v1/assets?type=…&channel=…` for other asset types is
  stage 3.

### 7.2 Mirror mode in the package catalog (0.2.0)

- Manifest gains a destination need:
  `destinations: [{name: upstream, kind: http, purpose: "Marketplace feed (RFC-0077)"}]`.
  The operator binds it to a destination with **bearer auth = the machine
  key**; the key lives in the destination, never in the catalog's
  configuration or storage (`oaap.net.destinations`).
- New configuration:

  | Key | Meaning | Default |
  |---|---|---|
  | `CATALOG_UPSTREAM_CHANNEL` | channel to follow | `stable` |
  | `CATALOG_UPSTREAM_RELEASE` | `auto` = release on arrival; `hold` = operator releases | `auto` (D3) |
  | `CATALOG_UPSTREAM_INTERVAL_MIN` | polling interval | `15` |

- Without a bound `upstream` the catalog behaves exactly as 0.1.1.
- Each poll: `GET feed` (conditional), for every entry whose version the
  catalog does not hold: download to its `tmp`, check size and SHA-256
  against the feed, then hand it to the **existing `add()`** (all current
  rules apply: manifest, paths, version, id) — `by: "upstream"`, note
  `"from <feed name>, channel <ch>"`. With `auto` it then calls
  `set_released(…, True, "upstream")`, which rewrites `store.json`.
- The catalog page shows the mirror: feed name, channel, last poll, last
  error, versions taken; a button "Jetzt abrufen" (admin only).
- Uploading by hand keeps working beside the mirror. A version that exists
  locally is never overwritten by the mirror (same rule as today).

### 7.3 Why the catalog in between (D2)

1. No platform release: the host already reads the catalog from storage.
2. The operator keeps a gate (`hold`, RFC-0050 §6.3).
3. Pull, not push: the marketplace holds no access to nodes and learns
   "node X fetched version Y at time T" without telemetry.
4. Closed tenants (RFC-0068) are served: the destination is the sanctioned
   door out.

### 7.4 Withdrawn upstream

Proposed (D7): with `auto`, a withdrawn version that is released locally is
**unreleased** with the reason in the catalog's audit log; instances that
run it are not touched, and the store page then offers the next highest
released version. With `hold`, the catalog only marks it. Deleting stays a
human act.

## 8. The web interface

Routes in the manifest:

| Path | Route | For |
|---|---|---|
| `/`, `/assets/*`, `/static/*`, `/img/*` | `public` | browsing what `anyone` may see; public downloads under `/d/*` |
| `/my/*` | `user` | the same pages signed in: more visible, entitlements, requests |
| `/api/public/v1/*` | `public` | read-only JSON of what `anyone` may see |
| `/api/v1/*` | `user` | search, details, downloads, publishing (§6), keys welcome |
| `/feed/v1/*` | `user` | recipients (§7) |
| `/admin/*` | `admin` | types, channels, publishers, visibility, entitlements, requests, statistics |
| `/mcp` | MCP door (RFC-0073) | stage 3 |

A public route carries no identity, so "signed-in view" is a second path
prefix serving the same templates with the headers — a link "Anmelden" goes
from `/x` to `/my/x`.

- **Search page:** a search field, facets (type, category, tag, channel),
  cards with icon, title, summary, publisher, latest version, a badge
  (free / locked / entitled / beta). Server-side search in SQLite FTS5.
- **Detail page:** header with icon and actions (Download, Request access),
  screenshot gallery, description in Markdown (escaped first, a few marks
  after — as the chat's `markdown.js`), facts (version per channel, size,
  licence, links, publisher), release history with notes (stage 2).
- Design per the OAAP design guidelines (blue tones, floorplans: list
  report = search, object page = detail), tablet first, dark mode.

## 9. Storage

- A small interface `BlobStore`: `put(stream) -> sha256, size`,
  `open(sha256)`, `stat(sha256)`, `delete(sha256)` (only when no release and
  no image references it).
- Stage 1: **local** in `/data/blobs/ab/cd/<sha256>`; metadata in SQLite
  `/data/market.db` (WAL). Both in the instance's storage, so the node's
  backup carries them.
- Stage 3: **S3-compatible** behind the same interface, chosen per
  instance. Open question O1: S3 requests are signed (SigV4) over the host
  name, so they cannot simply go through the destination proxy, which
  changes the host and adds its own credential. Options: a `tcp`-style
  destination that hands the app endpoint and keys; or presigned URLs made
  by the app and fetched by the client directly. To be measured before
  stage 3 is designed in detail. **Data in S3 is not in the node's
  backup**; the admin page says so.
- Downloads go through the app in stages 1–2 (statistics, entitlement
  check on every request). Presigned direct links are a stage-3 option for
  large public files.

## 10. MCP (stage 3)

Through RFC-0073, read first: `search_assets`, `get_asset`,
`list_releases`, `my_entitlements`. Writing tools (`place_release`,
`grant_entitlement`) only later and only with the chat's confirmation
(RFC-0074/0075). Every tool applies §5 before it answers.

## 11. Statistics

- Downloads per asset, version, channel, day; per principal for admins and
  (stage 4) for the partner of that principal. **No IP addresses are
  stored**; anonymous downloads count as "anonymous".
- Recipients: last feed poll, versions offered, files fetched. This is
  "**offered and fetched**", not "installed" — the page says so.
- Publishers see their own assets' numbers.

## 12. Security

- Nothing uploaded is ever executed, unpacked to disk or rendered as
  active content. ZIPs are inspected in memory (as `zipinfo.py`).
- **Images:** PNG, JPEG, WebP only (magic bytes checked, not the name), size
  limit, served with `X-Content-Type-Options: nosniff` and a strict CSP.
  **No SVG.**
- **Downloads:** `Content-Disposition: attachment`, `application/octet-stream`
  unless the type is on a short safe list.
- **Hidden means `404`**, never `403`.
- Keys are platform API keys (D10); the app never sees a secret and logs
  no query strings (as the catalog: no request lines).
- Cross-site POSTs refused as in the catalog (`Origin`/`Sec-Fetch-Site`).
- **Trust of a package:** SHA-256 and TLS prove the file is what the
  marketplace offers, not who made it. That is enough while the marketplace
  and the publisher are the same operator. With third-party publishers,
  **signatures** (stage 4: publisher key, Ed25519 over the file's SHA-256,
  verified by the catalog and later by the node) become necessary.
- Public routes are throttled by the platform (RFC-0010).

## 13. Stages

| Stage | Content | Done when |
|---|---|---|
| **1 — MVP** | marketplace 0.1: SQLite, local blobs, types `oaap-app` + `file`, publish API + `publish.py`, channels `stable`/`beta`, yank, visibility + entitlements (user, group), feed + files, a plain admin page; **package catalog 0.2.0 mirror mode** | M1–M12 (§15.4) green on oaap-test; then a real run: release on oaap-test → check-in → oaapx02's catalog has it → a tenant admin updates |
| 2 — Store front | search with cards and facets, detail page with gallery, release history, the three states visible, request access, images | Jörg's browser test |
| 3 — Services | S3 (after O1 is measured), MCP door, statistics pages, generic feed | measured per piece |
| 4 — Partners | partner delegation, configurable asset types, signatures | per decision |

## 14. Decisions

Decided by Jörg on 2026-11-10:

- **D1 — An app of its own, generic assets.** Not an extension of the
  package catalog; `oaap-app` is one asset type.
- **D2 — The catalog stays in between.** Nodes take packages through the
  package catalog in mirror mode; the host is unchanged.
- **D3 — Mirrored versions are released automatically by default,**
  configurable per catalog (`auto` | `hold`).
- **D4 — No payment or licensing in this RFC.** The model leaves room (an
  entitlement can later carry an origin such as an order).
- **D5 — Name: Marketplace**, app id `marketplace`.

Decided by Jörg on 2026-11-11, each as recommended:

- **D6 — The productive marketplace runs on oaapx01** (public name, TLS,
  off-site backup), in Jörg's own tenant; oaap-test stays the measuring
  ground.
- **D7 — Withdrawn upstream → unreleased locally with `auto`** (§7.4),
  never deleted, instances untouched.
- **D8 — Publisher rights in the app for stage 1;** moving them to
  RFC-0045 (domain permissions) when that has a second user.
- **D9 — SQLite in the instance's storage;** RFC-0057 only when a measured
  need shows up.
- **D10 — Platform API keys of machine users for recipients and AI
  publishers;** no own token scheme in the app. Rotation and revocation
  happen in the portal ("Zugänge").
- **D11 — A new asset starts "visible, locked"** (listed for `anyone`,
  obtainable only with an entitlement). Free download is an explicit
  switch per asset. Reason: an OAAP package is code; making it freely
  downloadable should be a decision, not a default.
- **D12 — Channels are global names** (`stable`, `beta` preset, more
  configurable), not per asset.

Open questions:

- **O1** — S3 through the destination proxy or with handed-over
  credentials (§9).
- **O2** — Does the destination proxy carry 256 MB downloads within its
  limits and timeouts? Measured in stage 1 (M10).
- **O3** — Should the catalog report back what was *installed* (not only
  fetched)? Not now; it would be telemetry from the node and needs its own
  decision.

## 15. Implementation plan

### 15.1 Repositories and files

- `oaap-apps/apps/marketplace/` (new): `oaap-app.yaml` (manifest 0.13,
  routes §8, storage `data`, config below, health `/healthz`),
  `Dockerfile` (python:3.12-slim, stdlib only as far as possible),
  `app.py` (HTTP server and routing, as the catalog), `db.py` (schema,
  migrations by `user_version`), `blobs.py` (`BlobStore`, local),
  `access.py` (§5 in **one** function `can(principal, asset, action,
  channel)` — every path calls it, see "Zwei Wege, eine Regel"),
  `zipinfo.py` (copied from the catalog, same tests), `feed.py`,
  `publish.py` handlers, `templates/`, `static/`, `tools/publish.py`,
  `test_marketplace.py`, `README.md` (German).
- `oaap-apps/apps/package-catalog/`: 0.2.0 — `upstream.py` (poll, download,
  verify, hand to `add()`), the destination need and three config keys,
  status block on the page, tests with a fake feed served by a local
  `http.server`.
- Store list of `oaap-apps`: both entries (version in three places, checked
  by `check-store.py`).
- `oaap-spec/spec/oaap.dist.marketplace.md` 0.1 (new capability spec: model,
  §5 rules, API, feed format) — written with stage 1, from this RFC.
- `oaap-spec/spec/oaap.apps.runtime.md`: one paragraph at the catalog
  section (mirror mode), no change to the host.
- `oaap-lab/marketplace-probe/`: the measuring script (§15.4).

### 15.2 Configuration of the marketplace

| Key | Meaning | Default |
|---|---|---|
| `MARKET_NAME` | shown in the header and the feed | `Marketplace` |
| `MARKET_MAX_FILE_MB` | largest file | `256` |
| `MARKET_CHANNELS` | channel names | `stable,beta` |
| `MARKET_TYPES` | enabled built-in types | `oaap-app,file` |
| `MARKET_FILE_EXTENSIONS` | allowed for type `file` | `zip,pdf,png,jpg,txt,md` |

### 15.3 SQLite schema (stage 1)

```sql
asset(id TEXT PK, type, title, summary, description, visibility TEXT,  -- JSON
      free_channels TEXT, created_at, created_by)
release(asset, version, notes, created_at, created_by,
        yanked_at, yanked_by, yank_reason, PRIMARY KEY(asset, version))
file(sha256 PK, size, media_type)
release_file(asset, version, sha256, name, role)
placement(asset, version, channel, placed_at, placed_by,
          PRIMARY KEY(asset, version, channel))
entitlement(id PK, principal_kind, principal, asset, channels, granted_by,
            granted_at, expires_at, note)
publisher(id PK, principal_kind, principal, asset_pattern, channels)
event(id PK, at, kind, asset, version, channel, principal, detail)
```

### 15.4 Measurements for stage 1 (oaap-test)

Setup: marketplace instance `market-test` in tenant A; a machine user
`node-b` with an API key; a package catalog in tenant B with destination
`upstream` → `market-test`, bearer = that key; a publisher machine user
`ci` with an API key.

- **M1** `publish.py` with `ci` checks in `probe-app 0.1.0` into `beta`:
  `201`, sha256 matches the local file.
- **M2** Same file again: `200`, same release; changed bytes, same version:
  `409`.
- **M3** A ZIP with `../x`, a link, no manifest, version `1.0`: each refused
  with a sentence, nothing stored.
- **M4** `ci` without a publisher right for `other-*`: `403`.
- **M5** `node-b` without entitlement: the feed omits the app; the detail
  page as `anyone` shows it "locked"; the file URL answers `404`.
- **M6** Entitlement `node-b` × `probe-app` × `stable`; release only in
  `beta`: feed empty. Place in `stable`: feed lists `0.1.0`.
- **M7** Mirror: within one interval (or "Jetzt abrufen") the catalog holds
  `0.1.0`, released (`auto`), `store.json` lists it; the store page of
  tenant B offers it after the state refresh. Install works (host checks
  sha256 on its copy).
- **M8** Check in `0.1.1` into `stable`: the store page offers
  "Update to 0.1.1"; the update runs.
- **M9** Yank `0.1.1` with a reason: feed lists it under `withdrawn`; the
  catalog unreleases it (`auto`), audit line names the reason; the running
  instance stays on `0.1.1`; the store page offers nothing higher than
  `0.1.0`.
- **M10** A 200 MB package through the destination proxy (O2): time, memory
  of the catalog, no partial file left on failure.
- **M11** `hold`: a new version arrives unreleased; the operator releases it
  by hand.
- **M12** Hidden asset: `anyone` gets `404` on detail and download, the
  search count does not change, `/api/public/v1` does not list it.

### 15.5 After stage 1 — the real run

Marketplace on oaapx01 (D6), machine user for oaapx02, destination in
oaapx02's catalog. The next release of `hbvp` goes the new way: released on
the development side, checked in by `publish.py`, mirrored into oaapx02's
catalog, updated by a tenant admin of a club. Manual uploads on oaapx02 then
stop for that app.

### 15.6 Stage 1 as built (2026-11-11)

`oaap-apps/apps/marketplace` 0.1.0 (`app.py`, `db.py`, `access.py` -- the one
rule --, `blobs.py`, `zipinfo.py`/`multipart.py` copied from the catalog,
`tools/publish.py`, `test_marketplace.py` 46/46) and
`oaap-apps/apps/package-catalog` 0.2.0 (`upstream.py`, `test_upstream.py`
19/19 against the real marketplace in-process, old tests green). Where the
build sharpened the text:

- **Principals are user names** (`X-OAAP-User`) and groups (`X-OAAP-Groups`)
  in stage 1, not user ids: an operator types a name into the admin page. A
  machine user's name does not change; RFC-0040's id becomes the key when a
  partner UI (stage 4) picks principals from a list.
- **A yanked release is never placed again** (`409` with a sentence), also
  not by checking the same file in again.
- **The mirror checks id and version against the manifest inside the ZIP
  before `add()`**, not after: otherwise a package that is something else
  than the feed claims would land in the catalog under its own name. A
  `package.url` that is not `files/<sha256>` is refused (it would lead past
  the destination).
- `/admin` answers `404` to a non-operator, like a hidden asset.
- Search in stage 1 is a substring over id, title and summary; FTS5 comes
  with the store front (stage 2).

**Measured on `oaap-test` (2026-11-11)** with machine users `m77-ci`
(publisher right `probe-*`) and `m77-node-b` (keys limited to the instance,
7 days), marketplace `market-test` in the default tenant, catalog
`katalog-probe` in tenant `zzz-probe`, destination `market-upstream` →
`http://10.10.10.96:8134` (the node's own LAN address and the instance's
port: the node cannot reach its own public name, and the gateway accepted
the call to its own port), bearer = `m77-node-b`'s key:

- **M1** `publish.py` → `201`, SHA-256 equal, placed in `beta`. **M2** again
  `200`/not created; other bytes `409`. **M3** `../x`, no manifest, `1.0`
  each refused with a sentence, nothing stored. **M4** `other-app` → `403`.
- **M5** feed empty, public detail page "freischalten", file `404` both ways.
  **M6** entitlement for `stable` with the release in `beta` only → feed
  empty; placed in `stable` → feed lists `0.1.0`.
- **M7** "Jetzt abrufen" in the catalog: fetched through the destination,
  `0.1.0` released (`auto`); `oaap store add-catalog`; installed from the
  portal's store as `server_admin` → instance `marktprobe` 0.1.0 runs.
- **M8** `0.1.1` into `stable` → mirrored and released → portal update →
  the instance runs `0.1.1`.
- **M9** yank `0.1.1` ("Messung M9") → feed lists it under `withdrawn`;
  the catalog unreleased it (`withdraw` by `upstream`, reason in the audit
  log, version kept), `store.json` offers `0.1.0`, the instance stays on
  `0.1.1`.
- **M10 / O2** a 209,716,015-byte package: check-in from a laptop in 14 s,
  mirrored through the destination proxy in 3 s, SHA-256 equal, no file left
  in the catalog's `tmp`, catalog at 23 MiB memory (streamed). *Not*
  measured live: a download broken off half way (covered by the unit test's
  clean-up path only).
- **M11** `CATALOG_UPSTREAM_RELEASE=hold` → `0.1.2` arrived unreleased;
  released by hand → `store.json` lists `0.1.2`.
- **M12** visibility `principals` → public list count `0`, detail `404`, the
  entitled machine keeps its feed; back to `anyone` → count `1`.

**Left on `oaap-test` for stage 2:** `market-test`, `katalog-probe`,
`marktprobe`, the two machine users and their keys (expire 2026-11-18), the
catalog store source.

### 15.7 Stage 2 as built (2026-11-11, marketplace 0.2.0)

New modules `views.py` (store front, detail, admin), `render.py` (a copy of
`help`'s Markdown renderer with its own `slug()`), `images.py` (magic bytes);
`db.py` schema version 2 (asset fields, `image`, `access_request`, an FTS5
table `asset_fts` with `unicode61 remove_diacritics 2`, fallback to a
substring search). The JSON list `/api/v1/assets` uses the same search as
the page. Tests: `test_storefront.py` 35/35, stage 1's `test_marketplace.py`
46/46 unchanged, the catalog's `test_upstream.py` 19/19.

Where the build sharpened the text:

- Facet counts take the other chosen facets into account (the usual
  "drill-down" counts) -- and are made after `can_see`, so the anonymous
  count for `tag=verein` was 1 with a second, hidden asset carrying the tag.
- An image is served with `Content-Security-Policy: default-src 'none';
  sandbox` in addition to `nosniff`, and its file is deleted once nothing
  refers to it.
- A rejected request needs an answer; the person sees it on the detail page.
  Asking again after a rejection opens a new request.
- Badges: *frei* (free channel), *berechtigt* (entitlement), *Betreiber*,
  *freischalten* (locked), and the channel name when the only current
  release is outside the first channel (e.g. *beta*).

**Measured on `oaap-test`:** upgrade 0.1.0 → 0.2.0 kept every stage-1
release, channel and entitlement (migration to schema 2); metadata and a PNG
icon by the publisher's machine key, SVG refused (`400`), public detail page
with Markdown and the `<script>` escaped, icon served `image/png` + `nosniff`,
search "messung" and facet `tag=probe` find the asset, a machine user's
access request appears in `/admin`, the rejection's answer appears on its
detail page; the catalog's mirror still polls against 0.2.0.

**Rolled out on `oaapx01`:** tenant `oaap-web` (Jörg 2026-11-11, first
administrator `oaap-web-admin`, credentials in `test/.env`), instance
`market` 0.2.0 (`MARKET_NAME` "OAAP Marketplace"); three own packages
checked in through the API with that administrator's session into `stable`,
made free, with descriptions from their READMEs: `help` 0.3.0,
`package-catalog` 0.2.0, `marketplace` 0.2.0. Anonymous download verified
(size and SHA-256 equal). The tenant also holds the central `help` (§ RFC-0078).

### 15.8 Completing stage 2 — the MVP for setup templates (design, 2026-11-12)

Jörg on 2026-11-12, after looking at the Microsoft Store and Amazon pages
together: business users are the audience; the marketplace carries mostly
**digital content** — OAAP setup templates (tenant profiles, RFC-0055),
BDT sample projects, apps. His MVP: **setup templates checked in and
maintained automatically, versioned, with texts in several languages and
images, without ever leaking a secret, and with a fast review — four eyes,
but digital: a second AI checks, only escalations reach a human.** Decided
in the conversation: landscapes are configurable, only `oaap` is fixed; an
asset may be in several categories; a `default` landscape holds
cross-cutting categories; UI language from the browser, switchable;
operator settings limited to accent colour, logo and the start page rows;
sharing = one link plus a QR code, and the package catalog learns to take
that link (§15.8.7). Everything not listed here goes to a follow-up RFC
(§15.8.10).

#### 15.8.1 Landscapes and categories

```text
Landscape  id (slug), sort, logo (image sha), texts {lang: {title, description}},
           fixed (bool)                 — "oaap" is created by the schema, fixed
Category   id (slug), landscape (id | "default"), sort, logo, texts {…}
Asset      + landscapes[] (ids), categories[] (ids)   — both many-to-many
```

- `oaap` is created at schema migration and cannot be deleted or renamed;
  further landscapes (e.g. `bdt`) and all categories are configured by the
  marketplace admin in `/admin/taxonomy`.
- A category of the landscape `default` is **cross-cutting**: it is offered
  under every landscape (e.g. "Templates", "Documentation").
- Landscape and category are **facets**; the category facet shows the
  categories of the chosen landscape plus the `default` ones. The start page
  shows landscape tiles with logo, title and description.
- Migration: free category slugs from stage 2 become categories of the
  landscape `default` with their slug as title — nothing is lost.
- Assigning an unknown landscape or category is refused (`400`); a
  publisher may assign, only the admin defines.

#### 15.8.2 Content type and the new asset type `oaap-profile`

- A third built-in asset type **`oaap-profile`** — a setup template:
  exactly one primary file, JSON, at most 256 KB. Validator
  `oaap-profile`: valid UTF-8 JSON, `profile == "oaap.tenant-profile/1"`,
  `id` an asset id, `version` `x.y.z[-pre]` (required here, optional on the
  node), `title` present, `steps` a non-empty list. **Asset id = profile
  `id`, release version = profile `version`** — as `oaap-app` takes them
  from the manifest. The node checks the profile again on upload (RFC-0079);
  the marketplace's check is a gate, not the authority.
- A facet **Content** ("Inhalt") is derived, not stored: `OAAP app`,
  `Setup template`, and for type `file` the kind of its primary file
  (`PDF`, `JSON`, `Image`, `Text`, `Archive`).

#### 15.8.3 Texts in several languages

- **English is the base language** (`MARKET_DEFAULT_LANG`, default `en`).
  Title, summary, description and release notes are stored per language:
  `asset.texts = {lang: {title, summary, description}}`,
  `release.notes_i18n = {lang: text}`; landscapes and categories alike.
- Display: the asked language → `en` → the first language present, and a
  small hint "only in …" when it fell back. The asked language comes from
  `?lang=` (remembered in a cookie `market_lang`, no identity in it), else
  from `Accept-Language`. The UI's own strings exist in `en` and `de`.
- Search indexes all languages of an asset.
- Migration: stage-2 texts were written in German; they move to
  `texts.de`, `en` stays empty until written (the hint shows it).
- A check-in may carry any number of languages; translation by machine is
  out of scope (§15.8.10).

#### 15.8.4 No secret leaves through the marketplace — `secretguard.py`

Every check-in and every listing change passes a **synchronous gate**
before anything is stored. A finding refuses with `422`, names **where**
(field, JSON path, ZIP member) and **which rule**, and **never echoes the
value**; the event log records rule and place only.

| Rule | Applies to |
|---|---|
| Secret-file names (the categories `env`, `vcs`, `keys`, `cloud` of RFC-0084's `guard.CATEGORIES`, copied; a test compares them with the platform's list when the repository is beside) | members of an `oaap-app` ZIP, file names of type `file` |
| Content patterns: PEM private key, OAAP API key `oaapk_…`, AWS access key, GitHub / GitLab / Slack tokens, `sk-…` API keys, JWT, URL with user:password, `aws_secret_access_key`, `.npmrc` auth token | every text field (all languages, notes, links), every string in a profile, text members of a ZIP (≤ 1 MB each) |
| Profile: a parameter of kind `secret`; an `app.config` step whose key looks like a secret (`PASSWORD`, `SECRET`, `TOKEN`, `PRIVATE`, `API_KEY`, `CREDENTIAL`, `…_KEY`) with a **literal** `value` — allowed are `generate: true` (RFC-0079), a pure `{param}` placeholder, or empty | `oaap-profile` |
| Image metadata: EXIF, XMP, IPTC, PNG text chunks and WebP EXIF/XMP are **removed** before the image is stored (a camera's GPS position or a user name in a screenshot's metadata is a leak too); the SHA-256 is taken after stripping | every image |

The gate is pattern-based and therefore incomplete; the review (§15.8.5)
is the second pair of eyes, and the reviewer is told explicitly to look for
personal data and internal names in texts and screenshots.

#### 15.8.5 Review — four eyes, digital first

Switched on per marketplace: `MARKET_REVIEW` = `off` (default, stage-1
behaviour) | `on`.

```text
Review  id, kind (release | listing), asset, version?, created_at, created_by,
        state (open | approved | rejected | escalated), precheck {…},
        decided_by, decided_at, decided_as (reviewer | admin), summary,
        findings [{severity: info|warn|block, text}]
Reviewer principal (user | group) — granted by the admin
```

- **Release review (gate).** With `on`, a new release starts `pending`:
  its placements exist but do not count — the channel's current release is
  the highest **approved** non-yanked version; the feed, downloads and the
  public page do not show it. The publisher and reviewers see it as
  "in review" on the detail page.
- **Listing review (afterwards).** A change of texts, images, tags or
  categories by a non-admin publisher is visible at once and opens a
  `listing` case; the reviewer approves or escalates. An admin's own edit in
  the browser opens no case (it is already a human).
- **Four eyes:** the reviewer must not be the case's author (`403`).
  Verdicts: `approve` → the release counts; `reject` → it never counts, the
  publisher sees the findings, the fix is a new version; `escalate` → an
  admin decides in `/admin/reviews`. An admin deciding a case they authored
  is allowed and recorded as such (`decided_as: admin`, "own release").
- **Escalation by time:** a case open longer than
  `MARKET_REVIEW_ESCALATE_HOURS` (default 24) is shown to admins as
  escalated — computed when read, no timer.
- **API for the reviewing AI** (a machine user with the reviewer right,
  platform API key, D10):
  `GET /api/v1/reviews?state=open` (cases with texts in all languages,
  image URLs, file links and the gate's result — a reviewer may fetch a
  pending release's files), `POST /api/v1/reviews/{id}` with
  `{verdict, summary, findings}`.
- **Reference reviewer `tools/review.py`** (standard library): fetches open
  cases, repeats the deterministic checks, and — when given an
  OpenAI-compatible chat endpoint (e.g. the AI gateway, RFC-0064) — asks
  the model for a verdict against a fixed checklist (secrets and personal
  data, misleading claims, missing English text, steps that install from
  unknown sources, screenshots that show internal data). **Without a model
  it never approves; it escalates.** It approves only when the model says
  `approve` and no finding is `block`. The marketplace never calls a model
  itself (no outbound door needed).

#### 15.8.6 Detail page as an object page, start page, operator settings

- **Header (always visible):** icon, title, publisher, landscape and
  categories, badges (free / locked / entitled / beta / in review), the one
  main action (Download · Request access · Sign in), **Share**, summary.
  Directly below: the **gallery** (large, horizontally scrollable).
- **Sections as tabs** (anchors, work without script): *Overview*
  (description, links), *Versions* (per channel, history with notes),
  *Technical details* (id, type, file names, sizes, SHA-256, media type,
  licence, the share snippets of §15.8.7). Technical facts live in the last
  tab, not on the first screen.
- **Start page** without search or filter: a *featured* strip (assets the
  admin marks `featured`, first screenshot as banner), landscape tiles,
  rows *New* (latest approved release) and *Most downloaded* (downloads of
  the last 90 days; the catalogs' feed fetches do not count; computed after
  `can_see`). With a search or filter: the existing result list.
- **Operator settings** (`/admin/settings`, stored in the database):
  accent colour, logo (image, as §15.8.4), which start page rows are shown
  and in which order, default language for the UI.
- Business tone: no age ratings; the badges say what a business user asks
  (free, locked, in review, the content type).

#### 15.8.7 Share: one link, a QR code — and the catalog takes the link

- **One link for everything:** the canonical address of the detail page,
  `https://<market>/assets/<id>` (optionally `?channel=beta`). "Share"
  offers *copy link* and a **QR code** of the same link (SVG generated by
  the app with `segno`, pinned; never an uploaded SVG). The link opens the
  detail page for a human.
- **Package catalog 0.3 — "Add from clipboard":** the operator pastes the
  link; the catalog parses host, asset id and channel, **checks that the
  host is the target of its bound `upstream` destination**, and puts the
  id on its **follow list**. It never calls the pasted address itself — the
  link is a name, the destination is the only door (RFC-0068). An unknown
  host is answered with "this marketplace is not connected here" and the
  operator's step (bind `upstream`).
- New catalog configuration `CATALOG_UPSTREAM_SCOPE` = `all` (default,
  0.2 behaviour: every obtainable app) | `followed` (only the follow list).
  Following an id the feed does not offer shows "not obtainable for this
  node (yet)" — e.g. before the partner grants access.
- For a setup template, the *Technical details* tab offers the download
  link; the node takes it through the existing profile upload (RFC-0079). A
  pull of profiles by the node is the generic feed of stage 3.

#### 15.8.8 Automated check-in and maintenance — `publish.py sync`

A folder describes an asset completely; `publish.py sync <folder>` makes
the marketplace match it, idempotently:

```text
my-template/
  market.json        {"asset": "handballverein", "type": "oaap-profile",
                      "file": "handballverein.json", "channels": ["beta"],
                      "landscapes": ["oaap"], "categories": ["setup-templates"],
                      "tags": ["handball", "verein"], "license": "…", "links": […],
                      "texts": {"en": {"title": "…", "summary": "…",
                                       "description_file": "README.en.md"},
                                "de": {…}},
                      "notes": {"en": "…", "de": "…"},
                      "images": {"icon": "icon.png", "screenshots": ["1.png", "2.png"]}}
  handballverein.json, README.en.md, README.de.md, icon.png, 1.png, 2.png
```

- Release: checked in; the same bytes are `200` (nothing new), a changed
  file with the same version is `409` (raise the version).
- Listing: texts, tags, categories, links set with one `PUT`; images
  uploaded (content-addressed, so unchanged images change nothing) and
  images no longer listed removed. The answer lists what changed.
- The gate (§15.8.4) applies to all of it; a finding stops the sync before
  anything is written for that asset.

#### 15.8.9 Partner light — publishers answer for their own assets

The smallest piece of stage 4 that the BDT premium templates and the
handball portal's "get to know, then agree" need:

- A principal who may publish into an asset (§6) may, **for that asset
  only**, see and answer its access requests and grant or revoke
  entitlements (user or group, the channels it may publish into), in
  `/my/manage`. Visibility stays the admin's (never widened by a partner,
  §5).
- An answer may carry a link (e.g. an invitation link of RFC-0055 stage 4
  for a cloud tenant); it is shown only to the requester.
- Requesters need an account in the marketplace's tenant; signing in from
  other tenants is a later question (follow-up RFC).

#### 15.8.10 Not in this MVP — follow-up RFC "marketplace as a platform"

Partner tiers (small / medium / XL) with menu and API rights; campaigns,
"app of the week" chosen automatically, sponsored placement (always
labelled "sponsored", never counted in rankings); coupon codes as
entitlements with an origin (D4); security advisories per asset and
version range (pattern: the node's `advisories.py`, RFC-0070); update
search for foreign sources; asset types *reference* (only the source of a
partner), *recipe* (an app from a repository: `oaap app install <git>
--path … --ref …`) and *build guide*; ratings and comments (only by those
who obtained); support cases (RFC-0061); notifications to partners
(RFC-0080); cascading marketplaces (the generic feed, stage 3); paid
machine translation; digital-twin data (RFC-0031); signing in from other
tenants.

#### 15.8.11 Measurements (oaap-test, `market-test`)

| # | Measurement |
|---|---|
| N1 | Upgrade 0.2.1 → 0.3.0 keeps releases, entitlements, images; old categories appear under `default`, old texts under `de`; `oaap` exists and cannot be deleted |
| N2 | `publish.py sync` of `handballverein` with `en` + `de` and three images: asset, release, texts, images; a second run changes nothing |
| N3 | Gate: a profile with a literal `…_PASSWORD` value, a description with an `oaapk_` key, a ZIP with `.env` — each `422`, the answer names place and rule, not the value; the event log has no value |
| N4 | An uploaded JPEG with EXIF GPS is stored without it (bytes checked) |
| N5 | Review on: a new release is invisible publicly and in the feed until approved; the publisher cannot approve it; `review.py` without a model escalates; an admin approves; then it counts |
| N6 | Listing change by the publisher is visible and opens a case; the reviewer approves |
| N7 | Facets landscape / category / content; `default` categories under every landscape; counts after `can_see` |
| N8 | `Accept-Language: de` shows German, `en` falls back with the hint, `?lang=en` is remembered |
| N9 | Share: QR code decodes to the canonical link; catalog 0.3 with `followed` takes the pasted link, refuses a foreign host without a request to it, mirrors only the followed app |
| N10 | Partner light: a publisher grants a group on its own asset, cannot on another; the requester sees the answer with the link |

### 15.9 Stage 2 completed as built (2026-11-12, marketplace 0.3.0, package catalog 0.3.0)

New modules `secretguard.py` (the gate), `profileinfo.py` (type
`oaap-profile`), `i18n.py` (UI strings en/de, language choice); `db.py`
schema 3 (asset `texts`, `landscapes`, `featured`; release `review`,
`notes_i18n`; tables `landscape`, `category`, `setting`, `review`,
`reviewer`) with the migration of §15.8.1/§15.8.3; `views.py` rewritten
(start page, object page, share box, `/my/manage`, admin pages for reviews,
taxonomy, settings, texts per language); `tools/publish.py sync`,
`tools/review.py`; QR codes with `segno` 1.6.6 (pinned, pure Python). The
catalog: `upstream.py` follow list, `parse_link`, `CATALOG_UPSTREAM_SCOPE`.
Tests: `test_marketplace.py` 46, `test_storefront.py` 35 (now with texts
and categories as separate forms), new `test_mvp.py` (N1–N10 in-process, and
the copied RFC-0084 name categories compared with `guard.py`),
`test_tools.py` (sync, reviewer), catalog `test_upstream.py` (+ N9: a foreign
link is refused without a request to it) and `test_package_catalog.py`, all
green.

Where the build sharpened the text:

- **The feed states `origin`.** A catalog only knows its destination's proxy
  address (`OAAP_DESTINATION_UPSTREAM_URL`), not the target; it compares a
  pasted link with the `origin` the marketplace states about itself through
  that destination. `MARKET_PUBLIC_URL` fixes the origin when the
  destination reaches the marketplace by another address (on `oaap-test` the
  LAN address) -- otherwise share link and feed origin would differ.
- **Following needs a full feed.** After a new follow (and when no origin is
  known yet) the catalog drops its ETag, so the next poll is not a `304`.
- **An upgraded instance keeps its stored configuration.** `MARKET_TYPES`
  stayed `oaap-app,file` after 0.2.1 → 0.3.0; `oaap-profile` had to be
  switched on (`oaap app config set … MARKET_TYPES oaap-app,oaap-profile,file`,
  likewise `MARKET_FILE_EXTENSIONS` for `json`). The same applies to every
  instance being upgraded.
- **Feed fetches are no downloads.** A file fetched through `/feed/v1/files/`
  is logged as `fetch`; "most downloaded" counts `download` only.
- **A granted request's answer stays visible** (with its link) after the
  request box disappears, so an invitation link reaches the requester.
- **Listing reject by the reviewer becomes escalate** (the change is already
  visible; a human decides what to do).
- **The `oaapk_` pattern** follows RFC-0027's key form `oaapk_<id>_<secret>`
  with an alphanumeric id (the first draft assumed hex).
- JPEG stripping drops APP1 (EXIF and XMP), APP12, APP13 and comments, and
  keeps JFIF, ICC and Adobe segments; a lost EXIF orientation may turn a
  photo -- screenshots are unaffected.

**Measured on `oaap-test` (2026-11-12, through the real gateway with
machine keys `m77-ci` publisher, `m77-node-b` recipient, new `m77-review`
reviewer limited to `market-test`, 7 days):**

| # | Result |
|---|---|
| N1 | 0.2.1 → 0.3.0: schema 3, 4 releases all `approved`, entitlement and image kept, `werkzeug` → category of `default`, texts of `probe-market` under `de`, `oaap` fixed |
| N2 | `publish.py sync` of `handballverein` 1.2.0 (the profile from `oaap-docs`, en + de, icon + 2 screenshots): release `pending`, listing, 3 images; second run: no change |
| N3 | literal `DB_PASSWORD` in a profile, an `oaapk_`-shaped string in a summary, `config/.env` in a ZIP: each `422` with place and rule; neither value in the answers, the event log or the container log |
| N4 | a JPEG with EXIF GPS is served without `Exif`/`GPSLatitude`, JFIF kept |
| N5 | before approval no 1.2.0 on the public page; the publisher gets `404` on the review API; `review.py` without a model escalated both cases; the reviewer then gets `409`; the operator approved → 1.2.0 public. Feed: `probe-market` 0.2.1 checked in → node-b's feed still 0.2.0 and the catalog took nothing; approved → feed 0.2.1, the catalog took it (`hold`) |
| N6 | a tag change by the publisher visible at once, a listing case opened, the reviewer approved |
| N7 | facets `ls=oaap`, `content=template`, `cat=werkzeug`; public taxonomy; start page with landscapes and "new" |
| N8 | `Accept-Language` de/en, fallback hint on `probe-market` (only `de`), `?lang=de` beats the browser and sets the cookie, cookie remembered |
| N9 | canonical link from `MARKET_PUBLIC_URL`, the QR code is that of the link, script under `script-src 'self'`; catalog with `followed`: link of `market.oaap-web.oaap.joomp.de` refused with the operator's step, link of `market-test` followed (origin via the destination = the public address) |
| N10 | node-b asks for `handballverein`; `m77-ci` sees it under "My assets", grants with an invitation link; node-b sees the link as a link and can download; node-b cannot grant |

Left on `oaap-test`: `market-test` (review on, `MARKET_PUBLIC_URL` set,
landscape `bdt`, categories `setup-templates`, `sample-projects`, `docs`,
reviewer `m77-review`, asset `handballverein`), `zzz-probe-katalog-probe`
(`followed`, follows `probe-market`).

**Not yet:** Jörg's browser test (the criterion of the stage); the rollout
to `oaapx01` (`oaap-web-market` stays in maintenance until Jörg says so; on
upgrade set `MARKET_TYPES`, `MARKET_REVIEW`, `MARKET_PUBLIC_URL`, and the
landscapes and categories); a reviewer with a model (the AI gateway is not
on `oaapx01`, RFC-0064); real screenshots for the templates; the follow-up
RFC "marketplace as a platform" (§15.8.10).

---

## Deutsche Zusammenfassung (für Jörg)

**Worum es geht:** Eine neue App **Marketplace** verteilt digitale Assets.
OAAP-Apps sind ein Asset-Typ unter mehreren. Ein Asset hat **Releases**
(unveränderlich, Dateien über ihren SHA-256 abgelegt) und **Kanäle**
(`stable`, `beta`, …). Ein Kanal ist nur ein Zeiger auf Releases: Was in
Beta gut war, wird in Stable „hineingelegt“, mit denselben Bytes. Rückruf
heißt „zurückziehen“ (mit Grund). Der Kanal fällt dann auf das nächstniedrige
Release zurück.

**Sehen ist nicht Bekommen:** Ein Asset ist für jemanden *verborgen*
(Antwort 404), *sichtbar, aber gesperrt* („freischalten“) oder *beziehbar*.
Beziehbar ist es, wenn es frei ist oder eine **Berechtigung** (Person,
Maschine oder Gruppe × Asset × Kanäle) besteht. Suche, Zahlen und MCP
filtern, *bevor* gezählt wird. Partner dürfen später Berechtigungen für ihre
Kunden vergeben, aber nie die Sichtbarkeit erweitern.

**Einchecken:** Nach deiner Freigabe auf oaap-test lädt eine KI oder ein
Skript (`tools/publish.py`) das Paket mit einem Maschinenschlüssel per API
hoch, direkt in den gewünschten Kanal. Dieselbe Version mit anderen Bytes
wird abgelehnt.

**Beziehen, ohne den Knoten zu ändern:** Der **Paketkatalog** bekommt einen
**Spiegelmodus**. Über eine Destination (der Maschinenschlüssel liegt dort,
nicht im Katalog) holt er alle 15 Minuten den Feed, prüft Größe und
SHA-256, nimmt das Paket mit seinen bisherigen Regeln auf und gibt es frei
(Standard „auto“, wahlweise „hold“). Der Knoten liest den Katalog weiter wie
bisher. Es braucht also **kein Plattform-Release**. Zurückgezogene Versionen
nimmt der Katalog aus der Freigabe, laufende Instanzen bleiben unberührt.
Stufe 3 von RFC-0050 (Empfänger im Katalog) entfällt damit, der Marketplace
übernimmt sie.

**Oberfläche:** Öffentlich unter `/` (ohne Anmeldung), angemeldet unter
`/my/` (eine öffentliche Route kennt keine Identität). Suche mit Cards und
Facetten, Detailseite mit Bildern, Markdown, Versionen je Kanal und
Verlauf. Bilder nur PNG/JPEG/WebP, kein SVG.

**Ablage:** Zuerst lokal im Speicher der Instanz, damit das Backup sie
trägt. Später S3-kompatibel. Offene Frage O1: S3-Anfragen sind signiert und
passen nicht einfach durch den Destination-Proxy. Das messen wir vor Stufe 3.

**Stufen:** (1) MVP: API, Kanäle, Berechtigungen, Feed, Spiegelmodus,
gemessen mit M1–M12 auf oaap-test, danach echt mit hbvp von oaapx01 nach
oaapx02. (2) Schaufenster mit Cards, Details und Freischalt-Anfragen.
(3) S3, MCP, Statistiken. (4) Partner, eigene Asset-Typen, Signaturen.

**Entschieden (10.11.):** D1 eigene App, D2 Katalog dazwischen, D3
automatische Freigabe als Standard, D4 kein Geld, D5 Name Marketplace.
**Entschieden (11.11., alle wie empfohlen):** D6 produktiv auf oaapx01 (in
deinem Mandanten, oaap-test bleibt Messfeld), D7 Zurückgezogenes wird lokal
aus der Freigabe genommen (nie gelöscht, Instanzen unberührt), D8 Rechte
zum Veröffentlichen zunächst in der App, D9 SQLite im Speicher der Instanz,
D10 Plattform-API-Schlüssel von Maschinenbenutzern, D11 ein neues Asset
startet „sichtbar, gesperrt“, D12 Kanäle sind globale Namen. **Damit
Accepted; Stufe 1 wird gebaut.**

**Stufe 1 gebaut und gemessen (11.11., §15.6):** Marketplace 0.1.0 und
Paketkatalog 0.2.0 mit Spiegelmodus, Spec `oaap.dist.marketplace` 0.1.
Auf oaap-test lief der ganze Weg einmal echt durch: Einchecken mit
`publish.py`, die Berechtigung, der Katalog holt über die Destination, die
App aus dem Store installiert, Update, Rückruf (der Katalog nimmt die
Version aus der Freigabe, die Instanz bleibt) und `hold`. M1–M12 sind grün.
Ein 200-MB-Paket ging in 3 s durch den Proxy (O2 beantwortet). Nächster
Schritt ist der echte Lauf: Marketplace auf oaapx01, Katalog auf oaapx02,
hbvp auf dem neuen Weg. Das nur auf dein Wort.

**Stufe 2 gebaut (11.11., §15.7):** das Schaufenster. Suche mit Facetten
(gezählt wird nur, was man sieht), Karten mit Icon, Detailseite mit Bildern,
Markdown, Fakten und Versionsverlauf, Freischalt-Anfragen mit Antwort,
Bearbeiten in der Verwaltung. Auf oaap-test gemessen und produktiv auf
oaapx01 im neuen Mandanten `oaap-web`: https://market.oaap-web.oaap.joomp.de/
mit drei eigenen Apps als frei ladbare Beispiele. Fertig ist die Stufe, wenn
dein Browsertest besteht.

**Stufe 2 abschließen = MVP Aufbau-Vorlagen (12.11., §15.8, Entwurf nach
deinen Antworten):**

- **Landschaften und Kategorien** sind konfigurierbar, nur `oaap` ist fest.
  Kategorien der Landschaft `default` gelten übergreifend. Ein Asset kann in
  mehreren Landschaften und Kategorien stehen. Logo, Titel und Beschreibung
  gibt es je Sprache. Beides sind Facetten, dazu kommt der Inhaltstyp.
- Neuer Asset-Typ **`oaap-profile`** (Aufbau-Vorlage): Kennung und Version
  stammen aus dem Profil, wie beim Manifest einer App.
- **Mehrsprachig:** Englisch ist die Basissprache, weitere Sprachen sind je
  Text möglich. Angezeigt wird die Browsersprache, umschaltbar, mit Hinweis,
  wenn eine Sprache fehlt. Die bisherigen deutschen Texte wandern nach `de`.
- **Keine Geheimnisse:** Eine Sperre läuft vor jedem Speichern:
  - Dateinamen wie bei RFC-0084
  - Muster wie Schlüssel, Token, PEM
  - Profil-Regeln: kein wörtlicher Wert bei Schlüsseln wie `…_PASSWORD`,
    stattdessen `generate` oder Parameter
  - Bild-Metadaten (z.B. GPS) werden entfernt

  Die Fehlermeldung nennt Ort und Regel, nie den Wert.
- **Review mit vier Augen, digital:** Ein neues Release zählt erst nach der
  Freigabe. Eine Prüf-KI arbeitet als Maschinenbenutzer über die API. Wer
  einstellt, darf nicht selbst freigeben. Nur Eskalationen gehen an den
  Menschen, ebenso alles, was länger als 24 h offen ist. Textänderungen sind
  sofort sichtbar und werden danach geprüft. Das mitgelieferte `review.py`
  gibt ohne Modell nie frei, sondern eskaliert. Der Marketplace selbst ruft
  keine KI auf.
- **Detailseite als ObjectPage:** Oben stehen das Wichtige und die Galerie,
  darunter die Reiter Übersicht · Versionen · Technische Details. Die
  **Startseite** hat Hervorgehobenes, Landschaftskacheln, Neu und
  Meistgeladen. Der **Betreiber** stellt Akzentfarbe, Logo, Reihen und
  Sprache ein.
- **Teilen:** Ein Link und ein QR-Code. Der **Paketkatalog 0.3** nimmt den
  Link aus der Zwischenablage, prüft ihn gegen seine Destination (er ruft
  den Link selbst nie auf) und folgt dann genau dieser App
  (`CATALOG_UPSTREAM_SCOPE=followed`).
- **Automatisch pflegen:** `publish.py sync <ordner>` gleicht Release,
  Texte und Bilder aus einem Ordner mit `market.json` ab. Ein zweiter Lauf
  ändert nichts.
- **Partner light:** Wer in ein Asset einstellen darf, beantwortet dessen
  Anfragen und schaltet Benutzer oder Gruppen frei, nur für dieses Asset.
  Eine Antwort kann einen Einladungslink tragen.
- Alles andere kommt in ein Folge-RFC „Marketplace als Plattform“:
  Partnerstufen, Kampagnen, Coupons, Sicherheitshinweise, Bewertungen,
  Support, Kaskade, Zwilling.

**Gebaut und gemessen (12.11., §15.9):** Marketplace 0.3.0 und Paketkatalog
0.3.0 auf oaap-test, N1–N10 grün, durch das echte Gateway mit
Maschinenschlüsseln. Die Vorlage `handballverein` 1.2.0 ist per `sync` mit
EN/DE und Bildern drin. Die Sperre hat Passwort, Schlüssel und `.env`
abgewiesen, ohne den Wert irgendwo zu hinterlassen. Die Prüf-KI (ohne Modell)
hat eskaliert, der Betreiber hat freigegeben, und erst dann kam die neue
Version bis in den Katalog. Der Katalog hat einen fremden Link abgelehnt und
dem eigenen gefolgt. Zwei Befunde für den Rollout: Eine aktualisierte
Instanz behält ihre alte Typenliste (`oaap-profile` von Hand einschalten),
und `MARKET_PUBLIC_URL` setzen, damit Teilen-Link und Feed dieselbe Adresse
nennen. **Offen:** dein Browsertest, danach oaapx01 (Wartung bleibt bis
dahin), eine Prüf-KI mit Modell, echte Screenshots.

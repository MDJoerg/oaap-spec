# RFC-0144: A Tenant's Short Links — a Service the Platform Knows, and Campaigns You Can Measure

- **Status:** **Accepted (2026-11-28)** — direction decided by Jörg the
  same day, D1–D8 all as recommended („Ja, wie empfohlen“).
  **Stage 0 measured 2026-11-28 (§9)** — create, click, statistics through
  a platform key; W1–W4 for stage 1.
  **Amended 2026-11-28 (§10, §11):** hierarchical campaigns in the
  provider, shared through the twin (Jörg's addition); campaigns built
  in the Wegweiser 0.7.0 and measured on oaap-test; D9–D12 decided as
  recommended the same day.
  **Stage 1, platform half, built and measured 2026-11-28 (§12)** —
  reference 0.1.410, Wegweiser 0.8.0: the tenant's service, the door, the
  contract; W1–W4 answered.
  **Stage 1 complete 2026-11-28 (§13)** — reference 0.1.411, Wegweiser
  0.8.1: the instance's tab *Kurzlinks* and the tenant settings' page
  *Kurzlinks*, measured on oaap-test.
  **Stage 2, first part, 2026-11-28 (§14)** — reference 0.1.412: the daily
  pull, series per link and campaign, the tab, the tenant page, the weekly
  report; measured on oaap-test; W5 found.
- **Date:** 2026-11-28
- **Authors:** Jörg (the need: „apps shortlinks erzeugen können und wir
  dadurch eine messbarkeit und den Erfolg von kampagnen … messen, informiert
  werden und diese informationen … im Verlauf auswerten können“), Claude
  (design)
- **Depends on:** the Wegweiser app (`oaap-apps/apps/wegweiser`, 0.6.2:
  areas, links, QR, REST API `/api/v1` with platform API keys, per-link
  statistics), RFC-0043 (an instance's names), RFC-0027 (API keys), I-81
  (page statistics), RFC-0080 (notifications), RFC-0143 (people bound to
  instances), RFC-0142 (the situation on the go)
- **Changes (when accepted):** `oaap.core.tenant` (the tenant's short-link
  service), `oaap.apps.runtime` (a manifest need `shortlinks` and an offer
  `provides: shortlinks`), a contract `oaap.work.shortlinks`,
  `oaap.core.notifications` (two types), `oaap.core.portal`, the Wegweiser
  app (campaigns, the platform's door), `oaap.data.twin` (platform types
  `Campaign`, `ShortLink`, §11)

## Summary

The page statistics say *that* people come to a site; a short link says
*from where* — the flyer, the Instagram post, the newsletter. The Wegweiser
already makes short links with QR codes and counts their use, but it is an
app like any other: other apps cannot ask it for a link, and nobody sees
its numbers next to the site's.

This RFC makes the Wegweiser **the tenant's short-link service, known to
the platform**. A tenant names one instance as its service. **Apps of the
tenant ask the platform for a short link** (a manifest need) with a
campaign, a channel and a target; the platform creates it in the tenant's
Wegweiser and remembers which instance it belongs to. The clicks per day
come back into the **picture of the situation** (RFC-0142), the weekly
report and the portal — **per link and per campaign, over time** — and the
people who look after the instance (RFC-0143) see them. Two notifications
tell them when a campaign **takes off** or a printed link **points to a dead
page**.

## 1. The tenant's short-link service

- The tenant record carries `shortlinks: {instance, since, by}`: one
  production instance of the tenant that **provides** short links. Set by
  the `tenant_admin` or the `server_admin` in the portal (tenant settings,
  card *Kurzlinks*) or `oaap tenant shortlinks <tenant> <instance>|off`;
  log `tenant.shortlinks`.
- An app **provides** the service by declaring `provides: [shortlinks]` in
  its manifest and answering the contract `oaap.work.shortlinks` (§3) — the
  Wegweiser is the first, not the only one (capability first).
- The platform checks the instance is the tenant's, production, and
  answers the contract's `GET /…/about` before the setting is accepted.

## 2. Apps ask for short links

- An app declares the need `shortlinks` in its manifest. Its instances may
  then call the platform's door (inside the node, authenticated as the
  instance — the credential is measured in stage 0) to **create, list,
  pause, resume and retarget** links. The app never talks to the Wegweiser
  directly and needs no key of its own.
- **Create:** `{target, campaign, channel, title, key?}` → `{url, qr_svg,
  id}`. `target` must be https; a target on one of the tenant's own
  instances is marked as such (follow-through, §4). `channel` from a short
  list (`web`, `social`, `print`, `mail`, `chat`, `other`) so campaigns can
  be compared.
- The platform keeps for each link its **owner instance**, campaign,
  channel, creator and the Wegweiser's id (`apps/shortlinks/<tenant>.json`).
- People create links too: in the portal (an instance's tab *Kurzlinks*,
  for its *Verantwortliche* and the `tenant_admin`) and in the Wegweiser's
  own UI as today. Links made in the Wegweiser's UI appear in the platform's
  view through its listing, without an owner instance.

## 3. The contract `oaap.work.shortlinks`

What a provider answers to the platform (service credential of the
platform, scoped to one area of the provider reserved for it):

| Call | Purpose |
|---|---|
| `GET about` | name, version, the hosts links are made under (RFC-0043) |
| `GET campaigns` | the campaign tree: key, parent key, title, period, archived (§10) |
| `POST campaigns`, `PATCH campaigns/<key>` | create a campaign (under a parent), change, archive |
| `POST links` | create in the platform's area, with campaign (key)/channel/owner as fields |
| `PATCH links/<id>` | pause, resume, new target |
| `GET links?updated_since=` | the area's links |
| `GET stats?day=` | per link and day, with the link's campaign key: clicks, unique-per-day estimate, referrer host, device class — **counts only** |

The Wegweiser 0.7 adds the fields, the platform's area and `stats`; its own
UI, areas and roles stay as they are.

## 4. Measuring a campaign

- **Counts only, no person:** the platform's area keeps per click no
  address and no cookie — the same rule as the page statistics (I-81):
  clicks per day, a per-day estimate of distinct clients under a daily salt,
  referrer host, device class.
- **Over time:** per link and per campaign the daily series for 90 days
  (D4), the first day, the best day, the last 7 days against the 7 before.
- **Follow-through** (D5): when the target is one of the tenant's
  instances, the Wegweiser appends `utm_campaign=<campaign key>` (the
  link's own campaign, the platform rolls arrivals up the tree, §10) and
  `utm_source=<channel>`; the page statistics of that instance count those
  two keys — and only those, the rest of a query string is still dropped —
  as arrivals per campaign. „120 Klicks auf den Flyer-Link, 95 kamen auf der
  Seite an, 30 blieben länger als eine Seite.“
- **Where it shows:** the instance's tab *Kurzlinks* (table and a chart per
  link and campaign), the picture of the situation (deviations: a campaign
  with three times its usual clicks), the phone (RFC-0142, screen
  *Kampagnen*), the weekly report (a section *Kampagnen*: top links,
  campaigns compared by channel), and the chat's reading tools.
- **Who sees:** the `tenant_admin`, the link's creator, and the people bound
  to its owner instance (RFC-0143).

## 5. Being told

Two matters per link, routed like any notification (to *Zuständige der
Instanz* by default, RFC-0143):

- **`link.surge`** — a link's clicks today are at least 50 and at least
  three times its daily mean of the last 14 days: „Die Kampagne hebt ab“.
  Once per link and day, no reminder.
- **`link.dead`** — the target of an active link answers 4xx/5xx or not at
  all on two daily checks in a row (one `HEAD` per active link per day,
  reading only, at most 200 per tenant, the site check's honest
  User-Agent); closes when it answers again. A printed flyer cannot be
  reprinted, but the link can be retargeted — from the phone.

A campaign that goes quiet is a line in the weekly report, not a mail.

## 6. Stages

| Stage | Content | Done when |
|---|---|---|
| 0 | Measure: create, list and read statistics in the Wegweiser with a platform key; the credential an app instance has toward the platform; whether a redirect keeps a referrer; the cost of a daily `stats` pull on oaapx01 | a table in this RFC |
| 1 | `shortlinks` on the tenant, `provides`/need in the manifest, the contract (with campaigns, §10), Wegweiser 0.7 (**campaigns built 2026-11-28**), the platform's door (create, list, pause, retarget), the tab *Kurzlinks* | an app instance on oaap-test creates a link with a QR code, the portal shows it with its owner |
| 2 | Statistics into the platform: series per link and campaign (rolled up the tree), follow-through with the two `utm_` keys, weekly report, picture of the situation; **the campaign tree and its daily counts mirrored into the tenant's twin** (§11) | a link clicked on oaap-test shows its clicks and its arrivals |
| 3 | `link.surge`, `link.dead` | a link to a removed page opens `link.dead` and closes after retargeting |
| 4 | Phone and chat (RFC-0142 stage 4) | — |
| 5 | **The twin as the campaigns' master** for a tenant that plans campaigns in another app (§11, D12) | a campaign created through the twin appears in the Wegweiser's choice; a link assigned there counts in the twin |

## 7. Non-goals

- Tracking people across sites; a cookie; an address kept.
- A marketing suite (A/B tests, attribution models). Clicks, arrivals,
  comparison over time and by channel.
- Short links across tenants or a node-wide service.

## 8. Decisions

*Decided by Jörg 2026-11-28:* the short-link service belongs to the tenant,
and the platform knows it.

*Decided by Jörg 2026-11-28 („Ja, wie empfohlen“) — D1–D8 all as recommended:*

- **D1 — One service per tenant?** Recommended: **exactly one designated
  instance**; other Wegweiser instances keep working as apps.
- **D2 — Bound to the Wegweiser, or a contract?** Recommended: **a
  contract** (`provides: shortlinks`), the Wegweiser its first provider.
- **D3 — Apps through the platform, or directly?** Recommended: **through
  the platform** — no key in the app, the owner instance known, the same
  door for portal, phone and chat.
- **D4 — How long are click series kept?** Recommended: **90 days per day,
  then per week for a year**.
- **D5 — Follow-through with `utm_campaign`/`utm_source`?** Recommended:
  **yes, only to the tenant's own instances**, and the page statistics
  count only these two keys.
- **D6 — Notifications.** Recommended: **`link.surge` and `link.dead`**;
  quiet campaigns only in the weekly report.
- **D7 — Checking targets.** Recommended: **one `HEAD` per active link per
  day**, reading only, two failures in a row before `link.dead`.
- **D8 — Who creates links in the portal?** Recommended: **the
  `tenant_admin` and the instance's *Verantwortliche*** (RFC-0143).

## 9. Stage 0 measured (2026-11-28, reference 0.1.404, Wegweiser 0.6.2)

On oaap-test with a 1-day key of the probe principal `wegweiser-probe`,
limited to the instance `wegweiser`, revoked afterwards:

| Step | Result |
|---|---|
| list areas | 200 in 0.15–0.27 s: five areas, the redirect area `r` at log level `standard` |
| create a link (`POST /api/v1/links`, field `target_url`) | 201 in 0.15 s, id and key |
| click (iPhone UA, Referer instagram) | 301 → 302 → target, 13 + 31 ms |
| link statistics (`/links/<id>/stats?days=1`) | 200 in 0.16 s: 1 click, by day, referrer host `www.instagram.com`, class mobile, Safari, iOS |
| delete link | 200 |

**Findings for stage 1:**

- **W1 — The link the Wegweiser hands out is `http://`** — every click
  costs a redirect to https first (13 ms here, a round trip more on a
  phone). Wegweiser 0.7 hands out https.
- **W2 — Level `standard` keeps the address shortened to /24** (and `full`
  the whole address and User-Agent). §4 wants counts only: the platform's
  area gets a level without any address — referrer host, device class,
  browser, OS, day.
- **W3 — Statistics are per link or per area**, 0.16 s each: for the
  daily pull the contract needs one call for all links of the platform's
  area and a day (`GET stats?day=`), not one per link.
- **W4 — The instance's credential toward the platform** (§2: an app asks
  the platform) is not measured: app instances hold an instance key
  (`oaap app instance-keys`) — whether it can authenticate a call to a
  platform door is stage 1's first question.
- Whether a browser's redirect keeps the referrer for the **target** is not
  measured (a browser, not curl, decides); follow-through uses the `utm_`
  keys (D5) and does not depend on it.

**My mistake while measuring:** the clean-up loop of the first attempt
revoked not only its own key but eight older keys of the probe principal
`wegweiser-probe` (from the probes of 2026-09-24 to 27, last used in
September, one of them for all instances). Harmless — a probe principal on
oaap-test — but not intended; the loop now revokes only the key it issued.

## 10. Campaigns (amendment 2026-11-28)

Jörg: „Wir sollten das Kampagnenthema auch im Wegweiser verankern, damit wir
gruppieren und besser auswerten können. Kampagnen könnten hierarchisch
aufgebaut sein. … Minimal sollte eine Kampagne im Wegweiser erstellt werden
können, damit wir dann die Links zuordnen können.“

A campaign so far was a free text on a link. It becomes an object of the
provider:

- **A tree**, at most four levels („Sommerfest 2027“ → „Plakate“ →
  „Innenstadt“). A campaign has a **key** — lower case, digits, hyphen,
  unique in the instance, made from the title, **fixed after creation**:
  the key is how the platform, the twin and the page statistics
  (`utm_campaign`) find it again. Further: title, optional period
  (`starts_on`, `ends_on`), description, archived.
- **A link belongs to at most one campaign** and carries a **channel**
  (`web`, `social`, `print`, `mail`, `chat`, `other`).
- **Counting rolls up**: a campaign's numbers include every level below —
  calls per day, per channel, per sub-campaign, per link. A call is a use
  that did what the link is for (redirected, pixel loaded, downloaded).
- **Who:** everyone in the instance sees all campaigns and may assign their
  own links; the creator and `admin` change, archive and delete. Delete
  only an empty campaign — otherwise archive (it leaves the choice for new
  links, its numbers stay). Other people's links count in a campaign, but
  their titles and targets stay theirs.

**Built — Wegweiser 0.7.0 (2026-11-28):** table `campaigns`, the columns
`campaign_id`/`channel` added to an existing database on start; REST
`/api/v1/campaigns` (list as a tree with sums over the subtree, create,
read, change, delete, `…/stats`), links take `campaign` (id or key) and
`channel`; the tab *Kampagnen* (tree, form, a campaign's page with calls
per day, channel, sub-campaign and link, „Neuer Link in dieser
Kampagne“); the MCP tool `wegweiser_campaigns` (read only, counts only); 40
new checks, 246 in all, bite on removing the roll-up or the edit rule.
**Measured on oaap-test** through the gateway with a 1-day platform key
(revoked by its id afterwards): a tree of two levels, two links (print in
the sub-campaign, social in the top one), 3 + 1 calls from an iPhone →
the top campaign counts 2 links, 4 calls, `{print: 3, social: 1}`, its
sub-campaign 3; each call 0.15–0.17 s; deleting the non-empty top
campaign refused (409); everything removed again. The instance's eight
existing links kept, the two columns added.

## 11. Sharing campaigns through the twin (amendment 2026-11-28)

Jörg: „Vielleicht sollten wir hier auch unseren Zwilling nutzen, um diese
Daten zu teilen und mit anderen Apps (z. B. Kampagnen) zu teilen?“

Yes — campaigns are data other apps want: an app that plans campaigns
(dates, budget, material), the weekly report, the chat, an outside
marketing tool. The tenant's twin (`oaap.data.twin`, RFC-0120: REST
`/twin/v1`, upsert by key, relations, values with a period, series, MCP) is
where a tenant's data meet.

- **What goes in:** an object of a platform type **`Campaign`** per campaign
  (key `campaign:<key>`; title, period, archived) with the relation
  **`part_of`** to its parent; an object **`ShortLink`** per link of the
  platform's area (owner instance, channel) with **`belongs_to`** its
  campaign and **`points_to`** the instance when the target is one of the
  tenant's; the **daily counts** (calls, arrivals) as series on the link
  and the campaign. Counts only — no address, no client, as §4.
- **Who writes:** the platform, in its daily pull (stage 2), as the
  client principal of the short-link service, upsert by key — a renamed
  campaign stays the same object because its key is fixed.
- **Who reads:** any app or person of the tenant through the twin's REST
  and MCP doors, with their rights there (RFC-0120). A planning app joins
  its budget to the calls without asking the Wegweiser.
- **The master (D12).** In stage 2 the provider is the master and the twin
  a mirror (one direction). A tenant that plans campaigns in another app
  switches `campaigns.master` to `twin` (stage 5): then campaigns are
  created in the twin, the Wegweiser reads its tree from there (by key)
  and offers it for assignment; creating campaigns in the Wegweiser is
  then off. **Never two masters at once.**

*Amendment 2026-11-28 — decided by Jörg:* campaigns are anchored in the
provider, hierarchical, and can minimally be created there so links can be
assigned (§10, built).

*Decided by Jörg 2026-11-28 („Wie empfohlen“) — D9–D12 all as recommended:*

- **D9 — Depth and the key.** Recommended: **at most four levels; the key
  fixed after creation** (it is the name the twin and `utm_campaign` use).
- **D10 — `utm_campaign`.** Recommended: **the key of the link's own
  campaign**; the platform rolls arrivals up the tree it knows.
- **D11 — Into the twin?** Recommended: **yes, from stage 2, as a mirror**:
  `Campaign` with `part_of`, `ShortLink` with `belongs_to`/`points_to`,
  daily counts as series.
- **D12 — The master.** Recommended: **the provider first; the twin as the
  master per tenant setting when a planning app arrives (stage 5); never
  both.**

## 12. Stage 1, the platform's half (2026-11-28, reference 0.1.410, Wegweiser 0.8.0)

**Built.**

- **Manifest 0.24** (`oaap.apps.runtime` 2.44): the need
  `shortlinks: {create: true}` and the offer `provides: [shortlinks]`. The
  registry keeps both (`shortlinks_create`, `provides`).
- **The tenant's service** (`oaap.core.tenant` 1.31):
  `oaap tenant shortlinks <tenant> <instance>|off|show`, record
  `shortlinks: {instance, since, by}`, log `tenant.shortlinks`. Accepted
  only for a production instance of the tenant that offers `shortlinks` and
  answers `GET about` with the contract.
- **W4 — the instance's credential.** The construction of the case and
  people keys: `OAAP_SHORTLINKS_KEY`, scope `oaap.shortlinks:<name>`, opens
  exactly the door `/platform/shortlinks` on the instance's own site.
- **The door — a change against §2 and §3.** Behind it the **gateway**
  speaks to the provider directly, as the machine principal
  `platform:shortlinks`, and names the asking instance in the source
  headers. So:
  - the platform holds **no key at the provider** (§3 spoke of a service
    credential);
  - the **owner** is set by the gateway, never by the app's body, and lives
    in the provider (`links.owner`), not in a platform file
    `apps/shortlinks/<tenant>.json` (§2). One place for one fact; the
    portal reads it through the listing;
  - the provider shows an instance **only its own links**; another
    instance's link answers 404, also for pause, retarget and delete.
- **The contract in the Wegweiser 0.8.0** (`oaap.work.shortlinks` 0.1):
  - `GET about` (contract, version, hosts, channels); the platform's first
    call creates **its area** — `k` (short, it is printed on flyers), else
    `oaap-k` — redirects only, open to nobody else;
  - **W2:** a new log level **`anonymous`** for that area: referrer host,
    device class, browser, OS — no address, no User-Agent, no language.
    Distinct visitors per day are estimated through a salt that holds for
    one day and is replaced the next; the mark never leaves the app, not
    even as CSV;
  - **W3:** `GET stats?day=` — one call per day for all links of the area,
    with calls, visitors, referrer hosts, device classes, campaign key,
    channel and owner;
  - `GET links?updated_since=`; `owner` and `updated_at` on links; a create
    by the platform returns the address **and** `qr_svg` in one answer;
  - the platform principal is never `admin` or `keyuser`, whatever its key
    carries; only it may set `owner`.
- **W1** needed no change: since reference 0.1.399 `OAAP_INSTANCE_NAMES`
  says `https`, and the Wegweiser hands out what it is told. Stage 0's
  `http://` came from an instance started before that.

**Tests.**

- `test_shortlinks.py`, 39 checks: the manifest, key and door, which
  provider a site reaches (same tenant, still offering, never for a
  rehearsal), the marker, and every refusal of the setting. Two mutations
  bite (the platform's name at the provider, the `provides` check).
- `test_instance_keys.py` knows the new key.
- The Wegweiser: 285 checks (39 new). Mutations bite: the platform with
  `admin` in its key reaches foreign areas; an address stored on level
  `anonymous`.
- Green: 28 reference files that touch the manifest, the keys or the
  gateway lines.

**Measured on oaap-test** (backed up first, 0.1.410 staged; the Wegweiser's
data archived before the update to 0.8.0). A probe app `slprobe` declares
the need.

| Step | Result |
|---|---|
| install `slprobe` | key and address in its environment |
| the door before a service is named | 404 |
| name `slprobe` (no `provides`) | refused, with the reason |
| `oaap tenant shortlinks default wegweiser` | 3.8 s, area `k` created, links under `https://wegweiser.oaap-test…` |
| `about` through the door | 200 in 0.14 s |
| without a key / with a made-up key | 303 to the login / 401 |
| create (with `owner: wegweiser` in the body) | 201 in 0.14 s, owner **`slprobe`**, https address, `qr_svg` |
| list, QR as SVG | 200, 0.12–0.14 s, only its own link |
| pause, resume with a new target | 200, 200 |
| a foreign area, the instance's hosts | 403, 403 |
| three clicks (2 × iPhone, 1 × Windows, referrer Instagram) | 302 in 7–11 ms |
| `stats` through the door | 3 calls, 2 visitors, `www.instagram.com` 3, mobile 2 / desktop 1, owner and channel |
| the database of area `k` | 3 rows: address, User-Agent, language all empty |
| the existing links | 8 before (4 live), 9 after (5 live) — only the probe's added |
| the key at the Wegweiser's API / at `slprobe`'s own pages | 403 / 403 |
| `off`, then the door | 404; named again: 200 |
| the tenant's log | `tenant.shortlinks` for each change |

My mistake while measuring: the probe followed the redirect of a call
without a key and reported the login page's 200 as the door's answer. curl
showed the 303.

**Left on oaap-test for the portal step:** the Wegweiser 0.8.0, `slprobe`
with its one link, the setting on.

**Still open in stage 1:** the portal — the instance's tab *Kurzlinks* (its
links with owner, create, pause, retarget) and the card in the tenant
settings. Built in §13.

## 13. Stage 1, the portal's half (2026-11-28, reference 0.1.411, Wegweiser 0.8.1)

**What was built** (`oaap.core.portal` 0.3.73 §2.28, `oaap.core.tenant`
1.32):

- **The node reads, the portal shows.** The portal sits on no app network
  and never reaches a provider. The node writes `shortlinks-view.json` (0600,
  per tenant that named a service: whether it is usable, the provider, its
  area and hosts, and the links of the platform's area with owner, channel,
  title, campaign and today's calls and visitors) every minute and after
  every change. Only listed fields: no PIN, no creator id. A node where no
  tenant named a service writes nothing.
- **The node calls the provider from the host,** straight to its container
  on its app network (like the self-check, RFC-0084), every method. A write
  names the instance whose tab it came from in the source headers, exactly
  as the gateway does behind the app's own door: the provider sets the
  owner and refuses another instance's link with 404. So one rule decides
  ownership, whether the app or a person makes the link.
- **The instance's tab *Kurzlinks*** (both instance pages, after
  *Seitenstatistik*): the instance's links with target, channel, today's
  counts, a QR code as SVG for print (made by the portal from the view's
  address, only for an own link), *Pausieren*/*Fortsetzen*, *Neues Ziel*,
  *Kurzlink anlegen* (the target preset to the instance's address) and
  *Neu lesen*. Without a service it names the way to the tenant settings; a
  rehearsal makes no links. No delete: a printed link is paused, not taken
  away.
- **Who (D8):** administrators; of the bound people a *Verantwortliche*
  writes (`shortlinks`), every bound person reads again
  (`shortlinks:read`). One spool action `shortlinks`, judged like every
  instance action (`bindings.py`, `may()`); each change in the tenant's log
  as `instance.shortlinks` with person and role.
- **The tenant settings' page *Kurzlinks*** (`/tenant/shortlinks`, the
  tenant_admin for the own tenant, the server_admin for any): the service
  with since/by and whether it is usable, a choice of the tenant's
  production instances that offer `shortlinks` or none, the apps that ask,
  and all links over the platform with their instance. A spool action
  `tenant-shortlinks` runs the same function as `oaap tenant shortlinks`,
  the role and tenant taken from the actor's record.
- **Wegweiser 0.8.1:** a `PATCH` without `title` or `note` left both empty
  — pausing from the portal took a link's title away (found while
  measuring: the probe's link of §12 had lost its title through its
  retarget). Now only fields that are sent change; the form still empties a
  field that is sent empty.

**Tests.** `test_shortlinks_portal.py`, 65 checks: who may, the node's
call (source, body, every refusal, no delete, the log), the view (fields,
counts, an unusable service, 0600), the worker's two actions, the portal
(tab on both pages, forms per role, QR only for an own link, the requests
it queues, the tenant page). Mutations bite (create without the source; a
Betreuer allowed to write). The Wegweiser: 288 checks (3 new, they fail on
0.8.0). Green: 29 reference files that render the instance pages or touch
the spool, bindings and tenants.

**Measured on oaap-test** (backed up first; the Wegweiser's data archived
before 0.8.1):

| Step | Result |
|---|---|
| the view | written by the minute job; 0.09 s per write |
| the tab, as server_admin | the probe's link with target, channel *Druck*, 3 calls / 2 visitors today, all forms |
| create (form with `owner=wegweiser`) | owner **`slprobe`**, title and channel kept |
| pause, call the link | 404; resume: 302 to the target |
| pause: the title | stays (it did not on 0.8.0) |
| an `http://` target | refused with the reason |
| the probe's link from the page of `wegweiser` | refused: no such link of this instance; QR there 404 |
| a request through the portal | 1–2 s (the spool's polling) |
| a person without a right | 403, tab and tenant page |
| a Betreuer / a Verantwortliche (bound for the test, then unbound) | tab with both links; *Neu lesen* only / also create, pause, new target |
| the tenant page | service, choice, the asking app, both links with instance |
| *keiner*, then `wegweiser` | the door 404, then 200; `slprobe` as service refused (no `provides`) |
| the tenant's log | `instance.shortlinks` per change, `tenant.shortlinks` per setting |

**My mistake while measuring:** busybox `wget` POSTs again after a 303.
The first run therefore showed 405 for every button (the action had
happened, the view said so) and looped on the tenant page — eight
`tenant.shortlinks` lines on oaap-test for one setting. Measured again
with a client that does not follow redirects.

**Left on oaap-test:** the Wegweiser 0.8.1, `slprobe` with its two links,
the setting on.

**Next:** stage 2 — the daily pull into the picture of the situation and
the weekly report (§4), the notifications `link.surge`/`link.dead` (§5).

## 14. Stage 2, first part: the counts over time (2026-11-28, reference 0.1.412)

Stage 2 (§6) has five pieces. This part builds three — the daily pull with
its series (rolled up the tree), the tab and the tenant page, the weekly
report. Still open in stage 2: **the follow-through** with the two `utm_`
keys (the Wegweiser appends them, the page statistics count them), **the
twin's mirror** (§11), and **the picture of the situation** — RFC-0142's
picture is not built yet (its stage 1); the counts wait for it in the store.

**What was built** (`oaap.core.portal` 0.3.74 §2.28, `oaap.core.notifications`
0.19 §2.9):

- **The daily pull.** Once a UTC day (the provider counts by UTC day), after
  00:20 UTC, the minute job asks each tenant's service for the days it does
  not have: `GET stats?day=` per day (W3), the campaign tree, the links'
  titles. The first pull reaches **14 days** back, so stage 3's 14-day mean
  has its baseline at once; a failed day ends the run and is tried again
  after 30 minutes, never more often. `oaap tenant shortlinks <tenant> pull`
  does it now.
- **The store** `apps/shortlinks/<tenant>.json` (0600, directory 0700): per
  day and link calls, the visitor estimate, campaign key, channel, owner, at
  most 8 referrer hosts and device classes — the fields are listed, nothing
  else the provider might send is kept (§4, counts only). **D4:** 90 days per
  day, then per week (links and campaigns rolled up) for a year.
- **The series** (`services/shortlinks_stats.py`, pure functions): per link
  and campaign the first day, the best day, the last 7 against the 7 before,
  90 days in all, 30 for the chart. A campaign counts every level below it
  (§10); **per owner instance** the same from its own links only — an
  instance's tab never shows another instance's numbers.
- **The portal:** columns *7 Tage* (*Vorwoche*) and *Verlauf* (inline SVG,
  no script), *Kampagnen dieser Instanz*; on the tenant page all campaigns
  with best day. Both name the day the numbers reach.
- **The weekly report:** a section *Kampagnen* (calls against the week
  before, top 5 links, campaigns by channel, *ruhig geworden*) and a line in
  the summary. Read from the store when the report is written — not from
  the ledger, whose local midnight comes before the provider's UTC midnight.

**Tests.** `test_shortlinks_stats.py`, 57 checks: which days are missing,
counts only (a provider's address field is not kept), the roll-up (three
levels, an unknown key, a loop), the series, days into weeks, the week's part
(quiet, archived is not quiet), the report's section, the pull (backfill,
nothing twice, a failing day resumed, no service, 0600), the minute's timing
and retry, the view, the tenant's report, the portal (chart, columns,
campaigns of an instance from its own links only, tenant page). Mutations
bite: no roll-up; an address kept. Green in the Linux runner with
`test_shortlinks_portal.py`, `test_shortlinks.py`, `test_weekly_report.py`,
`test_link_reports_portal.py`, `test_care_portal.py`.

**Measured on oaap-test** (backed up first, 0.1.412 staged):

| Step | Result |
|---|---|
| the minute job after staging | pulled 14 days (11-14 … 11-27) by itself, a minute later; no error in the journal |
| store | 0600 in a 0700 directory; only the listed fields |
| a tree at the Wegweiser (`sonde-fest` → `sonde-druck`), the probe's two links assigned through the platform with `slprobe` as source | 201, 201; 200, 200 |
| 5 clicks (3 + 2, iPhone and Windows, referrers Instagram, example.org, Facebook) | 302 each |
| a pull with tomorrow as now (today as yesterday) | 1 day in **0.08 s**; the links 6 and 4 calls (with the clicks of §13), referrer hosts and device classes |
| roll-up | `sonde-fest` 10 = its own 4 + `sonde-druck` 6; per owner `slprobe` the same |
| the view | 0.08 s; both links with history |
| the tab / the tenant page (GET through the gateway) | 7 days, the week before, chart (120 bars), the instance's campaigns indented, „bis 28.11.“ / card *Kampagnen* |
| the weekly report into a temporary directory | *Kampagnen*: top links, the tree by channel (Druck 6, Soziale Medien 4), the summary line „Kurzlinks: 10 Aufrufe (Vorwoche 0)“ |
| afterwards | today taken out of the store again (the real pull tomorrow fetches the whole day) |

**W5 — the provider counts automated fetchers as calls.** The probe's link
showed 3 of its 4 calls from the device class `bot` (the stage-1 probes
used Python and wget). A messenger's link preview is such a fetcher: a
social link would count its previews as people. The page statistics keep
people and automats apart (I-81); the contract's `stats` should too —
calls and visitors without `bot`, the automats as their own number. That is
a change in the Wegweiser (0.8.2), not in the platform.

**Left on oaap-test:** 0.1.412, the Wegweiser 0.8.1 with the campaigns
`sonde-fest`/`sonde-druck`, `slprobe`'s two links assigned, the store of 14
days.

**Next:** W5 in the Wegweiser; then the rest of stage 2 (follow-through, the
twin) or stage 3 (`link.surge`, `link.dead`).

## Deutsche Zusammenfassung

**Worum es geht:** Die Seitenstatistik zeigt, *dass* Besucher kommen, ein
Kurzlink zeigt, *woher*: Flyer, Instagram, Newsletter. Der Wegweiser kann
Kurzlinks mit QR-Code und zählt sie, ist aber eine App wie jede andere.
Andere Apps können ihn nicht nutzen, und seine Zahlen stehen nirgends neben
denen der Seite.

**Vorschlag:**
- **Der Wegweiser wird der Kurzlinkdienst des Mandanten**, und die Plattform
  kennt ihn: Der Mandant benennt genau eine Instanz. Sie bietet einen
  Vertrag `oaap.work.shortlinks` an; der Wegweiser ist der erste Anbieter.
- **Apps fordern Kurzlinks über die Plattform an** (Bedarf im Manifest), mit
  Ziel, Kampagne und Kanal; zurück kommen Adresse und QR-Code. Die Plattform
  merkt sich, zu welcher Instanz der Link gehört. Auch im Portal lassen sich
  Links anlegen, pausieren und umleiten.
- **Messen ohne Person:** Klicks je Tag, ohne Adresse und ohne Cookie.
  Verlauf je Link und je Kampagne. Zeigt ein Link auf eine eigene Instanz,
  hängt der Wegweiser `utm_campaign`/`utm_source` an, und die
  Seitenstatistik zählt, wie viele angekommen sind.
- **Sichtbar** im Reiter „Kurzlinks“ der Instanz, im Lagebild, auf dem Handy
  (Kampagnen), im Wochenbericht und für den Chat — für den Mandanten-Admin,
  den Ersteller und die Zuständigen der Instanz (RFC-0143).
- **Informiert werden:** `link.surge` (eine Kampagne hebt ab) und
  `link.dead` (ein Link zeigt zweimal hintereinander auf eine tote Seite;
  einmal täglich nur lesend geprüft). Umleiten geht auch vom Handy.

**Stufen:** 0 messen, 1 Kurzlinkdienst des Mandanten und Anlegen über die
Plattform, 2 Zahlen und Ankünfte in die Plattform, 3 Meldungen, 4 Handy und
Chat.

**Entschieden (Jörg, 28.11.):** Der Wegweiser gehört in den Mandanten, die
Plattform kennt ihn. **Entschieden (Jörg, 28.11., „Ja, wie empfohlen“): D1–D8 wie empfohlen:** genau ein Dienst je
Mandant; ein Vertrag statt fester Bindung an den Wegweiser; Apps über die
Plattform; 90 Tage täglich, dann wöchentlich ein Jahr; utm-Weitergabe nur zu
eigenen Instanzen; zwei Meldungen; ein Ziel-Check pro Tag; anlegen dürfen
Mandanten-Admin und Verantwortliche.

Stufe 0 gemessen (28.11., oaap-test, Wegweiser 0.6.2): Anlegen über einen
Plattform-Schlüssel 0,15 s, Klick mit Herkunft Instagram gezählt, Statistik
je Tag mit Herkunft, Gerät, Browser. Befunde: (W1) der Wegweiser gibt
`http://`-Links aus — jeder Klick kostet eine Umleitung mehr; (W2) die
Stufe `standard` speichert die gekürzte Adresse — der Bereich der Plattform
braucht eine Stufe ganz ohne Adresse; (W3) Statistik nur je Link oder
Bereich — der Vertrag braucht einen Abruf für alle Links eines Tages; (W4)
mit welchem Ausweis eine App die Plattform ruft, klärt Stufe 1. Mein
Versehen: Beim ersten Versuch widerrief die Aufräumschleife auch acht alte
Schlüssel des Probe-Kontos `wegweiser-probe` (zuletzt im September benutzt)
— harmlos, aber nicht gewollt.

**Ergänzung (28.11.): Kampagnen im Wegweiser, geteilt über den Zwilling**
(Jörg: Kampagnen im Wegweiser verankern, hierarchisch, minimal dort
anlegbar; Daten über den Zwilling mit anderen Apps teilen). **Kampagnen**
bilden einen Baum mit höchstens vier Ebenen. Der Kurzname entsteht aus dem
Titel und bleibt danach fest, denn unter ihm finden Plattform, Zwilling und
Seitenstatistik die Kampagne wieder. Ein Link gehört zu höchstens einer
Kampagne und trägt einen Kanal (Webseite, Soziale Medien, Druck, E-Mail,
Messenger, Sonstiges). Gezählt wird über alle Ebenen darunter: je Tag, je
Kanal, je Unterkampagne. Alle sehen alle Kampagnen und ordnen ihre Links zu;
ändern dürfen Ersteller und admin. Löschen geht nur leer, sonst archivieren.
**Gebaut: Wegweiser 0.7.0**, auf oaap-test gemessen (zwei Ebenen, zwei Links,
4 Aufrufe richtig nach Kanal und Unterkampagne gezählt, danach aufgeräumt).
**Zwilling:** Ab Stufe 2 spiegelt die Plattform den Baum (`Campaign` mit
`part_of`), die Links (`ShortLink` mit `belongs_to`/`points_to`) und die
Tageszahlen in den Zwilling des Mandanten. Andere Apps lesen dort mit ihren
Rechten. Plant ein Mandant seine Kampagnen in einer eigenen App, wird der
Zwilling der Herr der Kampagnen (Stufe 5) und der Wegweiser liest von dort;
nie zwei Herren zugleich. **Entschieden (Jörg, 28.11., „Wie empfohlen“):** vier Ebenen und fester
Kurzname (D9); `utm_campaign` = Kurzname der eigenen Kampagne (D10);
Zwilling ab Stufe 2 als Spiegel (D11); erst der Wegweiser, später auf Wunsch
der Zwilling als Herr (D12).

**Stufe 1, Plattformhälfte (28.11., Referenz 0.1.410, Wegweiser 0.8.0):**

- Eine App erklärt `shortlinks: {create: true}` und bekommt einen Schlüssel
  für ihre eigene Tür `/platform/shortlinks` (W4).
- Hinter der Tür spricht das **Gateway** selbst mit dem Wegweiser, als
  `platform:shortlinks`, und nennt die App als Quelle. Die Plattform braucht
  deshalb keinen eigenen Schlüssel beim Wegweiser.
- Den **Besitzer** setzt das Gateway, nicht die App. Er steht im Wegweiser,
  nicht in einer Plattformdatei. Jede App sieht und ändert nur ihre eigenen
  Links.
- Der Mandant benennt seinen Dienst mit `oaap tenant shortlinks`. Vorher
  prüft die Plattform: eigener Mandant, Produktivkanal,
  `provides: [shortlinks]`, und `about` antwortet mit dem Vertrag.
- Der **Wegweiser 0.8.0** legt beim ersten Ruf der Plattform deren Area `k`
  an. Sie speichert auf der neuen Stufe „anonymous“: Herkunft und Gerät,
  aber keine Adresse (W2). Besucher je Tag werden über einen Tages-Salz
  geschätzt. `stats?day=` liefert alle Links eines Tages in einem Ruf (W3).
- W1 war schon erledigt: Seit 0.1.399 bekommen Apps ihre Namen mit https.

Auf oaap-test gemessen mit der Sonde `slprobe`:

- Die Sonde legte einen Link an (0,14 s). Er gehörte `slprobe`, obwohl sie
  „wegweiser“ als Besitzer mitschickte. QR-Code, Pause und Umleiten gingen.
- Drei Klicks ergaben 3 Aufrufe und 2 Besucher, Instagram als Herkunft. In
  der Datenbank steht keine Adresse.
- Ohne Dienst antwortet die Tür 404, ein fremder Bereich gibt 403.

**Stufe 1, Portalhälfte (28.11., Referenz 0.1.411, Wegweiser 0.8.1):**

- Jede Instanz hat einen Reiter **„Kurzlinks“**: ihre Links mit Ziel, Kanal
  und den Zahlen von heute, QR-Code zum Drucken, Pausieren, neues Ziel,
  neuer Link. Schreiben dürfen die Verwaltung und Verantwortliche, lesen
  alle Gebundenen. Löschen gibt es nicht; ein gedruckter Link wird pausiert.
- In den Mandanten-Einstellungen gibt es die Seite **„Kurzlinks“**: welcher
  Dienst es ist, die Auswahl, die Apps, die Links anfordern, und alle Links
  mit ihrer Instanz.
- Das Portal erreicht den Dienst nie selbst. Der Knoten liest jede Minute
  und nach jeder Änderung und schreibt eine Sicht. Ändern geht über den
  Spool. Dabei nennt der Knoten die Instanz als Quelle wie das Gateway, und
  der Dienst setzt den Besitzer.
- Beim Messen gefunden: Der Wegweiser hat bei einem PATCH ohne Titel den
  Titel gelöscht. Das ist in 0.8.1 behoben.
- Auf oaap-test gemessen: Pausiert antwortet der Link mit 404, danach
  wieder mit 302. Ein fremder Link wird abgelehnt, ein Betreuer sieht nur
  „Neu lesen“. Mein Messfehler: busybox-wget schickt nach einem 303 noch
  einmal POST, daher acht Protokollzeilen auf oaap-test.

**Stufe 2, erster Teil (0.1.412, §14):**
- Der Knoten holt die Zahlen einmal am Tag ab (nach 00:20 UTC, beim ersten
  Mal 14 Tage zurück) und hält sie je Mandant: 90 Tage je Tag, dann ein Jahr
  je Woche, nur Zahlen.
- Der Reiter zeigt je Link 7 Tage gegen die Vorwoche und einen Verlauf über
  30 Tage, dazu die Kampagnen der Instanz, nur aus ihren eigenen Links. Die
  Mandantenseite zeigt alle Kampagnen.
- Der Wochenbericht bekommt einen Abschnitt „Kampagnen“ mit den stärksten
  Links, den Kanälen und „ruhig geworden“.
- Auf oaap-test gemessen: ein Abruf 0,08 s.
- Befund W5: Der Wegweiser zählt Automaten als Aufrufe, auch die
  Link-Vorschau eines Messengers.
- Offen in Stufe 2: der Rücklauf über `utm_`, der Spiegel im Zwilling und
  das Lagebild (es wartet auf RFC-0142 Stufe 1).

**Als Nächstes:** W5 im Wegweiser, dann der Rest von Stufe 2 (Rücklauf,
Zwilling) oder Stufe 3 (`link.surge`, `link.dead`).

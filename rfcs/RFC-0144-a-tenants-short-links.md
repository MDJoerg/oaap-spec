# RFC-0144: A Tenant's Short Links — a Service the Platform Knows, and Campaigns You Can Measure

- **Status:** **Accepted (2026-11-28)** — direction decided by Jörg the
  same day, D1–D8 all as recommended („Ja, wie empfohlen“).
  **Stage 0 measured 2026-11-28 (§9)** — create, click, statistics through
  a platform key; W1–W4 for stage 1.
  **Amended 2026-11-28 (§10, §11):** hierarchical campaigns in the
  provider, shared through the twin (Jörg's addition); campaigns built
  in the Wegweiser 0.7.0 and measured on oaap-test; D9–D12 decided as
  recommended the same day.
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

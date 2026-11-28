# RFC-0144: A Tenant's Short Links — a Service the Platform Knows, and Campaigns You Can Measure

- **Status:** **Accepted (2026-11-28)** — direction decided by Jörg the
  same day, D1–D8 all as recommended („Ja, wie empfohlen“).
  **Stage 0 measured 2026-11-28 (§9)** — create, click, statistics through
  a platform key; W1–W4 for stage 1.
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
  app (campaign fields, the platform's door)

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
| `POST links` | create in the platform's area, with campaign/channel/owner as fields |
| `PATCH links/<id>` | pause, resume, new target |
| `GET links?updated_since=` | the area's links |
| `GET stats?day=` | per link and day: clicks, unique-per-day estimate, referrer host, device class — **counts only** |

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
  instances, the Wegweiser appends `utm_campaign=<campaign>` and
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
| 1 | `shortlinks` on the tenant, `provides`/need in the manifest, the contract, Wegweiser 0.7, the platform's door (create, list, pause, retarget), the tab *Kurzlinks* | an app instance on oaap-test creates a link with a QR code, the portal shows it with its owner |
| 2 | Statistics into the platform: series per link and campaign, follow-through with the two `utm_` keys, weekly report, picture of the situation | a link clicked on oaap-test shows its clicks and its arrivals |
| 3 | `link.surge`, `link.dead` | a link to a removed page opens `link.dead` and closes after retargeting |
| 4 | Phone and chat (RFC-0142 stage 4) | — |

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

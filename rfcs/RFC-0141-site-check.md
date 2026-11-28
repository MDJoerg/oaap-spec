# RFC-0141: Site Check — A Weekly Look at a Tenant's Web Site, From Outside

- **Status:** **Accepted (2026-11-28)** — D1–D7 decided by Jörg, all as
  recommended (§10, „Wie empfohlen“). **Stage 0 measured 2026-11-28
  (§11)** — five findings change stage 1's design, none a decision.
- **Date:** 2026-11-28
- **Authors:** Jörg (the need: „Ok i-83“, after the look at `sglok-sbk.de`
  that started RFC-0140), Claude (design)
- **Depends on:** RFC-0140 (base hardening — the probes of its §1 are the
  first checks here, its D4/D8 point at this RFC), I-81 (the website mode:
  page statistics, the switch „Hinweise zur Webseite“ = `site_watch`,
  notifications `site.google`/`site.notfound`), RFC-0080
  (notifications), RFC-0084 (secret files refused at the gateway),
  RFC-0115 (a tenant's own domain, its DNS check), RFC-0018 (canonical
  name and aliases), RFC-0085 (the fleet — a later check from another node)
- **Changes (when accepted):** `oaap.core.portal` (a card „Seiten-Check“
  on the tab „Seitenstatistik“), `oaap.core.notifications` (a type
  `site.check`), the instance record (a switch), the CLI

## Summary

On 2026-11-27 a look at `sglok-sbk.de` from outside — as Google, as a
visitor, as an attacker would — found gaps the tenant could not see:
JavaScript sent uncompressed, no security header, `www` serving the same
page as the apex, `TRACE` ending in a 500, an AVIF logo old Safari does not
show. RFC-0140 closed what is the platform's to close. What is the
**site's** to fix — a canonical link, structured data, image sizes, a
content security policy, reachable imprint and privacy pages, fonts loaded
from Google without consent — the tenant has to *learn*, and today nobody
tells them.

This RFC adds a **site check**: once a week, and on a button, the node
reads a production instance's public start page the way a visitor's
browser does, compares what it finds with a short list of rules, and shows
the result on the tab „Seitenstatistik“ as a traffic light in four areas —
**Sicherheit, Auffindbarkeit, Tempo, Recht**. Every point says what was
found, why it matters in one sentence, and **who fixes it**: a switch of
the platform (with a link to it) or the site's author. A new red point
reaches the tenant's lists through the existing switch „Hinweise zur
Webseite“; nothing else mails.

It reads, it never tries: one start page, its own scripts, styles and
images, `robots.txt` and the sitemap — a few dozen requests a week, one at
a time, under an honest User-Agent.

## 1. Why now, and why the platform

- The platform already knows half of the answers without asking the site:
  whether the instance is production, its canonical name and aliases, the
  alias mode, compression and headers on or off (RFC-0140), the AI-fetcher
  level, whether a secret file was asked for (RFC-0084), whether Google
  comes (I-81). A check that combines these with what the page says is
  worth more than any outside tool, which knows none of it.
- The tenants with web sites are the ones who did not write them
  themselves (a deploy URL from another AI, a club's volunteer). A list of
  „do this“ in German, with the platform's switch beside it, is what they
  can use; a Lighthouse score of 73 is not.
- The measurement code exists (RFC-0140 stage 0 scripts), the switch
  pattern exists (`site_watch`, `ai_fetchers`), the notification path
  exists (`site.google`). Stage 1 is small.

## 2. The rules — reading only

The check is a **visitor**, not a scanner. It obeys the rule the project
keeps for its own probes against a tenant's site
(`schutzproben-auf-oaap-test`): no load, no forged identity, no attempt to
break in.

1. **What it fetches:** `GET /` on the canonical name (https), following
   redirects (at most 5); the same-origin scripts, styles and images the
   start page names (at most 30, each at most 5 MB, the rest counted, not
   fetched); `/robots.txt`; the sitemap that `robots.txt` names, else
   `/sitemap.xml` (only its head — is it there, how many URLs, which host);
   `http://<canonical>/` and each alias's `https://<alias>/` without
   following, for the redirect answers. Nothing else. **No `/.env`, no
   `/.git/`:** what the secret-file guard does, the gateway's own config
   and RFC-0084's log say.
2. **How:** one request at a time, 200 ms apart, timeout 15 s each, from
   the node itself (§5), User-Agent `OAAP-Seiten-Check/1 (+<node's external
   name>)`. The page statistics count it as an automaton of its own and
   never as a visit.
3. **What it keeps:** the findings (§3) and a few numbers — never the
   page's text, never a cookie, never a screenshot. The last 12 results per
   instance.
4. **Only on a production instance** whose administrator switched it on
   (§4). A test instance sends `noindex` and is not finished; a rehearsal
   is never checked.

## 3. The checks

Each check yields **green**, **yellow** (worth doing) or **red** (it hurts
now) and the party who fixes it: **Plattform** (a switch on this page) or
**Seite** (the author). Red is kept for what clearly costs visitors or
trust; everything a matter of taste is at most yellow.

### 3.1 Sicherheit

| Check | Red | Yellow | Fixes |
|---|---|---|---|
| Certificate | < 14 days left or invalid | < 30 days | Plattform (renewal) |
| http → https | `http://` serves the page | — | Plattform |
| TLS versions | 1.0/1.1 accepted | — | Plattform |
| HSTS, `nosniff`, `Referrer-Policy` | — | missing (a switch off, or the app sends a weaker value) | Plattform (switch) / Seite |
| Content-Security-Policy | — | none | Seite |
| Embedding (`frame-ancestors` / `X-Frame-Options`) | — | none (RFC-0140 D4) | Seite |
| Framework announced (`X-Powered-By`, `Server` with a version) | — | yes (RFC-0140 D8: informative, not a defect) | Seite |
| Secret files asked for | — | RFC-0084 refused requests in the last 7 days (shown as „wird versucht, wird abgewiesen“ — reassurance, not a fault) | — |

### 3.2 Auffindbarkeit

| Check | Red | Yellow | Fixes |
|---|---|---|---|
| `noindex` (header or meta) on production | yes | — | Seite (I-81: the platform sends none on production) |
| `robots.txt` | disallows `/` for everybody | missing | Seite |
| Sitemap | names another host | missing; or listed URLs on http | Seite |
| Canonical link | points at another host than the canonical name | missing | Seite |
| Aliases | — | an alias serves the page (`alias_mode` serve) | Plattform (switch, RFC-0140 stage 3) |
| `<title>`, `meta description` | title missing | description missing, title > 70 or description > 160 characters | Seite |
| `og:image` / `og:url` | — | missing, relative, or on another host than the canonical name | Seite |
| Structured data (`application/ld+json`) | — | none | Seite |
| `<html lang>` | — | missing | Seite |
| Google comes | — | `site.google` open (I-81) | — |

### 3.3 Tempo

| Check | Red | Yellow | Fixes |
|---|---|---|---|
| Time to first byte of `/` | > 3 s | > 1 s | Seite (or the node) |
| Weight of the start page (HTML + fetched assets, as transferred) | > 5 MB | > 2 MB | Seite |
| Uncompressed text (JS/CSS/HTML/SVG > 1 KB without `Content-Encoding`) | — | any | Plattform (switch) / Seite |
| Large images (> 500 KB each) | — | any, with name and size | Seite |
| Image formats | — | AVIF/WebP without a fallback in `<picture>` (old Safari shows nothing) | Seite |
| Cache headers on hashed assets | — | none | Seite |

### 3.4 Recht — hints, not legal advice

The card says so in its first line: *„Hinweise, keine Rechtsberatung.“*

| Check | Red | Yellow | Fixes |
|---|---|---|---|
| Imprint | — | no link whose text or path says Impressum/Imprint on the start page | Seite |
| Privacy statement | — | no link Datenschutz/Privacy | Seite |
| Third-party resources loaded on the start page | — | each foreign host named (fonts.googleapis.com, a YouTube or Maps iframe, an analytics script), with the sentence that loading it passes the visitor's address to that host | Seite |
| Cookies set on the first answer | — | each name, with whether it looks technical (session) or not | Seite |

## 4. Switch, button, CLI

- **Switch `site_check`** on the instance record, like `site_watch`:
  `{on, since, by}`; absent = off. Who may: the instance's
  `tenant_admin` and the `server_admin` (as `site_watch`, RFC-0140 D6).
  Audit `instance.site-check`. Kept by an update and a takeover test →
  production.
- **Weekly run** by the existing daily job, on the instance's weekday
  derived from its name (spread over the week, never all at once).
- **„Jetzt prüfen“** on the card, at most once an hour per instance; the
  result appears when the page is reloaded (a spool request `site-check`,
  the host runs it).
- **CLI** `oaap app site-check <instance> [on|off|run|show]`.

## 5. Where the check runs

From the **node itself**, against the public name as the world resolves
it. Directly on the internet (oaapx01) that is the way a visitor comes.
Behind an edge (RFC-0006) the request goes out to the public address and —
if the router allows the loop back (hairpin NAT) — in again through the
edge: the visitor's path, with the edge's certificate. If the loop is not
allowed, the check says „von diesem Knoten aus nicht erreichbar —
Ergebnis fehlt“ and is **grey, not red**; stage 0 measures every node.

Later (§9, not in this RFC): a node of the fleet checks another node's
sites (RFC-0085), which is „from outside“ in the strict sense and also
sees a router that blocks the world.

## 6. Results and notifications

- The card **„Seiten-Check“** on the tab „Seitenstatistik“, under
  „Hinweise zur Webseite“: the date of the last run, four lights, then the
  yellow and red points sorted by area, each with *gefunden — warum — wer
  — was tun*; a „Plattform“ point links to its switch. „Seit dem letzten
  Mal neu“ and „behoben“ marked against the previous run.
- **Mail only through `site_watch`:** if „Hinweise zur Webseite“ is on, a
  red point that was not red in the previous run opens a matter
  `site.check/<instance>` (`oaap.core.notifications`), and it closes when
  a run finds no red point. One mail when it begins, one when it ends — the
  rhythm of `site.google`. Yellow never mails; it waits in the portal and
  in the weekly report.
- The weekly report (RFC-0083) lists per checked instance its four
  lights.

## 7. Stages

| Stage | Content | Done when |
|---|---|---|
| 0 | Measure: hairpin from every node to its own public names; the check as a script against oaap-test's instances and our own production sites (`market.oaap-web…`, `go.joomp.de`, `projects.joomp.de`), never a foreign tenant's; count requests and time per run | a table in this RFC |
| 1 | Switch, CLI, weekly run, Sicherheit + Auffindbarkeit + Tempo (§3.1–3.3), card with lights and points | the oaap-test instances and two of our own sites show plausible points; the page statistics show the check as an automaton |
| 2 | Recht (§3.4), `site.check` notification through `site_watch`, weekly report line, „neu / behoben“ | a red point opens and closes a matter on oaap-test |
| 3 | More than the start page: up to 10 URLs from the sitemap (broken internal links, missing titles per page), history of 12 runs as a small chart | a planted broken link is found |

## 8. Tests and measurement

- Unit: each rule on a fixture page (HTML + headers) — green, yellow, red,
  and the „fixes“ party; the fetch limits (30 assets, 5 MB, 5 redirects);
  only production and switched on; the weekday spread.
- Gateway: the check's User-Agent is counted as an automaton, never as a
  visit (`site_stats`).
- Measured on oaap-test per stage; on a tenant's site only after its
  administrator switched the check on, and then only by the check itself.

## 9. Non-goals

- A score or a ranking. Points with a sentence, not a number.
- A scanner: no attempt at a vulnerability, no secret paths, no forms
  sent, no login.
- Rendering with a browser (JavaScript executed, Core Web Vitals). Heavy
  (a headless Chromium per node) and the start page's HTML answers most
  questions; revisit if a site is pure client-side rendering and the check
  sees nothing.
- Legal judgement. Hints only.
- The extensions of I-83 idea 4 — a watch for certificate, domain and DNS
  between runs, SPF/DKIM/DMARC of the tenant's domain, an accessibility
  baseline, a status page per tenant — each its own RFC when wanted.

## 10. Decisions

*Decided 2026-11-28 by Jörg: D1–D7 all as recommended.*

- **D1 — Where does the check run?** Recommended: **on the node itself**
  (§5), grey where the hairpin fails. Alternative: from another fleet node
  from the start — truer, but needs the fleet's trust path for a new kind
  of request and leaves single nodes (Bernd) without a check.
- **D2 — Its own switch, or part of „Hinweise zur Webseite“?**
  Recommended: **its own switch** `site_check` (seeing points in the
  portal is wanted more often than mails), and **mails only through
  `site_watch`**. Alternative: one switch for both.
- **D3 — Who may switch it on?** Recommended: **the instance's
  `tenant_admin` and the `server_admin`**, as `site_watch`.
- **D4 — Default for a new production instance?** Recommended: **off**
  — the tenant decides whether the node reads their site. Alternative: on
  for an instance whose app is a web site (`website-starter`), since only
  its own node reads it.
- **D5 — The Recht area at all?** Recommended: **yes, as hints** with the
  sentence „keine Rechtsberatung“ — imprint, privacy and Google Fonts are
  the three things a German club gets letters about. Alternative: leave it
  out.
- **D6 — Rhythm.** Recommended: **weekly plus the button** (once an hour).
  Alternative: daily — cheap too, but a site changes rarely and a daily
  mail rhythm is not wanted.
- **D7 — Only the start page in stage 1?** Recommended: **yes**; the
  sitemap's pages in stage 3.

## 11. Stage 0 measured (2026-11-28, reference 0.1.402)

A script of the check (stdlib Python, the rules of §3.1–3.4, the limits
of §2) ran from the nodes against oaap-test's instances and our own
production sites only — no foreign tenant's site.

**M1 — Does a node reach its own public names?**

| Node | Way in | IPv4 | IPv6 |
|---|---|---|---|
| oaapx01 | direct | 303/200 in ≈ 23 ms | no AAAA record |
| oaap-test (.96) | behind edge .75 | 303 in 0.09 s (router loops back) | hits the router itself, see M2 |
| oaap-demo (.75) | edge | 303 in 0.08 s | same |
| oaap-bernd (.95) | own port forwarding | 303 in 0.15 s | same |
| raspberrypi | no external name | — | — |

The loop back works on every node with web sites — D1 holds; „grey“
stays for a router that does not loop back.

**M2 — IPv6 points at the router (finding outside this RFC).** The
`duckdns` names and `projects.joomp.de` carry an AAAA record
`2003:fd:f7ff:5a0:…:e2f0` — the FRITZ!Box's own WAN address. From inside
the LAN it answers 443 with its own remote-access certificate
(`fritz.box`, `myfritz.net` …), so curl, which tries IPv6 first, failed
with „self-signed certificate“ before the cause was found. From outside
(oaapx01 over IPv6) the connection is **refused** within 35–190 ms, so a
browser falls back to IPv4 and a visitor sees a short delay at most.
Consequences for the check: probe **A and AAAA separately**; behind an
edge the node judges IPv4 only and says „IPv6 von hier nicht prüfbar“;
an AAAA that refuses from outside is a real yellow point („IPv6-Eintrag
zeigt ins Leere“), visible only from another node (§5, later). The record
itself is the router's DynDNS — Jörg's to decide.

**M3 — Cost of one run.**

| Site | Requests | Seconds | Transferred |
|---|---|---|---|
| `bdt.vuebung…` (oaap-test, 50 own assets, 30 fetched) | 34 | 9.5 | 1.3 MB |
| `projects.joomp.de` (Forgejo) | 11 | 2.8 | 0.5 MB |
| `market-test…` / `market.oaap-web…` | 8 / 6 | 2.1 / 1.4 | 10 / 7 KB |
| `go.joomp.de` | 4 | 0.9 | 1 KB |

Within §2's limits; a weekly run is no load.

**Findings that change stage 1 (no decision needed):**

- **F1 — Most production instances are apps, not web sites.** BDT,
  the marketplace and the short-link service get seven yellow
  „Auffindbarkeit“ points each (no robots.txt, sitemap, canonical,
  description, og:image, og:url, structured data), and `go.joomp.de`
  gets a red `noindex` it sends on purpose. The switch already means
  „this is a web site“ (D4: off by default), but the card must not drown
  the few points that matter: points of one area and one fixer are
  **grouped** into one line with the details folded („Für Suchmaschinen
  kaum vorbereitet: 7 Punkte“), red always unfolded.
- **F2 — `no-transform` is the app's choice.** `projects.joomp.de`
  sends its HTML uncompressed although the site has `encode`: Forgejo
  answers `Cache-Control: … no-transform` and Caddy obeys. The check
  reads the header and says „die App verbietet Umformung“, fixer
  **Seite**, never „Plattform“.
- **F3 — The check counts as a visitor today.** `site_stats.bot_of`
  knows no needle in `OAAP-Seiten-Check/…`, so the stage-0 runs were
  counted as page views (63 requests on five sites). Stage 1 adds the
  check to `BOTS` as kind `other`, with a test.
- **F4 — „TLS 1.0/1.1 accepted“ is measurable, but only one way.**
  Python's `ssl` with `SECLEVEL=0` offers TLS 1.0/1.1 (OpenSSL 3.5.9 on
  oaapx01) and gets the **server's** alert `protocol version` — a real
  „not accepted“. `openssl s_client -tls1_1` with the system's default
  configuration fails on the client („no protocols available“) and
  proves nothing. The check keeps the probe and tells the two apart: a
  server alert = green, a client-side error = grey („von hier nicht
  prüfbar“), never green.
- **F5 — Our own apps announce their versions.** `server:
  marketplace/0.5.2 Python/3.13.18`, `oaap-wegweiser/0.6.2 …` — a yellow
  point under D8 (informative); worth a line in those apps, not in the
  platform.

All rules gave plausible answers otherwise: certificates 50–89 days,
TLS 1.3, HSTS/`nosniff`/Referrer present everywhere (RFC-0140),
Tempo green on BDT (1.3 MB gzip), `og:image` relative on Forgejo found.

## Deutsche Zusammenfassung

Anlass: Die Prüfung von `sglok-sbk.de` fand Lücken, die der Mieter selbst
nicht sieht. Was die Plattform beheben kann, hat RFC-0140 erledigt. Was
Sache der Seite ist (Canonical-Link, strukturierte Daten, Bildgrößen, CSP,
Impressum/Datenschutz erreichbar, Google Fonts ohne Einwilligung), muss
der Mieter **erfahren** — heute sagt es ihm niemand.

Vorschlag: ein **Seiten-Check** je Produktivinstanz, vom Mandanten-Admin
eingeschaltet. Einmal pro Woche und auf Knopfdruck liest der Knoten die
Startseite wie ein Browser (Startseite, ihre eigenen Skripte/Styles/Bilder,
`robots.txt`, Sitemap, die Umleitungen — ein paar Dutzend Anfragen, einzeln
nacheinander, mit ehrlicher Kennung). **Nur lesen, nie probieren:** keine
Geheimpfade, keine Last, keine gefälschte Kennung.

Ergebnis im Reiter „Seitenstatistik“: eine **Ampel in vier Bereichen**
(Sicherheit, Auffindbarkeit, Tempo, Recht). Jeder Punkt sagt, was gefunden
wurde, warum es zählt, und **wer es behebt** — ein Schalter der Plattform
(mit Link) oder der Autor der Seite. Rot nur, wo es jetzt schadet
(Zertifikat läuft ab, `noindex` auf Produktion, Seite ohne https), alles
andere gelb. Recht ausdrücklich als Hinweis, keine Rechtsberatung. **Mail
nur über den vorhandenen Schalter „Hinweise zur Webseite“**, und nur bei
einem neuen roten Punkt.

Der Check läuft auf dem Knoten selbst gegen den öffentlichen Namen; hinter
einem Edge braucht das die Rückschleife des Routers (wird in Stufe 0 je
Knoten gemessen; geht sie nicht, ist das Ergebnis grau statt rot). Später
kann ein anderer Flottenknoten von wirklich außen prüfen.

Stufen: 0 Messung (Rückschleife, Skript gegen oaap-test und unsere eigenen
Seiten, nie gegen fremde Mieter), 1 Schalter + Sicherheit/Auffindbarkeit/
Tempo + Karte, 2 Recht + Mail + Wochenbericht, 3 Unterseiten aus der
Sitemap und Verlauf.

Entschieden 28.11.2026 von Jörg: D1–D7 alle wie empfohlen -- auf dem Knoten selbst; eigener
Schalter, Mail über „Hinweise“; Mandanten-Admin und Server-Admin dürfen;
Vorgabe aus; Recht als Hinweis ja; wöchentlich plus Knopf; erst nur die
Startseite.

Stufe 0 gemessen (28.11.): Die Rückschleife über den Router klappt auf
allen Knoten mit Webseiten (oaapx01 direkt, oaap-test/oaap-demo/oaap-bernd
über IPv4). Ein Lauf kostet 4–34 Anfragen, 1–10 s, höchstens 1,3 MB.
**Nebenbefund:** Die duckdns-Namen und `projects.joomp.de` haben einen
IPv6-Eintrag auf die Fritzbox selbst -- von innen antwortet ihr
Fernzugang mit eigenem Zertifikat, von außen wird abgelehnt und der
Browser weicht auf IPv4 aus. Das ist Sache der Fritzbox/DynDNS (Jörg).
Befunde für Stufe 1: (F1) die meisten Produktivinstanzen sind Apps, keine
Webseiten -- gleichartige Punkte werden zusammengefasst, Rot bleibt
offen; (F2) `no-transform` der App (Forgejo) erklärt fehlende
Kompression, Behebung „Seite“; (F3) die Seitenstatistik zählt den Check
heute als Besucher -- wird in die Automatenliste aufgenommen; (F4)
TLS 1.0/1.1 ist mit Python messbar, Fehler auf Client-Seite = grau;
(F5) unsere eigenen Apps nennen ihre Versionen im `Server`-Header.

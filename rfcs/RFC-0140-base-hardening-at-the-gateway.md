# RFC-0140: Base Hardening at the Gateway — Compression, Headers, One Address

- **Status:** **Accepted (2026-11-27)** — D1–D8 decided by Jörg, all as
  recommended (§10). **Stage 0 measured 2026-11-27 on oaap-test (§11)**;
  D9 (finding F1, the brake counts per worker) decided 2026-11-27 as
  recommended: fixed in stage 1. **Stage 1 built and measured 2026-11-27
  (§12)**: reference 0.1.400, `oaap.core.gateway` 0.2.28. **Stage 2 built
  and measured 2026-11-27 (§13)**: reference 0.1.401, gateway 0.2.29.
  **Stages 1 and 2 on the fleet 2026-11-28** (all nodes but oaapx02).
  **Stage 3 built and measured 2026-11-28 (§14)**: reference 0.1.402,
  gateway 0.2.30.
- **Date:** 2026-11-27
- **Authors:** Jörg (the need: look at `sglok-sbk.de`, a tenant's page made
  with the deploy-URL procedure, as Google, as a visitor and as an attacker
  would; „Ja, RFC entwerfen“ for what the platform should fix), Claude
  (measurement from outside, design)
- **Depends on:** RFC-0009/0018 (canonical name and aliases), RFC-0084
  (secret files refused at the gateway — the pattern of a site-level block
  written for every instance), RFC-0006 (the edge terminates TLS), I-81
  (the website mode: noindex per channel, AI fetchers, site statistics),
  RFC-0130 (security reports)
- **Changes (when accepted):** `oaap.core.gateway` (a section „Base
  hardening“), the instance record (three switches), the CLI, the portal's
  instance page

## Summary

Every instance site the gateway writes passes the app's answer to the
visitor as the app wrote it. On 2026-11-27 a look at `sglok-sbk.de`
(reference 0.1.399) showed what that costs a tenant who did not think of
it: JavaScript and CSS travel **uncompressed** (≈ 450 KB instead of
≈ 130 KB), the answer carries **no security header** at all, and
`www.sglok-sbk.de` — an alias — serves the **same page with 200** instead
of sending the visitor to the canonical name, which search engines count
as duplicate content. `TRACE /` reaches the app and ends in a 500.

None of this is the tenant's fault, and none of it needs the tenant: the
gateway can do it once, for every instance, the way it already refuses
secret files (RFC-0084). This RFC adds four things to the one body every
instance site shares (`site_body`):

1. **Compression** (`encode zstd gzip`) — skipped where the app already
   compressed.
2. **A small set of base headers**, set only where the app set none.
3. **An alias may redirect** (301) to the canonical name instead of
   serving — a switch per instance.
4. **TRACE, TRACK and CONNECT are refused** at the gateway.

Each is on by default and can be switched off per instance, because an app
may have a reason the platform does not know.

## 1. What was measured (2026-11-27, from outside, reading only)

| Probe | Answer | Who should fix it |
|---|---|---|
| `Accept-Encoding: br, gzip` on `/` | HTML 117 KB → 16 KB brotli — the **app** compresses | — |
| same on `framework-*.js`, `index-*.js`, `index-*.css` | 190 KB, 185 KB, 70 KB, no `Content-Encoding` | platform |
| security headers on `/` | none of HSTS, `X-Content-Type-Options`, `Referrer-Policy`, CSP, `frame-ancestors` | platform (base), tenant (CSP) |
| `https://www.sglok-sbk.de/` | 200, same page; `og:image` points at www, sitemap at the apex | platform (switch), tenant (canonical link) |
| `TRACE /` | 500 „Internal Server Error“ from the app | platform |
| `/.env`, `/.git/HEAD`, `/.git/config`, `/docker-compose.yml` | 404, 9 bytes, from the gateway | RFC-0084 works |
| TLS | 1.2 and 1.3 only, Let's Encrypt, valid until 2027-02-25 | works |
| unknown SNI on the node's address | no TLS handshake | works |

The code confirms it: no `encode` and no `Strict-Transport-Security`
anywhere in the gateway generator; the only security header written today
is the `frame-ancestors` of an MCP App's sandbox origin (RFC-0075 D6).

Not probed (left for stage 0 on oaap-test, on purpose not against a
tenant's production site): the brake under many requests (RFC-0010), the
AI-fetcher switch (0.2.27), forged identity headers on public routes.

## 2. Compression

`encode zstd gzip` at site level in `site_body`, so every route of every
entry point (LAN port, automatic name, own names, aliases) gets it.

- Caddy does not encode an answer that already carries `Content-Encoding`
  — an app that compresses itself (as this one does for HTML) is
  untouched, its brotli wins.
- Caddy's defaults decide what is compressed (text, JSON, JS, CSS, SVG …;
  not images or video) and leave out answers under 512 bytes.
- WebSocket upgrades are not touched.
- **Risk to measure:** streamed answers (`text/event-stream` of the chat,
  the AI gateway, MCP's streamable HTTP). Caddy flushes the encoder on
  every flush of the upstream, so streams should keep coming in pieces;
  stage 0 measures it with the chat before anything else. If it does not
  hold, `text/event-stream` is excluded by a `match` block — never the
  whole feature.

Brotli is not in the standard Caddy build; zstd and gzip are. A custom
build for brotli is a non-goal (§9): gzip already takes JS from 190 KB to
about 55 KB.

## 3. Base headers

Set with Caddy's `?` prefix — **only when the app did not set the header
itself**. An app that knows better keeps its own value.

| Header | Value | Where | Why this value |
|---|---|---|---|
| `Strict-Transport-Security` | `max-age=31536000` | sites the visitor reaches over https (own names, aliases, automatic names; behind an edge too, since the edge speaks https to the browser); never a LAN `http://` port | without `includeSubDomains` and `preload`: the tenant owns the domain and decides about its other names |
| `X-Content-Type-Options` | `nosniff` | every site | stops a browser from running an upload as script |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | every site | the browsers' default today; written for older ones and so a scan sees it |

Deliberately **not** in the base set, because a wrong default breaks an
app without anybody seeing why:

- `Content-Security-Policy` — depends on what the app loads; the app's
  business (a later Seiten-Check tells the tenant).
- `frame-ancestors` / `X-Frame-Options` — the portal, the chat (MCP Apps)
  and tenants' own pages may frame an instance on purpose. D4 asks whether
  `'self'` plus the instance's own names becomes a default later.
- `Permissions-Policy` — LiveKit, the video service and the chat's
  microphone need camera and microphone.

## 4. An alias that redirects

RFC-0018 made every alias a front door that serves. For a website that is
the wrong answer: two addresses, one content, and the search engine picks
one itself. New switch on the instance record:

- `aliases: serve | redirect` — `serve` is today's behaviour; `redirect`
  writes each alias site as `redir https://<canonical>{uri} permanent`
  (301). The canonical name is unchanged and keeps every protection.
- Certificates: each alias keeps its own site and certificate (ACME is
  answered by Caddy before any route), so a visitor of
  `https://www.…` gets a valid certificate and then the redirect.
- `OAAP_INSTANCE_NAMES` (RFC-0043) still lists the aliases after the
  canonical name; an app that builds a canonical link takes the first.
- The automatic node name (`<instance>.<tenant>.<node>`) is not an alias
  and keeps serving — operators and the portal reach the instance there.
- The site statistics (I-81) count a redirected alias as a redirect, not
  as a page view.

## 5. Methods no app needs

`@oaap_method method TRACE TRACK CONNECT` → `respond 405` at site level.
Nothing else: WebDAV apps (Nextcloud, BookStack's file side) need
`PROPFIND`, `MKCOL` and friends, so the gateway does not keep a list of
allowed methods.

## 6. Switches, CLI, portal, migration

- Instance record: `hardening: {"compress": true, "headers": true}` and
  `aliases: "serve" | "redirect"`; absent = the defaults of D1–D3.
- CLI:
  `oaap app hardening <instance> [--compress on|off] [--headers on|off]`
  and `oaap app address aliases <instance> serve|redirect`; both rewrite
  the instance's site and reload the gateway; `show` prints the state.
- Portal: on the instance page next to „KI-Abrufer“ and „Suchmaschinen“,
  three switches with one sentence each; `tenant_admin` for the alias
  switch (it is about the tenant's address), `server_admin` for the other
  two.
- Migration `cmd_migrate_hardening`, modelled on `cmd_migrate_guard`:
  rewrites every instance site, idempotent, silent when nothing is to do,
  one line in the update output.
- Methods (§5) have no switch: there is no app that needs TRACE.

## 7. Stages

| Stage | Content | Done when |
|---|---|---|
| 0 | Measure on oaap-test: the probes of §1 not run, plus chat streaming, WebSocket, an app that compresses itself, and `nosniff` against every app of the fleet's store (does any serve JS with a wrong type?) | a table in this RFC |
| 1 | Compression + methods (§2, §5), switch `compress`, migration | `sglok-sbk.de` JS with `Content-Encoding`, `TRACE` → 405 |
| 2 | Base headers (§3), switch `headers` | HSTS/nosniff/Referrer on every https site, app values kept |
| 3 | Alias redirect (§4), CLI + portal | `www.sglok-sbk.de` → 301 after the tenant switched it |

## 8. Tests and measurement

- Generator tests: every entry point of an instance carries `encode`, the
  method block and the header block exactly once; a switched-off instance
  carries none; LAN `http://` sites carry no HSTS; a rehearsal and a
  sleeping instance keep their own rules.
- An alias with `redirect` produces a site with nothing but the redirect;
  the canonical site is unchanged byte for byte.
- On oaap-test: chat answer streams in pieces with `encode` on
  (time to first token compared with off); an app's own `Content-Encoding`
  passes unchanged; an app's own `Strict-Transport-Security` is not
  overwritten.

## 9. Non-goals

- A Content-Security-Policy written by the platform.
- Brotli through a custom Caddy build.
- Image conversion at the edge (AVIF/WebP) — a later idea.
- A list of allowed HTTP methods.
- `/.well-known/security.txt` per instance — belongs with RFC-0130's
  contact, D7 decides whether it comes later.
- Removing framework fingerprints (`X-Nextjs-Cache`, `X-Vinext-Cache`,
  `Via`) — little gain, D8.

## 10. Decisions

Decided 2026-11-27 by Jörg: **all as recommended**.

- **D1 — Compression on by default?** Recommended: **yes, for every
  instance**, switch off per instance. Alternative: only for new instances
  — leaves the fleet as slow as today.
- **D2 — Base headers on by default?** Recommended: **yes**, only where the
  app set none, after stage 0 found no app that breaks with `nosniff`.
- **D3 — Default of the alias switch?** Recommended: **`serve` for
  existing instances, `redirect` for an alias added from this version on**
  — nobody's site changes behaviour on an update, and the next `www` is
  right from the start.
- **D4 — `frame-ancestors` in the base set?** Recommended: **no, not now**;
  revisit with the Seiten-Check, which can tell the tenant.
- **D5 — HSTS lifetime?** Recommended: **one year without
  `includeSubDomains`/`preload`**. Alternative: six months for a start.
- **D6 — Who may flip the switches?** Recommended: **alias switch
  `tenant_admin`, compression and headers `server_admin`**.
- **D7 — `security.txt` from the platform?** Recommended: **later**, with
  RFC-0130's contact address, as a default an app's own file overrides.
- **D8 — Strip framework fingerprint headers?** Recommended: **no** —
  attackers find the framework from the page anyway; the Seiten-Check
  wants to read it.

- **D9 — Fix F1 (brake counts per worker)?** *(Added after stage 0;
  decided 2026-11-27 by Jörg as recommended.)* Recommended: **yes, in
  stage 1** — the buckets in one place all workers share (a small SQLite
  file in identity's data volume, or `/dev/shm`), measured again with the
  700-request probe (first 429 at 301). Alternative: divide the limit by
  the worker count — quick, but wrong the day the count changes.

## 11. Stage 0 measured (2026-11-27, oaap-test, 0.1.399)

From the LAN through the gateway's instance ports (the same `site_body` as
every external name), so every answer passed the real rules. Temporary
changes were made by hand on oaap-test only and taken back the same hour:
`vuebung-bdt.caddy` restored from its copy and the gateway reloaded, the
SSE test container removed, the AI switch set back to `allow`.

| # | Question | Measured | Result |
|---|---|---|---|
| M1 | Compression gain | `vuebung-bdt` (public, 50 files): 5 407 267 bytes without; with `encode zstd gzip` in its site 1 616 503 (gzip) / 1 514 069 (zstd) | **−70 %**; HTML 99 KB → 23 KB |
| M2 | Streams with `encode` | a test SSE responder behind the same site, 5 events 1 s apart, 600 bytes each | gzip: events at 0.00 / 0.99 / 2.02 / 3.03 / 4.01 s — same as uncompressed; **no exclusion of `text/event-stream` needed** |
| M3 | App compresses itself | `forgejo`, `ws375-git`: 8 assets already `gzip` | untouched by design (Caddy skips an encoded answer); see stage 1 test |
| M4 | `nosniff` and wrong types | every public page of the 51 instances and its scripts/styles: 20 assets on 3 public instances | **0 wrong types**; 3 instances already send `nosniff` themselves. Login-protected apps (48) not covered — stage 2 checks them in a signed-in browser (console shows a `nosniff` refusal) |
| M5 | Methods | `TRACE` 405 (this app), `TRACK` 400, `CONNECT` **502** (gateway hands it to the app), `PROPFIND` 405 | §5 needed: today the answer depends on the app (sglok: 500) |
| M6 | AI fetchers (0.2.27) | `oaap app ai-fetchers vuebung-bdt all` | GPTBot, ClaudeBot, CCBot 403; Googlebot, Firefox 200; robots.txt from the platform; back to `allow` → GPTBot 200 again. **Works** |
| M7 | Forged identity headers | static: all 56 generated site files, every `handle` that proxies to an app or the portal (1 045) either passes `forward_auth … /verify` with `copy_headers` or strips `X-OAAP-User/Roles/User-Id/Email`; live: `X-OAAP-User`, `-Groups`, `-Roles` on a public route change nothing (same 99 216 bytes), on a protected one → 303 to the login | **Works**, no gap |
| M8 | Brake (RFC-0010), default 300 per 60 s | 700 requests in 58 s on one route of `vuebung-bdt` from one address | **first 429 at request 594** — see F1 |
| M9 | WebSocket with `encode` | not measured (no public WebSocket on oaap-test); Caddy does not encode a 101 upgrade | stage 1 test with the chat |

**F1 — the brake lets twice the limit through.** identity runs
`gunicorn --workers 2` and keeps the buckets in a per-process dict
(`_RATE`); each worker counts only the requests it got, so a client reaches
≈ 2 × limit before the first 429. RFC-0084's scanner was stopped „after
about 730 requests“ — the same effect. Not part of §2–§5, but found here
and cheap to fix: D9.

## 12. Stage 1 built and measured (2026-11-27, reference 0.1.400)

Built: `harden_site_lines` in the body every entry point shares —
`encode zstd gzip` unless the instance's `hardening.compress` is `false`,
and `TRACE TRACK CONNECT` rewritten to `/.oaap-method-refused` → 405, first
of all rewrites; `oaap app hardening <instance> [--compress on|off]`;
`migrate-hardening` in the update; the switch survives a redeploy. identity:
the brake's buckets in one SQLite file in `/dev/shm` (named after
identity's data directory) shared by both gunicorn workers, one
`BEGIN IMMEDIATE` transaction per hit, a fallback to the worker's own
memory if the file fails. `oaap.core.gateway` 0.2.28 (sections „Base
hardening“, „Public-route throttling“). Tests: `test_base_hardening` new
(26 checks, both workers on one file included); `test_rehearsal_shape`
exempts the 405 block like the guard's; the 45 files that generate sites
or touch the brake green except `test_diagnose` and `test_instance_page`,
red already before this change (portal template expects `i.ai` since
0.1.397).

Measured on oaap-test after staging 0.1.400 (the update's migration
rewrote `vuebung-bdt.caddy` and `external.caddy`, 50 `encode` lines):

| Probe | Before (stage 0) | After |
|---|---|---|
| `vuebung-bdt`, 50 files, first visit | 5 407 267 bytes | 1 616 548 (gzip) / 1 514 069 (zstd) |
| `forgejo` assets, the app compresses itself | `gzip` | `gzip`, unchanged |
| `TRACE` / `TRACK` / `CONNECT` | 405 (app) / 400 / 502 | 405 / 405 / 405, empty body from the gateway |
| `PROPFIND`, `OPTIONS` | reach the app | still reach the app (its 18-byte answer) |
| brake, 700 requests in 61 s on one route | first 429 at 594 | **first 429 at 292** (≈ 9 requests to the same route a minute before) |
| status of `/` on all 50 instances | — | identical to before |
| identity log „shared brake unavailable“ | — | 0; the file in `/dev/shm` 4 MB (WAL) of 64 MB |

Not measured: WebSocket through `encode` (no public WebSocket on
oaap-test) — Caddy does not encode a 101 upgrade; the chat is checked when
the fleet is updated. Not on the fleet yet.

## 13. Stage 2 built and measured (2026-11-27, reference 0.1.401)

Built: `header_site_lines` inside `harden_site_lines`, so every entry
point has it --
`header @oaap_tls ?Strict-Transport-Security "max-age=31536000"` with
`@oaap_tls protocol https`, the same line again with
`@oaap_edge_tls header X-Forwarded-Proto https` (behind an edge only the
edge's header is believed, `write_edge_trust`; two matchers instead of a
CEL expression -- both set with `?`, the first wins),
`header ?X-Content-Type-Options nosniff`,
`header ?Referrer-Policy strict-origin-when-cross-origin`. Switch
`hardening.headers` with `oaap app hardening <instance> --headers on|off`
(one switch per call, independent of `compress`); `migrate-hardening`
also rewrites sites from stage 1. Gateway 0.2.29. Tests:
`test_base_hardening` 41 checks; the 34 files that generate sites green
except `test_diagnose` (red before, `i.ai`).

Measured on oaap-test after staging 0.1.401 (the update rewrote the
sites, 100 `nosniff` lines in 50 instance files and `external.caddy`):

| Probe | Result |
|---|---|
| all 50 instance LAN ports | `nosniff` exactly once on 50/50, `Referrer-Policy` once on 50/50, no HSTS on plain http (except `auth`, Keycloak's own) |
| status of `/` on all 50 | identical to stage 1 |
| an app's own values | `auth` (Keycloak) keeps `max-age=31536000; includeSubDomains` and `no-referrer` -- not overwritten, not doubled |
| HSTS through the edge | `https://bdt.vuebung.oaap-test…/` → `Strict-Transport-Security: max-age=31536000`, `nosniff`, `Referrer-Policy`; `http://` → the edge's 301 without HSTS |
| `/platform/app.js`, `theme.css` (from the gateway) | `text/javascript` / `text/css` with `nosniff` |
| M4 open from stage 0: `nosniff` behind the login | every instance's own container with signed-in identity headers: 39 scripts and styles on 8 apps, **0 wrong types** (the other apps load none from their first page, or only the platform's two files; `ws375-wiki` sends to Keycloak first, not covered) |

Not measured: a browser console per app behind the login (the type
check above is what `nosniff` acts on).

## 14. Fleet for stages 1 and 2, stage 3 built and measured (2026-11-28)

**Fleet (0.1.401):** oaap-test, raspberrypi, oaap-bernd, oaap-demo and
oaapx01, each backed up first, then `oaap update` from Git. oaapx02 is
not touched by us; `sglok-sbk.de`, the site that started this RFC, lives
there, so its own measurement waits for that node. Before/after over
every public name of oaap-demo (17) and oaapx01 (83): no status changed
(studio on oaap-demo answers again, it timed out before). Reading only,
from outside: `market.oaap-web…`, `app.bdt…`, `team.bdt…` and
`projects.joomp.de` send HSTS, `nosniff` and `Referrer-Policy`, the
first three `Content-Encoding: zstd`.

**M9, WebSocket through `encode` (open since stage 0):** a temporary
site on oaap-test's gateway with exactly `harden_site_lines` in front of
Uptime Kuma's socket.io, removed afterwards: with and without
`Accept-Encoding: zstd, gzip` the upgrade answers `101 Switching
Protocols` without `Content-Encoding`, and the first frame is a plain text
frame (`0{"sid":…`) after 3–8 ms. `encode` leaves upgrades alone.

**Stage 3 built:** the record's switch is `alias_mode` -- the RFC's
working name `aliases` is already the alias list. `alias_redirect_site`
writes the alias's own site with the edge guard (behind an edge), the
access log and `redir https://<canonical>{uri} permanent` inside a
`handle`; in direct mode `http://<alias>` goes to the canonical https
name in one hop. Absent = `serve`; an instance's first alias from 0.1.402
on stores `redirect` (D3); an explicit `serve` is stored and kept.
`oaap app address aliases <instance> serve|redirect`, the portal's
button in the „Aliasse“ card (spool op `alias-mode`), audit
`instance.aliases`, kept by an update. Tests: `test_base_hardening`
57 checks, `test_gates` knows the gate line.

Measured on oaap-test (behind edge 10.10.10.75), with temporary names on
`vuebung-bdt`, removed afterwards:

| Probe | Result |
|---|---|
| first alias added | stored `redirect`, CLI says so; `show` prints „Aliases: redirect (301)“; `OAAP_INSTANCE_NAMES` still lists the alias |
| alias from the edge, `/foo?x=1` | `301`, `Location: https://s3probe.example/foo?x=1` |
| alias not from the edge | first build: **301** -- Caddy orders a bare `redir` before `handle`, so the guard's 403 came too late (no secret leaks, but the edge rule must hold); fixed by the `handle` above, then **403** |
| canonical name from the edge | `200` with HSTS and `nosniff`; the automatic node name `200` from outside |
| switch to `serve` | no redirect line left, alias `200` |
| access log | the alias's 301 and 403 are logged (the site statistics count neither as a page view) |
| audit | two `instance.aliases` lines with tenant and subject |

**Found on the way (not RFC-0140):** the update said „external.caddy
rewritten … identity headers“ on every run since 0.1.383 -- the
staleness check of RFC-0040's migration did not know the gate block's
`copy_headers` line (RFC-0135) nor the coupling door's own strips
(RFC-0136), so it rewrote the file and reloaded the gateway every time.
Fixed in 0.1.402 (`_COPY_GATE`, `COUPLE_HEADERS` excluded); two stagings
in a row on oaap-test: silent.

Not measured: the portal button clicked in a real browser.

## Deutsche Zusammenfassung

Anlass: Die Vereinsseite `sglok-sbk.de` läuft gut, aber unser Gateway
reicht die Antwort der App ungeschützt und ungepackt durch. JS und CSS
gehen unkomprimiert raus (≈ 450 KB statt ≈ 130 KB), es gibt keinen
einzigen Sicherheits-Header, `www.sglok-sbk.de` zeigt dieselbe Seite statt
weiterzuleiten (für Google doppelter Inhalt), und `TRACE` bringt die App zu
einem Fehler 500. Der Geheimdatei-Wächter (RFC-0084) und TLS wirken.

Vorschlag — einmal im Gateway, für alle Instanzen, je Instanz abschaltbar:

1. **Kompression** (`encode zstd gzip`); Apps, die selbst packen, bleiben
   unberührt. Risiko Streaming (Chat) wird zuerst gemessen.
2. **Grund-Header** HSTS (1 Jahr, ohne Subdomains), `nosniff`,
   `Referrer-Policy` — nur, wo die App selbst keinen setzt. CSP,
   Einbett-Schutz und Kamera/Mikro-Regeln bewusst nicht, weil sie Apps
   brechen können.
3. **Alias als Weiterleitung**: Schalter `serve | redirect`; bei `redirect`
   leitet z. B. www per 301 auf den Hauptnamen.
4. **TRACE/TRACK/CONNECT** am Gateway mit 405 abweisen.

Stufen: 0 Messung auf oaap-test (auch die heute nicht gemachten Proben zu
Drosselung, KI-Abrufer, gefälschten Headern), 1 Kompression + Methoden,
2 Header, 3 Alias-Weiterleitung mit CLI und Portal.

Entschieden 27.11.2026 von Jörg: D1–D8 alle wie empfohlen, u. a. Kompression und Header für alle,
Alias-Weiterleitung nur für neue Aliase als Vorgabe (bestehende Seiten
ändern sich beim Update nicht).

Stufe 0 gemessen (27.11., oaap-test): Kompression spart 70 % (5,4 MB →
1,6 MB), Streams (SSE) kommen weiter im Sekundentakt, keine falschen
Inhaltstypen auf öffentlichen Seiten (angemeldete Apps prüft Stufe 2),
KI-Abrufer-Schalter und Schutz der Identitäts-Header wirken lückenlos.
**Befund F1:** Die Drosselung lässt doppelt so viel durch (erste 429 bei
Anfrage 594 statt 301), weil die zwei Identity-Prozesse getrennt zählen.
D9 entschieden (27.11., wie empfohlen): F1 wird in Stufe 1 mit einem
gemeinsamen Zähler behoben.

Stufe 1 gebaut und auf oaap-test gemessen (0.1.400, gateway 0.2.28): jede
Instanzseite komprimiert (vuebung-bdt 5,4 → 1,6 MB, Forgejo packt weiter
selbst), TRACE/TRACK/CONNECT bekommen 405 vom Gateway, PROPFIND/OPTIONS
gehen weiter an die App, Schalter `oaap app hardening <instanz> --compress
off`. Die Bremse zählt in einer gemeinsamen Datei: erste 429 jetzt bei
Anfrage 292 statt 594. Noch nicht auf der Flotte.

Stufe 2 gebaut und auf oaap-test gemessen (0.1.401, gateway 0.2.29): HSTS
(nur über https, auch hinter dem Edge), `nosniff` und `Referrer-Policy` auf
jeder Instanzseite, nur wo die App keinen eigenen Wert setzt (Keycloak
behält seine). Alle 50 Instanzen gleicher Status, 0 falsche Inhaltstypen
auch bei Apps hinter dem Login (39 Dateien, 8 Apps). Schalter
`--headers off` je Instanz. Noch nicht auf der Flotte.

28.11.: Stufen 1 und 2 auf der Flotte (alle Knoten außer oaapx02, dort
liegt sglok-sbk.de); keine öffentliche Adresse hat ihren Status
geändert, Header und Kompression von außen bestätigt. WebSocket durch
`encode` gemessen: unverändert. Stufe 3 gebaut und gemessen (0.1.402,
gateway 0.2.30): Aliasse können mit 301 auf den Hauptnamen umleiten,
Schalter `alias_mode` (bestehende liefern weiter aus, der erste Alias ab
jetzt leitet um), CLI `oaap app address aliases`, Knopf im Portal. Dabei
gefunden und behoben: der Edge-Wächter griff bei der Umleitung zu spät,
und eine Migration schrieb seit 0.1.383 bei jedem Update `external.caddy`
neu.

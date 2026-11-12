# RFC-0084: Secret Files — Refused at the Gateway, Looked For in Every Instance

- **Status:** Accepted (2026-11-12, Jörg: "RFC-0084 schreiben und gleich bauen";
  D1–D6 as recommended); **built (reference 0.1.263, §6)** —
  `oaap.core.gateway` 0.2.22, `oaap.core.notifications` 0.5,
  `oaap.core.portal` 0.3.47
- **Date:** 2026-11-12
- **Authors:** Jörg (the need: "that our gate works is good. But we should also
  make sure our instances do not have these weaknesses at all — look for
  secret files like .env or vercel.json ourselves and report it, and not let
  such requests through even if the files exist"), Claude (design, build)
- **Depends on:** RFC-0010 (the brake), RFC-0083 (who/when counting, the
  weekly report), RFC-0080 (notifications), RFC-0068 (closed networks)

## Summary

On 2026-11-11 a scanner (`TLM-Audit-Scanner/2.0`, one address) sent 3 043
requests in one minute to `market.oaap-web.oaap.joomp.de`, asking for `.env`,
`vercel.json`, `serverless.json`, `.git/config` and similar. The brake stopped
it after about 730 requests; nothing leaked — but only because the app had no
such file. The brake counts, it does not protect a file.

Two layers, one list of paths:

1. **The gateway refuses** a request for a well-known secret path with 404,
   for every instance, before the app is reached — whether the file exists or
   not. Counted like a braked request (who, when; never an address).
2. **The node looks for them**: once a day it asks every running instance
   directly, past the gateway, for the same paths. Real content is a finding —
   a critical notification to the instance's tenant and the node's owners.

## 1. Facts

- Instance sites are written by one function (`site_body`) shared by every
  entry point (LAN port, automatic name, own names, aliases, external site).
- Caddy runs `rewrite` before every `handle` (directive order), regardless of
  how app routes are sorted — a rewrite to a reserved path cannot be
  overtaken by an app route.
- Many apps answer every unknown path with their start page (single-page
  apps): a 200 with HTML. A naive "200 = exposed" check would flag them all.
- Express (CAP) does not serve dot-files by default; `.env` is safest where
  frameworks hide it — but `backup.sql`, `vercel.json`, a key file are served
  like any other file (measured, §6).
- Instances on a closed network (RFC-0068) are not reachable from the host,
  only from the gateway.

## 2. Proposal

### 2.1 The list (categories)

| Category | Paths (end of the path, any prefix, case-insensitive) |
|---|---|
| `env` | `.env`, `.env.*` |
| `vcs` | `.git/…`, `.svn/…`, `.hg/…` |
| `keys` | `id_rsa`, `id_ed25519` …, `.ssh/…`, `*.pem`, `*.key`, `*.p12`, `*.pfx` |
| `cloud` | `.aws/…`, `.npmrc`, `.pypirc`, `.netrc`, `.docker/config.json`, `.git-credentials`, `.htpasswd`, `.htaccess` |
| `deploy` | `vercel.json`, `now.json`, `netlify.json`, `serverless.(json\|yml)`, `docker-compose*.yml`, CI files |
| `php` | `wp-config.php*`, `config.php.bak` …, `*.php~` |
| `dumps` | `*.sql`, `*.sqlite`, `*.db`, `*.dump`, `*.bak` (also `.gz`/`.zip` …) |

Not on the list on purpose: `/config.json` (many single-page apps load their
runtime configuration from it), `/.well-known/…`.

### 2.2 The gateway

Every instance site gets, before everything else:

```
@oaap_guard path_regexp oaap_guard "(?i)(^|/)(…)$"
rewrite @oaap_guard /.oaap-guard
handle /.oaap-guard {
    rewrite * /guard?scope=<instance>
    reverse_proxy identity:8000 { header_up X-OAAP-Client … }
}
```

Identity answers `404 Not found` (no-store) and counts per instance and hour
with the brake's format (distinct clients as keyed hashes, capped at 50;
busiest minute) in `guard-denied.json`.

An instance may be **allowed** a category, by the `server_admin`, with a
reason — `oaap guard allow <instance> <category> --reason "…"` (an app that
offers its export as `.sql`, a CA that hands out its `.pem`). The reason is
in the tenant's log.

### 2.3 The self-check

- Once a day from the minute job (never while a backup copies `apps/`), and
  on demand: `oaap guard scan [instance]`.
- Per running instance (standby skipped): first a random nonexistent path —
  its answer is the instance's "nothing here" signature — then ~20 probe
  paths, plus `.env` and `.git/config` under every declared route prefix.
- Directly to the container on its network; if the host cannot reach it
  (closed network), from inside the gateway.
- A **finding** needs a 200 whose body looks like the file: `NAME=` lines for
  `.env`, `[core]` for `.git/config`, `-----BEGIN … PRIVATE KEY-----`,
  `CREATE TABLE`/`INSERT INTO`, `SQLite format 3`, … — never HTML, never the
  signature of the "nothing here" answer.
- Results in `apps/guard-scan.json` (0644): paths and categories, never
  content.

### 2.4 What follows from a finding

- `exposure.found` — category `critical`, one matter per instance, in the
  tenant's scope **and** the node's; never "only in the report". The text
  names the paths and says what to do: remove the file from the image or
  storage, redeploy, treat credentials in it as known. "Behoben" when the
  next check no longer finds it. An allowed category is listed, not alarmed.
- The health page: card **Geheimnisdateien** (findings; refused requests of
  24 h per instance with "1 Adresse · in 1 Minute").
- The weekly report: refused requests per instance and the findings, a
  finding in bold in the summary.

## 3. Decisions (taken as recommended, 2026-11-12)

- **D1 — refuse at the gateway for every instance**, whether the file exists
  or not, with 404. *Yes.*
- **D2 — the seven categories of 2.1**, `/config.json` deliberately not.
  *Yes.*
- **D3 — exceptions per instance and category, `server_admin` only, with a
  reason.** *Yes.*
- **D4 — a daily self-check past the gateway**; a finding needs content that
  looks like the file. *Yes.*
- **D5 — `exposure.found` is critical**, to tenant and node, never
  report-only. *Yes.*
- **D6 — counting like the brake**, into the health page and the weekly
  report. *Yes.*

## 4. Out of scope

Scanning images and storage for files that are not served (a `.env` in a
container that the app never hands out is the app's business, not an
exposure); blocking clients by address (fail2ban-style); intrusion detection
(its own RFC).

## 6. Built (2026-11-12, reference 0.1.263)

As proposed. The guard sits in `site_body` (every entry point);
`oaap migrate-guard` rewrites the sites written before it, once, at update.

**Measured on oaap-test:**
- update: "37 instance site(s), external.caddy rewritten"; the gateway took
  the configuration; a second update rewrote nothing;
- `wegweiser`: `/api/.env.local` was a login redirect (303) before, 404 after;
  `.env`, `.git/config`, `backup.sql` 404; four refused requests counted, one
  address, one minute; `forgejo` `/` and `/user/login` still 200;
- self-check of 37 instances in 4–6 s: 33 direct, 1 through the gateway
  (`abfl-a`, closed network — found because the first run said "no answer"),
  3 in standby skipped (found: Docker answers "invalid IP" for a stopped
  container — now recognised); no finding;
- a harmless `backup.sql` (`CREATE TABLE probe …`) put into `cap-bookshop`'s
  web root: from outside 404 (the app never saw it); the self-check found
  "ein SQL-Abzug"; **the mail arrived 6 s later** (IMAP) naming instance,
  path and what to do; found and fixed: its link went to `/`, now
  `/instances/cap-bookshop`; file removed → next check → "Behoben" arrived.

## Zusammenfassung (deutsch)

Anlass: Ein Scanner fragte am 11.11. in einer Minute 3 043-mal nach `.env`,
`vercel.json` & Co. Die Bremse griff nach etwa 730 Anfragen; geleakt wurde
nichts — aber nur, weil die Dateien fehlten.

Zwei Schichten, eine Liste:

1. **Das Gateway weist ab:** Anfragen nach `.env`, `.git/`, Schlüsseln,
   Zugangsdateien, Deploy-Konfigurationen, PHP-Sicherungen und
   Datenbank-Abzügen beantwortet es selbst mit 404 — für jede Instanz, ob die
   Datei existiert oder nicht; die App sieht die Anfrage nie. Gezählt wie die
   Bremse. Ausnahmen je Instanz nur durch den server_admin, mit Grund.
2. **Der Knoten sucht selbst:** täglich fragt er jede laufende Instanz direkt
   (am Gateway vorbei) nach diesen Dateien. Nur echter Inhalt zählt (nicht die
   Startseite einer App). Ein Fund ist eine kritische Meldung an den Mandanten
   und die Serverbesitzer, „Behoben“ wenn er weg ist; dazu Gesundheitsseite und
   Wochenbericht.

Gemessen auf oaap-test: 37 Sites umgestellt, eine harmlose `backup.sql` in
einer Test-App war von außen 404, die Selbstprüfung fand sie, die Mail kam
6 s später, nach dem Entfernen „Behoben“.

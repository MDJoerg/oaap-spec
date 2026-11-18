# RFC-0095: The MCP Gateway for the Person — Own Calls, Own Credentials, Readiness

- **Status:** **Accepted (2026-11-18)** — Jörg: "D1–D11 wie empfohlen".
  **Stage 1 built** (mcp-gateway 0.15.0, spec 0.13.0, 2026-11-18):
  `/me`, `/me/v1/calls`, columns `status`/`door`; the realm `sub`
  header of D2 not yet. **Stage 2 built** (mcp-gateway 0.16.0, spec
  0.14.0): procedure U, personal credentials on `/me`. **Stage 3 and
  D2 built** (mcp-gateway 0.17.0, chat 0.7.0, spec 0.15.0, reference
  0.1.307 with `X-OAAP-User-Idp`). Stage 4 (OAuth per person) later.
- **Date:** 2026-11-18
- **Authors:** Jörg (the direction, 2026-11-18, after the first real use in
  the tenant bec: "as a user I don't see the MCP gateway — right for
  maintaining views, but I'd like to see my calls and above all errors;
  later the configuration of set-up MCP servers will live here, e.g. my own
  credentials for Jira; a view for the user: which assistants have tools
  that haven't been set up yet"), Claude (reading of the gateway, design)
- **Depends on:** `oaap.ai.mcp-gateway` 0.11.0 (views, procedures X/I/A/P,
  usage rows with `user_sub`/`user_iss`/`client`, §10 never recorded, the
  vault), RFC-0065 (the gateway), RFC-0066 (propagation; form A),
  RFC-0074 (chat and assistants), RFC-0064 (usage rows, retention stage 4
  not built), RFC-0007 (instance visibility), RFC-0061 (cases — for a
  complaint about a call, later)
- **Not part of this RFC:** the operator side (unchanged, role `admin`);
  feedback on answers in the chat (I-62 W2/W3, its own RFC); OAuth
  authorization of a person at a remote server (named as stage 4, designed
  later)

## Summary

The MCP gateway has one face today: the operator's (`/`, role `admin`).
A person whose calls run through it — from the chat (procedures A and P),
from a client signed in at the tenant's identity provider, from an OAAP
app (procedure I) — sees nothing of it. When a tool fails, the chat shows
the sentence of that one turn; afterwards it is gone, and calls from other
clients (Claude Code, an IDE) are not visible to the person at all.

This RFC gives the gateway a **second face for the person**, a route
`/me` with role `user`, in three stages:

1. **My calls** (read only): the person's own usage rows — when, which
   view, which entry, outcome, and for a refusal the reason in words and
   who refused (gateway, platform, destination, server). Nothing new is
   recorded; the rows exist already.
2. **My credentials** (procedure **U**, *user credential*): a server can be
   marked so that every person brings their own credential (a personal
   access token for Jira, an API key). The person enters it on `/me`; the
   gateway keeps it in its vault, never shows it again, and uses it only
   for that person's calls. Missing credential → a refusal that names the
   server and links to `/me`.
3. **Readiness**: per view, which servers are ready for this person and
   which still need something from them. The chat asks this per assistant
   and shows "not set up yet" on the assistant's card and in *check setup*.

Stage 4, later: OAuth authorization of the person at a remote server
(MCP authorization, authorization code per person), replacing pasted
tokens where the server supports it.

## 1. Motivation

Measured in bec on 2026-11-18: the assistant `sap-a4h-access-support`
calls SAP as JMUELLER through procedure P. When the destination refused
(L24, 403 "This binding does not carry the signed-in person …"), the person
saw the sentence once in the chat; the operator found the cause in the
usage row and the audit log. The person had no place to look again, nor to
see that the same call from Claude Code failed the same way.

The second need is coming with servers that know persons by their own
credentials (Jira, GitHub, Confluence, many SaaS MCP servers): procedure X
(token exchange) needs an identity provider the server trusts, procedure P
needs a destination with a CA the backend trusts. Neither exists for a
SaaS server that only accepts a personal token. Today the only option is a
shared technical credential in the server record — exactly what RFC-0066
set out to avoid (one user for everyone, no attribution at the server).

## 2. Who "me" is

The platform authenticates `/me` like any `user` route and hands the
gateway `X-OAAP-User-Id` (the platform's UUID of the person, RFC-0040).

- Calls carried by the platform (procedures A, P, I) are recorded with
  `user_iss = platform`, `user_sub = <that UUID>` — they match directly.
- Calls of a client signed in at the tenant's identity provider (§2.2 of
  the spec) are recorded with the realm's issuer and the realm's `sub`.
  Whether that `sub` is the same person as the platform UUID is a question
  of the platform (D2).
- Key calls have no person; they never appear on `/me`.

`/me` shows **only rows of this person**. The operator's view of all rows
is unchanged.

## 3. Stage 1 — My calls

A page `/me` and the same as JSON at `/me/v1/calls` (for the chat):

- one line per call: time, view, kind and name in the view, the client and
  assistant if a chat carried it, procedure, outcome, duration;
- filter "only problems" (default when there are any in the last 7 days),
  by view, by day;
- for each outcome other than `ok` a sentence **made from the recorded
  code**, not from recorded text: `refused` + reason `destination` →
  "The destination or the target system refused (HTTP 403)." with a hint
  what a person can do ("ask your tenant administrator; quote time and
  view"), `limited` → which limit, `upstream_error` → "server not reachable
  or faulty", `tool_error` → "the tool reported an error (its text is not
  stored)".

The spec's §10 stays as it is: **no argument, no result, no free text** of
a server or a person in any row. To make the sentence precise, the usage
row gains two **structured** columns: `status` (the HTTP status of a
refusal, a number) and `door` (`gateway`, `platform`, `destination`,
`server`). Neither can carry a payload. (D3)

Retention: the person sees what the rows hold, at most the last 30 days
(D4). RFC-0064 stage 4 (compaction) will shorten it further, not lengthen.

## 4. Stage 2 — My credentials (procedure U)

### 4.1 The server record

A new auth kind `personal` ("U") next to none/bearer/basic/header,
exchange (X), platform (I), propagate (P). The operator sets:

- how the credential is sent: `bearer` or a header name (`header:X-Api-Key`)
  with an optional prefix — the same forms as today's server credentials;
- a **hint for the person**: where to create the token, which scopes
  ("Jira → Profile → Personal Access Tokens, scope read"), as a link and
  one sentence;
- no credential of their own. A `personal` server has no shared fallback —
  ever (as with P: no technical user behind a person).

Like X, I and P, `personal` is a person kind: it is refused in views that
accept keys (`PERSON_KINDS`).

### 4.2 The person's credential

- Entered on `/me` per server, **write only**: after saving the page shows
  "stored on <date>, last used <date>", never the value, not even in part.
- Kept in the gateway's vault (`gwcore/vault.py`, the instance's
  `MCPGW_MASTER_KEY`), keyed by (issuer, sub, server), with its own domain
  so that a server credential and a personal one are never interchangeable.
  A backup of `/data` alone reveals nothing.
- Replace and delete by the person at any time. Audit entries
  `personal.store` / `personal.delete` name person (UUID, never a name —
  §10), server and time, never the value.
- The operator sees **per server how many persons** have stored a
  credential and may **delete** one (revocation, e.g. after a leak or when
  someone leaves) but never read it (D6).
- Unused for 180 days → marked on the operator's page; deleting stays a
  human decision (D8).

### 4.3 The call

For a call to a `personal` server the gateway sends that person's
credential in the configured form, nothing else of the person (no
assertion, no platform token — the server would not know them). Without a
stored credential the call is refused **before** anything goes out, with
the sentence "For server ‹jira› you have not stored a credential yet —
`/me`", recorded as `refused`/`personal`. A `401`/`403` of the server is a
refusal of this person (like P: counted as `refused`/`server`, does not
open the circuit breaker) and `/me` shows "the server rejected your
credential (HTTP 401) — renew it".

The **catalog** of a `personal` server is read with the credential of the
operator who presses "read catalog" — as a person, as with P (P3). If the
operator has none, the page says so.

## 5. Stage 3 — Readiness

`GET /me/v1/readiness?view=<view>` answers per server in the view:

| state | meaning |
|---|---|
| `ready` | nothing needed from the person |
| `needs_credential` | `personal` server, no credential stored (with the hint of §4.1) |
| `credential_rejected` | the last call was refused by the server with 401/403 |
| `not_for_you` | the person's profile does not reach the view, or the light of the view is above what the profile allows |

The chat (RFC-0074) calls this through its via door with the person's
assertion, per assistant (each assistant names one view), and shows a mark
on the assistant's card ("2 tools not set up yet — set up") and a step in
*check setup* with the link to `/me` of that gateway. The gateway does not
know assistants and does not learn them: assistants live in the chat
(D9). On `/me` the gateway shows the same per view, for the views the
person's profiles reach.

## 6. Visibility

`/` stays `admin`. `/me` and `/me/v1/…` are role `user` (`keyuser` and
`admin` included). The portal shows the gateway instance to persons of the
tenant with the title "My tools" and the entry `/me` (D10). The manifest
gets the route; the instance's visibility (RFC-0007) decides who sees the
tile, as for every app.

## 7. Decisions

- **D1 Where the person's face lives.** (a) in the gateway at `/me`,
  (b) in the chat, (c) in the portal. *Recommendation: (a)* — calls come
  from more clients than the chat, and credentials belong next to the
  server records that use them; the chat links there.
- **D2 Calls of a client signed in at the realm.** Matched to the person
  only if the platform tells the gateway the person's realm `sub` (a
  header from the platform at `/me`). *Recommendation:* stage 1 shows
  platform-carried calls (A, P, I) and says that calls signed in at the
  realm follow once the platform passes the realm `sub`; that header is a
  small addition to `oaap.apps.runtime`, built with stage 1 if cheap.
- **D3 What an error says.** *Recommendation:* two structured columns
  (`status`, `door`) and sentences made from codes on the page; no
  free-text column (§10 stays literally true).
- **D4 How far back.** *Recommendation:* 30 days on `/me`.
- **D5 Kind of personal credential.** *Recommendation:* stage 2 a static
  secret (personal access token, API key) in bearer or a named header;
  OAuth per person as stage 4.
- **D6 What the operator sees of personal credentials.** *Recommendation:*
  number per server and the persons as platform UUIDs (the gateway knows
  no names, §10), delete yes, read never.
- **D7 Where they are kept.** *Recommendation:* the gateway's vault, own
  domain, keyed (issuer, sub, server); no second store.
- **D8 When someone leaves.** The gateway does not learn it.
  *Recommendation:* mark unused credentials after 180 days, the operator
  deletes; a platform event "person removed" is a later RFC (would also
  serve chat histories).
- **D9 Readiness for assistants.** *Recommendation:* the gateway answers
  per view; the chat maps assistants to views and shows it.
- **D10 Visibility.** *Recommendation:* route `/me` with role `user`, tile
  "My tools" for the tenant's persons; the operator side unchanged.
- **D11 The letter.** *Recommendation:* **U** (user credential) — X, I, P,
  A, T are taken.

## 8. Stages and tests

| stage | content | done when |
|---|---|---|
| 1 | `/me` + `/me/v1/calls`, columns `status`/`door`, manifest route | a person sees only their rows (bait: a second person's row never appears), refusals in words, key calls absent |
| 2 | auth kind `personal` (U), credentials on `/me`, vault, audit, operator count/delete | the server receives exactly the person's credential; a second person's call never carries it; without one: refused before anything goes out; the value appears in no page, log, row or audit entry (bait value searched in all of `/data` except the vault) |
| 3 | `/me/v1/readiness`, chat shows it per assistant | a missing credential shows on the assistant card; storing it turns the card ready without a reload of the chat app |
| 4 | OAuth per person at a remote server | later RFC section |

Each stage is a gateway version; stage 3 also a chat version. Spec
changes go into `oaap.ai.mcp-gateway` (§2 a third way in for the person's
own page, §3.11 procedure U, §9 the columns, §12 tests).

## Zusammenfassung auf Deutsch

Heute hat das MCP-Gateway nur eine Seite für den Betreiber. Wer es als
Person benutzt, über den Chat, Claude Code oder eine App, sieht dort nichts.
Der RFC schlägt eine zweite Seite **`/me` für die Person** vor (Rolle `user`,
im Portal als „Meine Werkzeuge“), in drei Stufen:

1. **Meine Aufrufe**, nur lesend: die eigenen Messzeilen der letzten 30
   Tage, vor allem Fehler. Der Grund steht in Worten da, mit dem Hinweis, wer
   abgelehnt hat (Gateway, Plattform, Destination, Server). Neu gespeichert
   werden nur zwei strukturierte Spalten (HTTP-Status, „Tür“), kein freier
   Text: Die Regel „nichts von Inhalten im Protokoll“ bleibt wörtlich wahr.
2. **Meine Zugangsdaten** (Verfahren **U**): Der Betreiber markiert einen
   Server als „jede Person bringt ihren eigenen Zugang“, etwa ein
   persönliches Jira-Token. Die Person trägt es auf `/me` ein. Es liegt
   verschlüsselt im Tresor des Gateways und wird nie wieder angezeigt. Das
   Gateway benutzt es nur für die Aufrufe dieser Person. Fehlt es, wird
   abgelehnt, bevor etwas hinausgeht, mit Verweis auf `/me`. Der Betreiber
   sieht, wie viele Personen eins hinterlegt haben, und kann eins löschen,
   aber nie lesen. Einen technischen Benutzer als Rückfall gibt es nicht.
3. **Bereitschaft**: Je Sicht sagt das Gateway, welche Server für die
   Person bereit sind und wo noch etwas fehlt. Der Chat zeigt das je
   Assistent an: „2 Werkzeuge noch nicht eingerichtet – einrichten“.

Später als Stufe 4: Anmeldung der Person per OAuth beim fremden Server statt
eingefügter Tokens.

Offene Entscheidungen D1–D11 mit Empfehlung. Die wichtigsten: Ort `/me` im
Gateway selbst (D1). Aufrufe von Clients mit Anmeldung am Anmeldedienst erst,
wenn die Plattform die `sub` aus dem Realm mitgibt (D2). Fehler als Codes
statt Text (D3). Zugangsdaten zunächst als statisches Token (D5). Der
Betreiber kann löschen, aber nicht lesen (D6). Abgänge markiert das Gateway
nach 180 Tagen ohne Nutzung, gelöscht wird von Hand (D8).

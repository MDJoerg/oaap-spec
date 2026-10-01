# oaap.core.management — The Tenant's Own Hand on the Platform, as an API

- **ID:** `oaap.core.management`
- **Version:** 0.1.1
- **Maturity:** draft (0.1.1 accepts a ZIP that holds the template in ONE
  folder (§2.4), the way an explorer packs a folder; 0.1 is RFC-0046 stage 2: the cohort commands as a
  tenant-scoped JSON API, the job model they need, and the handout as a
  download. Users and single instances follow in later versions under the
  same prefix)
- **Based on:** RFC-0046 (§8, D6), RFC-0027 (API keys; a key is a second
  way to answer `/verify`), RFC-0022 / `oaap.core.tenant` (the tenant is
  the boundary), RFC-0012 (store sources and their trust),
  `oaap.apps.runtime` 2.19 (the cohort and its commands),
  `oaap.core.portal` (the host-side spool the portal already uses)

## 1. Purpose

Everything `oaap cohort` does needs `root` on the node. A trainer at a
customer is a `tenant_admin`, not the node's operator. This capability
gives that person the same operations **in their own tenant and nowhere
else**, as an API that a browser page, a script on a laptop or an app
with a key can call. The CLI stays; the API is its second door, and
**both call one implementation** (RFC-0046 §8).

It says nothing new about *what* a cohort is (`oaap.apps.runtime` 2.19).
It says who may ask, how a long job is carried, what a tenant's trainer
may reference, and how the passwords of a new course reach the trainer
without being kept.

## 2. Interface

### 2.1 Who may call, and where

All calls are under the portal's own host, i.e. the tenant's place
(`oaap.core.tenant`), at `/api/v1/tenant/…`. They sit behind `/verify`
and accept **a session or an API key** (`Authorization: Bearer
oaapk_…`, RFC-0027).

- The caller MUST be a `tenant_admin` (of the tenant in the host and in
  their own record) or a `server_admin`. Anyone else gets `403`.
- **The tenant is the caller's own** — taken from the caller's record,
  never from the request. A body or a query that names a tenant is
  ignored for a `tenant_admin`. A `server_admin` MAY name one with
  `tenant` (a label) in a body.
- A key issued by a `tenant_admin` carries `tenant_admin` for that
  tenant only, expires, and can be revoked; it cannot carry
  `server_admin` (RFC-0027). So a leaked trainer key reaches one
  tenant's cohorts and nothing else.
- **A state-changing call made with a session cookie** (not a key) MUST
  carry the header `X-OAAP-API: 1`. A browser cannot add a custom header
  to a cross-site form post, so a page on another site cannot drive the
  trainer's session. A call with a Bearer key needs no such header: a
  key is not sent by the browser on its own.

Answers are JSON (`application/json`), except the handout download
(2.6). Errors are `{"error": "<one sentence>"}` with `400` (the request
is wrong), `403` (not allowed), `404` (no such object **in this
tenant** — also when it exists in another), `409` (the state forbids
it), `413` (too large).

### 2.2 The cohort

| call | meaning | answer |
| --- | --- | --- |
| `GET /cohorts` | the tenant's cohorts: name, seats, state (`running`, `stopped`, `incomplete`), `ends` | `200`, read now |
| `GET /cohorts/{name}` | one cohort: lifetime, seats with user, instance(s), state, address, waiting/refused notes | `200`, read now |
| `POST /cohorts` | create a cohort from a template (2.4) | `202`, a job (2.3) |
| `POST /cohorts/{name}/stop`, `…/start` | stop or start every instance; nothing is deleted | `202`, a job |
| `POST /cohorts/{name}/extend` `{"ends": "YYYY-MM-DD", "dry_run": false}` | move the end later (2.19 "Moving the end") | `202`, a job |
| `POST /cohorts/{name}/seats` `{"name": "<participant>"}` | add a seat (`name` for a named participant, else the next number) | `202`, a job with a handout |
| `POST /cohorts/{name}/seats/{id}/reset` `{"keep_home": false}` | rebuild one seat from the template | `202`, a job with a handout |
| `DELETE /cohorts/{name}/seats/{id}` `{"purge": true, "confirm": "<name>"}` | remove one seat's instance(s) (and with `purge` their data) | `202`, a job |
| `DELETE /cohorts/{name}` `{"purge": true, "users": true, "confirm": "<name>"}` | remove the cohort | `202`, a job |

- A **removal** MUST carry `confirm` equal to the cohort's name; the
  host checks it again (as for an instance removal: a replayed or
  misdirected request cannot take down another object).
- `GET` answers come from the host's own records, read through the same
  worker as the writes (2.3), so a list is never older than the last
  job.
- The cohort commands that need the node's operator stay CLI-only in
  0.1: `sweep` (it is the timer's), `secret` (named secrets are the
  operator's to store, 2.5) and `export` (it writes a file on the node).

### 2.3 Jobs

A create takes minutes (images, containers); a request MUST NOT hold the
connection open for it. A state-changing call therefore answers `202`
with `{"job": "<id>", "status_url": "/api/v1/tenant/jobs/<id>"}`.

`GET /jobs/{id}` answers:

```json
{"id": "…", "op": "create", "status": "queued|running|done",
 "ok": true, "message": "…", "handout": true, "created": "…"}
```

- `status` is `queued` while the request waits, `running` while the host
  works on it, `done` when it has answered; `ok` and `message` are there
  only when `done`. `message` is the host's own sentence (the CLI's last
  line), never a stack trace.
- A job is visible to the `tenant_admin`s of **its tenant** and to
  `server_admin`; to nobody else (`404`).
- The host works one request at a time, in order (the spool of
  `oaap.core.portal`); a create therefore delays the requests behind it.
  This is stated, not hidden: `status: queued` is the honest answer.
- A finished job's record is kept **24 hours**, then removed.

### 2.4 The template, uploaded

`POST /cohorts` takes the template directory (2.19, `cohort.yaml`,
seeds, material) **as a ZIP**: `Content-Type: application/zip`, the
body is the archive, `cohort.yaml` at its root. (ZIP rather than a Git
address: a trainer's repository is usually private, RFC-0019.)

- **One wrapper folder is tolerated** (0.1.1): when `cohort.yaml` is not
  at the root but is directly inside the **only** top-level folder, that
  folder is taken off on extraction — the way "send folder to ZIP" packs
  (Windows, macOS; `__MACOSX/` beside it is ignored). Exactly one level,
  and a template is never searched for: two folders, or `cohort.yaml`
  two levels down, are refused. Every other rule below applies unchanged,
  to the paths as they are in the archive.

- Extraction MUST refuse: a path outside the target (`..`, absolute,
  drive letters, backslashes), a symbolic or hard link, a device or
  special entry, more than 5 000 entries, more than 512 MiB unpacked or
  more than 256 MiB uploaded (`413`). Nothing is extracted before the
  whole archive has been checked.
- The host MUST check the extracted tree **again** (the spool is data,
  not trust) and then applies every rule of 2.19 to it, with all
  problems reported at once.
- The template's own `tenant:` line is ignored for a `tenant_admin`.
- The uploaded copy is deleted when the job ends, success or not. What
  stays is the host's stored copy (2.19).

### 2.5 What a tenant's trainer may reference

A template names the apps of a seat. For a `tenant_admin` the host MUST
accept only an **app id from a configured store source whose trust is
not `unverified`** (RFC-0012 §3). It MUST refuse a Git address (the
node's operator is the authority for those) and MUST NOT accept a
`confirm_source`. A `server_admin` through the API has the CLI's
freedom.

A secret named in a template (`{secret: …}`) MUST already exist for the
tenant; the API cannot create one in 0.1.

### 2.6 The handout, as one download

Creating a cohort, adding a seat and resetting a seat make passwords the
node does not keep (2.19). The host writes them into the job's handout
file (mode 0600, in the job's own directory) and nowhere else.

`POST /jobs/{id}/handout` with an optional body `{"password": "<text>"}`
returns **a ZIP** (`application/zip`, `Content-Disposition: attachment`)
holding `handout.csv`:

- **with `password`** the ZIP is encrypted (AES-256). The trainer chose
  the password, **at the time of the download**; the service never
  stores it and never writes it to a log. The password MUST be at least
  8 characters (`400` otherwise).
- **without `password`** the ZIP is a plain container and the response
  says so in `X-OAAP-Handout: unencrypted`. That is the trainer's call,
  and the same as the CLI's file.
- **One time.** After a successful download the handout file is
  overwritten with zeros and removed; a second call answers `410`. It is
  removed after 24 hours unclaimed.
- The download is allowed for **the person who started the job** and for
  `server_admin` — not for any other `tenant_admin` of the tenant.
- A job record never contains a password; neither does the audit log.

The plaintext file exists on the node between the end of the job and the
download, readable by the node's operator and the portal. That is the
price of letting the trainer choose the password after the fact; the
24-hour limit and the removal after one download are what bound it.

### 2.7 Audit

Every state-changing call is an entry in the tenant's audit log
(`oaap.core.tenant` 1.7) with the actor — a person or a key's id — and
the operation: `cohort.create`, `cohort.start`, `cohort.stop`,
`cohort.extend`, `cohort.seat-add`, `cohort.seat-reset`,
`cohort.seat-remove`, `cohort.remove`, `cohort.handout`. A refused call
is recorded as `denied` with its reason, like a refused worker action.

## 3. Security requirements

- The tenant comes from the caller's record only (2.1); a name that
  exists in another tenant answers `404`, exactly as one that does not
  exist.
- A `tenant_admin` cannot reach the node: no Git address as an app, no
  unverified source, no `server_admin`-only command.
- A job and its handout are not readable across tenants, and the handout
  not by a colleague (2.6).
- A cross-site request cannot use a session (2.1).
- An uploaded archive cannot write outside its directory or smuggle a
  link (2.4).
- No password appears in a job record, a log or the audit log (2.6, 2.7).

## 4. Checks

1. **Scope.** A `tenant_admin` of tenant A calling for tenant B's cohort
   gets `404`; naming `tenant: B` in a body changes nothing; a person
   without the role gets `403`; a key of A cannot reach B.
2. **Door.** A session call without `X-OAAP-API: 1` is refused; a Bearer
   call without it works.
3. **Create from ZIP.** A valid archive makes the cohort and a job that
   ends `done`, `ok`, with `handout: true`; an archive with `../x`, a
   link, an absolute path or too many entries is refused before any
   extraction and nothing is created.
4. **Sources.** A template with a Git address, or with an app of an
   unverified source, is refused for a `tenant_admin` and accepted for a
   `server_admin`.
5. **Jobs.** A job is `queued`, then `running`, then `done`; another
   tenant's job is `404`; a job record is gone after 24 hours.
6. **Handout.** With a password the ZIP is encrypted and opens only with
   it; without one it says `unencrypted`; a second download is `410`;
   a colleague `tenant_admin` is refused; the file is gone afterwards; a
   password under 8 characters is `400`.
7. **Operations.** `stop`/`start`/`extend` act as the CLI does and
   delete nothing; a removal without `confirm` is `400`, with a wrong one
   `409`.
8. **Audit.** Each call, allowed or refused, is one entry with its
   actor; none contains a password.

## 5. Not in 0.1

- Users and single instances as resources of this API (the tenant already
  administers them in the portal).
- Creating a named secret through the API.
- A portal page for cohorts (a later stage of RFC-0046 uses this API).
- Webhooks or server-sent progress; a client polls the job.

## Deutsche Zusammenfassung (v0.1 — die Verwaltungs-API für Kohorten)

Bisher braucht jeder `oaap cohort`-Befehl `root` auf dem Knoten. Diese
Spezifikation gibt dem **`tenant_admin` eines Mandanten** dieselben
Handgriffe **in seinem Mandanten und nirgends sonst**, als JSON-API unter
`/api/v1/tenant/…` am Ort des Mandanten — per Sitzung oder per
API-Schlüssel (RFC-0027). Kommandozeile und API rufen **eine**
Umsetzung auf.

- **Mandant:** immer der aus dem eigenen Benutzersatz des Aufrufers; ein
  Fremdname in der Anfrage zählt nicht, ein Objekt eines anderen Mandanten
  ist `404`. Mit Sitzung (nicht Schlüssel) verlangen ändernde Aufrufe den
  Kopf `X-OAAP-API: 1` (Schutz vor Fremdseiten).
- **Aufträge:** Anlegen dauert Minuten, daher `202` und ein Auftrag
  (`queued`/`running`/`done`), den man abfragt. Der Knoten arbeitet einen
  Auftrag nach dem anderen; das wird offen gesagt. Aufträge bleiben 24 h.
- **Vorlage hochladen:** als ZIP, streng geprüft (kein `..`, keine Links,
  Obergrenzen) — vor dem Entpacken und auf dem Knoten noch einmal.
- **Was ein Ausbilder darf:** nur Apps aus eingerichteten Store-Quellen,
  deren Vertrauen nicht `unverified` ist; keine Git-Adresse, kein
  `confirm_source`. Benannte Geheimnisse legt weiter der Betreiber an.
- **Handout als ZIP:** einmaliger Download, auf Wunsch **mit selbst
  gewähltem Passwort** (AES-256, mindestens 8 Zeichen), das erst beim
  Herunterladen genannt und nie gespeichert wird. Danach wird die Datei
  überschrieben und gelöscht (sonst nach 24 h). Nur wer den Auftrag
  gestartet hat, und `server_admin`, darf es holen. Kein Passwort in
  Auftrag, Protokoll oder Audit.
- **Nicht in 0.1:** Benutzer und Einzelinstanzen als API-Objekte, Geheimnisse
  anlegen, eine Portal-Seite (kommt als nächste Stufe auf dieser API).

## Deutsche Zusammenfassung (v0.1.1 — ein Ordner im ZIP)

Wer unter Windows oder macOS „Ordner als ZIP senden“ wählt, bekommt ein
Archiv, in dem alles in **einem** Ordner liegt. Das nimmt die API jetzt an:
liegt `cohort.yaml` nicht oben, aber direkt in dem einen obersten Ordner,
wird dieser Ordner beim Entpacken abgenommen (`__MACOSX/` daneben wird
übergangen). Genau eine Ebene: zwei Ordner oder `cohort.yaml` zwei Ebenen
tief werden weiter abgelehnt — es wird nie gesucht. Alle anderen Prüfungen
gelten unverändert.

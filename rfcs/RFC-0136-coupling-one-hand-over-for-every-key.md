# RFC-0136: Coupling — One Hand-Over for Every Key

- **Status:** **Accepted (2026-11-26)** — D1–D8 decided by Jörg one at a
  time, all as recommended (§9). Nothing built; stage 0 (measure) next.
- **Date:** 2026-11-26
- **Authors:** Jörg (the need, I-76: couplings — destinations, Node-RED, SAP,
  AI gateways in a cascade, across tenants and nodes — "angenehm aber sicher",
  one procedure for the whole platform, "auch so, dass eine App Schlüssel
  anfordern kann, auch eigene"; the model is the SAP BTP service key), Claude
  (design)
- **Depends on:** RFC-0027 (machine principals and API keys), RFC-0085 A3
  (fleet pairing, `OAAP-PAIR1`, the pattern this generalises), RFC-0135 (gates
  and their accesses, the first user), RFC-0062 (instance keys), RFC-0054
  (broker access), RFC-0033 (connector offers), RFC-0028 (terminal pairing)
- **Changes (when accepted):** identity (coupling tickets and their
  redemption), the portal (a coupling instead of a shown key, a page
  „Kopplungen“), the gateway (a redemption door on the tenant's place); later
  the manifest (`coupling`) and the fleet pairing on the same procedure

## Summary

Today a key is handed over by **showing it once** (RFC-0027, the gate page of
RFC-0135): a person copies a secret from a page into a mail, a chat, a ticket
or SM59. The secret then lives wherever it was pasted, for as long as it is
valid — 90 days for a gate access. The fleet already does it better
(RFC-0085 A3): a **pairing file** that carries no secret but a **one-time
code**, valid 15 minutes, with the server's certificate fingerprint; the
receiver redeems the code and only then gets its key.

This RFC makes that **one procedure for every key of the platform**:

- A **coupling** is a ticket: one line `OAAP-COUPLE1.<base64url>` (the same
  content as a JSON file and as a QR code) with the address, the kind, the
  target, the user name, the certificate fingerprint, the expiry of the
  ticket, links to ping and template — and a **redemption code**, never the
  secret.
- **Redeeming** (`POST /platform/couple/redeem`, on the address in the
  ticket) creates the key **at that moment** in identity and answers it once,
  with everything the receiver needs. The code works once and only within its
  window (15 minutes by default). A ticket that was redeemed, expired or
  revoked is worthless; one that leaked after redemption gives nothing.
- **Who redeems:** a program (Node-RED, another OAAP node, a script, an app)
  calls the door itself. A **person** (SAP, where SM59 takes only user and
  password) opens the ticket's short-lived **link** in a browser and sees the
  key once, to paste it — the same as today, but the key is born on that page,
  not when the administrator clicked, and the link dies after use.
- Every ticket and every redemption is **audited** and listed on a portal page
  „Kopplungen“ (issued by, for what, until when, redeemed when and from which
  address); an open ticket can be withdrawn.
- **Kinds:** stage 1 the gate access (RFC-0135); stage 2 platform keys
  (RFC-0027, page „Zugänge“) and the fleet pairing on the same procedure
  (`OAAP-PAIR1` stays readable); stage 3 a door for **apps**: an app declares
  `coupling` in its manifest and has the platform issue keys for its *own* API,
  which the platform holds, expires, revokes and checks.

## 1. Words

- **Coupling ticket** — what is handed over: no secret, a redemption code and
  the parameters. Text form `OAAP-COUPLE1.<base64url(JSON)>`.
- **Redemption** — the one call that turns a code into a key.
- **Window** — how long a ticket can be redeemed (default 15 minutes).
- **Kind** — what the key is for: `gate-access`, `platform-key`,
  `fleet-node`, `app-key` (stage 3).
- **Issuer** — the person (or, stage 3, the app) who made the ticket.

## 2. The ticket

```json
{"v": 1, "kind": "gate-access",
 "address": "https://bec.brandeis.de/gate/sap-support",
 "label": "SAP A4H 001", "user": "sap-support",
 "redeem": "https://bec.brandeis.de/platform/couple/redeem",
 "code": "c1_7Hq…(32 bytes base64url)",
 "until": "2026-11-26T19:15:00Z", "key_days": 90,
 "pin": "sha256 of the server certificate, only for a non-public address",
 "links": {"ping": "…/gate/sap-support",
           "template": "…/gate/sap-support/template?form=placeholders",
           "browser": "https://bec.brandeis.de/platform/couple/<uuid>"},
 "issuer": "bec.carl", "issued": "2026-11-26T19:00:00Z"}
```

- One content, three forms: the **line** (copy and paste, a mail wraps it —
  whitespace is ignored as in `fleet_pair.decode`), the **file** (`.json`,
  download and upload), the **QR code** (a phone, a second screen). The line
  is what the portal shows first.
- Nothing in it is a secret by itself: the code is worth something only
  within the window and only once. identity stores only its hash.
- `pin` is set when the address is not publicly trusted (an internal node, a
  self-signed gateway); the redeeming program checks the certificate against
  it, as `fleet_pair` does. For a public address the normal chain applies.

## 3. Redemption

`POST <redeem>` with `{"code": "…"}` (JSON or form field), no login:

- **valid code, in the window, not used** → `200` with the key and the
  parameters (`{"kind", "key", "user", "address", "expires", "label",
  "sm59": {…}}` for a gate access); the ticket is marked redeemed with time
  and caller address in the same transaction (a second call with the same
  code gets `410`);
- **expired, redeemed, withdrawn** → `410` with one sentence („Diese
  Kopplung ist abgelaufen oder schon eingelöst — bitte eine neue anfordern.“);
- **unknown code** → `404`, the same short sentence for every unknown code;
  failures count per caller address (the identity throttle), so guessing is
  bounded (and a 32-byte code is not guessed).

The **key is created at redemption**, not when the ticket is made: before,
there is nothing to steal; the principal (for a gate: `gate-<name>-<n>`) is
created with the ticket, inactive, and activated by the redemption — so the
page shows the access as „wartet auf Einlösung“ from the start.

**The browser link** (`links.browser`, a random UUID, same window): a page on
the tenant's place that shows the label, the target and a button „Schlüssel
jetzt erzeugen“ — only the click redeems (a link preview of a mail or chat
program must not use the ticket up). After the click: the key once, with the
SM59 parameters (as GATE_KEY_BODY today), and a note that the page cannot be
opened again.

## 4. Issuing

On the gate page (RFC-0135), „Zugang ausstellen“ becomes two buttons:
**„Kopplung erzeugen“** (default) and **„Schlüssel sofort zeigen“** (today's
way, kept for the administrator who stands at SM59 themselves). The coupling
shows the line, a download, a QR code and the browser link, with the window
counting down. The platform-key page (RFC-0027) gets the same in stage 2.

The window: 15 minutes by default; the issuer may choose up to 7 days for a
hand-over by mail to someone who will act later (D3). The key's own validity
(90 days for a gate) is separate and starts at redemption.

## 5. The page „Kopplungen“

Per tenant: open tickets (kind, target, issuer, window left, withdraw),
redeemed ones (when, from which address, which key — a link to the access),
expired ones (30 days). A server_admin sees every tenant. The tenant log
records `coupling.issue`, `coupling.redeem`, `coupling.withdraw`,
`coupling.refused` (with the reason, never the code).

## 6. Kinds and stages

| Kind | What redemption creates | Stage |
|---|---|---|
| `gate-access` | key limited to `oaap.gate:<tenant>/<gate>`, principal activated | 1 |
| `platform-key` | an RFC-0027 key with its scope and label | 2 |
| `fleet-node` | the node key of RFC-0085 A3 (today `OAAP-PAIR1` node code) | 2 |
| `app-key` | a key for an app's own API, held by the platform | 3 |

**Stage 3, the app door.** An app declares in its manifest

```yaml
coupling:
  issue: [app-key]          # the app may have keys for its own API issued
  scopes: [read, write]     # what such a key may be limited to
```

and gets a platform door `/platform/coupling/v1` with its instance key:
`issue` (a ticket for a key of this app, with a scope and a label; the
redemption creates the key in identity, limited to `app:<instance>:<scope>`),
`list`, `withdraw`, and `verify` (the app asks whether a presented key is one
of its own and which scope it has — or, simpler, the gateway checks it on the
app's site as it checks every key today, and the app gets the scope in a
header). The platform holds every key, so expiry, revocation and the audit
are one place for all apps (D7).

The coupling across tenants and nodes (an AI gateway in a cascade, a
destination to another tenant) is a `platform-key` ticket redeemed by the
other side's connector or destination; its form (who redeems on the
receiving node) is a stage-2 question, measured first.

## 7. Security

- No secret in the ticket; code stored as hash; one use; short window; the
  redemption is atomic; the key is born at redemption.
- Redemption is rate-limited per caller address; a refusal says the same for
  every unknown code.
- A ticket names its address; a ticket redeemed elsewhere does nothing (the
  code exists only on the issuing node).
- The browser link redeems only on a click (no prefetch, `POST`), and the
  page is `no-store`.
- Pinning where the address is not publicly trusted.
- Every step in the tenant log; the page lists what is open.

## 8. Relation to what exists

- `fleet_pair.py` (`OAAP-PAIR1`): the same idea for the fleet; stage 2 lets it
  produce `OAAP-COUPLE1` tickets of kind `fleet-node` and keeps reading
  `OAAP-PAIR1` (one node of the fleet may be older than the hub).
- RFC-0028 (terminal pairing), RFC-0033 (connector offers), RFC-0062
  (instance keys), RFC-0134 D10 (agent keys) keep their own forms for now;
  each is named in §6 when it moves.
- RFC-0135 §8 already said the coupling file "will plug in here".

## 9. Decisions

Each with a recommendation; to be decided one at a time.

- **D1 Form of the ticket.** (a) one line `OAAP-COUPLE1.<base64url(JSON)>`,
  the same content as a JSON file and a QR code (recommended — copy, file and
  phone carry one thing, as `OAAP-PAIR1`); (b) a JSON file only.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D2 Where the secret comes from.** (a) a one-time redemption code in the
  ticket, the key handed out at redemption (recommended — a leaked ticket is
  worthless after use or expiry); (b) the key in the ticket, encrypted with a
  passphrase that travels separately.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D3 Window.** (a) 15 minutes by default, the issuer may choose up to 7 days
  (recommended — a hand-over by mail to someone who acts tomorrow); (b) always
  15 minutes.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D4 When the key is born.** (a) at redemption, by identity; until then the
  access exists inactive, „wartet auf Einlösung“ (recommended — before
  redemption there is nothing to steal, also not on the platform); (b) at
  issue, kept until redeemed.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D5 A person as receiver (SAP).** (a) the ticket's browser link: a page
  that creates and shows the key once after a click (recommended — SM59 takes
  only user and password; the link is single-use, a mail preview does not
  spend it); (b) only the administrator's direct display, as today.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D6 Kinds in the first stage.** (a) gate accesses only, then platform keys
  and the fleet pairing (recommended — one user, measured, then widened);
  (b) all kinds at once.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D7 Keys of an app's own API (stage 3).** (a) the platform holds them
  (identity, limited to the app's instance and a scope; the gateway checks;
  the app gets the scope in a header) (recommended — expiry, revocation and
  audit in one place for every app); (b) the app keeps its own keys, the
  platform only hands over the ticket.
  → **Decided 2026-11-26: (a)** (Jörg).
- **D8 Certificate pinning.** (a) the fingerprint in the ticket only when the
  address is not publicly trusted; the redeemer checks it then (recommended —
  internal nodes and self-signed gateways work, public ones keep the normal
  chain); (b) always pinned.
  → **Decided 2026-11-26: (a)** (Jörg).
## 10. Stages

- **Stage 0 — measure:** what the receivers can do: Node-RED (`http request`
  node, a flow that redeems and stores the key in its credentials), curl, an
  OAAP node's connector, ABAP (`cl_http_client`, whether a program could
  redeem instead of a person); how a mail and a chat client (Teams, the
  platform's chat) preview a link (D5's click).
- **Stage 1 — gate accesses:** tickets and redemption in identity, the door
  on the tenant's place, the browser page, the two buttons on the gate page,
  the page „Kopplungen“, the audit.
- **Stage 2 — platform keys and the fleet:** the page „Zugänge“; `fleet-node`
  tickets; the cross-node and cross-tenant coupling, measured first.
- **Stage 3 — apps:** the manifest block `coupling`, the door
  `/platform/coupling/v1`, app keys checked by the gateway.

## Non-goals

- A secret store for the receiver (where Node-RED or SAP keeps the key is
  theirs).
- Client certificates instead of keys (possible later; RFC-0135 non-goal too).
- Moving the existing pairing forms of §8 before their stage.

## Deutsche Zusammenfassung

Heute wird ein Schlüssel übergeben, indem er **einmal angezeigt** wird. Dann
liegt er dort, wo er hineinkopiert wurde: in einer Mail, einem Chat oder
einem Ticket, und das so lange, wie er gilt (bei einem Tor 90 Tage). Die
Flotte macht es schon besser (RFC-0085 A3): Eine Kopplungsdatei enthält kein
Geheimnis, sondern einen **Einmalcode** mit 15 Minuten Gültigkeit und dem
Fingerabdruck des Zertifikats.

Dieses RFC macht daraus **ein Verfahren für alle Schlüssel der Plattform**:

- Eine **Kopplung** ist ein Ticket: eine Zeile `OAAP-COUPLE1.…`, gleich als
  Datei und QR-Code. Es enthält Adresse, Art, Ziel, Benutzername, bei Bedarf
  den Zertifikats-Fingerabdruck, die Frist, Links zu Ping und Vorlage und
  einen **Einlösecode**, nie das Geheimnis.
- **Einlösen** (`POST /platform/couple/redeem`) erzeugt den Schlüssel **erst
  in diesem Moment** und gibt ihn einmal heraus. Der Code gilt einmal und nur
  in seiner Frist (15 Minuten, auf Wunsch bis 7 Tage). Danach ist das Ticket
  wertlos.
- Ein **Programm** (Node-RED, ein anderer OAAP-Knoten, eine App) löst selbst
  ein. Ein **Mensch** (SAP, SM59 kennt nur Benutzer und Passwort) öffnet den
  Link des Tickets und erzeugt den Schlüssel dort mit einem Klick. Er sieht
  ihn einmal, der Link verfällt danach. Eine Linkvorschau im Mailprogramm
  verbraucht ihn nicht.
- Jede Ausgabe und Einlösung steht im Protokoll und auf einer Portalseite
  **„Kopplungen“** (offen, eingelöst von wo und wann, abgelaufen). Offene
  Tickets lassen sich zurückziehen.
- **Stufen:** 1 Tor-Zugänge, 2 Plattformschlüssel und die Flottenkopplung im
  selben Verfahren, 3 eine Tür für **Apps**. Eine App erklärt `coupling` im
  Manifest und lässt Schlüssel für ihre **eigene** API ausstellen. Die
  Plattform hält, prüft, lässt ablaufen und widerruft sie.

**Entschieden am 26.11. (Jörg, einzeln, alle wie empfohlen):**
- D1 Zeile, Datei und QR mit gleichem Inhalt;
- D2 Einlösecode statt Geheimnis;
- D3 15 Minuten, bis 7 Tage wählbar;
- D4 Schlüssel entsteht erst beim Einlösen;
- D5 Browser-Link für Menschen;
- D6 zuerst nur Tor-Zugänge;
- D7 App-Schlüssel hält die Plattform;
- D8 Zertifikat nur bei nicht öffentlicher Adresse festnageln.

# RFC-0019: Artifact Deployment — Deploying Without Holding Someone Else's Key

- **Status:** Accepted (2026-08-15)
- **Date:** 2026-08-15
- **Authors:** Jörg (direction and decisions), Claude (write-up)
- **Depends on:** RFC-0004 (app packaging and manifest), RFC-0007 (visibility
  groups), RFC-0011 (node profiles), RFC-0015 (declared endpoints),
  RFC-0016 (app isolation and app-to-app links)
- **Amends:** `oaap.apps.runtime` 2.5, which states that a deploy request
  *"can never supply a different source or upload a package"*. This RFC
  opens exactly that door — narrowly, and with the compensating checks
  that sentence was standing in for.
- **Driver:** `bdt-app` — a private repository that may never become
  public, whose AI already produces ready-to-install OAAP packages
  (~10 MB). The Git path would require the platform to store a foreign
  access credential in order to deploy it.

## Summary

An instance may be deployed from an **uploaded artifact** (a ZIP package)
instead of from a recorded Git source — for the first installation *and*
for subsequent updates, as a parallel option, never as a replacement.

The upload runs as a **three-phase handshake**: the client announces the
new version and its manifest, the platform validates that announcement
and answers with a **single-use upload grant**, and only that grant admits
the artifact itself — which is then checked again, against what was
announced, before anything is unpacked or built.

Validation is governed by one rule: **a deploy token redeploys within the
envelope already granted to the instance; anything that widens the
envelope requires a human.**

## Motivation

### The borrowed key

The Git path requires a credential for the source repository. For a
private repository that means the platform stores a **personal access
token in cleartext** in `/var/lib/oaap/apps/registry.json`, from where it
travels into every backup. This is already live: `bdt-hub-test` holds such
a token today.

For the operator's own repository that is a tolerable trade. For a
repository that belongs to someone else — a customer, a partner, a
contractor's AI — it is the wrong direction: **the platform accumulates
keys to systems that are not its own.** A compromised node, or a leaked
backup, then exposes not only what runs on the platform but read access to
foreign source code.

Artifact deployment inverts this. The platform receives a **package, not
an access right**. The only secret involved is the deploy token, which
points *at* the platform, is issued by the platform, and can be revoked by
the platform alone. Nothing foreign is held.

This is not a convenience argument. For private sources, the artifact path
is the **better security posture**, and that — not ease of use — is why it
belongs in the platform.

### The ordering problem

`oaap app install` requires `oaap-app.yaml` in the package, and
`oaap app token create` requires an existing instance. A project's AI
therefore cannot be given a working deploy loop until a human has already
produced a valid manifest at a reachable location. For a project whose
artifacts exist but whose repository does not (or is unreachable), there is
no first step at all.

### What stays true

Nothing here weakens the production path. Promotion to production remains a
human action with a version bump, and deploy tokens for production
instances still MUST NOT exist (2.5, unchanged).

## Decisions (Jörg, 2026-08-15)

1. **Artifact upload is a parallel deployment path, for updates too** —
   not merely a bootstrap for the first installation. A project with a
   permanently private source must be able to live on this path.
2. **The manifest is checked on every deployment, and a deployment is
   refused when defined characteristics differ.** Validation is not a
   formality at install time; it is the standing control that makes an
   unattended upload path acceptable.
3. **Deployment becomes a phased exchange**: announce the new version and
   manifest → platform validates and issues a single-use token → artifact
   is accepted only against that token → contents validated again.
4. **Size is bounded**, but size is the lesser concern; content validation
   is the substance.
5. **An envelope widening may be confirmed in the portal** (`server_admin`),
   not only at the machine. The confirmation is a deliberate, audited act
   either way; forcing it onto the CLI would push the operator back into
   the path this RFC exists to remove.
6. **Three predecessors are retained** per instance — enough to compare
   versions, not just to step back one.
7. **Studio may upload, not only validate** — for usability, and because an
   offline scenario (no reachable forge, only a file on a stick) must have
   a working path that does not require the operator to know the portal's
   instance machinery. §"Studio" defines the bounded form this takes.
8. **Studio stores no credential.** The deploy token is kept by the
   operator and entered at each upload; instance creation runs on a
   single-use grant. This keeps the Studio app's own decision *"Keine
   Deploy-Token im Studio"* intact rather than trading it away for
   convenience.

## Design

### 1. A third source kind

The registry's `source` object gains `kind: "artifact"` alongside `git`
and `local`:

```json
"source": {
  "kind": "artifact",
  "version": "0.4.1",
  "sha256": "9f2c…",
  "stored": "artifacts/0.4.1-9f2c….zip",
  "received": "2026-08-15T09:14:02Z"
}
```

The artifact itself is **retained on the node** under the instance's
directory. This is what makes the artifact path a real source rather than
a dead end: a redeploy has something to fetch, `oaap app list` can say what
is running, and a rollback has something to roll back to (§4).

A `local` install (an operator unpacking a ZIP by hand) is unchanged and
remains what it is: a one-off, not a recorded source.

### 2. The three-phase handshake

All three phases run through the gateway's `/deploy/*` handler, which is
exempt from session auth and authorized solely by bearer credential
(2.5, unchanged).

**Phase 1 — announce.**

```
POST /deploy/<instance>/announce
Authorization: Bearer <deploy-token>
Content-Type: application/json

{ "version": "0.4.1",
  "manifest": "<the complete oaap-app.yaml, verbatim>",
  "artifact_sha256": "9f2c…",
  "artifact_bytes": 10485760 }
```

**Phase 2 — the platform decides.** The manifest is parsed, schema-
validated (2.2) and checked against the envelope rule (§3). The declared
size is checked against the configured maximum. On acceptance:

```
200 OK
{ "upload_token": "<single-use secret>",
  "upload_url": "https://…/deploy/<instance>/artifact",
  "expires_in": 900 }
```

On refusal, a machine-readable reason **and** a human-readable sentence —
the recipient is an AI that must be able to correct itself without asking a
person:

```
422 Unprocessable Content
{ "refused": "envelope_widened",
  "details": ["route '/' changes visibility from 'groups' to 'public'"],
  "message": "This deployment would widen what the instance may reach or
              who may reach it. It needs confirmation by an administrator." }
```

**Phase 3 — upload.**

```
PUT /deploy/<instance>/artifact
Authorization: Bearer <upload-token>
Content-Type: application/zip
<body>
```

The upload token is:

- **bound** to one instance, one announced manifest and one
  `artifact_sha256`,
- **short-lived** (default 15 minutes),
- **single-use** — consumed on the first upload that is accepted for
  processing; a transport failure may be retried within the TTL, capped at
  a small number of attempts,
- stored as a digest only, like deploy tokens,
- invalidated when the deploy token is revoked or the instance moves to
  production.

Before anything is unpacked the platform verifies: byte count against the
announcement, SHA-256 against the announcement, and — after safe extraction
(§5) — that the `oaap-app.yaml` inside the artifact is **byte-identical to
the announced manifest**.

That last check is what makes Phase 1 meaningful. Without it, a client
could announce a harmless manifest and upload a different one, and the
entire handshake would be theatre.

### 3. The envelope rule

> A deploy token redeploys an instance **within the envelope already
> granted to it**. Anything that widens the envelope requires a human.

This is not new policy. The reference implementation already protects
granted properties from being undone by a redeploy — a declared endpoint
survives, the instance's own address survives, the throttle override
survives, and a group-restricted instance must not be silently reopened.
RFC-0019 states the same instinct positively and makes it checkable.

**Hard refusal — no confirmation path:**

| Condition | Why |
| --- | --- |
| `app.id` differs from the installed instance | An instance belongs to one app. An upload must not turn `bdt-app-test` into something else. |
| Manifest invalid against the schema | 2.2, unchanged. |
| Artifact manifest ≠ announced manifest | The announcement is the contract. |
| Size or checksum mismatch | Integrity. |
| `app.version` equals the installed version | Without a commit hash, the version is the only answer to "what is running". Same-version redeploy remains legal on the Git path; on the artifact path it is refused. |

**Refusal with an administrator confirmation path — envelope widening:**

- a route becomes `public` that was not, or a new `public` route appears
- visibility loses or widens its group restriction (RFC-0007)
- a new declared non-HTTP endpoint or fixed port appears (RFC-0015)
- a new app-to-app link appears (RFC-0016)
- a new storage mount appears, or an existing mount's path changes

**Silent pass — inside the envelope:** everything else. New config keys
with defaults, changed labels and words (RFC-0014), new internal services,
route changes that do not alter reach. This is the normal case and must be
frictionless; a path that stops for a human on every deployment has failed
at its purpose.

### 4. Retention and rollback

Artifacts are kept per instance with their checksum and receipt time. The
current one plus **three predecessors** are retained (decision 6), so that:

- a redeploy has a source to fetch,
- `oaap app list` and the portal can name the running artifact
  (version + short checksum) instead of "local",
- a rollback is a normal install of the retained predecessor.

Retained artifacts live under the instance's directory and are therefore
covered by `oaap backup create` — a design consequence worth stating: a
backup of an artifact-deployed instance is now genuinely self-contained,
which the Git path never was.

### 5. Unpacking safely

Extraction of an attacker-supplied archive is the sharpest edge in this
RFC and belongs in the specification, not in a code review:

- Entry paths MUST be rejected if absolute, containing `..`, or resolving
  outside the extraction root after normalisation.
- Symlinks, hard links, device nodes and other non-regular entries MUST be
  rejected.
- Total uncompressed size, per-entry uncompressed size and entry count MUST
  be bounded (decompression bombs); the bound is checked **during**
  extraction, not from declared headers.
- Extraction MUST target a fresh temporary directory and MUST never write
  over an existing instance tree; installation replaces the tree only after
  every check has passed.
- Announce and upload endpoints MUST be throttled like the deploy hook and
  MUST NOT reveal whether an instance name exists (2.5, unchanged).

### 6. Audit

Both phases are recorded in the existing deploy log: announcement (version,
checksum, decision, refusal reason) and upload (outcome, resulting
revision). A refused announcement is as interesting as a successful
deployment — repeated refusals are the signal that something is trying
things.

## Portal and Studio

- **Portal (`server_admin`)** carries the privileged surface, because it
  already has it: upload an artifact when creating a test instance
  (alongside the existing Git URL form, RFC-0011), see the running
  artifact and its checksum on the instance page, confirm an envelope
  widening, roll back to any retained predecessor.
- **Studio** reads an uploaded package's `oaap-app.yaml` to **validate it
  and prefill the project entry** (app id, version, type, routes, config
  keys, storage) — which requires no privilege at all — and hands the
  operator a single **deployment sheet** for the project's AI: test URL,
  hook URLs, contract link and the token, shown once.

### Studio may deploy — and how it does so without becoming a second control plane

Decision 7 grants Studio the upload. The concern it raises is real: an
ordinary app that can install code is a second path to the platform's most
privileged action. The resolution is that Studio does not receive that
power — it **uses the same door as any other client**, and the platform
cannot tell the difference.

**Updating an existing instance — no new privilege at all.** Studio runs
the ordinary three-phase handshake of §2 against the instance's deploy
hook, authorised by that instance's deploy token. This is byte-for-byte
what the project's AI does. Studio gains nothing it could not already do by
holding a token, every check of §3 applies unchanged, and the audit trail
records it like any other deployment. That this path exists at all is the
point: it is the frequent case, and it is now free.

**Studio stores no token (Jörg, 2026-08-15).** The token is created in the
portal, kept by the operator (a password manager is the right place), and
**entered at the moment of each upload** — for the first deployment and for
every update alike. Studio holds it for the duration of one request and
nothing longer.

This preserves the Studio app's original decision *"Keine Deploy-Token im
Studio"* instead of overturning it, and it changes the exposure in a way
worth stating precisely:

- **At rest the exposure disappears.** No token in Studio's database, none
  in Studio's backup, nothing for a later reader of that volume to find.
- **In use it does not.** Studio must forward the token to the deploy hook,
  so a compromised Studio can capture it while it passes through. What the
  measure removes is *standing custody*, not *momentary custody*.
- **Which is exactly the part that mattered.** A stored token lets Studio
  deploy unasked, later, repeatedly. A pasted token lets Studio deploy
  only while the operator is present and deliberate. Every deployment
  through Studio therefore has a human in it — the same posture the
  envelope rule (§3) already takes for widening.

Required handling, because a pasted secret is easy to leak by accident:

- password-type field, never pre-filled, never echoed back, no
  autocomplete of Studio's own,
- **never in a URL, never in a log line** — the gateway records full
  request URIs including query strings (verified on `oaap-demo`,
  2026-08-08), so a token in a query parameter lands in cleartext in a log
  file,
- not retained in session state beyond the request that uses it.

The cost is small because Studio's upload is the **exception path, not the
daily one**: the project's AI deploys through the hook with its own copy of
the token and is unaffected. Studio uploads when a person is doing it by
hand — offline, from a file, without a forge — and in that situation the
person is at the keyboard anyway.

The result is one uniform rule for the whole Studio surface: **Studio never
holds a credential. Every privileged act carries one the operator supplies
at that moment** — a pasted deploy token for a deployment, a single-use
grant for a creation.

**Creating the first instance — a bounded, spendable grant.** Before an
instance exists there is no token, so this step genuinely needs privilege.
Rather than granting Studio a standing one, `server_admin` issues in the
portal an **instance creation grant**: single-use, short-lived, bound to
one instance name and one channel (`test`), spent by Studio for exactly one
creation, recorded in the deploy log, revocable before use. It is the same
mechanism as the upload token of §2, applied one level up — a *spendable*
permission, not a *held* one.

The distinction that matters: Studio never holds a capability it can reuse.
Every privileged thing it does is something the operator handed it, once,
for one named purpose — which is why this stays inside the platform's
security posture and does not reopen it.

**Node profile.** Both paths are development acts and therefore require the
node profile `dev` (RFC-0011), exactly as portal-created test instances do
today.

**Offline.** Both paths work with no forge and no internet: a file from a
stick, a browser on the LAN, a node that has never seen GitHub. This is the
scenario decision 7 names, and it is the one the Git path cannot serve at
all.

## Non-goals

- **No artifact deployment to production instances.** 2.5 is unchanged:
  deploy tokens exist only for test-channel instances. An administrator
  installing a production instance from an uploaded package by hand remains
  possible — that is 2.1's local upload, performed by a human.
- **No signature verification.** The artifact is authenticated by the
  channel (deploy token + upload grant), not by a signature over its
  content. Signed artifacts are a plausible later addition and would fit
  this handshake without changing it.
- **No replacement of the Git path.** Where a repository is reachable and
  its credential is the operator's own, Git remains the better path: it has
  history, and it needs no upload.
- **No general file upload API.** The only thing that may be uploaded is an
  app package, for one named instance, against a grant issued for exactly
  that package.

## Consequences for existing decisions

- **`oaap.apps.runtime` 2.5** — the sentence forbidding package upload on a
  deploy request is replaced by the three-phase handshake of §2 and the
  envelope rule of §3. Everything else in 2.5 stands: test channel only,
  digest-only storage, revocable, audited, throttled, no existence
  disclosure.
- **Studio's decision *"Keine Deploy-Token im Studio"* stands unchanged.**
  Decision 8 keeps it: the token is the operator's, entered per upload,
  never stored. Studio gains the ability to deploy without gaining custody
  of a key.
- **Backup content changes** — retained artifacts now travel in backups.
  That is a gain: the backup of an artifact-deployed instance is
  self-contained, which the Git path never was.

## Deutsche Zusammenfassung

**Das Problem — der geliehene Schlüssel.** Der bisherige Weg setzt Zugriff
auf das Git-Repository voraus. Bei einem privaten Repository heißt das: die
Plattform speichert einen fremden Zugangs-Token im Klartext in der Registry
und damit in jedem Backup (bei `bdt-hub-test` heute schon so). Für Dein
eigenes Repository erträglich — für ein Repository, das Dir nicht gehört
und vielleicht nie öffentlich wird, die falsche Richtung: **die Plattform
sammelt Schlüssel zu fremden Systemen.** Der ZIP-Weg dreht das um: wir
bekommen ein Artefakt, kein Zugangsrecht. Das einzige Geheimnis ist der
Deploy-Token — er zeigt auf uns, wir stellen ihn aus, wir allein können ihn
widerrufen. Für private Quellen ist das nicht bequemer, sondern
**sicherheitstechnisch besser**, und deshalb gehört es in die Plattform.

**Der Vorschlag.** Eine Instanz kann aus einer **hochgeladenen ZIP**
aufgebaut *und aktualisiert* werden — parallel zum Git-Weg, nie als Ersatz.
Der Ablauf ist Dein Drei-Phasen-Modell:

1. **Anmelden** — die KI meldet neue Version, das vollständige Manifest,
   Prüfsumme und Größe der ZIP.
2. **Prüfen und Freigeben** — die Plattform prüft Schema und Rahmen (siehe
   unten) und gibt bei Erfolg ein **Einmal-Token** zurück, 15 Minuten
   gültig, an genau diese Instanz und genau diese Prüfsumme gebunden. Bei
   Ablehnung kommt eine maschinenlesbare **und** eine verständliche
   Begründung zurück — Empfänger ist eine KI, die sich selbst korrigieren
   können muss.
3. **Hochladen** — nur mit diesem Token. Danach wird erneut geprüft: Größe,
   Prüfsumme, und ob das Manifest **in** der ZIP zeichengleich dem
   angemeldeten ist. Genau diese letzte Prüfung macht Phase 1 überhaupt
   ehrlich; ohne sie meldet man Harmloses an und lädt Anderes hoch.

Wichtig zur Einordnung: Das Einmal-Token ist **kein zweiter
Vertrauensfaktor** — wer den Deploy-Token hat, kann auch Phase 1. Es bringt
zwei andere Dinge: Ablehnung *vor* der Übertragung von 10 MB und einem
Build, und ein Upload-Endpunkt, der nicht dauerhaft offensteht.

**Die Regel für Ablehnungen.** *Ein Deploy-Token rollt innerhalb des
bereits erteilten Rahmens neu aus; alles, was den Rahmen erweitert, braucht
einen Menschen.* Das ist nichts Neues — die Referenz schützt heute schon
Adresse, Bremse, erteilte Ports und Gruppenbeschränkung vor einem
Deployment. Der RFC spricht es nur als Regel aus:

- **Harte Ablehnung:** geänderte App-Id, ungültiges Manifest, Manifest ≠
  angemeldet, Prüfsumme/Größe falsch, **unveränderte Version** (ohne
  Commit-Hash ist die Version das Einzige, was „was läuft da" beantwortet).
- **Ablehnung mit Bestätigungsmöglichkeit:** neue öffentliche Routen,
  aufgehobene Gruppenbeschränkung, neue feste Ports (RFC-0015), neue
  Verbindungen zu anderen Apps (RFC-0016), neue Storage-Mounts.
- **Läuft durch:** alles andere — neue Konfigurationsschlüssel, geänderte
  Texte, interne Umbauten. Das ist der Normalfall und muss reibungslos
  sein; ein Weg, der bei jedem Deployment nach Dir ruft, hat seinen Zweck
  verfehlt.

**Damit ZIP kein Sackgassenweg ist:** Die ZIP **bleibt auf dem Knoten
liegen** — mit Prüfsumme und Zeitstempel, samt Vorgänger. Dadurch gibt es
eine echte Quelle zum Neuausrollen, `oaap app list` kann sagen welches
Artefakt läuft, und ein Rückschritt ist eine normale Installation des
Vorgängers. Nebenwirkung: ein Backup einer ZIP-Instanz ist erstmals
wirklich vollständig — beim Git-Weg war es das nie.

**Entpacken** ist die scharfe Kante und steht deshalb in der Spec, nicht im
Code-Review: keine absoluten Pfade, kein `..`, keine Symlinks, Grenzen für
entpackte Gesamtgröße, Einzeldateigröße und Anzahl (gegen „Zip-Bomben"),
Prüfung *während* des Entpackens, immer in ein frisches Verzeichnis, und
der Instanzbaum wird erst ersetzt, wenn alles durch ist.

**Portal und Studio.** Das **Portal** behält die privilegierte Oberfläche:
ZIP beim Anlegen einer Test-Instanz, laufendes Artefakt mit Prüfsumme auf
der Instanzseite, Bestätigung einer Rahmenerweiterung, Rückschritt.
**Studio** liest das Manifest aus der ZIP, **prüft es** und füllt damit den
Vorhaben-Eintrag — dafür braucht es kein Sonderrecht — und gibt Dir den
**Deployment-Zettel** für die KI: Test-URL, Hook-Adressen, Contract-Link,
Token (einmalig).

**Und Studio darf hochladen (Deine Entscheidung 3).** Meinen Einwand —
eine normale App, die Code installieren kann, ist eine zweite
Steuerungsebene — habe ich nicht weggeschrieben, sondern konstruktiv
aufgelöst:

- **Bestehende Instanz aktualisieren: gar kein neues Recht.** Studio läuft
  dieselben drei Phasen wie die KI, gegen denselben Deploy-Hook, mit dem
  Deploy-Token der Instanz. Die Plattform kann Studio von einem beliebigen
  anderen Client nicht unterscheiden, alle Prüfungen greifen unverändert.
  Das ist der häufige Fall — und er ist damit umsonst zu haben.
- **Studio speichert keinen Token (Deine Ergänzung vom 15.08.).** Der
  Token wird im Portal erzeugt, **Du** verwahrst ihn (Passwortmanager),
  und er wird **bei jedem Upload eingegeben** — beim ersten wie bei jedem
  weiteren. Studio hält ihn nur für die Dauer der einen Anfrage.
  Wirkung: im Ruhezustand verschwindet die Aussetzung vollständig (nichts
  in Studios Datenbank, nichts im Studio-Backup). Bei der Benutzung
  bleibt sie — Studio muss den Token weiterreichen und könnte ihn dabei
  mitlesen. Weg ist also die **dauerhafte Verwahrung**, nicht die
  **augenblickliche**. Und genau darauf kam es an: ein gespeicherter Token
  ließe Studio ungefragt und wiederholt deployen, ein eingegebener nur,
  während Du dabeistehst. Damit steckt in jedem Studio-Deployment ein
  Mensch — dieselbe Haltung, die die Rahmenregel ohnehin einnimmt.
  Pflicht dabei: Passwortfeld, nie vorbelegt, nie zurückgezeigt, **nie in
  einer URL und nie in einer Logzeile** (das Gateway protokolliert die
  vollständige URI samt Query-String — am 08.08. auf oaap-demo
  nachgeprüft).
- **Erste Instanz anlegen: eine verbrauchbare Erlaubnis.** Vorher gibt es
  keinen Token, hier braucht es also echtes Recht. Statt Studio ein
  dauerhaftes zu geben, stellt `server_admin` im Portal eine
  **Anlege-Erlaubnis** aus: einmalig, kurzlebig, gebunden an einen
  Instanznamen und den Kanal `test`, protokolliert, vor Gebrauch
  widerrufbar. Dasselbe Muster wie das Upload-Token, eine Ebene höher.
- Der Unterschied, auf den es ankommt: Studio **hält** nie ein Recht, das
  es wiederverwenden kann. Alles Privilegierte ist etwas, das Du ihm im
  Augenblick der Handlung in die Hand gibst — ein eingegebener Deploy-Token
  fürs Deployment, eine einmalige Erlaubnis fürs Anlegen.
- Der Preis ist klein, weil Studios Upload der **Ausnahmeweg** ist, nicht
  der tägliche: die KI deployt über den Hook mit ihrer eigenen Kopie des
  Tokens und merkt von alldem nichts. Studio lädt hoch, wenn ein Mensch es
  von Hand tut — offline, aus einer Datei, ohne Git-Hoster. Dann steht der
  Mensch ohnehin an der Tastatur.
- **Offline** funktioniert beides ohne Internet und ohne Git-Hoster: Datei
  vom Stick, Browser im LAN, Knoten der GitHub nie gesehen hat. Genau das
  Szenario aus Deiner Begründung — und das einzige, das der Git-Weg
  überhaupt nicht bedienen kann.

**Ausdrücklich nicht:** kein ZIP-Deployment auf Produktiv-Instanzen (2.5
bleibt: Token nur für Test); keine Signaturprüfung (später möglich, ohne
den Ablauf zu ändern); kein Ersatz des Git-Wegs; keine allgemeine
Datei-Upload-Schnittstelle.

**Deine drei Entscheidungen vom 15.08. sind eingearbeitet:**

1. **Rahmenerweiterung darf im Portal bestätigt werden** (`server_admin`) —
   nicht nur an der Maschine. Sie bleibt ein bewusster, protokollierter
   Akt; der CLI-Zwang hätte Dich zurück in genau den Weg gedrängt, den
   dieser RFC abschaffen soll.
2. **Drei Vorgänger-ZIPs** werden aufgehoben — genug zum Vergleichen, nicht
   nur zum Zurückspringen.
3. **Studio darf hochladen** (Begründung: Benutzerfreundlichkeit und
   Offline-Szenarien) — in der oben beschriebenen begrenzten Form, und
   **ohne Token zu speichern** (Deine Ergänzung).

**Was beim Bauen mit umgestellt werden muss:** `oaap.apps.runtime` 2.5
enthält den Satz, dass ein Deploy-Request niemals ein Paket hochladen kann;
er wird durch den Drei-Phasen-Ablauf ersetzt. Alles Übrige aus 2.5 bleibt:
nur Test-Kanal, nur Hash gespeichert, widerrufbar, protokolliert,
gedrosselt, keine Auskunft über die Existenz einer Instanz. Die
Studio-README bleibt dagegen **gültig wie sie ist** — „Keine Deploy-Token
im Studio" überlebt Deine Ergänzung unverändert.

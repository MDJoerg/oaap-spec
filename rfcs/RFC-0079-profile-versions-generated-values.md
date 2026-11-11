# RFC-0079: Profile Versions and Generated Values

- **Status:** **Accepted (2026-11-11)** — D1–D9 as recommended (Jörg: "wie empfohlen"). Built in reference 0.1.251 (§7); `hbvp` still has to declare `generate: vapid` (D9, the app's author)
- **Date:** 2026-11-11
- **Authors:** Jörg (the observation: an uploaded profile shows no version;
  the wish to settle the push key for the fan app together with it), Claude
  (facts read in `tenant_build.py`, `appctl.py`, the portal, the runtime
  spec 2.8 `generate: token`, FAQ F37; design)
- **Depends on:** RFC-0055 (tenant build profile; §14 upload, §16
  `app.config`), `oaap.apps.runtime` 0.2.22 (`generate: token`)
- **Closes:** I-42 parts (2) and (3)
- **Not part of this RFC:** profiles that travel through the marketplace
  (RFC-0077 could carry them later as an asset type); migrating a tenant
  that was built from an older profile version to a newer one

## Summary

A tenant build profile gets an optional **version** (`x.y.z`). The node
keeps **every version** it was given, refuses a changed file under a version
it already holds, shows the version in the portal, and records in every
build which version and which digest it ran. A build that was interrupted
continues with **exactly the version it started with**, even after a newer
one was uploaded.

A step `app.config` may say **`"generate": true`** instead of a value. The
node then produces the value itself, of the kind the **app's manifest**
declares for that key, and only if the instance has **no value yet**. The
manifest gains a second kind besides `token`: **`vapid`**, a P-256 private
key for Web Push. The portal's "Erzeugen" button produces it as well.

## 1. What is there today

- A profile is `{"profile": "oaap.tenant-profile/1", "id": …, "title": …,
  "params": …, "steps": …}`. Its identity is its `id` alone.
- Uploading a profile with an id the node already holds **replaces it
  silently**. The previous file is gone.
- A build stores the profile's SHA-256 (`state["digest"]`). Continuing a
  build whose profile file changed since is **refused** ("start a new build
  instead"). The digest is shown nowhere.
- Unknown top-level keys of a profile are ignored by `profile_problems` — an
  older node accepts a profile that carries `version` and simply does not
  show it.
- The manifest's `config` entry may say `generate: token` (runtime 0.2.22):
  only for a key whose value the app itself defines; the portal produces
  32 random bytes as base64url and shows them until "Speichern". Any other
  `generate` value is recorded as "no".
- `app.config` (RFC-0055 §16) sets one key of one instance; a value never
  appears in a note, the audit trail or the deploy log. It requires `value`.
- A VAPID key (FAQ F37) is the 32-byte private scalar of a P-256 key pair as
  base64url; the app derives the public key from it. Each instance needs its
  own; replacing it invalidates every push subscription of that instance.

## 2. Versions

1. **Field.** `"version": "x.y.z"` (same form as an app version, optional
   pre-release `-…`). Optional; a profile without it counts as *without
   version* and is shown as such. The format string stays
   `oaap.tenant-profile/1` (D1).
2. **Upload rules** (D2) for an id the node already holds:

   | Uploaded | Current | Result |
   |---|---|---|
   | higher version | any | becomes current; the previous one stays in the history |
   | same version, same bytes | — | nothing changes (`no change`) |
   | same version, other bytes | — | **refused**: "Version 1.1.0 gibt es schon mit anderem Inhalt — Version erhöhen." |
   | lower version | — | **refused** |
   | without version | with version | **refused** |
   | without version | without version | becomes current; the previous one stays in the history |

   The comparison is numeric (`1.2.10` after `1.2.9`, `1.0.0` after
   `1.0.0-rc1`), the same function the marketplace uses.
3. **History** (D3). The node keeps every accepted file under its digest,
   with id, version, upload time and uploader. Portal → Aufbau shows the
   version beside each profile and a "Verlauf" with download per version.
   Deleting a profile removes the current file and its history, and is
   refused while a build that uses it is `running`, `waiting` or `failed`.
4. **Builds remember** (D4). A new build records `profile`, `version` and
   `digest`. The build page and the tenant's build list show
   "handballverein 1.1.0" and the first 12 characters of the digest.
5. **Continuing** (D5). A build loads its profile **by digest from the
   history**, not by id. Uploading a newer version no longer blocks an
   interrupted build; the refusal "the profile file changed" disappears.
   Only a build whose digest is missing from the history (a node before
   this RFC) keeps today's refusal.

## 3. Generated values

1. **In the profile** (D6). A step

   ```json
   {"id": "push-test", "type": "app.config", "name": "hvp-test",
    "key": "HIB_FAN_VAPID_PRIVATE", "generate": true}
   ```

   carries `generate: true` **instead of** `value` (both together, or
   neither, is a refusal). The profile never names the kind: **only the
   manifest knows** what the value is (D6, same rule as runtime 2.8).
2. **Check and run** (D7).
   - The instance has a non-empty value for the key: **done**, nothing is
     produced. This holds on a rerun, on a continued build and when the
     operator typed a value by hand. A generated value is **never
     replaced** by a build.
   - The key's manifest entry declares no `generate`: **conflict** — "Die
     App erlaubt nicht, dass der Knoten diesen Wert erzeugt."
   - Otherwise the node produces the value on the host, sets it through
     the same function `oaap app config set` uses, and writes "generated
     (vapid)" into the note and the audit trail — never the value.
3. **New kind `vapid`** (D8) in the manifest, beside `token`:
   32 random bytes taken as a big-endian integer, kept only if
   `1 ≤ k < n` (the order of P-256), else drawn again; written as base64url
   without padding — the format of FAQ F37. Produced by the host from the
   operating system's random source; no external tool. The portal's
   "Erzeugen" button offers it too (I-42 (2)), with the existing rule that
   a value is shown until it is saved.
4. **The app's part** (D9). The app declares
   `generate: vapid` on its key and derives the public key itself. For
   `hbvp` that is one line in `oaap-app.yaml` (`HIB_FAN_VAPID_PRIVATE`);
   the app's author makes it. An older node records the unknown kind as
   "no" and shows an ordinary secret field — nothing breaks.
5. **An older node and a newer profile.** A node before this RFC refuses a
   step with `generate` and without `value` ("needs 'value'") at upload —
   it fails closed, with a sentence, before anything runs.

## 4. The profile `handballverein` after this RFC

`version: 1.1.0`, and after the two `app.install` steps of `hvp-test` and
`hvp` each:

- `app.config` `HIB_MODE` = `club` (fixed),
- `app.config` `HIB_OPERATOR_NAME` = `{title}`,
- `app.config` `HIB_CONTACT` = `{contact}` (new optional parameter, kind
  text; empty leaves the key alone),
- `app.config` `HIB_FAN_VAPID_PRIVATE` with `generate: true` (behind a new
  bool parameter `push`, default true — the step is skipped without it).

What remains by hand: the deploy token for `hvp-test` and the partners in
the Vorgänge.

## 5. Stage and measurements

One stage, reference + spec (`oaap.core.tenant` profile section,
`oaap.apps.runtime` 2.8), then `oaap-docs` (checklist, F37, profile).
Measured on `oaap-test`:

- **V1** upload 1.0.0, then 1.1.0: both in the history, 1.1.0 current.
- **V2** 1.1.0 again with the same bytes: no change; with other bytes:
  refused, nothing stored.
- **V3** 1.0.1 after 1.1.0: refused. Unversioned over versioned: refused.
- **V4** a build started on 1.0.0, interrupted at the waiting point; upload
  1.1.0; continue: the build finishes on 1.0.0 (its digest), the page says
  1.0.0.
- **V5** delete refused while a build is open; after it is done, delete
  removes current and history.
- **G1** a probe app with `generate: vapid`: a build sets a value; it is a
  valid P-256 scalar (public key derivable); it appears in no note, audit
  line, deploy log or build state file.
- **G2** a second build / continue: the value is unchanged.
- **G3** a value typed by hand first: the build leaves it.
- **G4** a key without `generate` in the manifest: conflict with the
  sentence, nothing set.
- **G5** portal "Erzeugen" on a `vapid` key: shows a valid key, stores
  nothing until "Speichern".
- **G6** two instances from one build get two different keys.

## 6. Decisions for Jörg

| | Question | Recommendation |
|---|---|---|
| D1 | `version` optional, format stays `/1` | yes — old profiles keep working, older nodes ignore the field |
| D2 | upload rules as in the table §2.2 | yes — same as releases in the marketplace |
| D3 | keep every version on the node; delete removes all, not while a build is open | yes |
| D4 | builds show profile, version, digest | yes |
| D5 | continue by digest from the history | yes — removes today's dead end |
| D6 | `generate: true` in the profile, kind only from the manifest | yes — the profile cannot generate into somebody else's credential |
| D7 | generate only into an empty key, never replace | yes — replacing a VAPID key kills every subscription |
| D8 | new manifest kind `vapid`, also behind the portal button | yes |
| D9 | `hbvp` declares `generate: vapid` itself (app author) | yes — Jörg passes it to the hbvp session |

## 7. Built and measured (2026-11-11, reference 0.1.251)

- **Code:** `services/gen_values.py` (one generator for the portal button
  and the build step: `token`, `vapid`), `tenant_build.py` (version field
  and ordering, `upload_decision`, history under
  `profiles/.history/<id>/<digest>.json` with a `.meta.json`, `app.config`
  with exactly one of `value` / `generate: true`), `appctl.py` (upload by
  the rules, the replaced file kept first -- also one written on the
  machine; delete takes the history; a build keeps its file at start and
  continues by digest; the drivers generate only into an empty key), the
  portal (version column, page "Verlauf" with a download per file, version
  and digest on the build page and in the list, button "Push-Schlüssel
  (VAPID) erzeugen").
- **Tests:** `test_profile_versions.py` 33/33; `test_tenant_build`,
  `test_tenant_build_doors` (the digest refusal now only without the kept
  file), `test_tenant_build_config`, `test_config_generate` green.
- **Live on `oaap-test`:** host side with a probe app (`vapid-probe`, three
  instances, a node-written profile): V4 continue on 1.0.0 after 1.1.0
  replaced the file, G1 valid P-256 scalar (public point checked on the
  curve), no value in state, audit, views or logs, G2, G3 (typed by hand
  stays), G4 (conflict sentence, nothing set), G6 -- all PASS. Portal side
  16/16: V1-V3, list and history page, download of the old file, build page
  with version and digest, V5 (delete takes the history; refused while a
  build is open), G5 (the button shows a valid key).
- **Found while building:** `generate: "vapid"` (text) slipped through the
  general text check of a step; it is now refused -- the kind belongs to
  the manifest.
- **Profile `handballverein` 1.1.0** (`oaap-docs`): mode, operator name,
  contact in both portals; push behind the tick `push` (default off until
  `hbvp` declares `generate: vapid`).

## Zusammenfassung für Jörg (Deutsch)

**Versionen:** Ein Profil bekommt eine Versionsnummer (`1.1.0`). Der Knoten
hebt **jede Fassung** auf. Eine höhere Version ersetzt die aktuelle, die
gleiche Version mit anderem Inhalt wird abgelehnt, ebenso eine ältere. Im
Portal steht die Version neben dem Profil, dazu ein Verlauf zum
Herunterladen. Jeder Aufbau zeigt, mit welcher Version er lief. Ein
unterbrochener Aufbau läuft mit **seiner** Version weiter, auch wenn
inzwischen eine neuere hochgeladen wurde. Das löst eine heutige Sackgasse:
bisher wurde das Fortsetzen dann verweigert.

**Erzeugte Werte:** Im Profil kann bei `app.config` statt eines Werts
`"generate": true` stehen. Der Knoten erzeugt den Wert dann selbst. **Welche
Art** von Wert, sagt nur das Manifest der App, nie das Profil. Neu ist neben
`token` die Art `vapid` (Push-Schlüssel). Der Wert wird **nur erzeugt, wenn
noch keiner da ist**, nie ersetzt, denn ein neuer Push-Schlüssel würde alle
Fan-Abos ungültig machen. Er erscheint in keinem Protokoll. Der Knopf
„Erzeugen“ im Portal kann es dann auch.

**Für hbvp:** Die App muss im Manifest eine Zeile ergänzen
(`generate: vapid` bei `HIB_FAN_VAPID_PRIVATE`). Das macht die hbvp-Sitzung,
du gibst es weiter. Danach setzt das Profil `handballverein` 1.1.0
Betriebsmodus `club`, Betreibername, Kontakt und den Push-Schlüssel je
Instanz selbst. Von Hand bleiben nur der Deploy-Token und die Partner.

# RFC-0037: Sideloading — Installing a Package Into Production Without a Store

- **Status:** Draft (2026-09-11) — D1 and D2 decided by Jörg; D3 proposed,
  awaiting decision; the whole awaiting acceptance
- **Date:** 2026-09-11
- **Authors:** Jörg (idea, D1, D2), Claude (design and write-up)
- **Depends on:** RFC-0008 (`server_admin`), RFC-0011 (node profiles),
  RFC-0012 (store sources), RFC-0019 (artifact deployment), RFC-0020
  (promotion), RFC-0022 (tenant audit log)
- **Extends:** `oaap.core.host` 2.5 (a new profile), `oaap.apps.runtime`
  2.6 (portal installs), 2.14 (artifact deployment), 2.14.1 (the paths to
  production). Nothing here is withdrawn.
- **Driver:** Jörg has a self-built OAAP app as a ZIP and wants it running
  on **another** node, on the production channel — without putting it
  into a curated store list and without first creating a test instance
  there. The model he named is Android: an APK can be installed directly,
  next to the Play Store, once the owner of the device allows it.

## Summary

On a node with the profile **`sideload`**, a `server_admin` may upload an
app package in the portal and install it **directly into a production
instance** — a new one, or an update of an existing one.

Android does not simply allow sideloading; it surrounds it with
safeguards. This RFC takes over the ones that translate:

| Android | OAAP |
|---|---|
| "Install unknown apps" is **off** until the owner switches it on | the profile `sideload`, empty by default, set **only on the machine** |
| permissions are shown **before** installing | the package's **envelope** and **checksum** are shown before anything installs; installing is an explicit confirmation |
| app info says **where an app came from** | the instance's origin reads *uploaded*, with person, time and checksum, and the act is in the tenant's audit log |
| an update must carry the **same signing key** | **not available** — OAAP packages are unsigned (RFC-0019 non-goal). The interim substitute is weaker and named as such: same app id, higher version, and a checksum a person can compare |

## Motivation

### The paths to production today, and the gap between them

| Path | Needs |
|---|---|
| Store one-click (2.6) | the app in a configured store list |
| Promotion (2.14.1, RFC-0020) | a tested artifact in a test instance **on the same node** |
| `oaap app install <zip>` (2.1) | a terminal on the target node |

Jörg's case falls between all three: the app is finished, the ZIP is in
hand, the target is a different node. It *can* be done today — download
the retained package from the source node (2.14, 0.2.21), copy it over,
install on the command line. But that makes every such rollout an
administration act at a terminal, which is exactly the argument RFC-0020
already accepted for promotion: *the portal is where the decision
belongs, because that is where the person is who is allowed to make it.*

### Why not the `dev` profile

`dev` is a workbench: it creates **test** instances from the portal and
relaxes where a *source* may come from. Putting `dev` on a production
machine to get an upload button would hand that machine both relaxations
for the price of one wish. `sideload` is narrower: one kind of input (an
uploaded package), one channel (production), one role, and nothing about
Git sources.

### Why not wait for promotion across nodes

Cross-node promotion (RFC-0020 "Open for later", capability ideas
2026-08-23) is the stronger answer: the same bytes, carried by an
authenticated node-to-node path. It depends on the fleet's write path
(RFC-0021 stage 2, signed commands) and is not near. Sideloading does not
replace it — it is its **manual precursor**: the checksum shown before
installing lets a person verify by eye that the package is the one that
ran in test on the other node.

### What a `sideload` node gives up

This has to be stated, the way RFC-0011 stated the cost of `dev`. The
property of 2.6 is: *a compromised portal can at worst install apps the
`server_admin` already chose to trust*, because the portal names only an
app id and the host resolves it. **On a `sideload` node that property is
given up for production**: a compromised portal, or a stolen
`server_admin` session, can put arbitrary code into a production
instance.

The compensating controls are the design: off by default and set at the
machine, `server_admin` only, full review and explicit confirmation,
visible origin, an audit record, and the ordinary rollback. Whether that
trade is right is a **per-node** decision — reasonable on a node that
runs its owner's own apps, questionable on a node that hosts other
people's tenants.

## Design

### D1 — A node profile `sideload` (decided 2026-09-11)

Effects, and this list is deliberately exhaustive:

1. The portal may **create a production instance** from an uploaded
   package.
2. The portal may **update an existing production instance** from an
   uploaded package (D2, within D3).
3. Nothing else.

Consequences of being a profile (`oaap.core.host` 2.5):

- **Set on the machine:** `sudo oaap node add-profile sideload`. The
  first-run wizard does **not** offer it — like Android's switch, it is
  turned on when first needed, not at setup.
- **Visible:** `oaap status` and the health page name it.
- **Independent:** `sideload` does not imply `dev`, and `dev` does not
  imply `sideload`. A node may hold both.
- **Removing it** stops the portal from offering uploads. Nothing that
  was sideloaded is removed or changed; such instances keep running and
  can still be updated on the command line or rolled back.

### D2 — New instances and updates (decided 2026-09-11)

**A new instance:** the name must be free and well-formed, the instance
is created on the **production** channel, in the tenant the issuer's own
record names (the rule everywhere, `oaap.core.tenant` 1.4).

**An update** follows the rules promotion already established
(2.14.1), because it is the same act with a different origin of the
bytes:

- the target is on the **production** channel;
- the package's **app id matches** the target — an instance belongs to
  one app;
- the package's **version is higher** than what runs — going back is a
  rollback (retention, RFC-0019), a different and deliberate act;
- the **envelope is reviewed against the target**; a widening is not
  refused, but shown in full and confirmed;
- the target **keeps** its data, configuration values, address(es),
  visibility, tile, brake, granted endpoints and links. Only the package
  changes.

### D3 — Which production instances an upload may update (proposed)

**Proposal:** only instances whose current source is **already a
package** (`kind: "artifact"`) — that is, instances that were sideloaded,
promoted (RFC-0020) or installed from a ZIP on the command line. An
instance installed from a store list or a Git URL is **refused**, with
the sentence: *"This instance gets its updates from <source>. Switching
it to uploaded packages is done on the machine."*

**Why:** an instance has one answer to "where do my updates come from".
If an upload could silently replace a store-installed instance, the
store would later offer an "update" that overwrites the uploaded code —
or the other way around — and neither the portal nor the operator would
see the conflict coming. This is the one place where Android's signature
rule, which OAAP cannot yet enforce, is approximated by a rule OAAP can:
an app that did not come from a package cannot be replaced by a package
from the browser.

**Alternative:** allow it with a second, explicit confirmation ("the
instance will no longer follow <source>"). Simpler for the user, but it
turns a rare, structural change into a checkbox.

### Review before install

Nothing installs on upload. The act has two steps, and the host carries
both:

1. **Upload and review.** The portal streams the file into the spool
   (as the `dev` path does today) and asks the host to review it. The
   host applies the untrusted-archive rules of 2.14 (paths, links, entry
   count, size while unpacking), validates the manifest (2.2, including
   `must_understand`) and answers with:
   - app id, name, version, package size, **SHA-256**;
   - the target: *new instance* or *update of X, running version Y*;
   - for a new instance, the **whole envelope** — every route reachable
     without login, every declared endpoint, every storage mount, the
     profiles the app expects (RFC-0011); there is nothing to compare
     against, so all of it is new;
   - for an update, the **widening** against the target, or the plain
     statement that there is none;
   - a hard refusal with its reason, if any rule above fails.
2. **Confirm and install.** The confirmation names the **checksum** and
   the **target** it was given for. The reviewed file stays in the spool
   for at most **15 minutes** (the upload grant's lifetime, 2.14) and is
   then deleted.

The portal page says in plain words what is being confirmed, e.g.:
*"Dieses Paket stammt aus keiner Store-Liste. Prüfen Sie Herkunft und
Prüfsumme, bevor Sie es in Produktion installieren."* An unread
confirmation is worse than a refusal, so the envelope is named in full,
never summarised as a count.

### What is checked, on the host

The spool is data, not trust. At **install** time the host re-checks
everything, even what the review already checked:

1. The node holds `sideload` — at review **and** at install.
2. The requester is `server_admin`, decided from the host's own user
   record.
3. The file's SHA-256 equals the confirmed checksum.
4. The target is still what was reviewed. If the target changed in
   between (another upload, a promotion, a rollback), the install is
   refused with *"the instance changed since the review — upload
   again"*, because the version comparison and the widening were
   computed against a state that no longer exists.
5. New: the name is still free. Update: D2's rules, and D3.
6. No deploy token and no grant is created as a side effect; production
   instances still never carry one (2.5).

### What is recorded

- The instance's source is an artifact source that names its origin:
  `sideloaded_by` (the user), `received` (the time), `sha256`. The
  portal shows it under *Überblick → Herkunft* as *"hochgeladen von …
  am …"*, next to RFC-0020's *"übernommen aus …"*.
- The **tenant audit log** (`oaap.core.tenant` 1.7) records who, when,
  which instance, new or update, version, checksum, and — in full — the
  widenings that were confirmed.
- Retention applies as always (current plus three predecessors), so the
  way back is the existing rollback.

### Who

**`server_admin` only.** Not `tenant_admin`, not an app, not the Studio,
not a deploy token, not a grant. Putting code into production inside a
tenant is operator power; whether a tenant's own administrator should
ever hold it is the mirror image of the ownership question the package
download (2.14, 0.2.21) deliberately left open, and it stays open here
for the same reason.

### Interfaces

- **Portal — Store page:** on a `sideload` node, a card *"Paket
  hochladen"* next to the store lists: choose file, choose *new instance
  (name)* or *update (existing production instance)*, then the review
  page, then one button. On a node **without** the profile, the page
  says in one line that this exists and that it is switched on at the
  machine with `sudo oaap node add-profile sideload` — an absent
  possibility is explained, not hidden.
- **Portal — production instance page, section *Deployment*:** *"Neues
  Paket hochladen"*, leading to the same review page with the target
  preset. Shown only on a `sideload` node and only where D3 allows it.
- **Portal — hint towards promotion:** if the node already has a test
  instance of the same app whose retained package has the **same
  checksum**, the review page SHOULD point out that promotion (RFC-0020)
  does the same with a proven origin.
- **CLI:** `oaap app install <zip> [--name N]` exists and keeps working
  **without** the profile — at the machine, the person is the authority
  (2.1). It gains what the portal path requires, so both paths apply the
  same rules to production:
  - for an existing production instance, the envelope review with
    `NOTE:` lines and **`--confirm`** before a widening proceeds (today
    this review runs only for test instances — see Consequences);
  - the higher-version rule of D2;
  - the origin record (`sideloaded_by: cli`).

## Non-goals

- **No unattended path to production.** No token, grant, Studio, AI,
  hook or schedule can sideload. Every sideload has a person in it.
- **No upload of a URL.** The portal does not fetch a package from an
  address; a place to fetch from is a *source*, and sources belong to the
  store lists (RFC-0012).
- **No change to `dev`.** Portal-created test instances stay `dev`'s.
- **No signature verification.** Packages remain unsigned (RFC-0019).
- **No `tenant_admin` sideloading** (see *Who*).
- **Not a replacement for promotion.** Where a tested package already
  lies on the same node, promotion is the better path, and the portal
  says so.

## Consequences

For the specification, after acceptance:

- **`oaap.core.host` 2.5** — defined profile `sideload`, with D1's
  exhaustive effects.
- **`oaap.apps.runtime` 2.6** — a second exception to "the portal
  creates test instances": on a `sideload` node, a `server_admin` may
  create a production instance from an uploaded package.
- **`oaap.apps.runtime` 2.14** — new subsection *2.14.2 Sideloading*
  (review before install, host re-checks, D2, D3, recording). 2.14.1's
  sentence *"This is the one path from an uploaded package to
  production"* becomes *"one of two portal paths"*; RFC-0019's non-goal
  *"No artifact deployment to production instances"* is clarified as
  *no token- or grant-based* deployment to production, which stays true.
- **`oaap.core.tenant` 1.7** — the sideload entry in the audit log.

For the reference implementation:

- `sideload` in the profile table (`appctl.py`), a review action and an
  install action in the spool worker, the Store card and the instance
  section in the portal.
- **A gap found while writing this RFC, fixed in the same round:** the
  CLI's ZIP path runs the envelope review only when both the request and
  the instance are on the test channel. Updating a **production**
  instance from a ZIP on the command line therefore installs a widening
  without saying so. Promotion already shows and requires `--confirm`;
  the CLI ZIP path gets the same.

## Open for later

- **Signed packages.** A publisher key per app would give updates
  Android's full rule — *only the same publisher may replace this app* —
  and would make D3's approximation unnecessary. It fits RFC-0019's
  handshake without changing it; the unsolved part is the same key
  distribution question RFC-0012 named for signed lists.
- **Promotion across nodes** — the authenticated form of what a person
  does here by comparing a checksum.
- **Sideloading by `tenant_admin`** — together with the package download
  question, once supplier ownership inside a tenant is decided.

## Deutsche Zusammenfassung

**Worum es geht:** Eine selbstgebaute App als ZIP-Datei soll direkt in
den Kanal **Produktion** eines Knotens — ohne Store-Liste und ohne
Test-Instanz auf diesem Knoten. Vorbild ist das Sideloading von APKs bei
Android.

**Heute** geht das nur an der Kommandozeile (`sudo oaap app install
app.zip`). Im Portal gibt es den Paket-Weg nur für Test-Instanzen
(Profil `dev`) und die Übernahme nach Produktiv nur auf demselben Knoten.

**Der Vorschlag**, mit Androids Sicherungen:

- **D1 (entschieden):** neues Knotenprofil **`sideload`** — ab Werk aus,
  nur an der Maschine einschaltbar (`sudo oaap node add-profile
  sideload`), unabhängig von `dev`.
- **D2 (entschieden):** gilt für **neue** Produktiv-Instanzen **und für
  Updates** bestehender. Bei Updates dieselben Regeln wie bei der
  Übernahme: gleiche App-Kennung, höhere Version, Rahmen-Erweiterungen
  werden vollständig angezeigt und bestätigt, Daten und Einstellungen
  der Instanz bleiben.
- **D3 (vorgeschlagen, deine Entscheidung):** Ein Upload darf nur
  Instanzen aktualisieren, die schon aus einem Paket stammen
  (hochgeladen, übernommen, per ZIP installiert). Eine Instanz aus dem
  Store oder aus Git wird im Browser nicht umgestellt — sonst würde der
  Store später ein „Update" anbieten, das den hochgeladenen Code
  überschreibt. Das ist unser Ersatz für Androids Signaturregel, die wir
  mangels signierter Pakete noch nicht haben.
- **Erst prüfen, dann installieren:** Nach dem Upload zeigt das Portal
  App, Version, **Prüfsumme** und den **Rahmen** (öffentliche Adressen,
  Ports, Speicher). Installiert wird erst nach Bestätigung, innerhalb von
  15 Minuten; der Knoten prüft beim Installieren alles noch einmal.
- **Nachvollziehbar:** Die Instanz zeigt „hochgeladen von … am …", der
  Vorgang steht im Audit-Log des Mandanten, der Rückweg ist der normale
  Rollback.
- **Nur `server_admin`** — keine KI, kein Token, kein Studio, kein
  Mandanten-Admin.
- **Der Preis, offen gesagt:** Auf einem `sideload`-Knoten kann ein
  gekapertes Portal oder eine gestohlene Admin-Sitzung beliebigen Code
  in Produktion bringen. Deshalb eine Entscheidung je Knoten.

**Nebenbefund:** Die Kommandozeile zeigt beim ZIP-Update einer
**Produktiv**-Instanz heute keine Rahmen-Erweiterung an; das wird im
selben Zug an die Übernahme angeglichen (`--confirm`).

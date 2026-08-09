# RFC-0014: The Manifest Owns the Words

- **Status:** Draft (2026-08-09) — six open questions, decisions pending
- **Date:** 2026-08-09
- **Authors:** Jörg (the principle: the maker should carry the
  responsibility and hold the power over the texts), Claude (write-up)
- **Depends on:** RFC-0004 (manifest), RFC-0012 (list format, §1.2/§1.3),
  RFC-0013 (the Store Editor, which is where the gap became visible)
- **Touches:** `oaap-app.schema.json` (manifest 0.3),
  `oaap.apps.runtime`, `oaap.core.portal` (store page)

## Summary

RFC-0012 §1.3 splits a store entry into **generated** (from the
manifest) and **editorial** (a human's judgement). Building the Store
Editor showed the split does not hold: of the eleven fields §1.3 calls
generated, the manifest can supply **five**. Everything a user actually
reads in a catalogue — the one-liner, the long text, the categories,
the maturity, the links — is editorial, which means it is written by
whoever catalogued the app rather than by whoever built it.

Jörg's direction (2026-08-09): **as much as possible should live in the
manifest, so the maker carries the responsibility and holds the power
over the texts.** This RFC proposes manifest **0.3** with a `catalog:`
block and works out what that costs.

## Motivation

### The evidence is our own catalogue

The Store Editor's manifest-maintenance report (build step 2) exists to
tell an app's maintainer what their manifest fails to back up. Run
against our eight apps, almost every line it produces says *"the format
does not know this field"*. **A report that can only ever ask for two
fields is itself the finding.** The manifest can carry `class` and a
short `description`; everything else the catalogue claims has no home
in the package.

### The principle, restated and then moved

RFC-0012 §1.3 puts it well: *the manifest is the truth about what the
app is; the list is the truth about how it is presented and
classified.* Jörg's direction moves the boundary, and the reason holds
up: **how an app presents itself is part of what it is**, at least as
far as its maker is concerned. A description written by a cataloguer is
a second-hand account, and it goes stale silently — the app changes,
the catalogue text does not, and nothing detects it. The version
mismatch we already check for is the same failure in a field where we
happen to have a comparison.

What genuinely remains the catalogue's is **curation**, not
description: which apps appear at all, under which categories *for this
audience*, with what warnings, in what order.

### Precedent: `app_class` already made this move

RFC-0012 §1.3's addendum moved `app_class` from editorial to
manifest-generated, for three reasons — the node must answer offline,
a foreign list must not rearrange a stranger's launchpad, and a value
re-read from a list drifts. Only the first two are about consequences.
The third — **drift** — applies to text just as much: a description
that lives only in a catalogue diverges from the software it describes,
and nobody notices.

## Proposal

### 1. Manifest 0.3 gains a `catalog:` block

```yaml
oaap_manifest: "0.3"

app:
  id: uptime-kuma
  name: Uptime Kuma
  version: 1.23.0
  type: wrapped
  class: frontend
  description: "Überwacht Dienste und meldet Ausfälle."   # THE one line
  icon: icon.svg                                          # relative to the PACKAGE
  profiles: [dev]                                         # RFC-0011

catalog:
  description: |                                          # the long text
    Uptime Kuma prüft in einstellbaren Abständen …
  categories: [monitoring, iot]
  audience: [operator]
  maturity: beta
  status: active
  tags: [uptime, alerting]
  license: MIT
  links:
    - { rel: homepage, url: "https://…" }
    - { rel: docs, url: "https://…" }
  screenshots:
    - { src: shots/1.png, caption: "Übersicht" }
```

**Why a separate block rather than more keys under `app:`.** `app:` is
what the platform acts on — identity, version, packaging, class,
profiles. `catalog:` has **no runtime effect whatsoever**: a node that
ignores it installs exactly the same software. Keeping them apart says
that in the structure instead of in a comment, and it gives a natural
home to anything added later for presentation.

`app.description` stays where it is and keeps its job: the **one line**
shown at the instance. `catalog.description` is the long text. That is
also the mapping the Store Editor's report already uses — the list's
`summary` is offered as `app.description`, and the list's long
`description` has nowhere to go today.

### 2. The list still carries a generated copy

Unchanged from §1.3 and for the same reason: **a store page has only
the list.** It cannot fetch eight manifests to render one page, and on
a node whose source is disabled or unreachable it could not fetch any.
So the list keeps `summary`, `description`, `categories` and the rest —
generated at publishing time, exactly like `roles` and `app_class`
today.

What changes is not the list format. It is **who the author is**.

### 3. The marked override stays — and stops being exceptional

RFC-0012 §1.3 already requires that an override of a generated value be
*marked*, so the next regeneration does not silently undo it. The Store
Editor implements this (build step 2). Nothing here weakens it: a
cataloguer may always disagree with a maker's words.

But the honest observation is that **overrides will become common, not
rare**, and the reason is language (see question 4). That is not an
argument against this RFC; it is an argument for taking the override
mechanism seriously as a first-class path rather than an escape hatch.

### 4. Not a `must_understand` feature

A reader that ignores `catalog:` shows a duller entry. It does not
install anything half-understood. Same reasoning as `app_class`
(RFC-0012 §8.2): `must_understand` is for features whose absence
produces a broken install, and using it anywhere else makes every
format extension a flag day.

### 5. The cost, stated plainly

**After this, a foreign maintainer's words appear in your catalogue.**
Today a cataloguer writes them; afterwards a regeneration pulls them
from a package somebody else controls. Three things bound it, and none
of them is new:

- Regeneration is **always explicit** — a button, never automatic.
- The checker shows what would change before it changes, and the change
  summary separates generated from editorial (RFC-0013).
- The override is marked and survives.

A fourth bound exists at the other end: on any node that is not the
publisher's, the list arrives with a trust class, and an `unverified`
one costs a confirmation before anything installs (RFC-0012 §3).

## Open questions

Recommendations included, decisions Jörg's.

**1. `catalog:` block, or more keys under `app:`?**
*Recommendation: a separate `catalog:` block*, because it has no
runtime effect and `app:` does. The cost is one more level of nesting
in a file people write by hand.

**2. Do `maturity` and `status` belong to the maker?**
*Recommendation: yes.* "beta" and "deprecated" are statements about
one's own software, and a cataloguer who leaves `status: active` on an
abandoned app is publishing a falsehood the maker had already
corrected. Counter-argument worth hearing: a cataloguer may consider an
app "beta" *for their audience* even if its maker calls it stable —
that is exactly what the marked override is for.

**3. `icon` — how does the file reach the catalogue?**
The schema already has `app.icon`; the obstacle is the reference point.
In a list, an image path is relative to **the list** (RFC-0012 §1.1, so
that opening a store page never contacts a host nobody chose); in a
manifest it is relative to **the package**.
*Recommendation: the editor copies the file into the list repository
when publishing* (build step 3, which writes anyway). The alternatives
are worse: leaving `icon` editorial keeps the one field users notice
first out of the maker's hands, and letting a list point into a foreign
repository breaks §1.1.

**4. Languages — now or later?**
The maker writes one language. Our catalogue is German; a foreign app
writes English, and a German maker's app in an international catalogue
has the same problem mirrored.
*Recommendation: nothing now*, and say so out loud rather than leaving
it implied — i18n touches the manifest, the store page and the portal
at once and deserves its own RFC. **But this is the reason overrides
will be common**, and that changes how the Store Editor should present
them: not as a warning, as a normal way of working.
Alternative if you want it now: `catalog.description.de` / `.en`, with
a fallback chain. It is not hard; it is just wide.

**5. Does `profiles` move too, and into which block?**
*Recommendation: yes, and into `app:` rather than `catalog:`* — it has
a **consequence** (the store filters and warns, RFC-0011), and the
`app_class` decision established that fields with consequences belong
to whoever built the software. This also closes one of the four §1.3
gaps found in build step 1.

**6. What happens to `released`?**
*Recommendation: it does not move.* It is the date of a Git tag, i.e. a
property of the repository, not a statement anybody should maintain by
hand — a hand-kept release date is wrong the first time somebody
forgets. It stays a field the publishing step fills in. This leaves
§1.3 with exactly one field it calls generated and cannot generate, and
that is honest rather than aspirational.

## Consequences for RFC-0012 §1.3

If this is accepted, §1.3's two groups become three, and the middle one
is the interesting one:

| Group | Fields | Author |
|-------|--------|--------|
| Identity and runtime | `id`, `name`, `type`, `version`, `class`, `roles`, `profiles`, `package` | the manifest (and the repository) |
| Presentation | `summary`, `description`, `categories`, `audience`, `tags`, `maturity`, `status`, `license`, `links`, `screenshots`, `icon` | the manifest, **overridable with a mark** |
| Publishing | `released` | the publishing step |

The "roughly six inputs a human must think about" from §1.3 then drops
to nearly zero for a well-maintained app — and the Store Editor becomes
what it should be: a **curation** tool, not a text editor.

## Deutsche Zusammenfassung

**Worum es geht.** Jörgs Richtungsentscheidung vom 09.08.2026: So viel
wie möglich soll im **Manifest** stehen, damit der „Hersteller" die
Verantwortung trägt und die Macht über die Texte hat. Dieser RFC
schlägt dafür Manifest **0.3** mit einem eigenen Block `catalog:` vor.

**Warum das nötig ist — der Beleg kommt aus unserem eigenen Katalog.**
Der Nachpflege-Bericht des Store Editors soll einer App sagen, was ihr
Manifest nicht belegt. Gegen unsere acht Apps gehalten, sagt fast jede
Zeile: *„das Format kennt dieses Feld nicht".* **Ein Bericht, der nur
zwei Felder überhaupt einfordern kann, ist selbst der Befund.**

**Das Prinzip verschiebt sich, und die Begründung trägt.** RFC-0012
§1.3 sagt: Das Manifest ist die Wahrheit darüber, *was* die App ist;
die Liste darüber, wie sie *dargestellt* wird. Jörgs Richtung
verschiebt die Grenze — wie eine App sich darstellt, gehört zu dem, was
sie ist, jedenfalls aus Sicht dessen, der sie gebaut hat. Eine
Beschreibung aus zweiter Hand veraltet **still**: Die App ändert sich,
der Katalogtext nicht, und niemand merkt es. Genau dieses Driften war
schon das dritte Argument dafür, `app_class` ins Manifest zu holen.

Was dem Katalog wirklich gehört, ist nicht die Beschreibung, sondern
die **Kuratierung**: welche Apps überhaupt drinstehen, unter welchen
Kategorien *für dieses Publikum*, mit welchen Warnungen.

**Die Liste behält eine erzeugte Kopie** — sie muss, denn eine
Store-Seite hat nur die Liste und kann nicht acht Manifeste holen, um
eine Seite zu zeichnen. Es ändert sich nicht das Format, sondern
**wer der Verfasser ist**.

**Der Preis, offen gesagt:** Danach stehen die Worte eines fremden
Pflegers in Deinem Katalog. Begrenzt wird das durch dreierlei, das es
alles schon gibt: Die Neuerzeugung passiert **immer ausdrücklich** (ein
Knopf, nie automatisch), der Prüfer zeigt vorher, was sich ändern
würde, und die **markierte Übersteuerung** überlebt jede Neuerzeugung.

**Sechs Fragen sind offen** — Empfehlungen stehen dabei, entschieden
wird von Dir:

1. **Eigener Block `catalog:` oder mehr Schlüssel unter `app:`?**
   Empfehlung: eigener Block. Er hat **keinerlei Wirkung im Betrieb**,
   `app:` schon — das sollte man der Struktur ansehen.
2. **Gehören Reifegrad und Stand dem Hersteller?** Empfehlung: ja. Ein
   Katalog, der `status: active` auf einer aufgegebenen App stehen
   lässt, verbreitet eine Unwahrheit, die der Hersteller längst
   korrigiert hatte. Gegenargument: Ein Kataloghalter darf eine App
   *für sein Publikum* anders einschätzen — dafür gibt es die
   markierte Übersteuerung.
3. **Das Bild — wie kommt die Datei in den Katalog?** `app.icon` gibt
   es schon; das Hindernis sind die Bezugspunkte (im Katalog relativ
   zur Liste, im Manifest relativ zum Paket). Empfehlung: **Der Editor
   kopiert die Datei beim Veröffentlichen** ins Listen-Repository — das
   kann Bauschritt 3, der ohnehin schreibt.
4. **Sprachen — jetzt oder später?** Empfehlung: **später**, aber
   ausdrücklich gesagt statt stillschweigend vertagt. Und daraus folgt
   etwas für heute: **Übersteuerungen werden der Normalfall, nicht die
   Ausnahme** — ein deutscher Katalog und ein englisches Manifest sind
   genau dieser Fall. Der Editor sollte sie entsprechend darstellen:
   als gewöhnlichen Arbeitsweg, nicht als Warnung.
5. **Wandern die Knotenprofile mit?** Empfehlung: ja, aber nach `app:`
   und nicht nach `catalog:` — sie haben eine **Wirkung** (der Store
   filtert und warnt), und für Felder mit Wirkung gilt seit der
   `app_class`-Entscheidung: Sie gehören dem, der die Software gebaut
   hat.
6. **Und das Freigabedatum?** Empfehlung: **bleibt draußen.** Es ist
   das Datum eines Git-Tags, also eine Eigenschaft des Repositorys —
   ein von Hand gepflegtes Freigabedatum ist beim ersten Vergessen
   falsch. Damit bleibt in §1.3 genau **ein** Feld übrig, das „erzeugt"
   heißt und nicht erzeugt werden kann, und das ist ehrlich statt
   ambitioniert.

**Was das für den Store Editor bedeutet:** Für eine gut gepflegte App
sinken die „ungefähr sechs Eingaben" aus §1.3 auf fast null. Der Editor
wird damit das, was er sein sollte — ein Werkzeug zum **Kuratieren**,
nicht zum Texten.

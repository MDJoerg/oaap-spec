# RFC-0012: Store Sources and List Format

- **Status:** Proposed (2026-08-09)
- **Date:** 2026-08-09
- **Authors:** Jörg (requirements and direction), Claude (write-up)
- **Depends on:** RFC-0004 (app packaging), RFC-0008 (`server_admin`),
  RFC-0011 (node profiles)
- **Resolves:** findings B1–B5 in `program/store-konzept.md`, and with
  them step 4 of `program/portal-statt-cli.md`

## Summary

The store works, and it works by accident. A source is a URL with a
label; the list format exists only as whatever the reference
implementation happens to read; an app id is resolved by walking the
sources in configured order and taking the first hit. That is enough
for two lists we wrote ourselves and stops being enough the moment a
third party publishes one.

This RFC makes four things explicit — the **list format**, the
**source**, the **trust class**, and the **resolution rule** — and
names the one thing we are not yet solving (integrity of foreign
lists), so it stops being an unspoken assumption.

## What exists today (verified in the code, 2026-08-09)

- **Sources** live per node in `store-sources.json` as `{url, name}`.
  No enabled flag, no kind, no trust class, no stable identity.
  Maintained only by `oaap store add-source|remove-source`; the
  portal's store page points at the command line.
- **The list format** is a de-facto format:
  `{store, name, description, apps[]}`, each app `id, name,
  description, type, version, package{git,path[,ref]}, license,
  homepage`. There is no schema in `oaap-spec/schema/` and no
  normative section anywhere.
- **Resolution** (`_store_lookup`) walks the sources in file order and
  returns the **first** app whose id matches and which names a git
  package. On oaap-demo the community list is configured ahead of the
  platform list.
- **One-click install** deliberately sends only the app id; the host
  resolves it against the configured sources (`oaap.apps.runtime` 2.6).
  This is the property that keeps a compromised portal from installing
  something arbitrary — and it is why the portal has no free-form Git
  URL outside a `dev` node (RFC-0011).
- **Sources are written once, at installation, and never touched
  again** — not even by `oaap update`.

## Proposal

### 1. The list format becomes a specified, versioned artefact (B1)

A store list is a JSON document with a declared format version, and it
gets a schema next to `oaap-app.schema.json`. Today's lists declare
`"store": "0.1"`; this RFC defines **`0.2`**, and a reader must keep
accepting `0.1` (every field below is optional except the ones `0.1`
already required).

```jsonc
{
  "store": "0.2",
  "id": "oaap.community",            // stable, reverse-DNS-ish, see §4
  "name": "OAAP Community-Liste",
  "description": "…",
  "publisher": "MDJoerg",            // shown verbatim as the origin
  "apps": [
    {
      "id": "uptime-kuma",
      "name": "Uptime Kuma",
      "description": "…",
      "type": "wrapped",             // RFC-0004
      "version": "1.23.0",
      "package": { "git": "…", "path": "apps/uptime-kuma", "ref": "v1.23.0" },
      "license": "MIT",
      "homepage": "…",
      "category": "monitoring",      // controlled vocabulary, see Q5
      "keywords": ["uptime", "alerting"],
      "maturity": "beta",            // alpha | beta | preview | stable | expert-only
      "profiles": ["dev"],           // RFC-0011: what the app is meant for
      "icon": "…"
    }
  ]
}
```

Three notes on fields that are not cosmetic:

- **`package.ref`** already exists in the reader but nothing pushes
  anybody to set it. An entry without a ref installs whatever the
  default branch says *at that moment*. That is not a packaging detail;
  it is the difference between "install version 1.23.0" and "install
  whatever this repository contains today". See §5.
- **`maturity`** is Jörg's requirement, with `expert-only` decided as a
  **hint with confirmation, not a gate** (2026-08-08), consistent with
  RFC-0011: the author describes, the operator decides.
- **`profiles`** is RFC-0011's "apps may state which profiles they
  expect". The store filters and warns; it never refuses. This is where
  that RFC said the mechanism would land.

### 2. A source becomes an object (B2)

```jsonc
{
  "sources": [
    {
      "id": "oaap.platform",         // stable identity, never the URL
      "name": "OAAP Plattform-Apps",
      "url": "https://…/oaap-apps/main/oaap-store.json",
      "trust": "platform",           // platform | verified | unverified
      "enabled": true,
      "origin": "MDJoerg / oaap-apps",   // shown to the user verbatim
      "shipped": true,               // came with the installation, see §4
      "shipped_url": "https://…"     // what we shipped, to detect edits
    }
  ]
}
```

`id` is what everything else refers to — the registry entry of an
installed instance, the confirmation record, the reconcile step in §4.
The URL is an attribute of the source, not its name; that distinction
is the whole of B4.

### 3. Trust classes, and resolution by trust instead of order (B3)

Three classes, as decided (Jörg, 2026-08-08):

| class        | meaning                                              | shown as              |
|--------------|------------------------------------------------------|-----------------------|
| `platform`   | shipped and maintained by us                          | „von uns"             |
| `verified`   | curated by us, or a selected partner                  | „geprüft"             |
| `unverified` | foreign community, customer-owned, unknown            | „muss bestätigt werden" |

The finer distinctions travel in `origin` as plain text, not as more
classes — six levels would demand a judgement call at every new source
that in practice gets made inconsistently.

**Resolution rule.** When more than one enabled source lists the same
app id, the **highest trust class wins**; within a class, configured
order decides. Today the first configured source wins, which turns a
foreign list into a takeover path: claim a known id, sit above the real
list, and collect the one-click install.

Two additions that cost little and close the remaining gaps:

- **The portal sends source id *and* app id**, not the id alone. This
  is not a retreat from `oaap.apps.runtime` 2.6: the host still refuses
  anything that is not a **configured** source, so a compromised portal
  still cannot introduce a source of its own. It gains only the ability
  to pick among sources the `server_admin` already chose — and in
  exchange the user sees, and the log records, which list an app came
  from.
- **An installed instance keeps the source id it came from**, and later
  resolution for that instance prefers it. Otherwise an app installed
  from the platform list could silently be re-resolved to a different
  list after a source change. A change of source stays possible and
  becomes a deliberate, reported act.

**Installing from an `unverified` source requires an explicit
confirmation** (Jörg, 2026-08-08) and the confirmation is written to
the install log: who accepted which source, when, for which app. This
is a brake against inattention, not a security boundary — what protects
against a compromised portal is still 2.6's rule that only configured
sources resolve at all.

### 4. Shipped sources survive a move (B4)

Today a source is written at installation and never touched again. If
one of our URLs moves, every existing node strands — visibly only as an
empty store. Since the repository is expected to move once more, and
since B4 is a hard precondition for going public, the mechanism has to
exist before the move, not after it.

- Sources we ship carry `shipped: true`, a stable `id`, and
  `shipped_url` — the URL as we shipped it.
- **`oaap update` reconciles shipped sources**: for each shipped id in
  the delivered set, if the node's stored `url` still equals its
  `shipped_url`, both are updated to the new URL. If they differ, the
  operator has edited it — the entry is left alone and the difference is
  reported.
- `enabled`, `name` and `trust` set by the operator are never
  overwritten. A source the operator disabled stays disabled after it
  moves.
- Removing a shipped source stays removal, not a request to have it
  re-added on the next update: the removal is remembered by id.

**Migration of existing nodes.** Existing `{url, name}` entries get
`enabled: true` and an id and trust class derived **once** from the URL
prefix: our known prefixes become `platform`/`verified`, everything
else becomes `unverified` and is marked as needing review. That is the
URL prefix used exactly as far as it is trustworthy — as a suggestion
at one moment, never as a value recomputed on every lookup (see the
notes in `store-konzept.md`).

This migration changes behaviour on at least one real node: on
oaap-demo the community list is configured ahead of the platform list,
so after migration the platform list wins ties. That is the intended
fix and should be stated in the update output rather than discovered.

### 5. Integrity of foreign lists (B5) — partly solved, openly stated

HTTPS authenticates the **host** that serves a list. It says nothing
about the content, and a list can change under a node at any time
without anybody noticing. Today the referenced package is installed
unseen.

What this RFC proposes now:

- **Pinning is the cheap part and it should be pushed hard.** A list
  entry should name `package.ref` (tag or commit). The store shows
  whether an entry is pinned; an unpinned entry from a non-`platform`
  source is marked as such.
- **Signed lists are the real answer and are not proposed yet.** They
  need a key distribution story (which keys ship, who rotates them, what
  happens when verification fails on a node with no operator present)
  that we cannot write down responsibly today.

What this RFC does **not** claim: that pinning makes a foreign list
safe. It makes a foreign list *stable* — you get the same thing
tomorrow that you inspected today. Against a list that was malicious to
begin with, the protection remains the trust class, the confirmation,
and the fact that somebody had to configure the source at all.

### 6. One store page, with filters

The store page shows apps from all enabled sources as one catalogue,
with the source and its trust class visible on every entry. Filters:
category, maturity, trust class, source, installed/not installed,
license, and fit with the node's profiles (RFC-0011). Apps whose
`profiles` do not match the node are filtered out by default and
reachable with one click — filtered, not hidden.

### 7. Sources in the portal (step 4 of `portal-statt-cli.md`)

`server_admin` manages sources on a portal page: add, rename, enable,
disable, remove, and set the trust class — the last one as a
deliberate act with a warning, since raising a class is exactly the
step that skips the confirmation in §3. The CLI keeps working
unchanged; both write through the existing spool worker, like every
other portal-side registry write.

**One thing stays on the machine**, mirroring RFC-0011's implementation
note: nothing here lets the portal grant *itself* more reach than the
`server_admin` already granted, because adding a source is visible,
reversible, and does not by itself install anything. Setting a node
profile was different in kind, which is why that one stayed on the
machine.

## What this RFC does not do

- It does not build the **Store Editor**. It defines the format that
  editor will write, which is the part that has to be stable first.
- It does not introduce a source kind "development". RFC-0011's `dev`
  profile already covers the brand-new-repository case, and the Store
  Editor covers the durable one. A third mechanism for the same need
  would be one too many.
- It does not change `oaap.apps.runtime` 2.6's rule that only
  configured sources are installable. It makes the *selection* among
  them explicit.

## Open questions

1. **Which sources ship by default, and which of them disabled?**
   Today exactly one ships (the community list); the platform list is
   added by hand per node — which is why Studio was missing on
   oaap-demo. Proposal: both ship, both enabled, `oaap.platform` first.
2. **Confirmation for `unverified` sources: per install, or once per
   source?** Your requirement says before the installation, so: per
   install. The alternative — acknowledge the source once when adding
   it — is less noisy but puts the decision at the moment when the
   least is known about what will be installed from it.
3. **Unpinned entries from non-`platform` sources: warn, or refuse?**
   Recommendation: warn now, and revisit once our own lists are fully
   pinned — refusing today would make most of the existing community
   list uninstallable.
4. **May the operator raise a source to `platform`?** Recommendation:
   no — reserve `platform` for what the installation shipped, and let
   operators use `verified` for their own lists. It keeps "von uns"
   meaning one thing on every node.
5. **Category vocabulary: controlled or free text?** Recommendation:
   controlled and extended by us, for the same reason profiles are not
   free tags (RFC-0011 decision 2) — a typo produces a category with
   one app in it and breaks the filter silently.
6. **How does the Store Editor publish a list to Git without holding
   credentials?** Recommendation for the first version: it produces the
   file and a human commits it — no credentials in the app at all. A
   push path can follow once there is a reason.

## Deutsche Zusammenfassung

**Warum jetzt.** Der Store funktioniert — aber er funktioniert nur,
solange alle Listen von uns sind. Eine Quelle ist heute nur eine URL
mit Beschriftung, das Listenformat steht nirgends geschrieben, und bei
gleicher App-Kennung gewinnt schlicht die **zuerst eingetragene**
Quelle. Sobald Fremde Listen veröffentlichen, ist das ein
Übernahmeweg: bekannte Kennung beanspruchen, weiter oben stehen,
Ein-Klick-Installation kassieren. Dieser RFC macht vier Dinge
verbindlich — **Listenformat, Quelle, Vertrauensklasse,
Auflösungsregel** — und benennt das eine, was wir noch nicht lösen.

**1. Listenformat wird spezifiziert** (B1), Version `0.2` mit Schema
neben dem App-Manifest, die heutigen `0.1`-Listen bleiben lesbar. Neu
darin: Deine **Kategorie** und Dein **Reifegrad** („alpha", „beta",
„preview", „stable", „expert only" — Hinweis mit Bestätigung, wie
entschieden), Herausgeber, Stichworte, Symbol — und die **Profile aus
RFC-0011**, wo dort versprochen war, dass der Store filtert und warnt.

**2. Eine Quelle wird ein Objekt** (B2): stabile Kennung, Anzeigename,
URL, Vertrauensklasse, an/aus, Herkunft im Klartext. Erst damit gibt es
Dein „vorkonfiguriert, teilweise deaktiviert" überhaupt.

**3. Aufgelöst wird nach Vertrauen statt nach Reihenfolge** (B3): drei
Klassen wie entschieden („von uns" / „geprüft" / „muss bestätigt
werden"), die höchste gewinnt, innerhalb einer Klasse die Reihenfolge.
Dazu zwei Kleinigkeiten mit großer Wirkung: Das Portal schickt künftig
**Quelle + Kennung** statt nur der Kennung (kein Rückschritt gegenüber
2.6 — es bleibt eine Auswahl **unter den konfigurierten** Quellen, und
dafür sieht man endlich, aus welcher Liste eine App kam), und eine
installierte Instanz **merkt sich ihre Quelle**, damit sie später nicht
stillschweigend aus einer anderen Liste bedient wird. Installation aus
einer unbestätigten Quelle verlangt eine Bestätigung, die **im
Protokoll landet**.

**4. Umzug mitgelieferter Quellen** (B4): Mitgelieferte Quellen tragen
eine stabile Kennung und die ausgelieferte URL. `oaap update` gleicht
ab — hat der Betreiber die URL nicht angefasst, zieht sie mit; hat er
sie geändert, bleibt sie stehen und der Unterschied wird gemeldet.
Deaktiviert bleibt deaktiviert, entfernt bleibt entfernt. **Das muss
vor dem Repo-Umzug existieren, nicht danach** — sonst strandet jeder
bestehende Knoten, sichtbar nur an einem leeren Store. Beim Umstellen
bekommen vorhandene Einträge ihre Klasse **einmalig** aus dem
URL-Präfix (genau so weit, wie ein Präfix trägt — als Vorschlag in
einem Moment, nicht als bei jeder Auflösung neu berechnete Wahrheit).
Ehrlich dazu: Auf oaap-demo ändert das Verhalten — dort steht die
Community-Liste vor der Plattform-Liste, künftig gewinnt die
Plattform-Liste. Das ist die gewollte Korrektur und wird beim Update
ausgegeben, statt dass Du sie entdeckst.

**5. Integrität fremder Listen** (B5) — hier bleibe ich ausdrücklich
unvollständig: HTTPS beweist, **wer** die Liste ausliefert, nicht
**was** darin steht; eine Liste kann sich jederzeit unbemerkt ändern.
Billig und sofort machbar ist **Pinning** (die Liste nennt Tag oder
Commit) — das macht eine fremde Liste nicht sicher, aber **stabil**: Du
bekommst morgen dasselbe, was Du heute angesehen hast. Signierte Listen
wären die richtige Antwort, brauchen aber eine Schlüsselverwaltung, die
ich heute nicht verantwortlich aufschreiben kann — deshalb benannt und
vertagt statt halb gebaut.

**6./7.** Ein zusammenfassender Store über alle Quellen mit Filtern
(Kategorie, Reifegrad, Vertrauen, Quelle, installiert, Lizenz,
Knoten-Profil) — und die **Quellenverwaltung im Portal**, womit Schritt
4 aus `portal-statt-cli.md` fällt.

**Sechs Fragen an Dich** (mit meiner Empfehlung, Details oben):

1. Welche Quellen liefern wir ab Werk, welche deaktiviert? *(Vorschlag:
   beide unsere Listen, beide aktiv, Plattform-Liste zuerst — heute
   fehlt die Plattform-Liste ab Werk, deshalb war Studio auf oaap-demo
   nicht da.)*
2. Bestätigung bei unbestätigten Quellen: **je Installation** oder
   einmal je Quelle? *(Deine Anforderung sagt „vor der Installation" —
   also je Installation.)*
3. Nicht gepinnte Einträge fremder Listen: **warnen** oder ablehnen?
   *(Vorschlag: warnen — ablehnen macht die heutige Community-Liste
   unbenutzbar.)*
4. Darf der Betreiber eine Quelle auf „von uns" heben? *(Vorschlag:
   nein — sonst bedeutet „von uns" auf jedem Knoten etwas anderes.)*
5. Kategorien: feste Liste oder freier Text? *(Vorschlag: feste Liste,
   von uns erweitert — genau die Begründung wie bei den Profilen: ein
   Tippfehler erzeugt sonst still eine Kategorie mit einer App.)*
6. Wie veröffentlicht der Store Editor eine Liste nach Git, ohne
   Zugangsdaten zu halten? *(Vorschlag für die erste Fassung: Er
   erzeugt die Datei, ein Mensch committet sie — gar keine Zugangsdaten
   in der App.)*

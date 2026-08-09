# RFC-0012: Store Sources and List Format

- **Status:** Accepted (2026-08-09) — all fifteen questions decided
  across three rounds on the same day
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

§8 does something different and equally deliberate: it **reserves
ground** for dependencies, app sets, service bundles and curated
annotations without building any of them, and fixes the two places
where today's readers would reject tomorrow's lists outright.

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

The shape below is what a user expects from a store — title, picture,
what it is for, who it is for, how far along it is, where to read more
(Jörg, 2026-08-09) — and it is at the same time the input mask of the
Store Editor that will write these lists.

```jsonc
{
  "store": "0.2",
  "id": "oaap.community",            // stable, reverse-DNS-ish, see §4
  "name": "OAAP Community-Liste",
  "description": "…",
  "publisher": "MDJoerg",            // shown verbatim as the origin
  "apps": [
    {
      // --- identity: generated from the manifest (§1.3) ---
      "id": "uptime-kuma",
      "name": "Uptime Kuma",
      "type": "wrapped",             // RFC-0004: how it is packaged
      "version": "1.23.0",
      "released": "2026-07-14",      // date of THIS version, see below
      "package": { "git": "…", "path": "apps/uptime-kuma", "ref": "v1.23.0" },
      "profiles": ["dev"],           // RFC-0011: which nodes it is meant for
      "roles": ["user", "keyuser"],  // derived from the manifest's routes

      // --- classification: editorial, all filterable (§1.2) ---
      "categories": ["monitoring", "iot"],   // controlled, several allowed
      "app_class": "frontend",       // frontend | service (see §1.2)
      "audience": ["operator"],      // everyone | operator | developer | expert
      "maturity": "beta",            // alpha | beta | preview | stable
      "status": "active",            // active | deprecated | archived
      "tags": ["uptime", "alerting"],// free text, for search — not a filter

      // --- presentation: editorial ---
      "summary": "Überwacht Dienste und meldet Ausfälle.",  // one line
      "description": "…",            // long text, may be Markdown
      "icon": "icons/uptime-kuma.svg",       // relative to the list, see below
      "screenshots": [
        { "src": "shots/uptime-kuma-1.png", "caption": "Übersicht" }
      ],
      "links": [                     // typed link list instead of fixed fields
        { "rel": "homepage", "url": "https://…" },
        { "rel": "docs",     "url": "https://…" },
        { "rel": "demo",     "url": "https://…" },
        { "rel": "changelog","url": "https://…" }
      ],
      "license": "MIT",

      // --- named alternatives of the SAME app (§8) ---
      // version/released/package above ARE the "default" variant.
      "variants": {
        "preview": { "version": "2.0.0-rc1", "released": "2026-08-01",
                     "package": { "git": "…", "ref": "v2.0.0-rc1" } },
        "demo":    { "version": "1.23.0",
                     "package": { "git": "…", "path": "apps/uptime-kuma-demo" } }
      }
    }
  ]
}
```

#### 1.1 Six notes on fields that are not cosmetic

- **`package.ref`** already exists in the reader but nothing pushes
  anybody to set it. An entry without a ref installs whatever the
  default branch says *at that moment*. That is not a packaging detail;
  it is the difference between "install version 1.23.0" and "install
  whatever this repository contains today". See §5.
- **`profiles`** is RFC-0011's "apps may state which profiles they
  expect" (Studio: `dev`). The store filters and warns; it never
  refuses. This is where that RFC said the mechanism would land.
- **`released` is what makes "new" possible**, and it is deliberately
  not a `new` flag. A stored `new` would need somebody to remove it
  again, so it would be permanently wrong on every unmaintained entry.
  A date cannot go stale in that way — the badge is computed from it.
  See §1.2.
- **`icon` and `screenshots` are paths relative to the list URL**, not
  arbitrary external URLs. If a store entry could name any image host,
  every node that opens the store page would make requests to servers
  nobody chose — announcing the node's existence and address to a third
  party for the sake of a thumbnail. Relative paths mean exactly one
  host is contacted: the one the operator already trusted by
  configuring the source.
- **`links` replaces a growing set of fixed fields.** `homepage` from
  `0.1` is read as `{"rel": "homepage"}`. The `rel` vocabulary is
  controlled (`homepage`, `docs`, `source`, `demo`, `changelog`,
  `support`, `privacy`, `license`) so the store can label and order
  them; unknown `rel` values are shown under "Weitere Links" rather
  than dropped.
- **`variants` are not the deploy channel.** `oaap.apps.runtime`
  already has `--channel production|test`, which decides how an
  *instance* on *this node* may be redeployed. A variant says that the
  publisher offers the same app in a second shape (`preview`, `demo`,
  and whatever comes later). Keeping them distinct matters because they
  combine: a preview variant installed on the production channel is a
  perfectly sensible thing to want, and a confusing thing to name
  twice.

**Why variants are a field and not extra entries.** The obvious
alternative — a separate list entry `uptime-kuma-preview` — would
reintroduce exactly the ambiguity §3 removes: two entries claiming to
be the same app, resolved by whichever comes first. One entry per app
id stays the rule. Installing a variant therefore produces a *separate
instance* with its own name (`studio-preview`), which the platform
already supports — instance name and app id have been separable since
the beginning.

The `default` variant is the top-level `version`/`released`/`package`,
which is what keeps `0.1` lists readable and avoids saying the same
thing twice. A hosted **demo you click through without installing** is
something else again and stays a `links` entry with `rel: demo`.

#### 1.2 Four vocabularies, and why they are four and not one

Jörg's list — maturity, target group, category, application class —
looked at first like one axis with many values. It is four, and
collapsing them is what makes store filters useless elsewhere.

**`categories` — what the app is about.** Controlled, **several per
app** (a monitoring tool for IoT devices is both). Starter vocabulary,
extended by us: `business`, `productivity`, `documents`,
`communication`, `media`, `monitoring`, `iot`, `automation`, `ai`,
`development`, `security`, `storage-backup`, `infrastructure`.

**`app_class` — what the app technically is.** This is Jörg's
observation that we build front-ends today and will ship other things
tomorrow. Not to be confused with RFC-0004's `type`
(`native|image|wrapped`), which says *how it is packaged*:

| value      | meaning                                        |
|------------|------------------------------------------------|
| `frontend` | has a user interface — today's normal case     |
| `service`  | backend only, used by other software (bdt-hub) |

This one is more than a filter: **a `service` has no business owning a
launchpad tile.** Today every instance gets one, which is why a purely
machine-facing app like bdt-hub appears as a tile that leads to a page
no human wants. `app_class` is the field that fixes that, and it is
also checkable — a `frontend` whose manifest exposes no user-facing
route is an inconsistent entry, and the Store Editor can say so.

**Correction to my own first sketch:** I had a third value `data` here,
for the data models behind Jörg's digital-twin direction. The idea log
already answers that better and earlier (`program/capability-ideas.md`,
from the pre-project chat): a data model is **`kind: DataModel`, its
own store artefact type next to apps** — separately packageable and
versionable — and the same entry foresees `kind: Agent`. That is right,
and it is not an app class: a data model has no service, no health
check and no launchpad tile, so nearly every field the app schema
requires would be meaningless. See §8.5, where sets run into the same
question and get the same answer.

**`audience` — who the app is for.** Several allowed:
`everyone` · `operator` · `developer` · `expert`. This is where
`expert only` belongs, and moving it here keeps the decision of
2026-08-08 intact: an app for `expert` is **clearly marked and takes a
confirmation, but nobody is locked out**. It was an awkward maturity
value — "expert only" says nothing about how finished something is.

**`maturity` and `status` — two different questions.** Jörg's proposed
lifecycle (`alpha, beta, preview, new, stable, retired, archived`)
contains three axes, and separating them is the one change I would ask
for:

- **`maturity`** = how finished: `alpha` · `beta` · `preview` ·
  `stable`.
- **`status`** = whether it is still carried: `active` ·
  `deprecated` (still installable, no longer recommended) ·
  `archived` (no longer offered). This has real behaviour attached, not
  just a badge: archived entries are hidden from the store by default,
  and an *installed* instance whose entry has become `deprecated` or
  `archived` is worth reporting on the health page — that is the moment
  an operator actually needs to know.
- **`new`** = age, and therefore **computed from `released`**, never
  stored (see §1.1).

**`tags` — free text, and here that is right.** Decision 5 (controlled
categories) was about *filters*: a typo produces a filter entry with
one app behind it. Tags are search aids, not filters — a typo there
costs one missed search hit and nothing else. Both mechanisms exist on
purpose; the store filters by `categories` and searches across `tags`,
`name`, `summary` and `description`.

**On extending controlled vocabularies.** The vocabularies are
published by us as part of the spec, but a node must not refuse a list
that uses a value newer than the node. Unknown values are therefore
**accepted, shown verbatim, and grouped under "Sonstiges"** rather than
rejected — otherwise every vocabulary extension would strand every
node that has not updated yet, which is precisely the failure mode B4
exists to prevent.

#### 1.3 Where each field comes from — the 80 % rule

Jörg: most of this can be pre-filled, and the rest belongs behind an
"advanced" section. That splits the fields cleanly, and the split is a
property of the **Store Editor**, not of the format — a list stays one
flat JSON document anybody can write by hand.

- **Generated** from the manifest and the repository: `id`, `name`,
  `type`, `version`, `released`, `package` (including `ref` from the
  tag), `roles` (from the manifest's route roles), `profiles`, `icon`,
  and a first `description`. The editor fills these and shows them
  read-only unless "erweiterte Konfiguration" is opened.
- **Editorial**, the fields a human actually has to think about:
  `summary`, `categories`, `audience`, `maturity`, `status`,
  `screenshots`, `links`. Roughly six inputs per app.

The principle behind it, worth stating because it decides future
questions too: **the manifest is the truth about what the app is; the
list is the truth about how it is presented and classified.** Where the
list repeats manifest content, that copy is *generated at publishing
time* — it must be, because a store page has only the list and cannot
fetch every manifest. Where an editor overrides a generated value, the
override is marked, so the next regeneration does not silently undo an
intentional edit.

The same rule answers `roles`: it is **not** a field somebody
maintains. Route roles live in the manifest (RFC-0002/0004); the list
carries a generated copy so the store can say "wer kann das nutzen"
without cloning the repository.

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

| class        | meaning                                    | shown as                |
|--------------|--------------------------------------------|-------------------------|
| `platform`   | shipped and maintained by us               | „von uns"               |
| `verified`   | curated by us, or a selected partner       | „geprüft"               |
| `unverified` | foreign community, customer-owned, unknown | „muss bestätigt werden" |

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
with the source and its trust class visible on every entry.

**Filters:** `categories`, `app_class`, `audience`, `maturity`,
`status`, trust class, source, license, installed/not installed, and
fit with the node's profiles (RFC-0011). **Search** additionally covers
`tags`, `name`, `summary` and `description`.

**Three defaults, each with a reason:**

- Apps whose `profiles` do not match the node are filtered out by
  default and reachable with one click — filtered, not hidden.
- `status: archived` is filtered out by default for the same reason.
- `audience: expert` is **not** filtered out. It is shown, marked, and
  costs a confirmation at install (decision of 2026-08-08). Hiding it
  would turn a hint into a gate through the back door.

The list report follows the design guidelines' floorplans: list report
for the catalogue, object page per app — icon, summary, screenshots,
long description, version and release date, links, and the classifying
badges. That object page is the reason the format carries presentation
fields at all; without it they would be decoration.

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

### 8. Built to be extended — reserved ground for what comes next

Jörg listed (2026-08-09) what will want a place later: dependencies
between apps, data models and their maintenance apps, dependencies on a
platform capability, variants, selectable services with `small/medium/
large` bundles, app sets, and curated tags. His framing is the right
one: **prepare the format so this fits later, do not build it now.**
This section is that preparation, and it is deliberately the cheapest
part of the whole RFC.

#### 8.1 Two findings that make this urgent

Extensibility is not a matter of adding empty fields. It is a matter of
what a reader does with something it has never seen — and on that,
today's code answers badly in two places.

**The manifest version is a hard equality.** `validate_manifest` refuses
anything whose `oaap_manifest` is not exactly `"0.1"`, and the schema
says `"const": "0.1"`. The day we publish manifest `0.2` to carry
dependencies, **every node in the field rejects those apps outright** —
not "ignores the new field", but "manifest invalid". That is precisely
the trap this section exists to avoid, and it is in the code today.

**The reference supports exactly one service per app**
(`if len(services) != 1: "exactly one service is supported in runtime
increment 1"`), while the schema already allows several. So the
compose-profile idea — selectable services, `small/medium/large` —
is not blocked by the list format at all. It is blocked one level down,
by multi-service support in the runtime. Worth knowing before designing
a bundle syntax for something that cannot run.

#### 8.2 Three rules that make later additions safe

1. **A reader ignores what it does not know, and never refuses because
   of it.** Both for lists and manifests. Unknown fields, unknown
   category values, unknown link `rel` — accepted, shown verbatim where
   sensible, otherwise skipped.
2. **`must_understand` is the exception that makes rule 1 safe.** An
   entry may name features a reader has to understand to handle it
   correctly — `"must_understand": ["dependencies"]`. A reader missing
   one of them refuses **that entry** with a clear message instead of
   installing something half-understood. Without this, rule 1 would mean
   an old node silently ignores a dependency and installs a broken app.
   (Same idea as `crit` in JOSE, or `Pre-Depends` in dpkg: most things
   may be skipped, a few may not.)
3. **The format version bumps only when a reader that ignores the new
   thing would be *wrong*.** Adding optional presentation fields is not
   a new version. This is the rule that stops us from stranding the
   fleet every time the store learns a word.

Consequence for the manifest, and it should be fixed with this RFC even
though it is not store work: `oaap_manifest` must be read as "major
version I understand", not compared for equality. Strict validation
belongs in **authoring tools** — the Store Editor, CI — where a typo
should be caught. A node in the field reads tolerantly. Strict schema,
tolerant runtime.

#### 8.3 Reserved names, and what they will mean

Names are the expensive part: a word used for one thing cannot later
mean another. These are reserved now, specified later.

| name                | where    | meaning when it lands                                |
|---------------------|----------|------------------------------------------------------|
| `depends`           | manifest | apps/capabilities required to work                   |
| `recommends`        | manifest | sensible together, offered, not required             |
| `suggests`          | manifest | mentioned on the object page only                    |
| `conflicts`         | manifest | must not run alongside                               |
| `provides`          | manifest | virtual name this app satisfies                      |
| `requires_platform` | manifest | capability + version, e.g. `oaap.core.portal >= 0.3` |
| `variants`          | list     | named alternatives of one app (§1) — in use now      |
| `bundles`           | manifest | named service selections (`small`/`large`)           |
| `sets`              | list     | top-level collection of app sets (§8.5)              |
| `annotations`       | list     | our remarks about *someone else's* app (§8.6)        |

Vocabulary borrowed from Debian on purpose (Jörg's suggestion): the
words are decades old, widely understood, and each already carries the
distinction between "will not work without" and "is nicer with".

Two more names are reserved from the **existing** digital-twin model in
the idea log, and they must not be confused with the ones above:

| name          | where    | meaning when it lands                     |
|---------------|----------|-------------------------------------------|
| `consumes`    | manifest | data regions this app reads               |
| `contributes` | manifest | data regions this app writes into         |
| `data_models` | list     | reserved collection for `kind: DataModel` |
| `agents`      | list     | reserved collection for `kind: Agent`     |

**`depends`/`provides` and `consumes`/`contributes` answer different
questions.** The first pair is about *software*: does this thing need
that thing installed. The second is about *data*: which regions of the
shared twin does this app read and which does it own — with the
Owner/Contributor/Consumer responsibility the idea log describes. An
app can perfectly well `consume` a data region without depending on any
particular app that fills it; that is the whole point of the twin as a
shared layer.

#### 8.4 The one thing I would veto: automatic dependency resolution

Borrow the vocabulary, not the machinery. A package manager resolves
dependencies automatically because it draws from **one archive, with
one namespace, one version discipline and one trust decision**. We
deliberately have the opposite: several sources of different trust
classes, and a rule (§3) that installing from an unverified source
takes a confirmation.

Automatic resolution would walk straight through that rule — the store
would install a dependency out of a list the operator never looked at,
without the confirmation, because it was needed by something else. So:

- Dependencies are **declared, displayed, and offered** ("diese App
  braucht X — mitinstallieren?"), one confirmation per source as usual.
- They are **never** silently installed, and a missing dependency
  **warns rather than blocks** — same posture as `profiles` in RFC-0011
  and `expert` in §1.2: the author describes, the operator decides.

There is a second reason, specific to us. Debian installs a package
once per system; OAAP installs an *app* as one or more *instances*,
possibly several of the same app, possibly on different nodes. "CRM
depends on data model X" therefore has no single answer — which
instance, on which node? That is a real design question (same node? any
node? chosen at install time?) and it deserves its own RFC. What
belongs in the format today is only the **declaration**.

#### 8.5 One collection per artefact kind — sets, and later models and agents

Jörg's example — "KI-Support" = ollama + open-webui — is a
**metapackage**, and it should be a separate top-level collection in
the list, not an app entry with empty fields:

```jsonc
"sets": [
  { "id": "ai-support", "name": "KI-Support",
    "summary": "Sprachmodell und Weboberfläche",
    "categories": ["ai"], "icon": "…", "screenshots": [ … ],
    "members": [ { "id": "ollama", "required": true },
                 { "id": "open-webui", "required": true },
                 { "id": "n8n", "required": false } ] }
]
```

A set has no version, no package, no manifest and no health check —
forcing it through the app schema would leave half the required fields
meaningless. It also resolves differently: §3 resolves *app ids*; a set
expands to app ids first and each member then resolves normally, with
its own source, trust class and confirmation.

**This generalises, and that is the actual structural decision here.**
The idea log already names two more artefact kinds — `kind: DataModel`
and `kind: Agent` — and both fail the app schema for the same reason a
set does. So the rule is: **`apps` stays what it is (which keeps `0.1`
lists readable), and every further artefact kind gets its own top-level
collection.** `sets` now; `data_models` and `agents` reserved.

The alternative — one array with a `kind` discriminator — was
considered and dropped: with four kinds that share only `id`, `name`
and the presentation fields, almost every other field would become
conditional on `kind`, which is a schema nobody can validate cleanly
and nobody can read. Shared presentation fields are shared by
definition, not by putting unlike things in one list.

Honest scope for the first version: the store **shows** a set and offers
to install its members as ordinary installs. No transaction, no
rollback if member three fails. Anything else means ordering, partial
failure and undo — real work, and not needed to make sets useful.

**`bundles` and `sets` must not be confused**, which is why they get
distinct words: a **bundle** selects services *inside one app*; a
**set** groups *several separate apps*.

#### 8.6 Curated tags: not a restriction, a second layer

Jörg asked whether tags are more attractive if only we assign them.
The pull behind that is right — publisher tags are marketing, and a
curated word is worth more. But it cannot be done by restricting the
field: we do not write foreign lists, and in our own we control the
tags simply by writing them.

The mechanism that actually delivers it is a **curation overlay**: an
entry in *our* list that carries no package but annotates an app from
*another* list — our tags, our remarks, a review date. That also gives
the `verified` trust class teeth it does not have today, where trust is
a property of the whole source and never of a single app.

Worth building, not worth building now. Reserved as `annotations`
(§8.3). Until then: `tags` stay the publisher's free text, used for
search and never for filters (§1.2).

#### 8.7 Where a new concept belongs — the three-way rule

This keeps coming up, so it is written down once:

- **Fact about the app** → the **manifest**. The list carries a
  generated copy for display (§1.3). Dependencies, required platform
  capabilities, bundles, declared profiles are all facts about the app.
- **Judgement about the app** → the **list**. Categories, audience,
  maturity, status, screenshots, remarks. Someone decided these; they
  can differ between lists, and that is correct.
- **Fact about this machine** → **node state**. Profiles (RFC-0011),
  sources, instance configuration. Never in a manifest, or an app would
  be dictating to the operator.

The rule answers most "where does this new field go?" questions before
they turn into discussions.

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

## Decisions (Jörg, 2026-08-09)

All six questions of the first draft answered along the recommendation:

1. **Both our lists ship by default, both enabled, `oaap.platform`
   first.** Fixes the gap that made Studio absent on oaap-demo.
2. **Confirmation for `unverified` sources happens per installation**,
   not once per source — the decision belongs to the moment when it is
   known what is about to be installed.
3. **Unpinned entries from non-`platform` sources warn, they do not
   refuse.** Refusing today would make most of the existing community
   list uninstallable; revisit once our own lists are pinned.
4. **The operator may not raise a source to `platform`.** That class
   stays reserved for what the installation shipped, so „von uns" means
   the same thing on every node; operators use `verified`.
5. **Controlled category vocabulary**, extended by us — same reasoning
   as RFC-0011 decision 2. Refined while writing §1.2: unknown values
   are accepted and grouped under "Sonstiges" rather than rejected, or
   every vocabulary extension would strand every node that has not
   updated yet.
6. **The Store Editor produces the file and a human commits it.** No
   credentials in the app; a push path can follow when there is a
   reason.

## Decided, rounds two and three (Jörg, 2026-08-09)

**All nine questions below were answered along the recommendation.**
They are kept in question form because the reasoning is the record;
what follows each one is what now holds.

The list format grew after the decisions above (Jörg, 2026-08-09).
Five things were worth one more confirmation before this became a
schema; my recommendation is with each, and each was accepted.

1. **Splitting the lifecycle into `maturity` + `status`, with `new`
   computed.** Your list was `alpha, beta, preview, new, stable,
   retired, archived`. Recommendation: `maturity`
   (`alpha|beta|preview|stable`), `status`
   (`active|deprecated|archived`), and `new` derived from `released`.
   Reason in §1.2 — a stored `new` is permanently wrong on every entry
   nobody maintains, and "archived" answers a different question than
   "beta". `retired` I would fold into `deprecated`; if you want both
   (retired = no longer developed, still supported / deprecated = do
   not use for new installations), say so and it stays two values.
2. **`status` with consequences, or badge only?** Recommendation:
   consequences — `archived` filtered out of the store by default, and
   an installed instance whose entry turned `deprecated`/`archived`
   reported on the health page. That last part is the one that helps
   somebody who installed an app a year ago; it also means the node
   re-reads the store list periodically, which it does not do today.
3. **Screenshots and icons only from the list's own repository.** The
   alternative (any URL) means every node opening the store page calls
   servers nobody chose. Recommendation: relative paths only. Say if
   you want external image URLs allowed anyway — then it should at
   least be visible in the store which host is being contacted.
4. **`app_class` decides the launchpad tile.** Recommendation: a
   `service` gets no tile by default (bdt-hub is the example that
   exists today), overridable per instance. This is the one item here
   that changes behaviour for already-installed apps.
5. **Data models are not an app class — they are their own artefact
   kind.** I had sketched `app_class: data`; the idea log's earlier and
   better answer is **`kind: DataModel`**, a separate store artefact
   next to apps, and the same entry already foresees `kind: Agent`.
   Recommendation: `apps` keeps its meaning, and every further kind
   gets its own collection (`sets` now, `data_models` and `agents`
   reserved) — §8.5.

Flagged rather than asked: **variants (`preview`, `demo`) and the
deploy channel `production|test` are different things** with
confusingly similar names. No better word came up, so `variants` it is
— and the two must be named apart wherever they meet in the UI.

**On decision 1:** `retired` and `deprecated` were offered as possibly
two values and stay **one** — `deprecated`. Nobody asked for the
distinction, and an unused enum value only invites inconsistent use.

### From §8 (extensibility), added 2026-08-09

1. **Fix the manifest's version check with this RFC?** `oaap_manifest`
   is compared for equality today, so publishing `0.2` would make every
   node in the field reject those apps. It is RFC-0004 territory, not
   store work — but it is the single change that decides whether any of
   your later ideas can ship without a flag-day update. Recommendation:
   fix it now, while nothing depends on it yet.
2. **Accept `must_understand`?** It is what lets a reader ignore
   everything it does not know (rule 1) without ever ignoring something
   that mattered. Cheap now, impossible to retrofit later.
3. **Sets as their own collection, not app entries?** Recommendation:
   own collection — a set has no version, no package and no health
   check, and it resolves differently from an app id.
   *Asked back and clarified (Jörg): the decisive argument is §8.2
   rule 1. A node that does not know sets simply never sees a `sets`
   key. Put the same set inside `apps`, and that node renders it as an
   app with no version and an install button that fails. Storage and
   presentation stay separate questions — the store page may still show
   sets and apps side by side.*
4. **Do you accept the veto on automatic dependency resolution?**
   Declared, shown, offered — never installed silently. §8.4 has the
   reasoning; the short version is that auto-resolution would walk
   straight through the confirmation rule from §3.

Reserved but explicitly *not* proposed for now, per your own framing:
`depends`/`recommends`/`suggests`/`conflicts`/`provides`,
`requires_platform`, `bundles`, `annotations`, `consumes`/`contributes`,
`data_models`, `agents`. Names taken, semantics sketched, nothing built.

## Build order that follows from this

1. ✅ **Schema `oaap-store-0.2.json`** next to `oaap-app.schema.json` —
   B1, and the thing everything else is measured against.
   *(2026-08-09, `oaap-spec/schema/oaap-store.schema.json`.)*
2. ✅ **Manifest version tolerance** (§8 decision 1) — small, and it must
   land before anything publishes a `0.2` manifest.
   *(2026-08-09, runtime spec 2.2, `appctl.read_manifest_version`,
   `must_understand` implemented as an empty feature set.)*
3. ✅ **Source objects and migration** (§2, §4) — B2/B4, the part with a
   deadline: it has to exist before our repository moves.
   *(2026-08-09, runtime spec 2.9, `oaap store` gains `enable`,
   `disable`, `trust`, `reconcile`; `oaap update` reconciles.)*
4. ✅ **Resolution by trust, source id in the install request,
   confirmation logging** (§3) — B3.
   *(2026-08-09, runtime spec 2.6 with conformance tests 25–29.)*
5. **Store page and object page** (§6) — where the format becomes
   visible. *Not started.* The portal's store page carries the trust
   class and the confirmation since step 4, but it still groups by
   source and shows none of the `0.2` presentation fields.
6. **Sources in the portal** (§7) — closes step 4 of
   `portal-statt-cli.md`. *Not started;* sources are still CLI-only.
7. **`app_class` and the launchpad tile** — the only item that changes
   behaviour for already-installed apps; deserves its own careful pass.
   *Not started.*

Sets (§8.5) and everything reserved in §8.3 are deliberately not in
this list.

**What steps 2–4 deliberately did not touch.** Nothing publishes a
`0.2` manifest or a `0.2` list yet; the tolerance exists so that the
first one does not strand the fleet. `MANIFEST_FEATURES` is empty on
purpose — a `must_understand` entry only becomes accepted when the
feature it names is actually implemented, which is the whole point of
the mechanism.

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
neben dem App-Manifest, die heutigen `0.1`-Listen bleiben lesbar. Es
enthält jetzt das, was man aus einem Store kennt (Deine Ergänzungen vom
09.08.): Titel, Kurztext und Langtext, Symbol, **Bildergalerie**,
Release-Datum, **Linkliste** (Doku, Landingpage, Demo, Quellcode,
Changelog …), **Hashtags**, eine optionale **Vorschau-Version derselben
App** — und die **Profile aus RFC-0011**, wo versprochen war, dass der
Store filtert und warnt (Studio → `dev`).

**Dabei habe ich Deine Vorschläge an vier Stellen aufgeteilt statt
übernommen** — jedes Mal, weil zwei verschiedene Fragen in einem Feld
steckten:

- **Aus einer Kategorie werden mehrere.** „IoT", „Personal Utils" —
  und ein Überwachungswerkzeug für IoT-Geräte ist eben beides. Also
  Mehrfachzuordnung, aus einer festen Liste (wie entschieden).
- **Kategorie ≠ Hashtag.** Die feste Liste gilt für die **Filter**;
  Hashtags bleiben **freier Text** für die **Suche**. Das ist kein
  Widerspruch zu Deiner Entscheidung 5: Ein Tippfehler im Filter
  erzeugt eine Kategorie mit einer einzigen App, ein Tippfehler im
  Hashtag kostet einen verpassten Suchtreffer.
- **Aus Deinem Lebenszyklus werden zwei Felder plus eine Rechnung.**
  „alpha, beta, preview, stable" ist **Reifegrad**; „retired,
  archived" ist etwas anderes — nämlich, ob die App noch getragen wird
  (**Status**); und **„new" ist Alter** und wird deshalb aus dem
  Release-Datum **berechnet**. Ein gespeichertes „new" müsste jemand
  wieder wegnehmen — bei jeder ungepflegten Liste bliebe es für immer
  stehen und wäre für immer falsch.
- **„Expert only" wandert zur Zielgruppe**, genau wie Du vorgeschlagen
  hast. Es war als Reifegrad schief (es sagt nichts darüber, wie fertig
  etwas ist). Die Entscheidung vom 08.08. bleibt dabei unangetastet:
  deutlich gekennzeichnet, eine Bestätigung bei der Installation,
  **niemand wird ausgesperrt**.

**Deine Anwendungsklasse ist mehr als ein Filter.** `frontend` /
`service` / `data` — nicht zu verwechseln mit dem `type` aus RFC-0004
(`native/image/wrapped`), der sagt, *wie verpackt* wird. Der praktische
Nutzen zeigt sich sofort an bdt-hub: ein reiner Backend-Dienst bekommt
heute trotzdem eine Kachel im Launchpad, die zu einer Seite führt, die
kein Mensch sehen will. Ehrlich dazu: **`data` geht heute noch gar
nicht** — das Manifest verlangt mindestens einen laufenden Dienst. Ich
schlage vor, den Wert trotzdem jetzt zu benennen, damit das Vokabular
später nicht bricht.

**Die 80-%-Regel, die Du genannt hast, ist der eigentliche Bauplan für
den Store Editor.** Der größere Teil dieser Felder ist gar nicht
Redaktion, sondern **aus Manifest und Repository ableitbar**: Kennung,
Name, Typ, Version, Release-Datum, Paket samt Tag, Rollen, Profile,
Symbol. Die füllt der Editor vor und zeigt sie nur in der
**erweiterten Konfiguration** — überschreiben geht, wird aber vermerkt,
damit die nächste Erzeugung eine bewusste Änderung nicht still
zurücknimmt. Übrig bleiben rund sechs Eingaben, über die man wirklich
nachdenken muss: Kurztext, Kategorien, Zielgruppe, Reifegrad, Status,
Bilder, Links.

Dahinter steht eine Linie, die auch künftige Fragen entscheidet: **Das
Manifest ist die Wahrheit darüber, was die App *ist*; die Liste ist die
Wahrheit darüber, wie sie *dargestellt und eingeordnet* wird.** Wo die
Liste Manifest-Inhalte wiederholt, ist das eine beim Veröffentlichen
erzeugte Kopie — sie muss es sein, denn eine Store-Seite hat nur die
Liste und kann nicht für jede App das Repository klonen.

**Ein Detail mit Datenschutz-Wirkung:** Symbol und Screenshots sind
**Pfade in der Liste selbst**, keine beliebigen fremden URLs. Sonst
würde jeder Knoten, der die Store-Seite öffnet, Server kontaktieren,
die niemand ausgewählt hat — und dabei seine Existenz und Adresse an
Dritte melden, für ein Vorschaubild.

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
(Kategorien, Anwendungsklasse, Zielgruppe, Reifegrad, Status,
Vertrauen, Quelle, Lizenz, installiert, Knoten-Profil) und einer Suche
über Hashtags und Texte — Listenbericht plus Objektseite je App, so wie
die Design-Guidelines es vorsehen. Dazu die **Quellenverwaltung im
Portal**, womit Schritt 4 aus `portal-statt-cli.md` fällt.

**Deine sechs Antworten vom 09.08. sind eingearbeitet** (alle entlang
der Empfehlung, siehe „Decisions"). Eine Präzisierung ist beim
Schreiben dazugekommen: Ein Knoten darf eine Liste **nicht ablehnen**,
nur weil sie eine Kategorie nennt, die er noch nicht kennt — unbekannte
Werte landen unter „Sonstiges". Sonst würde jede Erweiterung des
Vokabulars genau die Knoten stranden lassen, die noch nicht aktualisiert
sind — dasselbe Versagen, gegen das B4 antritt.

**Fünf Punkte, bei denen ich noch eine Bestätigung brauche** (Details
unter „Open questions (second round)"):

1. **Lebenszyklus in Reifegrad + Status aufteilen, „new" berechnen** —
   wie oben begründet. Offen bleibt nur, ob Du „retired" und
   „deprecated" wirklich getrennt haben willst (nicht mehr
   weiterentwickelt vs. bitte nicht mehr neu installieren).
2. **Soll der Status Wirkung haben oder nur ein Abzeichen sein?**
   Vorschlag: Wirkung — „archived" wird standardmäßig ausgeblendet, und
   eine **installierte** App, deren Eintrag auf „deprecated"/„archived"
   springt, erscheint auf der Gesundheitsseite. Genau das hilft dem, der
   vor einem Jahr installiert hat. Preis: Der Knoten muss die Liste
   regelmäßig neu lesen, was er heute nicht tut.
3. **Bilder nur aus dem Repo der Liste** (siehe Datenschutz-Hinweis
   oben) — oder willst Du fremde Bild-URLs trotzdem erlauben?
4. **Anwendungsklasse steuert die Launchpad-Kachel:** ein `service`
   bekommt standardmäßig keine, je Instanz umstellbar. Das ist der
   einzige Punkt hier, der **bereits installierte Apps** verändert.
5. **`data` schon jetzt benennen**, obwohl es noch nicht installierbar
   ist?

Und ein Namenshinweis: **Varianten („preview", „demo") und der
Deploy-Kanal „production/test" sind verschiedene Dinge** mit gefährlich
ähnlichen Namen. Falls Dir ein besseres Wort einfällt — jetzt ist der
Moment.

## Deutsche Zusammenfassung — §8: auf Erweiterung gebaut

Deine zweite Runde (Abhängigkeiten, Portal-Capabilities, Varianten,
Compose-Profile mit Bündeln, App-Sets, kuratierte Hashtags) habe ich
genau so behandelt, wie Du es gerahmt hast: **Platz schaffen, nicht
alles bauen.** Das ist der billigste Teil des ganzen RFC — und der, den
man später nicht nachholen kann.

**Zwei Funde im Code, die das dringend machen.** Erweiterbarkeit
entsteht nicht durch leere Felder, sondern dadurch, was ein Leser mit
etwas Unbekanntem tut. Da antwortet der heutige Stand an zwei Stellen
schlecht:

1. **Die Manifest-Version wird auf Gleichheit geprüft.** `oaap_manifest`
   muss exakt `"0.1"` sein, im Schema steht `const`. An dem Tag, an dem
   wir Manifest `0.2` veröffentlichen — und genau das brauchen
   Abhängigkeiten —, **weisen alle Knoten im Feld solche Apps ab**.
   Nicht „ignorieren das neue Feld", sondern „Manifest ungültig". Das
   ist exakt die Falle, die Du vermeiden willst, und sie steckt heute
   im Code.
2. **Die Referenz erlaubt genau einen Service je App**
   („exactly one service is supported in runtime increment 1"), während
   das Schema mehrere zulässt. Deine Compose-Profil-Idee mit
   `small/medium/large` scheitert also **nicht** am Listenformat,
   sondern eine Ebene tiefer an der Mehr-Service-Fähigkeit der Laufzeit.
   Gut zu wissen, bevor man eine Bündel-Syntax für etwas entwirft, das
   noch nicht laufen kann.

**Drei Regeln, die spätere Ergänzungen ungefährlich machen:** Ein Leser
**ignoriert, was er nicht kennt, und lehnt nie deswegen ab**. Die
Ausnahme, die das erst sicher macht, heißt **`must_understand`** — ein
Eintrag darf sagen, welche Eigenschaften ein Leser verstanden haben
muss; wer eine davon nicht kennt, lehnt **diesen Eintrag** mit klarer
Meldung ab, statt etwas halb Verstandenes zu installieren (sonst würde
ein alter Knoten eine Abhängigkeit stillschweigend übergehen und eine
kaputte App installieren). Und die **Formatversion steigt nur**, wenn
ein Leser, der das Neue ignoriert, dadurch *falsch* läge. Daraus folgt:
strenge Prüfung in den **Werkzeugen** (Store Editor, CI — dort soll ein
Tippfehler auffallen), **tolerantes Lesen auf dem Knoten**.

**Namen sind der teure Teil**, deshalb jetzt reserviert und später
spezifiziert: `depends`, `recommends`, `suggests`, `conflicts`,
`provides` (Manifest), `requires_platform` (Capability + Version, z. B.
`oaap.core.portal >= 0.3`), `bundles` (Service-Auswahl im Manifest),
`sets` (Liste), `annotations` (Liste). Das Vokabular ist bewusst von
Debian geborgt, wie Du vorgeschlagen hast — die Wörter sind Jahrzehnte
alt und tragen den Unterschied zwischen „geht nicht ohne" und „ist
schöner mit" bereits in sich.

**Mein Veto, und Du hast ausdrücklich darum gebeten:** *Vokabular*
übernehmen, *Automatik* nicht. Ein Paketmanager löst Abhängigkeiten
automatisch auf, weil er aus **einem Archiv mit einem Namensraum, einer
Versionsdisziplin und einer Vertrauensentscheidung** schöpft. Wir haben
absichtlich das Gegenteil: mehrere Quellen verschiedener
Vertrauensklassen und die Regel, dass eine Installation aus einer
unbestätigten Quelle eine Bestätigung kostet. Eine automatische
Auflösung liefe an genau dieser Regel vorbei — der Store würde eine
Abhängigkeit aus einer Liste installieren, die sich nie jemand
angesehen hat. Also: **deklarieren, anzeigen, anbieten** („diese App
braucht X — mitinstallieren?"), nie still installieren; eine fehlende
Abhängigkeit **warnt statt zu blockieren**, dieselbe Haltung wie bei
Profilen und „expert only".

Dazu kommt ein Punkt, den Debian gar nicht kennt: Dort wird ein Paket
**einmal je System** installiert. Bei uns wird eine App zu **einer oder
mehreren Instanzen**, womöglich auf verschiedenen Knoten. „CRM braucht
Datenmodell X" hat deshalb keine eindeutige Antwort — welche Instanz,
auf welchem Knoten? Das ist eine echte Entwurfsfrage und verdient einen
eigenen RFC. Ins Format gehört heute nur die **Erklärung**, nicht die
Auflösung. Der Weg zum digitalen Zwilling führt übrigens über
`provides`: Ein Datenmodell erklärt `provides: ["twin.model.gebaeude"]`,
die Pflege-App verlangt genau diesen Namen — nicht eine bestimmte App,
sondern eine Fähigkeit. Genau dafür gibt es das Konstrukt.

**App-Sets sind keine Apps.** Dein „KI-Support" (ollama +
open-webui) ist ein Metapaket und bekommt eine **eigene Sammlung**
neben `apps` — ein Set hat keine Version, kein Paket, kein Manifest und
keine Gesundheitsprüfung; durch das App-Schema gepresst wären die
Hälfte der Pflichtfelder sinnlos. Es löst sich auch anders auf: Ein Set
wird erst zu App-Kennungen aufgefaltet, und jede davon geht dann den
normalen Weg mit eigener Quelle, Vertrauensklasse und Bestätigung.

**Und dabei habe ich mich selbst korrigiert — Dein Ideenspeicher war
schneller.** Ich hatte Deine Anwendungsklasse um einen dritten Wert
`data` ergänzt, für die Datenmodelle Richtung digitalem Zwilling. Im
Ideenspeicher steht dazu längst die bessere Antwort (aus dem
Vorlauf-Chat): **`kind: DataModel` als eigener Store-Artefakttyp neben
Apps**, separat paketier- und versionierbar — und derselbe Eintrag
sieht schon `kind: Agent` vor. Das ist richtig, und es ist keine
App-Klasse: Ein Datenmodell hat keinen Dienst, keine
Gesundheitsprüfung, keine Kachel. Daraus wird die eigentliche
Strukturentscheidung: **`apps` bleibt, was es ist** (das hält die
`0.1`-Listen lesbar), **und jeder weitere Artefakttyp bekommt eine
eigene Sammlung** — `sets` jetzt, `data_models` und `agents`
reserviert. Die Alternative, ein Feld `kind` in einer gemeinsamen
Liste, habe ich verworfen: Bei vier Typen, die sich nur Kennung, Name
und die Darstellungsfelder teilen, hinge fast jedes andere Feld an
einer Bedingung — ein Schema, das niemand sauber prüfen und niemand
lesen kann.

Zwei Namen aus demselben Ideenspeicher-Eintrag sind ebenfalls
reserviert und dürfen **nicht** mit den Debian-Wörtern verwechselt
werden: **`consumes`/`contributes`** (welche Datenbereiche eine App
liest bzw. verantwortet, mit der Owner/Contributor/Consumer-Logik von
dort). `depends`/`provides` beantwortet eine Frage über **Software**
(„braucht das installiert"), `consumes`/`contributes` eine über
**Daten** („liest/besitzt diesen Bereich"). Eine App kann einen
Datenbereich lesen, ohne von irgendeiner bestimmten App abzuhängen, die
ihn füllt — genau das ist der Sinn des Zwillings als gemeinsame Ebene.
Ehrlicher Umfang für die erste Fassung: anzeigen und die Mitglieder als
normale Installationen anbieten — **keine Transaktion, kein Rücknehmen,
wenn das dritte Mitglied scheitert**. Alles andere heißt Reihenfolge,
Teilfehler und Rückabwicklung; das ist echte Arbeit und für den Nutzen
nicht nötig. Und weil man es sonst garantiert verwechselt, zwei klar
getrennte Wörter: **Bündel** wählt Services *innerhalb einer App*, ein
**Set** fasst *mehrere eigenständige Apps* zusammen.

**Zu den kuratierten Hashtags — hier widerspreche ich Dir teilweise.**
Der Zug dahinter stimmt: Herausgeber-Hashtags sind Marketing, ein
kuratiertes Wort ist mehr wert. Aber über eine Einschränkung des Feldes
geht es nicht — **fremde Listen schreiben wir nicht**, und in unserer
eigenen bestimmen wir die Hashtags ohnehin dadurch, dass wir sie
hinschreiben. Was Du eigentlich willst, ist eine **Kuratierungs-Ebene**:
ein Eintrag in *unserer* Liste, der kein Paket mitbringt, sondern eine
App aus *einer fremden* Liste kommentiert — unsere Stichworte, unsere
Bemerkung, ein Prüfdatum. Das gäbe nebenbei der Klasse „geprüft" einen
Biss, den sie heute nicht hat: Vertrauen ist bisher eine Eigenschaft
der ganzen Quelle und nie einer einzelnen App. Lohnt sich — aber nicht
jetzt. Reserviert als `annotations`.

**Und die Regel, die künftig die meisten „wohin gehört das?"-Fragen
beantwortet, bevor sie zur Diskussion werden:** Eine **Tatsache über
die App** gehört ins **Manifest** (die Liste führt eine erzeugte
Kopie) — Abhängigkeiten, verlangte Plattform-Capabilities, Bündel,
Profile. Ein **Urteil über die App** gehört in die **Liste** —
Kategorien, Zielgruppe, Reifegrad, Status, Bilder, Bemerkungen; das
darf sich zwischen Listen unterscheiden, und das ist richtig so. Eine
**Tatsache über die Maschine** gehört in den **Knoten-Zustand** —
Profile, Quellen, Instanz-Konfiguration; niemals ins Manifest, sonst
macht eine App dem Betreiber Vorschriften.

**Alle vier Fragen entschieden (Jörg, 2026-08-09), entlang der
Empfehlung:** Die Manifest-Versionsprüfung wird gleich mitrepariert;
`must_understand` kommt; Sets bekommen eine eigene Sammlung; das Veto
gegen automatische Abhängigkeitsauflösung ist angenommen. Zur
Set-Frage kam eine Rückfrage — der ausschlaggebende Grund ist Regel 1
aus §8.2: Ein Knoten, der Sets nicht kennt, sieht den Schlüssel `sets`
schlicht nie. Stünde dasselbe Set in `apps`, zeigte derselbe Knoten es
als App ohne Version mit einem Installieren-Knopf, der scheitert.
Speicherung und Darstellung bleiben getrennte Fragen: Die Store-Seite
darf Sets und Apps trotzdem nebeneinander zeigen.

**Damit ist RFC-0012 abgenommen** — fünfzehn Fragen in drei Runden an
einem Tag. Die Baureihenfolge steht unter „Build order that follows
from this"; Schritt 1 (das Schema) ist erledigt:
`schema/oaap-store.schema.json`.

# oaap.data.model — Type Registry for the Digital Twin

- **ID:** `oaap.data.model`
- **Version:** 0.1
- **Maturity:** draft
- **Based on:** RFC-0031 (data model & digital twin — Model is Schritt
  2 of the build order: Store, Model, Twin, reference apps, browser,
  then broker) §3–§5, RFC-0012 §8.3 (the manifest names `data_model`,
  `contributes`, `consumes` reserved there) and §8.5 (the reserved
  store collection `data_models`), `oaap.data.store` (this registry's
  tables live in the store, schema `oaap_model` — no data of its own
  outside it), `oaap.apps.runtime` (manifest processing at install,
  RFC-0011 node profiles for the store the tables need)

## 1. Purpose

A **registry of types** — object, attribute, group, relation and
activity types (RFC-0031 §3.1) — with their origin (§4), value types,
per-type time model, optional aliases and optional semantic ID
(§3.7). It answers *what kinds of things exist, and what do they
mean?* and nothing else: this capability has **no instance data and no
service of its own** (RFC-0031 §2). `oaap.data.twin` (Schritt 3) is the
only reader of the instances such types describe; `oaap.data.model`
only ever reads and writes *definitions*.

Concretely, this capability:

- reads the manifest sections `data_model`, `contributes`, `consumes`
  at install time and turns them into registered types, tenant
  activations and instance bindings (§2.2–§2.4);
- lets a tenant define its own types from the CLI, standing in for the
  twin browser (`oaap.core.portal`'s Schritt 5, not yet built) —
  RFC-0031 §4 names this the third origin;
- compares two versions of the same type, allows what is additive,
  refuses what is destructive (§2.5);
- says, in a sentence, what an app's `contributes`/`consumes`
  declarations mean, **before** the install proceeds (RFC-0031 D7).

Out of scope for 0.1: instance data of any kind (Schritt 3), the twin
browser's type editor (Schritt 5 — the CLI `register` action is its
stand-in until then), the install-time picker dialog for an ambiguous
or unmatched binding (RFC-0031 D4 — 0.1 offers the CLI equivalent, an
explicit `--bind` flag, and refuses rather than guessing), semantic-ID
lookup against ECLASS/IEC CDD/AAS concept dictionaries (only the field
to hold one, per RFC-0031 §3.7).

**Where `global_asset_id` is configured is answered — not here.** The
E1–E3 decision record left it open between this capability and
`oaap.data.twin`, "je nachdem wo Mandanteneinstellungen dieser Art
schon liegen." They do not lie anywhere yet: `oaap.core.tenant` has no
per-tenant settings bag today, only fixed fields (§1.2 there), and the
field itself is computed **on every twin read**, never stored — it is
purely `oaap.data.twin`'s concern, has no type, no origin and no
version, and does not belong in a *type* registry at all. Schritt 3
answers it, by adding the one setting it actually needs; Schritt 2 has
nothing to add here because it never held a candidate for it.

## 2. Interface

### 2.1 Where the registry lives

Four tables in schema `oaap_model` of this node's `store`
(`oaap.data.store`), created on first use, **node-wide** — one
registry per node, not per tenant (RFC-0031 D2): `type_definitions`,
`type_aliases`, `activations` (tenant × type), `bindings` (instance ×
type). A node without the `store` profile (RFC-0011) therefore has no
model registry either; an app that declares `data_model`/`contributes`
/`consumes` still installs there, but its declarations are **not**
registered or bound, and the CLI says so plainly rather than failing
the install — the same posture `oaap.data.store` 2.1 takes for a node
that never carries it.

A `type_definitions` row is never deleted while an activation or a
binding references it (`ON DELETE CASCADE` runs the other way: dropping
a type drops its aliases/activations/bindings, not the reverse) — 0.1
has no CLI to drop a type at all; that is a Schritt-5 concern once a
type can be checked for instances.

### 2.2 The manifest sections (RFC-0031 §5, RFC-0012 §8.3)

Three names reserved in RFC-0012 §8.3 are specified here and become
part of `oaap.apps.runtime`'s manifest schema (its 2.2), effective from
**manifest 0.3**:

```yaml
data_model:                    # types this package ships, origin app:<id>
  object_types:
    - key: Customer
      title: Kunde
      title_plural: Kunden
      identifying: [VatId, Email]   # RFC-0031 §3.6 duplicate detection
  attribute_types:
    - key: VatId
      title: VAT-ID
      value_type: text            # text | int | decimal | bool | date | datetime | enum | ref
  group_types:
    - key: crm.core               # dotted: <namespace>.<name>
      on: Customer
      attributes: [VatId, Email]
      relations: [isContactOf]
      activities: [PhoneCall]
  relation_types:
    - key: isContactOf
      title: "is contact of"
      title_inverse: "has contact"
      from: Person
      to: Customer
      valid: true                 # opt-in validity axis (RFC-0031 §3.4)
  activity_types:
    - key: PhoneCall
      title: Phone call
      is_task: false

contributes:                     # what THIS app writes
  - type: Customer
    role: owner                  # owner | contributor
    group: crm.core              # required when role is contributor

consumes:                        # what THIS app reads
  - type: Person
    as: Mitarbeiter               # the app's own word (D4)
    fields: [reference, Email]    # omit for reference-only (D6)
```

Every list is optional and independent: a package may ship only
`data_model` (a `data_models` artefact, §2.6), only `consumes` (a pure
reader), or all three. Manifest tolerance (`oaap.apps.runtime` 2.2)
applies unchanged: a node on an older manifest MINOR ignores these
sections entirely rather than refusing the install — the app's
containers come up, its data-model declarations are simply never
registered. `must_understand` is deliberately **not** used for this:
omitting the sections costs a missing registration, not a broken
install (the same test 2.2 already applies to `app.class`).

**Structural validation** at install time (before anything else runs):
every type key is `[A-Za-z][A-Za-z0-9]*` except a group-type key, which
is dotted-lowercase (`[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)+`) so it reads
as `<namespace>.<name>` on the object page (RFC-0031 §3.3 example:
`crm.core`, `raci.assignments`); an `attribute_types` entry names one
of the fixed `value_type`s above; a `contributes` entry with
`role: contributor` names a `group`; every `type:`/`on:`/`from:`/`to:`
value is a non-empty string (resolved to a real type at install, not
at manifest-parse time — see §2.4). A malformed section refuses the
install with the field named, same as every other manifest error.

### 2.3 Registering a package's types

At install (and at every redeploy — a version bump is exactly the
moment a definition may change), each entry of `data_model` is
registered under origin `app:<app-id>` (RFC-0031 §4):

- **A key that does not exist yet** is inserted as-is.
- **A key already owned by this same app** is compared to what it held
  before (§2.5): additive is applied silently, destructive is refused.
- **A key already owned by a different origin** refuses the whole
  install with the owning origin named — RFC-0031 D1: *"an app cannot
  alter a type the tenant made; the tenant cannot alter a type the CRM
  shipped."* Registration is **all-or-nothing**: every entry is checked
  before any is written, so a conflict on entry five of six leaves the
  first four unregistered rather than half a package's model on the
  node.

The tenant origin (`model type add`'s CLI stand-in, and now the twin
browser too, Schritt 5) uses the same table with `origin =
"tenant:<tenant-id>"` and `package` set to the tenant-id. **This was
not the first shape** (0.1's own first build): `origin` was written as
the bare word `"tenant"`, identical for every tenant, on the claim
below that the ownership rule "applies identically" regardless of who
is asking. That claim was wrong, found while building Schritt 5's
"a tenant creates its own type" (2026-09-10), before it had ever been
exercised live: the ownership check at §2.3 compares `ex_origin !=
origin`, and a BARE `"tenant"` origin is the SAME string for every
tenant on the node — so tenant B registering the exact key tenant A
already claimed would pass that check (both origins read `"tenant"`)
and either update A's own definition (additive) or refuse the whole
install with a confusing "already registered" (destructive), neither
of which tenant B could make sense of, and neither of which protects
tenant A. Qualifying the origin with the tenant-id closes this the same
way `app:<id>`/`model:<id>` already close it for the other two origins
— the KEY namespace stays one flat, node-wide space by design (RFC-0031
D2: two unrelated tenants still cannot each own an UNRELATED type under
the identical key, e.g. two tenants each wanting their own "Status" —
deliberately left as a known 0.2 limitation, not fixed here, because
the tenant browser's own key-collision message is enough for now and a
per-tenant key namespace would touch every `on:`/`from:`/`to:`
cross-reference inside a definition too).

### 2.4 Binding, and activation (D4)

For each `contributes`/`consumes` entry, `type:` is matched against
the registry: an exact, case-insensitive key match first, then a
case-insensitive match against a registered alias (§2.6). Exactly one
candidate binds automatically and **activates** the type for the
instance's tenant (a row in `activations`, harmless to repeat). Zero or
more-than-one candidates is the case RFC-0031 D4 sends to an install
dialog; `oaap.core.portal` does not have one yet (Schritt 5), so 0.1's
CLI equivalent is: refuse the install, list the candidates (or say
there were none) by name, and name the flag that resolves it —

```
oaap app install <pkg> --bind Kunde=Customer --bind Mitarbeiter=Person
```

— one `--bind <as-or-type>=<platform-key>` per entry that needs a
choice, matched by the same word the manifest entry showed. A binding,
once made (automatically or by `--bind`), is recorded in `bindings`
(instance, type, direction, the app's own word, role/group or fields)
and **survives redeploy** like every other operator decision this
runtime keeps (`oaap.apps.runtime` §2.8's pattern) — a later install of
the same instance with an unchanged manifest does not ask again.

`oaap data model bindings <instance>` shows the recorded bindings —
this is the instance's own record of "who declared what", the CLI
stand-in for the instance page RFC-0031 §5 says will show it once
Schritt 5 exists.

### 2.5 Comparing two versions of a type (D2, additive vs. destructive)

A definition is a small tree (its own fields plus, for a group type,
the attribute/relation/activity keys it lists). Comparing old to new:

| Change | Kind |
| --- | --- |
| a new attribute/relation/activity/group type added to `data_model` | additive |
| a new field added to an existing type's own attributes (e.g. a title added where there was none) | additive |
| a group type gains an attribute/relation/activity in its list | additive |
| a type, or a member of a group type's list, is **removed** | destructive |
| `value_type` (attribute type) or `kind` changes | destructive |
| `from`/`to` (relation type) changes | destructive |

**0.1 refuses every destructive change unconditionally.** RFC-0031 §4
ties the refusal to whether the type *has instances* — Schritt 3 (the
twin) is what can answer that question, and it does not exist yet, so
0.1 is deliberately the conservative half of the rule: no migration
declaration exists to override it either. This is the open point
Schritt 3 must close, not a design decision made here — the same shape
as `id_short` being left to Schritt 3 in the E1–E3 decision record.
Until then, a destructive redeploy is refused with the field named and
a pointer to this paragraph; the fix at 0.1 is to keep the old member
and add the new one under a different key, same as any additive change.

### 2.6 Aliases

`oaap data model alias <type-key> <word>` adds a word that resolves to
a type in §2.4's matching, case-insensitively. Two different types
sharing one alias word is not rejected at registration — ambiguity is
a *binding-time* concern (§2.4 lists every candidate rather than
picking one), never a registration-time one, because a second app may
legitimately want to call its own type the same everyday word another
app already claimed for something else.

### 2.7 The declaration sentence (D7)

Before an install with `contributes` and/or `consumes` proceeds, the
CLI prints one sentence built from the manifest alone (no registry
lookup needed — it must be shown even on a node without `store`):

```
NOTE (RFC-0031 D7): this app reads Person and writes into Customer
(contributor: raci.assignments).
```

This is the phone-permissions pattern from the idea log, applied to
data instead of device access: the operator sees what the app touches
in a sentence, before the button that starts the install. `oaap.core.
portal`'s store page shows the same sentence once it exists (Schritt
5); 0.1 ships the sentence-generating function so that page has nothing
left to invent.

### 2.8 The reserved store collection `data_models`

RFC-0012 §8.5 reserves a top-level list collection `data_models` for
artefacts that carry `data_model` only — no service, no route, no
health check. This capability defines what such an artefact validates
against: `app`, `data_model`, and nothing that names a service.

**Recognised structurally**, not by a declared class: a manifest with a
`data_model` section and no `services` key at all is an artefact.
`app.class` (§2.10 of `oaap.apps.runtime`) is a launchpad-tile question
— orthogonal to whether a package has a container to begin with — so
it is not how this is decided. An artefact also has no `app.type`
(native/image/wrapped describe how a container is packaged; an
artefact never runs one) and must not declare `routes`, `endpoints` or
`storage` — refused if it does, naming the field, the same as every
other manifest error.

**Origin `model:<id>`, never `app:<id>`** (RFC-0031 §4): an artefact is
not an app, so its types register under a different namespace than an
app's own. **No instance is created either** — installing one leaves
no image, no container, no port, no row in the instance registry;
`oaap app list` does not show it and `oaap app remove` has nothing to
remove. Its only lasting effect is the type registration itself, which
follows §2.3's ownership rule exactly like an app's would. Reinstalling
the same artefact at a new version re-runs that comparison
(additive/destructive, §2.5) the same way a redeploy would.

Found and fixed while building the first real one, **Kundenzufriedenheit**
(RFC-0031 Schritt 4, second wave, 2026-09-10): the install path used to
call the registration function with `app:<id>` unconditionally,
regardless of whether the package had a service — meaning the very
first artefact would have registered under the wrong namespace. Fixed
at the one call site inside the shared install function, before any
artefact had shipped to find it live.

## 3. Configuration

None beyond what `oaap.data.store` already configures — this
capability adds no secret, no port, no service. `MANIFEST_MINOR` is
raised to 3 to admit the sections in §2.2; a node's tolerant reading
(`oaap.apps.runtime` 2.2) means this is not a flag day for nodes still
on an older reference version.

## 4. Security requirements

- Origin ownership (§2.3) is enforced on every registration, not only
  the first: an app cannot later "adopt" a type the tenant made by
  shipping a `data_model` entry with the same key.
- A tenant-created type (§2.3) is written with `origin: tenant:<id>`
  and the tenant-id as `package` — never the tenant's Kürzel
  (RFC-0025/0026, the same rule `oaap.data.store` already applies to
  schema names). The tenant-id qualifies the ORIGIN so two tenants
  cannot collide on ownership of the same key (§2.3's own Nachtrag);
  it does not qualify the KEY itself, which stays one flat, node-wide
  namespace like every other type (RFC-0031 D2).
- A twin-browser type creation (Schritt 5) may only INSERT a brand-new
  key, never touch one that already exists — the connecting role holds
  `GRANT INSERT` on `type_definitions`/`activations` only, never
  `UPDATE`/`DELETE`; the additive/destructive version diff this section
  otherwise relies on is exclusively `appctl.py`'s own code path, run
  by a human on the host, not reachable from a tenant's own session.
- Binding (§2.4) never infers a tenant or origin from anything but the
  caller's own identity (the instance being installed, or — for the
  CLI `register`/`alias` actions — the node operator); RFC-0031 §5's
  rule that origin never comes from a request body applies to the
  registry exactly as it will to the twin.
- The registry holds **no instance data**, so it carries none of
  `oaap.data.twin`'s access-control surface; reading `oaap data model
  types`/`show`/`bindings` reveals type *shapes* and which tenants
  activated them, never a row of anybody's data.

## 5. Conformance tests (described)

1. **Registration and ownership:** a package's `data_model` is
   registered under `app:<id>`; a second package trying to redefine the
   same key under a different origin is refused, naming the owner; a
   redeploy of the *same* app extending its own type (additive)
   succeeds silently.
2. **Additive vs. destructive:** a redeploy adding a new attribute type
   to an existing group type succeeds; one removing a member, or
   changing an attribute type's `value_type`, is refused with the
   field named and the install otherwise unchanged (checked: the
   previous definition is still what is registered).
3. **Binding:** an app's `consumes`/`contributes` entries bind
   automatically when `type:` matches a key or alias exactly once;
   zero or multiple candidates refuse the install and name them; an
   explicit `--bind` resolves a refusal and the binding then survives
   a redeploy of the same manifest without being asked again.
4. **The declaration sentence:** built from `contributes`/`consumes`
   alone (no registry access), matching the shape "reads X and writes
   into Y (role: group)" for the RFC-0031 §5 CRM/RACI example
   manifests verbatim.
5. **Node without `store`:** an app with a `data_model` section still
   installs on a node without the `store` profile; the CLI states
   plainly that nothing was registered, and `oaap data model types`
   answers the same "not carried" shape `oaap.data.store` 2.1 defines.

## 6. Dependencies

`oaap.data.store` (the registry's tables live in its `store` service,
schema `oaap_model`), `oaap.apps.runtime` (manifest schema and the
install path this capability hooks — the sections specified here
become part of manifest 0.3), RFC-0012 §8.3/§8.5 (the reserved names
this spec fulfils), `oaap.core.tenant` (tenant-id as the stable key
`activations` and a tenant-origin type are recorded under).

## 7. Maturity

`draft` — becomes `beta` once conformance tests 1–4 pass on the
reference platform (`oaap-test`) using the Partnerverwaltung/RACI
reference apps named in the bauplan's Schritt 4 as real `data_model`
manifests, and test 5 is proven on a node deliberately left without
the `store` profile.

## Deutsche Zusammenfassung (v0.1)

**Ein Register der Typen**, nicht der Daten: Objekt-, Attribut-,
Gruppen-, Relations- und Aktivitätstypen mit Herkunft (App, Modell-
Artefakt oder Mandant, RFC-0031 §4), Wertetyp, Zeitmodell je Typ und
optionalen Aliassen. Kein eigener Dienst, keine Instanzdaten — das ist
`oaap.data.twin` (Schritt 3). Die vier Tabellen liegen im Schema
`oaap_model` des `store` (`oaap.data.store`); ein Knoten ohne dessen
Profil installiert Apps trotzdem, registriert ihre Datenmodell-Angaben
aber nicht — und sagt das offen, statt zu scheitern.

**Zwei Manifest-Abschnitte** (`contributes`/`consumes`, dazu
`data_model` selbst) werden mit Version 0.3 des Manifests aktiv; ein
Knoten mit älterem Referenzstand liest sie tolerant und ignoriert sie
einfach — kein Stichtag für die Flotte.

**Herkunft entscheidet, nicht Reihenfolge:** eine App darf einen von
ihr geschaffenen Typ erweitern, aber nie einen fremden — auch der
Mandant selbst nicht, wenn eine App ihn geschaffen hat. Erweitern
(additiv) geht stillschweigend durch, Entfernen oder Ändern
(destruktiv) wird in 0.1 **immer** verweigert, weil erst Schritt 3
(der Zwilling) wissen kann, ob ein Typ überhaupt Instanzen trägt — eine
bewusst offene Stelle, kein vergessener Fall.

**Die Bindung** (`consumes`/`contributes` → ein wirklicher Typ) läuft
automatisch, wenn genau ein Treffer über Schlüssel oder Alias
existiert; sonst verweigert die Installation und nennt die Kandidaten
— der CLI-Ersatz für den Dialog, den erst der Zwillings-Browser
(Schritt 5) bekommt. Ein Satz aus Klartext (RFC-0031 D7) steht **vor**
diesem Schritt: "liest X, schreibt in Y" — dieselbe Idee wie
Berechtigungsklartext bei Smartphone-Apps, hier auf Daten angewendet.

**Und die offene Frage aus der E1–E3-Entscheidung ist beantwortet:**
Der Konfigurationsort für `global_asset_id` ist **nicht** hier — ein
Typregister ist der falsche Ort für ein Feld ohne Typ, ohne Herkunft
und ohne Version, das bei jeder Zwilling-Abfrage neu berechnet wird.
Das klärt Schritt 3.

**Nachtrag nach Schritt 4, zweite Welle (2026-09-10):** Ein `data_models`-
Artefakt (§2.8, ein Paket nur mit `data_model`, ohne `services`) wird
jetzt an genau diesem Merkmal erkannt, nicht an einer Klasse — und
registriert korrekt unter der Herkunft `model:<id>`, nicht `app:<id>`,
wie RFC-0031 §4 es vorsieht. Vor dem ersten echten Artefakt
(Kundenzufriedenheit) rief der Installationspfad die
Registrierungsfunktion unbedingt mit `app:` auf; das erste Artefakt
wäre unter der falschen Herkunft gelandet. Gefunden und behoben, bevor
es passieren konnte — an der einen Stelle, die jeder Installationsweg
durchläuft. Ein Artefakt hinterlässt bewusst **keine Instanz**: kein
Container, kein Port, kein Eintrag in der Instanz-Registrierung — nur
die Typregistrierung selbst bleibt bestehen.

**Nachtrag nach Schritt 5, dem Zwillings-Browser (2026-09-10):** die
Mandanten-Herkunft heißt jetzt `tenant:<mandant-id>`, nicht mehr das
bloße Wort `tenant` — §2.3 beschrieb bislang fälschlich, dass die
Eigentums-Prüfung zwei Mandanten schon auseinanderhält; tatsächlich las
sie für jeden Mandanten dieselbe Herkunft und hätte einen zweiten
Mandanten, der zufällig denselben Schlüssel wählt, entweder in den
ersten Typ hineinschreiben lassen oder mit einer unverständlichen
Meldung abgewiesen. Gefunden beim Bau des Browsers, der diesen Pfad
zum ersten Mal wirklich benutzt (die alte CLI-Aktion war bis dahin nie
produktiv gelaufen) — behoben an der Herkunft, nicht am Schlüssel: der
Schlüsselraum bleibt bewusst flach und knotenweit (RFC-0031 D2); zwei
Mandanten, die zufällig denselben Namen wählen, kollidieren weiterhin
und bekommen das jetzt als klare Meldung, statt eines stillen
Übergriffs. Der Browser selbst darf einen Mandanten-Typ nur NEU
anlegen, nie einen bestehenden ändern — die additive/destruktive
Versionsprüfung bleibt allein `appctl.py`s Sache, auf dem Host, von
Hand. Einzelheiten in [`oaap.data.twin.md`](oaap.data.twin.md) 0.2.

# RFC-0125: The Twin After the AAS Metamodel — Meaning for Every Attribute, Submodels With Structure, Attributes on Relations

- **Status:** **Draft (2026-11-24)** — D1–D9 open (§13). Nothing built,
  **nothing measured**. The facts in §1 were read the same day in RFC-0031,
  RFC-0120, `oaap.data.model` 0.5, `oaap.data.twin` 0.16, the twin's tables in
  reference 0.1.359 (`platform/appctl.py`), `program/aas-zuordnung-knotendaten.md`
  (14.11.) and the IDTA publications listed in RFC-0123 §12.4. What was **not**
  read is in §1.4; stage 0 (§12) answers it before anything is built on it.
- **Date:** 2026-11-24
- **Authors:** Jörg (the direction, 2026-11-24, while deciding RFC-0123 D23/D24:
  "Attribute sind in Teilmodellen integriert und diese wiederum an den
  Zwilling — unsere Asset Instanz — gekoppelt … dass es immer ein Teilmodell
  default gibt … Attribute haben immer eine Semantik analog zur Concept
  Description des AAS. Entweder selbstdefiniert und wir haben dafür ein eigenes
  ‚Glossar' oder von standardisierten Attributen abgeleitet … Teilmodelle
  können aber auch komplexe Unterstrukturen, Tabellen, Referenzen u. ä.
  abbilden … Zukünftig könnten unsere Zwillinge von extern angereichert werden
  und umgekehrt Zwillinge der Industrie anreichern"), Claude (facts, design)
- **Follows:** RFC-0123 D25 (this RFC), D23 (the bill of material after
  IDTA 02011), D24 (attributes on relations after the
  `AnnotatedRelationshipElement`)
- **Depends on:** RFC-0031 (the data model and the twin — "standard outside,
  own model inside"), RFC-0120 (the twin's external door, §4.9 "friendly to
  AAS"), RFC-0034 (files), RFC-0090 (lifecycle and erasure in the twin)
- **Related:** I-51 (self-growing CMDB, AAS as the guiding picture),
  `program/aas-zuordnung-knotendaten.md`, `program/zielbild-datenplattform.md`,
  RFC-0032 (events — the AAS event elements are left to the events capability,
  §11), RFC-0045 (business authorization), RFC-0123 (the first consumer)
- **Changes (when accepted):** `oaap.data.model` (concept descriptions, a
  semantic ID on every attribute type, structured value types, attributes on
  relation types, several instances of one group type, the default group),
  `oaap.data.twin` (storing and returning all of it; the AAS JSON read of one
  object), new `model:` artefacts for the first IDTA templates
- **Not part of this RFC:**
  - **The AAS repository API** (`oaap.data.aas`): registry, discovery, the full
    Part 2 interface. Own RFC, on top of this one. This RFC makes it a mapping,
    not a rebuild.
  - **BaSyx as storage.** RFC-0031 stays: BaSyx is a test bench and a partner
    to exchange with, not the twin's persistence.
  - **Operations** (methods on an asset, I-51 "Methoden für Besitzer"): named
    in the mapping (§3), designed elsewhere.
  - **Events** (`BasicEventElement`): the AAS calls them experimental; they go
    to the events capability (§11).
  - **Data spaces** (EDC, Dataspace Protocol): last, as RFC-0031 decided.

## Summary

The twin was built "standard outside, own model inside" (RFC-0031): our
**groups** are the AAS submodels, every group has one origin, and a type
**may** carry a semantic ID from ECLASS, IEC CDD or OAAP's own short form.
That was enough to make a later AAS export cheap. It is not enough for what
Jörg asked for on 2026-11-24: twins that industry can **enrich** and that
**enrich industry twins** — which needs the inside to be shaped so closely
after the AAS metamodel that the mapping is a rename, in both directions.

Five things are missing today, all measured or read on 2026-11-24:

1. A semantic ID is **optional** and most attribute types have none. Our own
   short-form IDs point at a domain where nothing answers: there is no
   **glossary** behind them.
2. An attribute holds **one flat value** (`text | int | decimal | bool | date |
   datetime | enum | ref`). A submodel can hold collections, lists,
   multi-language text, ranges, files and references.
3. A relation carries **no attributes** — RFC-0031 §3.5 promised them, the
   build dropped them, and stage 0 of RFC-0123 found the role on a
   responsibility silently lost (S3).
4. An object has **at most one group per group type** (the table's key is
   `(object_id, group_key)`). The AAS lets a shell hold several submodels of
   one template — one bill of material per view, as RFC-0123 D23 wants.
5. There is **no place for a loose attribute**: everything must be declared in
   a group type first.

The proposal, in one line each:

- **Every attribute has meaning** (D1): a standard ID, or an entry in **our
  glossary** that the platform creates if the author gives none — never "no
  meaning".
- **The glossary is a set of concept descriptions** after IEC 61360 (D2):
  name in several languages, definition, unit, data type, value list,
  "is a case of" a standard concept.
- **Structured values** (D3): collection, list, multi-language text, range,
  file, reference — stored in the value the twin already keeps as JSON, no new
  table.
- **Several instances of one group type** on an object, told apart by an
  instance key (D4).
- **A default group** per origin on every object for attributes that no group
  type declares — but each still with meaning (D5).
- **Relations get attributes** after the `AnnotatedRelationshipElement` (D6).
- **IDTA templates ship as `model:` artefacts**, starting with 02011 (bill of
  material) and 02006 (nameplate) (D7). Where an AAS **entity** lives follows
  the AAS's own rule: a self-managed entity is its own object, a co-managed
  one lives inside the group (D8).
- **One object reads out as an AAS shell with its submodels in AAS JSON**, and
  an IDTA template reads in as an artefact; BaSyx is the test bench (D9).

## 1. Facts

### 1.1 What the model can do today (read 2026-11-24)

| # | Fact | Where |
|---|---|---|
| F1 | Five kinds of type: object, attribute, group, relation, activity. A group type names the attributes, relations and activities it holds — "the direct counterpart of an AAS submodel template". | RFC-0031 §3.1, §3.3 |
| F2 | Every group has exactly one origin (app, artefact, tenant). Nobody writes into another origin's group. | RFC-0031 §3.3 |
| F3 | `value_type` is one of `text · int · decimal · bool · date · datetime · enum · ref`; an attribute may be `periodic` (values with a period side by side), carry a `unit`, be `personal`. | `oaap.data.model` §2.2 |
| F4 | The value is stored as **`jsonb`** (`attributes.value`); validity (`valid_from`/`valid_to`) and history (`recorded_at`, `superseded_by`) are per attribute row. | reference, `appctl.py` (twin schema) |
| F5 | A relation row is `object_id, group_key, rel_key, target_id, valid_from, valid_to, recorded_*` — **no value column**. The target is always an object of the same tenant (`uuid`). | reference, `appctl.py`; RFC-0123 S3 |
| F6 | `groups` has the key `(object_id, group_key)`: **one instance per group type and object**. | reference, `appctl.py` |
| F7 | `semantic_id` is optional on object, attribute, group and relation types; three forms: IRI, IRDI, `oaap-aas:<Submodel>/<major>/<minor>[/<Element>…]`, the last expanded against `OAAP_SEMANTIC_BASE` (default `https://objid.info/oaap/aas`) only when read. Changing one is destructive, adding one additive. | `oaap.data.model` §2.9 |
| F8 | Type definitions are **node-wide** (`oaap_model.type_definitions`, `definition` as text); a tenant activates them. Tenant types are named `t.<tenant label>.<key>`; attribute, relation and group keys stay node-wide and are reused when registered with the same meaning. | `oaap.data.model` §2.4, §2.10 |
| F9 | A package with `data_model` and no services is an **artefact**, origin `model:<id>`, no instance — the first was *Kundenzufriedenheit*. | `oaap.data.model` §2.8 |
| F10 | The twin's reads answer `semantic_iri` where a type has one; the export in JSON-LD uses it. The AAS door is "a mapping on top, not a rebuild". | RFC-0120 §4.9 |
| F11 | Our node data was already mapped onto IDTA templates (Software Nameplate 02007, 02011, Contact Information 02002, Time Series 02008 …) with own submodels in IDTA style where none fits; for events the recommendation was our own catalogue with an envelope shaped after `EventPayload`. | `program/aas-zuordnung-knotendaten.md` |

### 1.2 What the AAS asks for (read 2026-11-24, RFC-0123 §12.4)

- **IDTA 02011 v1.1** (bill of material): `EntryNode`, nested `Node`s (AAS
  `Entity`), plain `RelationshipElement`s `HasPart` / `IsPartOf` / `SameAs`,
  `BulkCount` **on the node**, `ArcheType`. Another BOM is joined by `SameAs`
  to its entry node (self-managed entity, own shell). BOM views are out of the
  template's scope.
- **IDTA 02011-1** (IEC 81346 extension): aspect nodes, among them
  **location** — our stock tree.
- **Digital Nameplate 3.0** (02006): article and piece identity with IEC CDD
  IRDIs.
- **DPP Part 1 Metadata** (02099-1, 2026-05): `granularity` Model · Item ·
  Batch; a DPP is a set of submodels plus this one.

### 1.3 What follows

- The **group already is the submodel**; what is missing is inside it
  (structure, F3) and around it (meaning, several instances, F6/F7).
- The **value is already JSON** (F4): structured values cost no new table, only
  a schema for the JSON and a check on write.
- The **relation is the one place the storage must change** (F5): a value
  column, like the attribute's.
- **Type definitions are node-wide** (F8): so is a glossary of the node's
  packages. A tenant's own concepts need a tenant part — the same split as
  `t.<tenant>.<key>` types.

### 1.4 Not read, not measured

- **AAS Part 1 (metamodel) itself.** The element names in §3 are those of the
  metamodel V3 as known from the IDTA templates read on 2026-11-14 and
  2026-11-24; the list of submodel element kinds and the IEC 61360 data
  specification fields are to be checked against Part 1 and Part 3a in
  stage 0 before the spec names a field.
- What BaSyx (2.0, still in milestones on 2026-11-04) accepts when given a
  hand-written export of one twin object.
- What querying into a structured `jsonb` value costs at the size of RFC-0123's
  stock (11 111 nodes).
- How many existing attribute types on the fleet have no semantic ID (the
  migration's size, D1).

## 2. The line, restated

RFC-0031's line stays: **standard outside, own model inside**, because the
twin's tree navigation, validity in time, activities and provenance are not in
the AAS and must stay fast. What changes is how close "inside" is drawn:

> **Every element of the twin maps onto exactly one element of the AAS
> metamodel, and back.** Where the AAS has something we lack, we add it in the
> AAS's shape. Where we have something the AAS lacks (validity, activities,
> origin), it goes out as a qualifier or an own submodel and comes back
> unchanged.

That is what makes both directions of Jörg's goal possible: a partner's
submodel can be read into a twin object without losing anything, and a twin
object can be read out into a partner's AAS environment.

## 3. The mapping

| AAS | Twin today | Twin after this RFC |
|---|---|---|
| Asset Administration Shell | object | object; the shell's `id` is the object's `urn:oaap:obj:<uuid>` (RFC-0031 §3.2) |
| `globalAssetId`, `specificAssetIds` | source keys `(origin, key)` | unchanged; a source key may name the `globalAssetId` of a foreign shell (§9) |
| `assetKind` Type / Instance | — | an object-type property `asset_kind: type · instance` (article vs. installed piece, DPP granularity Model vs. Item) |
| Submodel | group | group, with an **instance key** where one object has several of one type (D4) |
| Submodel template | group type | group type; IDTA templates as `model:` artefacts (D7) |
| `semanticId` of a submodel / element | optional `semantic_id` | **always present** (D1) |
| Concept Description | — | a **glossary entry** (D2) |
| `Property` | attribute, flat value | unchanged |
| `MultiLanguageProperty` | — | value type `mltext` (D3) |
| `Range` | — | value type `range` (D3) |
| `File`, `Blob` | — | value type `file`: a reference into `oaap.data.files` (RFC-0034), never the bytes in the twin |
| `ReferenceElement` | `ref` (an object) | value type `reference`: an object, an element of an object, or an external IRI (D3) |
| `SubmodelElementCollection` | — | value type `struct` with named fields, each with its own semantic ID (D3) |
| `SubmodelElementList` | — | value type `list` of one value type or one `struct` (D3) |
| `RelationshipElement` | relation | relation |
| `AnnotatedRelationshipElement` | — (dropped, S3) | relation with **annotations** (D6) |
| `Entity` (self-managed / co-managed) | — | self-managed = its own object; co-managed = a `struct` inside the group (D8) |
| Qualifier | — | how validity, origin and `recorded_*` go out (§10) |
| `Operation`, `Capability` | — | not here (owner methods, I-51) |
| `BasicEventElement` | twin events (RFC-0032) | not here (§11) |
| — (not in the AAS) | activity | goes out as an own submodel `oaap-aas:Activities/1/0` (§10) |

## 4. Meaning for every attribute (D1)

**Rule:** every attribute type, every field of a `struct`, every annotation of a
relation type has a semantic ID. It is one of:

1. a **standard ID** — an IRI of a published template element, or an IRDI from
   ECLASS or IEC CDD — written by the author;
2. an **entry in our glossary** written by the author (`oaap-aas:…`, §5);
3. **an entry the platform creates** when the author writes none: from the
   type's key, title, description, unit and value type, in the origin's part
   of the glossary (`oaap-aas:<origin>/<key>/<major>/<minor>`). The manifest
   check names every attribute that got one, so the author can replace it by a
   standard ID later.

Case 3 keeps RFC-0031's promise ("usable for a five-person company on day
one"): nobody has to know ECLASS to model a satisfaction score. But no
attribute is ever without a meaning a partner can look up.

**A standard ID that the author gives later** is additive when the old one was
platform-created (the created entry gets `is_case_of` → the standard, §5);
changing an author-given ID stays destructive (F7).

## 5. The glossary (D2)

A **glossary entry** is a concept description after the IEC 61360 data
specification (fields to be checked against Part 3a in stage 0):

| Field | Meaning |
|---|---|
| `id` | the semantic ID (short form or IRI) |
| `preferred_name` | per language, required in at least one |
| `short_name` | per language, optional |
| `definition` | per language |
| `data_type` | the value type of §6 |
| `unit`, `unit_id` | text and, where known, an IRDI of the unit |
| `value_list` | for enumerations: value + its own semantic ID |
| `is_case_of` | standard concepts this one is a case of (IRI/IRDI) |
| `origin`, `version` | who ships it, in which package version |

Where it lives — the same split as types (F8):

- **Node-wide entries** come with packages (apps, `model:` artefacts) in their
  manifest, next to `data_model`. They describe a package's public model and
  may be **published**: `OAAP_SEMANTIC_BASE` then answers the short form as a
  concept description (the domain that F7 already names, where today nothing
  answers). Publishing is per package and off by default.
- **Tenant entries** are made by a tenant (an integration client with
  `models`, or a person in the twin's browser) under
  `oaap-aas:t/<tenant id>/…`. They are readable **only through the twin's
  doors** of that tenant, never published, and the tenant label never appears
  in the ID (the label can change; the ID must not).

The glossary is read through the twin's doors (`GET …/concepts`, an MCP tool
`twin_concepts`), so an assistant asked "what does *Zufriedenheit* mean here?"
answers from it.

## 6. Structured values (D3)

New value types, all stored in the attribute's existing `jsonb` value:

| Value type | AAS | Stored as |
|---|---|---|
| `mltext` | MultiLanguageProperty | `{"de": "…", "en": "…"}` |
| `range` | Range | `{"min": …, "max": …}` of one numeric or date type |
| `file` | File / Blob | `{"file": <oaap.data.files id>, "content_type": "…"}` |
| `reference` | ReferenceElement | `{"object": <id>}` · `{"object": <id>, "path": "<group>/<element>"}` · `{"iri": "…"}` |
| `struct` | SubmodelElementCollection | an object of named fields; the type declares each field with its own value type and semantic ID |
| `list` | SubmodelElementList | an ordered array of one value type or one `struct` |

- **Nesting** is allowed (`list` of `struct` with a `list` inside), bounded by a
  depth and a size the spec fixes after stage 0 measures the cost.
- **Validity and history stay per attribute** (F4): a changed field in a
  `struct` writes a new row for the whole value. That is coarser than per
  field and is the price of no new table; stage 0 measures whether it is
  acceptable for a `list` of a few hundred entries.
- **`personal`** may be set per field; an export leaves those fields out (twin
  §2.18).
- **Search and filters** reach into a `struct` by path in a later stage; the
  first stage returns and writes structured values whole.

## 7. Groups: several instances, and the default group

### 7.1 Several instances of one group type (D4)

A group gets an optional **instance key**: `bom.hierarchy` (the one, as today)
or `bom.hierarchy:sales`, `bom.hierarchy:manufacturing`. The key of `groups`
becomes `(object_id, group_key, instance)`, with `instance = ''` for every
existing row. The AAS reads it as two submodels with the same `semanticId` and
different `idShort`s.

### 7.2 The default group (D5)

Every origin has, on every object it may write to, a **default group**
`<namespace>.default` (`tenant.default` for the tenant). It holds attributes no
group type declares, under one condition: **each attribute names a glossary
entry or a standard ID** (§4) — the value type comes from there. So "put any
attribute anywhere" is possible without a schema, and still no attribute is
without meaning. The default group goes out as an own submodel of that origin
(`oaap-aas:<origin>/Default/1/0`).

## 8. Attributes on relations (D6)

A relation type declares **annotations** — a list of attribute types, each with
its semantic ID, the same declarations an attribute type has:

```yaml
relation_types:
  - key: responsibleFor
    title: "is responsible for"
    title_inverse: "has responsible"
    from: Person
    to: StockNode
    valid: true
    annotations: [ResponsibilityRole]   # attribute types, with semantic IDs
```

- Stored in a new `jsonb` column `relations.annotations`; validity and history
  stay per relation row (a changed role ends one row and starts the next).
- An annotation the type does not declare is **refused** with its name — no
  longer silently dropped (RFC-0123 S3).
- Goes out as an `AnnotatedRelationshipElement`; a relation without
  annotations stays a `RelationshipElement`.
- RFC-0123 D24 is the first use (the role on a responsibility). A bill of
  material does **not** use it for quantities: as in 02011, the quantity is on
  the node (§9).

## 9. IDTA templates as artefacts, and where an entity lives (D7, D8)

**D7.** A published IDTA template becomes a `model:` artefact (F9) whose group
types, attribute types and glossary entries carry the template's own semantic
IDs: `model:idta-02011` (bill of material, with the IEC 81346 aspects),
`model:idta-02006` (nameplate). A tenant activates them like any type.
Later: Contact Information 02002, Handover Documentation 02004, Technical Data
02003, DPP Metadata 02099-1. A new template version is a new artefact version
under the additive/destructive rule (`oaap.data.model` §2.5).

**D8 — where a 02011 `Entity` lives.** The AAS itself draws the line:

- A **self-managed entity** has its own shell (`globalAssetId`). In the twin it
  is **its own object**, and the BOM's `HasPart` is a relation to it. This is
  RFC-0123's stock: every site, room and installed piece is an object, the
  tree is relations, the location aspect of 02011-1 names the levels.
- A **co-managed entity** has no shell of its own. In the twin it is an entry
  in a `list` of `struct` inside the BOM group, with `BulkCount` as a field.
  This is an article's sales or manufacturing BOM: positions with quantity,
  kind (assembly, purchased item, service — a field with its own semantic ID,
  since 02011 has none) and a `reference` to the article it uses.
- **Nesting another BOM** (an assembly with its own BOM) is a `reference` from
  the position to the other article object — `SameAs` to its entry node — never
  a copy, exactly as 02011 does it.
- A BOM **per view** is one instance of the BOM group per view (D4).

So a stock of 11 111 nodes stays objects and relations (fast tree, validity per
relation, RFC-0123 D26), and an article's BOM with 40 positions stays one group
value (one read, one write).

## 10. In and out (D9)

**Out — one object as AAS JSON.** A read `GET …/objects/{id}/aas` answers the
object as one shell with its groups as submodels, in the JSON serialization of
the metamodel V3. Our own things go out in the AAS's shape:

- validity, origin and `recorded_at` as **qualifiers** on the element
  (`oaap:validFrom`, `oaap:origin`, …, own semantic IDs);
- activities as an own submodel `oaap-aas:Activities/1/0`;
- the glossary entries used, as concept descriptions in the same document.

It follows every rule of the twin's doors (D14 of RFC-0123, `personal`
fields left out, the reader's rights).

**In — a template as an artefact.** A tool reads an IDTA template's JSON and
writes the `model:` artefact (group types, attribute types, glossary entries).
Reading a partner's **instance** submodel into a twin object comes after; it
needs the merge rules of RFC-0031 §3.6 and is its own decision.

**BaSyx as the test bench.** Stage 3 loads the read-out of real objects into a
BaSyx AAS environment (packages exist as conversions under
`program/studio/builds/dacks-converted/aas-*`) and checks it opens there
unchanged. That is the measure of "industry can read our twins".

## 11. Events — handed to the events capability

The AAS's `BasicEventElement` / `EventPayload` are experimental in the
metamodel (F11). Jörg asked on 2026-11-24 (with RFC-0123 D15) for events to
become a **platform capability** in their own right, after **CloudEvents**:
apps publish and subscribe, with a broker, webhooks or messaging as the
integration layer. That is its own RFC (I-69). This RFC only asks of it that a
twin change event names the object, the group (with instance key) and the
semantic ID of what changed, so a subscriber can filter by meaning.

## 12. Stages

| Stage | What | Measured by |
|---|---|---|
| **0** | Read AAS Part 1 and Part 3a for the element kinds and IEC 61360 fields; count attribute types without semantic ID on the fleet; load one hand-written export into BaSyx; measure `jsonb` writes and reads of a `list` of 500 `struct`s and a path query on 11 111 nodes. | this RFC's §1.4 answered |
| **1** | Attributes on relations (D6) and meaning for every attribute (D1) with the glossary (D2), node-wide and per tenant, read through the doors. **RFC-0123 stage 1 needs this stage.** | a responsibility with a role written and read; a type without ID gets one; glossary through portal, `/twin/v1` and MCP |
| **2** | Structured values (D3), several instances (D4), the default group (D5). | a BOM with nested positions; two BOM views on one article |
| **3** | `model:idta-02011` and `model:idta-02006` (D7, D8); one object read out as AAS JSON (D9) and opened in BaSyx. | BaSyx shows the shell and both submodels unchanged |
| **4** | The template reader (D9 "in"). | 02011 read from its published JSON gives the same artefact as stage 3 |
| later | `oaap.data.aas` (repository API, registry, discovery); reading a partner's instance submodel; search inside structured values. | own RFCs |

## 13. Decisions (open)

| # | Question | Recommendation | Not chosen |
|---|---|---|---|
| **D1** | Must every attribute have a semantic ID? | **Yes**, and the platform creates a glossary entry when the author gives none (§4). Existing types get one on the next registration (additive). | Required from the author (blocks small companies); optional as today. |
| **D2** | What is the glossary, and where does it live? | **Concept descriptions after IEC 61360**, node-wide from packages (publishable per package under `OAAP_SEMANTIC_BASE`, off by default) and per tenant (never published, ID without the tenant label) (§5). | Only standard IDs; a free-text glossary without data type and unit; one glossary for the whole node including tenants. |
| **D3** | How do submodels get structure? | **New value types** `mltext`, `range`, `file`, `reference`, `struct`, `list` in the existing JSON value; history per attribute (§6). | A table per element kind (closer to the AAS, much more work, slower trees); only flat values plus groups. |
| **D4** | Several submodels of one template on one object? | **An instance key** on the group (`bom.hierarchy:sales`) (§7.1). | A group type per view (`bom.sales`, `bom.manufacturing` — the template's ID would no longer say which template); BOM views as separate objects. |
| **D5** | A place for undeclared attributes? | **A default group per origin** on every object; each attribute names a glossary entry or standard ID (§7.2). | None (everything declared first); a default group without meaning. |
| **D6** | Attributes on relations? | **Annotations declared on the relation type**, a `jsonb` column, refused when undeclared; out as `AnnotatedRelationshipElement` (§8). Fixes RFC-0123 S3. | A responsibility object between person and node (RFC-0123 D24 already chose this RFC's way). |
| **D7** | How do IDTA templates enter? | **As `model:` artefacts** with the template's own IDs, first 02011 (with 02011-1) and 02006 (§9). | Each app copies what it needs; a node-wide built-in set. |
| **D8** | Where does a 02011 entity live? | **The AAS's own line:** self-managed = own object (the stock), co-managed = `struct` in the group (an article's positions); nesting by reference, never copy (§9). | Every position an object (40 objects per article BOM, a write per position); every BOM a single value (no tree for the stock). |
| **D9** | Which way in and out first? | **Out first**: one object as AAS JSON, checked in BaSyx; in: IDTA templates as artefacts; partner instances later (§10). | The full repository API first; import first. |

## Deutsche Zusammenfassung

**Worum es geht.** Jörg will, dass unsere Zwillinge von der Industrie
angereichert werden können und umgekehrt Industrie-Zwillinge anreichern. Dafür
muss unser Datenmodell so eng an der Verwaltungsschale (AAS) liegen, dass die
Abbildung in beide Richtungen ein Umbenennen ist, kein Umbauen. Die Linie aus
RFC-0031 bleibt: außen der Standard, innen das eigene Modell (schnelle Bäume,
Gültigkeit, Aktivitäten, Herkunft). Neu ist: Jedes Element des Zwillings
entspricht genau einem Element des AAS-Metamodells.

**Was heute schon passt.** Unsere Gruppen sind die Teilmodelle, jede mit
einer Herkunft; eine semantische ID ist möglich; der Wert eines Attributs liegt
schon als JSON in der Datenbank.

**Was fehlt (am 24.11. gelesen).** Die Semantik ist freiwillig und meist leer,
und hinter unserer Kurzform antwortet kein Glossar. Ein Attribut hat nur einen
flachen Wert. Beziehungen tragen keine Attribute (RFC-0123 S3). Ein Objekt hat
je Gruppentyp nur eine Gruppe, also keine Stückliste je Sicht. Es gibt keinen
Platz für ein loses Attribut.

**Vorschlag (D1–D9, offen):**
- **D1:** Jedes Attribut hat eine Semantik. Wer keine angibt, bekommt von der
  Plattform einen Glossareintrag.
- **D2:** Das Glossar besteht aus Concept Descriptions nach IEC 61360 (Name
  mehrsprachig, Definition, Einheit, Datentyp, Werteliste, „ist ein Fall von“
  einem Standard). Knotenweit aus Paketen, auf Wunsch veröffentlicht; je
  Mandant nur über die Türen des Zwillings.
- **D3:** Neue Wertetypen: mehrsprachiger Text, Bereich, Datei, Verweis,
  Struktur, Liste. Gespeichert im vorhandenen JSON-Wert, ohne neue Tabelle.
- **D4:** Mehrere Gruppen eines Typs je Objekt über einen Instanzschlüssel,
  z. B. `bom.hierarchy:sales`.
- **D5:** Jede Herkunft hat auf jedem Objekt eine Vorgabe-Gruppe für lose
  Attribute, aber jedes davon mit Semantik.
- **D6:** Beziehungen bekommen Attribute nach dem
  `AnnotatedRelationshipElement`. Was nicht erklärt ist, wird abgewiesen statt
  still verworfen.
- **D7:** IDTA-Vorlagen kommen als `model:`-Artefakte, zuerst die Stückliste
  02011 (mit Ortsaspekt) und das Typenschild 02006.
- **D8:** Wo ein Stücklisten-Knoten liegt, entscheidet die AAS selbst: mit
  eigener Schale ist er ein eigenes Objekt (der Bestand), ohne eigene Schale
  ein Eintrag in der Gruppe (die Positionen eines Artikels). Verschachtelt wird
  über Verweis, nie über Kopie.
- **D9:** Zuerst nach außen: ein Objekt als AAS-JSON, geprüft in BaSyx. Nach
  innen zuerst die IDTA-Vorlagen; Instanzen von Partnern später.

**Ereignisse** gehören nicht hierher: Jörg will sie als eigene
Plattformfähigkeit nach CloudEvents (eigenes RFC, I-69).

**Stufen.** Stufe 0 liest das AAS-Metamodell im Original nach und misst Kosten
und BaSyx. **Stufe 1** (Beziehungsattribute, Semantik, Glossar) braucht
RFC-0123 für seine erste Stufe. Stufe 2 Strukturen und Instanzen, Stufe 3
Vorlagen und Export, Stufe 4 der Vorlagen-Leser. Die AAS-Schnittstelle
`oaap.data.aas` folgt als eigenes RFC.

**Nicht gelesen, nicht gemessen:** das AAS-Metamodell (Teil 1, Teil 3a) im
Original; was BaSyx annimmt; die Kosten strukturierter Werte; wie viele
Attributtypen heute ohne Semantik sind.

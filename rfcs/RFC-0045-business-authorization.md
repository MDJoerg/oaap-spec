# RFC-0045: Business Authorization — The App Declares, the Tenant Grants, the Data Holder Checks

- **Status:** **Accepted (2026-09-29)** — three questions decided by
  Jörg before the draft (2026-09-28), A1–A7 decided as recommended the
  next day. **A8 was not decided but reopened** with a direction: value
  lists belong to *semantic types* modelled on the AAS Concept
  Description, which is a change to `oaap.data.model` and gets its own
  RFC (§6.1). This RFC's steps 1–4 do not wait for it — a manifest
  `values:` list covers them, and §6.5 records what was checked so that
  nothing here blocks that RFC. **Stages 1 and 2 built 2026-10-03** (§11.1);
  **stage 3 built 2026-10-03** (§11.2).
- **Date:** 2026-09-28
- **Authors:** Jörg (the idea, the SAP/BTP comparison, the club and CRM
  cases), Claude (design and write-up)
- **Depends on:** RFC-0002 (security-first access model, the standard
  roles), RFC-0004 (manifest), RFC-0007 (visibility groups), RFC-0014
  (the manifest owns the words), RFC-0022 (tenant as boundary), RFC-0026
  (names are changeable, identity is not), RFC-0027 (machine principals
  and API keys), RFC-0031 (the digital twin), RFC-0040 (the person
  behind the name), RFC-0041 (external identity providers)
- **Amends:** RFC-0041's rule *"A provider's claims never become OAAP
  roles"* — sharpened, not weakened (§5, Decided 1)
- **Drivers:** the club service of `oaap-hbsha` (letter of 2026-09-19:
  Bereichsverantwortliche, Trainer, Sponsoren — hundreds of external
  people, all with platform role `user`); Jörg's CRM-style business apps
  (customer class A–D); `partnerverwaltung` as the tenant's who-is-who

## Summary

OAAP has eight **platform roles**. They decide who enters the node, a
route, a tenant — and they are a security boundary, not a vocabulary
for business. Everything a person does *inside* an app — a trainer
editing the line-up of *their* team, a sponsor maintaining *their own*
advertising, a clerk reading customers of class A–C but changing only
class D — is today every app's own problem.

This RFC proposes an **optional platform capability,
`oaap.core.authorization`**, built on three separations taken from SAP
BTP and one idea taken from classic SAP:

1. **The app declares** what can be allowed — authorization objects
   with activities and fields, and role templates — in its manifest.
   Definition per package, activation per tenant, exactly like the
   twin's types (RFC-0031 D2).
2. **The tenant grants** — its `tenant_admin` builds roles from
   templates, bundles them into role collections across apps, and
   assigns them to people, to OAAP groups, or to groups asserted by the
   tenant's identity provider through a mapping it writes itself.
3. **The data holder checks** — an app checks what concerns its own
   functions and data, with the effective authorizations the platform
   hands it; for data in the twin, the twin is the natural checker
   (reserved as a direction, §8.3, not decided).

From classic SAP it takes the **authorization object with activity and
field values** — because "read A, B, C, but change only D" is two
authorizations on one object, which BTP's role attributes cannot say
cleanly. From the club it takes the **contextual grant**: *person X has
role Y in context Z, granted by W* — one role "Trainer", many
assignments, one per team, instead of one role per team.

**Nothing is forced.** An app that declares nothing keeps its own
model, and loses nothing. This matters because the platform told
`oaap-hbsha` on 2026-09-21 to keep its own grant model (§0.3).

## 0. Why now

### 0.1 Apps from one hand start to work together

The twin (RFC-0031) was built so that apps couple loosely through
shared objects: the partner management owns the company, RACI and the
project app refer to it. The next step is business apps with business
roles, and the moment two of them need the same concept — "the teams
this person coaches", "the customers this clerk may change" — each
would build its own role table, its own admin page, its own assignment
dialog, and its own mistakes. For apps from Jörg's own hand that is
pure duplication; for a customer it is a separate admin screen per app.

### 0.2 What exists does not fit

- **Platform roles** (`oaap.core.identity` 2.1) are fixed, node-wide in
  meaning, and deliberately few. Adding `trainer` or `sponsor` to the
  enum would make a business word a platform word — the exact confusion
  RFC-0039 had to undo for `partner`, found in **nine** places.
- **Visibility groups** (RFC-0007) answer "which tile do I see". There
  is no `X-OAAP-Groups` header, no delegation, no registry — the
  platform's own letter to hbsha (2026-09-21, §4) listed exactly these
  three reasons why they are the wrong tool for "Mannschaft je Saison".
- **RFC-0041's mapping** carries a realm group to a visibility group,
  written by the operator, and — read in the code, not measured —
  applied **only at the first login** (`idp.first_login_grant`,
  `services/identity` line ~1803). A person removed from a realm group
  later keeps whatever the first login gave them. For visibility that
  was a tolerable simplification; for business rights it is not (§5.2).

### 0.3 The position this changes, said out loud

On 2026-09-21 the platform answered hbsha: *"Euer eigenes
Freigabemodell … ist die richtige Antwort und gehört zu euch."* That
answer stays true for them: **this RFC does not ask any app to move.**
What changed is the number of consumers. hbsha's model — *person X has
role Y in context Z, granted by W; nobody grants more than they hold in
the same context* — is precisely what a platform service would offer
(§3.3, §4). It is adopted here nearly word for word, as an **offer**:
hbsha may use it, keep its own, or move later. A letter says so
(§11, step 0).

## 1. Two layers, never mixed

```
 ┌──────────────────────────────────────────────────────────────────┐
 │ PLATFORM ROLES (unchanged)       server_admin … user, guest,    │
 │ who enters the node, the tenant, partner — gateway, /verify,     │
 │ the route                        X-OAAP-Roles                    │
 ├──────────────────────────────────────────────────────────────────┤
 │ BUSINESS AUTHORIZATION (new)     objects, activities, fields,    │
 │ what one does inside an app      templates, roles, collections,  │
 │                                  contexts — oaap.core.authz      │
 └──────────────────────────────────────────────────────────────────┘
```

- A business grant **never** confers a platform role, never opens a
  route, never crosses the tenant. Route gating stays with platform
  roles: a trainer is a `user` at the gateway and a trainer in the app.
- A platform role **never** implies a business grant. `tenant_admin`
  administers business roles; it does not automatically *hold* them
  (like SAP's user administrator, who is not thereby a sales clerk).
  Whether an app treats `admin` as "everything in my app" stays the
  app's own choice, as today.

### 1.1 Vocabulary

| OAAP (this RFC) | classic SAP | SAP BTP | club example |
| --- | --- | --- | --- |
| **authorization object** | Berechtigungsobjekt | scope (roughly) | `team` |
| **activity** | ACTVT | scope | `edit_lineup` |
| **field** | Berechtigungsfeld | attribute | `team`, `age_group` |
| **role template** (app) | Rollenvorlage / Masterrolle | role template | `trainer` |
| **role** (tenant) | abgeleitete Rolle | role | "Trainer Jugend" |
| **role collection** (tenant) | Sammelrolle | role collection | "Trainerteam" |
| **assignment** | Benutzerzuordnung | role collection assignment | Ben → Trainer |
| **context** | (Strukturelle Berechtigung, HCM) | — | Mannschaft mB |
| **mapping** | — | IdP group → role collection | realm group `vorstand` |

**Deliberately left behind** from SAP: profile generation, transaction
codes as authorizations, nested composite roles, an `SAP_ALL`, and
authorizations edited field by field. Everything starts from a template
the app shipped.

## 2. What the app declares

A new, optional manifest section. Keys are namespaced by app id at
registration (`<app>.<object>`), so two apps cannot collide on `team`.
Titles are the manifest's words (RFC-0014).

```yaml
authorization:
  objects:
    - key: team
      title: Mannschaft
      activities: [read, edit_lineup, manage_members]
      fields:
        - key: team
          context: Mannschaft          # a twin object type (§6.2)
    - key: ad
      title: Werbemittel
      activities: [read, create, change, delete, report]
      fields:
        - key: sponsor
          context: Organisation
    - key: news
      title: News
      activities: [read, publish]
      fields:
        - key: area
          values: [sponsoring, news, hallenzeiten, helpdesk]   # fixed list

  role_templates:
    - key: trainer
      title: Trainer/in
      grants:
        - object: team
          activities: [read, edit_lineup, manage_members]
          team: $context               # filled by the assignment (§3.2)
      may_grant: [co_trainer, zeitnehmer, spieler]   # delegation (§4)
    - key: spieler
      title: Spieler/in
      grants:
        - object: team
          activities: [read]
          team: $context
    - key: sponsor
      title: Sponsor
      grants:
        - object: ad
          activities: [read, create, change, delete, report]
          sponsor: $context
    - key: bereich
      title: Bereichsverantwortliche/r
      grants:
        - object: news
          activities: [read, publish]
          area: $value                 # filled by the tenant's role (§3.1)
```

A field's value comes from one of three sources:

| source | meaning | filled by |
| --- | --- | --- |
| `values: [...]` | a fixed list in the manifest | the tenant's role (`$value`) |
| `concept: <id>` | the value list of a **semantic type** (§6.1) — *reserved until that RFC* | the tenant's role (`$value`) |
| `context: <type>` | objects of a twin type | the assignment (`$context`) |

A template may also fix a value itself (`area: [news]`); then the
tenant cannot change it.

**A role stores a value's id, never its label.** For `values:` the id
is the manifest key; for `concept:` it will be the value's own id in
the semantic type (the AAS `valueId`). "Klasse D" renamed to
"Premium" must not change what a role grants — RFC-0026, applied to
values.

**Registration and change** follow `oaap.data.model` §2.3/§2.5 on
purpose: installing a package registers its declaration, and a new
version is compared to the old one — a new object, activity or template
is *additive*; a removed activity, a removed field or a changed field
source is *destructive* and is shown before the install proceeds,
naming the roles that would lose something.

**Readers of the new section** — before building, search every
repository, do not trust this list (RFC-0039's lesson: five named,
nine found): `oaap.apps.runtime`'s manifest schema, `schema/`,
`check-store.py`, Studio's manifest check and briefing, the store
editor.

## 3. What the tenant grants

### 3.1 Roles and role collections

A **role** is a template plus values, owned by the tenant: "Bereich
News" = template `bereich` with `area = news`. Jörg's CRM case is the
same mechanism with two grants on one object:

- Rolle „Vertrieb Süd" (template `sales_clerk`)
  - `customer` · read → customer class A, B, C, D
  - `customer` · create/change/delete → customer class D

A **role collection** bundles roles across apps ("Innendienst" =
Vertrieb Süd from the CRM + Bearbeiter from the complaints app). Only
collections are assigned; a single role is a collection of one, created
implicitly, so there is one assignment path, not two.

### 3.2 Assignments — to whom, and in which context

An assignment names:

- **who** — a person by their **user id** (RFC-0040's UUID, never the
  username, never the e-mail), an OAAP visibility group, or an IdP group
  through the mapping (§5);
- **what** — one role collection;
- **where** — the context object(s) for every `$context` field its
  templates carry, as **twin object ids** (§6.2);
- **how long** — `valid_from`/`valid_to`, optional (a season);
- **by whom** — `granted_by`, always recorded, never supplied by the
  caller.

The context sits in the **assignment**, not in the role. That is the
point of it: Ben is Trainer of mB and Carla is Trainer of mC with the
**same** role. SAP solves this with one derived role per organisational
value, which is how SAP systems end up with ten thousand roles; the
club has hundreds of short-lived contexts (hbsha's own words) and
would drown the same way.

### 3.3 Who may maintain all of this

- **`tenant_admin`** of the tenant: roles, collections, assignments,
  and the IdP mapping (Decided 2). Every change is an entry in that
  tenant's log (`oaap.core.tenant` 1.7), as for every other identity
  setting.
- **`server_admin`**: the same, as operator — never *more*, because
  there is nothing above the tenant here.
- **Delegates** (§4): exactly the assignments their own templates
  allow, in their own contexts.

## 4. Delegation — nobody grants more than they hold

hbsha's rule, made structural rather than checked afterwards. A holder
of a template with `may_grant: [co_trainer, spieler]` may create
assignments

1. only of the **listed** templates (or collections consisting only of
   them),
2. only in contexts where they **themselves** hold the granting
   assignment (Ben: mB, not mC),
3. only **until the end of their own** assignment's validity,
4. never with `may_grant` of their own unless their template lists a
   template that has it — so a delegation chain is exactly as deep as
   the app's declaration makes it, and no deeper.

What happens to Zeitnehmer Tim when trainer Ben leaves is A2.

## 5. The identity provider's groups (amends RFC-0041)

### 5.1 The sharpened rule

RFC-0041 says: *"A provider's claims never become OAAP roles."* This
RFC keeps the sentence and says what it now means (Decided 1):

- A provider's claims **never** become **platform** roles — unchanged,
  not negotiable, and `idp.first_login_grant` keeps ignoring every
  asserted role.
- A provider's **group membership** MAY be mapped to a **role
  collection** by a local mapping the tenant writes. An unmapped group
  grants nothing. Whatever the provider can assert — groups,
  organization membership, realm or client roles — is read as
  *membership*, never as a right: the provider says who, OAAP says what.

**Why the `tenant_admin` may write it** (Decided 2), although K4b gives
the first-login switch to the operator only: K4b protects the *node* —
a tenant that could open itself would open a door on a machine that
carries other customers. A business role reaches nothing outside the
tenant. A club that maps its own realm group onto its own "Vorstand"
collection gains nothing it could not grant by hand. The existing
mapping to **visibility groups** stays operator-only, unchanged.

### 5.2 Membership must be re-read, not remembered

The mapping is evaluated at **every** login, not only the first
(§0.2). A person removed from `vorstand` in Keycloak loses the mapped
collection at their next login. This is weaker than platform roles
("effective on the next request") and must be said wherever the mapping
is shown: *mapped rights follow the provider at each login*. Rights
assigned directly in OAAP stay effective on the next request (§7).

### 5.3 Self-registration

Nothing changes at the door: RFC-0041's `eingang` stays the default,
and `first_login: role` with self-registration stays refused unless set
deliberately. Behind the door, a tenant MAY name a **default collection
for newly registered people** (A6) — "Interessent", "Zuschauer" — never
one that contains `may_grant`.

## 6. The twin: value lists, contexts, and the person behind a login

### 6.1 Value lists — semantic types, after the Concept Description (A8, own RFC)

The draft proposed a new twin type kind `value_set`. Jörg reopened it
(2026-09-29) with a direction that is better anchored in the standard
the twin already borrows its vocabulary from:

> *A customer class is, from the twin's point of view, a Concept
> Description, and that is where its properties are defined. If the
> possible values can be defined there, we should do it there and
> build a management of semantic types modelled on the Asset
> Administration Shell — which an app can instantiate through its
> manifest, or use from the twin. Only if the value list cannot be
> solved through the Concept Description, an object type of kind
> "configuration" — and then master data and configuration data must be
> separated in meaning, maintained by an app for configurations.*

**It can be solved there.** An AAS Concept Description carries an
embedded data specification after IEC 61360, and that specification
has a **value list**: pairs of a value and a `valueId`, the value id
itself a reference that may point to its own Concept Description (the
way ECLASS gives every value an IRDI). A `Property` in a submodel then
carries both the value and its `valueId`. So "Kundenklasse" is one
Concept Description with the list A, B, C, D, each value with a stable
id; the customer's attribute refers to it by semantic id, and the
authorization field refers to **the same** concept (`concept:` in §2).
One definition, two uses, and the role stores the `valueId`.

The configuration object type stays the fallback for lists that
outgrow a Concept Description — values that carry their own data (a
discount per class), validity, or tenant-specific entries in the
hundreds. Then "master data vs. configuration" becomes a property of
the object type, and the maintenance app is the "Konfiguration" app.

**Two findings from the code, read, not measured (2026-09-29):**

- `oaap.data.model` 0.1 §1 promises *"optional semantic ID"* as a field
  (RFC-0031 §3.7). The reference has **no** such field — `semantic`
  does not occur in the platform code at all. The promise is in the
  spec only.
- `enum` is an accepted `value_type` (`MODEL_VALUE_TYPES`), but there is
  **no place to state its values**, and nothing checks them. An `enum`
  today is `text` with a different name.

Both are the natural first content of the semantic-types RFC. That RFC
also owns what the draft had put here: values are ended, never deleted
(a role naming class D must not suddenly name nothing), and customizing
is excluded from duplicate detection and reference search.

### 6.2 Contexts are twin objects

`Mannschaft mB`, `Organisation Sponsor X GmbH`, `Bereich News` are twin
objects. An assignment stores their **twin id** — so renaming the team
changes nothing (RFC-0026), and a merge of two duplicates keeps every
assignment working, because every read resolves merged ids forever
(RFC-0031 D3). An assignment's context must be an object **of the same
tenant's twin**, checked at assignment time.

### 6.3 The partner management as the tenant's who-is-who

`partnerverwaltung` (today 0.1.2: Firma, Kontaktperson, `isContactOf`)
grows into what Jörg described: **persons with and without a login,
organizations, groups, and their relations**, all as twin objects. It
is the natural owner of `Person` and `Organisation`, and therefore of
most contexts: a sponsor is an `Organisation`, its people are `Person`
objects related to it.

Its data becomes usable for authorization in two steps:

1. **as contexts** (this RFC, step 2): "Carla is Sponsor in the context
   of X GmbH" — the object comes from the partner management, the grant
   is written explicitly;
2. **as a derivation source** (reserved, A1, step 5): "whoever is
   `isContactOf` an organisation of category Sponsor holds Sponsor in
   the context of that organisation" — a rule the `tenant_admin` writes
   once.

Step 2 carries a warning that belongs in the rule editor itself: **a
derivation rule turns whoever may write the relation into someone who
grants rights**, without either of them being called an administrator.
The editor must say, before saving, which app(s) may write that
relation type — the declaration sentence of `oaap.data.model` §2.7,
applied to rights.

A known obstacle for the build, not for this RFC: the keys `Customer`
and `Person` are permanently taken on `oaap-test` by a throwaway probe
(see partnerverwaltung's manifest comment); a clean `Person`/
`Organisation` needs either a key decision or the missing `unregister`.

### 6.4 The person behind a login

A `Person` object and an OAAP user are different things: most persons
in a CRM never log in, and a user need not be in the CRM. When one
**does** log in, the link *Person ↔ user id* is what lets a
derivation rule or a future twin check find "the person asking". That
link is an identity claim — whoever can set it can make any user "be"
the contact of any sponsor. Therefore (A5): the link is written **only
by the platform** — by a `tenant_admin`, or by redeeming an invitation
(§10) — as a platform-owned group on the `Person` object, never by an
app.

### 6.5 What this RFC must not block — checked against the AAS direction (2026-09-29)

Jörg asked explicitly that nothing here closes a door. The twin's line
since RFC-0031 is **standard outside, own model inside**: the AAS
repository API is a projection (`oaap.data.aas`, own RFC), rebuilt by
OAAP rather than borrowed from an implementation, so that the inside
can be fast where the AAS is slow — above all on relations, which the
twin keeps as first-class rows valid in time, not as elements buried
in submodels. Checked, point by point:

| What RFC-0045 stores or reads | Why it does not block the AAS direction |
| --- | --- |
| a context as a twin **object id** | the same platform id the projection exports as the shell id (`urn:oaap:obj:<uuid>`, RFC-0031 §3.2); a rename or merge changes nothing (§6.2) |
| a field value as a **value id**, never a label (§2) | exactly what the AAS `valueId` is; switching a field from `values:` to `concept:` changes the source of the ids, not the shape of a role |
| an authorization field's meaning | may carry the **same** semantic id as the twin attribute it guards — one concept, used by the data and by the right |
| relations (only in reserved step 5, A1) | read through the twin's own relation model, never through a projection — so the AAS view of relations can be built or changed without touching grants; a relation id as a context is not excluded, only not needed in v1 |
| authorization objects, roles, grants | deliberately **not** twin types: they are not data about an asset. The AAS has its own security part with attribute-based access rules; whether the projection should ever export grants in that form belongs to `oaap.data.aas` — not checked in detail here, and nothing stored here prevents it, since grants reference the same object ids and semantic ids such rules would name |

What *would* have blocked it, and was changed for that reason: the
draft's own `value_set` kind (a value list as twin objects, owned by
the twin) and a role storing the label "D" rather than an id.

## 7. Where it is checked — delivery to the app

**The data holder checks.** For its own functions and its own data the
app checks, and the platform hands it what it needs:

- `GET {OAAP_AUTHZ_URL}/effective?user=<user id>` — the person's
  effective grants **for this app's own objects only**, with contexts,
  values and validity already resolved (collections, mappings,
  delegation flattened). An app never sees another app's grants, and
  never learns *why* a person holds something — only *that* they do.
- Authenticated with the instance's own key, scoped to `oaap.authz`
  (RFC-0027 D5), minted at install exactly as `oaap.data.twin` §2.2
  does for `oaap.twin`. Whether one key may carry both scopes is to be
  measured at the build, not assumed.
- A small reference client (Python first, a Node one for hbsha if they
  want it): `may(user, "team.edit_lineup", team=<id>)`. It **fails
  closed** — unreachable service, unknown object, unparseable answer:
  no.
- **Not a header.** `X-OAAP-Roles` stays the platform-role list and
  nothing else. Grants with contexts can be long, and a header is proof
  by the gateway on every request for *every* app — this is data one
  app asks for about one person.
- **Freshness** (A4): an app may cache an answer for a stated, short
  time; a revocation is effective within that bound, and the bound is
  written on the admin page.

## 8. What is deliberately left open

### 8.1 No policy language

No OPA, no Rego, no Cedar. Objects, activities, fields, contexts — the
SAP shape — cover every case named here. A policy language is the
tool for a case nobody has brought yet.

### 8.2 No field-level visibility

Which *attributes* of a customer a person may see is not an
authorization field here. An app may declare an object for it
(`customer_bank_data · read`) and check it itself.

### 8.3 The twin checking per person — a direction, not a decision

Jörg, 2026-09-28: *leave it open, wait — but it will probably come, and
it will be a strong argument for the platform in business.* Recorded
here so that nothing built in steps 1–4 blocks it:

- Today an app reads the twin as **itself** (`instance:<name>`), with
  the rule "an instance reads the types it consumes, all groups".
- The direction: the app reads **on behalf of** a person, and the twin
  returns the **intersection** of what the instance may read and what
  the person may read — so the filter "customer class D only" sits in
  one place for every consuming app instead of in each of them (the
  lesson recorded as *Zwei Wege, eine Regel*: the app that forgets the
  filter is the one nobody tested).
- The unsolved part, named: the twin must be able to **verify** "on
  behalf of Bernd" rather than believe the app, or every app can claim
  to ask for the admin. That needs a person assertion the gateway signs
  and the app only forwards. This is the RFC this section reserves.

Why this RFC's shape already prepares it: grants reference twin types,
twin ids and value ids (§6) — a later twin-side check reads the same
data the app-side check reads today.

## 9. Security requirements

- A business grant **never** confers or implies a platform role, never
  opens a route, never crosses a tenant.
- Provider claims become **membership only**; the mapping to
  collections is local and tenant-written; an unmapped group grants
  nothing; platform roles are never mapped (RFC-0041, sharpened).
- Mapped membership is re-evaluated at **every** login (§5.2).
- Assignments bind to the **user id** (RFC-0040), never to a username or
  an e-mail address.
- Delegation is limited **structurally** (§4): listed templates, own
  contexts, own validity — not checked after the fact.
- `granted_by` is recorded by the service from the authenticated caller,
  never taken from the request.
- An app reads only its own objects' grants; the effective answer names
  no other app.
- The reference client fails closed.
- Every change — role, collection, assignment, mapping, delegation — is
  an entry in the tenant's log.
- A context must be an object of the same tenant's twin.
- A rehearsal (RFC-0030) reads the production tenant's grants for the
  same app **read-only** and can change none (it shares the app id, A3);
  a grant written from a rehearsal is refused.

## 10. Non-goals (deliberate)

- Replacing an app's own model. Opt-in, always.
- Cross-tenant roles or a person with grants in two tenants — two
  tenants are two principals (RFC-0041).
- Approval workflows beyond RFC-0041's Eingang.
- **Invitations as a platform function** — hbsha's comfort variant
  (e-mail, expiry, an opaque context returned after registration). It
  fits here naturally — an invitation is a *prepared assignment* that
  also sets the Person link of §6.4 — but it is its own step, after
  step 4, and only when a second app asks for it.
- A policy language (§8.1), field-level visibility (§8.2), twin-side
  enforcement (§8.3).

## 11. Staging

0. **Letter to hbsha**: the offer, not a request; their model is §3.2
   and §4, nearly word for word; nothing changes for them unless they
   want it.
1. **Declaration**: spec `oaap.core.authorization` 0.1, the manifest
   section in `oaap.apps.runtime`, registration and additive/destructive
   comparison at install, a read-only list per tenant ("what could be
   allowed here").
2. **Grants and delivery**: roles, collections, assignments with values
   and contexts, the `effective` endpoint, the reference client — CLI
   and internal API first. **First consumer: `partnerverwaltung`**
   (its own objects `organisation`/`person`, a category as a manifest
   `values:` list until semantic types exist), because it is ours and
   it is also the source of contexts.
3. **Delegation and the provider**: `may_grant`, the IdP mapping with
   re-evaluation at every login, the default collection for
   self-registered people.
4. **The admin app "Rollen & Rechte"** (A7): a separate OAAP app on the
   internal API — the exemplary consumer that shows the service is made
   for apps. It shows persons, users, the link between them, roles,
   collections, contexts, and who granted what.
5. *(reserved)* derivation rules from twin relations (A1).
6. *(reserved)* twin-side enforcement per person (§8.3).

### 11.1 What was built (2026-10-03)

`oaap.core.authorization` 0.1 (`oaap-spec/spec/oaap.core.authorization.md`),
**inside the identity service** (Jörg's decision of 2026-10-03: identity
holds the user id, the tenant, the keys and the login — stage 3 must run
there): manifest 0.6 with the `authorization` section, registration at
install with the additive/destructive comparison and `--confirm-authorization`,
roles, collections and assignments (`oaap authz …`, `/internal/authz/*`),
`GET /authz/effective` authenticated by identity itself with a key of scope
`oaap.authz`, the reference client `platform/authz_client.py` that fails
closed, and `partnerverwaltung` 0.1.3 as the first consumer. Measured on
`oaap-test` (CURRENT_STATE 257).

Differences from the draft, each a decision made while building and recorded
in the spec: the unrestricted field means "not named in the grant"; a grant
restricted to a context only matches when the caller **names** that context
(a question without the team has no safe answer — `may_any` says "some"
explicitly); `may_grant` and the context check against the twin are accepted
and stored, **not enforced**; the first consumer **declares and does not yet
check** — enforcing would take every user's right to edit away until roles
exist, and that is a decision for the next stage.

### 11.2 Stage 3 built (2026-10-03): the provider's groups

`oaap.core.authorization` 0.2 §2.9. Mapping by **path** (the token carries
no group id — measured), read at **every** login (first included), only what
a login made is ever changed, a removed mapping ends its assignments at once,
and nothing a group says can name a platform role. Two limits decided while
building and recorded in the spec: a collection that needs a **context** and a
collection with `may_grant` cannot be mapped. The connector now puts a
group-membership mapper on the client OAAP makes (and adds it to one it found,
if missing) — before that, no `groups` claim reached OAAP at all.

### 11.3 Stage 4 (A7): the admin app — specified 2026-10-03

`oaap.core.authorization` 0.3 §2.10. Found while designing the app: **no app
could administer**, the whole administration API opened only to the host's
internal key. A7 therefore starts with a door, not with a page: a second key
scope `oaap.authz.admin` for an instance whose manifest says
`authorization.administer: true`, minted only if the operator confirms at
install, bound to the tenant of the instance. Every call names the person
(`on_behalf_of`) and **identity verifies that person** as `tenant_admin` of the
key's tenant (or `server_admin`) — a mistake in the app's own page cannot open
anything. Decisions of Jörg (2026-10-03, all as recommended): D1 own key scope
with identity's check; D2 only the operator, with confirmation, `administer`
additive in manifest 0.6; D3 first version without the person-to-user link and
without delegation; D4 `retire` (nothing deletes) built with it; D5 a normal
catalog app, the portal only links. The spec says openly what the door is: a
privileged one.

## Decided (2026-09-28, before the draft)

1. **IdP groups may be mapped to business role collections, never to
   platform roles.** Jörg: "ja". Carried into §5.1 as the sharpened
   RFC-0041 rule.
2. **The `tenant_admin` maintains that mapping.** Jörg: "ja,
   tenant_admin darf das mapping pflegen". Reasoning in §5.1; the
   visibility-group mapping stays operator-only.
3. **The twin filtering per person stays open.** Jörg: "wir können das
   als Idee offen lassen und noch abwarten. Ich vermute aber, dass
   dieses Feature kommt und ein starkes Argument für die Plattform im
   Business sein wird." Carried into §8.3 as a reserved direction.

## Decided (2026-09-29, A1–A7 as recommended; A8 reopened)

Put to Jörg as eight questions; seven answered with the recommendation,
the eighth answered with a direction instead.

- **A1 — Context: written in the assignment.** Derivation rules from
  twin relations come later (step 5), written by the `tenant_admin` as
  an explicit rule that says which apps may write the relation it reads
  (§6.3). Reason: an explicit grant has a `granted_by`; a derived one
  has a relation writer who never knew they were granting.
- **A2 — Delegated assignments stay when the delegator's own
  assignment ends**, keep their `granted_by`, and are listed as
  "granted by someone who no longer holds it" for the `tenant_admin`.
  A cascade would take the Zeitnehmer out mid-season because the
  trainer changed; a silent survival would hide it.
- **A3 — A role belongs to `(tenant, app id)`**, not to an instance.
  Test, production and rehearsal of one app share grants; a version
  whose declaration differs is caught by the destructive-change check
  at install. Per instance would make every promotion (RFC-0020)
  re-grant everything.
- **A4 — Freshness: at most 30 seconds.** The reference client caches
  for at most 30 s; a revocation is effective within that bound; the
  bound is printed where assignments are edited. Platform roles keep
  "next request".
- **A5 — Only the platform links a `Person` to a user id** — a
  `tenant_admin`, or a redeemed invitation — as a platform-owned group
  on the `Person` object; no app writes it (§6.4).
- **A6 — A default collection for self-registered people is allowed**,
  set by the `tenant_admin`, empty by default, and refused if any of
  its templates carries `may_grant`.
- **A7 — The admin surface is a separate app "Rollen & Rechte"** on the
  internal API, plus a CLI; the portal only links to it. The app is
  privileged and gets a key scoped to the tenant's administration,
  nothing node-wide.
- **A8 — reopened, not decided.** The draft's question was "value sets
  as a twin type kind (`kind: value_set`)?". Jörg's answer (2026-09-29,
  in substance): *think again — I want compatibility with the digital
  twin and the specification behind it. A customer class is a Concept
  Description, and its properties are defined there; if the possible
  values can be defined there, do it there, and build a management of
  semantic types modelled on the AAS, which an app instantiates through
  its manifest or uses from the twin. Only if that fails, an object
  type of kind "configuration", with master data and configuration
  separated in meaning, maintained by a configuration app. Relations,
  too, are objects to be kept in step with the AAS concept — through
  our own rebuilt AAS API, which also lets us compensate the AAS's
  performance problems, e.g. on relation data. Check that nothing here
  blocks that.* Carried into §6.1 (the Concept Description can hold a
  value list — IEC 61360) and §6.5 (what was checked); the design of
  semantic types is **its own RFC**, amending `oaap.data.model`.

## Deutsche Zusammenfassung

**Worum es geht.** OAAP hat acht Plattformrollen. Sie entscheiden, wer
auf den Knoten, in den Mandanten und auf eine Route kommt. Sie sind eine
Sicherheitsgrenze, keine fachliche Sprache. Alles, was jemand *in* einer
App tut, war bisher Sache jeder einzelnen App. Beispiele sind der
Trainer, der die Aufstellung *seiner* Mannschaft pflegt, der Sponsor mit
*seinen* Werbemitteln und der Sachbearbeiter, der Kundenklasse A–C
liest, aber nur D ändert. Dieser RFC schlägt dafür eine **freiwillige**
Plattformfähigkeit vor: `oaap.core.authorization`.

**Drei Trennungen, wie in der BTP:**

1. **Die App erklärt**, was es zu erlauben gibt. Im Manifest stehen
   Berechtigungsobjekte mit Aktivitäten und Feldern sowie
   Rollenvorlagen. Die Definition kommt mit dem Paket, freigeschaltet
   wird je Mandant, genau wie bei den Zwillings-Typen.
2. **Der Mandant vergibt.** Der `tenant_admin` baut aus Vorlagen
   Rollen, bündelt sie zu Rollensammlungen über Apps hinweg und ordnet
   sie Personen, OAAP-Gruppen oder IdP-Gruppen zu.
3. **Wer die Daten hält, prüft.** Die App prüft ihre eigenen Funktionen
   und Daten, mit den wirksamen Rechten, die die Plattform ihr liefert.
   Für Zwillingsdaten wäre der Zwilling der natürliche Prüfer. Das
   bleibt nach deiner Entscheidung vorerst offen.

**Aus dem klassischen SAP** übernimmt der RFC das Berechtigungsobjekt
mit Aktivität und Feldwerten. „A, B, C lesen, aber nur D ändern" sind
zwei Berechtigungen auf ein Objekt, und das kann die BTP mit ihren
Rollen-Attributen nicht sauber ausdrücken. **Aus dem Verein** übernimmt
er die **Zuordnung im Kontext**: „Person X hat Rolle Y im Kontext Z,
erteilt von W". Es gibt *eine* Rolle „Trainer" und je Mannschaft eine
Zuordnung, statt einer Rolle je Mannschaft. So vermeidet OAAP die
Rollenexplosion, die SAP-Systeme mit abgeleiteten Rollen je
Organisationswert kennen. Der Kontext ist ein **Zwillingsobjekt**
(Mannschaft, Organisation, Bereich). Deshalb übersteht die Zuordnung
Umbenennen und Zusammenführen.

**Weggelassen aus SAP:** Profilgenerierung, Transaktionen als
Berechtigung, verschachtelte Sammelrollen, ein `SAP_ALL` und die
feldweise Pflege. Man arbeitet immer von einer Vorlage der App aus.

**Delegation nach hbshas eigener Regel, aber baulich statt nachträglich
geprüft.** Wer eine Vorlage mit `may_grant` hält, darf nur die dort
genannten Vorlagen vergeben, nur in den eigenen Kontexten und nur bis
zum Ende der eigenen Gültigkeit. Ein Trainer von mB kann also
Co-Trainer und Spieler für mB freischalten, für mC nicht.

**IdP-Gruppen (ändert RFC-0041, verschärft statt aufgeweicht):**
Behauptungen des Anbieters werden **nie** zu Plattformrollen. Eine
Gruppenmitgliedschaft darf aber über eine Abbildung, die der
`tenant_admin` selbst pflegt, auf eine **fachliche Rollensammlung**
zeigen. Der Anbieter sagt, wer jemand ist, OAAP sagt, was er darf.
**Ein Befund beim Schreiben** (aus dem Code gelesen, nicht gemessen):
Die heutige Abbildung auf Sichtbarkeitsgruppen greift nur bei der
**ersten** Anmeldung. Für fachliche Rechte muss sie bei **jeder**
Anmeldung neu gelesen werden. Sonst behält jemand, der in Keycloak aus
dem Vorstand entfernt wurde, seine Rechte.

**Zwilling und Partnerverwaltung.** Die Werteliste einer Kundenklasse
A–D gehört nach deiner Richtung (A8) in einen **semantischen Typ** nach
dem Vorbild der AAS Concept Description. Das geht standardkonform: Die
Concept Description trägt nach IEC 61360 eine **Werteliste** aus Paaren
von Wert und `valueId`. Das Kundenattribut und das Berechtigungsfeld
zeigen auf **dasselbe** Konzept, und eine Rolle speichert die
`valueId`, nie die Beschriftung. Die Ausgestaltung wird ein eigener RFC,
der `oaap.data.model` ändert. Bis dahin reichen feste `values:`-Listen
im Manifest. Zwei Befunde aus dem Code gehören dorthin: Die Spec
verspricht ein Feld für die semantische ID, das es im Code nicht gibt,
und `enum` kennt keinen Ort für seine Werte. §6.5 prüft Punkt für
Punkt, dass RFC-0045 der AAS-Richtung nichts verbaut („außen Standard,
innen eigenes Modell“, Beziehungen innen als eigene Zeilen).
Die `partnerverwaltung` wird zum Wer-ist-wer des
Mandanten: Personen mit und ohne Anmeldung, Organisationen, Gruppen,
Beziehungen. Ihre Objekte werden zuerst zu **Kontexten** von
Zuordnungen und später, als eigener Schritt, zur Quelle von
**Ableitungsregeln**. Dazu eine Warnung, die in den Editor gehört: Eine
Ableitungsregel macht jeden, der die Beziehung schreiben darf, zu
jemandem, der Rechte vergibt. Die Verknüpfung „Person im Zwilling ↔
angemeldeter Benutzer" setzt deshalb nur die Plattform, nie eine App.

**Ehrlich benannt: eine Position ändert sich.** Am 21.09. haben wir hbsha
geschrieben: „Euer Freigabemodell gehört zu euch." Das bleibt wahr,
denn **keine App muss umziehen**. Neu ist, dass die Plattform genau
dieses Modell als Angebot bereitstellt. Ein Brief an hbsha steht als
Schritt 0 im Bauplan.

**Bauplan.** 0 Brief an hbsha → 1 Erklärung im Manifest → 2 Rollen,
Zuordnungen, Auslieferung an die App, erster Abnehmer ist die
`partnerverwaltung` → 3 Delegation, IdP-Abbildung, Vorgabe-Sammlung für
Selbstregistrierte → 4 App „Rollen & Rechte" → 5 (vorgemerkt)
Ableitungsregeln → 6 (vorgemerkt) der Zwilling prüft je Person.

**Entschieden am 28.09.:** (1) IdP-Gruppen dürfen auf fachliche
Sammlungen zeigen, nie auf Plattformrollen. (2) Die Abbildung pflegt der
`tenant_admin`. (3) Die Prüfung am Zwilling je Person bleibt als Idee
offen.

**Entschieden am 29.09. (wie empfohlen):**

- **A1** Kontext in v1 ausdrücklich in der Zuordnung; Ableitung aus
  Beziehungen erst später.
- **A2** Delegierte Zuordnungen bleiben bestehen, wenn der Trainer geht,
  werden aber als „verwaist" gelistet.
- **A3** Rollen gehören der App im Mandanten, nicht der Instanz. Test,
  Produktion und Generalprobe teilen sie.
- **A4** Der Client darf höchstens 30 Sekunden zwischenspeichern; diese
  Grenze steht auf der Admin-Seite.
- **A5** Die Verknüpfung Person ↔ Benutzer setzt nur die Plattform.
- **A6** Eine Vorgabe-Sammlung für Selbstregistrierte ist erlaubt,
  standardmäßig leer und nie mit Delegationsrecht.
- **A7** Die Oberfläche wird eine eigene App „Rollen & Rechte" plus CLI.

**Wieder geöffnet:** **A8** Wertebereiche. Sie werden keine eigene
Typ-Art `value_set`, sondern semantische Typen nach der Concept
Description. Nur wo das nicht reicht, kommt ein Objekttyp der Art
„Konfiguration“ zum Einsatz, getrennt von Stammdaten. Das wird ein
eigener RFC.

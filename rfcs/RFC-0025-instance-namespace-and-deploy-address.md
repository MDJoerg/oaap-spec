# RFC-0025: The Instance Namespace — One Node, or One Tenant?

- **Status:** Draft (decisions open — see §7)
- **Date:** 2026-09-02
- **Authors:** Claude (analysis & proposal), Jörg (question and framing)
- **Depends on:** RFC-0005 (addressing), RFC-0009/RFC-0018 (instance
  names), RFC-0019 (artifact deployment and the deploy hook),
  RFC-0022 (tenant as boundary), RFC-0011 (node profiles)
- **Amends:** nothing yet. It puts on the table a decision that
  `oaap.core.tenant` 2.4 made in one sentence, in passing.
- **Driver:** Jörg, 2026-09-02: *"Wenn in zwei Mandanten zufällig die
  gleichen Namen ausgewählt werden, haben wir bei der Deploy-URL keine
  Eindeutigkeit mehr? Sollten wir hier den Tenant mitgeben?"*

## Summary

Today an instance name is unique **per node**. The deploy hook is
therefore unambiguous — `https://<node>/deploy/<name>` can only ever
mean one instance — and the question that prompted this RFC has a
reassuring answer.

The reassuring answer is not the whole answer. The platform now names
things at two different scopes: an instance's **public address** is
tenant-scoped (`<instance>.<label>.<node>`, `oaap.core.tenant` 2.4),
while its **identity** is node-scoped. That asymmetry is invisible with
two tenants and becomes a shared resource between strangers with twenty
— which is exactly the arrangement RFC-0022 D5 calls *"we operate, the
customer administers"*, and the one Jörg named as the real case:

> Für shared Instanzen beim Partner ist das auf jeden Fall relevant,
> weil man dort nicht immer weiß, was die `tenant_admin`s machen bzw.
> kaum Kommunikation hat, da man ja den Tenant-Aufbau bewusst delegiert.

This RFC states what is true today, what the shared namespace costs
under delegation, and offers three options. It **decides nothing**.

## 1. What is true today

**Instance names are unique per node.** `oaap.core.tenant` 2.4 says so
in one sentence and gives the reason: *"That is one fact the boundary
cannot hide: a name already taken elsewhere has to be refused, or the
refusal arrives later and less comprehensibly."* The rule is enforced
in four places — the portal's create form, the host worker's `create`
action, the store install path, and the creation permit.

**So the deploy address is unambiguous.** `/deploy/<name>` resolves to
exactly one instance, and the deploy token is bound to that instance
anyway: a delivery aimed at the wrong customer with a valid token is
not possible. Adding the tenant to the URL would add no uniqueness.

**The refusal is deliberately half-blind.** A `tenant_admin` who picks
a taken name is told *that* it is taken, never *whose* it is. The
collision is a fact the boundary cannot hide; the owner is not.

**What hangs off the bare name.** Everything below is keyed by the
instance name alone — which is why changing the scope would not be a
rename but a migration:

| Thing | Key today |
| --- | --- |
| registry entry | `instances[<name>]` |
| container names | `oaap-app-<name>`, `oaap-app-<name>-<service>` |
| per-app network (RFC-0016) | `oaap-inst-<name>` |
| gateway site file | `apps-caddy/<name>.caddy` |
| data directory | `apps/<name>/` — storage and `instance.env` |
| deploy token (RFC-0019) | `deploy-tokens.json[<name>]` |
| creation permit (RFC-0019) | by name |
| app-to-app links (RFC-0016) | by name |
| deploy hook | `/deploy/<name>` |
| deploy log | by name |

## 2. What the shared namespace costs

### 2.1 Customers compete for ordinary words

`crm`, `wiki`, `viewer`, `shop`. The first customer to arrive takes the
word; everyone after them prefixes. And the prefix then stutters in the
address the platform generates by itself:
`cls-viewer.cls.oaap.joomp.de`.

### 2.2 Under delegation, the operator is not in the loop

This is the argument that makes the rest matter. In the *"we operate,
the customer administers"* model the whole point is that the operator
**does not** watch what tenant administrators do — the tenant build-out
is delegated on purpose, and there is little or no conversation. In
that arrangement:

- a customer's install fails on a name whose reason they cannot see,
  and the person who could explain it is not in the conversation;
- the operator learns about the collision, if at all, from a support
  request;
- the namespace is a **shared mutable resource between parties who do
  not talk to each other** — precisely the situation the tenant
  boundary abolishes everywhere else.

### 2.3 It has already produced one leak (now closed)

Removing an instance keeps its storage and its `instance.env` unless
deletion is asked for explicitly — deliberately, because reinstalling
under the same name is how an operator repairs an app without losing
its data. Combined with a node-wide namespace, that gave:

> tenant A removes `viewer` → the name is free → tenant B creates
> `viewer` → the install mounts A's storage and reads A's secrets out
> of `instance.env`, because existing values win over manifest
> defaults.

Closed in reference 0.1.56 (`oaap.core.tenant` 0.2.2): retained data
records the tenant it was written for, an install into a different
tenant is refused, and `oaap app purge` deletes it as an operator act
recorded in the owning tenant's audit log.

**It is listed here as evidence, not as an open item.** One shared
namespace produced one leak of this shape; the question this RFC asks
is how many more of the same shape wait where node scope and tenant
scope meet.

## 3. Option A — keep node-wide names (status quo plus the guard)

Names stay unique per node. The leak of §2.3 stays closed by the guard
already shipped. Collisions are answered with "taken, not whose".

- **For:** nothing to build, no migration. The deploy address stays
  exactly as it was handed to customers — and this platform has already
  paid once for an address that moved (`hub.bdt.joomp.de`, RFC-0009).
- **Against:** §2.1 and §2.2 remain. Every future feature keyed by
  instance name inherits the same shape, and each one has to be checked
  for the §2.3 pattern by hand.
- **Honest cost:** an operating rule instead of a mechanism — *give
  every customer instance a tenant prefix* — enforced by nobody.

## 4. Option B — tenant-scoped names

An instance is `(tenant, name)`. Two customers may both hold `viewer`.
The deploy address becomes `/deploy/<tenant>/<name>`.

- **For:** the namespace matches the boundary. Customers stop competing
  for words. Cross-tenant collisions stop existing, so the half-blind
  refusal of §1 is no longer needed at all. Data directories become
  `apps/<tenant>/<name>/`, which closes §2.3 structurally instead of by
  a guard.
- **Against:** every row of the table in §1 becomes a composite key —
  registry, containers, networks, gateway files, directories, tokens,
  permits, links, the hook, the log. That is a migration on the
  **registry**, the heart of the node, and it must run on live
  installations that are serving customers.
- **And a trap this platform knows:** deploy hook addresses are already
  in the field, in scripts and in AI briefings. RFC-0009's lesson is
  that a delivered address is load-bearing. `/deploy/<name>` would have
  to keep working for the default tenant — probably forever.

## 5. Option C — scoped names, node-wide identity

Keep one node-wide **identifier** for everything in the table (opaque,
or derived as `<label>-<name>`), and let the tenant choose a **display
name** independently.

- **For:** no change to the registry's shape. The customer sees the
  word they want, because the address is already tenant-scoped anyway.
- **Against:** two names for one thing, everywhere. Log lines,
  container names and portal pages would disagree about what an
  instance is called, and every operator would have to learn to read
  both. This platform's own rule — *the manifest owns the words*
  (RFC-0014) — cuts against inventing a second vocabulary here.

## 6. Recommendation

**Option A now; Option B as a considered decision before a third
customer shares one node.** In order:

1. Nothing today is broken. The deploy address is unambiguous, and the
   one real hazard the shared namespace produced is closed.
2. Option B's cost is not code, it is a registry migration on live
   customer nodes. Paying that with two tenants and one instance
   between them buys nothing; paying it with twelve customers costs
   more.
3. The right trigger is not a number of tenants but the **delegated**
   model of §2.2 actually starting: the first node where somebody
   outside our own operation administers a tenant we do not watch.

What Option A owes in the meantime, and what this RFC asks to be
recorded as debt rather than as a decision:

- a **naming convention** for multi-customer nodes, written down and
  applied by us, because nothing enforces it;
- a rule for design reviews: **whenever something new is keyed by
  instance name, ask what happens when that name is later taken by
  another tenant.** §2.3 is the template of that mistake.

## 7. Decisions for Jörg

- **D1 — Do we accept node-wide instance names for now** (Option A),
  with the guard from 0.1.56 and the debt of §6?
- **D2 — What triggers Option B?** Proposed: the first node where a
  tenant is administered by someone outside our own operation. A number
  of tenants is the wrong trigger; delegation is the right one.
- **D3 — If Option B: does `/deploy/<name>` keep working** for the
  default tenant permanently (RFC-0009's lesson), or only for a named
  grace period, as a renamed tenant label does (RFC-0022 Q3)?
- **D4 — A naming convention today?** Even under Option A, deciding now
  that customer instances carry a tenant prefix would make an eventual
  migration to Option B nearly free — the names would already be unique
  per tenant. The price is the stutter of §2.1 in every generated
  address.

## Non-goals

- **Renaming instances.** Nothing here proposes that an existing
  instance changes its name; that is a separate problem with the same
  address-in-the-field trap.
- **Sharing one instance across tenants.** An instance belongs to
  exactly one tenant (RFC-0022 D1); nothing here softens that.

## Zusammenfassung auf Deutsch

**Die Frage:** Wenn zwei Mandanten denselben Instanznamen wählen — ist
die Deploy-URL dann noch eindeutig?

**Die Antwort:** Ja, denn sie *können* nicht. Instanznamen sind
knotenweit eindeutig, nicht mandantenweit; der zweite Mandant wird
abgelehnt — „der Name ist vergeben", und absichtlich nicht, wem er
gehört. `/deploy/<name>` trifft also immer genau eine Instanz, und das
Deploy-Token hängt ohnehin an einer einzigen Instanz. Den Mandanten in
die URL zu schreiben, brächte keine zusätzliche Eindeutigkeit.

**Warum die Frage trotzdem richtig war:** Die Plattform benennt Dinge
auf zwei verschiedenen Ebenen. Die **Adresse** einer Instanz trägt das
Mandanten-Kürzel (`<instanz>.<kürzel>.<knoten>`), ihre **Kennung**
nicht. Mit zwei Mandanten merkt das niemand. Mit zwanzig ist der
Namensraum eine geteilte Ressource zwischen Fremden — und genau das ist
das Modell „wir betreiben, der Kunde verwaltet": Dort sieht der
Betreiber absichtlich *nicht*, was die `tenant_admin`s tun. Ein Kunde
bekommt dann eine Ablehnung, deren Grund er nicht sehen kann, von
jemandem, mit dem er gar nicht spricht.

**Ein Leck hat der geteilte Namensraum schon erzeugt** (inzwischen
geschlossen, 0.1.56): Entfernt ein Mandant eine Instanz, bleiben Daten
und Geheimnisse absichtlich liegen — und der nächste Mandant, der den
frei gewordenen Namen nimmt, hätte sie geerbt. Das steht hier als
**Beleg**, nicht als offener Punkt: Ein geteilter Namensraum hat einen
Fehler dieser Form hervorgebracht, und die Frage ist, wie viele
derselben Form noch dort warten, wo Knoten-Ebene und Mandanten-Ebene
aufeinandertreffen.

**Vorschlag:** Vorerst so lassen (Option A). Der Umbau auf
mandantenweite Namen (Option B) ist keine Code-Arbeit, sondern eine
Migration am Register — dem Herzstück des Knotens — auf laufenden
Kundenanlagen. Das lohnt sich nicht bei zwei Mandanten und einer
Instanz dazwischen; bei zwölf Kunden wird es teurer. Der richtige
Auslöser ist **nicht** eine Anzahl von Mandanten, sondern der erste
Knoten, auf dem jemand außerhalb unseres Betriebs einen Mandanten
verwaltet.

**Zu entscheiden (§7):** ob wir es vorerst so lassen (D1), was den
Umbau auslöst (D2), ob `/deploy/<name>` danach dauerhaft weiterlebt
(D3) — und ob wir schon heute eine Namenskonvention mit
Mandanten-Präfix setzen (D4). D4 ist der billigste Hebel: Wären die
Namen von Anfang an je Mandant eindeutig, wäre der spätere Umbau fast
umsonst. Der Preis ist der Stotterer `cls-viewer.cls.oaap.joomp.de` in
jeder erzeugten Adresse.

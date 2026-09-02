# RFC-0025: The Instance Namespace — One Node, or One Tenant?

- **Status:** Accepted (2026-09-02) — Option B, with the key
  derivation of §8 that the draft did not yet ask about
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
under delegation, and offers three options. **Jörg decided Option B on
2026-09-02**, together with the key derivation the draft had not
thought to ask about; both are recorded in §7 and §8. What made the
decision easy was that Option B turned out to be affordable in a way
this draft got wrong — see §8.3.

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

## 7. Decisions (Jörg, 2026-09-02)

- **D1 — no.** Option A is not taken. The rebuild happens now, while
  exactly one customer tenant exists and it can be set up again from
  scratch — the cheapest moment there will ever be. Jörg: *"Ich setze
  den Tenant cls neu auf. Die fremde KI kennt zwar unsere Vorgehensweise,
  aber noch keine URL."*
- **D2 — moot.** The trigger question disappears with D1. The reasoning
  behind it survives as the reason D1 went this way: the delegated
  model is the case, and it is close.
- **D3 — `/deploy/<name>` keeps working, permanently and without a
  compatibility layer.** It falls out of the key rule of §8.1 rather
  than being maintained: for the default tenant the key *is* the name.
- **D4 — superseded.** A hand-applied naming convention was the
  fallback for Option A. The platform now composes the prefix itself,
  which is the same effect enforced by a mechanism instead of by
  discipline — and without the stutter, because the customer types and
  reads the bare name while only the key carries the prefix.
- **D5 (new) — the key derives from a frozen slug**, not from the
  current label and not from the UUID. See §8.1.

## 8. The decision (Jörg, 2026-09-02)

### 8.1 Option B, with one new field on the tenant

An instance is `(tenant, name)`. What everything node-scoped uses is a
**node key**, composed once and never recomputed:

    key = <slug>-<name>        for a tenant with a slug
    key = <name>               for the default tenant

The **slug** is a new field on the tenant record: minted when the
tenant is created (initially the label, with a numeric discriminator
if that slug is already taken), and **never changed afterwards** —
`tenant rename` does not touch it.

Jörg chose this over deriving the key from the current label, and over
deriving it from the tenant UUID. The reasoning:

- **From the label** would mean every rename is a real migration —
  containers rebuilt, networks recreated, data directories moved,
  gateway files rewritten. On a customer node that is downtime for
  that tenant's apps, charged for a cosmetic change. RFC-0022 Q3
  already promises that a rename is *"a renaming, not a migration"*;
  deriving keys from the label would have broken that promise the day
  it was tested.
- **From the UUID** is perfectly stable but unreadable. `docker ps`
  would stop answering "whose container is this", and it answers that
  question at exactly the moment when someone is under pressure.
- **A frozen slug** keeps both properties. The price is honest and
  small: after a rename, container names and paths still carry the old
  slug. That is cosmetic drift in identifiers, not in addresses, and
  it is written down here so nobody has to rediscover it.

### 8.2 The deploy address does not change shape

`/deploy/<key>`. For the default tenant the key **is** the name, so
every address already handed out keeps working unchanged, forever, with
no compatibility layer to maintain — D3 answers itself. A tenant's
instance gets `/deploy/cls-viewer`, and because the slug is frozen,
that address survives a rename too. The draft's fear in §4 — that the
hook would need `/deploy/<tenant>/<name>` and a permanent fallback —
was misplaced: the key already carries the tenant, and it carries it
in the stable form rather than the mutable one.

### 8.3 The migration renames nothing

This is what made the decision cheap, and the draft underestimated it.
Existing instances **keep the keys they have**. The migration adds two
fields and moves no data:

- every tenant gets a `slug` (the default tenant's is the empty
  string, exactly as its label is the absence of a label in a hostname);
- every instance gets a `name`, initialised to its current key.

Only instances created *after* the migration get a slug-prefixed key.
An instance that predates it keeps a bare key and a name equal to it,
which is correct and unambiguous — keys only have to be unique, not
uniform. No container is rebuilt, no directory moves, no address
changes, and a node with one tenant cannot tell that anything happened.

The consequence for §2.3 is worth naming: with slug-prefixed keys a
freed name **cannot** be taken by another tenant, because their key
would differ. The guard from 0.1.56 stays as a second line — it still
catches a tenant deleted and recreated under the same slug — but the
leak is now closed by construction, which is what Option B promised.

### 8.4 What must be checked at creation

Two refusals, not one:

- the composed **key** must be free on the node (as today), and
- the **name** must be free *within the tenant*.

The second is not implied by the first for instances that predate the
migration, and forgetting it would let one tenant hold two instances
both called `viewer`.

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

**Entschieden am 02.09. (Jörg): wir bauen jetzt um.** Nicht, weil es
dringend wäre, sondern weil es der billigste Moment ist, den es je
geben wird: Es gibt genau einen Kundenmandanten, er lässt sich neu
aufsetzen, und die fremde KI kennt noch keine URL.

**Wie der Umbau aussieht (§8):** Ein Instanzname gilt künftig **je
Mandant**. Alles Knotenweite — Containername, Netzwerk,
Datenverzeichnis, Registry-Schlüssel, Deploy-Adresse — benutzt einen
**Schlüssel**, der einmal zusammengesetzt und nie neu berechnet wird:
`<kurzname>-<name>`, und für den Standard-Mandanten schlicht `<name>`.

Der **Kurzname** ist ein neues Feld am Mandanten: beim Anlegen einmal
vergeben (zunächst das Kürzel) und danach **unveränderlich** — ein
`tenant rename` fasst ihn nicht an. Das ist Jörgs Entscheidung gegen
zwei Alternativen: Vom aktuellen Kürzel abzuleiten hätte jedes
Umbenennen zu einer echten Migration mit Ausfallzeit gemacht und das
Versprechen aus RFC-0022 Q3 gebrochen („Umbenennen, keine Migration");
von der UUID abzuleiten wäre stabil, aber `docker ps` beantwortet dann
nicht mehr, wem ein Container gehört — und diese Frage stellt man
ausgerechnet unter Druck. Der Preis des Kurznamens ist ehrlich und
klein: Nach einem Umbenennen zeigen Containernamen und Pfade noch den
alten Kurznamen. Kosmetik an Kennungen, nicht an Adressen.

**Zwei Dinge, die den Umbau billig machen und im Entwurf noch zu
pessimistisch standen:** Die **Deploy-Adresse ändert ihre Form nicht** —
für den Standard-Mandanten *ist* der Schlüssel der Name, jede
ausgelieferte URL gilt unverändert weiter, ganz ohne Übergangsschicht.
Und die **Migration benennt nichts um**: Bestehende Instanzen behalten
ihre Schlüssel, es kommen nur zwei Felder dazu. Kein Container wird neu
gebaut, kein Verzeichnis verschoben, keine Adresse ändert sich — ein
Knoten mit einem Mandanten merkt nichts davon.

**Was das Leck aus 0.1.56 angeht:** Mit mandantenpräfigierten
Schlüsseln *kann* ein frei gewordener Name gar nicht mehr von einem
anderen Mandanten genommen werden — die Schlüssel unterscheiden sich.
Die Sicherung von 0.1.56 bleibt als zweite Linie stehen (sie greift
noch, wenn ein Mandant gelöscht und unter demselben Kurznamen neu
angelegt wird), aber die Lücke ist jetzt durch die Bauart geschlossen.

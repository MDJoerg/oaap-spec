# RFC-0011: Node Profiles — What a Node Is For

- **Status:** Proposed (2026-08-08)
- **Date:** 2026-08-08
- **Authors:** Jörg (idea and direction), Claude (write-up)
- **Depends on:** RFC-0001 (capability model), RFC-0003 (topology),
  RFC-0008 (`server_admin`)
- **Resolves:** the open question in `oaap.apps.runtime` 2.6 — may test
  instances be created from the portal?

## Summary

Nodes are not interchangeable. One is a workbench, one carries a
customer's production data, one is a demo machine, one will be an
appliance in a workshop. Today the platform knows none of this, so
every rule has to be written for the most cautious case and applied
everywhere. This RFC gives a node **zero or more profiles** —
`server_admin`-maintained, part of the node's own state — and lets a
small, explicitly bounded set of behaviours depend on them.

## Motivation

Three unrelated frictions turn out to be the same missing concept.

1. **`oaap.apps.runtime` 2.6 forbids creating test instances from the
   portal**, reasoning that a test instance is a development act, not a
   usage act. The reasoning is sound but the rule is global — and on a
   machine that exists *for* development it is simply wrong. Jörg's
   objection (2026-08-08) is that the resulting CLI-only path is
   unusable for the target audience.
2. **Some apps only make sense on some nodes.** OAAP Studio manages
   development projects; installing it on a customer's production
   appliance is noise at best. Today the store offers everything
   everywhere.
3. **The fleet is already heterogeneous** — recorded by Jörg himself in
   the idea log on 2026-08-06 ("Knoten-Typen/-Profile steuern den
   Funktionsumfang", with five types drawn from the real fleet:
   central, worker, hoster, edge, IoT gateway). This RFC is that idea,
   narrowed to what we can decide today and generalised from mutually
   exclusive *types* to combinable *profiles*.

## Why "profile" and not "role"

`role` is taken, twice over, and reusing it would be a lasting mistake:
RFC-0002 roles (`admin`, `keyuser`, `user`, …) describe **people**, and
they are forwarded verbatim into every app as `X-OAAP-Roles`. An
app-facing AI reading "the node has role dev" would reasonably assume
it arrives in that header. `capability` is likewise taken (RFC-0001,
`oaap.core.*`). **Profile** is free, and it is the word the original
idea used.

## Proposal

A node carries a set of profiles, empty by default.

- **Maintained by `server_admin` only** (RFC-0008) — this describes the
  machine, not an app and not a person.
- **Combinable**, not exclusive: a demo node can be `dev` and
  `showcase` at once. The 2026-08-06 list of types becomes a list of
  profiles, and a node may hold several.
- **Visible**: the health page and `oaap status` state the profiles, so
  nobody has to guess why a node behaves differently from its
  neighbour.
- **Empty by default, including on upgrade.** A node that says nothing
  behaves exactly as today. Nothing about this RFC changes an existing
  installation until somebody decides it should.
- The setup wizard asks once, at first run, what the node is for — the
  natural moment, and it makes the concept visible from day one.

### First profile: `dev`

Effects, and this list is deliberately exhaustive:

1. **The portal may create test-channel instances** (resolves 2.6).
2. **The portal may install from a source that no store list carries
   yet** — the case a brand-new app repository is always in.
3. Nothing else.

Point 2 carries a real cost that must be stated rather than buried:
2.6's property is that a compromised portal can at worst install apps
the `server_admin` already chose to trust, because the portal names
only an app id and the host resolves it against configured store
sources. **On a `dev` node that property is given up**, in exchange for
being able to develop from the browser. That is a reasonable trade on a
workbench and a bad one on a machine holding customer data — which is
exactly why it is a per-node decision and not a global relaxation.

### Apps may state which profiles they expect

An app manifest may declare the profiles it is meant for (e.g. Studio:
`dev`). Effect:

- The store **filters and warns**. It does not refuse.
- Installing anyway is possible and takes one confirmation.

**A hint, not a gate**, for a reason worth writing down: the manifest is
written by the app's author, the machine belongs to the operator. An
app that could refuse to run on a node it dislikes would be dictating
to the person who owns the hardware. The platform tells the operator
what the author intended and then does as it is told.

This dovetails with the store work in progress: an app marked
`expert only` on a node without `dev` is precisely the pairing that
should produce a warning.

### What profiles must never become

- **Not a second authorization system.** Profiles gate *platform
  behaviour*, never a user's access to anything. Whether a person may
  do something stays a question of roles and groups (RFC-0002/0007/0008).
- **Not a security boundary against the portal.** On a `dev` node the
  portal is deliberately more powerful. Profiles describe intent; they
  do not contain a compromised component.
- **Not the topology.** RFC-0003's controller/worker says how nodes form
  *one* platform. A profile says what *this* platform is for. A worker
  can be `dev`; so can a controller.

## `headless` — deliberately not part of this RFC

Jörg's third suggestion was a profile that "opens the channel to nodes
that can be managed very extensively from a central server". That is
not another value in this enum; it is an **inbound control channel into
an otherwise autonomous platform**, and it deserves its own RFC for two
concrete reasons.

**It reverses a decision RFC-0006 made on purpose.** There we wrote that
only the *entrance* is shared: "users, apps, updates, backups stay
autonomous per platform — explicitly not controller/worker from
RFC-0003", and Jörg confirmed that Bernd's platform stays Bernd's and
can move away at any time. Remote administration is the opposite
direction. It may well be right — the service-partner scenario needs
it — but it needs the trust model written down first: who is the
central party, what exactly may it do, how does the owner see it, and
how does the owner revoke it without help.

**It may already exist, half-specified.** RFC-0003 defines a worker as
"fully managed by the controller", with `join` and `remote join`. None
of it is implemented. So before inventing `headless`, the question is
which of two different things is meant:

- a node that is **part of one platform** and has no identity of its
  own — that is RFC-0003's worker, and the work is to implement it; or
- a platform that **stays its own** (own users, own data, own portal)
  but grants a third party administrative access — that is new, and it
  is what the service scenario for Bernd actually needs.

Jörg's wording ("OAAP instances that are managed") points at the
second. Worth its own RFC; this one stays out of its way.

## Open questions

1. **Are `dev` and `test` two profiles or one?** The proposal above uses
   only `dev`. A separate `test` profile is only worth having if we can
   name a behaviour that differs between them — otherwise it is two
   words for one thing, and the second will be set inconsistently.
2. **Which profiles do we actually name now?** My suggestion: start with
   `dev` alone, and add others only when a concrete behaviour needs
   them. The 2026-08-06 list (central, worker, hoster, edge, IoT
   gateway) describes *topology and placement* more than behaviour;
   much of it may belong to RFC-0003 rather than here.
3. **Should the profile influence updates?** A `dev` node could take
   updates earlier than production nodes — a natural staging path, and
   the fleet already has the right shape for it (oaap-test as the
   proving ground). Attractive, but it is a second mechanism next to
   `oaap.core.updates`; worth deciding deliberately rather than
   drifting into it.
4. **Where does the profile live in a backup/restore?** Restoring a
   production backup onto a workbench should probably not silently
   bring `dev` along — or should it? (Compare the same question for
   instance addresses in RFC-0009.)

## Deutsche Zusammenfassung

**Die Idee ist Deine eigene vom 6.8.** („Knoten-Typen/-Profile steuern
den Funktionsumfang"), hier fortgeschrieben: statt sich ausschließender
Typen bekommt ein Knoten **mehrere kombinierbare Profile**, gepflegt
ausschließlich vom `server_admin`, standardmäßig leer — ein bestehender
Knoten verhält sich also unverändert, bis jemand etwas entscheidet.

**Warum nicht „Rolle":** Das Wort beschreibt in OAAP Menschen und wird
als `X-OAAP-Roles` an jede App durchgereicht; „Capability" ist durch
RFC-0001 belegt. „Profil" ist frei — und es ist das Wort, das Du am 6.8.
selbst verwendet hast.

**Erstes Profil `dev`.** Es bewirkt genau zwei Dinge: Das Portal darf
Test-Instanzen anlegen (damit ist die offene Frage aus 2.6 beantwortet),
und es darf aus einer Quelle installieren, die noch in keiner Store-Liste
steht — der Normalfall bei einem frisch angelegten App-Repo. Sonst
nichts.

Der Preis dabei, ausdrücklich benannt: Heute gilt, dass ein
kompromittiertes Portal schlimmstenfalls Apps installieren kann, denen
Du ohnehin vertraust. **Auf einem `dev`-Knoten gibst Du das auf.** Auf
einer Werkbank ist das ein guter Tausch, auf einer Maschine mit
Kundendaten ein schlechter — und genau deshalb ist es eine Entscheidung
je Knoten und keine globale Lockerung.

**Apps dürfen sagen, wofür sie gedacht sind** (Studio: `dev`). Der Store
**filtert und warnt**, verweigert aber nicht: Das Manifest schreibt der
App-Autor, die Maschine gehört dem Betreiber. Eine App, die sich weigern
könnte, auf einem Knoten zu laufen, würde dem Eigentümer der Hardware
Vorschriften machen. Passt zu Deinem Store-Reifegrad „expert only".

**`headless` habe ich bewusst herausgehalten.** Das ist kein dritter
Wert in derselben Liste, sondern ein **eingehender Steuerkanal in eine
fremde Plattform** — und damit die Umkehrung dessen, was RFC-0006
ausdrücklich entschieden hat („Bernds Plattform bleibt seine"). Es kann
richtig sein, Dein Service-Szenario braucht es sogar; aber es braucht
ein eigenes Vertrauensmodell: Wer ist die zentrale Stelle, was genau
darf sie, wie sieht der Eigentümer das, und wie entzieht er es ohne
fremde Hilfe. Dazu kommt: RFC-0003 beschreibt mit dem „Worker" bereits
einen Knoten, der vollständig zentral verwaltet wird — nur ist davon
nichts gebaut. Vor `headless` steht deshalb die Frage, welches von zwei
verschiedenen Dingen Du meinst: einen Knoten, der **Teil einer**
Plattform ist (das ist der Worker, dann ist es Umsetzungsarbeit), oder
eine Plattform, die **ihre eigene bleibt** und trotzdem fernverwaltet
wird (das ist neu — und das ist es, was das Service-Szenario mit Bernd
wirklich braucht). Deine Formulierung deutet auf das Zweite.

**Vier offene Fragen an Dich** stehen oben; die wichtigste ist die
erste: Sind `dev` und `test` zwei Profile oder eins? Ich würde mit
`dev` allein anfangen und ein zweites erst hinzunehmen, wenn wir ein
Verhalten benennen können, das sich wirklich unterscheidet — sonst
werden es zwei Wörter für dieselbe Sache, und das zweite wird uneinheitlich
gesetzt.

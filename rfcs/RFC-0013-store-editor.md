# RFC-0013: The Store Editor — Maintaining a List Without Knowing Git

- **Status:** Accepted (2026-08-09) — all five open questions decided,
  see "Decisions"
- **Date:** 2026-08-09
- **Authors:** Jörg (idea, direction, and the objection that shaped the
  write modes), Claude (write-up)
- **Depends on:** RFC-0012 (store sources and list format), RFC-0004
  (manifest), RFC-0008 (`server_admin`), RFC-0011 (node profiles)
- **Touches:** `oaap.apps.runtime` 2.8 (instance configuration — where
  an app's credentials live today)

## Summary

RFC-0012 made the store list a specified, versioned artefact. Nobody
can maintain one yet: today a list is a JSON file edited by hand and
pushed with git. This RFC proposes the **Store Editor** — an OAAP app,
in `oaap-apps`, that reads a list, checks it against the schema *and
against the manifests it points at*, lets a human edit the six fields
that are actually editorial, and writes it back to its repository.

Two things in it are load-bearing and neither is the form:

1. **The checker, not the form, is the point.** A store list is not a
   document; it is an instruction that installs software on other
   people's machines. The first increment therefore validates and
   regenerates — it does not write.
2. **How a list gets published is a property of the list, not of the
   person.** Three write modes, decided by *who reads the list*, and
   none of them requires the maintainer to know a git word.

## Motivation

### The failure that started this

Ollama has been listed as `app_class: service` in our community list
since 2026-08-09 (build step 5 of RFC-0012). Its manifest said nothing
of the sort. The list and the package therefore contradicted each
other, and the contradiction was invisible: it surfaced only because
somebody happened to build the launchpad rule and look.

No human reviewing that JSON would have caught it. A checker that
fetches the manifest a list entry points at and compares the generated
fields would have caught it the moment it was written. **That is the
Store Editor's actual job**; the editing form is the pleasant part on
top.

### The 80 % rule needs an owner

RFC-0012 §1.3 splits the fields: **generated** from the manifest and
the repository (`id`, `name`, `type`, `version`, `released`, `package`,
`roles`, `profiles`, `app_class`, `icon`, a first `description`) versus
**editorial**, roughly six inputs a human must think about (`summary`,
`categories`, `audience`, `maturity`, `status`, `screenshots`,
`links`). That split was written *for* an editor. Without one it is a
description of work nobody does.

### There will be lists we do not maintain

Jörg's BDT project is the first: its own repository, its own list, its
own maintainer, arriving on other nodes as `unverified`. The editor has
to work for somebody who is not us and who should not have to learn
git to keep an app list current.

## Proposal

### 1. It is an app, not part of the portal

`oaap-apps/apps/store-editor`, installed from the platform list like
any other app, subject to the same contract. Reasons, in order of
weight:

- **Dogfooding.** The Studio was made an app for this reason and it
  worked: it exercises the same install, deploy and update paths every
  other app gets, so their defects reach us before they reach anybody
  else.
- The portal is `server_admin` territory (RFC-0008). Maintaining a list
  is *editorial* work, and the person who writes an app description is
  not necessarily the person who administers a server.
- A list maintainer may have no OAAP node at all in the long run. An
  app can move; a portal page cannot.

### 2. Build order — the checker first

**Increment 1 — read, check, regenerate. Writes nothing.**

- Load a list from a configured source (or an uploaded file).
- Validate against `oaap-store.schema.json`; report unknown vocabulary
  values as warnings, not errors (RFC-0012 §8.1 — a node tolerates
  them, so the editor must not pretend they are fatal).
- For every entry, fetch the manifest its `package` points at and
  compare the **generated** fields. Report each difference as: what the
  list says, what the manifest says, and which one an editor probably
  wants. This is the Ollama check.
- Report entries whose package cannot be fetched at all — a list
  pointing at a dead repository is worse than an incomplete one.
- Useful on its own, on day one, for our two existing lists.

**Increment 2 — edit the editorial fields, produce a file.**

- One object page per entry, the six editorial fields, everything
  generated shown read-only unless explicitly unlocked (RFC-0012 §1.3:
  an unlocked override is *marked*, so the next regeneration does not
  silently undo an intentional edit).
- Result is a downloadable list. Still no credentials, still no git.

**Increment 3 — write it back to its repository.** The part that needs
the decisions below.

**Explicitly not in this RFC:** `sets`, `data_models`, `agents`
(RFC-0012 §8.3/§8.5), and the curation layer `annotations`. The editor
must not grow a second half-built feature per reserved name.

### 3. Three write modes, chosen by reach

Jörg's objection (2026-08-09): forcing a pull request on somebody who
maintains their own list, and would be lost with git, is exactly the
ceremony this project exists to remove. Correct — but "can they handle
git" is the wrong axis, because it makes a list's safety depend on the
skill of whoever happens to maintain it.

The right question is **whose machines read this list**, because a
store list installs software on them.

| Mode      | Writes                                | Who confirms                     | For                                            |
|-----------|---------------------------------------|----------------------------------|------------------------------------------------|
| `direct`  | straight to the default branch        | nobody                           | a list only its own author's nodes read        |
| `review`  | to the default branch, after approval | a second user of the same editor | a list a company's own fleet or customers read |
| `propose` | to a branch, opens a pull request     | whoever maintains the repository | a list strangers read                          |

**`review` is the mode worth building carefully.** It is the middle
ground and it is *not* a git mode: saving creates a proposal, a second
editor user with the right role sees the change **inside the editor** —
field by field, readable — and releases it. Only then is it pushed.
No branch, no pull request, no git vocabulary, but a real second
signature. This is the same shape as the confirmation an `unverified`
source already costs (RFC-0012 §3): the platform knows this pattern.

Two rules hold in **all three** modes.

- **The checker is the gate, not the human.** A change that does not
  pass increment 1's checks is not written, in any mode. A reviewer
  reading JSON will not notice that `app_class` contradicts a manifest;
  the checker will. Human approval answers "should we publish this",
  never "is this well-formed".
- **No git word appears in the user interface.** Save, submit, undo.
  Git is the storage engine, not the vocabulary. In `direct` mode this
  means every change is one commit with a readable message and the
  editor offers **undo** — which is a revert, and the user never needs
  to hear that word.

**Why `direct` is defensible at all,** given that it publishes
immediately: the write path is not the only defence. On any node that
is not the author's, that list is a configured source with a trust
class, and an `unverified` one costs a confirmation before it installs
anything (RFC-0012 §3). Publishing carelessly harms the publisher's own
fleet first. And `direct` is already an improvement on today's
practice — hand-edited JSON pushed with no checks at all.

The mode is stored **with the list configuration in the editor**, not
in the list file: it describes how *this installation* publishes, and
two people maintaining copies of the same list may legitimately differ.

`direct` mode carries two brakes, decided below: an explicit
confirmation when an entry's **package repository** changes, and a
**volume brake** above a per-list threshold — counting editorial and
structural changes only, never regeneration, and presented as a
summary of what will change rather than as a yes/no prompt. See
Decisions 5 for why the shape matters more than the existence.

### 4. What this RFC does not decide: branches as channels

Jörg raised `dev — beta — preview — main` as branches (2026-08-09).
Recommendation: **no**, and it is not a close call. Four branches of one
list are four copies that drift, and merging them is precisely the git
skill we are trying not to require. Maturity and variant already exist
*in the format* (`maturity`, `status`, `variants`, RFC-0012 §1.2/§8.3)
and the deploy channel already exists per instance. A branch is then
only the transport for `propose` mode, which is what a branch is for.

### 5. Credentials: deliberately deferred, with an interim answer

Increment 3 needs a credential that can push to a repository. What
exists today (`oaap.apps.runtime` 2.8) is per-instance configuration
with `secret: true`: write-only in the UI, never rendered back. Stored,
as of 2026-08-09, as plain text in the instance's env file with mode
0600 — and therefore included in every platform backup, which
`oaap backup create` states outright.

Four gaps that the Store Editor is the first real case to hit:

1. **Keys are declared in the manifest and therefore fixed.** The
   editor needs *one credential per list*, added at runtime. Today a
   second list would mean changing the app's manifest. **This is the
   blocker — not encryption.**
2. `secret: true` means "not shown", not "encrypted at rest". Defensible
   on a single-tenant node, but it is currently an implied promise
   rather than a specified one.
3. No rotation, no expiry, no record of last use.
4. No scoping: a credential is available to the whole app process, not
   to the one purpose it was issued for.

**Recommendation: do not build a credential store now, and do not block
the editor on one.** Increments 1 and 2 need no credentials at all. By
the time increment 3 lands, the requirement will be evidenced by one
real case instead of guessed at — the same way instance configuration
was only specified once a real production rollout demanded it
(`oaap.apps.runtime` 0.2.3). For the first editor instance: **one
declared `secret: true` key for one repository.** Small, honest, and it
tells us whether the general thing is needed.

Independently and now: **write down what `secret` means today.**
Amended into `oaap.apps.runtime` 2.8 with this RFC. An unstated promise
about credentials is the kind that bites later.

### 6. Where it runs

A `dev` node (RFC-0011) for the test instance, over the Studio path —
oaap-demo carries `dev` as of 2026-08-09. Production placement is a
later decision; nothing in the design assumes it runs next to the lists
it edits.

## Decisions (Jörg, 2026-08-09)

All five were decided along the recommendation except the last, where
Jörg went further. Recorded with the reasoning, because a decision
without its reason is re-litigated six months later.

1. **Specify three modes, build two.** `direct` and `review` first;
   `propose` is specified but deferred. It needs a pull request API per
   forge (GitHub, Forgejo behave differently) and — the deciding point —
   its audience can already use git, so they have a manual fallback that
   the other two audiences do not.
2. **`keyuser` releases in `review` mode, `user` proposes.** The app's
   own roles (RFC-0002), deliberately **not** `server_admin`: writing an
   app description is editorial work, and a server administrator is
   neither the bottleneck we want nor the right judge of a description
   text. "Anybody but the author" was rejected — in a small company that
   degenerates into "somebody clicked", and the second signature becomes
   decoration.
3. **One instance manages several lists.** We already have two
   (community, platform apps) and BDT makes three. This is also what
   makes §5's credential question real rather than hypothetical: one
   credential per list, added at runtime, is a requirement the current
   declared-key model cannot meet.
4. **An entry may be created before its manifest is fetchable**, with a
   standing warning that the checker repeats on every run. A list is
   often written before its repository is public; refusing would push
   people back to hand-editing, which is the practice this app exists
   to end. A separate "draft" state was rejected as a second concept
   the format does not have.
5. **Both brakes in `direct` mode** — the package-repository
   confirmation *and* a volume brake. Jörg went beyond the
   recommendation here; the recommendation had been the repository
   confirmation alone, on the grounds that a prompt which fires on every
   regeneration gets clicked away and then protects nothing.

   **That objection is answered by design, not by dropping the brake.**
   Two things make the volume brake meaningful:

   - **Regeneration does not count towards it.** The checker itself
     produced those values from the manifests, mechanically and
     verifiably (§2, increment 1). Only *editorial* and *structural*
     changes count. This removes the case that would have fired the
     prompt every time.
   - **The brake is a summary, not a dialogue box.** Above the
     threshold, publishing shows what will change — entry by entry,
     field by field — and is confirmed from that page. A summary is
     read; "Are you sure?" is clicked away. This is the same reason
     `review` mode shows a readable diff instead of sending people to a
     forge.

   The threshold is a per-list setting with a sensible default. The
   package-repository confirmation is **not** subject to it: one entry
   changing repository is enough, because that is the single shape an
   accident and a takeover have in common — the id stays, the package
   moves. It is the attack RFC-0012's trust classes address between
   lists, appearing here *inside* a list one already trusts.

   Both brakes apply to `direct` mode. In `review` mode a human is
   already reading the change, so the volume brake would be a second
   prompt in front of an approval; the repository confirmation stays,
   surfaced as part of what the reviewer sees.

## Deutsche Zusammenfassung

**Was das ist.** RFC-0012 hat die Store-Liste zu einem
spezifizierten Artefakt gemacht — pflegen kann sie bis heute niemand:
Sie ist eine JSON-Datei, die von Hand bearbeitet und mit Git
hochgeladen wird. Der **Store Editor** ist eine OAAP-App in
`oaap-apps`, die eine Liste liest, prüft, bearbeitbar macht und
zurückschreibt.

**Der Prüfer ist der Kern, nicht das Formular.** Eine Store-Liste ist
kein Dokument, sondern eine Anweisung, die auf fremden Rechnern
Software installiert. Der Beleg ist frisch: Ollama stand seit dem
09.08. als „Hintergrunddienst" in unserer Liste, sein Manifest sagte
davon nichts — der Widerspruch war unsichtbar und fiel nur zufällig
auf. Kein Mensch, der auf dieses JSON schaut, findet so etwas; ein
Prüfer, der das Manifest hinter jedem Eintrag holt und die erzeugten
Felder vergleicht, findet es sofort. Deshalb: **Bauschritt 1 prüft und
erzeugt, er schreibt nichts.** Bauschritt 2 ist das Formular für die
sechs redaktionellen Felder. Bauschritt 3 schreibt zurück.

**Drei Betriebsarten, und die Achse ist nicht das Können.** Jörgs
Einwand ist richtig: Wer seine eigene Liste pflegt und mit Pull
Requests überfordert wäre, darf nicht dazu gezwungen werden. Aber
„kann er Git" ist die falsche Frage — sonst hinge die Sicherheit einer
Liste am Kenntnisstand ihres Pflegers. Die richtige Frage lautet:
**Wessen Maschinen lesen diese Liste?**

- **Allein gepflegt** → direkt schreiben. Der Schaden trifft den Autor
  selbst; ein Vier-Augen-Prinzip mit sich allein ist Theater.
- **Vier Augen** → der interessante Mittelweg, und ausdrücklich *kein*
  Git-Verfahren: Speichern legt einen Vorschlag an, ein zweiter
  Benutzer sieht die Änderung **im Editor** — Feld für Feld, lesbar —
  und gibt sie frei. Erst dann wird geschrieben. Kein Zweig, kein Pull
  Request, aber eine echte zweite Unterschrift. Dieselbe Form wie die
  Bestätigung bei einer ungeprüften Quelle.
- **Vorschlag einreichen** → Zweig und Pull Request, für Listen, die
  Fremde lesen.

In allen drei Fällen gilt: **Der Prüfer ist der Wächter, nicht der
Mensch** — was nicht validiert, wird nicht geschrieben; ein Mensch
entscheidet „wollen wir das veröffentlichen", nie „ist das korrekt".
Und: **kein Git-Wort in der Oberfläche.** Speichern, einreichen,
rückgängig. „Rückgängig" ist technisch ein Revert — das Wort muss
niemand hören.

**Warum direktes Schreiben trotzdem vertretbar ist:** Der Schreibweg
ist nicht die einzige Verteidigung. Auf jedem fremden Knoten kommt
diese Liste als **ungeprüft** an und kostet dort eine Bestätigung.
Wer unvorsichtig veröffentlicht, schadet zuerst der eigenen Flotte.

**Zweige als Kanäle (`dev`/`beta`/`preview`/`main`): davon rate ich
ab.** Vier Zweige derselben Liste sind vier Kopien, die auseinander-
laufen, und sie zusammenzuführen verlangt genau das Git-Können, das wir
nicht voraussetzen wollen. Reifegrad und Variante stehen bereits *im
Format*, der Kanal steht an der Instanz. Ein Zweig ist nur das
Transportmittel für den Vorschlagsweg.

**Zugangsdaten: bewusst vertagt.** Bauschritt 3 braucht ein Token mit
Schreibrecht. Was es heute gibt, ist die Instanz-Konfiguration mit
`secret: true` — nie angezeigt, nie zurückgelesen, aber **im Klartext
auf der Platte** (Rechte 0600) und damit **in jedem Backup**; das sagt
`oaap backup create` auch deutlich. Die eigentliche Hürde ist nicht die
Verschlüsselung, sondern dass die Schlüssel **im Manifest festgelegt**
sind: Der Editor braucht ein Token *je Liste*, zur Laufzeit
hinzugefügt. Empfehlung: **jetzt keinen Zugangsdaten-Tresor bauen** und
den Editor nicht darauf warten lassen — Bauschritt 1 und 2 brauchen
gar keine. Bis Bauschritt 3 ansteht, ist der Bedarf durch einen echten
Fall belegt statt geraten; genauso ist die Instanz-Konfiguration
entstanden. Sofort erledigt wird nur eines: **aufschreiben, was
„geheim" heute bedeutet** — nachgetragen in `oaap.apps.runtime` 2.8.
Ein unausgesprochenes Versprechen über Zugangsdaten ist die Sorte, die
später weh tut.

**Alle fünf Fragen sind entschieden (Jörg, 09.08.2026).** Vier
entlang der Empfehlung: drei Betriebsarten festschreiben, aber erst
zwei bauen; im Vier-Augen-Modus gibt `keyuser` frei und `user` schlägt
vor (die eigenen Rollen der App, ausdrücklich **nicht**
`server_admin` — das ist redaktionelle Arbeit); eine Instanz verwaltet
mehrere Listen; und ein Eintrag darf entstehen, bevor sein Manifest
abrufbar ist, mit einer Warnung, die der Prüfer bei jedem Lauf
wiederholt.

**Bei der fünften ist Jörg weiter gegangen als meine Empfehlung.** Ich
hatte nur die Rückfrage beim Wechsel des Paket-Repositorys vorgeschlagen
und von einer Mengenbremse abgeraten, weil eine Nachfrage, die bei jeder
Neuerzeugung kommt, weggeklickt wird und dann nichts mehr schützt.
Entschieden ist: **beide Bremsen**. Mein Einwand wird dabei nicht
übergangen, sondern durch die Bauweise beantwortet — zwei Punkte machen
den Unterschied. Erstens zählt die **Neuerzeugung nicht mit**: Was der
Prüfer selbst aus den Manifesten gebildet hat, ist maschinell und
nachvollziehbar entstanden; gezählt werden nur redaktionelle und
strukturelle Änderungen. Damit entfällt genau der Fall, der die
Nachfrage jedes Mal ausgelöst hätte. Zweitens ist die Bremse **eine
Übersicht, kein Bestätigungsfenster**: Oberhalb der Schwelle zeigt das
Veröffentlichen, was sich ändert — Eintrag für Eintrag, Feld für Feld —
und wird von dieser Seite aus bestätigt. Eine Übersicht liest man;
„Sind Sie sicher?" klickt man weg.

Die Schwelle ist je Liste einstellbar. Die Repository-Rückfrage
unterliegt ihr **nicht**: Ein einziger Eintrag, der sein Repository
wechselt, genügt — das ist die Form, die ein Versehen und eine
Übernahme gemeinsam haben.

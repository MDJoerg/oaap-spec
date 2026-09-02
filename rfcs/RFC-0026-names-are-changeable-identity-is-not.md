# RFC-0026: Names Are Changeable, Identity Is Not

- **Status:** Draft (proposed; decisions in §8)
- **Date:** 2026-09-02
- **Authors:** Claude (analysis & proposal), Jörg (direction)
- **Depends on:** RFC-0009/RFC-0018 (instance names and aliases),
  RFC-0022 (tenant as boundary), RFC-0025 (the instance namespace)
- **Amends:** RFC-0025 §8.1 — the frozen slug loses the reason it was
  frozen for, and is withdrawn. See §6.
- **Driver:** Jörg, 2026-09-02, one day after RFC-0025 shipped:
  *"Es wäre schon interessant, sowohl den Tenant als auch die
  Instanznamen zu ändern und damit auch das Erscheinungsbild nach außen
  anpassen zu können. Für Stellen, an denen die Umbenennung schmerzhaft
  werden kann — z.B. die interne Ablagestruktur — könnten wir überlegen,
  ob wir dort UUID mit Aliasen nutzen. Ich halte es persönlich für
  interessant, wenn ein Tenant ein Verzeichnis definiert und die
  Instanzen eines Tenants unterhalb organisiert sind."*

## Summary

Two questions were asked. The second answers the first.

**Can we rename an instance, and a tenant, and have the outside world
follow?** Today: a tenant can be renamed and its addresses follow; an
instance cannot be renamed at all. Both are held back by the same
thing — a name is not just a name here, it is also the filing system.

**Should the painful places use UUIDs with readable aliases?** Yes, and
the painful place is exactly one: **where the data lives.** Everything
else a rename touches — a registry key, a container, a network, a
gateway file, a token entry — is cheap to rewrite or recreate. Moving
gigabytes is not, and it is the only thing on the list that can fail
half-way and leave a customer's data in two places.

So: **identity is a UUID, the filing system hangs off the UUID, and
every name a human reads is an alias that may change.** A rename then
costs a container restart, not a data migration — which is what makes
it offerable at all.

**And the tenant directory:** no, we do not have it today (§2). Every
instance sits flat in `apps/<key>/`, mixed in with the platform's own
JSON files. Organising instances *under* their tenant is worth doing on
its own merits, and it comes almost for free with the rest.

## 1. What a rename costs today, item by item

| What | Keyed by | Cost of a rename |
| --- | --- | --- |
| registry entry | instance key | rewrite one JSON key |
| gateway site file | instance key | regenerate — happens on every deploy anyway |
| deploy token, creation permit | instance key | rewrite one JSON key |
| app-to-app links | instance key | rewrite a list |
| container | instance key | recreate — happens on every deploy anyway |
| per-app network | instance key | recreate and reconnect the gateway |
| public address | tenant label + name | **the point of the exercise** |
| deploy hook path | instance key | **in the field** (RFC-0009's lesson) |
| **data directory** | instance key | **move the data** |

Nine rows, seven of them trivial or routine. The platform recreates
containers and regenerates gateway files on *every single deployment*;
doing it on a rename is not a new class of risk.

Two rows are different, and they are the whole RFC:

- **The data directory.** On `oaapx01` today that is 6.5 GB for
  `ollama` and 890 MB for `open-webui`. A move within one filesystem is
  a directory-entry change and effectively instant — but "within one
  filesystem" is an assumption about someone else's machine, and a
  half-finished move is the one failure here that loses data rather
  than availability.
- **The deploy hook path.** It is handed to CI systems and AI agents.
  This platform has already paid once for an address that moved
  (`hub.bdt.joomp.de`, 2026-08-23).

## 2. What we have today (Jörg's question answered)

Not the tenant tree. The layout is flat, and it mixes two kinds of
thing in one directory:

```text
/var/lib/oaap/apps/
    registry.json  tenants.json  store-sources.json  deploy-tokens.json  …
    ai-gateway/      bdt-app/      bdt-app-test/     bdt-hub/
    bdt-hub-test/    livekit/      ollama/           ollama-models/
    open-webui/
```

Platform files and customer data as siblings. Nothing tells you which
of those directories belongs to which tenant — that is why 0.1.56 had
to add a `.tenant` marker *file* inside each one. The marker exists to
compensate for a layout that does not say what it holds.

## 3. Proposal

### 3.1 An instance gets an identity

Every instance is given an **`id`** when it is created: short hex,
immutable, never displayed except where an identity is what is meant.
A tenant already has one.

### 3.2 The filing system hangs off identities

```text
/var/lib/oaap/
  apps/                                   platform files only
  tenants/
    <tenant-id>/
      instances/
        <instance-id>/
          instance.env
          storage/<volume>/
          artifacts/
    by-label/<label>  ->  ../<tenant-id>          readable alias
    <tenant-id>/by-name/<name> -> ../instances/<instance-id>
```

Three properties fall out, and each was asked for:

- **All of a tenant's data is one path.** That is what makes
  backup-per-tenant (RFC-0022 D7), export-then-destroy for deleting a
  tenant, and moving a tenant to another node (ADR-0006: *Wechselpfade
  sind Produktmerkmal*) into ordinary operations instead of projects.
- **A rename moves nothing.** Names live in symlinks; the data does not
  know its own name.
- **Data cannot cross a tenant boundary by accident.** The guard from
  0.1.56 — retained data marked with the tenant it belonged to — stops
  being a guard and becomes the shape of the tree. The `.tenant` marker
  is withdrawn with it.

**UUIDs with readable aliases**, exactly as Jörg proposed: the truth is
`tenants/<uuid>/instances/<uuid>/`, and
`tenants/by-label/cls/by-name/viewer/storage/data` is the same place,
spelled for a human at two in the morning. Containers mount the
resolved path, never the symlink.

### 3.3 Names become changeable, and the outside follows

Two new operations, both warned, both audited:

- **`oaap app rename <name> <new>`** and the same on the instance page.
  Effects: the registry name, the container and network (recreated),
  the gateway files, and the **address** — `viewer.cls.<node>` becomes
  `modelle.cls.<node>`.
- **`oaap tenant rename`** gains what it deliberately did not do
  before: identifiers follow the new label, because there is no longer
  a data move behind them.

**Both keep the old name working for a grace period.** RFC-0018 already
gives an instance a canonical name plus aliases, and RFC-0022 Q3
already keeps a former tenant label routing for a grace period. This is
that machinery applied to one more case, not a new mechanism.

### 3.4 The deploy hook gets a stable form and a readable one

- `POST /deploy/<instance-id>` — canonical, and it **never changes**.
  It is a machine-to-machine address; the token beside it is opaque
  too. An agent given this never has to be told about a rename.
- `POST /deploy/<readable key>` — keeps working, follows renames, and
  keeps the old spelling for a grace period.

Everything already handed out keeps working. For a single-tenant node
the readable form is exactly what it is today.

### 3.5 What a rename actually does, in order

1. Refuse if the new name is taken *in this tenant*, or if the new
   label is taken on the node (unchanged rules).
2. Print the consequences and require `--yes` — the same voice
   `tenant rename` and instance-address removal already use.
3. Rewrite the registry name; re-point the symlinks.
4. Recreate the containers and the network. **This is a restart**, and
   the dialog says so with the expected duration.
5. Regenerate the gateway files, keep the old name as an alias for the
   grace period, reload.
6. Write it to the tenant's audit log.

Nothing moves on disk at any point.

## 4. What this costs

- **A restart per affected app.** Seconds, and only when someone
  deliberately renames. Named in the dialog, not discovered afterwards.
- **A one-time migration that does move data** — from `apps/<key>/`
  into the tenant tree. It is a rename within one filesystem, so it is
  a directory-entry change, but it is the one irreversible step in this
  RFC and it warrants a backup first and a per-instance restart.
- **The registry key changes meaning.** It becomes the instance id.
  Everything a human types stays a name, and the CLI resolves it; on a
  node with several tenants a bare name may need `--tenant`, exactly as
  the user list already does.

## 5. What it buys

- Renaming a tenant **and** an instance, with the outside following —
  the thing that was asked for.
- A tenant's data as one subtree: backup, export, delete, move.
- The `.tenant` marker and the retained-data guard become unnecessary;
  a whole class of "the name was reused" bugs stops existing rather
  than being caught.
- A deploy address that survives every rename, permanently.

## 6. What this withdraws from RFC-0025

RFC-0025 §8.1 froze the tenant's short name so that renaming would stay
a renaming instead of becoming a migration. That was the right answer
to the question as it stood **one day ago**: the data directory hung
off the name, so a rename meant moving data, so the name had to be
unfreezable.

Once the data hangs off a UUID, the premise is gone. A frozen slug then
buys nothing and costs the drift it was honest about: identifiers still
carrying `cls` after the tenant became `abc`. **The slug is therefore
withdrawn**, and readable identifiers derive from the current label
again.

This is worth recording plainly rather than smoothing over: yesterday's
decision was correct given yesterday's constraint, and Jörg's question
removed the constraint. The cost of having shipped it first is one
field in one file and a migration that clears it.

## 7. Staging

1. **The tenant tree and instance identities** — `instance_dir()` is
   the single function every per-instance path already goes through, so
   the change is small; the migration is the careful part.
2. **`oaap app rename` and tenant rename following through**, with
   grace-period aliases for both the address and the deploy path.
3. **The portal**: rename on the instance page and on the tenant page,
   with the consequences named before the act.
4. **Withdraw the slug and the `.tenant` marker.**

## 8. Decisions asked for

- **D1 — the tenant tree**: instances filed under
  `tenants/<tenant-id>/instances/<instance-id>/`, with readable
  symlinks. Proposed: yes.
- **D2 — the registry key stays readable and becomes mutable.**
  Revised from the first draft of this section, which proposed keying
  the registry by the instance id. Reason for the revision: Jörg's
  suggestion was *targeted* — UUIDs **where renaming hurts** — and the
  only place it hurts is the data directory. Keying the whole registry
  by an id would also change every CLI argument, every log line, every
  message and the fleet document, and would leave an operator reading
  `oaap app list` a column of hex. That is a worse platform bought to
  fix a problem the directory change already fixes.

  So: the id exists, the **data hangs off it**, the canonical deploy
  path uses it — and everything a human reads stays a name. The
  registry key is rewritten on a rename, which is a JSON edit and a
  container recreate, not a data move.
- **D2b — readable identifiers follow the CURRENT tenant label**, and
  the frozen slug of RFC-0025 is withdrawn (§6). A tenant rename
  therefore re-keys that tenant's instances and restarts them. That is
  the trade this RFC makes deliberately: no drift between what a
  container is called and who it belongs to, paid for with a restart
  during an act that is rare, deliberate and warned.
- **D3 — a rename restarts the app.** Proposed: yes, said out loud in
  the dialog. The alternative is renaming containers in place, which
  Docker allows but networks do not, so it would only move the restart
  somewhere less visible.
- **D4 — the grace period for a former instance name.** Proposed: the
  same default as a former tenant label (30 days), for both the address
  and the deploy path.
- **D5 — when to migrate `oaapx01`.** Proposed: after a backup, with
  the nine apps restarted one at a time, at a moment Jörg picks.

## Non-goals

- **Renaming an app.** What an app *is* comes from its manifest
  (RFC-0014); this is about what an instance of it is *called* here.
- **Moving an instance between tenants.** Still refused, and the tenant
  tree makes it a deliberate, visible operation rather than an
  accident.
- **Moving a tenant to another node.** Made *possible* by the tree, not
  designed here.

## Zusammenfassung auf Deutsch

**Zwei Fragen, und die zweite beantwortet die erste.**

*Können wir Mandanten und Instanzen umbenennen und das Erscheinungsbild
nach außen mitziehen?* Heute: Ein Mandant lässt sich umbenennen, seine
Adressen folgen; eine **Instanz gar nicht**. Beides hängt am selben
Umstand — ein Name ist hier nicht nur ein Name, er ist auch die Ablage.

*Sollen wir an den schmerzhaften Stellen UUIDs mit Aliasen nehmen?*
**Ja — und die schmerzhafte Stelle ist genau eine: wo die Daten
liegen.** Alles andere, was eine Umbenennung anfasst, ist billig:
Ein Registry-Schlüssel, ein Container, ein Netzwerk, eine Gateway-Datei
werden bei **jedem** Deployment ohnehin neu geschrieben. Gigabytes zu
verschieben ist es nicht — und es ist das Einzige auf der Liste, das
halb fertig scheitern und Kundendaten an zwei Orten hinterlassen kann.

Also: **Die Identität ist eine UUID, die Ablage hängt an der UUID, und
jeder Name, den ein Mensch liest, ist ein Alias und darf sich ändern.**
Eine Umbenennung kostet dann einen Neustart der App statt einer
Datenmigration — und erst das macht sie überhaupt anbietbar.

**Zur Verzeichnisfrage: Nein, so haben wir es noch nicht.** Heute liegt
jede Instanz flach in `apps/<schlüssel>/` — zwischen den JSON-Dateien
der Plattform. Nichts an diesem Verzeichnis sagt, welchem Mandanten es
gehört; genau deshalb musste 0.1.56 eine Markierungsdatei
hineinschreiben. Die Markierung gleicht eine Ablage aus, die nicht
sagt, was sie enthält.

**Vorgeschlagen** ist Dein Bild: `tenants/<mandant>/instances/<instanz>/`,
beide UUIDs, dazu lesbare Symlinks —
`tenants/by-label/cls/by-name/viewer/storage/data` ist derselbe Ort,
für einen Menschen um zwei Uhr nachts buchstabiert. Drei Dinge fallen
dabei ab: **alle Daten eines Mandanten sind ein Pfad** (das macht
Sicherung je Mandant, Löschen mit Export und das Umziehen eines
Mandanten auf einen anderen Knoten zu normalen Vorgängen statt zu
Projekten); **eine Umbenennung verschiebt nichts**; und **Daten können
die Mandantengrenze gar nicht mehr versehentlich überqueren** — die
Sicherung von 0.1.56 wird zur Form des Verzeichnisbaums und die
Markierungsdatei überflüssig.

**Der Deploy-Hook bekommt zwei Formen:** eine stabile
(`/deploy/<instanz-id>`), die sich **nie** ändert — für KI und CI, die
niemand über eine Umbenennung informieren muss —, und die lesbare, die
weiterläuft und nach einer Umbenennung eine Schonfrist lang beide
Schreibweisen annimmt. Alles, was heute ausgeliefert ist, gilt weiter.

**Was ich gestern zurücknehme:** RFC-0025 hat den Kurznamen des
Mandanten eingefroren, damit ein Umbenennen keine Migration wird. Das
war die richtige Antwort auf die Frage, wie sie **gestern** stand — die
Ablage hing am Namen. Hängt sie an einer UUID, ist die Voraussetzung
weg, und der eingefrorene Kurzname kauft nichts mehr außer der Drift,
zu der er sich ehrlich bekannt hat. Er wird zurückgezogen. Das schreibe
ich lieber deutlich hin, als es zu glätten: Die gestrige Entscheidung
war unter der gestrigen Einschränkung richtig, und Deine Frage hat die
Einschränkung entfernt. Gekostet hat es ein Feld in einer Datei.

**Was es kostet:** ein Neustart je App bei einer Umbenennung (Sekunden,
und nur wenn jemand das ausdrücklich will — der Dialog sagt es vorher);
und **eine einmalige Umstellung, die wirklich Daten bewegt** —
`apps/<name>/` in den Mandantenbaum. Auf einem Dateisystem ist das ein
Eintrag im Verzeichnis und damit sofort, aber es ist der eine
unumkehrbare Schritt hier: Sicherung vorher, Instanzen einzeln neu
starten, und den Zeitpunkt bestimmst Du.

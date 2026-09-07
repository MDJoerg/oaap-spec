# RFC-0030: The Dress Rehearsal — New Code on a Copy of Production Data

- **Status:** Draft (2026-09-05) — six decisions open
- **Date:** 2026-09-05
- **Authors:** Jörg (question and direction), Claude (analysis & proposal)
- **Depends on:** RFC-0020 (promotion — the same-bytes promise this
  extends), RFC-0022 (tenant as boundary), RFC-0026 (instance identity
  and its data directory), RFC-0029 (backups — where the data comes
  from), RFC-0016 (app-to-app links)
- **Driver:** Jörg, 2026-09-05: *„Im SAP-Umfeld gibt es manchmal noch
  einen Instanztypen, wo kurz vor Übernahme in Produktion noch eine Art
  QAS-System aufgebaut wird: mit der neuen Programmlogik auf einer Kopie
  der Daten des aktuellen Produktivsystems. […] Ziel ist es, einen
  allerletzten Test zu machen, ob alles noch geht und vor allem nach
  Umstellung des Datenmodells hier auch noch mal eine Sicherheit
  reinzubekommen."*

## Summary

Today OAAP has two states for one app: a **test** instance with test
data, and a **production** instance with real data. Promotion (RFC-0020)
moves the tested bytes from one to the other and can prove they are the
same bytes. What it cannot prove is the thing that actually breaks a
release: **that the new code survives contact with the old data.**

A test instance says "the code works". It does not say "the migration
of four years of accumulated production records works, including the
three rows somebody typed by hand in 2023".

This RFC proposes the missing state: a **rehearsal instance**
(*Generalprobe*) — a temporary instance carrying **the code of the test
instance** and **a copy of the production instance's data**, built to be
looked at once and then thrown away.

| | Question | Recommendation |
| --- | --- | --- |
| **D1** | Where does the copied data come from — the last backup, or live production? | **From the last backup**, with copy-from-live as the fallback |
| **D2** | Is a rehearsal a third channel, or an ordinary instance with two more fields? | **Two more fields** — not a third channel |
| **D3** | What may a rehearsal reach? | **Nothing outward by default**: no external address, no public route, no app links, **and no secrets copied** |
| **D4** | What happens when it expires? | **Removed and its data deleted** — extendable any time, every extension recorded |
| **D5** | Who may create one? | `server_admin` **and** the `tenant_admin` of the instance's own tenant |
| **D6** | And shared data holding (Postgres, digital twin)? | **A rehearsal never shares a data source with production** — write the rule now |

## Motivation

### What it is actually for

The dangerous release is not the one with a bug in a button. It is the
one that changes the shape of stored data. A test instance has ten rows
that the developer made; production has forty thousand that reality
made. The migration runs green on the ten and dies on row 12 847 —
after it has already rewritten 12 846.

A rehearsal answers exactly one question, and it is the one nobody can
answer any other way:

> **Does this version come up on THIS data?**

Everything else — does the feature work, is the layout right, do the
roles hold — belongs in the test instance and is already covered.

### Why the answer is not "just restore the backup and try"

It is, in fact, nearly that — and that is the argument for building it
rather than deferring it. The platform can already make a complete
archive (RFC-0029) and reinstall an app from a retained package
(RFC-0019). A rehearsal is those two, aimed at a **new empty instance**
instead of an existing one. Almost all the parts are on the shelf.

What is missing is the frame that keeps it from being dangerous: the
thing being created is **a second copy of live customer data**, and if
it is created casually it becomes the weakest point on the node.

## The decisions

### D1 — Where does the data come from?

Two sources are possible.

- **(a) From the last backup archive.** The instance's own subtree is
  extracted out of the newest archive into the new instance's
  directory. **Recommended.**
- **(b) Copied from live production.** Production is stopped for the
  copy — the same rule the backup follows since RFC-0029 D3, because a
  copy taken from a running application is a copy of a half-written
  moment.

**Recommendation: (a), with (b) as the fallback when no archive is
recent enough.** Three reasons, and the third is the one that decides
it:

1. **No production downtime at all.** (b) costs the same outage as a
   backup — measured 14 s per 900 MB, 32 s for 8 GB. Small, but paid by
   the customers of a system that is working fine.
2. **The archive is already consistent.** It was written with the
   containers stopped; nothing has to be stopped a second time.
3. **Every rehearsal proves the backup.** „Eine ungeprüfte Sicherung ist
   keine" — and a restore drill that happens because somebody wanted
   something else is the only kind that happens regularly.

**This is deliberately not the restore that RFC-0029 D5 deferred.**
That one is hard because it means merging one tenant's data back **into
a running node** — deciding what happens to rows that changed since.
Here the target is a **new, empty instance**: nothing to merge, nothing
to overwrite, no conflict to resolve. The hard half is absent, which is
why this can be built without waiting for D5.

### D2 — A third channel, or two more fields?

- **(a) A third channel** `rehearsal` beside `test` and `production`.
- **(b) An ordinary instance** on the `production` channel, with two
  recorded facts: `rehearsal: {source, code_from, created, expires}`.
  **Recommended.**

**Recommendation: (b).** A channel governs how *deployments* are
treated — may the same version be redeployed, may a deploy token exist
(`oaap.apps.runtime` 2.3/2.5). A rehearsal wants exactly the production
answers to both: it should be **frozen** while it is being examined, and
nothing in a pipeline should be able to push into it. Making it a third
channel would add a third case to every channel check in the platform
to arrive back at production's answers.

What is genuinely new is not a channel but two facts: **where the data
came from** and **when this instance goes away**. Those are fields.

A consequence worth stating: a rehearsal is **not redeployable**. If the
package was wrong, delete it and build another — it takes as long as the
copy, and it is honest. A rehearsal you kept patching is no longer a
rehearsal of anything.

### D3 — What may a rehearsal reach?

This is the decision that makes the difference between a useful tool and
an incident.

**A copy of production data is production data.** But reading is not
what makes it dangerous. What makes it dangerous is **acting**: the
rehearsal sending the real dunning e-mails, posting to the real webhook,
writing into the shared database, charging the real card. In SAP terms
this is exactly why a QAS system gets its RFC destinations cut.

- **(a) Nothing outward by default. Recommended.**
  - no external hostname and no alias (RFC-0009/0018) — it is reachable
    through the portal and the node's own address, nowhere else;
  - no `public` route is served — every route requires a login, even one
    the app declares as public;
  - **app-to-app links are not carried over** (RFC-0016). A copy of A
    that still links to production B is not a copy, it is a second
    writer;
  - **no `secret: true` config value is copied.** The fields come up
    empty and the operator fills in what the rehearsal actually needs.
- **(b) Everything like the original**, the operator pays attention.
- **(c) Like (a), but each item can be released individually.**

**Recommendation: (a), and (c) as the explicit escape** — an operator
who needs the rehearsal to reach one real system says so per item, and
it is recorded.

**Why secrets are the line.** No manifest change is needed to find what
"acts on the world": a credential is what lets something act. It is not
a perfect rule — a plain `SMTP_HOST` is not secret and still points at a
real mail server — but it is the right default, it is fail-safe, and it
costs nothing. An app that cannot start without its secret **says so
loudly on the new instance**, which is the correct outcome; the wrong
outcome is a rehearsal that starts quietly and mails real customers.

The rehearsal is also **unmistakable in the UI**: its own badge, its
remaining lifetime next to its name, and a name it cannot shed.

### D4 — What happens at expiry?

- **(a) The instance is removed and its data is deleted.**
  **Recommended.**
- **(b) It is only stopped; the data stays for manual cleanup.**

**Recommendation: (a).** A copy of production data that expires into a
directory nobody looks at is the worst of both worlds: it is not being
used and it is still a full copy of everything a customer has. Deleting
it is the whole reason the expiry exists.

With three conditions:

- **Extendable at any time**, in the portal, by anyone who could have
  created it — with the remaining time visible, not buried.
- **Every extension is recorded** in the tenant's audit log. A rehearsal
  extended six times has stopped being temporary, and the log is what
  makes that visible rather than a matter of memory.
- **An expiry may exist only on a rehearsal.** This must never become a
  general "delete this instance on a date" — an automatic deletion that
  can reach an ordinary instance is a foot-gun with a timer.

Suggested default: **7 days**, extendable in steps of 7. Several
rehearsals may exist at once, which is normal — two migrations, two
rehearsals.

### D5 — Who may create one?

**Recommendation: `server_admin`, and the `tenant_admin` of the tenant
the production instance belongs to.** It is their data and their
release; requiring the operator for it would make the operator the
bottleneck of every customer's go-live.

Two guards come with it:

- **The node checks free space before it copies** and refuses loudly,
  the way `oaap backup create` does. A rehearsal doubles an instance's
  disk use for its lifetime, and discovering that at 90 % full is
  discovering it too late.
- **Creation and deletion are recorded in the tenant's audit log**,
  including who and from which source archive.

### D6 — And shared data holding?

Jörg, in the same message: *„Demnächst werden wir Anwendungen mit dem
Schwerpunkt auf geteilte Datenhaltung […] auf der Grundlage einer
Postgres-Datenbank oder […] digitaler Zwilling. Wir sollten das im Blick
haben, wenn wir jetzt solche Konzepte spezifizieren."*

He is right, and this is the cheapest decision in the RFC — one sentence
now, a rewrite later:

> **A rehearsal never shares a data source with production. What cannot
> be copied cannot be part of a rehearsal.**

Today an instance's data is its own directory, so "copy the data" is a
directory copy. The moment data lives in a shared Postgres or a digital
twin that other instances also write to, that stops being true — and a
rehearsal pointed at the *shared* database is not a copy at all. It is a
second writer on live customer data, running unreleased code, written
specifically to change the shape of that data. That is the worst thing
this design could accidentally produce.

The rule turns the requirement around, which is the point:

- **Every future capability that offers shared data holding must be able
  to answer: "how do I make an isolated copy of myself?"** A Postgres
  capability answers it with a database copy under a different name; a
  digital twin answers it with a snapshot, or it answers that it cannot.
- **A capability that cannot answer is not rehearsal-capable**, and an
  instance using it **refuses to be copied** — loudly, at creation, with
  the reason named. It never half-copies and points the rest at
  production.

**We already have a small version of this problem**, which is why the
rule is not theoretical: app-to-app links (RFC-0016). That is why D3
does not carry them over.

- **(a) Write the rule now. Recommended.**
- **(b) Decide when the first shared-data capability exists.**

## Non-goals

- **It is not a performance test.** The rehearsal runs on the same node,
  competing for the same CPU and the same disk as production. A
  rehearsal that feels slow proves nothing about the release.
- **It does not prove a migration is reversible.** It proves the
  migration completes on this data. Going back is still the backup.
- **It is not a second production.** It has no external address, no
  uptime expectation, and it disappears.
- **It is not for the test channel.** A rehearsal of test data is a test
  instance, and there already is one.

## Open questions (not decisions)

- Does the rehearsal keep the production instance's `OAAP_APP_SECRET`,
  or get its own? Getting its own is the platform's current behaviour
  and the safer default — but an app that encrypted stored data with it
  would then find its own data unreadable, which is arguably the
  rehearsal doing its job (it found a real restore problem).
- Should the portal offer "promote" **from** a rehearsal? Recommendation
  is no: the tested bytes come from the test instance, and RFC-0020
  already ships exactly those. A rehearsal is a verdict, not a source.

## Deutsche Zusammenfassung

**Die Generalprobe** — eine Instanz mit dem **Code der Testinstanz** und
einer **Kopie der Produktivdaten**, gebaut, um einmal hinzusehen, und
danach weg. Sie beantwortet die eine Frage, die keine Testinstanz
beantworten kann: *Kommt diese Version auf DIESEN Daten hoch?* Zehn
selbst angelegte Zeilen sagen nichts über vierzigtausend gewachsene.

Sechs Entscheidungen, mit Empfehlung:

- **D1 — Die Daten kommen aus der letzten Sicherung**, nicht aus der
  laufenden Produktion. Kein Ausfall, konsistent, und jede Generalprobe
  beweist nebenbei die Sicherung. Das ist ausdrücklich **nicht** das in
  RFC-0029 D5 vertagte Problem: Dort geht es ums Zurückspielen **in
  einen laufenden Knoten** (zusammenführen, überschreiben); hier ist das
  Ziel eine **neue, leere** Instanz — die schwierige Hälfte fehlt.
- **D2 — Kein dritter Kanal**, sondern zwei zusätzliche Angaben an einer
  gewöhnlichen Instanz: woher die Daten kamen und wann sie verschwindet.
  Ein Kanal regelt *Deployments*, und dort will eine Generalprobe genau
  die Produktiv-Antworten: eingefroren, kein Deploy-Token.
- **D3 — Nach außen nichts.** Keine externe Adresse, keine öffentliche
  Route, **keine App-Verknüpfungen**, und **keine Geheimnisse werden
  mitkopiert**. Gefährlich ist nicht das Lesen, gefährlich ist das
  **Handeln**: die echte Mahnung verschicken, den echten Webhook rufen.
  Eine App, die ohne ihr Geheimnis nicht startet, sagt das laut — das
  ist das richtige Ergebnis.
- **D4 — Beim Ablauf wird sie entfernt und ihre Daten gelöscht.**
  Verlängerbar jederzeit, jede Verlängerung im Mandantenprotokoll (eine
  sechsmal verlängerte Generalprobe ist keine mehr). Vorschlag: 7 Tage.
  Ein Ablaufdatum darf es **nur** an einer Generalprobe geben — eine
  automatische Löschung, die eine gewöhnliche Instanz erreichen kann,
  ist eine Falle mit Zeitschaltuhr.
- **D5 — `server_admin` und der `tenant_admin` des eigenen Mandanten.**
  Es sind seine Daten und sein Go-Live. Dazu: Platzprüfung vorher, laut
  abgelehnt statt nachts als volle Platte entdeckt.
- **D6 — Und die geteilte Datenhaltung.** Der billigste Satz im ganzen
  Papier, jetzt geschrieben statt später umgebaut:

  > **Eine Generalprobe teilt niemals eine Datenquelle mit der
  > Produktion. Was sich nicht kopieren lässt, kann nicht Teil einer
  > Generalprobe sein.**

  Jede künftige Fähigkeit mit geteilten Daten (Postgres, digitaler
  Zwilling) muss beantworten: *Wie mache ich eine isolierte Kopie von
  mir?* Wer das nicht kann, ist nicht generalprobenfähig — und eine
  Instanz, die ihn nutzt, **verweigert die Kopie mit Begründung**, statt
  halb zu kopieren und den Rest auf die Produktion zeigen zu lassen.
  Eine kleine Ausgabe dieses Problems haben wir schon: die
  App-Verknüpfungen aus RFC-0016.

**Was es nicht ist:** kein Lasttest (dieselbe Maschine), kein Beweis,
dass eine Migration rückwärts geht (dafür bleibt die Sicherung), kein
zweites Produktivsystem.

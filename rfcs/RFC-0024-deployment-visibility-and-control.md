# RFC-0024: A Deployment You Can See — Status, Retry, Cancel, Delete

- **Status:** Draft
- **Date:** 2026-08-29
- **Authors:** Jörg (direction and decisions), Claude (write-up)
- **Depends on:** RFC-0019 (artifact deployment), RFC-0020 (promotion to
  production)
- **Amends:** nothing normative. It closes gaps RFC-0019 left open: the
  deployment handshake it defines has no way to say *"still working"*, and
  the portal has no vocabulary for a deployment that is in flight.
- **Driver:** `bdt-hub-test` on `oaapx01`, 2026-08-29. A deployment that
  had succeeded in five seconds looked, to its operator, like one that had
  hung — and there was nothing in the portal to do about it either way.

## Summary

A deployment becomes a **thing with an identity, a state, and a handle**.

1. Every deploy request carries an **id**, and the status endpoint answers
   about *that* request instead of about the instance's last known outcome.
2. A deployment in flight is **visible in the portal**, on the instance and
   on the health page, with the time it has been running.
3. The **running package can be rolled out again** — today only *other*
   packages have a button.
4. A deployment that has not started yet can be **cancelled**; one that has
   started gets a **time limit** instead of running forever in silence.
5. A retained package can be **deleted**, except the one in service.
6. The word **"läuft"** stops meaning two things at once.

Nothing here changes what may be deployed, by whom, or under which checks.
The envelope rule of RFC-0019 and the promotion rule of RFC-0020 stand
untouched. This RFC is about *knowing* and *intervening*, not about
permission.

## Motivation

### The incident

On 2026-08-29 at 19:48 UTC, `bdt-hub-test` was deployed from an uploaded
artifact. The node's record is unambiguous:

```
19:48:31  announced 0.20.6                                  ok
19:48:33  oaap-deployd.service starting
19:48:38  deployed 0.20.6 from uploaded artifact  cea32464   ok
19:48:38  oaap-deployd.service finished, status 0
```

Five seconds, container up, `/healthz` 200 inside and out. And yet the
operator's reading of the same system was: *"a deployment is stuck:
`0.20.6-cea32464ab97.zip`, and from the portal I cannot do much about it."*

Both readings came from the same screen. That is the defect.

### Why a finished deployment reads as a stuck one

On the instance page, the table *Hochgeladene Pakete* marks the package in
service with the badge **"läuft"** — and that row is the only one **without
a button**, because "Hierauf zurück" is offered for the *other* packages.

In German, *läuft* means both *is in service* and *is still going*. So the
row says "this one is still busy" and offers nothing to do about it. The
platform was reporting success in a word that also means "wait".

This is not a translation slip to be fixed in passing. It is the visible
end of a real gap: **the platform has no way at all to say that a
deployment is in flight**, so it never occurred to anyone that the word
would have to distinguish the two.

### The status endpoint answers the wrong question

`POST /deploy/<name>` and `PUT /deploy/<name>/artifact` wait up to 120
seconds. A build that takes longer — entirely normal — returns `202` with
*"deployment is still running — poll GET /deploy/<name>/status"*.

That endpoint returns **the most recent deploy-log entry for the
instance**. While the new deployment is still building, that entry is the
*previous* one:

```json
{"instance": "bdt-hub-test", "ok": true, "version": "0.20.5", "...": "..."}
```

A pipeline that polls after a 202 reads `ok: true` and concludes that its
deployment succeeded. It did not; it is still running, and it may still
fail. **The platform answers a question about a deployment with facts
about a different deployment.** Of everything in this RFC, this is the one
that is actively wrong rather than merely missing, because it is wrong
silently and in the reassuring direction.

The cause is structural: a deploy request has an id in the spool
(`{rid}.json`), but that id is thrown away when the outcome is written.
Result and log record cannot be tied back to the request that produced
them.

### There is no brake

The worker (`oaap-deployd.service`) has no time limit. A build that hangs
— a network fetch without a timeout, a stalled registry — blocks the whole
queue with no sign of it anywhere in the portal. Every later deployment for
every instance waits behind it, and the only way to find out is
`systemctl` on the machine. The platform's own promise is that the
operator works from the portal.

### There is no retry, and no way to tidy up

A deployment that half-succeeded — image built, container not started, or
started and unhealthy — leaves the operator with a package that is present
and correct and no button that says *try that again*. Rolling back to the
predecessor and forward again is a workaround that changes what runs twice
in order to change nothing.

Likewise, retained packages are only ever removed by automatic pruning to
four. A package uploaded by mistake, or one carrying something that should
not sit on the disk any longer, stays until three more push it out.

## Decisions (Jörg, 2026-08-29)

1. **A deployment gets an id, and the status endpoint answers about that
   id.** A caller must be able to learn the outcome of *its own* request.
2. **A deployment in flight is visible in the portal**, with how long it
   has been running. State that exists only in `systemd` does not exist for
   the operator.
3. **The running package may be rolled out again** from the portal.
4. **Cancelling is offered only where it is honest**: a request the worker
   has not started may be withdrawn. A build already under way is *not*
   killed — a half-built state is worse than waiting. It is bounded by a
   time limit instead.
5. **A retained package may be deleted, except the one in service.**
   Backup, rollback and promotion all depend on the package in service
   being there.
6. **The vocabulary is fixed**: "in Betrieb" for the running version,
   "läuft" reserved for something actually in progress.

## Design

### 1. A deployment has an id

The spool already mints one (`rid`). It is now carried through:

- the `202` and `200` bodies of the two calls that can go asynchronous —
  `POST /deploy/<name>` and `PUT /deploy/<name>/artifact` — as
  `"deployment": "<id>"`;
- the result file the worker writes;
- the line the worker appends to `deploy-log.jsonl`, as `"id"`.

`POST /deploy/<name>/announce` deliberately hands out none: it *must*
answer synchronously, because its answer is the upload grant. A client
that does not get one retries the announcement, which is safe — a new
announcement supersedes the pending one. An id there would only invite
polling for the wrong thing.

The log is the durable record. Result files are pruned after an hour; the
log is not, so a client that comes back the next morning still finds the
outcome of the id it holds.

### 2. `GET /deploy/<name>/status` answers about a request

```
GET /deploy/<name>/status?deployment=<id>
```

answers with an explicit **state**, never with a bare outcome:

| state | meaning | body carries |
|---|---|---|
| `queued` | in the spool, worker has not picked it up | `since` |
| `running` | the worker is on it | `since` |
| `done` | finished — succeeded or failed | `ok`, `version`, `revision`, `message`, `url` |
| `unknown` | no such id on this node | — |

Without `deployment=`, the endpoint keeps answering about the instance —
but **it too now carries `state`**, and it MUST report an in-flight
deployment as `running`/`queued` rather than returning the previous
outcome. That is the part that fixes existing clients without their having
to change.

`state` is derived from what is on disk, in this order: a matching queue
entry (`queued`), a claim marker written by the worker when it picks a
request up (`running`), a result file or a log line with that id (`done`).

### 3. The portal shows a deployment in flight

Both the instance page and the health page gain one line, present only
while something is in flight:

> ⏳ Deployment läuft — seit 4 Minuten (angestoßen über den Deploy-Hook)

and, for a request still waiting:

> ⏳ Deployment wartet in der Warteschlange — seit 30 Sekunden

The line is read from the spool, the same source the state machine uses.
No new store, and therefore nothing that can disagree with the truth.

### 4. Roll out the running package again

The *Hochgeladene Pakete* table gains an action on **every** row:

- the package in service: **"Erneut ausrollen"**
- any other retained package: **"Hierauf zurück"** (unchanged)

Both go through the existing `rollback` action in the worker — installing
the running package again *is* a rollback to itself, and reusing the path
means reusing its checks. The audit line distinguishes them, because a
retry and a rollback are different intentions and the log has to preserve
the difference.

### 5. Cancel, and a time limit

**Cancel** removes a queue entry that has not been claimed. The portal
offers it only while the state is `queued`; the host re-checks, and a
request already claimed is refused in words:

> Das Deployment ist bereits angelaufen und wird nicht abgebrochen — ein
> halb gebauter Stand ist schlimmer als warten. Es endet spätestens nach
> 20 Minuten.

**The time limit** is the answer for everything past that point. The worker
bounds a single request at `DEPLOY_MAX_SECONDS` (default 1200). On expiry
it records a normal failed outcome —

```json
{"instance": "...", "ok": false, "id": "...",
 "message": "aborted after the 20 minute time limit — the build was
             stopped, nothing was left running"}
```

(The deploy log is English throughout; the portal says the same thing in
German. Mixing the two inside one log line would only make it harder to
grep.)

— releases the queue and moves on. A failure that is written down is
strictly better than silence: the client polling its id learns
`done, ok:false`, the portal shows it, and the next deployment is not stuck
behind it.

The claim marker also makes a **crashed worker** recoverable: a claim older
than the limit with no result belongs to a run that died, and the next
worker records it as failed rather than leaving the id unanswerable
forever.

Because the worker only runs when a request arrives, that record may be
written much later — so **every reader applies the same rule**: a claim
past the limit is never reported as `running`. The status endpoint answers
`done`/failed, and the portal says the deployment was broken off. The
worker writes it down when it next runs; nobody has to wait for that to be
told the truth.

### 6. Delete a retained package

Each non-running row gains **"Löschen"**, with the usual confirmation. The
host refuses to delete the package in service, by name, for a reason it
states: backup completeness (RFC-0019 §4), rollback, and promotion
(RFC-0020) all read that file. Deleting it would turn a working instance
into one that cannot be reproduced.

### 7. The words

| Where | Today | From here |
|---|---|---|
| Package in service | `läuft` | `in Betrieb` |
| Deployment in flight | *(nothing)* | `läuft — seit …` |
| Queue entry | *(nothing)* | `wartet` |

The rule behind the table: **"läuft" describes an activity, never the
state of being installed.** Anything in service *is in Betrieb*.

## Non-goals

- **Killing a running build.** Decision 4. A half-built image with a
  half-written registry entry is a worse position than a bounded wait.
- **Progress or streamed build output.** Knowing *that* it runs and *since
  when* is the operator's need. Following a build line by line is a
  developer's need and belongs to a workbench, not to the platform's
  portal.
- **Parallel deployments.** The queue stays sequential. Visibility makes
  the sequence bearable; it is not an argument for concurrency.
- **A retry that changes anything.** "Erneut ausrollen" ships the same
  bytes. A different package is a new upload.
- **Blue/green or health-gated rollout.** Still deferred, still waiting on
  telemetry.

## Consequences

- `oaap.apps.runtime` gains a deployment **state** as a named concept: a
  deploy request is `queued`, `running` or `done`, and the platform can be
  asked which. Until now a deployment existed only as an outcome after the
  fact.
- RFC-0019's three-phase handshake is unchanged. Only its answers grow a
  field, so existing clients keep working; a client that ignores
  `deployment` behaves exactly as today, except that it can no longer be
  told a previous deployment's success in place of its own.
- The worker gains a claim marker and a time limit — the first state it
  keeps between picking up a request and finishing it.

## Open for later

- **Notification instead of polling.** A deploy hook that calls back when
  it is done. Right now the caller is an AI in a build loop that can poll
  perfectly well; a callback means holding a foreign URL, which is the
  direction RFC-0019 deliberately walked away from.
- **A history per instance.** The deploy log is per node and read by tail.
  A tenant-scoped, paged deployment history belongs with the audit work of
  RFC-0022, not here.

## Deutsche Zusammenfassung

**Der Anlass.** Am 29.08.2026 um 19:48 UTC lief auf `oaapx01` ein
Deployment von `bdt-hub-test` auf 0.20.6 durch — Anmeldung, Bau, Start,
alles zusammen fünf Sekunden, Container gesund, von außen erreichbar. Für
Jörg sah dasselbe System so aus: *„da ist ein Deployment hängen geblieben,
und aus dem Portal heraus kann ich nicht viel machen."* Beide Lesarten
kamen von demselben Bildschirm. Genau das ist der Fehler.

**Warum ein fertiges Deployment wie ein hängendes aussieht.** In der
Tabelle *Hochgeladene Pakete* bekommt die laufende Fassung das Schildchen
**„läuft"** — und ist die einzige Zeile **ohne Knopf**, weil „Hierauf
zurück" nur für die *anderen* Pakete angeboten wird. „Läuft" heißt auf
Deutsch beides: *ist in Betrieb* und *ist noch am Laufen*. Die Zeile sagt
also „noch beschäftigt" und bietet nichts an. Das ist keine Vokabel-Panne,
sondern das sichtbare Ende einer echten Lücke: **die Plattform kann bisher
gar nicht sagen, dass ein Deployment gerade läuft** — deshalb ist nie
aufgefallen, dass das Wort zwei Dinge trennen müsste.

**Der stille Fehler dahinter.** Dauert ein Bau länger als 120 Sekunden,
antwortet der Hook mit `202 — frag unter GET /deploy/<name>/status nach`.
Dieser Endpunkt gibt aber schlicht **die letzte Protokollzeile der
Instanz** zurück. Während das neue Deployment noch baut, ist das die
*vorige* Zeile: `ok: true, 0.20.5`. Eine Pipeline liest „erfolgreich" und
liegt falsch — still und in die beruhigende Richtung. Das ist der einzige
Punkt hier, der nicht nur fehlt, sondern aktiv falsch ist. Ursache: die
Anfrage hat im Spool eine Kennung, aber sie wird weggeworfen, sobald das
Ergebnis geschrieben wird.

**Und es gibt keine Bremse.** Der Arbeiter hat kein Zeitlimit. Ein
hängender Bau blockiert die gesamte Warteschlange — für alle Instanzen —
und man sieht es nur auf der Maschine, nicht im Portal.

**Was wir beschließen.**

1. **Jedes Deployment bekommt eine Kennung**, und der Status-Endpunkt
   antwortet über *diese* Anfrage — mit einem ausdrücklichen Zustand:
   `wartet`, `läuft`, `fertig` (mit Ergebnis) oder `unbekannt`. Auch ohne
   Kennung meldet er künftig „läuft noch", statt das vorige Ergebnis zu
   nennen; damit sind auch bestehende Clients repariert, ohne dass sie sich
   ändern müssen.
2. **Ein laufendes Deployment ist im Portal sichtbar** — auf der
   Instanzseite und auf der Gesundheitsseite, mit „seit 4 Minuten". Ein
   Zustand, den es nur in `systemd` gibt, gibt es für Dich nicht.
3. **„Erneut ausrollen"** auf dem laufenden Paket. Technisch derselbe Weg
   wie der Rückschritt — dasselbe Paket, dieselben Prüfungen, dieselben
   Bytes.
4. **„Abbrechen" nur, wo es ehrlich ist:** eine Anfrage, die der Arbeiter
   noch nicht angefasst hat, kann zurückgezogen werden. Einen laufenden Bau
   schießen wir **nicht** ab — ein halb gebauter Stand ist schlimmer als
   Warten. Stattdessen ein **Zeitlimit von 20 Minuten**, nach dem das
   Deployment als fehlgeschlagen ins Protokoll geht und die Warteschlange
   freigibt. Ein aufgeschriebener Fehlschlag ist besser als Stille.
5. **„Löschen" je Paket — nie für das Paket in Betrieb.** Backup,
   Rückschritt und Übernahme nach Produktiv lesen genau diese Datei.
6. **Die Wörter werden getrennt:** „in Betrieb" für das, was installiert
   ist; „läuft" nur noch für etwas, das gerade tatsächlich arbeitet.

**Was ausdrücklich nicht kommt.** Kein Abschießen laufender Builds, kein
mitlaufendes Bau-Protokoll im Portal (das ist Werkbank, nicht Betrieb),
keine parallelen Deployments, kein Blau/Grün — das wartet weiter auf
Telemetrie.

**Was sich für Dich ändert.** Du siehst, ob gerade etwas läuft und seit
wann. Du kannst dasselbe Paket noch einmal ausrollen, ohne den Umweg über
den Vorgänger. Du kannst eine Anfrage zurückziehen, die noch wartet. Und
nichts bleibt mehr für immer hängen: spätestens nach 20 Minuten steht ein
Ergebnis im Protokoll.

# RFC-0071: Rebuild — An Instance Is Built Again on a Fresh Base, and Falls Back

- **Status:** **Accepted** (2026-11-06, Jörg: D1–D9 as recommended — D6 "no, for
  now"). Stage 1 next, after RFC-0070 stage 1 (built 2026-11-06, reference 0.1.226).
- **Date:** 2026-11-05
- **Authors:** Claude (measurement, proposal), Jörg (requirement: "eine Instanz wird als
  auffällig gemeldet und wir können versuchen, sie mit einer neuen gepatchten Version neu
  zu bauen. Wenn das nicht klappt, dann auch mit fallback", decides)
- **Depends on:** RFC-0019 (the retained package — the bytes a rebuild is made from),
  RFC-0020 (promotion: the same bytes go live), RFC-0024 ("Erneut ausrollen" is a rollback
  onto the running package; the deploy worker, its time budget, its health wait), RFC-0050
  (update of a named instance: test first where a test instance exists), RFC-0030
  (rehearsal), RFC-0069 (the node's window, the protections, the cases), RFC-0070 (the DSA
  reader — reused inside the image), RFC-0061 (cases), RFC-0032 (events), I-40 fields 2
  and 5
- **Changes:** `oaap.apps.runtime` (the base record per instance, the `rebuild` action, the
  predecessor image), `oaap.core.updates` (host care: the image state per instance; the
  platform's own images), `oaap.fleet.status` (counts), `oaap.core.host` (CLI),
  `oaap.core.portal` (the card on the instance page)

## Summary

An instance's image is built **on the node**, from the package, on top of a base image
the node pulled once. The build never pulls again, so every later build — a redeploy, a
retry, a rollback — stands on the base of the first day. Measured tonight: the base of
fourteen of our apps was pulled on 28 October and is already behind upstream; the
gateway and the broker run on images pulled on 22 June. The I-40 sentence "alte Abbilder
laufen sonst ewig" is a measurement now, not a fear.

This RFC gives the platform three things. A **reading**: for every instance, the base its
image stands on (reference, digest, date), whether upstream has moved, and — with the
reader of RFC-0070 run against the packages *inside* the image — how many security
advisories are open in it. A **rebuild**: the same package bytes built again on a freshly
pulled base, by hand or by itself, first on the test instance where one exists, never on
a protected instance, inside the node's window. A **fallback**: the running image is kept
as the predecessor before the rebuild; a build that fails changes nothing; a new container
that does not become healthy is replaced by the predecessor, and the case stays open and
says so.

What the platform cannot heal alone is said as plainly: a vulnerability in the app's own
dependencies (requirements, package-lock) or in a foreign image pinned to a version needs a
new package from the author; the platform reports it and offers the store update, nothing
more.

## 1. What the node does today (measured 2026-11-05, `oaap-test`)

| Question | Measured | Where |
|---|---|---|
| How is an instance's image made? | `docker build -q -t oaap-app/<id>:<version> <dir>` on the node, from the retained package; a foreign image (`image:` in the manifest) is `docker pull`ed | `appctl.py` (the deploy, ~17250) |
| Does the build pull the base again? | **No.** No `--pull`; Docker pulls a base only when the node has none | same |
| Base of our own apps | `python:3.13-slim` for 14 of 19 apps in `oaap-apps`; `node:22-slim` only in `oaap-lab` | the Dockerfiles |
| Local `python:3.13-slim` | pulled 2026-10-28, index digest `ae14d4…`; upstream index digest `09a17c…` — **behind** | `docker image inspect`, `docker buildx imagetools inspect` |
| Local `node:22-slim` | pulled 2026-10-28 — behind | same |
| Local `caddy:2` (the gateway) | pulled **2026-06-22** — behind | same |
| Local `eclipse-mosquitto:2` (the broker) | pulled **2026-06-22** — behind | same |
| Images behind running containers | built or pulled between June and September: forgejo (09.07.), stirling-pdf (06.08.), pgvector (13.08.), uptime-kuma and vaultwarden (22.08.), ollama, n8n, open-webui (03./04.09.) | `docker ps`, `docker image inspect` |
| What does "Erneut ausrollen" (RFC-0024) do to the base? | Nothing: it rebuilds from the retained package on the cached base. The image tag is overwritten; the old image becomes untagged and is not addressed by anything | RFC-0024 §4, the worker |
| What does a rollback restore? | The *package* (RFC-0019): it builds again. There is no handle on the previous *image* | same |
| Does `oaap update` pull the platform's own images? | No — the gateway's `caddy:2` is from June after dozens of updates | §1 rows above |

Both digests compared are index digests (what a multi-arch pull records in `RepoDigests`
and what `imagetools inspect` prints), so "behind" is a fact of the same kind on both sides.

**What is NOT measured:** whether any of the open Debian advisories inside the image is
reachable from the app. The reading says "older than the fix"; "not affected here" is a
person's sentence (RFC-0070 §6), recorded as the case's reason.

## 2. Three layers, one of which the platform can heal alone

| Layer | Example | The fix | Who can do it |
|---|---|---|---|
| **Base image** — the OS packages and the runtime inside the image | `python:3.13-slim`: Debian's libc, openssl, zlib, Python itself | the same package built again on a freshly pulled base | **the platform alone** — same bytes, new image |
| **The app's own dependencies** | `requirements.txt`, `package-lock.json` | a new package version from the author | the author; the platform reports and offers the store update (RFC-0050) |
| **A foreign image** | `quay.io/keycloak/keycloak:26.7.4` (pinned), `forgejo:11`, `n8n:latest` (moving) | pinned: a new package version naming the new tag; moving: pull again | pinned: the author; moving: **the platform alone** (a redeploy already pulls) |

The layer decides what "rebuild" can mean; the reading of §3 says which layer an instance
is in.

## 3. The reading (stage 1)

**The base record.** At every build the deploy records, per service of the instance:

```json
"base": {"ref": "python:3.13-slim",
         "digest": "sha256:ae14d4…",
         "pulled": "2026-10-28T02:04:41Z",
         "built": "2026-11-05T19:57:43Z"}
```

`ref` is the `FROM` line of the Dockerfile the package carries (the first stage's, for a
multi-stage build the last `FROM`); `digest` and `pulled` are what the node's Docker
holds for that reference at build time. A foreign image records the same for the image
itself. An instance built before this RFC has no record: its state is `unknown`, never
`fresh`.

**Upstream.** Once a day the node asks the registry for the index digest of every
*distinct* base reference it holds (a handful per node, not one per instance — the
registries rate-limit) and stores it with the time. A reference whose upstream digest
differs from the recorded one is **behind**; one the registry did not answer for is
`stale` (the last answer and its age are kept, like RFC-0070's list).

**Advisories inside the image.** The reader of RFC-0070 — Debian's DSA list against a
`dpkg` list with `dpkg --compare-versions` — runs against the *image*, not the container:
`docker run --rm --network none --read-only --entrypoint dpkg-query <image> -W -f …` (a
base without `dpkg`, such as Alpine's `caddy:2`, is `unknown`; D8). The result per image:
`open`, `oldest`, the names kept on the node. The same image serves many instances
(fourteen apps share one base): read once per image, attributed to every instance on it.

**Where it shows.** The three places of host care (RFC-0069 D4): the instance page (a
card "Abbild", next to "Neustart-Schutz": base, built, behind/fresh/unknown, open
advisories, the buttons of §4), `oaap status` / `oaap app status <name>`, and the fleet
document as **counts only** — instances behind, instances with open advisories, the oldest
— never names of packages or bases.

**State words** (one per instance, the worst of its services): `fresh` (base equals
upstream, 0 open), `behind` (upstream moved, 0 open — informative, not a finding),
`open` (advisories inside, n and oldest), `unknown` (no record, no dpkg, or no answer
older than 7 days), `stale` (no answer for less than 7 days; last reading shown with its
age).

## 4. The rebuild (stage 2)

**What it is.** The retry of RFC-0024 — a rollback onto the running package, the same
retained bytes — with one difference: the base is pulled first (`docker pull <ref>` for
every base reference of the package, then the build). The package is the same; the image
is new. RFC-0020's "the same bytes go live" is about the package and keeps holding (D1);
the base record of §3 is what tells the two images apart.

**The predecessor.** Before the build, the running image is tagged
`oaap-app/<id>:<version>-prev` (one per service). Exactly one predecessor exists per
instance; the next successful rebuild replaces it (D2). It is what the fallback of §5
returns to, and what `oaap app rebuild <name> --back` returns to by hand.

**Order.** The rules that already exist apply unchanged:

1. A **protected** instance (RFC-0069, held with a reason) is not rebuilt; the case says
   "held by … until …" and the rebuild waits for the hold to end.
2. Where the tenant holds a **test instance** of the same app, the test instance is
   rebuilt first and production follows by promotion (RFC-0050's rule from 2026-10-11,
   Jörg: "test first, where a test instance exists"). A rehearsal does not count.
3. A rebuild by itself (stage 3) runs only inside the node's **window** (RFC-0069), one
   instance at a time, and never on the day of a planned reboot.
4. By hand — the button on the card, `oaap app rebuild <name>` — runs now, with the
   worker's time budget (RFC-0024 §5).

**Health.** The deploy's existing health wait decides. Healthy: the predecessor tag moves
on, the base record is new, the audit line says `instance.rebuild` with the old and the
new digest. Not healthy within the budget: §5.

## 5. The fallback

A ladder, each rung only when the one above did not hold:

1. **The build fails** (pull refused, Dockerfile breaks on the new base, timeout): nothing
   has changed — the old container never stopped. True today already; the case records the
   build's last lines.
2. **The new container does not become healthy:** the worker recreates the service from
   the predecessor image, waits for health again, and the case stays open: "rebuilt at …,
   not healthy, running on the previous image (built …) since …". The instance's state
   stays `open`; a second automatic attempt waits for upstream to move again (a new
   digest), not for the next night.
3. **Upstream has not moved** (the base is `fresh` and still has open advisories, which
   happens between Debian's fix and the image maintainers' rebuild — often a day, sometimes
   a week): there is nothing to rebuild on. The case says "fix not yet in the base image";
   the reading repeats daily.
4. **The vulnerability is in the app's dependencies or a pinned foreign image:** not a
   rebuild at all. The case names the layer and the store update, if the catalog has a
   newer package (RFC-0050), and otherwise says that the author has to deliver.
5. **Quarantine** — closing the instance's outer door (its exposure, RFC-0044 / RFC-0068)
   when it is exposed, the finding is critical, and rungs 1–4 are exhausted — is **not**
   done by the platform (D6, recommended "no"): that is a person's decision, and the case
   is where it is taken.

## 6. The platform's own images (I-40 field 5, stage 4)

The gateway (`caddy:2`, Alpine), the broker (`eclipse-mosquitto:2`), identity and portal
(`python:3.13-slim`) are images too, and §1 shows they are the oldest on the node. The
same reading applies (`unknown` for Alpine until D8's OSV path). The rebuild is `oaap
update`'s: it pulls the moving tags of the core services and recreates those whose image
changed — **inside the window**, because recreating the gateway is a short outage for
every instance behind it, announced like a reboot (RFC-0069 stage 2: a case in every
production inbox, 24 h ahead). Outside the window `oaap update` keeps its promise of
today: the gateway is reloaded, never restarted.

## 7. Who may do what

| Who | May |
|---|---|
| Everyone who sees the instance page | read the card |
| `tenant_admin` of the instance's tenant | rebuild by hand, go back to the predecessor — the door of RFC-0069 stage 5 (same origin, the worker checks the tenant, cross-tenant is "unknown instance") |
| `server_admin` | the same on the CLI for any instance; set the node's rebuild policy (D3/D4: by itself in the window, or by hand only) |
| the node itself (stage 3) | rebuild inside the window on the trigger of D3; never a held instance; never a core service outside §6 |

## 8. Security requirements (additions to `oaap.apps.runtime` §4)

1. A rebuild builds from the **retained package** (RFC-0019) and nothing else — never from
   a working copy, a URL, or a package that is not the one in service.
2. The base is pulled by **reference**; the record holds the digest that came. A build
   whose base digest is not the one just pulled is refused (the cache must not win).
3. The predecessor image is **never** removed by a rebuild that did not reach health.
4. The reading inside an image runs with **no network**, **read-only**, as the image's
   user, with the worker's time budget; its output is a package list, parsed, never
   executed.
5. Names of packages and bases stay **on the node**; the fleet document carries counts and
   dates. The event on a broker node (RFC-0032) carries the instance name, the state word,
   and the count — nothing more.
6. "Not affected" is a **person's sentence** in the case's reason, with name, role and
   time; it holds until the base moves or a new advisory arrives.
7. A rebuild by itself happens **inside the window only**, one instance at a time, never
   on a held instance, never on a day with a planned reboot, and is written to the tenant's
   audit log with both digests.

## 9. Stages

| Stage | Content | Measured on |
|---|---|---|
| **1** | Spec (`oaap.apps.runtime`: the base record; `oaap.core.updates`: the image state in host care; fleet: counts); the record at build; the daily upstream question; the RFC-0070 reader against the image; the card, the status lines, the counts; `unknown` for everything built before | `oaap-test` (92 images, which are behind and which have open advisories — the number itself is the finding), `oaap-demo` |
| **2** | `oaap app rebuild <name>` and the button: pull, predecessor tag, build, health, the fallback to the predecessor, `--back`; test-first and protection respected; audit with both digests | `oaap-test`: one instance with open advisories rebuilt, 0 open after; one rebuild made to fail at health (a broken package on purpose) and the fallback measured |
| **3** | The node rebuilds by itself in the window on D3's trigger; the case before and after; the event | `oaap-test` with a real window night |
| **4** | Field 5: `oaap update` pulls the core images and recreates them in the window, the gateway announced like a reboot | `oaap-test`, then the fleet on Jörg's word |
| **5** | The dependency layer: `pip list` / `npm ls` inside the image against OSV (PyPI, npm ecosystems); reporting and the store update only, no rebuild | `oaap-test` |

## 10. Not part of this RFC

- Fixing an app's own dependencies — the author's package does that.
- Scanning for malware, secrets or misconfiguration inside images (trivy's other half).
- Judging reachability of a vulnerable library from the app.
- A fleet-wide order of rebuilds; every node acts for itself inside its window.
- Rebuilding on *every* upstream move (the base moves weekly without a security reason);
  the trigger is an open advisory (D3).

## 11. Decisions (Jörg)

| | Decision | Recommendation |
|---|---|---|
| **D1** | A rebuild is the same package on a new base: RFC-0020's "same bytes" stays about the package; the image is told apart by its base record | yes — otherwise a security rebuild would need a new package version from every author for every Debian advisory |
| **D2** | Exactly one predecessor image per instance, tagged, replaced by the next successful rebuild, never removed by a failed one | yes — the fallback needs a handle, and a stack of images costs disk the nodes do not have to spare ([[flotte-plattenplatz]]) |
| **D3** | Trigger of a rebuild by itself: an open advisory inside the image **and** a base that has moved upstream since; `behind` alone is informative | yes — upstream rebuilds weekly without a reason that concerns us; an advisory without a moved base has nothing to rebuild on (§5 rung 3) |
| **D4** | A rebuild by itself only inside the node's window, one at a time, test first where a test instance exists, never a held instance, never on a reboot day | yes — the rules exist; this RFC adds no new exception |
| **D5** | On a new container that does not become healthy: back to the predecessor, the case stays open, the next attempt waits for a new base digest | yes — "running on the previous image since …" is the honest state; retrying nightly on the same base would fail the same way |
| **D6** | Quarantine (closing an exposed instance's outer door) as the last rung — by the platform? | **no, for now** — a machine closing a production door on a reading of "older than the fix" takes a decision a person must take; the case is where it is taken, and RFC-0044/0068 give that person the handle |
| **D7** | Field 5: `oaap update` pulls the core images and recreates changed core services inside the window; the gateway's recreation is announced like a reboot | yes, as stage 4 — the gateway on a Caddy from June is the one door of every node; outside the window the reload-only promise stays |
| **D8** | Images without `dpkg` (Alpine: `caddy:2`) are `unknown` in stage 1; the OSV path (apk, PyPI, npm) comes with stage 5 | yes — `unknown` is honest, "0 open" would not be |
| **D9** | Build stage 1 now, before RFC-0070's stages 2–4 | yes — it is a reading, the reader exists after RFC-0070 stage 1, and the number of instances with open advisories on six nodes is the finding that decides how urgent stage 2 is |

## 12. Open questions, answered in words

- *Why not scan with trivy?* trivy reads the same Debian data and more (OSV for pip/npm),
  but it is a 60 MB binary with its own database and its own update cadence on every
  node. Stage 1 needs one reader we already have; stage 5 adds the OSV ecosystems the
  same way RFC-0070 planned to. trivy stays the comparison tool of the measurement.
- *Why read the image and not the container?* The container is what runs, but reading
  inside it means `docker exec` into a production process with its secrets and its
  network. The image is the same bytes, read with no network and read-only (§8.4).
- *Why not `--pull` on every deploy, simply?* Because then every retry and rollback would
  change the base silently, and RFC-0024's "retry changes nothing" would be false. The
  pull is the *point* of a rebuild and is recorded as such.
- *What about an instance whose package pins `FROM python:3.11`?* The rebuild pulls
  `python:3.11` again — Debian's packages inside move, Python's minor does not. A base
  that upstream no longer maintains is `behind` forever with open advisories; the case
  names the author.
- *Does a rebuild move data?* No — the same rules as a redeploy: the data directory stays
  (RFC-0024's rollback keeps data unless told otherwise).
- *And oaapx01's 22 instances?* Stage 1 says how many are `open`; stage 2 by hand on one
  of them, on Jörg's word; stage 3 only after a window night on oaap-test was measured.

## Deutsche Zusammenfassung

**Der Befund.** Das Abbild einer Instanz wird auf dem Knoten gebaut, aus dem Paket, auf
einem Basis-Abbild, das der Knoten einmal geholt hat. Der Bau holt nie wieder nach — ohne
`--pull` nimmt jeder spätere Bau, auch „Erneut ausrollen“ und jeder Rollback, die Basis
vom ersten Tag. Heute Nacht auf oaap-test gemessen: `python:3.13-slim` (Basis von 14
unserer Apps) am 28.10. geholt, Upstream schon weiter; `caddy:2` (das Gateway) und
`eclipse-mosquitto:2` (der Broker) vom **22. Juni**; laufende Container auf Abbildern von
Juni bis September. Ein Rollback stellt das *Paket* wieder her, nicht das Abbild — auf
das alte Abbild gibt es heute keinen Griff.

**Drei Schichten, eine kann die Plattform allein heilen.** Die *Basis* (Debian-Pakete,
Python im Abbild): dasselbe Paket auf frisch geholter Basis neu bauen — dieselben
Paket-Bytes, neues Abbild. Die *Abhängigkeiten der App* (requirements, package-lock) und
ein *festgenageltes Fremd-Abbild* (Keycloak 26.7.4): nur ein neues Paket des Autors hilft;
die Plattform meldet und bietet das Store-Update an.

**Drei Dinge.** Das **Lesen** (Stufe 1): je Instanz die Basis mit Digest und Datum, ob
Upstream weitergezogen ist, und — mit dem Leser aus RFC-0070 gegen die Pakete *im
Abbild* — wie viele Advisories darin offen sind; Zustände `fresh`, `behind`, `open`,
`unknown`, `stale`; Karte „Abbild“ auf der Instanzseite, `oaap status`, im
Flottendokument nur Zahlen. Der **Neubau** (Stufe 2/3): „Erneut ausrollen“ mit
vorherigem Pull; das laufende Abbild bleibt als *Vorgänger* getaggt (genau einer); zuerst
die Testinstanz, wo eine existiert (Jörgs Regel aus RFC-0050), nie eine geschützte
Instanz, von selbst nur im Fenster des Knotens und nur bei offenem Advisory **und**
weitergezogener Basis. Der **Rückfall**: Bau gescheitert → nichts verändert; neuer
Container nicht gesund → zurück auf den Vorgänger, Vorgang bleibt offen und sagt „läuft
seit … auf dem vorigen Abbild“; Basis noch nicht nachgezogen → „Fix noch nicht im
Basis-Abbild“; Abhängigkeit oder Fremd-Abbild → Autor genannt. **Quarantäne** (Außentür
schließen) macht die Plattform **nicht** (D6, Empfehlung nein): das entscheidet ein
Mensch im Vorgang.

**Feld 5.** Gateway, Broker, Identity, Portal sind auch Abbilder — dieselbe Lesung; der
Neubau ist der von `oaap update`, im Fenster, das Gateway angekündigt wie ein Neustart
(Stufe 4).

**Neun Entscheidungen** (§11), alle mit Empfehlung; D6 „nein, vorerst“, D9 „Stufe 1
jetzt bauen“, weil die Zahl der Instanzen mit offenen Advisories auf sechs Knoten erst
sagt, wie dringend Stufe 2 ist.

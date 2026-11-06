# RFC-0071: Rebuild — An Instance Is Built Again on a Fresh Base, and Falls Back

- **Status:** **Accepted** (2026-11-06, Jörg: D1–D9 as recommended — D6 "no, for
  now"). **Stages 1, 2 and 2b built** (reference 0.1.227, 0.1.228, 0.1.229; stage 2b: the recorded Git commit and manifest 0.10 `care.rebuild`, `oaap.apps.runtime` 0.2.52 §2.31, §15 below; stage 2: `oaap.apps.runtime` 0.2.51 §2.30, §14 below; stage 1: `oaap.apps.runtime` 0.2.50 §2.29,
  `oaap.core.updates` 0.9 §2.9, `oaap.fleet.status` 0.8), measured on oaap-test (§13).
  Stages 3–5 not built.
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

1. A rebuild builds from the **bytes in service** and nothing else: the **retained
   package** (RFC-0019) or the **commit a Git install recorded** (§15) — never from a
   working copy, a branch, or a package that is not the one in service.
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
| **2b** | The recorded Git commit; manifest 0.10 `care.rebuild: self \| release`; "Selbstheilung" on the card and in the CLI (§15) | `oaap-test`: a Git instance installed, rebuilt from its commit |
| **3** | The node rebuilds by itself (only with `care.rebuild: self`, §15) in the window on D3's trigger; the case before and after; the event | `oaap-test` with a real window night |
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

## 13. Stage 1 as built (2026-11-06)

**The number D9 waited for (oaap-test, 07:35 CET, 37 images, 11 distinct
references, 33 s for a full read, 1 s with the cache):**

| | Instances (28) |
|---|---|
| `open` — advisories inside the image | **19** |
| `behind` — 0 open, upstream moved (ollama, open-webui, stirling-pdf) | 3 |
| `unknown` — no dpkg (Keycloak, Alpine, forgejo, n8n) or image removed | 6 |
| `fresh` | 0 (no instance has a base record yet) |

- The fourteen `python:3.1x-slim` apps carry 1–5 open advisories each (apt
  2026-11-04; openssl, pcre2, xz-utils, ca-certificates since 2026-09-29) — the
  base of 28 October. Layer 1 of §2: a rebuild on a fresh base heals them.
- `vaultwarden` (moving tag, behind upstream): 8 open since 2026-08-14 — a pull heals it.
- `uptime-kuma:2.5.3` (pinned, = upstream): 5 open since **2026-05-19** — layer 3, the
  author's.
- **Platform (field 5):** the broker `mosquitto-go-auth:3.0.0-mosquitto_2.0.18`
  (pinned, = upstream) 5 open since **2025-05-29** — only a new tag in the platform
  helps; portal and identity 1 open (apt); the gateway `caddy:2` is Alpine (`unknown`)
  and behind upstream.
- **Found while reading:** three platform containers (connect, twin, relay) and two
  instances run on images the node has **removed** — a newer build took the tag, the
  container kept running the old id. They are `unknown` with that reason. Stage 4 (core
  images recreated in the window) will end the core case; for instances it is what the
  predecessor tag of §4 has to keep in mind: an untagged image is gone at the next
  prune.

**What differs from §3 as written.**

- The image read is the one the container **runs** (`docker inspect`), not the tag.
- Inside an image the archives are not known (slim images carry no package lists):
  every package is compared as Debian's. A vendor package with a Debian-like name could
  be counted as open; the reverse — a vendor package taken as clean — cannot happen.
- The platform's own containers are read in stage 1 already (shown as "platform"),
  rebuilt only with stage 4.
- The minute job reads inside a budget of 25 s; the rest comes ten minutes later.
  `sudo oaap node care images --read` reads everything now.

**Measured.** CLI with names on the node; `oaap status` line; the portal's node-table
row and the card "Abbild" rendered for three instances (open with count and date;
pinned = upstream; two services, both unknown with the reason); the base record
taken with real Docker on a package (`python:3.12-slim`, local `aa94…`, upstream
`4840…` → behind). A full install of a throw-away instance was **not** possible:
oaap-test has no free Docker address pool left ("all predefined address pools have
been fully subnetted") — a node condition, not this stage's; the half-installed probe
left two keys, which were revoked. Tests: `test_images.py` (40), neighbours green.

## 14. Stage 2 as built (2026-11-06, reference 0.1.228)

`oaap app rebuild <name> [--back]`, the buttons on the card "Abbild", the spool action
`rebuild` — one function (`oaap.apps.runtime` 0.2.51 §2.30).

**What differs from §4/§5 as written.**

- **Only from the retained package** (§8.1) is taken literally: an instance with a
  built service installed from a path or a branch is refused with that reason — on
  oaap-test that is 27 of 28 instances (only `wegweiser` came as a package). On a
  production node, where apps arrive as packages, it is the rule that holds; for the
  test node it is the honest answer. A foreign image needs no package.
- **Test first** is a check of the test instance's base record against the digest just
  pulled, not a promotion: the same package, so "promote" would move nothing.
- The predecessor tag is moved by **every** attempt, not only by a successful one: the
  image that ran when the attempt started is the one to fall back to. It is removed
  with the instance.
- "Answers" is the probe of standby's wake (any HTTP status line within 120 s).

**Measured on oaap-test (08:13–08:18 CET).**

| Case | Result |
|---|---|
| Fallback — a probe package that refuses to start on any image but its first (`rbprobe`, installed from a zip on the base of 28 October, base record `ae14…` written by the real install) | pull `python:3.13-slim` → `09a17…`, build, recreate, no answer in 120 s → tag back, recreated from `a052…`, answering again; base record back to `ae14…`; tenant log `instance.rebuild [failed] … a0524dd7c53c -> 84d9bf780c10; not answering within 120 s, back on the previous image`; 143 s in all |
| Success — `wegweiser` (package 0.4.1, 4 open: pcre2, xz-utils, ca-certificates, apt) | 13 s; `656e7c6f2ec4 -> 39ff70bc3fae`; afterwards `fresh`, **0 open**, base = upstream; gateway answers |
| `--back` through the spool, as the portal sends it | `ok`, "rbprobe runs on the previous image again.", one log line |
| The card, live | `wegweiser`: fresh, "Auf frischer Basis neu gebaut", both buttons; `studio` (git): no button, the §8.1 sentence |
| Remove | `oaap app remove rbprobe --purge` removes the predecessor tag (added for this stage) |

Afterwards oaap-test: 18 of 28 instances `open` (was 19). The install of the probe was
the first on oaap-test after its Docker address pools were extended (§13): its network
came from `10.240.0.0/16`.

## 15. Stage 2b: the recorded commit, and the author's promise (2026-11-06, reference 0.1.229)

**Why.** Stage 2 refused every instance from a Git source — on oaapx01
the six instances with open advisories in their image are all of them
(`ai-gateway`, `ollama-models`, `bec-wegweiser`, `studio`, `fleetview`,
`hbvp-rollen-rechte`), and these are apps we write ourselves. Jörg
(2026-11-06): "wir sind für verschiedene Apps sogar selbst
verantwortlich … Wenn es reicht, auf dem Knoten aktuelle Quellen zu
ziehen und einfach ein neues Image zu erzeugen, wäre das … eine
Zwischenlösung. Vielleicht sollten wir das aber auch im Manifest
festhalten: Selbstheilung möglich vs. nicht möglich?" — and on the
proposal: "1 und 2 OK".

**What changed (`oaap.apps.runtime` 0.2.52 §2.31).**

1. **The recorded commit.** Every install from a Git URL records the
   commit it checked out (`source.commit`). A rebuild of a Git instance
   fetches the repository and checks out exactly that commit — the bytes
   in service, like the retained package. §8.1 reads from now on: *a
   rebuild builds from the bytes in service — the retained package or the
   recorded commit — and nothing else.* "Pull the current sources" is not
   a rebuild but an update: new code may come with it, so it stays the
   store update's, through the test instance where one exists (RFC-0050).
   A Git install from before 0.1.229 has no recorded commit (the deploy
   log holds one for three of 28 instances on oaap-test, resolved before
   the clone and months old — not good enough to build from); it is
   refused until one store update records it.
2. **The promise, manifest 0.10.** `care.rebuild: self | release`. `self`
   is the author's promise that building the same source again on a fresh
   base changes nothing but the base (dependencies pinned, a lockfile);
   `release`, and a missing field, says only a new version heals. The
   platform judges whether a rebuild is *possible* (bytes in service);
   the author says whether it is *safe*. Self-heal — the node rebuilding
   by itself in its window, stage 3 — needs both. A person may rebuild by
   hand without the promise.
3. **Shown.** The card "Abbild" says what a rebuild would build from
   (package, commit, pull) and "Selbstheilung: möglich / nicht möglich —
   …"; `oaap node care images` prints the same per instance.

**Two layers, two workflows** (the answer to "how do we look for
security problems in our own apps"):

| | the base (Debian packages in the image) | the app's own dependencies (pip, npm) |
|---|---|---|
| seen by | the image reading (stage 1) | not by the node (stage 5, or the repository) |
| healed by | a rebuild on a fresh base (stage 2/2b), by itself with `self` (stage 3) | a new version from the author → store update, test first |

**Measured on oaap-test (2026-11-06, 11:50 CET, 0.1.229 staged).**

| Case | Result |
|---|---|
| `fleetview` (Git, test channel), installed before 0.1.229 | rebuild refused: "installed from Git before the commit was recorded -- one store update or reinstall records it" — nothing pulled |
| reinstall from its source | `source.commit` = `063e4d1763d7…`, `care_rebuild` = `''` (the manifest is silent); 3 open → 0 (the tag `python:3.13-slim` on the node was already fresh from the morning's pull) |
| `oaap app rebuild fleetview` | pull, blobless clone, checkout of exactly that commit, build, recreate, answers — 10 s; audit `commit 063e4d1763d7; service python:3.13-slim: 2ec654a52bb5 -> 235e18ea51d2` |
| `--back` | "fleetview runs on the previous image again." |
| `studio` (Git, before 0.1.229) | refused, one sentence |
| `oaap node care images`, the card (the live portal's view function) | the same answer for `fleetview` (git + commit, self-heal no: no promise), `studio` (no commit), `wegweiser` (package), `ollama` (pull) |

The image changed although base and commit were the same: a build is not
byte-reproducible (layer metadata), which is why "changes nothing but the
base" is the author's promise and not something the node can prove. The
rebuild removes `.git` from the checkout: a build context at the
repository's root would otherwise carry the clone's config — the URL,
perhaps with a credential — into the image. (An *install* from Git still
builds from the clone with `.git`; for every app on our nodes the build
context is a subdirectory, so nothing is carried today. Noted, not changed.)

**Documented for later (Jörg, 2026-11-06: "für später dokumentieren").**
A CI template for our app repositories: a scheduled job (weekly, and on
every push) that runs `osv-scanner` against the lockfiles and opens an
issue when a dependency has a known vulnerability; Dependabot alerts
switched on. CI here means: GitHub runs a small script by itself, on a
schedule or on a push — nobody has to remember. The template is written
once and copied into every app repository; together with `care.rebuild:
self` it is what makes the promise checkable. Not built.

## Deutsche Zusammenfassung

**Stand 06.11. (Stufe 2b):** Jede Installation aus Git hält ab 0.1.229 den
Commit fest; der Neubau baut genau diesen Commit auf frischer Basis neu —
die laufenden Bytes, wie beim Paket. „Neuester Stand aus Git“ bleibt ein
Store-Update. Manifest 0.10: `care.rebuild: self | release` — die Zusage
des Autors, dass ein Neubau nur die Basis ändert; Selbstheilung (Stufe 3)
nur mit Zusage **und** Bytes zum Bauen. Ältere Git-Instanzen brauchen
einmal ein Store-Update. Die CI-Vorlage für unsere App-Repos
(`osv-scanner` wöchentlich, Dependabot) ist für später festgehalten, nicht
gebaut. Einzelheiten §15.

**Stand 06.11. (Stufe 2):** Neubau gebaut (0.1.228) und auf oaap-test gemessen:
wegweiser in 13 s von 4 offenen Meldungen auf 0; eine absichtlich kaputte Sonde fiel
nach 120 s von selbst auf ihr voriges Abbild zurück, mit Protokollzeile; Zurück von
Hand über die Portal-Tür ging. Neu gebaut wird nur aus dem zurückbehaltenen Paket — auf
oaap-test hat das nur wegweiser, die anderen kamen aus Pfaden oder Git. Einzelheiten
§14.

**Stand 06.11.:** Angenommen (D1–D9 wie empfohlen, D6 „nein, vorerst“). Stufe 1
gebaut (Referenz 0.1.227) und auf oaap-test gemessen: **19 von 28 Instanzen haben
offene Debian-Meldungen im Abbild** — die vierzehn Python-Apps von der Basis vom
28.10. (heilt ein Neubau), vaultwarden seit August (heilt ein Pull), uptime-kuma
festgenagelt seit Mai (nur der Autor); der Broker der Plattform festgenagelt seit
**Mai 2025** (nur ein neuer Tag der Plattform). Nebenbefund: drei
Plattform-Container laufen auf Abbildern, die der Knoten schon gelöscht hat. Der
Knoten oaap-test hat keine freien Docker-Adressbereiche mehr (kein neues
Instanznetz möglich). Einzelheiten in §13.

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

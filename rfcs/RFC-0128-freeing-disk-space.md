# RFC-0128: Freeing Disk Space — a Care Measure of the Node

- **Status:** **Accepted (2026-11-24)** — D1–D6 decided the same day (§9):
  D1, D2, D3, D5, D6 as recommended, D4 with 2 GB instead of 1 GB. Nothing
  built yet. The facts in §1 were
  measured the same day on `oaap-demo` and in reference 0.1.376.
- **Date:** 2026-11-24
- **Authors:** Jörg (the need, 2026-11-24: "unnötigen Plattenplatz freigeben.
  Automatisch per Job oder auch für den Server-Admin aus dem Portal heraus"),
  Claude (facts, design)
- **Depends on:** RFC-0026 (retained packages), RFC-0069 (care, the reboot
  window), RFC-0071 (the rebuild and its predecessor `-prev`), RFC-0080
  (notifications), RFC-0083 (weekly report: disk growth per week)
- **Related:** RFC-0085 addendum of 2026-11-24 (`disk.trend`, a forecast of
  "disk full" — the trigger of §4.2), `oaap.data.backup` (backups keep their
  own retention)
- **Changes (when accepted):** `oaap.core.updates` (host care: a new care
  measure "space"), `oaap.core.portal` (a page for the `server_admin`),
  `oaap.apps.runtime` (which images an instance keeps), the CLI
  (`oaap care space`)
- **Not part of this RFC:** removing data of any kind — volumes, instance
  storage, backups, retained packages (they have their own rules); a quota per
  tenant.

## Summary

A node grows images it no longer needs: every new version of an app builds a
new image and the old one stays. On `oaap-demo` that was **+101 GB in one week**
(2026-11-16 to 22), mostly ten versions of `webtop` at 13 GB each. By hand,
removing old app images and the build cache freed **53 GB (58 % → 45 %)**.
This RFC makes it a care measure of the node: it knows which images an
instance still needs (the one in service, the predecessor of a rebuild, the
previous version as the fast way back), frees the rest by a nightly job and on
pressure, and shows the `server_admin` in the portal what can go — with images
the platform did not build left to a human.

## 1. Facts (measured 2026-11-24)

| # | Fact |
|---|---|
| F1 | Weekly reports of 2026-11-22: `oaap-demo` +101.1 GB, `oaap-test` +95.4 GB (peak 96 %), `oaap-bernd` +214 MB, `raspberrypi` +136 MB. |
| F2 | `oaap-demo`: 110 images, 202.7 GB; build cache 54.7 GB (1084 entries, none active). `oaap-app/webtop` in ten versions (0.1.2 … 0.2.0), 12.5–13.8 GB each. |
| F3 | By hand (Jörg's word): every `oaap-app/<id>` version older than the one in service and its direct predecessor (41 images), the dangling layers and the build cache — 242 GB → 189 GB used. Nothing running was touched. |
| F4 | The platform removes one image only: the `-prev` tag after a successful rebuild (RFC-0071, `appctl` `_prev_tag`). A new version leaves the old image in place forever. |
| F5 | Container logs are capped (`max-size=10m`, `max-file=3`, `CONTAINER_LOG_OPTS`); journald is not (1.3 GB on `oaap-demo`). |
| F6 | Retained packages are capped at four per instance (`ARTIFACT_KEEP`, `artifact_prune`) — an older version can always be **rebuilt** from its package; its image is only the fast way. |
| F7 | `oaap-demo` holds 30 Docker volumes (21.5 GB) no container uses — models, a database and n8n from before OAAP. They look like garbage and are not: never to be removed by a rule (memory of 2026-11-16). |
| F8 | Images the platform did not build (`sapse/abap-cloud-developer-trial` 85 GB, `ollama`, `open-webui` …) belong to someone's work; the platform cannot know whether a download of 85 GB is wanted again. |
| F9 | `disk.full` mails at a fixed level (`disk_warn`/`disk_crit`); a forecast `disk.trend` is being built (RFC-0085 addendum, 48 h warning / 12 h critical). |

## 2. Classes

| Class | What | Rule |
|---|---|---|
| **A — cache** | build cache, dangling image layers | always freeable |
| **B — old versions** | `oaap-app/<id>[-<svc>]:<version>` older than the newest version **kept** for an instance | freeable; per instance the platform **keeps** the image in service, the `-prev` of a rebuild, and the image of the previous version (D2) |
| **C — without an instance** | `oaap-app/*` images no registered instance (running, sleeping, rehearsal) uses | freeable after a grace (D6) — a removed app or an abandoned try |
| **D — foreign** | images the platform did not build (not `oaap-app/*`, not the platform's own) | **never** automatically; listed with size and age, removable one by one by the `server_admin` (D3) |
| **E — data** | volumes, instance storage, backups, retained packages | **never** by this measure |

A container of a registered instance is never removed, stopped or not
(a sleeping instance is a stopped container, RFC-0059). The platform's own
images (gateway, identity, portal, broker, …) are kept in the version in
service and the previous one, like class B.

## 3. What a run does

1. Read the registry: every instance, its services, their image in service,
   `-prev`, and the previous version's image (from the retained package's
   version list).
2. Compute the candidates per class; never one in use by any container.
3. Remove them (`docker rmi` per image — refuses on its own what is in use;
   `docker builder prune`, `docker image prune` for dangling layers).
4. Record one audit line: who or what started it, per class the count and the
   bytes, the disk before and after.
5. A dry run (`--dry-run`, the portal's preview) does steps 1–2 and says what
   would go and how much.

## 4. When it runs

### 4.1 Nightly (D1)

In the node's care window after the backup: classes A, B, C. Nothing to
confirm, nothing mailed; the weekly report gets a line "Platz freigegeben:
X GB in N Läufen".

### 4.2 On pressure (D5)

When `disk.full` (warning) or `disk.trend` opens, the node runs at once with
A, B, C — before the mail goes out — and the mail says what was freed and
whether that was enough ("nach dem Aufräumen 81 %, Platte voll in 9 Tagen").
Still above the threshold afterwards: the mail lists class D by size, so the
`server_admin` sees what only a human may remove.

### 4.3 By hand

- **Portal, host care, page "Platz"** (`server_admin` only): the disk now, the
  growth of the week, per class what can go and how much; a button "Jetzt
  freigeben" (A, B, C, after the same preview); class D as a list with size,
  age and a button per image, each asking once more.
- **CLI:** `oaap care space [--dry-run] [--class A,B,C]`, `oaap care space rmi
  <image>` for one foreign image.

## 5. Who may do what

| Who | May |
|---|---|
| the node (job) | classes A, B, C — nightly and on pressure |
| `server_admin` | see everything; start a run; remove a class-D image one by one |
| `tenant_admin` | nothing — images are the node's, shared by all tenants |

## 6. Security requirements

1. No rule ever removes a volume, instance storage, a backup or a retained package.
2. No run removes an image a container uses or the image a registered instance needs to start (in service, `-prev`, the kept previous version).
3. Class D only by a person, one image at a time, audited with name and size.
4. A run is idempotent and safe to interrupt: it removes, never rewrites.
5. A run never runs during a deploy or rebuild of the same node (the deploy lock).

## 7. Stages

| Stage | What | Measured by |
|---|---|---|
| **1** | `oaap care space [--dry-run]`, classes A–C, audit, nightly job, line in the weekly report | `oaap-test`: three versions of one app installed, run, the two kept and the rest gone; a sleeping instance and a rehearsal untouched; a foreign image untouched |
| **2** | portal page "Platz", class D one by one | `oaap-test` as `server_admin`; bait: `tenant_admin` 403, an image in use refused |
| **3** | the pressure run of §4.2, coupled to `disk.full`/`disk.trend` | `oaap-test`: a disk filled on purpose (a file), run before the mail, mail with what was freed |
| **4** | journald capped at 2 GB by the host (D4) | a node after `oaap update` |

## 8. Not part of this RFC

Volumes and data of apps; a quota per tenant; deduplicating images across nodes
(a registry, RFC-0050).

## 9. Decisions (Jörg, 2026-11-24)

- **D1 — A nightly job frees classes A–C without asking?** **Decided: yes**
  (as recommended). All three can be rebuilt (cache) or built again from the retained
  package; a node must not fill itself up by doing its job.
- **D2 — How many versions per instance stay?** **Decided: the one in
  service, the `-prev` of a rebuild, and the previous version** (as recommended). The previous
  version is the fast way back after an update; older ones come back from the
  retained package (four kept, F6), just slower.
- **D3 — Foreign images only by a person?** **Decided: yes, one by one,
  in the portal and on the command line** (as recommended). F8: the platform cannot judge an 85 GB
  download.
- **D4 — Cap journald on the host?** **Decided: yes, 2 GB**
  (`SystemMaxUse=2G`; recommended was 1 GB — more history for finding faults),
  set by install and `oaap update` in a drop-in file.
- **D5 — Run on pressure before mailing?** **Decided: yes** (as recommended), at
  `disk.full` warning and `disk.trend`; the mail then says what remained.
- **D6 — Grace for images without an instance (class C)?** **Decided:
  7 days** (as recommended) — long enough to reinstall a removed app the same week without a
  build.

## Deutsche Zusammenfassung

**Worum es geht:** Ein Knoten sammelt Images, die er nicht mehr braucht. Jede
neue Version einer App baut ein neues Image, das alte bleibt liegen. Auf
oaap-demo waren das in einer Woche +101 GB, vor allem zehn Versionen von
webtop zu je 13 GB. Von Hand aufgeräumt wurden heute 53 GB (58 % → 45 %).
Dieser RFC macht daraus eine Pflegemaßnahme der Plattform.

**Was weg darf (Klassen):** A Zwischenspeicher (Build-Cache, verwaiste
Schichten) immer; B alte Versionen einer App – es bleiben das laufende Image,
der Vorgänger eines Neubaus und die vorige Version als schneller Rückweg, alles
Ältere lässt sich aus dem aufbewahrten Paket neu bauen; C Images ohne Instanz
nach einer Frist; D fremde Images (z. B. das SAP-Trial mit 85 GB) **nie
automatisch**, nur einzeln durch den Server-Admin; E Daten (Volumes,
Speicher, Sicherungen, Pakete) **nie**.

**Wann:** nachts im Pflegefenster nach der Sicherung (A–C); bei Druck –
wenn „Platte fast voll“ oder die neue Vorhersage „voll in …“ anschlägt –
sofort vor der Mail, und die Mail sagt, was es gebracht hat; von Hand im
Portal (Seite „Platz“ in der Serverpflege, nur Server-Admin, mit Vorschau)
und per `oaap care space [--dry-run]`.

**Entschieden (24.11., D1–D6):** nächtlicher Lauf ohne Rückfrage und bei Druck
vor der Mail; es bleiben laufendes Image, Vorgänger und vorige Version;
fremde Images nur von Hand, Images ohne Instanz nach 7 Tagen; journald auf
**2 GB** begrenzt (statt der empfohlenen 1 GB). Gebaut ist noch nichts.

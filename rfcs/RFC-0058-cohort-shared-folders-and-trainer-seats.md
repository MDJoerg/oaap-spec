# RFC-0058: Cohort Shared Folders and Trainer Seats

- **Status:** **Accepted (2026-10-15)** — Jörg took D1–D6 as recommended.
  Nothing built; the six cases of §3 are measured first (D6).
- **Date:** 2026-10-15
- **Authors:** Jörg (the need: trainers keep course material current *during*
  a course; participants share a working folder), Claude (analysis, write-up)
- **Depends on:** RFC-0046 (the cohort), RFC-0034 §4 (storage bound as a file
  system), RFC-0016 (one network per instance), RFC-0029 (backup),
  RFC-0030 D4 (no timers on instances)
- **Changes:** `oaap.apps.runtime` (storage entries: a *shared* mount, a
  *read-only* mount; cohort template: `shared_storage`, `trainers`)
- **Origin:** `program/schulungsarbeitsplatz-webtop-2026-10-14.md`, stage 3;
  the Brandeis webtop project (`webtop-schulung`), which has two folder
  levels and trainer desks today
- **Language:** English per ADR-0003; German summary at the end.

## Summary

A cohort seat today owns its storage alone: `material` is **a copy per seat**
(RFC-0046 §2) and every seat is a participant. Two things a real course needs
are missing:

1. **Shared folders.** One directory for the whole cohort, mounted into every
   seat — *read-write* for a common working folder ("Gemeinsam"), or
   *read-only* for the course material ("Schulung") that the trainers keep up
   to date while the course runs.
2. **Trainer seats.** Seats from the same template and image, in a trainer
   group, that may write the material and see all seats of the cohort.

Both are small additions to the cohort template and one new capability in the
runtime: a storage entry that is owned by the cohort, not by one instance.

## 1. Measured starting point

On `oaap-test` (2026-10-15, webtop 0.1.7, a two-seat cohort from
`oaap-apps/kohorten/webtop-kurs`):

- the material is root-owned and **not** writable for the seat user
  (`Permission denied`) — the read-only side of the idea already works *per
  copy*;
- each seat has its own `/schulung`; updating the material means
  `oaap cohort material update` per seat;
- a seat's idle memory is 256–372 MiB, so N seats of one node are bounded by
  the limits, not by the shared folder.

Unmeasured: how a cohort-owned mount behaves under redeploy, reset and backup
(§3 names the cases).

## 2. Proposal

### 2.1 Shared storage in the template

```yaml
shared_storage:
  - name: gemeinsam          # read-write for every seat
    mount: /gemeinsam
    access: rw
  - name: schulung           # trainers write, participants read
    mount: /schulung
    access: ro               # for participant seats; trainer seats get rw
    source: material/        # initial content, directory next to the template
```

The platform creates one directory per name in the cohort's place
(`<tenant>/cohorts/<cohort>/shared/<name>`), owned by the image's user
(RFC-0046 seeds the same way), and binds it into every instance of the
cohort. `source:` fills it once at `create`; `material update` replaces the
**content**, never the directory (a bind mount follows the inode — a deleted
and recreated folder leaves running containers looking at an empty old one).

### 2.2 Trainer seats

```yaml
trainers: 2                  # or `trainer_names: [anna, ben]`
```

A trainer seat is an ordinary seat (same apps, same limits) with:

- the group `<cohort>-trainer` in addition to its own seat group;
- every `shared_storage` entry mounted **read-write**;
- visibility on *all* seats of the cohort (the trainer may open a
  participant's desktop; the seat group keeps participants apart from each
  other);
- no automatic `tenant_admin` role — trainers are users of the tenant, not
  its administrators (D4).

### 2.3 What stays

`reset` of a seat removes only that seat's storage, never a shared folder.
`stop`/`start` act on instances, never delete a shared folder. `remove
--purge` of the cohort deletes shared folders with the cohort, after naming
them (RFC-0046 §6.3 pattern).

## 3. Cases that must be measured before this is built

| Case | Question |
| --- | --- |
| Redeploy of one seat | does the shared mount survive, same inode? |
| `reset` of one seat | is the shared folder untouched? |
| Backup (RFC-0029) | the shared folder belongs to no instance — which archive carries it? |
| Rehearsal (RFC-0030) | does a copy of a seat copy a shared folder it does not own? |
| Two writers | `gemeinsam` rw from N containers: file locking, same user id, no platform guarantee |
| Cohort `remove` | with seats already removed by hand |

### 3.1 Result (2026-10-15, `oaap-test`, before any build)

Measured with two containers of the webtop image on a host directory
(`--user 911`), and by reading `oaap-reference/platform/appctl.py`
(`recreate_instance_containers`, `_cohort_reset`, `_cohort_material`,
the tenant archive, `create_rehearsal`):

| Case | Result | How |
| --- | --- | --- |
| Read-only for one reader | A writes, B (`:ro`) reads it; B's write fails with `Read-only file system` | measured |
| Recreate a container | content is still there (the data is the host directory) | measured |
| Replace content in place | the directory keeps its inode, the reader sees the new file | measured |
| Delete and recreate the directory | the running reader sees an **empty** old directory — the inode trap is real | measured |
| `material update` | `cohort.copy_material(replace=True)` empties the **content** and copies; the directory is kept — the trap is already avoided. It is **not atomic**: a reader can see an empty folder for a moment | code read |
| `reset` of one seat | `remove_instance(…, purge)` removes only the instance directory; a shared directory outside it is untouched | code read, not run |
| Redeploy | every door that recreates a container goes through `recreate_instance_containers`; the mount source is built there from `instance_dir/storage/<name>` (one place). A shared entry must be **recorded on the instance** (like `shm`), or the next restart drops it | code read |
| Node / tenant archive | the tenant archive carries `tenants/<tid>` and `files/<tid>`. A shared directory **below** `tenants/<tid>` would be in every nightly backup — against D5 | code read |
| Rehearsal | a rehearsal extracts the instance subtree from an archive; a shared directory is not in it, so a copy of a seat has no shared mount unless the record is made to carry it. A rehearsal must **not** be given the live shared folder | code read |
| Two writers | same image, same uid in every container, so permissions agree; the platform adds no locking and promises none | not measured, by design |
| Cohort `remove` with seats already removed by hand | not examined | open |

**Consequences for the build:**

1. Put the shared directories **outside** `tenants/<tid>` (proposal:
   `<data>/cohorts/<tid>/<cohort>/<name>`), so D5 holds: neither archive
   carries them. The cohort **`export`** must then copy them — today it
   copies only the template directory, so the export does not contain
   course material that trainers changed.
2. Record shared mounts on the instance and pass them through every door,
   as `shm` is passed.
3. Make `material update` for shared folders **atomic enough**: write to a
   sibling and rename the *content* entries, or document the gap; a trainer
   editing during a lesson is the expected case.
4. Rehearsal of a cohort instance: refuse or drop the shared mount, never
   bind the live folder.

## 4. Decisions for Jörg

| # | Question | Recommendation |
| --- | --- | --- |
| D1 | Is the shared folder part of the cohort (deleted with it) or an independent object with its own life? | Part of the cohort. An independent object needs its own lifecycle, backup rule and permissions — a second RFC; not needed for a course. |
| D2 | Do participants write `gemeinsam` and read `schulung`, trainers write both? | Yes, as in §2.1/§2.2; the access is set by the template, per name and per role. |
| D3 | Initial content: a directory next to the template, or a Git source? | Directory (as RFC-0046 material). Git later, if a course wants a living repository. |
| D4 | May a trainer seat be `tenant_admin`? | No by default; the tenant administrator creates the cohort, trainers are users with wider *visibility* only. |
| D5 | Backup of shared folders (§3): in the tenant archive, in the cohort's export, or excluded? | In the cohort `export` (a template with the content); not in the nightly node backup, because a course is a transient landscape (RFC-0046 lifetime). |
| D6 | Order of work? | Measure §3 on `oaap-test` with the `webtop-kurs` template first (cheap: two seats), then spec 2.x, then build. |

## 5. Not part of this RFC

- A file system *shared between tenants* — the tenant is the boundary.
- A share a participant can *grant* to another participant — that is a file
  service (RFC-0034 stage 1, `oaap.data.files`), not a mount.
- "Show" (a participant presents a web app): stage 4 of the webtop plan.

## Deutsche Zusammenfassung

Heute hat jeder Kursplatz **seine eigene Kopie** des Materials, und alle Plätze
sind Teilnehmer. Ein echter Kurs braucht zwei Dinge: **geteilte Ordner**
(„Gemeinsam“ für alle beschreibbar, „Schulung“ für Teilnehmer nur lesbar und
vom Trainer während des Kurses gepflegt) und **Trainer-Plätze** (aus derselben
Vorlage, beschreiben das Material, sehen alle Plätze, sind aber keine
Mandanten-Verwalter).

Die Laufzeit braucht dafür einen Mount, der der **Kohorte** gehört und in
mehrere Instanzen eingehängt wird (heute gehört ein Speicher genau einer
Instanz), sowie einen nur lesbaren Mount. `material update` ersetzt den
**Inhalt**, nie das Verzeichnis (Inode-Falle des Bind-Mounts).

Nichts ist gebaut. Gemessen ist nur die Ausgangslage auf oaap-test (Material
je Platz, für den Teilnehmer nicht beschreibbar). Sechs Entscheidungen (D1–D6)
warten auf Jörg; die Empfehlung ist: der Ordner gehört zur Kohorte, Trainer
sind Benutzer mit weiter Sicht, nicht Verwalter, und zuerst die Fälle in §3
auf oaap-test messen.

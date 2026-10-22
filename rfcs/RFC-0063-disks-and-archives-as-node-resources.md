# RFC-0063: Disks and Archives as Node Resources — Plugged In by the Operator, Handed to an Instance Folder by Folder

- **Status:** **Accepted (2026-10-22)** — Jörg took D1–D8 as
  recommended the same day. Stage 0 done by hand. **Stage 1 built the
  same day** (reference 0.1.208/0.1.209, `oaap.data.disks` 0.1,
  `oaap.apps.runtime` 0.2.46 §2.26), measured end to end on `oaap-test`
  and on real disks on `oaap-demo` (§11). **Stage 2 built** (reference
  0.1.210, `oaap.data.disks` 0.2 §2.6, §12). Stage 3 not built.
- **Date:** 2026-10-22
- **Authors:** Claude (proposal, measurements on `oaap-test` and `oaap-demo`),
  Jörg (requirement, decides)
- **Depends on:** RFC-0008 (`server_admin`), RFC-0016 (an app does not get
  host reach), RFC-0029 (backup exclusions), RFC-0030 (rehearsal), RFC-0053
  (the vault: removable disks, recognised by UUID, LUKS), RFC-0058 (read-only
  shared mounts recorded on the instance)
- **Changes:** new capability `oaap.data.disks` 0.1; `oaap.apps.runtime`
  (a grant base mounted into the primary service); `oaap.data.backup`
  (grants never archived); `oaap.core.portal` (a node page for disks)

## Summary

The operator plugs a USB disk into a node. Today OAAP does not know the
disk exists. The only way to get its data into an app is a hand-made
mount on the host, and that is lost at the next reboot.

This RFC makes disks a **node resource** with three nouns:

- **Disk:** one recognised device, known by its UUID, with a role:
  - `raw`: as delivered, never written;
  - `work`: the platform may format it.
- **Source:** something on a disk that can be handed out:
  - a **path** (the whole disk or one folder);
  - an **archive** (a tar, zip or compressed file). The platform presents
    an archive as a read-only folder through an index, without
    extracting it.
- **Grant:** a source handed to an instance under a name, either
  read-only or read-write. A tenant can be the target in a later stage.

It is operated by `server_admin` through `oaap disk …` and a node page in
the portal.

The mechanics rest on measurements, not on reading the code (§2). Two of
the measurements change the obvious design:

- **A grant must be set read-only in one mount call.** If a bind mount is
  made first and set read-only afterwards, the host shows `ro`, but a
  running container that sees it through propagation still writes (M13).
- **Never bind a disk or an archive mount straight into a container.** The
  container then keeps the old FUSE process alive and the disk cannot be
  unmounted ("target is busy") until the container is removed (M5b).

Instead, each instance gets one **grant base**. It is an immutable folder
on the system disk, covered at runtime by a read-only tmpfs. Only that
base goes into the container, with `rslave` propagation. The platform
mounts grants into the base and removes them there while the container
runs. An empty base after a reboot cannot be written to, even by root in
the container (M12).

## 1. Why

The first case is a research project on `oaap-demo`, which is in the
intranet:

- One delivered disk holds eight tar archives (302 GB).
- A second disk is the working disk for indexes, extracted text and
  results.
- The analysis runs in a browser desktop (`joerg-desk`, RFC-0058 family).
  Later an app of its own will run in the same tenant.

The data is sensitive. It must stay on the node and leave no copy in any
backup.

The same shape recurs elsewhere:

- a customer hands over a disk with years of scans (Bernd);
- course material for a cohort;
- a media library for the video service (fall A/B, unresolved);
- an import from an old NAS in the home lab.

In all of these, the operator has a disk, and an app needs some part of
it.

OAAP decided twice that **an app does not open a disk**: RFC-0016, and
RFC-0053 D1, where the vault became a platform capability for exactly
this reason. This RFC keeps that decision. The platform holds the disk,
and the app receives folders.

## 2. What was measured (2026-10-22)

All measurements on `oaap-test` (Debian 13, kernel 6.12, Docker 29.7,
util-linux 2.41, ratarmount 1.3.0) used loop devices and synthetic
archives only. The scripts are in `program/messungen/datentraeger-messung-*.sh`.

The real-case figures come from `oaap-demo`. Only metadata of that disk
was read: sizes, formats, timings.

| # | Question | Result |
|---|---|---|
| M1 | Recognise a disk by UUID; LUKS without key | `/dev/disk/by-uuid/` link exists for exFAT and LUKS; the LUKS label is readable without the key; `cryptsetup open UUID=…` with a key file works |
| M2 | Raw exFAT read-only for a container user | `ro` plus `uid=/gid=` mount options map ownership (exFAT has none); the container reads and gets `Read-only file system` on write; `blockdev --setro` holds |
| M2b | Does the kernel write lock follow the disk? | **No, it sticks to the device number.** A reused loop device came up locked. A replugged USB disk gets a new device, so the lock must be set again on every attach. |
| M3 | ratarmount into a container | Without `allow_other`: `Permission denied` for uid 1000. With `allow_other,uid=,gid=`: readable, writing refused. The index is reused, and the raw disk is unchanged. |
| M4 | Archive mounted **after** the container started | Standard bind (`rprivate`): not visible. Bind of the parent with `rslave`: visible at once. |
| M5b | Direct bind of an archive mount, then the archive is unmounted on the host | The container still reads the **old** content. The old ratarmount process stays alive, and the disk below cannot be unmounted ("target is busy") until the container is removed. |
| M7 | ratarmount as a systemd service (`-f`) | Starts, mount appears, an `rslave` container sees it; stop leaves no dead FUSE mount |
| M8 | Nested archive | `--recursive` shows an inner tar as a folder |
| M9 | Grant base per instance (§4.5) | Grants appear and disappear in the running container without restart; the other instance does not see them; the container (even root) cannot unmount or remount them; eject works while containers keep running; replug and re-grant work without restart; `docker restart` keeps them |
| M10 | Idmapped bind mounts | Refused (`invalid argument`) on ext4, exFAT and FUSE in this setup, so not used. ratarmount `uid=/gid=` does the job. |
| M11 | Formats through ratarmount 1.3.0 | tar, tar.gz, tar.bz2, tar.xz, tar.zst, zip and single .gz: **ok**. 7z: **fails** (backend missing). rar: not measured. |
| M12 | Empty grant folder (reboot, Docker starts the container itself) | Immutable base (`chattr +i`): root in the container gets `Operation not permitted`. A tmpfs over it set `ro` after the placeholders are made: `Read-only file system` in a placeholder whose grant is missing. The system disk stays empty. |
| M13 | Read-only flag of a grant made while the container runs | (A) bind, then `remount,bind,ro`: host `ro`, **container `rw` and writable**. (B) `mount -o bind,ro` in one call (util-linux 2.41 uses the fd-based mount API): container `ro`, writing refused. (C) mount privately, then `--move` into the shared base: refused by the kernel. |
| M14 | The host unmounts and remounts a base tmpfs while the container runs | Works when the container was made on the bare folder (the first grant, every reboot): the new tmpfs and its grants arrive. |
| M15 | The container is made while the base tmpfs is already mounted (every later recreate) | Grants still come and go live and new placeholders appear. **But** this container has bound the tmpfs itself, so a host-side unmount and remount of the tmpfs would never reach it. Rule: the tmpfs stays while the instance exists. |

Real case on `oaap-demo`:

| | |
|---|---|
| Disks | two 500 GB 2.5" USB disks, delivered as exFAT; SMART passed, 26 h and 0 h powered on |
| Ports | the raw disk on USB 3 (5 Gbit/s), the work disk on USB 2 (480 Mbit/s): `lsusb -t` makes the difference visible, the page should show it |
| SHA-256 of all 21 files (302 GB) | 54 min, ~93 MB/s average (111 MB/s sustained) |
| Index for eight uncompressed tar archives | 0.2–2.2 s for six of them; 33 s and 152 s for the two with the most entries (14 000 / 49 000 files); 24 MB index in total |
| Size extracted | equal to the archive size (uncompressed tar) |
| Work disk | LUKS2 + ext4 made by hand, key file under `/etc/oaap/disks/` (0400), header backup next to it |

## 3. Nouns and states

### 3.1 Disk

A disk is recorded in `apps/disks.json` when the operator **adopts** it.
The record holds:

- name (the operator's choice, e.g. `rohdaten-1`), UUID (filesystem UUID,
  or the LUKS UUID if encrypted), filesystem, size;
- role `raw` or `work`;
- encryption `none` or `luks` (with the key file path), the adopter, the
  time.

States, shown on the page and in `oaap disk list`:

| State | Meaning |
|---|---|
| `absent` | not plugged in |
| `present` | plugged in, not opened or mounted |
| `open` | mounted under `/srv/oaap/disks/<name>`, archives started, grants mounted |
| `busy` | eject asked, but something still holds it (named) |

A **raw** disk is mounted `ro,noatime,nodev,nosuid,noexec`, and the
kernel write lock is set on the partition and the disk each time (M2b).
The platform never formats, repairs or writes it.

A **work** disk is mounted `noatime,nodev,nosuid`. The platform may format
it (D6).

Recognition is by UUID only, never by `/dev/sdX`. A device that matches no
record is listed as **unknown** with its size, model, filesystem, label
and USB speed. It stays untouched until it is adopted.

### 3.2 Source

A source is either:

- a **path** on a disk (`rohdaten-1:/`, `rohdaten-1:/ordner`), or
- an **archive**: one file on a disk, presented as a folder by ratarmount.

For an archive:

- its index is written to a chosen work disk under `index/`, or to
  `/var/lib/oaap/archive-index/` when no work disk exists. **Never next to
  the archive** (ratarmount's default would write to the raw disk);
- it runs as `oaap-archive@<name>.service` (`ratarmount -f -o
  allow_other,uid=…,gid=…`) and is mounted under
  `/srv/oaap/archives/<name>`;
- the name of a source is the operator's word. The file name inside the
  disk is shown only to `server_admin` (D7).

`oaap disk scan <disk>` lists the candidate archives on a disk by
**number, size and detected format**. Format is detected from the header
bytes, never with `file`, which prints names embedded in gzip headers.
`oaap disk archive add <disk> <number|path> --name …` creates the source.

### 3.3 Grant

A grant hands a source to an instance under a **grant name**, `ro` or `rw`:

- a source on a `raw` disk can only be granted `ro`;
- an archive is always `ro`;
- `rw` is allowed only for a path on a `work` disk.

Grants are recorded on the instance, like `shared_mounts` (RFC-0058) and
`resources`. Every door that recreates the container reads them from the
registry first.

A grant may be **optional**. Then the instance starts without it, and an
empty placeholder is all that shows.

## 4. Mechanics

### 4.1 Paths

```
/srv/oaap/disks/<disk>                 mounted disks
/srv/oaap/archives/<source>            ratarmount mounts
/srv/oaap/grants/<instance-id>/        grant base: immutable dir, tmpfs at runtime
/srv/oaap/grants/<instance-id>/<grant> one bind per grant
```

All of this is **outside** `/var/lib/oaap`. The node archive and the
tenant archive tar an explicit list of paths below the data directory, so
nothing here can be included.

*Changed while building stage 1 (2026-10-22):* no `--one-file-system` as
a second guard. A node whose `files/` or `tenants/` lies on a separate
mount would silently lose that data from every backup. The guard would
protect against a case the paths already exclude, and break a real one.

The instance id is used, not the name, so a rename does not move mounts
(RFC-0026).

### 4.2 Grant base (M9, M12)

At instance install, the platform creates `/srv/oaap/grants/<id>/` empty
and sets it immutable (`chattr +i`). The primary service gets:

```
--mount type=bind,src=/srv/oaap/grants/<id>,dst=/oaap/disks,bind-propagation=rslave
```

The container sees `/oaap/disks` before any disk is there, also when
Docker starts it at boot.

When the platform opens the instance's grants, it does this in order:

1. `mount -t tmpfs -o size=1m,mode=0755` over the base, `--make-shared`;
2. one placeholder folder per grant, then `remount,ro` of the tmpfs;
3. per grant **one** call `mount -o bind,ro <source> <base>/<grant>`, or
   `mount -o bind` for `rw` (M13 B);
4. **check from inside**: read `/proc/<container-pid>/mountinfo` and
   compare each grant's flag with the record. A mismatch revokes the grant
   and reports it. This also catches a future util-linux that falls back
   to two calls.

Revoking a grant is `umount <base>/<grant>`, without a restart. What the
container may hold open at that moment is its own business. The platform
does not wait.

### 4.3 Start rule

A grant is **mandatory** unless it is marked optional. Before
`recreate_instance_containers` or `wake_instance` starts an instance with
a mandatory grant whose source is not mounted, the platform refuses with
`DiskAbsent` and names the disk.

The start Docker does on its own at boot bypasses this check. M12 makes
it harmless: the app sees empty, unwritable placeholders until the disks
are open, and the boot unit (§4.6) opens them.

The platform never creates a missing mount point on the system disk. This
is the idea behind `ensure_idp_dir`, and today's mount loop does the
opposite (`os.makedirs` on the host side).

### 4.4 Eject

`oaap disk eject <disk>` does, in order:

1. unmount every grant of every source on the disk, in every instance;
2. stop the archive services of the disk;
3. unmount the disk; for LUKS, `cryptsetup close`;
4. report **safe to unplug**.

The containers keep running (M9). A step that fails leaves the disk in
`busy` and names who holds it (`fuser -m`). Nothing is forced. A lazy
unmount is never used, because it reports success while the disk is
still in use.

Pulling the cable without an eject is not measured yet. It is measured
on real hardware before stage 1 is called done.

### 4.5 Encryption and formatting

- **Raw disks are never touched.** They stay in the format they were
  delivered in. Re-encrypting a disk in place destroys the claim that it
  was not changed, and it is a real risk to the data.
- **Work disks:** `oaap disk format <disk> --luks` does LUKS2 + ext4. It
  writes a random key file `/etc/oaap/disks/<name>.key` (0400) and a header
  backup next to it. It then **tells the operator to add a passphrase of
  their own** (`cryptsetup luksAddKey`, typed by the person, never by the
  platform). Without that passphrase, the work disk depends on the node's
  system disk.
  - Formatting requires the role `work`, and either an empty filesystem or
    the disk's UUID typed back as confirmation (D6).
  - `--plain` (ext4 without LUKS) exists, but the page recommends LUKS
    whenever a source is sensitive.
- An already-encrypted work disk is adopted with `--luks-key <file>`
  without formatting. That is how today's manual disk on `oaap-demo` moves
  into stage 1.

### 4.6 Boot and hot-plug

**Stage 1** has one unit, `oaap-disks.service` (after `local-fs.target`).
It opens every adopted disk that is present: LUKS with its key file, then
the mount, the write lock for `raw`, the archive services, and the grant
bases of all instances. It runs at boot and on `oaap disk open`.

**Stage 3** adds a udev rule. It starts `oaap-disk-attach@<uuid>.service`
when a known UUID appears. An unknown disk only raises a notice on the
page, and nothing is mounted until a person adopts it.

### 4.7 Integrity

`oaap disk verify <source>` hashes every file of a source with SHA-256,
at low IO priority as a service. It writes the list to a work disk under
`integritaet/` and compares it with the previous list.

The output shows counts, the duration and "equal / N different", never
file names (D7). On a raw disk the first run is the reference. A later
run that differs is an alarm on the page.

The list stays on the node unless the operator copies it away. Its value
lies in also existing somewhere else.

### 4.8 Ownership inside the container

- **Archives:** `uid=/gid=` of the instance's app user, set on the
  ratarmount service.
- **exFAT/NTFS paths:** the `uid=/gid=` mount options apply to the whole
  disk. If two instances with different users get paths of the same
  disk, the disk is mounted for the platform user, and each grant is `ro`
  with read for all (`fmask=0222`).
- **ext4 work disk:** `chown` of the granted folder to the app user, the
  same as own storage.

Idmapped mounts are not used (M10).

### 4.9 Rehearsal, backup, tenant archive, removal

- **Rehearsal (RFC-0030):** a rehearsal copy gets **no** grants. Its base
  stays empty, just as it gets no shared folder. A rehearsal must never
  reach the live sources.
- **Backup and tenant archive:** never include grant content (§4.1). The
  tenant archive records each grant as metadata only (grant name, source
  name, `ro|rw`), so a restore can say which grants are missing.
- **Removal:** removing an instance revokes its grants and removes its
  base. Removing a source refuses while grants exist, unless `--revoke`
  is given.

### 4.10 Audit

The node audit log records, with actor and time: adopt, forget, open,
eject, format, archive add/remove, grant, revoke, verify and any mismatch.

## 5. CLI (`oaap disk`)

| Command | Does |
|---|---|
| `oaap disk list` | adopted and unknown disks, state, size, free, USB speed, SMART summary |
| `oaap disk adopt <uuid> --name N --role raw\|work [--luks-key F]` | records a disk |
| `oaap disk forget <disk>` | removes the record (refuses while sources exist) |
| `oaap disk open\|eject <disk>` | §4.6 / §4.4 |
| `oaap disk format <disk> --luks\|--plain [--confirm-uuid U]` | §4.5, `work` only |
| `oaap disk scan <disk>` | candidate archives: number, size, format (§3.2) |
| `oaap disk archive add <disk> <nr\|path> --name S [--index-on <work-disk>] [--recursive]` | archive source |
| `oaap disk path add <disk> <path> --name S` | path source |
| `oaap disk source list\|remove <S>` | sources, with grants |
| `oaap disk grant <S> --instance I --as G [--rw] [--optional]` | §4.2 |
| `oaap disk revoke <G> --instance I` | §4.2 |
| `oaap disk verify <S>` | §4.7 |

The commands are root-only, like the rest of `appctl`. `list` and
`source list` are added to the read-only list.

## 6. Portal: the node page "Datenträger" (`server_admin`)

The page follows the existing spool pattern. The portal writes a request
into the deploy spool, and `oaap-deployd` checks the role again on the
host and runs it. The spool actions are `disk-adopt`, `disk-open`,
`disk-eject`, `disk-format`, `disk-archive-add`, `disk-grant`,
`disk-revoke` and `disk-verify`.

The page has five parts:

- **Disks:** state, role, encryption, size and free space, USB speed (with
  a warning on USB 2 for a disk in use), SMART. An **adopt** button for an
  unknown disk, and **eject** with "safe to unplug" or the name of who
  holds it.
- **Sources:** per disk the archives and paths, index size, last
  verification.
- **Grants:** per source the instances with `ro|rw` and an "arrived in the
  container" check (§4.2 step 4). Grant and revoke from a list of
  instances.
- **Formatting:** only for `work`, behind the UUID confirmation.
- **Instance page:** a read-only line "Datenträger: G1 (ro), G2 (rw)" in
  the administration tab.

A tenant view (`tenant_admin` sees the grants of the tenant's instances)
comes with stage 3.

## 7. Stages

| Stage | Content |
|---|---|
| **0 — by hand** (done 2026-10-22) | `oaap-demo`: raw disk `ro` + write lock, work disk LUKS2 + ext4, SHA-256 of all files, eight archives through ratarmount with indexes on the work disk. Not persistent and not granted. Measurements M1–M13 on `oaap-test`. |
| **1 — CLI** | `oaap.data.disks` 0.1, `disks.json`, adopt/list/open/eject/format/scan, archive and path sources, grants to instances (§4.2–4.4), the start rule, `oaap-disks.service`, audit. Measured on `oaap-test` with loop devices, then the manual setup on `oaap-demo` adopted without formatting, one archive granted to `joerg-desk`, a reboot and a pulled cable. |
| **2 — Portal** | §6 |
| **3 — Tenant and hot-plug** | grants to a tenant (its admin attaches them to the tenant's instances), udev, `verify` with history on the page |

## 8. Not part of this RFC

- **An egress rule per tenant** ("this tenant's data does not leave the
  node or the LAN", enforced at the AI gateway and the instance network).
  The same case raised it, but it has its own idea entry (I-34).
- **Network shares** (NFS, SMB) and S3 as sources. The model fits: a share
  would be a disk with a different opener. Not now.
- **Writing into archives, deduplication, snapshots.**
- **Parsing and indexing the content** (mail boxes, documents, OCR). That
  is the app's work on the folders it receives.
- **7z and rar** until a ratarmount backend is measured.

## 9. Security requirements

- An app MUST NOT receive a device, a raw disk mount or a FUSE mount
  directly. It receives only its grant base.
- A `ro` grant MUST be mounted `ro` in a single mount call. Its flag MUST
  be checked inside the container after mounting, and a mismatch MUST
  revoke the grant.
- A `raw` disk MUST be mounted read-only with the kernel write lock set
  at every attach. It MUST NOT be formatted, repaired or written by the
  platform, and no index may be written to it.
- The platform MUST NOT create a missing mount point or grant folder on
  the system disk. Grant bases MUST be immutable on the system disk.
- Grant content MUST NOT enter any backup, tenant archive or rehearsal.
- A disk MUST be recognised by UUID only.
- Key files MUST be root-only (0400). The platform MUST NOT set or know
  the person's passphrase.
- Every state change MUST be audited with its actor. The portal path MUST
  re-check `server_admin` on the host.

## 10. Decided (2026-10-22, D1–D8 as recommended)

| | Question | Decision |
|---|---|---|
| **D1** | Platform capability or app? | **Platform**, like the vault (RFC-0053 D1). A disk needs host root, and RFC-0016 stays shut. |
| **D2** | Grant target in stage 1 | **Instances only.** Tenants in stage 3, once the instance path is measured. |
| **D3** | Where grants appear in the container | **One fixed base `/oaap/disks/<grant>`.** A manifest may later declare which grant names an app expects, but stage 1 needs no manifest change. |
| **D4** | Grant and revoke live, or by recreating the container | **Live** through the grant base (M9). A recreate per grant is what RFC-0058 does, and it would restart a desktop in use. |
| **D5** | Raw disks | **Never touched**: `ro` + write lock, no format, no encryption afterwards. Its integrity is shown by `verify`. |
| **D6** | Formatting a work disk from the portal | **Allowed**, only for role `work`, only when empty or with the UUID typed back. LUKS is the default. |
| **D7** | File names inside a source (archive names, hash lists) in CLI and portal | **Numbers, sizes and formats by default.** Names only on an explicit "show names" by `server_admin`, never in the audit log. |
| **D8** | Today's manual setup on `oaap-demo` | **Adopt it in stage 1 without formatting** (work disk with its existing key file). Until then it stays as it is, not persistent. |

## 11. Stage 1 as built (2026-10-22)

It was built as proposed, except for these changes, each found while building or measuring:

| | Change | Why |
| --- | --- | --- |
| 1 | No `--one-file-system` on the backup `tar` calls (§4.1) | It would silently drop a separately mounted `files/` or `tenants/` from every backup. The paths already keep `/srv/oaap` out. |
| 2 | `format` always needs `--confirm-uuid`, also on an empty disk (§4.5) | Deciding "empty" means mounting a disk that is about to be erased. Typing the UUID costs a line. |
| 3 | `grant --rw --owner UID` | `webtop` (linuxserver) starts as root and drops to uid 1000. The image's user is 0, and the folder was not writable for the app (measured). |
| 4 | The base tmpfs is never unmounted while the instance exists (M14/M15) | A container made against a mounted tmpfs binds the tmpfs itself, and a remount would not reach it. |
| 5 | Archives stop by unmounting first, then the unit | Stopped by SIGTERM, ratarmount 1.3.0 exits 1 and the unit stays `failed`. |
| 6 | `disks.json` root only (0600), `disk list` needs root | A source's path is a file name on the disk (D7), and the portal container reads `apps/`. |
| 7 | Loop devices count as disks; mounted ones are hidden from "not adopted" | Image files attached on purpose (and the tests), not snaps. |
| 8 | ratarmount runs with `-d 0` (0.1.209) | When it builds an index, its default level writes the archive's path, a file name, into the journal (measured with test data). Found while adopting the disks on `oaap-demo`, where all eight indexes were reused and nothing was written. |

Measured end to end on `oaap-test` against the real instance `webtop`:

- adopt, format (LUKS), open, scan, three sources, three grants;
- the first grant recreated the container once, later grants arrived without a restart;
- reads as uid 1000, also of a 0600 root file inside the tar;
- `ro` refused writing, the container flags matched, no disk or archive in the container;
- revoke without restart, eject with the container running, the refused restart left the container in place, reopening brought the grants back without a restart;
- `verify` twice, `--status` "unchanged";
- a reboot reproduced by stopping the container, losing the host mounts and starting it again: the bare base was not writable for root, and `oaap-disks.service` restored both grants;
- clean-up left nothing.

Measured on `oaap-demo` the same day (real USB disks, CURRENT_STATE 350): a grant to `joerg-desk`; a real reboot, after which `oaap-disks.service` restored disks, archives and the grant by itself while the device names had swapped; and a pulled cable, unintentionally on both disks. The platform does not notice a pull by itself: stale mounts stay and the app gets I/O errors until `oaap disk eject`, which also cleans up dead devices. After replugging, `open` brought the grant back without a restart. Stage 3 should eject on the udev remove event.

## 12. Stage 2 as built (2026-10-22)

The page follows §6, except for these changes:

| | Change | Why |
| --- | --- | --- |
| 1 | One spool action `disk` with an op, not eight action names | The jobs of the management API already work this way (cohort, tenant-build): one result file per job, one place where the role is checked. |
| 2 | A ninth op, `scan` | The page adds an archive by its number, and a number needs a scan. The scan with its names is kept root only (`disk-scan.json`, 0600); the view gets numbers, sizes and formats. |
| 3 | The page shows no file name at all, not even on request | D7 allowed "show names" for `server_admin`. On the page a name would pass through the spool and a file the portal reads. `scan --names` at the node is the one place. |
| 4 | `forget`, `path add` and `source remove` stay on the command line | A path is a name; the other two are rare and easy to undo by hand. |
| 5 | Adopting a LUKS disk on the page needs its key file at the node first | The page never takes a key or a passphrase. |
| 6 | The view shows `stale`: mounted while the device is gone | Measured with the pulled cable (§11). The platform still does not act on it (stage 3); the page says so and offers `eject`. Mounts are read from the kernel's table, because `stat` on a dead mount fails. |
| 7 | SMART is not on the page | Stage 1 has no SMART either. `smartctl` stays a check by hand. |

The view (`disk-view.json`, 0644) is written by every disk command and by the minute timer, the timer only where `disks.json` or the view already exists. The first run of the suite found that the timer had asked every node, also one without disks, for its block devices (`test_wireguard_access.py`, whose fake allows no unexpected command). A job's answer is the command's output without journal lines, because a journal line may name a file.

## Deutsche Zusammenfassung

Steckt der Betreiber eine USB-Platte an einen Knoten, weiß OAAP davon
heute nichts. Die Daten erreichen eine App nur über ein von Hand
gemachtes Einhängen auf dem Host, und das ist beim nächsten Neustart weg.

Der RFC macht Platten zu einer **Ressource des Knotens**, mit drei
Begriffen:

- **Datenträger:** eine erkannte Platte, an ihrer UUID wiedererkannt,
  mit einer Rolle:
  - `raw`: so, wie sie geliefert wurde, wird nie beschrieben;
  - `work`: die Plattform darf sie formatieren.
- **Quelle:** ein Pfad auf der Platte, oder ein **Archiv**, das die
  Plattform mit einem Index als nur lesbaren Ordner zeigt, ohne es zu
  entpacken.
- **Freigabe:** eine Quelle, die eine Instanz unter einem Namen bekommt,
  `ro` oder `rw`.

Bedient wird das von `server_admin` über `oaap disk …` und eine Seite
„Datenträger“ im Portal.

**Gemessen** (oaap-test mit künstlichen Platten, oaap-demo nur
Metadaten). Zwei Befunde ändern das naheliegende Design:

- **Eine Schreibsperre muss in einem einzigen Aufruf gesetzt werden.**
  Wird erst eingehängt und dann auf `ro` gestellt, zeigt der Host `ro`,
  der laufende Container schreibt trotzdem (M13).
- **Nie eine Platte oder ein Archiv direkt in einen Container reichen.**
  Der Container hält sonst den alten Prozess am Leben, und die Platte
  lässt sich nicht aushängen (M5b).

Daher bekommt jede Instanz einen **Freigabe-Ordner**: auf der
Systemplatte unveränderlich, zur Laufzeit von einem schreibgeschützten
tmpfs überdeckt, mit `rslave` in den Container gereicht. Freigaben
kommen und gehen ohne Neustart (M9). Ein leerer Ordner nach einem
Neustart ist auch für root im Container nicht beschreibbar (M12).

Weitere Ergebnisse:

- **Formate:** tar, tar.gz/bz2/xz/zst, zip, einzelne .gz und
  verschachtelte Archive gehen; 7z geht nicht.
- **Reale Zahlen auf oaap-demo:** Index der acht Archive in 0,2 bis
  152 Sekunden, zusammen 24 MB. Prüfsummen über 302 GB in 54 Minuten.

**Stufen:**

- **0:** von Hand, heute erledigt.
- **1:** Kommandozeile, Startregel, Boot-Dienst; danach wird die
  Handlösung auf oaap-demo übernommen.
- **2:** Portal.
- **3:** Freigaben an Mandanten, automatische Erkennung beim Anstecken,
  Prüfsummen mit Verlauf.

**Entschieden (22.10., alle wie empfohlen):**

- **D1:** Plattform statt App.
- **D2:** In Stufe 1 nur an Instanzen freigeben.
- **D3:** Fester Ort `/oaap/disks/<Name>` im Container.
- **D4:** Freigeben ohne Neustart.
- **D5:** Rohdatenplatten werden nie angefasst.
- **D6:** Formatieren im Portal nur für Arbeitsplatten, mit Bestätigung
  der UUID, LUKS als Standard.
- **D7:** Dateinamen nur auf ausdrückliche Anforderung.
- **D8:** Die Handlösung wird ohne Neuformatieren übernommen.

**Stufe 1 gebaut (22.10.):** Referenz 0.1.208, `oaap.data.disks` 0.1.
Auf oaap-test mit Loop-Platten an der echten Instanz `webtop` von Anfang
bis Ende gemessen. Sieben Abweichungen stehen in §11. Die wichtigsten:

- **Kein `--one-file-system`** in der Sicherung, weil es getrennt
  eingehängte Daten still verlieren würde.
- **`--owner` für `rw`-Freigaben**, weil Webtop als root startet und erst
  danach zum Benutzer 1000 wechselt.
- **Das tmpfs eines Freigabe-Ordners bleibt**, solange die Instanz
  existiert. Sonst erreicht ein Neueinhängen einen schon laufenden
  Container nicht (M14/M15).

Am selben Tag auf oaap-demo mit echten USB-Platten gemessen:

- Ein Neustart stellt alles von selbst wieder her.
- Ein gezogenes Kabel merkt die Plattform nicht. `eject` räumt danach
  auf.

**Stufe 2 gebaut (22.10.):** Referenz 0.1.210, `oaap.data.disks` 0.2.
Die Seite „Datenträger“ im Portal liest eine Ansicht ohne Pfade und ohne
Dateinamen. Jede Schaltfläche stellt einen Auftrag `disk`, und der
Knoten führt denselben Befehl aus wie die Kommandozeile. §12 nennt
sieben Abweichungen von §6:

- **Ein Auftragstyp mit Unteraktion** statt acht Namen.
- **„Durchsuchen“ als neunte Aktion**, damit ein Archiv über seine
  Nummer angelegt werden kann.
- **Gar keine Dateinamen auf der Seite**, auch nicht auf Anforderung.
  Die zeigt nur `scan --names` am Knoten.
- **Drei Befehle bleiben auf der Kommandozeile:** Vergessen,
  Ordner-Quelle und Quelle entfernen.
- **Eine LUKS-Platte übernimmt die Seite nur**, wenn ihr Schlüssel schon
  am Knoten liegt.
- **Die Seite zeigt eine „verwaiste“ Einhängung** nach gezogenem Kabel.
- **Kein SMART** auf der Seite.

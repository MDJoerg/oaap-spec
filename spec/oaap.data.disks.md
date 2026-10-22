# oaap.data.disks — Disks and Archives as Node Resources

- **ID:** `oaap.data.disks`
- **Version:** 0.1
- **Maturity:** draft. 0.1 is RFC-0063 stage 1 and only that: the
  command line, the start rule and the boot unit. The portal page is
  stage 2. Grants to a tenant and recognition at hot-plug are stage 3.
  Pulling the cable without an eject is not yet measured on real
  hardware.
- **Based on:** RFC-0063 (D1–D8), RFC-0053 (removable disks by UUID,
  LUKS), RFC-0058 (read-only mounts recorded on the instance), RFC-0016
  (an app gets no host reach), RFC-0030 (a rehearsal), `oaap.apps.runtime`
  2.26 (the grant base in the container)

## 1. Purpose

The operator plugs a disk into a node. This capability lets the
platform hold that disk and hand parts of it to app instances, folder by
folder. The app never opens the disk.

It has three nouns:

- **Disk:** a device known by its UUID, with a role. `raw` means as
  delivered and never written. `work` means the platform may format it.
- **Source:** a path on a disk, or an archive on a disk shown as a
  read-only folder through an index.
- **Grant:** a source handed to an instance under a name, `ro` or `rw`.

## 2. Interface

### 2.1 Records

`<data>/apps/disks.json` (0600, root only) holds `disks` and `sources`:

- **disk:** `name`, `uuid`, `role`, `encryption` (`none` | `luks`),
  `key` (path of a root-only key file), `fstype`, `size`, `label`,
  `model`, `adopted`, `by`;
- **source:** `kind` (`archive` | `path`), `disk`, `path` (relative to
  the disk), and for an archive also `format`, `index_on` (a work disk,
  or empty) and `recursive`.

The file is root only because a source's `path` is a file name on the
disk, and a name may be content (RFC-0063 D7).

Grants are recorded on the instance in the registry as `disk_grants`:
`[{grant, source, rw, optional, since, by}]`. A redeploy keeps them, and
a rehearsal never has them.

### 2.2 Host paths

| Path | What |
|---|---|
| `/srv/oaap/disks/<disk>` | a mounted disk |
| `/srv/oaap/archives/<source>` | an archive source (ratarmount, unit `oaap-archive@<source>.service`) |
| `/srv/oaap/grants/<instance-id>/` | the instance's grant base: immutable on the system disk, a read-only tmpfs while grants are open |
| `/srv/oaap/grants/<instance-id>/<grant>` | one bind mount per grant |
| `/etc/oaap/disks/<disk>.key`, `.luks-header` | key file and header backup (0400) |

All of this lies outside `<data>`, which is the platform's data
directory. Neither the node archive nor the tenant archive can carry it.

### 2.3 Commands (`oaap disk`, root)

| Command | Does |
|---|---|
| `list` | adopted disks with state (`absent`, `present`, `open`), size, path, USB speed (a warning below 5000 Mbit/s), free space; then devices not adopted (never the system disk); then sources with their grants |
| `adopt <uuid> --name N --role raw\|work [--luks-key F]` | records a device. A LUKS device needs a key file. It is copied to `/etc/oaap/disks/<N>.key` and tested, and the platform never asks for a passphrase. |
| `forget <disk>` | removes the record; refused while the disk is open or carries sources |
| `open <disk>` \| `open --all` | unlocks (LUKS, `--readonly` for raw), sets the kernel write lock (raw, every time), mounts, starts the archives whose disks are open, and opens the grants of the instances concerned |
| `eject <disk>` | unmounts the grants of every source on the disk (or indexed on it), stops those archives, unmounts the disk and closes LUKS. Never lazy: a busy disk names who holds it and stays mounted. Containers keep running. |
| `format <disk> --luks\|--plain --confirm-uuid U` | `work` only, closed, without sources, the UUID typed back. `--luks` is LUKS2 + ext4 with a fresh 64-byte key file and a header backup, and the output tells the operator to add a passphrase of their own. The new UUID is recorded. |
| `scan <disk> [--names]` | every file, numbered in a fixed sorted order, with size and format from the header bytes. Names only with `--names`. |
| `archive add <disk> <nr\|path> --name S [--index-on W] [--recursive]` | an archive source. The format must be one of `tar`, `gzip`, `bzip2`, `xz`, `zstd`, `zip`. The index goes on the named work disk, else on the only open one, else under `/srv/oaap/archive-index/` with a note. |
| `path add <disk> <path> --name S` | a path source (a folder on the disk) |
| `source list` \| `source remove <S> [--revoke]` | sources; removal refused while granted unless `--revoke` |
| `grant <S> --instance I --as G [--rw [--owner UID]] [--optional]` | records the grant and mounts it. A `rw` folder goes to the image's user, or to `--owner` for an image that starts as root and drops to its own user (linuxserver: 1000). A container made before its first grant is recreated once to get its base, and every later grant arrives without a restart. |
| `revoke <G> --instance I` | unmounts it and drops the placeholder, without a restart |
| `verify <S> [--to W]` \| `verify <S> --status` | SHA-256 of every file of the source as the unit `oaap-disk-verify-<S>`, written to `<W>/integritaet/<S>-<stamp>.sha256`. `--status` prints counts against the previous list (equal, different, new, missing), never names. |

### 2.4 Rules

1. **Recognition by UUID only**, never by device name.
2. **Raw disks** are mounted `ro,noexec,noatime,nodev,nosuid`. ext4 is
   also mounted `noload`, because a read-only mount still replays the
   journal. exFAT, FAT and NTFS get `uid=0,gid=0,fmask=0222,dmask=0222`.
   The kernel write lock is set on the partition and the disk at every
   open, because it sticks to the device number, not to the disk. A raw
   disk that comes up writable is unmounted again. A raw disk is never
   formatted, repaired, re-encrypted or written, and no index is put on
   it.
3. **Work disks** need a filesystem with owners and modes (ext4, xfs,
   btrfs). Otherwise opening is refused with the advice to format.
4. **Grants:** an archive and a source on a raw disk are only `ro`. `rw`
   is only for a path on a work disk, whose folder is then given to the
   app's user.
5. **One mount call per read-only grant:** `mount -o bind,ro`. Binding
   first and remounting read-only afterwards shows `ro` on the host
   while the running container writes (RFC-0063 M13).
6. **Checked from inside:** after mounting, each grant's per-mount flag
   is read from the running container's `/proc/<pid>/mountinfo`. A
   mismatch with the record unmounts the grant and reports it.
7. **The grant base is sealed:** immutable on the system disk before
   anything is mounted on it, and a tmpfs that is read-only except for
   the instant placeholders are made. An empty placeholder cannot be
   written, not even by root in the container (M12). A base that is not
   empty when it is to be sealed is refused.
8. **Start rule:** an instance with a mandatory grant whose source is
   not there is not (re)created, and `wake` does not start it. The
   refusal comes before the old container is removed and names the
   disk. An optional grant shows an empty placeholder instead.
9. **Never a disk or a FUSE mount directly in a container** (M5b). Only
   the instance's base, bound `rslave`.
10. **The base tmpfs stays while the instance exists.** Once mounted,
    it is unmounted only when the instance is removed. A container made
    while the tmpfs is mounted binds the tmpfs itself. If the host then
    unmounted and remounted it, the new one would never reach that
    container (measured 2026-10-22, M14/M15). At a reboot the tmpfs is
    gone and Docker binds the bare, sealed folder (M12).
11. **Rehearsal:** no base and no grant.
12. **Removal** of an instance unmounts its grants and removes its base.
13. **Audit:** adopt, forget, open, eject, format, source add/remove and
    verify go to the node's default tenant. Grant and revoke go to the
    instance's tenant. Every entry carries the actor.

### 2.5 Boot

`oaap-disks.service` (oneshot, after `local-fs.target` and
`docker.service`, enabled by install and by update) runs
`oaap disk open --all`. Docker starts the containers by itself
meanwhile. Their bases stay sealed until the unit has run.

## 3. Configuration

- `OAAP_DISKS_ROOT` (default `/srv/oaap`) and `OAAP_DISKS_KEYS` (default
  `/etc/oaap/disks`), for tests.
- The tools are opt-in: `sudo bash ops/install-disk-tools.sh` installs
  cryptsetup, exfatprogs, fuse3, smartmontools and psmisc, plus
  ratarmount 1.3.0 through pipx (pinned to the version measured).

## 4. Security requirements

The MUSTs of RFC-0063 §9 apply unchanged. In short:

- no device, raw mount or FUSE mount for an app;
- `ro` in one call, and checked inside the container;
- raw disks never written;
- no mount point created on the system disk for an absent source;
- grants in no backup, archive or rehearsal;
- UUID only;
- key files 0400, and the platform never knows a passphrase;
- every change audited with its actor.

## 5. Conformance tests (described)

`test/test_disks.py`, with no Docker, no disk and no root:

- the mount options of each role and filesystem;
- the grant refusals and name rules;
- format detection from header bytes;
- the fixed scan order;
- the per-mount flag read from mountinfo;
- the order of sealing, tmpfs, sharing and `bind,ro` in one call, and
  never `remount,bind,ro`;
- a second open changes nothing;
- the inside check revokes a mismatch;
- revoke removes the placeholder;
- the runtime's `--mount … bind-propagation=rslave` and nothing of the
  disk itself;
- refusal before `docker rm`;
- optional grants;
- rehearsal;
- redeploy keeps the grants, and `wake` asks the start rule.

## 6. Dependencies

`oaap.apps.runtime` 2.26, `oaap.core.tenant` (audit), `oaap.data.backup`
(must not include `/srv/oaap`).

## 7. Maturity

Draft 0.1: the command line only.

- **Stage 2:** the portal page (RFC-0063 §6).
- **Stage 3:** grants to a tenant, udev at hot-plug, and `verify` with
  history on the page.
- **Not measured yet:** a pulled cable without an eject, and a real
  reboot with real disks.

## Deutsche Zusammenfassung

Die Plattform übernimmt eine angesteckte Platte, erkennt sie an ihrer
UUID und gibt Teile davon an Instanzen weiter. Die App selbst öffnet nie
eine Platte. Bedient wird das über `oaap disk …`, als root.

- **Datenträger:** `raw` wird nie beschrieben. `work` darf die
  Plattform formatieren, mit LUKS als Standard.
- **Quelle:** ein Ordner auf der Platte, oder ein Archiv, das
  ratarmount mit einem Index als nur lesbaren Ordner zeigt. Der Index
  liegt auf der Arbeitsplatte, nie neben dem Archiv.
- **Freigabe:** Die Instanz sieht sie unter `/oaap/disks/<Name>`.

Die Regeln aus den Messungen:

- `ro` in **einem** Aufruf, danach im Container nachgeprüft.
- Der Freigabe-Ordner ist versiegelt.
- Fehlt eine Pflicht-Freigabe, startet die Instanz nicht. Das wird
  entschieden, bevor der alte Container entfernt wird.
- Eine Generalprobe bekommt nichts.
- Auswerfen geht bei laufenden Containern und ist nie „lazy“.
- Dateinamen erscheinen nur mit `--names`. Die Datensatz-Datei
  `disks.json` darf nur root lesen.

Noch nicht gemessen: Kabelziehen ohne Auswerfen und ein echter
Neustart mit echten Platten. Das Portal kommt in Stufe 2.

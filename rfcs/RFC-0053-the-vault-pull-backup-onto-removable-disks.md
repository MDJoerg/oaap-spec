# RFC-0053: The Vault — A Pull Backup Onto Removable Encrypted Disks, and the Tenant's Own Copy

- **Status:** Proposed (2026-10-02) — draft for Jörg's decisions D1–D8
  (§8). Nothing built.
- **Date:** 2026-10-02
- **Authors:** Jörg (the need: a "light" off-site backup for a home or a
  workshop — a Raspberry Pi with a USB disk that is only powered when
  needed, encrypted, and swapped weekly for a second disk kept
  elsewhere; and the question whether a customer can do the same for
  their own tenant), Claude (facts measured in the reference, design)
- **Depends on:** RFC-0029 (schedule, generations, D4 "the source knows
  nothing about the puller", D5/D5b the tenant archive and exclusion,
  D6 push mode), `oaap.data.backup` 0.4, `oaap.core.tenant` 1.0 §2.11
  (an empty node adopts a tenant archive), RFC-0022 (tenant as
  boundary), RFC-0016 (app isolation), ADR-0005 (Raspberry Pi is Tier 1
  arm64)
- **Extends:** `oaap.data.backup` (a puller with a removable target),
  `oaap.core.portal` (a page on the pulling node)
- **Driver:** Jörg, 2026-10-02: *„Mir geht es um eine ‚light' Variante
  für zuhause … Die USB-Platte wird aktiviert, wenn wir sie brauchen
  und wir schalten sie wieder ab, wenn das Backup durch ist … mit
  mehreren Platten arbeiten und diese wochenweise tauschen … Der remote
  Knoten soll davon nichts merken."*

## Summary

A node like Bernd's already makes a complete archive every night and
offers it through a door that can do exactly three things: list, give
one checksum, send one archive (RFC-0029, `ops/backup-serve.sh`). This
RFC adds the **other end for the small case**: a second machine — a
Raspberry Pi is enough — that fetches those archives onto a **vault**:
a removable disk that is encrypted as a whole, mounted only for the
minutes of the run, and one of a **set** of such disks that a person
swaps on a fixed day and keeps elsewhere. The node being backed up
needs **nothing new**; the puller is just one more key in its
`authorized_keys`, which RFC-0029 D4 already allows.

The second half answers Jörg's follow-up question: **yes, a tenant can
have its own copy.** The tenant archive of RFC-0029 D5 exists, and since
`oaap.core.tenant` 1.0 an empty node can adopt it — the exit right of
RFC-0041 K6. What is missing is a door that hands *one tenant's*
archives to *that tenant's* key and nothing else (§5). With it, a
customer's vault at home holds their whole club or workshop, nightly,
and the operator's exclusion of RFC-0029 D5b finally has a concrete
"backed up separately, by whom".

This is deliberately a **platform capability with a page**, not an
app: a container cannot open a disk, and we do not open that door in
RFC-0016 for this (D1).

## 1. Facts (measured in the reference, 2026-10-02, 0.1.175)

- **The door on the node is scoped by file name.** `backup-serve.sh`
  permits `ls`, `cat …sha256` and `rsync --sender` only for
  `/var/backups/oaap/oaap-backup-*.tar.gz`. Tenant archives are named
  `oaap-tenant-<label>-<host>-<stamp>.tar.gz` (`appctl.py`,
  `backup_create`). **A tenant archive cannot be fetched through the
  existing door at all** — not by the operator's puller and not by
  anybody else. That is correct today and is what §5 changes
  deliberately.
- **The nightly timer makes the node archive only.** `backup-nightly.sh`
  has no `--tenant`; a tenant archive exists when a human asks for one.
- **The puller already does the hard part.** `backup-pull.sh` fetches by
  rsync, verifies the source's checksum, keeps generations
  daily/weekly/monthly as hard links (so a kept generation costs no
  second copy), records every pull under
  `/var/lib/oaap/apps/backup-pulls` and writes `status.json`. It has a
  `--local` mode and already handles a CIFS target that refuses hard
  links.
- **A tenant archive has a reader.** `oaap tenant adopt <file.tar.gz>`
  (`oaap.core.tenant` 1.0 §2.11, format `tenant-0.2`) brings a tenant
  onto an **empty** node with its own record, names, ports and provider
  binding; it refuses a node archive and refuses an archive it cannot
  see completely. Merging into a *running* node with other tenants
  remains unpromised (RFC-0029 D5).
- **Archives are 0600 root and unencrypted at the source.** The door
  runs its three requests through `sudo`; the constraint is the script,
  not the file mode. Encryption at rest is "planned later, providers
  MAY" (`oaap.data.backup` §4). The weakest link of the chain is
  therefore the source's own disk, not the vault.
- **Hard links need a POSIX filesystem.** exFAT and NTFS targets fall
  back to full copies in the current script; a vault under LUKS carries
  ext4 and keeps the generation scheme free of charge.
- **Raspberry Pi 4/5, 64-bit, is Tier 1** (ADR-0005). The puller runs
  no app containers; a Pi with a USB disk is more machine than it
  needs.

## 2. Vocabulary

| Word | Meaning here |
| --- | --- |
| **source** | the node that makes archives and offers the door (unchanged by this RFC) |
| **puller** | the machine that fetches — the Pi; an OAAP node whose job is this |
| **vault** | one removable disk, encrypted as a whole, with a name and a LUKS UUID |
| **vault set** | all vaults the puller knows; exactly one is *inserted* at a time |
| **run** | open the inserted vault, pull, verify, close — a few minutes |
| **swap** | a person replaces the inserted vault with another one from the set |
| **tenant door** | a second forced command on the source that hands out one tenant's archives only (§5) |

## 3. The vault

### 3.1 Encryption: the whole disk, LUKS (D2)

The vault is a LUKS container over the whole disk, ext4 inside. Two key
slots:

1. a **key file on the puller**, root-only, which lets the nightly run
   open the vault without a person;
2. a **passphrase on paper**, kept where the vaults are not — the
   recovery path when the puller is gone.

The LUKS header is backed up once per vault (`cryptsetup luksHeaderBackup`)
and kept with the paper. **Losing both slots loses every vault**, and the
page says so when a vault is added (§4).

Why whole-disk and not per-archive: the puller can then **read the
archive back after writing it**, which is the same completeness rule
that `oaap.data.backup` 0.1.4 imposed on the source — a backup is what
was *measured* to be restorable, not what was asserted. With
per-archive public-key encryption (`age`) the puller could only prove
that the ciphertext is intact, because the private key must not be on
it. That stronger model protects against the theft of the puller *with*
the inserted vault; it is a later stage (§7), not the first, and nothing
in this RFC makes it harder: `age` encrypts a file, and a file is what
the generation scheme keeps.

### 3.2 Open only for the run; power off where it can be measured (D3)

Outside a run the vault is **closed**: unmounted, LUKS closed, drive in
standby (`hdparm -y` where the USB bridge passes it through). That is
stage 1 and needs no hardware. A closed vault on a running puller is as
good as the puller's root — which is the honest statement about stage
1 and the reason stage 2 exists.

Stage 2 removes the drive electrically between runs. Two means, chosen
**after a measurement on the actual Pi and enclosure**, not from a
data sheet:

| Means | What it does | What is known |
| --- | --- | --- |
| `uhubctl` | switches USB port power | Pi 4 switches all ports together; a hub with per-port switching makes it reliable; `udisksctl power-off` alone removes the device until re-plugged and is not enough |
| a switchable socket (Shelly/Tasmota, local HTTP) | cuts the mains of a 3.5" drive with its own supply | the clearest statement: between runs the vault does not exist electrically; needs a drive with its own power supply |

The run then becomes: power on, wait for the device, open, pull,
verify, close, power off. Each step reports; a step that fails leaves
the vault **closed and powered off**, never open.

### 3.3 The set and the swap (D4)

Every vault is **complete on its own**. Because OAAP keeps only full
archives (RFC-0029 D3), a vault that was away for a week simply receives
the current archive and its own generations; there is no chain to catch
up and no gap to explain. This is the second time D3 pays for itself.

The puller knows the set; at run time it uses **whichever vault is
inserted**, recognised by LUKS UUID, never by device name (`/dev/sda`
is whatever came up first). Per vault it records: name, UUID, last
seen, last successful run, generations held, free space.

The swap is **visible, not hoped for**:

- a vault inserted longer than the rhythm (default 7 days) shows
  **"swap due"** on the page and sends one message to the operator;
- a vault not seen for longer than two rhythms shows **"missing"**;
- `oaap backup vault forget <name>` marks a vault as lost; because of
  §3.1 a lost vault is worthless to its finder, and the record says
  when it was last complete.

Default set: **two in rotation, one spare**, swapped on a fixed weekday.
Nothing enforces the weekday; the page measures the days.

### 3.4 The puller is an OAAP node

The puller runs the reference platform like any other node (it may be
headless, RFC-0011) and no app containers. Its portal shows the page of
§4. It can carry FleetView or the fleet status reader as well, which
costs nothing and gives the household one screen. What it must **not**
carry is anything that would make it worth attacking for its own sake —
the cheapest way to keep a backup machine out of harm's way is to give
it nothing else to do.

Direction and reach are unchanged from RFC-0029: the puller fetches when
it can **reach** the source — same LAN, or a source on the internet.
A source behind a firewall the puller cannot reach needs RFC-0029 D6
(the source pushes with a create-only right) or an RFC-0044 tunnel; the
vault is the same in either case (D5).

## 4. The page (puller side, RFC-0029 D2)

One page on the puller, `server_admin` of the puller, machine-readable
first (`status.json` extended, not a second record):

- **inserted vault**: name, since when, swap due / ok;
- **last run**: when, duration, bytes, checksum verified, **read back
  ok** — failures stay listed;
- **next run** from the timer itself, never from stored intention
  (`oaap.data.backup` §2.4);
- **the set**: each vault with last seen, last complete, generations,
  free space; lost vaults greyed with the date;
- **the sentence on adding a vault**: "two keys open this vault; the
  one on this machine and the one on paper. If both are lost, the
  vault is lost."

The **source's** page keeps showing what the source can verify — that
an archive was made and read back — and nothing about vaults, which it
cannot see (D2 of RFC-0029 unchanged).

## 5. The tenant's own copy (D6)

### 5.1 Why it is worth having

The question was whether the same thing can be done **for one or more
tenants**, so that the backup moves to the customer. Three facts make
this more than a nice-to-have:

- a tenant archive exists (RFC-0029 D5, `oaap.data.backup` §2.1.1) and
  says of itself what it guarantees: **existence**;
- since `oaap.core.tenant` 1.0 an **empty node can adopt it** — the
  customer who holds last night's archive holds the means to leave,
  which RFC-0041 K6 promised and which until now required the operator
  to hand the file over;
- RFC-0029 D5b lets the operator exclude a tenant from the node archive
  only with a reason the tenant can see — and the reason was always
  meant to be *"this tenant is backed up separately, and here is by
  whom"*. Without §5 that sentence has nobody to point to.

So the customer's vault at home holds **their** club or workshop, and
the operator's archive shrinks to **"everything I am responsible for"**.
This is the honest division of duty for an operator with customers,
and it is the one that makes a stolen operator archive smaller.

### 5.2 The tenant door

A second forced command on the source, bound to a key **per tenant**:

```text
command="/usr/local/bin/oaap-backup-serve --tenant hbvp",restrict ssh-ed25519 AAAA... vault@hbvp
```

- It permits the same three requests — list, one checksum, send one
  archive — and **only for `oaap-tenant-hbvp-*.tar.gz`**. The tenant
  label is baked into the command line on the source, not sent by the
  client; a key for `hbvp` cannot name `cls`.
- `server_admin` issues the key (`oaap backup door add --tenant hbvp
  --key <pubkey>`), the `tenant_admin` holds the private half. Revoking
  is removing the line; the tenant's audit log records both
  (`oaap.core.tenant` 1.7), the same counterweight as D5b.
- The node archive stays behind the first door. Nothing a tenant key
  sends reaches the node archive, and the script, not a file mode, is
  the constraint — the same rule as today.

### 5.3 The tenant archive on a schedule

A tenant door is useless without something behind it, so the source
gains a **tenant schedule**: `oaap backup schedule --tenant hbvp` makes
the tenant archive nightly, stopping only that tenant's containers for
the copy (§2.1.1), and keeps the N newest at the source like the node
archive (D4). The tenant's own health page (its *place*, RFC-0042)
shows done/planned/running for its archive — the source's truth, said
once.

### 5.4 What the customer is told, in the archive and on the page

Three sentences, and they are the contract:

1. **"This archive contains everything of your tenant and nothing of
   anybody else's."** Measured by the completeness check narrowed to
   that tenant's instances (§2.1.1).
2. **"It can be brought onto an empty OAAP node with `oaap tenant
   adopt`. It cannot be merged into a running node."** The adoption
   path is the one that exists; a merge is not promised (RFC-0029 D5).
3. **"It holds your users' password hashes and your apps' secrets in
   clear."** The customer now guards their own secrets; that is the
   point, and it has to be said.

### 5.5 What it is not

It is not a per-instance backup, not an app-level export, and it does
not change what the tenant archive contains. A tenant that is excluded
by the operator **and** has no vault of its own has no backup; the
operator's exclusion reason must therefore name the vault, and the page
of the excluded tenant must show when *its* door was last used. An
exclusion whose named vault has not pulled for two rhythms is a loud
sentence on the operator's page, not a quiet one on the customer's.

## 6. Security requirements

- The puller's key to the source MAY only list, read one checksum and
  receive one archive (unchanged, `backup-serve.sh`). A tenant key MAY
  do the same for exactly one tenant's archives and nothing else.
- The vault's key file MUST be root-only on the puller and MUST NOT be
  written to any vault. The paper passphrase MUST exist before the
  first run; the tool refuses to add a vault with a single key slot.
- A run MUST verify the source checksum before writing to the vault and
  MUST read the written archive back; a vault whose read-back fails is
  reported, never silently retried onto another vault.
- A failed step MUST leave the vault closed (and, in stage 2, powered
  off). The vault MUST NOT be left mounted between runs.
- A lost vault MUST be recordable; the record MUST say when it was last
  complete.
- The tenant archive's three sentences (§5.4) MUST be in the archive's
  manifest and on the tenant's page; an archive that cannot be adopted
  MUST say so in the archive.
- The source MUST NOT learn or record which vault fetched; RFC-0029 D4
  stands. The puller's registry is the only record of fetches.

## 7. Staging

| Stage | What | Where |
| --- | --- | --- |
| **0 — trial run** | Pi with Debian, one LUKS disk, `install-backup-pull.sh --to /mnt/vault`, a wrapper `vault-run.sh`: open, pull, read back, close, standby. Weeks of real nights before any spec. | `oaap-reference/ops/`, like the existing scripts |
| **1 — the vault in the platform** | `oaap.data.backup` 0.5: `oaap backup vault add/list/forget`, `oaap backup pull`, the page of §4, swap-due message, UUID-based recognition. | reference + spec |
| **2 — power** | `uhubctl` or socket after measurement on the real Pi; failed step leaves it off. | reference |
| **3 — the tenant door** | §5.2–5.4: `--tenant` on serve and pull, `oaap backup door add`, tenant schedule, the three sentences, the exclusion link. | reference + spec |
| **later, by need** | `age` per archive for the "puller stolen" model; RFC-0029 D6 push for unreachable sources; per-tenant merge if ever decided. | — |

Stage 0 comes first for the same reason the ops scripts did: *what
survives real nights goes into the specification, not the other way
round.* The restore drill — adopt a tenant from a vault onto an empty
node, restore a node from a vault — goes **into the calendar** at stage
1, once per vault.

## 8. Decisions for Jörg

| | Question | Recommendation |
| --- | --- | --- |
| **D1** | App or platform capability? | **Platform**, with a page on the puller. A container cannot open a disk; the alternative is the first app with host reach, and RFC-0016 stays shut for this. "Backup App" remains the name of the page. |
| **D2** | Encryption | **LUKS whole disk**, key file on the puller + paper passphrase, header backed up. `age` as a later stage for the "puller stolen" model. |
| **D3** | Power | **Stage 1 without hardware** (closed between runs), **stage 2 `uhubctl` or socket after a measurement** on the real Pi. |
| **D4** | Rotation | **Two in rotation, one spare**, weekly, every vault complete on its own, swap-due and missing measured and shown, `forget` for a lost vault. |
| **D5** | Direction and reach | **Unchanged from RFC-0029**: pull where the puller reaches the source; D6 push or RFC-0044 tunnel otherwise. The vault does not care. |
| **D6** | The tenant's own copy | **Yes, as stage 3**: a key per tenant behind a second forced command scoped to that tenant's archives, a tenant schedule on the source, three sentences as the contract, and D5b's exclusion reason names the vault. |
| **D7** | Verification | **Read back every run; a drill per vault in the calendar.** A vault that was never adopted from is a hope. |
| **D8** | Order | **Stage 0 as script trial run before anything is specified**, then 1, 2, 3. |

## Deutsche Zusammenfassung

**Worum es geht.** Ein Knoten wie bei Bernd sichert sich jede Nacht
selbst und bietet seine Archive über eine Tür an, die genau drei Dinge
kann: auflisten, eine Prüfsumme geben, ein Archiv senden. Dieser RFC
baut das **andere Ende für den kleinen Fall**: ein Raspberry Pi mit
einer USB-Platte als **Tresor**. Die Platte ist als Ganzes
verschlüsselt, nur für die Minuten des Laufs geöffnet und eine von
mehreren, die ein Mensch wöchentlich tauscht und woanders lagert. Der
gesicherte Knoten merkt davon nichts und braucht nichts Neues: Der Pi
ist ein weiterer Schlüssel in seiner `authorized_keys`, was RFC-0029 D4
ausdrücklich erlaubt.

**Gemessen vor dem Schreiben.** Die Tür auf dem Knoten gibt nur
`oaap-backup-*` heraus. Mandantenarchive heißen `oaap-tenant-*` und
sind durch die Tür heute **gar nicht** erreichbar. Der nächtliche Lauf
macht nur das Knotenarchiv. Der Abholer kann schon alles Schwere:
holen, Prüfsumme, Generationen als Hardlinks, Protokoll. Und seit
`oaap.core.tenant` 1.0 kann ein **leerer Knoten ein Mandantenarchiv
adoptieren**.

**Die Form.** Plattformfähigkeit mit einer Seite im Portal des
Abholers, keine App: Ein Container kann keine Platte öffnen, und diese
Tür in RFC-0016 bleibt zu (D1). LUKS über die ganze Platte, Schlüsseldatei
auf dem Pi plus Passphrase auf Papier, Header gesichert; so kann der Pi
jedes Archiv nach dem Schreiben **zurücklesen** (D2). Außerhalb des
Laufs ist der Tresor geschlossen; Strom wirklich abschalten per
`uhubctl` oder schaltbarer Steckdose erst nach Messung am echten Pi
(D3). Jeder Tresor ist für sich vollständig, weil es nur Vollarchive
gibt; der Pi erkennt den eingelegten an der LUKS-Kennung, misst die
Tage und sagt „Wechsel fällig" oder „fehlt"; ein verlorener Tresor ist
aussprechbar und für den Finder wertlos (D4). Richtung und Reichweite
bleiben wie in RFC-0029: Pull, wo der Pi den Knoten erreicht, sonst D6
oder RFC-0044 (D5).

**Die Erweiterung für Mandanten (Jörgs Frage).** Ja, sinnvoll, und aus
drei Gründen mehr als nett: Das Mandantenarchiv existiert, ein leerer
Knoten kann es adoptieren, und das Ausnehmen eines Mandanten aus dem
Knotenarchiv (D5b) brauchte immer einen Satz „wird woanders gesichert,
und zwar von …", auf den bisher niemand zeigen konnte. Die Form: ein
**Schlüssel je Mandant** hinter einer zweiten erzwungenen Tür, die nur
`oaap-tenant-<kürzel>-*` herausgibt; das Kürzel steht auf dem Knoten
in der Befehlszeile, nicht in der Anfrage. Dazu ein Zeitplan für das
Mandantenarchiv auf dem Knoten und drei Sätze als Vertrag: alles vom
Mandanten und nichts von anderen; auf einen **leeren** Knoten
übernehmbar, nicht in einen laufenden mischbar; enthält die eigenen
Passwort-Hashes und App-Geheimnisse im Klartext. Ein ausgenommener
Mandant ohne eigenen Tresor hat **keine** Sicherung, deshalb muss die
Begründung des Betreibers den Tresor nennen, und ein Tresor, der zwei
Rhythmen nicht geholt hat, ist ein lauter Satz auf der Seite des
Betreibers (D6).

**Reihenfolge.** Stufe 0 als Skript-Probelauf auf dem Pi, wochenlang
echte Nächte, bevor etwas spezifiziert wird; dann Stufe 1 der Tresor in
der Plattform (`oaap.data.backup` 0.5), Stufe 2 Strom, Stufe 3 die
Mandantentür. Zurücklesen bei jedem Lauf und ein Probelauf der
Wiederherstellung je Tresor im Kalender (D7, D8).

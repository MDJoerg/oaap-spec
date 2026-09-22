# RFC-0034: Documents and File Storage — One Place to Put a File, Many Places to Keep It

- **Status:** Accepted (2026-09-08) — twelve decisions D1–D12 taken by
  Jörg in the design round, eleven following the recommendation;
  **D9 decided differently**: the mirror export is the rule now, a
  human-readable backing follows later as a marked special case.
  Nothing is built.
- **Date:** 2026-09-08
- **Authors:** Jörg (the idea, the standards, the SAP lesson), Claude
  (analysis & proposal)
- **Depends on:** RFC-0016 (app isolation; app-to-app links — the
  shape a binding copies), RFC-0022 (tenant as boundary — one
  repository world per tenant), RFC-0026 (names are changeable,
  identity is not — a document's ID outlives its location), RFC-0027
  (machine principals — the S3 face authenticates with them),
  RFC-0029 (backups — what is copied and what is referenced), RFC-0030
  D6 (shared data holding must be able to copy itself), RFC-0031
  (`oaap.data.store` holds the metadata; D6 references; D8 the schema
  copy), RFC-0033 D1 (the app never holds the credential)
- **Followed by:** capability specs `oaap.data.files` and
  `oaap.data.documents`; a later RFC for outward adapters (CMIS) when a
  consumer exists; the retention enforcement stage (§10).
- **Supersedes:** the idea-store entry *„Datei-Storage mit
  Provider-Modell (`oaap.data.files`)"* of 2026-08-04, whose backing
  and migration thoughts are kept here and whose "human folder on the
  NAS" is answered in §9.
- **Driver:** Jörg, 2026-09-08: *„Ich habe die Idee, eine
  Funktionalität abzubilden, dass wir in der Plattform
  Storage-Ablagesysteme definieren, wo unterschiedliche Connectoren
  dran hängen und wir die üblichen Standards bieten können. Aus der App
  heraus lassen sich so Dokumente einheitlich ablegen und sind aus Sicht
  von Backups beherrschbarer. Wir müssen dann auch eine Migration oder
  das Umspeichern berücksichtigen oder dass auf die Dokumente anders und
  durch mehrere Apps zugegriffen werden soll. Also eigentlich so ähnlich
  wie der Digitale Zwilling eine über die Plattform geteilte
  Funktionalität."*

## Summary

An app on OAAP today keeps its files in its own declared storage mount.
That is correct for isolation and wrong for the three things a file in a
small company actually has to survive: a backup that must know what it
holds, a second app that needs the same document, and a storage box that
gets replaced. This RFC gives the platform one way to put a file and
many ways to keep it, cut along the same seam as RFC-0031:

- **`oaap.data.files`** answers *where do the bytes live, and how are
  they copied?* — repositories per tenant, **backings** behind them
  (the node's own data directory, any S3-compatible service, an SMB
  share), backup scope, the isolated view for a rehearsal, and the move
  from one backing to another. It knows nothing about documents.
- **`oaap.data.documents`** answers *what is a document, whom does it
  belong to, and what is it attached to?* — a stable platform ID,
  metadata, immutable versions, the link to a twin object, a retention
  date. It is the only capability an app talks to.

The lesson this copies is ArchiveLink's: SAP always kept the **link
table** (business object → document) apart from the **content
repository**. That separation is why a repository could be swapped
without any application noticing. Here it is the same separation with
the twin as the link table and `oaap.data.files` as the repository.

The rule that carries the design, in one sentence:

> **An app holds the document's identity, never its location. Bytes are
> written once and never changed; where they lie is the platform's
> business and may change at any time.**

## Motivation

### 1. The idea store already asked, and the answer was "when the NAS is real"

The 2026-08-04 entry (`oaap.data.files`) named Bernd's acceptance
protocols — tablet capture with photos and signatures, rendered as PDF,
filed by customer → order → date, destined for the Synology so the
"Montageakte" is visible in the familiar folder world. The design idea
then was a backing *below* the storage mount: the app writes files as
before, the platform decides what lies behind. Migration was a portal
sequence with a maintenance mode. The decision was to wait.

Two things changed since. RFC-0031 gave the platform a place for shared
metadata and a shape for "shared holding": a Postgres schema per tenant
that the rehearsal copies. And RFC-0033 gave the platform a shape for
"an app uses something the operator owns": a binding as a grant, the
app never seeing the credential. Documents fit both shapes exactly, and
the maintenance-mode migration turns out to be unnecessary (§3.4).

### 2. The twin needs the file next to the object

The twin (RFC-0031) holds the customer, the order, the activity — and
says nothing about the protocol PDF that belongs to the order. Apps
store references, not copies (RFC-0031 §3.3). A document reference must
therefore be something that resolves platform-wide and outlives the app
that wrote the file. A path inside one app's mount is neither.

### 3. Every shared holding must be able to copy itself

RFC-0030 D6 is the cheapest sentence in the platform and the one this
RFC must obey before anything is built: *a rehearsal never shares a
data source with production; every shared holding must answer "how do I
make an isolated copy of myself?"* For a Postgres schema the answer is a
schema copy. For a terabyte of PDFs a copy is not an answer; §8 gives a
better one, and it only works because of D3.

### 4. Backups: the bytes are the bulk, and some of them are not ours

RFC-0029 backs up the node's data directory. Files are most of that
volume, and the idea store already noted that an external NAS "has its
own backup world" and should be referenced, not copied. What was missing
is the piece that makes referencing honest: after a restore, someone
must be able to say *which* documents are missing, not only *that* the
NAS was not part of the archive.

### 5. Standards: what to take from S3, CMIS and ArchiveLink

Three standards were on the table. **S3** is a protocol every library
speaks; it is how a foreign container app expects to write files. **CMIS**
is a full document-management protocol — heavyweight, and alive today
mostly in the SAP and Alfresco worlds. **ArchiveLink** is SAP-only as a
protocol but carries the semantics that matter: the link between
business object and document, the swappable repository, retention.

The choice (D8): the platform's own document API inward, **S3 as a
second face** on the same repository, ArchiveLink's *semantics* built in
(link, move, retain), and CMIS only as an outward adapter when a real
consumer asks for it.

## Vocabulary — SAP and S3 to OAAP

| SAP / S3 term | OAAP term | Note |
| --- | --- | --- |
| ArchiveLink link table (TOA*) | a **relation** in the twin, `has_document` | RFC-0031 D6: a reference, nothing more |
| Content repository | **backing** | where bytes lie; per version, swappable |
| Content server / KPro | `oaap.data.files` | the byte service |
| DMS / CMIS repository | **repository** | a named, tenant-scoped container of documents |
| S3 bucket | repository | the S3 face maps bucket ↔ repository |
| S3 object key | a **source key** of the document | the app's name; the platform ID is separate (RFC-0031 D3 applied to files) |
| Archiving, retention | `retain_until`, `legal_hold` | field now, enforcement later (D10) |
| RFC destination cut in QAS | rehearsal overlay (§8) | reads production, writes only into its own backing |

## 1. Two capabilities (D1)

| Capability | Question it answers | Owns |
| --- | --- | --- |
| **`oaap.data.files`** | *Where do the bytes live, and how are they copied?* | repositories; backings and their kinds; the content-addressed local store; the S3 and SMB clients; backup scope and the backing manifest; the rehearsal overlay; the move between backings |
| **`oaap.data.documents`** | *What is a document, whom does it belong to, what is it attached to?* | document identity and source keys; versions; metadata; bindings to instances; the document API and the S3 face; the twin relation; retention fields; mirror-export rules |

`oaap.data.files` never sees a title or a link; it stores and returns
bytes by hash and moves them between backings. `oaap.data.documents`
never opens a file; it keeps the metadata in `oaap.data.store`
(RFC-0031) and asks `files` for bytes. The split is what makes the
backing swap (§3.4) and the rehearsal overlay (§8) testable without
any document semantics, and the document semantics testable against a
single local backing.

## 2. The document (D2, D3)

### 2.1 Identity

A document has an **opaque platform ID** issued once and never
reused, and any number of **source keys**: the key an app chose through
the S3 face, an external number, a filename. RFC-0031 D3 applied to
files: the platform ID is what the twin references and what survives
every move; a source key is what an app is allowed to call it.

### 2.2 Versions are immutable (D3)

Bytes are **written once**. A document is a sequence of versions; a new
upload under the same document is a **new version with its own ID**,
the old one stays readable. Nothing is overwritten in place. Each
version carries:

| Field | Meaning |
| --- | --- |
| `version_id` | opaque, stable |
| `sha256` | the content hash — the only thing `files` addresses bytes by |
| `size` | bytes |
| `media_type` | as uploaded |
| `backing` | **which backing holds the bytes right now** (D2) |
| `created_at`, `created_by` | recorded time, the machine principal (RFC-0027) |
| `retain_until`, `legal_hold` | §10 |

Immutability is not a style choice; it is what the rest of the RFC
rests on. Because a version never changes, a rehearsal may read
production bytes without any risk (§8), a backup can verify itself by
hash (§7), a move between backings can be checked byte for byte (§3.4),
and retention (§10) has something to hold on to. It matches the twin's
"append, never update" for recorded time.

### 2.3 The backing pointer lives on the version (D2)

Each version knows where its bytes are. A repository does not have *a*
backing; it has a **default backing for new versions** and any number of
versions that currently lie elsewhere. This is what turns migration
from a maintenance-mode event into a background job (§3.4) and what
lets a repository straddle two backings for as long as it takes.

## 3. Repositories and backings (D2, D11)

### 3.1 The repository

A repository is a named, **tenant-scoped** container of documents:
label, tenant, default backing, mirror-export rule (§9), and the
bindings that grant instances access (§4). One tenant may have several
(`protokolle`, `belege`, `fotos`); a repository never spans tenants.
Storage isolation follows RFC-0022: one tenant's bytes are never
addressable from another tenant's repository, whatever backing they
share physically.

### 3.2 Backing kinds

| Kind | What it is | Credential | In the backup (§7) |
| --- | --- | --- | --- |
| `local` | the node's own content-addressed store under the data directory (D11) | none | **copied** |
| `s3` | any S3-compatible endpoint (a NAS with S3, a cloud bucket, another OAAP node's S3 face) | access key + secret | **referenced** + manifest |
| `smb` | a share mounted on the host through the spool pattern of the backup targets (CURRENT_STATE 2026-08-07) | user + password | **referenced** + manifest |

Every backing is **managed**: keys are the content hash, layout is the
platform's, nothing in it is meant for a person to browse. The human
folder is a different thing (§9). Credentials of `s3` and `smb`
backings live in a `0600` file on the host, as the backup targets do;
they are never in an instance's environment, never in the backup, and
an app never sees them (RFC-0033 D1 word for word).

### 3.3 The local store (D11)

The reference builds the `local` backing itself: `<data>/files/<tenant>/
<hh>/<sha256>`, one file per distinct content, deduplicated **within a
tenant** and never across tenants. It is in the data directory, so it
is in the backup today without any new component in the backup scope,
the rehearsal, or the update path. S3 is spoken **as a client** toward
external backings, not run as a service on the node. Garage stays the
named alternative should a node ever need a real S3 service of its own
(ARM64-capable, ADR-0005); MinIO is not considered because the
licensing and maintenance situation of its community edition
deteriorated in 2025 — to be re-checked before any such decision.

### 3.4 The move (D2)

```
oaap files move --tenant bernd --repository protokolle --to synology-s3
```

Per version: copy the bytes to the target, read them back, compare the
hash, flip the version's backing pointer, and only then schedule the
source bytes for deletion after a grace period. Resumable, idempotent,
visible in the portal with progress like a deployment (RFC-0024).
**No maintenance mode**: an app reading version *n* during the move gets
the bytes from wherever the pointer currently says; an app writing gets
the repository's default backing, which the operator switches at the
start or the end of the move as they prefer. The 2026-08-04 portal
sequence (maintenance → migrate → switch → release) collapses to "set
the default, start the move, watch it finish".

## 4. Binding — how an instance gets a repository (D6)

Exactly the shape of a destination (RFC-0033 §1.2) and of an app-to-app
link (RFC-0016):

- **Default none.** A freshly installed instance can store nothing.
- **The manifest declares a need**, not a grant:

  ```yaml
  documents:
    needs:
      - name: protokolle          # the name the app uses
        purpose: "Abnahmeprotokolle als PDF mit Fotos"
        access: write             # read | write
  ```

- **The operator binds** a repository of the instance's tenant to each
  need, in the install dialog or later on the instance page. Recorded,
  revocable, shown on the instance and on the repository.
- **A rehearsal instance** is bound automatically to its overlay (§8)
  and to nothing else.

The app reaches the repository under the name it declared; the platform
resolves name → repository → backing. Access `read` lets the instance
fetch and list; `write` adds create and new-version; deletion is a
separate right (§10) that a binding may grant explicitly.

## 5. The twin relation (D7)

A document is **not** a twin object. It has its own ID outside the twin
and `oaap.data.documents` works without a twin at all. Where the twin
exists, the platform registers one relation type, `has_document`, from
any object type to a document reference in exactly the form of RFC-0031
D6: **id, title, media type, origin — and nothing else**. Writing the
relation is a document-API call (§6.1) that the platform forwards to the
twin API in the app's name (RFC-0027); the app never writes the relation
by hand.

Consequences:

- The twin browser shows the Montageakte at the order, the invoice at
  the customer, without either app knowing the other.
- Several apps reading the same order find the same documents through
  the same reference — Jörg's "durch mehrere Apps zugegriffen".
- A merge of two objects (RFC-0031 D3) carries the relations; a
  document linked to the alias is found under the canonical.
- A rehearsal's twin copy (RFC-0031 D8) carries the relations; they
  resolve against the overlay, which reads through to production (§8).

## 6. The interfaces (D8)

### 6.1 The document API

The primary face. Authenticated as the instance's machine principal,
scoped by its bindings.

| Method | Path | Meaning |
| --- | --- | --- |
| `POST` | `/documents/{repo}` | create a document with its first version (body = bytes; title, media type, source key, optional `link_to` object ID in headers or a multipart part) |
| `POST` | `/documents/{repo}/{id}/versions` | add a version |
| `GET` | `/documents/{repo}/{id}` | metadata and versions |
| `GET` | `/documents/{repo}/{id}/content[?version=]` | bytes, latest by default; `ETag` = sha256 |
| `GET` | `/documents/{repo}?q=&object=&key=` | list: by text, by linked twin object, by source key |
| `POST` | `/documents/{repo}/{id}/links` | link to a twin object (§5) |
| `DELETE` | `/documents/{repo}/{id}` | soft delete; refused while `retain_until` is in the future or `legal_hold` is set (§10) |

### 6.2 The S3 face

The same repository, spoken as S3 so that foreign container apps
(Paperless, Nextcloud, anything built on boto or rclone) run unchanged:

- **bucket = repository label** as bound to the instance;
- **key = source key** of the document; a `PUT` to a new key creates a
  document, a `PUT` to an existing key creates a **new version** (D3:
  S3's overwrite becomes a version); `GET` returns the latest;
  `?versionId=` returns one; `DELETE` is the soft delete of §6.1;
- **credentials = the instance's machine principal** (RFC-0027): the
  API key ID is the access key, its secret signs SigV4. No second
  credential system;
- endpoint: the gateway under the node's name, path-style buckets; a
  per-tenant host is not needed because the bucket name already
  resolves through the binding.

What the S3 face does **not** offer: bucket creation or deletion (that
is the operator's), ACLs and policies (bindings are the policy),
cross-tenant listing, multipart beyond what the reference needs for
large files.

### 6.3 Outward adapters — later, on demand

CMIS and ArchiveLink-protocol endpoints are **adapters** on top of §6.1,
built when a consumer exists (an SAP system that wants to archive into
an OAAP repository, or the reverse). They are named here so nobody
builds a document API that cannot carry them: the properties CMIS
requires (object ID, name, content stream, version series) all exist in
§2.2. Not part of any stage below.

## 7. Backup (D5)

RFC-0029 gains two rules:

1. **`local` backings are in the backup** as today — they are part of
   the data directory. Nothing changes for the generations, the hard
   links, or the pull direction.
2. **External backings (`s3`, `smb`) are referenced, not copied**, and
   every backup carries a **backing manifest** per external backing:
   the backing definition (without its credential) and the list of
   every version that lies there — version ID, sha256, size. The
   manifest is small, is written by `files` at backup time, and is what
   makes a restore honest: after restoring the node, `oaap files verify`
   walks the manifest against the backing and reports **which documents
   are missing or corrupt**, by ID and title, not just "the NAS was not
   backed up".

The metadata of every document — identity, versions, links, retention
— lives in `oaap.data.store` and is therefore in the backup regardless
of where the bytes are. Losing an external backing loses bytes, never
the knowledge of what existed.

## 8. The rehearsal (D4)

RFC-0030 D6 answered by two facts that already exist:

- **Metadata is copied** with the tenant's schema (RFC-0031 D8):
  `docs_<tenant>` → `docs_<tenant>_r_<instance>`. Cheap; it is rows.
- **Bytes are shared read-only** because versions are immutable (D3).
  The rehearsal's copied metadata points at the same version IDs and
  the same hashes; reading them changes nothing.

Everything the rehearsal **writes** goes to an **overlay backing**
created with the rehearsal, bound only to it, and deleted with it. A
new version, a new document, a soft delete — all of it is a change in
the copied metadata plus, for new bytes, a file in the overlay.
Production's metadata and bytes are not touched; the overlay cannot be
bound to any other instance; a move (§3.4) never targets an overlay.

If the schema copy or the overlay creation fails, the rehearsal is
refused with the reason named — RFC-0030's rule, word for word. There
is no "copy the whole repository" option, and none is needed: a
rehearsal sees the entire production document set as of the copy and
can spoil none of it.

## 9. The human folder: a view, not a store (D9)

Bernd wants the Montageakte in the folder world he knows. A
content-addressed store is not browsable, and a browsable store is not
safe. The decision (D9, differing from the recommendation in scope,
not in principle) is **both, in this order**:

### 9.1 The mirror export — the rule, now

A repository may carry a **mirror-export rule**: a target (an `smb` or
`s3` backing used as a *destination*, or a plain host path) and a path
template resolved through the twin:

```yaml
mirror:
  target: synology-share
  path: "{customer.number} {customer.name}/{order.number}/{created:%Y-%m-%d} {title}.{ext}"
```

`files` writes every new version there after commit, re-exports when a
version is superseded, and never reads back. The folder is a
**shop window**: rename, move or delete in the Explorer and nothing in
the platform changes; the next export puts the file back. Same principle
as RFC-0031's "platform sub-models are views over app models": the
system of record is the repository, the folder is a projection of it.

### 9.2 The readable backing — later, marked fragile

A later stage adds a backing kind whose keys *are* human paths — for the
case where the folder must be the single copy (a customer who refuses a
second one). It is explicitly marked **fragile** in the portal and in
the spec: a rename or move on the share breaks the hash check, the
document then shows *content missing*, and `oaap files verify` reports
it. No move (§3.4) is *from* such a backing without a verify first. It
is a documented exception, not a second normal.

## 10. Retention (D10)

Two fields now, enforcement later:

- `retain_until` — a date before which the version may not be deleted;
- `legal_hold` — a flag that blocks deletion until cleared by a
  `tenant_admin`.

Stage 1 stores and returns them and **refuses a delete** while either
holds — that much costs nothing and prevents the one mistake that
cannot be undone. The enforcement stage (§13, stage 6) adds the sweep
that deletes expired versions on request, the evidence trail (who set
what, when), and the export a tax auditor asks for. German GoBD is the
driver: acceptance protocols and invoices are business records, and
ArchiveLink existed for exactly this.

## 11. Security requirements

- An app holds a document's **identity**, never a backing path, never a
  backing credential (RFC-0033 D1).
- Backing credentials live in a `0600` file on the host; not in
  instance environments, not in backups, not in the portal database.
- **Tenant isolation is absolute**: repositories are tenant-scoped,
  dedup is per tenant, the S3 face resolves buckets only through the
  instance's bindings, listing across tenants is impossible by
  construction.
- Bytes are verified by hash on every move, every backup manifest, and
  on demand by `verify`; the reference reads with the hash and refuses
  to serve content whose hash does not match.
- A rehearsal instance can write only into its overlay and cannot be
  bound to anything else.
- Deletion is soft, is a separate right in a binding, and is refused
  under retention; hard deletion of bytes is a platform sweep, never an
  app call.
- The S3 face authenticates with machine principals only; no static
  bucket keys exist.

## 12. Non-goals (deliberate)

- **Not a DMS.** No full-text search, OCR, workflows, check-out/check-in
  in this RFC. Search over document text may come with the twin's
  deferred embedding search (RFC-0031 "deferred").
- **No CMIS or ArchiveLink server** in any stage below; adapters on
  demand (§6.3).
- **No sync client**, no WebDAV, no "Nextcloud replacement". Apps that
  provide that run on top of the S3 face.
- **No cross-tenant dedup** and no cross-node replication — the second
  is RFC-0032/RFC-0033 territory (a document reference through the
  tunnel is a data path like any other).
- **No encryption at rest by the platform** in stage 1; the local
  backing inherits the disk, external backings their own. To be
  revisited with the credential store.

## 13. Staging (D12)

Built **after** RFC-0031's steps 1–3 (`oaap.data.store`, `oaap.data.model`,
`oaap.data.twin`), because the metadata schema and the twin relation
depend on them. The RFC is written now so the decisions stay warm.

1. ~~**`oaap.data.files`, local only.**~~ **Gebaut 2026-09-22**
   (Referenz 0.1.113, `oaap.data.files` 0.1): content-addressed store,
   tenant directories, put/get/verify by hash, in the backup. Testable
   alone, and tested alone.

   **What it corrected in this RFC's own words:** §3.3 says the local
   store "is in the data directory, so it is in the backup today
   without any new component". That was wrong, and wrong in the
   familiar way — the reference's backup archives a written **list of
   paths**, not the directory. A new subdirectory is invisible to a
   list nobody updated, and invisible in the only way that matters,
   because the command still succeeds and the archive still restores.
   The same shape as the 2026-09-05 gap, which was `tenants/` missing
   from that same list. Now named in the backup, in the restore, in
   the tenant archive (RFC-0029 D5) and per tenant where a tenant is
   excluded from the node archive (D5b) — an excluded customer's bytes
   are that customer's bytes.
2. **`oaap.data.documents`.** The schema in `oaap.data.store`, the
   document API (§6.1), bindings as grants, needs in the manifest, the
   `has_document` relation in the twin, retention fields with delete
   refusal. Rehearsal: schema copy plus overlay (§8).
3. **The S3 face** (§6.2) with machine-principal credentials; a foreign
   container app (Paperless is the candidate from the idea store) as
   the proof.
4. **External backings and the move.** `s3` client, `smb` through the
   spool pattern, the backing manifest in the backup, `verify`, the
   per-version move with progress in the portal. Bernd's Synology as
   the proof.
5. **Mirror export** (§9.1) with twin-resolved path templates.
6. **Retention enforcement** (§10): sweep, evidence, export.
7. **Readable backing, marked fragile** (§9.2), and outward adapters
   (§6.3) when a consumer asks.

## 14. Stufe 4 as a design, and the load test that asks for it

Written 2026-09-22, ahead of the build, because the video-service
decision (CURRENT_STATE 152) is waiting on exactly these answers and
deserves them in writing rather than in a conversation.

### 14.1 What Stufe 4 is

An external backing (`s3` or `smb`) holds a repository's bytes; the
node holds the metadata. Per §7 the archive then **references** those
bytes instead of copying them, and carries a **backing manifest**: the
backing's definition without its credential, plus every version that
lies there — version id, sha256, size. Three things follow, and the
third is the one that makes it honest:

1. **The node archive stops growing with the library.** What is copied
   during the stop-the-apps window is metadata and the small manifest.
2. **The bytes are then somebody's responsibility, and it is not this
   platform's.** "Referenced" means "not backed up by us".
3. **A restore can say what is missing, by document.** `oaap files
   verify` walks the manifest against the backing and reports which
   documents are absent or corrupt, by id and title — not "the NAS was
   not in the backup". Because the metadata is in `oaap.data.store` and
   therefore always in the archive, **losing an external backing loses
   bytes, never the knowledge of what existed.**

Point 2 is the same shape RFC-0029 D5b settled for tenants, one level
down, and it takes the same answer: **what an archive leaves out, it
must record that it left out.** The backing manifest is that record.
Who keeps the external store safe is an operator decision; the
platform's duty is to make the gap impossible to discover by accident.

### 14.2 The load test: a video service

The driver is Jörg's measurement (2026-09-21): the nightly backup stops
app containers for the copy, and a library around 100 GB turns that into
hours. The question "does RFC-0034 fix this?" has two answers, and which
one applies is a **property of the video service we choose**, not of
this RFC.

**Shape A — the video service keeps its own storage.** PeerTube and
every comparable product do this: their own directory layout, their own
database, their own notion of a file. They will not store through
`oaap.data.documents`, and asking them to is a fork, not an
integration.

- RFC-0034 buys **nothing** here. The bytes are an instance's ordinary
  storage volume, under `tenants/<t>/instances/<i>/`, and the nightly
  copy walks all of it.
- The answer that does exist is **RFC-0029 D5b, built 2026-09-22**:
  put the video service in its own tenant and **exclude that tenant
  from the node archive**, with a recorded reason, and back its storage
  up separately — a snapshot on the NAS, or the service's own export.
  The archive then records the omission, the restore names it and
  leaves those instances dormant, and the tenant reads it in their own
  audit log. The nightly window goes back to minutes.
- What this costs, stated plainly: the platform no longer knows what is
  in that library. There is no per-document verify, because there are
  no documents — only a directory somebody else is looking after.

**Shape B — the video service stores through the platform.** It speaks
the S3 face (Stufe 3) against a repository whose default backing is
external; OAAP holds identity, metadata, retention and the twin
relation, the NAS or bucket holds the bytes.

- This is what RFC-0034 was written for, and here §7 answers the
  downtime question directly: the archive carries manifest entries, not
  gigabytes.
- It also answers questions Shape A cannot: *which* recording is
  missing after a disk failure, how long a recording must be kept
  (§10), what it is attached to in the twin (§5), and what a rehearsal
  sees (§8, read-only shared bytes).
- The price is that the service must be one we can point at an S3
  endpoint and be content with — which narrows the field considerably,
  and may narrow it to something we would build rather than adopt.

### 14.3 What this means for the choice

The honest summary, and it is a decision criterion rather than a
recommendation for a product:

- **If the video service is adopted as-is, plan for Shape A**, and the
  thing that makes it bearable already exists as of today. RFC-0034 is
  then not on the critical path for video at all, and Stufe 4 can be
  built when documents need it rather than when video does.
- **If S3-backed storage is a hard requirement of the choice, say so
  before the product is chosen**, because it is the single property
  that decides which of the two worlds we are in — and it is much
  cheaper to require it at selection time than to retrofit it.
- **Either way the storage lives outside the node.** Shape A puts it
  outside our sight; Shape B puts it outside our archive but inside our
  bookkeeping. The difference between those two is the whole value of
  Stufe 4, and it is worth naming before the product is chosen rather
  than after.

Stufe 4 therefore stays where the build order put it — after documents
— unless the video decision turns out to require it, which is a
question this section exists to make askable.

## Decisions

Decided by Jörg on 2026-09-08 in the design round, form mode, twelve
questions:

- **D1 — Two capabilities**, `oaap.data.files` (bytes, backings,
  copies) and `oaap.data.documents` (identity, metadata, links,
  retention). Accepted as recommended.
- **D2 — The backing pointer lives on the version, not on the
  repository.** Online, per-version migration, no maintenance mode.
  Accepted as recommended.
- **D3 — Objects are immutable; a new version is a new object; the
  content hash is a metadatum.** Accepted as recommended.
- **D4 — A rehearsal reads production bytes and writes only into its
  own overlay backing;** metadata is copied with the schema. Accepted
  as recommended.
- **D5 — External backings are referenced, not copied; every backup
  carries a manifest of IDs and hashes** so a restore can name what is
  missing. Accepted as recommended.
- **D6 — Repositories are bound to instances like destinations**:
  default none, per instance, recorded, revocable, never a grant in the
  manifest; the app never sees a backing credential. Accepted as
  recommended.
- **D7 — A document is its own thing with its own ID; the twin holds a
  `has_document` relation as a reference** (RFC-0031 D6). `documents`
  works without a twin. Accepted as recommended.
- **D8 — Inward: the platform's own document API plus an S3 face on the
  same repository; CMIS and ArchiveLink protocol only as outward
  adapters on demand.** Accepted as recommended.
- **D9 — Both: the mirror export as the rule now, a human-readable
  backing later as a marked fragile special case.** Decided *beyond*
  the recommendation (mirror export only). Consequence in §9.2: the
  readable backing is a documented exception with a verify gate, not a
  second normal.
- **D10 — `retain_until` and `legal_hold` in the model now, delete
  refusal now, full enforcement in a later stage.** Accepted as
  recommended.
- **D11 — The reference builds its own local content-addressed backing
  and speaks S3 only as a client;** Garage stays the named alternative
  for a node that needs an S3 service, MinIO is not considered.
  Accepted as recommended.
- **D12 — RFC-0034 is written now; building starts after RFC-0031's
  steps 1–3.** RFC-0032 stayed reserved for events at the time; it was
  filled 2026-09-11. Accepted as recommended.

## Deutsche Zusammenfassung

**Worum es geht.** Eine App legt ihre Dateien heute in ihrem eigenen
Storage-Mount ab. Das ist richtig für die Isolation und falsch für die
drei Dinge, die eine Datei in einer kleinen Firma überleben muss: ein
Backup, das wissen muss, was es enthält; eine zweite App, die dasselbe
Dokument braucht; und eine Ablagebox, die irgendwann ersetzt wird.
Dieses RFC gibt der Plattform **einen Weg, eine Datei abzulegen, und
viele Wege, sie aufzubewahren**.

**Zwei Capabilities, derselbe Schnitt wie beim Zwilling (D1):**

- **`oaap.data.files`** — *Wo liegen die Bytes, und wie werden sie
  kopiert?* Repositories je Mandant, **Backings** dahinter (das
  Datenverzeichnis des Knotens, jeder S3-kompatible Dienst, eine
  SMB-Freigabe), Backup-Umfang, die isolierte Sicht für die
  Generalprobe, das Umspeichern. Weiß nichts von Dokumenten.
- **`oaap.data.documents`** — *Was ist ein Dokument, wem gehört es,
  woran hängt es?* Stabile Plattform-ID, Metadaten, unveränderliche
  Versionen, Verknüpfung mit einem Zwillingsobjekt, Aufbewahrungsfrist.
  Nur damit spricht eine App.

Das ist die ArchiveLink-Lehre: SAP hat die **Verknüpfungstabelle** immer
vom **Content Repository** getrennt, und nur deshalb ließ sich ein
Repository tauschen, ohne dass eine Anwendung es merkte. Hier ist der
Zwilling die Verknüpfungstabelle und `files` das Repository.

**Der Satz, der alles trägt:** *Eine App hält die Identität eines
Dokuments, nie seinen Ort. Bytes werden einmal geschrieben und nie
verändert; wo sie liegen, ist Sache der Plattform und darf sich jederzeit
ändern.*

**Das Dokument (D2, D3).** Opake Plattform-ID plus beliebig viele
Quellschlüssel (der S3-Key der App, eine Nummer, ein Dateiname) — RFC-0031
D3 auf Dateien angewandt. **Versionen sind unveränderlich**: ein neuer
Upload ist eine neue Version mit eigener ID, nichts wird überschrieben.
Jede Version trägt Hash, Größe, Typ, Erfassungszeit, Prinzipal,
`retain_until`, `legal_hold` — und **den Zeiger auf ihr Backing**. Weil
der Zeiger an der Version hängt und nicht am Repository, ist Umspeichern
ein Hintergrundjob je Version (kopieren, zurücklesen, Hash prüfen,
Zeiger umsetzen, Quelle nach Schonfrist löschen), **ohne Wartungsmodus**,
sichtbar im Portal wie ein Deployment. Der Portal-Ablauf aus dem
Ideenspeicher vom 04.08. schrumpft auf „Vorgabe setzen, Move starten,
zuschauen".

**Backings (D11).** `local` ist ein eigener, Hash-adressierter Speicher
im Datenverzeichnis (je Mandant dedupliziert, nie über Mandanten hinweg),
damit heute schon im Backup, ohne neue Komponente. `s3` und `smb` werden
**als Client** gesprochen; Zugangsdaten liegen in einer 0600-Datei auf
dem Host, nie bei der App, nie im Backup (RFC-0033 D1 wörtlich). Garage
bleibt die benannte Alternative, falls ein Knoten je einen echten
S3-Dienst braucht; MinIO wird wegen der 2025 verschlechterten Lizenz-
und Pflegelage nicht betrachtet.

**Bindung (D6).** Wie Destinations: Standard keins, das Manifest nennt
einen **Bedarf** (`documents.needs`), der Betreiber **bindet** ein
Repository des Mandanten daran, protokolliert, widerrufbar. Eine
Generalprobe wird nur an ihr Overlay gebunden.

**Zwilling (D7).** Das Dokument ist **kein** Zwillingsobjekt, sondern
eine eigene Sache mit eigener ID; `documents` läuft auch ohne Zwilling.
Wo der Zwilling existiert, gibt es eine Relation `has_document` als
Referenz nach RFC-0031 D6 (ID, Titel, Typ, Herkunft, sonst nichts). Der
Zwillings-Browser zeigt die Montageakte am Auftrag; mehrere Apps finden
dieselben Dokumente über dasselbe Objekt; ein Merge trägt die Relationen
mit.

**Schnittstellen (D8).** Nach innen die eigene Dokumenten-API (ablegen,
Version anfügen, holen, auflisten nach Text/Objekt/Schlüssel, verknüpfen,
weich löschen) **plus ein S3-Gesicht** auf dasselbe Repository: Bucket =
Repository, Key = Quellschlüssel, ein `PUT` auf einen vorhandenen Key
wird zur neuen Version, Zugangsdaten = Maschinen-Principal (RFC-0027),
keine zweite Schlüsselwelt. Damit laufen Paperless, Nextcloud und
Fremd-Apps ohne Umbau. CMIS und das ArchiveLink-Protokoll nur als
**Adapter nach außen**, gebaut bei realem Bedarf; die Dokumenten-API ist
so geschnitten, dass sie sie tragen kann.

**Backup (D5).** `local`-Backings liegen im Backup wie heute. Externe
Backings werden **referenziert, nicht kopiert**, aber jedes Backup trägt
ein **Manifest** (Backing-Definition ohne Geheimnis, alle Versionen mit
ID, Hash, Größe). Nach einer Wiederherstellung sagt `oaap files verify`,
**welche** Dokumente fehlen — mit ID und Titel, nicht nur „die NAS war
nicht dabei". Die Metadaten liegen ohnehin in `oaap.data.store` und
damit immer im Backup.

**Generalprobe (D4).** Metadaten werden mit dem Schema kopiert (billig,
RFC-0031 D8); Bytes werden **lesend geteilt**, weil Versionen
unveränderlich sind. Alles, was die Probe schreibt, geht in ein
**Overlay-Backing**, das mit ihr entsteht, nur an sie gebunden ist und
mit ihr gelöscht wird. Keine Terabyte-Kopie, nichts erreicht die
Produktion, Verweigerung mit Grund wie in RFC-0030.

**Der menschliche Ordner (D9, abweichend von der Empfehlung).**
Bernds Ordnerwelt auf der Synology ist ein **Spiegel-Export**: eine
Regel je Repository mit Pfadvorlage, die über den Zwilling aufgelöst
wird (`{Kundennummer Kundenname}/{Auftrag}/{Datum} {Titel}.pdf`),
einseitig geschrieben, nie zurückgelesen — ein Schaufenster, das
System der Wahrheit bleibt das Repository. **Später** kommt als
ausdrücklich **fragil** markierter Sonderfall ein Backing, dessen
Schlüssel menschliche Pfade sind, für den Kunden, der keine zweite Kopie
duldet: Umbenennen auf der Freigabe bricht die Hash-Prüfung, das Dokument
zeigt „Inhalt fehlt", `verify` meldet es, kein Move ohne vorheriges
`verify`.

**Aufbewahrung (D10).** `retain_until` und `legal_hold` jetzt im Modell,
Löschen wird darunter **jetzt schon verweigert**; Sweep, Nachweis und
Prüfer-Export folgen in einer eigenen Stufe. Treiber ist die GoBD:
Abnahmeprotokolle und Rechnungen sind Geschäftsbelege, und ArchiveLink
gab es genau dafür.

**Nicht-Ziele:** kein DMS (Volltext, OCR, Workflow), kein CMIS-Server,
kein Sync-Client, keine mandantenübergreifende Deduplizierung, keine
Replikation über Knoten (das ist RFC-0032/0033), keine
Plattform-Verschlüsselung im ersten Wurf.

**Staffelung (D12), Bau nach RFC-0031 Schritt 1–3:** (1) `files` lokal;
(2) `documents` mit API, Bindung, Zwillings-Relation, Fristen,
Overlay; (3) S3-Gesicht mit Paperless als Beweis; (4) externe Backings,
Manifest, `verify`, der Move — Bernds Synology als Beweis; (5)
Spiegel-Export; (6) Fristen-Durchsetzung; (7) fragiles Backing und
Adapter bei Bedarf.

**Alle zwölf Entscheidungen stehen (Jörg, 08.09.).** Elf folgen der
Empfehlung; D9 geht darüber hinaus (Sicht jetzt, fragiles Backing
später). Nichts gebaut.

## Deutsche Zusammenfassung (§14, 2026-09-22 — Stufe 1 gebaut, Stufe 4 entworfen)

**Gebaut ist Stufe 1**, der reine Byte-Speicher (`oaap.data.files` 0.1,
Referenz 0.1.113): Inhalte werden über ihre Prüfsumme abgelegt und
gefunden, je Mandant getrennt, und der Speicher kann gefragt werden, ob
er noch hält, was er zu halten behauptet. Beim Bauen hat sich dieser
RFC an einer Stelle selbst korrigiert: §3.3 behauptete, der Speicher sei
„im Datenverzeichnis, also in der Sicherung". Gesichert wird aber eine
aufgeschriebene **Liste von Pfaden** — und ein neues Unterverzeichnis ist
so einer Liste unsichtbar, auf die einzige Art, die zählt: Der Befehl
gelingt weiter, und das Archiv spielt weiter zurück. Dieselbe Gestalt
wie die Lücke vom 05.09. Jetzt steht es in Sicherung, Wiederherstellung,
Mandantenarchiv — und je Mandant, damit es auch mit ausgenommenen
Mandanten stimmt.

**Und jetzt der Teil, der für die Videoentscheidung zählt.** Die Frage
war: Die nächtliche Sicherung stoppt die Container fürs Kopieren, und
100 GB Video machen daraus Stunden. Löst RFC-0034 das? Die Antwort hat
zwei Hälften, und **welche gilt, entscheidet der Videodienst, den wir
wählen — nicht dieser RFC.**

**Fall A — der Dienst verwaltet seinen Speicher selbst.** PeerTube und
jedes vergleichbare Produkt tun das: eigene Verzeichnisse, eigene
Datenbank, eigener Dateibegriff. Sie werden nicht über OAAP ablegen, und
sie dazu zu bringen wäre eine Abspaltung, keine Anbindung.

- RFC-0034 bringt hier **nichts**. Die Bytes sind der gewöhnliche
  Speicher einer Instanz, und die nächtliche Kopie läuft durch alles.
- Die Antwort, die es trotzdem gibt, ist **RFC-0029 D5b — und die ist
  seit heute gebaut**: Den Videodienst in einen eigenen Mandanten
  stellen und **diesen Mandanten aus der Knotensicherung ausnehmen**,
  mit festgehaltener Begründung, und seinen Speicher getrennt sichern
  (Schnappschuss auf dem NAS oder der Export des Dienstes selbst). Das
  Archiv schreibt die Auslassung auf, die Wiederherstellung nennt sie
  und lässt die Instanzen ruhen, und der Mandant liest es in seinem
  eigenen Protokoll. Das nächtliche Fenster ist wieder Minuten lang.
- Der Preis, offen gesagt: Die Plattform weiß dann nicht mehr, was in
  dieser Mediathek liegt. Es gibt keine Prüfung je Dokument, weil es
  keine Dokumente gibt — nur ein Verzeichnis, um das sich jemand anders
  kümmert.

**Fall B — der Dienst legt über die Plattform ab.** Er spricht die
S3-Fassade (Stufe 3) gegen eine Ablage, deren Standard-Hintergrund
extern liegt: OAAP hält Identität, Metadaten, Aufbewahrung und den
Bezug zum Zwilling, das NAS oder der Bucket hält die Bytes.

- Dafür ist dieser RFC geschrieben, und §7 beantwortet die
  Stillstandsfrage direkt: Ins Archiv wandert ein **Verzeichnis der
  Kennungen und Prüfsummen**, keine Gigabytes.
- Er beantwortet außerdem Fragen, die Fall A gar nicht stellen kann:
  *welche* Aufnahme nach einem Plattenausfall fehlt, wie lange eine
  Aufnahme aufbewahrt werden muss, woran sie im Zwilling hängt, und was
  eine Generalprobe davon sieht.
- Der Preis: Der Dienst muss einer sein, den wir auf einen S3-Endpunkt
  richten können und mit dem wir dann zufrieden sind — das verengt das
  Feld erheblich, womöglich auf etwas, das wir eher bauen als
  übernehmen.

**Was das für die Wahl bedeutet** (ein Entscheidungskriterium, keine
Produktempfehlung):

- Wird ein Dienst **so übernommen, wie er ist, plane mit Fall A** — und
  das, was ihn erträglich macht, existiert seit heute. RFC-0034 liegt
  dann für Video gar nicht auf dem kritischen Pfad, und Stufe 4 wird
  gebaut, wenn Dokumente sie brauchen, nicht wenn Video sie braucht.
- Ist **S3-fähige Ablage eine harte Anforderung, muss das VOR der
  Produktwahl gesagt werden** — es ist die eine Eigenschaft, die
  entscheidet, in welcher der beiden Welten wir landen, und sie
  vorher zu fordern ist viel billiger, als sie nachträglich
  einzubauen.
- **In beiden Fällen liegt der Speicher außerhalb des Knotens.** Fall A
  legt ihn außerhalb unserer Sicht, Fall B außerhalb unseres Archivs,
  aber innerhalb unserer Buchführung. Genau dieser Unterschied ist der
  ganze Wert von Stufe 4 — und er gehört vor die Produktwahl, nicht
  dahinter.


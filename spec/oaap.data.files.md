# oaap.data.files — Where the Bytes Live

- **ID:** `oaap.data.files`
- **Version:** 0.1.1
- **Maturity:** draft (0.1 is RFC-0034 Stufe 1 and only that: the
  node's own content-addressed store, `put`/`get`/`verify`, tenant
  isolation by path, and the archive question answered. External
  backings — S3, SMB — and the move between them are Stufe 4 and are
  named here as the frontier, not specified)
- **Based on:** RFC-0034 (documents & file storage, D1/D3/D11),
  `oaap.core.tenant` (the tenant id is the isolation boundary, never
  the label), `oaap.data.backup` (this store is archive content),
  RFC-0030 (the rehearsal reads these bytes read-only)

## 1. Purpose

**Where the bytes live, and how they are copied.** This capability
never sees a title, a link, an owner or a retention date. It stores
content and returns it by hash.

The other half — what a document *is*, whom it belongs to, what it is
attached to, how long it must be kept — is `oaap.data.documents`
(RFC-0034 D1) and is **not** this spec. The split is deliberate and it
is what makes both halves testable: the byte layer against no document
semantics at all, the document layer against a single local backing.

An application never talks to this capability. It talks to
`oaap.data.documents`, which asks here for bytes.

## 2. Interface

### 2.1 The local backing (RFC-0034 D11, §3.3)

The reference implementation carries its own content-addressed store
under the platform data directory:

```
<data>/files/<tenant-id>/<first two hex chars>/<sha256>
```

- **The name is the content.** A file is addressed by the SHA-256 of
  its bytes and by nothing else. Writing the same content twice is a
  no-op, and the store can therefore be asked whether it still holds
  what it says it holds without any second record to compare against
  (2.3).
- **The tenant is part of the path, not a column.** One tenant's bytes
  MUST NOT be addressable from another tenant's store. A lookup MUST
  take the tenant and the hash together; a lookup by hash alone would
  let one customer ask whether another holds a given file, and for many
  kinds of document the existence of a specific file *is* the
  information.
- **Identical content is stored once per tenant and never deduplicated
  across tenants.** This costs disk on a node whose customers happen to
  hold the same file, and it is the right trade: cross-tenant
  deduplication would make one customer's storage cost and one
  customer's deletion depend on another customer's data.
- **A write MUST be atomic.** Content is written under a temporary name
  in the same directory and renamed into place, so a half-written file
  can never be found by its hash. An interrupted write may leave a
  temporary; it MUST NOT leave a lie.
- The fan-out directory is not decoration: a single directory holding
  a hundred thousand entries is slow to enumerate on every filesystem
  this platform targets.

### 2.2 Storing and reading

- **`put(tenant, bytes) -> (sha256, stored)`**, where `stored` says
  whether anything was written. It MUST accept an **expected hash** and
  MUST refuse when the content does not match it. Filing the bytes
  under their real hash instead would record a damaged transfer as a
  successful upload — the one failure this layer exists to make
  impossible.
- **`get(tenant, sha256)`** returns the content or nothing. It MUST NOT
  fall back to another tenant's store, and MUST NOT distinguish "this
  tenant does not have it" from "nobody has it".

### 2.3 Verification

The implementation MUST offer an operation that re-reads every stored
file and checks it against its own name, reporting:

- content that **no longer hashes to its name** — silent corruption,
  the case backups exist for and the case nobody notices;
- a **name that is not a content hash** — something other than the
  platform wrote into the store;
- a file in the **wrong fan-out directory** — the same, less obviously:
  it will never be found by its hash again.

Each finding MUST name the tenant and the file and MUST say what to do.
"Corruption detected" without a next step is a worry, not a report.

### 2.4 The archive (RFC-0034 §7, and a warning)

The store lies inside the platform data directory, **and that is not by
itself enough**. Where an implementation's backup archives a written
list of paths rather than the directory as a whole, a new subdirectory
is invisible to that list — and invisible in the only way that matters,
because the backup still succeeds and the archive still restores. The
implementation MUST therefore name this store in its backup content and
in its restore, and MUST do so per tenant wherever a tenant may be
excluded from the node archive (`oaap.data.backup` 2.1.2): an excluded
customer's bytes are that customer's bytes.

*Measured while building 0.1: the reference's backup path list did not
contain the new directory, exactly as the 2026-09-05 gap had not
contained `tenants/`.*

The restore MUST ask the **archive** whether it carries this store,
never the version number — naming a path an older archive does not hold
fails the whole restore over a directory that was never meant to be
there.

## 3. Security requirements

- Stored content is readable only by the platform (mode `0600`).
- The tenant boundary is the path, and every operation takes the
  tenant. There is no "look everywhere" call.
- This capability holds **no credential** in 0.1, because the only
  backing is local. When external backings arrive (Stufe 4), their
  credentials live in a `0600` file on the host, never in an instance's
  environment, never in an archive, and no app ever sees them
  (RFC-0034 §3.2, RFC-0033 D1 word for word).

## 4. Out of scope for 0.1 — and why it is named rather than silent

- **External backings (`s3`, `smb`) and the move between them**
  (RFC-0034 §3.2/§3.4, Stufe 4). This is where the interesting
  questions are, and they are not answered here.
- **Deletion.** There is no way to remove content in 0.1, deliberately:
  bytes are deleted because a *document* may be deleted, and that is
  `oaap.data.documents` with its retention rules (RFC-0034 §10). A byte
  layer that can delete on its own is a byte layer that can delete
  something a document version still points at.
- **Documents**: identity, versions, metadata, bindings, the twin
  relation, the S3 face, the mirror export. All `oaap.data.documents`.

## 5. Conformance tests (described)

1. The same content stored twice writes once; the same content for two
   tenants writes twice.
2. Content only one tenant holds is not findable by another, and the
   answer does not reveal that it exists elsewhere.
3. A `put` with a wrong expected hash refuses **and leaves nothing
   behind** under the real hash.
4. Verification finds: altered content, a non-hash name, a file in the
   wrong fan-out directory — and names the remedy for the first.
5. The node archive contains the store; with a tenant excluded
   (`oaap.data.backup` 2.1.2) it contains the other tenants' bytes and
   not that tenant's; the restore asks the archive whether the store is
   in it.
6. **Every operation is reachable under the name the documentation
   uses for it.** Not a formality: in the reference implementation the
   verification existed and worked, while the spelling RFC-0034 names
   three times (`oaap files verify`) was refused by the command
   wrapper, which knew every other node-wide capability and not this
   one. A capability that answers only to an undocumented spelling is
   not delivered, and the gap is invisible to every test that calls the
   function directly.

## 6. Dependencies

`oaap.core.tenant` (the boundary), `oaap.data.backup` (archive
content), `oaap.data.store` — **not** required by 0.1: the byte store
is files on disk and needs no database. `oaap.data.documents` will
require it.

## 7. Maturity

Draft. Built and tested; not yet exercised on a node with real volume,
which is the whole point of Stufe 4 and of the video question that
prompted it. Conformance test 6 was added after the first build failed
it (0.1.114).

## Deutsche Zusammenfassung (v0.1 — der Byte-Speicher, und nur er)

**Was diese Fähigkeit beantwortet:** *Wo liegen die Bytes, und wie
werden sie kopiert?* Sie sieht nie einen Titel, einen Verweis, einen
Eigentümer oder eine Aufbewahrungsfrist. Sie legt Inhalte ab und gibt
sie über ihren Hash zurück. Die andere Hälfte — was ein Dokument *ist*,
wem es gehört, woran es hängt, wie lange es bleiben muss — ist
`oaap.data.documents` und steht hier ausdrücklich nicht. Dieser Schnitt
ist der Grund, warum sich beide Hälften einzeln prüfen lassen.

**Zwei Eigenschaften tragen alles Weitere:**

- **Der Name ist der Inhalt.** Adressiert wird über die SHA-256-Summe
  der Bytes und über nichts sonst. Denselben Inhalt zweimal zu
  schreiben ist folgenlos — und der Speicher kann gefragt werden, ob er
  noch hält, was er zu halten behauptet, ganz ohne eine zweite
  Aufzeichnung, gegen die man vergleichen müsste. Genau das findet die
  **stille Veränderung**: die Sorte Datenverlust, die niemand bemerkt,
  bis jemand die Datei braucht.
- **Der Mandant steht im Pfad, nicht in einer Spalte.** Die Bytes des
  einen Kunden sind aus dem Speicher des anderen nicht adressierbar,
  und eine Suche allein über den Hash gibt es nicht. Sonst könnte ein
  Kunde fragen, ob ein anderer eine bestimmte Datei hat — und bei
  vielen Dokumenten ist genau das schon die Information. Der Preis:
  gleicher Inhalt liegt bei zwei Kunden zweimal. Bewusst so, denn eine
  mandantenübergreifende Entdoppelung machte Speicherkosten und
  Löschung des einen Kunden von den Daten des anderen abhängig.

**Eine kaputte Übertragung wird nicht als Tatsache abgelegt.** Wer beim
Ablegen sagt, welchen Hash er erwartet, bekommt eine Ablehnung, wenn es
ein anderer ist — statt dass die beschädigten Bytes unter ihrem echten
Hash landen und damit als erfolgreicher Upload gelten.

**Und der Fund beim Bauen, der es in die Spezifikation geschafft hat:**
„Es liegt im Datenverzeichnis, also ist es in der Sicherung" stimmt
**nicht**. Gesichert wird eine aufgeschriebene Liste von Pfaden, und ein
neues Unterverzeichnis ist einer Liste, die niemand nachgezogen hat,
unsichtbar — auf die einzige Art, die zählt: Der Befehl gelingt weiter,
und das Archiv spielt weiter zurück. Dieselbe Gestalt wie die Lücke vom
05.09.2026. Deshalb steht es jetzt als Muss in der Spezifikation, je
Mandant, damit es auch mit ausgenommenen Mandanten stimmt.

**Was 0.1 bewusst nicht kann:** externe Ablagen (S3, SMB) und das
Verschieben dazwischen — das ist Stufe 4, und dort sitzen die
interessanten Fragen. Und **Löschen**: Bytes verschwinden, weil ein
*Dokument* verschwinden darf, und das entscheidet die Dokumentschicht
mit ihren Aufbewahrungsregeln. Eine Byte-Schicht, die von sich aus
löschen kann, kann etwas löschen, worauf eine Dokumentfassung noch
zeigt.

**Nachtrag 0.1.1 (22.09.2026), beim Vorbereiten des Flottenlaufs
gefunden:** Die Pruefung gab es, sie lief, sie war richtig — nur war sie
unter dem Namen, den RFC-0034 dreimal nennt (`oaap files verify`), nicht
erreichbar. Der Befehlsaufsatz an der Maschine kannte jede andere
knotenweite Faehigkeit und diese eine nicht; gegangen waere nur
`oaap app files verify`, und das steht nirgends. **Eine Faehigkeit, die
nur auf eine undokumentierte Schreibweise hoert, ist nicht geliefert** —
und kein Test, der die Funktion direkt aufruft, kann das je bemerken.
Deshalb ist es jetzt Konformitaetstest 6.

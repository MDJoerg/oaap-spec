# RFC-0050: A Package Catalog — Released Packages as a Store Source, with Distribution to Recipient Nodes

- **Status:** **Proposed (2026-10-01)** — design only; Jörg decided the three
  scoping questions (operator-only upload, visibility "all" first, record as
  RFC). Nothing built.
- **Date:** 2026-10-01
- **Authors:** Jörg (the need and the three decisions), Claude (facts read in
  the reference code, design)
- **Depends on:** RFC-0012 (store sources and list format), RFC-0019 (artifact
  deployment), RFC-0020 (promotion), RFC-0022 (tenant as boundary, the store
  as the catalogue for whoever installs into a tenant), RFC-0049 (releases and
  updates — this RFC is its stage 2 with a user interface)
- **Driver:** On a multi-tenant node, installing or updating a released
  package that is not in a public store means: export a ZIP, move it by hand
  across two machines, install it as a test instance, promote it. That does
  not scale to many tenants and many nodes, and the tenant administrator
  cannot do it at all.

## Summary

An operator-run **catalog** (an OAAP app in an operator tenant) holds uploaded
packages with a version history and checksums. It publishes itself as a
**store source** whose entries point at ZIP packages instead of Git
repositories. The existing store page then lists those apps for every tenant
administrator, installs by app id (the host resolves it — the property that
keeps a compromised portal harmless), and offers "update to vX" as it already
does. Later, a catalog on the reference node can **supply** registered
recipient nodes directly, so a tested package never travels through a
laptop.

## 1. Facts (read in the reference code, 2026-10-01)

- The portal's store page is shown to `server_admin` **and** `tenant_admin`
  (`can_store`): "the catalogue is for whoever may install into a tenant
  (RFC-0022 §4); the sources stay the node operator's". Nothing new is needed
  to put a catalogue in front of a tenant administrator.
- One-click install sends an **app id** (and at most a source id). The host
  resolves it against the *configured* sources; a request can pick among them
  and can never add one. Unverified sources need an explicit confirmation.
- A store-list entry today names a **Git package** (`package{git,path[,ref]}`);
  no entry can name a ZIP. ZIP installs exist only on the private path of
  RFC-0019 (`oaap app install <file.zip>`), which verifies a checksum and
  unpacks defensively.
- The store install of a *new* instance lands on the **production** channel;
  there is no way in the store dialog to say "with a test instance". The CLI
  has `--channel`; a redeploy keeps the instance's channel.
- Store sources are **per node**, written by `oaap store add-source`, with a
  trust class (`verified`/`unverified`). They are not per tenant.
- A promotion on the reference node (RFC-0020) already defines "released":
  the exact bytes that run in production there.

## 2. Decisions taken

1. **Only the operator uploads.** Tenants cannot publish into the catalog.
   (A tenant that needs its own private package keeps the existing artifact
   path of RFC-0019/RFC-0037.)
2. **Visibility: "all" first.** Every tenant administrator of a node that has
   the catalog as a source sees every released package. A per-tenant filter is
   a later extension (§6, question 1).
3. **Recorded as an RFC** because it extends the store-list format (RFC-0012)
   and the store install (spec `oaap.apps.runtime` 2.6).

## 3. Stage 1 — the catalog app

An OAAP app (working name `package-catalog`) in an operator tenant:

- **Upload** of a package ZIP by the operator; the app reads `oaap-app.yaml`
  from it (id, name, version, description), computes **SHA-256**, rejects a
  version that already exists for that app id, and keeps the file.
- **Version history** per app id: version, checksum, size, uploader, date,
  a free note, and the flag **released** (the operator sets it; a package that
  is uploaded but not released is invisible to the store).
- **Download** of any stored ZIP for the operator (the "give me the ZIP" case).
- **Retention:** keep all released versions; unreleased uploads may be
  deleted. Deleting a released version needs a reason (as `backup exclude`).
- **Backup:** the catalog's storage is part of the node archive like any app.
- The app never runs uploaded code and does not unpack it beyond reading the
  manifest. Reading the manifest uses the same bounded, defensive unpacking as
  RFC-0019 §5.

## 4. Stage 2 — the catalog as a store source

- The catalog serves a **store list** (format `0.2` extended, RFC-0012 §1) at a
  stable address. Each entry carries `package{zip, sha256, size}` in place of
  `package{git, path}`. A reader must keep accepting `git` packages.
- The node registers it as a source of trust class `verified`
  (`oaap store add-source`). Same-node catalog: an internal address; no
  public exposure is required.
- The host fetches the ZIP **by the app id it resolved**, verifies the
  checksum from the list *and* from the file, and then installs with the
  existing artifact code path. A mismatch aborts before anything is unpacked.
- **Updates:** the store page's "update to vX" appears when the list carries a
  higher version than the instance runs — no new mechanism.
- **Channel choice in the dialog:** the store install gains one choice for a
  new instance: *with a test instance* (installs `<name>-test`, promote
  later) or *straight to production* (the default today). A tenant
  administrator decides per app; the operator does not impose either.
- **Access control for the catalog itself:** the list and the downloads are
  reachable only by registered nodes (a token per recipient, §5), never by an
  anonymous caller. A package is code that the node builds and runs; the list
  is therefore as sensitive as a store source of class `verified`.

## 5. Stage 3 — supplying recipient nodes from the reference node

Jörg's wish: development, test and pre-production run on the reference node;
a tested package should go from there to one or more registered **recipients**
without the download-and-upload detour.

- A **recipient** is a node registered at the catalog (name, a per-recipient
  token, optionally a note). The catalog on the reference node serves each
  recipient its own list, containing only what has been **supplied** to it.
- **Supplying is a deliberate, manual act:** on a package version the operator
  chooses "supply to: A, B". Nothing leaves the reference node unasked.
  "Supplied" makes the package *available* in the recipient's store; whether
  and when a tenant there installs or updates it is the recipient's
  (RFC-0049 policy: automatic, hold, window — within the operator's limits).
- **Feeding the catalog from a promotion** (optional, later): a promotion on
  the reference node may place the promoted package into the catalog as an
  *unreleased* entry, so "released" still means a human's decision.
- **Pull, not push:** a recipient fetches from the reference node's catalog
  (the same direction and trust reasoning as the pull-based backup). The
  reference node holds no access into recipients; recipients hold one token
  that can only read their own list and download what it names.
- **Rules by condition** ("supply every production promotion of app X to ring
  1") are a later step on top of the manual act, not a replacement for it.

## 6. Answers (Jörg, 2026-10-01) and what follows

1. **Per-tenant visibility: not ruled out, so not blocked.** First version:
   "all". The list format and the source resolution MUST leave room for a
   tenant filter (an optional `visible_to` on an entry and on a version, absent
   = everybody), so adding it later changes no reader.
2. **Where the catalog runs.** The catalog is a *function* ("exchange ZIPs
   with history"), not a place. Usually it runs on the node where the packages
   are installed (the multi-tenant node itself). Later it may be offered as a
   shared service, so that **several hosting nodes** (e.g. several
   multi-tenant nodes for associations) take their newest released versions
   from **one reference catalog**. Consequences for the design: a catalog is
   both a *source* (it serves a list) and may itself *be a recipient* of
   another catalog (§5 pull, per-recipient token), so a local catalog can
   mirror a central one; a node needs no more than one registered source to
   reach all of it.
3. **Trust at the first install: a configuration option.** Default
   `verified`; an operator may set the catalog source to require explicit
   confirmation per app (like `unverified` sources) so that he can try every
   version in his own test portal before it reaches his tenants.
4. **The channel choice is per installation, not a tenant default.** Examples
   from Jörg: a link service needs no test instance; a website definitely
   does; the association portal not necessarily, but it is useful for
   training. The store dialog therefore asks on each install: *with a test
   instance* or *straight to production*.

## 7. Out of scope

Billing or entitlement per package; signed packages (the checksum protects
integrity in transit, not the publisher — the operator is the publisher);
tenant-uploaded packages; automatic installation without a human or a policy
(RFC-0049 owns the policy).

## Zusammenfassung (deutsch)

Ein **Paketkatalog** als OAAP-App im Betreiber-Mandanten: Der Betreiber lädt
Pakete (ZIP) hoch, die App rechnet die Prüfsumme, führt die **Versionshistorie**
und das Kennzeichen „freigegeben" und gibt die ZIPs heraus. Der Katalog
veröffentlicht sich als **Store-Quelle**: Einträge verweisen auf ein ZIP statt
auf ein Git-Paket (Listenformat 0.2 erweitert). Dann sehen die
Mandantenverwalter die Apps in der vorhandenen Store-Seite (die zeigt sie
Mandantenverwaltern schon heute), installieren per App-Kennung — der Knoten löst
sie selbst auf und prüft die Prüfsumme — und bekommen „Aktualisieren auf vX"
ohne neuen Mechanismus. Im Dialog kommt eine Wahl dazu: **mit Testinstanz oder
gleich produktiv**. Entschieden (Jörg, 01.10.): **nur der Betreiber lädt
hoch**, **Sichtbarkeit zunächst „alle"**, festgehalten als RFC. Perspektivisch
**Belieferung** (Stufe 3): Auf dem Referenzknoten (Entwicklung, Test,
Vorproduktiv) steht der Katalog; **registrierte Empfängerknoten** holen sich
dort, was der Betreiber ausdrücklich für sie bereitgestellt hat (manuell,
Abholung per Token, kein Zugang des Referenzknotens in die Empfänger). Damit
entfällt Herunter- und Hochladen über den Arbeitsplatz. Ob und wann ein Mandant
im Empfänger aktualisiert, regelt die Richtlinie aus RFC-0049. Die vier Fragen sind am 01.10. beantwortet
(§6): Sichtbarkeit je Mandant ist nicht ausgeschlossen und wird im Format
offengehalten; der Katalog ist eine Funktion, meist auf dem Installationsknoten,
später auch als geteilter Referenzkatalog für mehrere Hosting-Knoten; die
Vertrauensstufe am ersten Tag ist eine Konfigurationsoption; die Wahl
Testinstanz oder produktiv gilt je Installation. Nichts gebaut.

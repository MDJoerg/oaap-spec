# RFC-0057: A Database for an App — Managed Postgres From the Platform, Declared in the Manifest

- **Status:** **Draft (2026-10-05)** — eight decisions (D1–D8) are open and
  wait for Jörg. Nothing is built. The measurements of §2 were made by hand on
  `oaap-test` and removed again.
- **Date:** 2026-10-05
- **Authors:** Jörg (the need: a CAP application should find its database on
  the platform, as it does on BTP), Claude (measurement and write-up)
- **Depends on:** RFC-0031 §7 (the store; names `app_<instance>` as the later
  case), RFC-0016 (one network per instance), RFC-0011 (node profile `store`),
  RFC-0026 (identity is an id, names change), RFC-0029 (backup, tenant archive),
  RFC-0030 (rehearsal), RFC-0004 (manifest)
- **Changes:** `oaap.data.store` 0.1 → 0.2, `oaap.apps.runtime` (manifest 0.7,
  install, removal, rehearsal), `oaap.data.backup` (tenant archive)
- **Origin:** the CAP spike of 2026-10-05 (`oaap-lab/cap-spike/README.md`,
  finding 2)

## Summary

An app that needs a relational database declares it in its manifest. At
install the platform creates **one database and one role** for that instance in
the node's managed Postgres, hands the instance its connection data as
environment variables, and opens a network path from the instance to the store.
The database follows the instance through its life: kept on a redeploy, copied
for a rehearsal, carried in a backup as a dump, dropped on a purge.

Today the store serves exactly one client, the twin service. An app that needs
Postgres brings its own container. This RFC makes the store usable by apps —
and, because apps are not trusted the way the twin is, it first closes what the
store leaves open for a client it does not trust.

## 1. Why

1. **RFC-0031 §7 already promised it.** The store was specified as "a schema per
   tenant and purpose (`twin_<tenant>`, later `app_<instance>` for apps that ask
   for Postgres)". `oaap.data.store` 0.1 names the case and does not build it.
2. **An app that brings its own Postgres is backed up as files.** Its data
   directory is a storage mount, copied while the app is stopped.
   `oaap.data.store` §2.4 says why the store itself is dumped instead: a dump
   survives a Postgres major-version change, a data directory does not. That
   reasoning applies to an app's database just as well, and today it is not
   applied there.
3. **A rehearsal needs a copy of the data.** RFC-0030 tests new code on a copy
   of production data. For a bundled Postgres the copy is a copy of the data
   directory; for a database in the store the platform can make it with a dump
   and give it its own role (§2.2, measured).
4. **Portability from BTP.** A CAP application binds to a database service the
   platform provides. With this RFC the same application finds one here; without
   it, every ported application gains a second container and a password the
   operator sets by hand.

What this RFC does **not** claim: that it saves much memory. Measured on
`oaap-test`, a bundled `postgres:16-alpine` holds 20–30 MB when idle; the store
holds 58 MB. The gain is one Postgres to maintain, dump and upgrade — not RAM.

## 2. Measured (2026-10-05, `oaap-test`, reference 0.1.193, PostgreSQL 16.15)

### 2.1 An application against the store (CAP spike, measurement B)

The CAP application of `oaap-lab/cap-spike` ran as a second instance against a
schema and a role made with `oaap data store create`. It created its five
tables, loaded its initial data and answered through the gateway with 200. Its
role could not read a table of the twin schema and could not create another
schema. No line of application code changed; four configuration values of the
instance pointed elsewhere.

Two things had to be done by hand, outside the platform:

- the role's password was typed into the instance configuration, and
- `docker network connect --alias store oaap-inst-<name> oaap-store-1` — the
  store was attached to that instance's network.

### 2.2 Schema or database (`program/messungen/store-app-datenbank-messung.sh`)

Two throwaway roles A and B, once as two schemas in the shared database
`postgres`, once as two databases. All objects were removed afterwards.

| | Schema in the shared database | Database per instance |
| --- | --- | --- |
| A reads B's rows | refused | cannot connect to B's database |
| A sees the **names** of B's tables and columns | **yes** (`pg_class`, `pg_attribute`) | no |
| A sees the names of the twin's tables | **yes** (10 tables) | no — unless it connects to `postgres`, see below |
| A sees schema names (they carry tenant ids) | **yes** | no |
| A sees database names | — | yes |
| A sees role names (the twin's carry tenant ids) | yes | **yes** |
| A reads password hashes (`pg_authid`) | refused | refused |
| A creates a further database | — | refused |

Further, for the database variant:

- **The shared database stays open by default.** A's role could connect to the
  database `postgres` and count the twin's tables there. PostgreSQL grants
  `CONNECT` on every database to everyone unless it is revoked; on `oaap-test`
  it is not revoked for `postgres`.
- **An extension needs the superuser.** `CREATE EXTENSION vector` as the owner
  of the database was refused ("Must be superuser").
- **A copy under a new role works without rewriting the dump.**
  `pg_dump --no-owner --no-acl A | psql` into a fresh database owned by a new
  role: 1000 of 1000 rows, the table owned by the new role; the original's role
  cannot enter the copy, the copy's role cannot enter the original.
- **A connection limit per role holds.** With `CONNECTION LIMIT 1` the second
  connection was refused ("too many connections for role").

### 2.3 Read, not measured

- The store's `pg_hba.conf` (read on the node) ends with
  `host all all all scram-sha-256`: every role, the superuser included, may log
  in with its password from every network the container is attached to.
- The node backup runs `pg_dumpall` (read in `appctl.py`), which covers every
  database and every role. A database made under this RFC would be in it. No
  backup was taken and restored to prove it.
- The tenant archive dumps one schema, `twin_<tenant>`, into
  `tenant-store-dump.sql`. No reader of that file was found in the reference
  (searched for the name): `oaap tenant adopt` does not replay it.
- A rehearsal instance gets no twin key, because the copy of the twin schema
  (RFC-0031 D8) is not built.
- The gateway's membership in an instance network is made by hand
  (`docker network connect`) and re-made on every path that recreates an app or
  the gateway. The store would need the same care.

## 3. Proposal

### 3.1 The manifest declares the need (manifest 0.7)

```yaml
database:
  engine: postgres        # the only engine
  extensions: [vector]    # optional, from the node's allow-list (§3.3)
```

One database per instance. A manifest with the section declares
`oaap_manifest: "0.7"` or newer. An app without it is unaffected and may keep
bringing its own container.

### 3.2 What the platform creates at install

For an instance with the section, on a node that carries `store`:

- a role and a database, both named `app_<instance-id>` — the instance **id**
  (RFC-0026), never its name, so a rename changes nothing;
- the role owns the database, has a generated password and a connection limit;
- `CONNECT` on the database is revoked from everyone else;
- the declared extensions are created by the platform, as the superuser, inside
  that database.

All of it is done from the host through the container's own socket, like every
other statement the store runs today. Nothing is created twice: a redeploy finds
the database and leaves it alone.

### 3.3 Extensions

An app cannot create an extension itself (§2.2). The node has an allow-list —
to begin with, what the store image ships and is safe to hand out: `vector`. A
manifest naming an extension outside the list is refused at install, with the
list in the message.

### 3.4 What the instance receives

| Variable | Value |
| --- | --- |
| `OAAP_DB_HOST` | `store` |
| `OAAP_DB_PORT` | `5432` |
| `OAAP_DB_NAME` | `app_<instance-id>` |
| `OAAP_DB_USER` | `app_<instance-id>` |
| `OAAP_DB_PASSWORD` | generated, url-safe |
| `OAAP_DB_URL` | `postgresql://…` built from the five above |

They are platform-owned like `OAAP_APP_SECRET`: reserved names, minted once,
not editable through `oaap app config`, never copied into a rehearsal. An app
whose product expects other names maps them in its own entrypoint, as the
Keycloak package already does for its bundled database.

### 3.5 The network path

The store joins the instance's network under the alias `store`, the way the
gateway joins it. The instance still reaches only the gateway, its own
containers and now the store; identity, portal and twin stay out of direct
reach. The
membership is re-made wherever the gateway's is, and additionally whenever the
store container is recreated.

Only instances that declared a database get the store on their network.

### 3.6 Closing the store for a client it does not trust

Before the first app is attached (stage 0, §5):

1. `CONNECT` on the database `postgres` is revoked from everyone and granted to
   the roles the platform's own services use there (the twin's). Existing nodes
   are migrated.
2. The superuser cannot log in over the network at all. The host needs only the
   local socket; `pg_hba.conf` gets a rule for that.
3. An app's role may connect only to the database that carries its own name
   (`pg_hba`: `sameuser`), in addition to the revoked `CONNECT`.

### 3.7 The database through the life of the instance

| Event | What happens to the database |
| --- | --- |
| redeploy, config change, restart | nothing |
| rename, new address | nothing (named by id) |
| `oaap app remove` | kept, like the storage; reinstalling under the same name finds it |
| `oaap app remove --purge`, `oaap app purge` | dropped with its role, named in what the purge says it deletes |
| rehearsal (RFC-0030) | copied into `app_<rehearsal-id>` under a new role (§2.2); if the copy cannot be made, the rehearsal is refused — it never starts on the production database and never on an empty one |
| end of the rehearsal | the copy and its role are dropped |
| promotion to production (RFC-0020) | each instance keeps its own database; the package moves, the data does not |
| node backup | in the dump of the whole store, as today |
| tenant archive | one dump per database of the tenant's instances, next to the twin's |
| `oaap tenant adopt`, move to another node | the dump is replayed into a database the target node creates; **the reader is built together with the writer** |

### 3.8 A node without `store`

Installing an app that declares a database on a node without the profile is
refused before anything is built, with the reason and the command that adds the
profile. Nothing falls back silently to a container.

### 3.9 What changes in `oaap.data.store`

0.1 says an app never sees a database credential. 0.2 says: **an app sees the
credential of its own database and of nothing else.** The twin's schemas remain
reachable only by the twin service. `oaap data store schemas` lists databases as
well, with instance, tenant and size.

## 4. Decisions for Jörg

| | Question | Recommendation |
| --- | --- | --- |
| **D1** | A **database** per instance, or a **schema** in the shared database as RFC-0031 §7 words it? | **Database.** In a shared database every app reads the names of every other tenant's tables and columns (§2.2). This departs from the wording of RFC-0031 §7, not from its intent. |
| **D2** | Network path: the store joins the instance network, or a separate proxy service in between? | **The store joins.** Measured, no new service; the price is one more membership to re-make. |
| **D3** | One database per instance, or a list? | **One.** A list invites apps to split what a rehearsal must copy as a whole. |
| **D4** | Extensions: an allow-list created by the platform, or none? | **Allow-list, starting with `vector`.** The app cannot create them itself. |
| **D5** | Node without `store`: refuse, or start a bundled Postgres automatically? | **Refuse**, with the reason. An automatic fallback would be a second way to the same place. |
| **D6** | `oaap app remove` without `--purge`: keep the database? | **Keep**, like the storage. |
| **D7** | Limits: a connection limit per role (default 20 of the node's 100), no disk quota? | **Yes.** PostgreSQL has no quota per database; the store view shows sizes instead. |
| **D8** | Move existing packages with a bundled Postgres (Keycloak) into the store? | **No, not in this RFC.** New packages may choose; a migration is its own piece of work. |

## 5. Build stages

- **Stage 0 — close the store (§3.6).** Revoke and grant, `pg_hba`, migration of
  existing nodes; measured with a role that must be refused at each of the three
  doors. No app-facing change.
- **Stage 1 — the database.** `oaap.data.store` 0.2, manifest 0.7, install,
  removal, purge, the six variables, the network membership. First consumer: the
  CAP spike without its bundled `db` service.
- **Stage 2 — copy and carry.** Rehearsal copy; tenant archive with its reader;
  move. Measured by a backup that is actually restored and an archive that is
  actually adopted.
- **Stage 3 — visibility.** Portal: the store view lists databases, sizes and
  connections per instance.

## 6. Security requirements

1. A role reaches exactly one database: its own. It is refused at the
   privilege (`CONNECT`) and at the login rule (`pg_hba`), independently.
2. The superuser has no network login.
3. The database and role are named by the instance id. No tenant label and no
   instance name appears in a name another role can list.
4. The connection data are delivered only as environment variables of the
   instance, never written into its mounts, never shown again after install.
5. A rehearsal never receives the production credentials and never runs on the
   production database.
6. A purge that drops a database says so before it does.
7. An archive that should contain a database dump and does not is a failed
   archive, not a smaller one (`oaap.data.backup`, the 9 KB lesson).

## 7. Open and not measured

- **Role names stay visible.** Any role can list all roles; the twin's are named
  `twin_<tenant-id>`. That is a tenant id, not a label, and no secret — but it
  is visible to every app with a database. Renaming the twin's roles is not part
  of this RFC.
- **One Postgres for all.** A slow or greedy app shares CPU, memory and I/O with
  the twin and with every other app. Only the number of connections is limited.
- **One version for all.** An app that needs another Postgres major version or
  an extension outside the list keeps bringing its own container.
- Not measured: restore of a node backup with app databases; a store recreated
  while instances are attached; the three rules of §3.6 against a running twin;
  arm64.

## 8. Non-goals

Password rotation; a second engine; a database shared between instances;
several tenants in one instance (the BTP subscription model — an extension of
RFC-0022, if an operator case becomes real); direct database access for people.

## Deutsche Zusammenfassung

**Worum es geht:** Eine App, die eine relationale Datenbank braucht, sagt das
im Manifest. Die Plattform legt beim Installieren **eine Datenbank und eine
Rolle** für genau diese Instanz im Postgres des Knotens an, gibt der Instanz
die Zugangsdaten als Umgebungsvariablen und öffnet den Netzweg dorthin. Heute
bringt jede solche App ihr eigenes Postgres als Container mit; der Store
bedient nur den Zwillingsdienst.

**Warum:** RFC-0031 hat es angekündigt (`app_<instanz>`), gebaut ist es nicht.
Eine mitgebrachte Datenbank wird als Dateikopie gesichert und übersteht keinen
Versionswechsel von Postgres; eine Generalprobe braucht eine Kopie der Daten;
und eine CAP-Anwendung erwartet, dass die Plattform ihr die Datenbank stellt.
Arbeitsspeicher spart es kaum (gemessen 20–30 MB je mitgebrachtem Postgres).

**Gemessen am 05.10. auf `oaap-test`:**

- Die CAP-App lief unverändert gegen ein Schema des Stores. Von Hand nötig
  waren das Passwort in der Instanz-Konfiguration und `docker network connect`.
- Liegen zwei Apps als **Schemas** in derselben Datenbank, liest die eine zwar
  keine Zeilen der anderen, sieht aber die **Namen ihrer Tabellen und
  Spalten** — auch die des Zwillings und anderer Mandanten.
- Bekommt jede App eine **eigene Datenbank**, sieht sie davon nichts. Sie kann
  sich aber in die gemeinsame Datenbank `postgres` verbinden, solange das
  Recht dort nicht entzogen ist.
- Eine Erweiterung wie `vector` kann nur der Superuser anlegen.
- Die Kopie für die Generalprobe gelingt als Dump in eine neue Datenbank unter
  neuer Rolle (1000 von 1000 Zeilen), und eine Obergrenze der Verbindungen je
  Rolle greift.

**Der Vorschlag in Stufen:** Zuerst den Store für Klienten schließen, denen man
nicht traut (Stufe 0: Verbindungsrecht entziehen, Superuser ohne Netz-Anmeldung,
jede Rolle nur in ihre Datenbank). Dann die Datenbank je Instanz mit
Manifest 0.7 (Stufe 1, erster Abnehmer ist der CAP-Spike ohne eigenen
Datenbank-Container). Dann Generalprobe, Mandantenarchiv und Umzug — Leser und
Schreiber zusammen (Stufe 2). Zuletzt die Anzeige im Portal (Stufe 3).

**Acht Entscheidungen für Jörg (D1–D8), mit Empfehlung:** eigene Datenbank
statt Schema (weicht vom Wortlaut in RFC-0031 §7 ab); der Store tritt dem
Instanznetz bei; eine Datenbank je Instanz; Erweiterungen aus einer Liste des
Knotens, angelegt von der Plattform; ein Knoten ohne `store` lehnt die
Installation ab; beim Entfernen ohne `--purge` bleibt die Datenbank;
Verbindungsgrenze je Rolle, kein Plattenkontingent; bestehende Pakete mit
eigenem Postgres (Keycloak) ziehen nicht um.

**Offen bleibt:** Rollennamen sind für jede Rolle sichtbar (die des Zwillings
tragen die Mandanten-ID), alle teilen sich ein Postgres in einer Version, und
ungemessen sind die Wiederherstellung einer Sicherung mit App-Datenbanken und
ein neu erzeugter Store bei angehängten Instanzen.

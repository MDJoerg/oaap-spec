# RFC-0110: A Wiki in the Tenant — a Contract for Knowledge, BookStack as the First Connector

- **Status:** **Accepted (2026-11-20)** — D1–D10 as recommended (Jörg:
  "Ja, wie empfohlen"). Nothing built. The
  facts in §1 were measured the same day on oaap-test with a loose probe
  (`oaap-lab/wiki-probe`), not with a package and not through the OAAP
  gateway.
- **Date:** 2026-11-20
- **Authors:** Jörg (the goal, 2026-11-20: a wiki in the platform, for
  people to document their organisation, for the AI to keep knowledge
  and to research in; single sign-on with Keycloak; REST and MCP that
  agree with our roles and rights; BookStack as the favourite because
  people get along with shelves and books; "we could define an internal
  wiki standard and make the products exchangeable"), Claude
  (measurement, design)
- **Depends on:** RFC-0091 (roles per realm group, an app as OIDC client:
  `identity.oidc_client`), RFC-0066 (principal propagation, the
  platform's assertion), RFC-0065/0073 (MCP gateway, apps as MCP
  sources), RFC-0104 (the setup door), RFC-0093 (upgrades that change
  data), RFC-0030 (rehearsal), RFC-0032 (events), RFC-0068 (the closed
  tenant)
- **Not part of this RFC:**
  - the **index service** (embeddings, pipeline, vector store as a
    platform service that respects rights) — idea I-65, its own RFC;
    this RFC only fixes what a wiki must offer it (§2, verbs `changes`
    and `may`);
  - the **build service** (recipes that turn upstream compose files and
    build scripts into current OAAP packages) — idea I-66, its own RFC;
  - `help` (RFC-0078/0094): the documentation that comes *with* apps
    stays where it is. The wiki is what the tenant's people and
    assistants write themselves.

## Summary

A tenant gets a wiki as an app. People sign in through the tenant's
realm; the realm's groups are the wiki's roles. Assistants and agents
reach the same wiki through the tenant's MCP gateway, **always as the
person they work for**, and the wiki itself decides what that person
may see.

Two things make this an RFC rather than a store package:

1. **A contract, not a product.** OAAP names a small set of verbs a
   wiki must answer (`spaces`, `read`, `search`, `write`, `changes`,
   `may`, …), one table per product, as it did for identity providers.
   BookStack is the first row. Chat, MCP gateway and the later index
   service speak to the contract only.
2. **An adapter outside the product.** BookStack's API accepts only its
   own token per user. The measurement shows that a small service next
   to it can close that gap without touching BookStack's code — at the
   price of one place that depends on BookStack's tables. That place is
   named, checked at every start and part of every update rehearsal.

The rule that shapes everything else: **the wiki is the only place that
decides who may read a page.** Nothing in OAAP copies its permission
logic.

## 1. Facts (measured on 2026-11-20)

BookStack 26.05.5 and 26.09.3 (`lscr.io/linuxserver/bookstack`),
MariaDB 11.4, Keycloak 26.7.4. Scripts and details:
`oaap-lab/wiki-probe/README.md`.

| # | Question | Result |
|---|---|---|
| F1 | Sign-in through Keycloak, groups → roles | Works. The account is created at the first sign-in; the roles are exactly the groups (matched by the role's `external_auth_id`), including removal. **A change arrives only at the next sign-in.** BookStack requires `https` at the issuer. |
| F2 | The API as the person | Works with a token per user: lists, pages and search show exactly what that person may see; a page written this way carries the person as author. `Authorization: Bearer` → 401. **The API has no endpoint to create tokens**; a row in `api_tokens` (secret as bcrypt) works. |
| F3 | Taking rights away without a sign-in | `PUT /api/users/{id}` with a new role list takes effect at once, also for that user's token. |
| F4 | Webhook, then fetch | The event names page, book, revision and who did it; **no content, no signature**. The call is **synchronous**: a receiver that takes 3 s makes saving take 3.4 s. `GET /api/pages/{id}` returns Markdown, HTML, tags, author, revision count. Webhooks cannot be created through the API. |
| F5 | Images | By default the image of a restricted page is readable **without sign-in**. With `STORAGE_TYPE=local_secure_restricted` only who may see the page gets the image. Images uploaded before the switch stay open. |
| F6 | Update and the way back | 25.02.5 → 26.09.3 with data: 13 migrations, content and tokens intact. Back to the old image **without** a snapshot: `Table 'books' doesn't exist`. Old image + database dump + files as a pair bring everything back. |
| F7 | Size | About 65 MB (app) + 140 MB (database) idle. |

Also true and read, not measured: there is no official BookStack image;
BookStack supports MySQL/MariaDB only; licence MIT.

**Not measured:** BookStack as a package behind the OAAP gateway; an
event when only a book's permissions change; file attachments; creating
an account for a person who never signed in to the wiki; behaviour
under load.

## 2. The contract: `oaap.data.wiki`

A wiki connector answers verbs. As in `idp_admin.py`, a row per product
says which verbs it has, which come later, which never, and through
which **door** a verb goes (the product's API, its database, a
container).

| Verb | What it answers | BookStack (door) |
|---|---|---|
| `version` | what the product says about itself | `GET /api/system` (api) |
| `spaces` | the containers a person may see, two levels at most (shelf, book) | `/api/shelves`, `/api/books` (api, as the person) |
| `read` | one document: Markdown, title, author, revision, tags, address for people | `/api/pages/{id}` (api, as the person) |
| `search` | full text, as the person | `/api/search` (api, as the person) |
| `write` | create or change a document as the person, with an origin (§5) | `POST`/`PUT /api/pages` (api, as the person) |
| `may` | may this person read this document — **answered by the product** | a `read` as the person: 200 or 404 (api) |
| `changes` | what changed since, as events without content | webhook in, event out (api + database for the registration) |
| `people` | the person's account in the wiki and its roles, set now | `/api/users`, `/api/roles` (api, as the adapter) |
| `act_as` | a credential that makes a call count as this person | a row in `api_tokens` (**database**) |
| `export` | a whole space in a portable form | later |

`never`: **`decide`**. A connector never returns "who may read X" as a
list for others to enforce, and no consumer keeps such a list as the
truth. Whoever needs the answer asks `may`. (A coarse hint for
pre-filtering — "this space belongs to these groups" — may travel with
`spaces`; it narrows a search, it never grants.)

A document in the contract has: an id that is stable within the
connector, a space, a title, the body as Markdown, a revision counter,
author and last editor as OAAP persons, tags as name/value pairs, and
the address a person opens. Nothing BookStack-specific (chapters, sort
order, editor type) is part of it; a connector may carry such things in
an `x-` field.

A second product is added by a row and its request bodies. Whether the
contract holds is only known when a second row exists (stage 5).

## 3. The adapter

A small service **in the wiki's package**, in the same instance, next
to BookStack and its database. It is the only thing that speaks
BookStack; everything else in the tenant speaks the contract to it.

It lives in the package and not in the MCP gateway or the platform
because of the `act_as` door: it needs BookStack's database credential,
and that credential should never leave the instance.

**3.1 A call as the person.** The adapter accepts a call only with the
platform's assertion for a person (RFC-0066; the MCP gateway uses it as
procedure P). It then

1. finds the BookStack account whose `external_auth_id` is the person's
   subject in the tenant's realm;
2. sets that account's roles from the groups in the assertion, if they
   differ (`people`, F3) — so rights are as fresh as the assertion, not
   as old as the last sign-in (F1);
3. uses a token for that account (`act_as`): created on demand with a
   short expiry, kept in memory only, never handed out; at start the
   adapter removes the tokens it created before;
4. makes the call with it and returns the answer in the contract's
   form.

There is **no** shared technical user for reading or writing content.
The adapter's own BookStack token (role with user management) is used
for `people` only. A person without an account in the wiki gets a
refusal in words ("sign in to the wiki once"), until creating accounts
from outside has been measured (D6).

**3.2 Changes.** The adapter registers one webhook to itself. It
answers at once and puts the event in a queue (F4: a slow receiver
slows every save). The address carries a secret, because the product
signs nothing. Events leave the adapter in the contract's form — to the
tenant's broker (RFC-0032) when there is one — and carry no content; a
consumer that wants the content calls `read` as someone.

**3.3 What breaks first.** `act_as` and the webhook registration
depend on two of BookStack's tables. At every start the adapter checks
the columns it writes; if they differ it refuses `act_as` with a
sentence naming the table, and the instance's health says so. The
rehearsal of an update (§6) runs the same check against the new
version.

**3.4 Doors of the package.** The adapter is an MCP source for the
tenant's MCP gateway (RFC-0073): tools `wiki_spaces`, `wiki_search`,
`wiki_read`, later `wiki_write`. The same verbs are a REST API for
apps. BookStack's own pages are for people, through the gateway like
any app.

## 4. The package `bookstack`

- **Image.** No official one exists. Stage 1 takes
  `lscr.io/linuxserver/bookstack` with an exact tag (RFC-0093 §7); a
  build from BookStack's release is the first case for the build
  service (I-66).
- **Database.** MariaDB as a container of the instance — not
  `oaap.data.store`, which is PostgreSQL.
- **Sign-in.** `identity.oidc_client` (RFC-0091): the package gets its
  own client in the tenant's realm, groups as a claim. BookStack's own
  login is off.
- **Roles.** The setup door (RFC-0104) creates a BookStack role per
  realm group it is given, with `external_auth_id` = group name, and
  never overwrites a role a person changed.
- **Images and files** in the protected mode **from the first start**
  (F5). The package cannot be switched to the open mode.
- **Upgrade.** `upgrade: one-way` (F6), the snapshot is database dump +
  files as a pair, the check after an update is the adapter's own
  (§3.3) plus one `read`.
- **Backup scope:** database and the files folder; the adapter keeps
  nothing.

## 5. The AI as author

An assistant writes through `write`, therefore as the person it works
for and with that person's rights; the page history shows the person.
Every such page or revision carries tags the adapter sets and a caller
cannot leave out: `herkunft=ki` and the assistant with its revision
(`assistant@rev`, RFC-0097).

Where it writes is a decision (D7). The recommendation: by default into
a space for proposals ("KI-Notizen") that people move from; an
assistant may write elsewhere only if its view in the MCP gateway
contains `wiki_write` and the person may write there anyway.

The reason is the later index: text the AI wrote comes back as a source
for the AI. With the tag, a search or an index can leave such pages out
or mark them.

## 6. Keeping up with the product

The promise is a current package soon after an upstream release. Three
things carry it, none of them is the build service alone:

1. **A thin surface.** OAAP touches BookStack through its REST API, its
   webhook and two tables — and nothing inside its code (no theme, no
   patch).
2. **A measured update.** Every package version is updated on existing
   data before it is released (RFC-0093 §7), with the checks of
   `oaap-lab/wiki-probe` turned into the package's own check.
3. **Exact tags.** A patch release upstream is a package version.

## 7. Stages

0. **Measured** (2026-11-20): the probe, §1.
1. **The package** `bookstack`: sign-in through the tenant's realm,
   roles from groups through the setup door, protected files, upgrade
   notes. People can use the wiki. Measured on oaap-test behind the
   gateway.
2. **The adapter, reading:** assertion → person, roles from the
   assertion, `act_as`; `spaces`, `search`, `read`, `may` as REST and
   as an MCP source; a view in the MCP gateway; the chat finds and
   quotes wiki pages with their address.
3. **Writing and changes:** `write` with origin tags, the proposals
   space, webhook → queue → events.
4. **Spec** `oaap.data.wiki` 0.1 from what stages 1–3 taught.
5. **A second connector**, to learn whether the contract is one.

The index service (I-65) can start after stage 3; it needs `changes`,
`read` and `may`.

## 8. Decisions for Jörg

**Decided 2026-11-20: D1–D10 as recommended.**

- **D1 — BookStack as the first connector?** *Recommendation: yes.* It
  passed all five measurements; the one gap (F2) closes outside its
  code.
- **D2 — The wiki alone decides who may read (`never: decide`)?**
  *Recommendation: yes.* The alternative — rights copied into an index
  — is two places for one rule.
- **D3 — The adapter writes into BookStack's database for `act_as`?**
  *Recommendation: yes, and only there*, with the check of §3.3. The
  alternatives: a person creates their own token by hand (RFC-0095,
  procedure U — correct, but nobody will do it for a wiki), or code
  inside BookStack (breaks the thin surface).
- **D4 — The adapter in the package, not in the gateway?**
  *Recommendation: in the package* (§3).
- **D5 — Roles set from the assertion at every call?**
  *Recommendation: yes.* Otherwise a person removed from a group keeps
  their rights in the wiki until they sign in again (F1).
- **D6 — A person who never opened the wiki:** refuse with a sentence,
  or create the account? *Recommendation:* refuse in stage 2; measure
  creation, then decide.
- **D7 — Where the AI writes:** *Recommendation:* the proposals space
  by default (§5).
- **D8 — One wiki per tenant?** *Recommendation: yes*, as an ordinary
  instance; a second one is possible like any app, nothing connects
  them.
- **D9 — The capability's name:** `oaap.data.wiki`, or wider
  (`oaap.data.knowledge`) so that other sources fit later?
  *Recommendation:* `oaap.data.wiki` — the wider thing is the index
  service, and it gets its own name.
- **D10 — Image in stage 1:** the linuxserver image with an exact tag,
  or wait for the build service? *Recommendation:* the image now; the
  build service gets BookStack as its first case.

## Deutsche Zusammenfassung

**Worum es geht:** Ein Mandant bekommt ein Wiki als App. Menschen
melden sich über den Realm des Mandanten an, die Gruppen des Realms
sind die Rollen im Wiki. Assistenten und Agenten erreichen dasselbe
Wiki über das MCP-Gateway des Mandanten, **immer als der Mensch, für
den sie arbeiten**, und das Wiki entscheidet selbst, was dieser Mensch
sehen darf.

**Zwei Dinge machen daraus einen RFC statt nur ein Store-Paket:**

1. **Ein Vertrag statt eines Produkts** (`oaap.data.wiki`): wenige
   Verben, die ein Wiki beantworten muss — Räume, lesen, suchen,
   schreiben, „darf dieser Mensch das sehen“, Änderungen, Konten und
   Rollen, „als dieser Mensch handeln“. Eine Tabelle je Produkt, wie
   beim Anmeldeserver. BookStack ist die erste Zeile. Das ist der
   „interne Wiki-Standard“.
2. **Eine Zwischenschicht außerhalb des Produkts** (der Adapter, ein
   kleiner Dienst im selben Paket): BookStacks API kennt nur eigene
   Tokens je Benutzer. Der Adapter nimmt die Zusicherung der Plattform
   an, findet das Konto des Menschen, stellt dessen Rollen aus den
   Gruppen der Zusicherung ein und ruft BookStack mit einem kurzlebigen
   Token dieses Menschen auf.

**Die Regel dahinter:** Das Wiki ist der einzige Ort, der entscheidet,
wer eine Seite lesen darf. Nichts in OAAP baut seine Rechtelogik nach.

**Gemessen am 20.11. auf oaap-test** (loser Aufbau, kein Paket, nicht
durch das OAAP-Gateway): Anmeldung über Keycloak mit Gruppen → Rollen
geht, Änderungen kommen aber erst bei der nächsten Anmeldung an. Mit
einem Token je Benutzer gelten in der API genau dessen Rechte, auch in
der Suche. Die API kann solche Tokens nicht anlegen; ein Eintrag in der
Datenbank geht. Rechteentzug über die Admin-API wirkt sofort. Webhooks
kommen ohne Inhalt und ohne Signatur und bremsen das Speichern, wenn
der Empfänger langsam ist. Bilder sind in der Vorgabe ohne Anmeldung
abrufbar; der geschützte Modus muss vom ersten Start an gesetzt sein.
Ein Update über 13 Migrationen lief sauber; zurück geht es nur mit
Sicherung (Abbild, Datenbank und Dateien als Paar).

**Die eine empfindliche Stelle:** Der Adapter schreibt für die Tokens
und den Webhook in zwei Tabellen von BookStack. Er prüft deren Aufbau
bei jedem Start und in jeder Generalprobe eines Updates und verweigert
mit einem Satz, statt falsch zu schreiben.

**KI als Autor:** Sie schreibt als der Mensch, für den sie arbeitet.
Der Adapter setzt die Markierung „von der KI“ samt Assistent und
Fassung, der Aufrufer kann sie nicht weglassen. Vorgabe: in einen Raum
für Vorschläge, aus dem Menschen übernehmen.

**Nicht Teil:** der Index-Dienst (Embeddings, Vektoren, mit Rechten) —
I-65, eigener RFC, kann nach Stufe 3 beginnen. Der Build-Dienst — I-66,
eigener RFC; BookStack wäre sein erster Fall. Die Hilfe (RFC-0078/0094)
bleibt, was sie ist.

**Stufen:** (0) gemessen; (1) Paket `bookstack` mit Anmeldung, Rollen,
geschützten Dateien, Update-Hinweisen; (2) Adapter lesend, als
MCP-Quelle, der Chat findet und zitiert Wiki-Seiten; (3) Schreiben und
Änderungsereignisse; (4) Spec 0.1; (5) ein zweites Produkt als Probe
auf den Vertrag.

**Entscheidungen D1–D10**, am 20.11.2026 von Jörg wie empfohlen
angenommen: BookStack zuerst
(ja); das Wiki entscheidet allein (ja); Datenbank-Eintrag für die
Tokens (ja, nur dort, mit Prüfung); Adapter im Paket (ja); Rollen bei
jedem Aufruf aus der Zusicherung (ja); wer das Wiki nie geöffnet hat,
wird zunächst mit einem Satz abgewiesen; die KI schreibt in den
Vorschlagsraum; ein Wiki je Mandant; Name `oaap.data.wiki`; in Stufe 1
das linuxserver-Abbild mit exaktem Tag.

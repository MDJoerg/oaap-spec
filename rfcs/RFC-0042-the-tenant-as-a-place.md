# RFC-0042: The Tenant as a Place — Its Own Address, Its Own Face

- **Status:** **Accepted (2026-09-22)** — all five decided by Jörg,
  each as recommended, in the same sitting as RFC-0041's seven. Nothing
  built. This is the one to build **first**: RFC-0041 K5 needs the
  tenant address, and nothing here needs Keycloak.
- **Date:** 2026-09-22
- **Authors:** Jörg (the idea and its scope), Claude (design and write-up)
- **Depends on:** RFC-0022 (tenant as boundary), RFC-0025/RFC-0026
  (names are changeable, identity is not), RFC-0007 (visibility groups),
  RFC-0035 **D3** (the tenant-level theme, name reserved 2026-09-08),
  RFC-0036 **D2/D4** (the tenant launchpad editor, deferred 2026-09-11),
  RFC-0034 Stufe 1 / `oaap.data.files` (where a logo lives)
- **Companion:** RFC-0041 (external identity providers). That RFC's **K5**
  needs the address decided here. **This RFC needs nothing from it** —
  see §0, which is the reason it is written separately.

## 0. Why this is its own RFC, and why it should be built first

Everything here works with the platform's **built-in** identity, today.
A club gets an address, a face and a launchpad without a single line of
OIDC. Keeping the two apart buys three things:

1. **The clubs see something before the identity work lands.** This is
   the visible half and the cheap half.
2. **The identity RFC does not have to carry the presentation
   questions**, which are a different kind of decision (what may a
   tenant change about how the platform looks?) and would otherwise be
   argued in the middle of a security design.
3. **RFC-0041 K5 depends on this, not the other way round.** A login
   that knows which realm to use needs a tenant-scoped entry point
   first. Built in this order, that dependency is already satisfied when
   it is needed.

This also settles something two earlier RFCs deliberately postponed.
RFC-0035 **D3** reserved the tenant theme's variable names and said a
tenant-level override is *"a later phase… so that phase needs no
breaking change"*. RFC-0036 **D2** declined the tenant launchpad editor
because *"none of that is justified without more than one manifest
actually using the new field first."* The condition both were waiting
for has arrived: `oaapx01` carries four tenants, two of them customers
with their own people.

## 1. The decisions

### T1 — The tenant answers at `<label>.<node>`

> **Recommendation: yes — and close the namespace hole it exposes.**

The naming scheme already carries the tenant: `<instance>.<label>.<node>`
for every tenant but the default, whose prefix is deliberately empty
(`<instance>.<node>`). So `<label>.<node>` is the one slot the scheme
describes and nothing occupies. `cls.oaap.joomp.de` is not an addition
to the scheme; it is the part of it that was never filled in.

**The finding that comes with it.** Tenant labels and *default-tenant
instance names* share that host namespace, and nothing checks across
them: `label_is_free()` asks only about tenants, and instance creation
asks only about the registry. Today this is harmless because nothing
answers at `<label>.<node>`. The moment this RFC ships, a tenant
labelled `studio` and the default tenant's `studio` instance both want
`studio.<node>`, and whichever site the gateway writes last wins —
silently, which is this project's recurring failure mode.

*Measured on `oaapx01`, 2026-09-22:* tenants `cls`, `hbvp`, `pxx`
against twelve default-tenant instance names — **no collision today**.
So the fix is a guard, not a migration.

- Creating or renaming a tenant label MUST refuse a name that a
  default-tenant instance holds, and vice versa.
- Both refusals keep the existing rule: **say that the name is taken,
  never by whom** (`oaap.core.tenant` 2.4).
- Unexpired **former** labels count as taken, exactly as they already do
  for tenants (RFC-0026 3.3) — a name that still routes somewhere must
  not be handed to someone else.

TLS costs nothing here: the wildcard `*.oaap.joomp.de` already covers it.

### T2 — The **portal** answers there, tenant-scoped

> **Recommendation: the portal, not a separate Launchpad app.**

Jörg's sketch says *"dahinter könnten wir dann eine Launchpad App
konfigurieren"*. A separate app would have to re-acquire four things the
portal already has and has had tested for months: the launchpad itself,
the role **and** visibility-group filter (RFC-0007), the tenant boundary,
and the session. Building them a second time is how this codebase
produces its most expensive defects — three times in the last week a
second path carried a rule the first one did (0.1.109, 0.1.110, 0.1.111).

So: the portal serves a **tenant-scoped launchpad** at `<label>.<node>`.
It shows the tiles of that tenant's instances, filtered by the caller's
roles and groups exactly as the launchpad does now, wearing that
tenant's theme (T3).

What is genuinely new is small and honest: the portal must learn that
the *host it was reached through* scopes what it shows — and it must
**fail closed**, the same rule `tenant_host_prefixes` already follows.
A host naming a tenant this node does not have serves nothing; it does
not fall back to the operator's own view.

The app direction is not discarded — it is T4.

### T3 — A tenant's face: title, two colours, a logo

> **Recommendation: exactly these, and no stylesheet.**

The tenant record gains a small, closed set:

| Field | Meaning |
| --- | --- |
| `title` | what the club calls itself, shown in the header and the tab |
| `color_primary` | the one colour that carries the brand |
| `color_accent` | the second, for states and emphasis |
| `logo` | an image |

**Closed on purpose.** RFC-0035 chose its variable names so a
tenant-level override costs no breaking change; it did not promise a
tenant arbitrary CSS. A tenant that can ship a stylesheet can move,
hide or fake any control on a page the platform is responsible for.
Four values cannot.

**The logo is a file, and that is the point.** `oaap.data.files` (built
2026-09-22, RFC-0034 Stufe 1) stores content by hash, per tenant,
tenant-isolated by path, and it is in the backup, in the tenant archive
and in the rehearsal already. A tenant logo is its first real consumer
and a good one: small, immutable, per tenant, and worthless to anybody
else.

**Two rules the theme does not get to break:**

- **`server_admin` surfaces stay platform-themed.** An operator must
  always be able to tell, by looking, that they are on a page where they
  hold node-wide power. A themed node administration is a page that can
  be mistaken for a customer's.
- **A theme MUST NOT be able to impersonate another tenant or the
  platform.** The tenant's own name is shown next to its theme on every
  page the theme applies to — not as decoration, as an anchor.

The **login page carries the tenant's theme**, and that is deliberate:
it is the first page a club member ever sees, and it is theirs. It stays
recognisably the platform's page in structure — the theme colours it,
it does not redraw it.

### T4 — "Apps as tenant plugins": a direction, not a mechanism

> **Recommendation: reserve the idea, build nothing — the third time
> this pattern is the right answer.**

Jörg: *"Vielleicht über OAAP-Apps, die als Plugin für Tenants
klassifiziert sind."* That is a good direction and a bad first version.
RFC-0035 D3 and RFC-0036 D1/D4 both took the same shape — name it now,
so growing into it costs no breaking change; build it when a real
consumer exists to test it against.

What this RFC does: nothing goes into the manifest schema yet. What it
*records* is the shape a mechanism would take — an app declaring that it
contributes something to its tenant's page rather than a tile of its own
— and the question that must be answered first and cannot be answered
today: **what happens when an app's contribution and a tenant's chosen
arrangement disagree?** RFC-0036 D2 named that question as the reason it
stopped, and it is still unanswered.

Speculatively shipping half a plugin mechanism risks locking in the
wrong shape before a consumer exists. Two clubs with a launchpad each
will say more about the right shape in a month than this RFC can.

### T5 — The tenant page requires a login

> **Recommendation: yes, in v1.**

It is a launchpad: it lists what *you* may open, which presupposes
knowing who you are. A club's **public** face is a normal app on a public
route (`oaap.core.gateway`), which already works and is what the
infoboard does today.

The alternative — a public tenant page that becomes a small CMS — is a
different product, and inventing one here would be the largest
unrequested thing in this RFC.

Unauthenticated, `<label>.<node>` therefore shows the **themed login**
(T3), and after login the launchpad. RFC-0040's deep link already makes
that return to where the visitor was going.

## 2. Non-goals

- **No layout editor.** No creating, renaming, reordering or dragging of
  sections. RFC-0036 D2's reasons stand; only the *face* is decided here.
- **No arbitrary CSS, no custom fonts, no per-tenant templates.**
- **No public/anonymous tenant page** (T5).
- **No change to how instances are addressed.** `<instance>.<label>.<node>`
  is untouched; this RFC fills the empty slot beside it.
- **No plugin mechanism** (T4).
- **Nothing about identity providers.** That is RFC-0041, and the two do
  not need each other in this direction.

## 3. Build order

1. **The guard of T1** — labels and default-tenant instance names become
   one namespace, checked both ways. Small, and it must land before
   anything answers at that host, not after.
2. **The generated tenant site** and the portal's host-scoped launchpad
   (T1, T2), unthemed. At this point a club has an address that works.
3. **The face** (T3): the four fields, the logo through
   `oaap.data.files`, the themed login, the two rules it may not break.
4. Then RFC-0041 K5 has what it needs.

**Confirmed 2026-09-22**, with the decisions taken. Two notes the
decisions add:

- Step 1 is **not** optional and **not** deferrable behind step 2. The
  guard is cheap while nothing answers at `<label>.<node>` and becomes
  a migration the moment something does. The measurement on `oaapx01`
  (no collision among `cls`, `hbvp`, `pxx` and twelve default-tenant
  instance names) holds *today*; it is not a property of the system,
  only of its current contents.
- Step 3 makes the tenant logo the **first real consumer** of
  `oaap.data.files` 0.1.1. That is worth saying out loud because it is
  also the first test of it outside its own test file: a real file,
  written by a real operator, surviving a backup and a restore.

T4 adds nothing to this list, by decision — which is the point of it.

## 4. What this makes possible later

Worth naming because it is the reason the address matters more than it
looks: once a tenant is a **place** — a name that answers, a face, a
launchpad — the move of that tenant to its own node (RFC-0041 K6) stops
being an infrastructure operation and becomes a change of address. The
club's people keep the same page; the label in front of the node name is
what changes, and RFC-0026's former-label grace already keeps the old
one answering while the word gets around.

## Deutsche Zusammenfassung

**Warum das ein eigenes RFC ist:** Alles hier funktioniert mit unserer
**eingebauten** Anmeldung, heute. Ein Verein bekommt Adresse, Gesicht
und Launchpad ohne eine einzige Zeile OIDC. Und RFC-0041 braucht diesen
Teil (für „welcher Realm ist zuständig?"), nicht umgekehrt — in dieser
Reihenfolge gebaut, ist die Abhängigkeit schon erfüllt, wenn sie
gebraucht wird. Außerdem holt es zwei Punkte nach, die zwei frühere RFCs
bewusst vertagt hatten: RFC-0035 D3 (Mandanten-Design, Namen reserviert)
und RFC-0036 D2 (Launchpad je Mandant, zurückgestellt bis es mehr als
einen echten Fall gibt). Die Bedingung ist eingetreten: `oaapx01` hat
vier Mandanten, zwei davon Kunden mit eigenen Leuten.

**T1 — Der Mandant antwortet unter `<kürzel>.<knoten>`.** Das ist keine
Erweiterung des Namensschemas, sondern die Stelle darin, die nie gefüllt
wurde: Instanzen heißen längst `<instanz>.<kürzel>.<knoten>`.

**Der Befund dazu:** Mandanten-Kürzel und die Instanznamen des
**Standard-Mandanten** teilen sich diesen Namensraum, und **niemand
prüft dagegen**. Solange dort nichts antwortet, ist das folgenlos. Ab
diesem RFC wollen ein Mandant `studio` und die Instanz `studio` dieselbe
Adresse — und es gewinnt, wer zuletzt geschrieben wird. Lautlos, also
genau die Fehlerform, die dieses Projekt sammelt. **Auf oaapx01
nachgesehen: heute keine Kollision** (cls, hbvp, pxx gegen zwölf
Instanznamen). Es braucht also eine Wache, keine Migration.

**T2 — Dort antwortet das Portal, nicht eine eigene App.** Eine eigene
Launchpad-App müsste vier Dinge neu erwerben, die das Portal hat und die
getestet sind: das Launchpad, den Rollen- **und** Gruppenfilter, die
Mandantengrenze und die Sitzung. Genau so entstehen die teuersten Fehler
dieses Codes — dreimal in der letzten Woche trug ein zweiter Weg eine
Regel nicht, die der erste trug. Neu ist nur: Das Portal muss lernen,
dass der **Host**, über den es erreicht wurde, bestimmt, was es zeigt —
und dabei **fehlschlagen statt ausweichen**, wenn der Host einen
Mandanten nennt, den dieser Knoten nicht hat.

**T3 — Das Gesicht: Titel, zwei Farben, ein Logo. Mehr nicht.** Wer ein
eigenes Stylesheet mitbringen darf, kann jedes Bedienelement auf einer
Seite verschieben, verstecken oder fälschen, für die die Plattform
geradesteht. Vier Werte können das nicht. **Das Logo ist eine Datei** —
und damit der erste echte Nutzer von `oaap.data.files` aus RFC-0034
Stufe 1, die heute gebaut wurde: inhaltsadressiert, je Mandant getrennt,
schon in Sicherung, Mandantenarchiv und Generalprobe.

Zwei Regeln, die das Design nicht brechen darf: **`server_admin`-Flächen
bleiben plattformfarben** — wer knotenweite Macht hat, muss das ansehen
können —, und ein Design darf **niemals einen anderen Mandanten oder die
Plattform nachahmen**; der Name des Mandanten steht neben seinem Design
auf jeder Seite, nicht als Zierde, sondern als Anker. Die
**Anmeldeseite trägt das Design des Vereins**, absichtlich: Sie ist die
erste Seite, die ein Vereinsmitglied je sieht, und sie gehört ihm.

**T4 — „Apps als Plugins für Mandanten": Richtung ja, Mechanismus nein.**
Zum dritten Mal ist dieses Muster die richtige Antwort (nach RFC-0035 D3
und RFC-0036 D1/D4): den Namen reservieren, damit das Hineinwachsen
später nichts bricht, und bauen, wenn es einen echten Abnehmer gibt.
Die Frage, die zuerst beantwortet werden muss und heute nicht
beantwortet werden kann, steht schon in RFC-0036 D2: **Was gilt, wenn
der Vorschlag einer App und die Anordnung eines Mandanten sich
widersprechen?** Zwei Vereine mit je einem Launchpad sagen dazu in einem
Monat mehr, als dieses RFC heute kann.

**T5 — Die Mandantenseite verlangt eine Anmeldung.** Sie ist ein
Launchpad; sie zeigt, was *Du* öffnen darfst. Das öffentliche Gesicht
eines Vereins ist eine normale App auf einer öffentlichen Route — genau
das, was das Hallen-Infoboard heute schon ist. Die Alternative wäre ein
kleines CMS, und das ist ein anderes Produkt.

**Und wozu das später führt:** Sobald ein Mandant ein **Ort** ist — ein
Name, der antwortet, ein Gesicht, ein Launchpad —, wird der spätere
Umzug auf einen eigenen Knoten (RFC-0041 K6) von einer
Infrastrukturaktion zu einem **Adresswechsel**. Die Leute des Vereins
behalten ihre Seite; es ändert sich das Kürzel vor dem Knotennamen, und
die Schonfrist für frühere Kürzel aus RFC-0026 hält die alte Adresse so
lange am Leben, bis es sich herumgesprochen hat.

## Nachtrag: die Entscheidungen vom 22.09.2026

Jörg hat alle fünf entschieden, jede wie vorgeschlagen — anders als
bei RFC-0041, wo zwei anders ausgingen. Das heißt der Reihe nach:

- **T1:** Der Mandant bekommt `<kürzel>.<knoten>`, **und die Wache
  kommt mit.** Ein Mandanten-Kürzel darf keinen Namen bekommen, den
  eine Instanz des Standard-Mandanten hält, und umgekehrt. Die
  Ablehnung sagt, dass der Name vergeben ist — nie von wem.
- **T2:** Das **Portal** antwortet dort, mandantenbezogen. Keine zweite
  Anwendung, die Launchpad, Rollen- und Gruppenfilter, Mandantengrenze
  und Sitzung noch einmal erwerben müsste. Neu ist nur, dass das Portal
  lernt: der Host bestimmt, was ich zeige — und wenn der Host einen
  Mandanten nennt, den dieser Knoten nicht hat, zeigt es **nichts**
  statt auf die Betreibersicht auszuweichen.
- **T3:** Titel, zwei Farben, ein Logo. **Kein Stylesheet.** Das Logo
  ist eine Datei und damit der erste echte Nutzer von
  `oaap.data.files`. `server_admin`-Flächen bleiben plattformfarben,
  damit man einer Seite ansieht, dass man dort knotenweite Macht hält.
- **T4:** Plugin-Richtung festgehalten, **nichts gebaut** — das dritte
  Mal, dass dieses Muster die richtige Antwort ist. Die Frage davor
  bleibt unbeantwortet: Was gilt, wenn der Vorschlag einer App und die
  Anordnung eines Mandanten sich widersprechen?
- **T5:** Anmeldung nötig. Unangemeldet zeigt die Adresse die
  Anmeldemaske im Design des Vereins. Die öffentliche Seite eines
  Vereins bleibt eine normale App auf einer öffentlichen Route.

**Reihenfolge, jetzt beidseitig bestätigt:** Dieses RFC zuerst, dann
RFC-0041. Es braucht nichts von Keycloak, und RFC-0041 K5 braucht die
Mandantenadresse. Die Vereine sehen damit etwas, bevor die
Identitätsarbeit landet — und die Identitätsarbeit muss die
Gestaltungsfragen nicht mittragen.

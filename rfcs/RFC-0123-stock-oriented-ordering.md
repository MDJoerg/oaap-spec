# RFC-0123: Stock-Oriented Ordering — a Customer Builds Its Stock by Ordering Into It

- **Status:** **Accepted (2026-11-23)** — D1–D11 decided in conversation (§12.1),
  D12–D20 decided one by one the same day, each as recommended (§12.2).
  Nothing built. **Stage 0 measured 2026-11-24 on `oaap-test` (§1.4);**
  **its six consequences decided the same day as D21–D26 (§12.3).**
  The facts in §1.1 were read the same day in RFC-0031, RFC-0045, RFC-0061,
  RFC-0103 and RFC-0120 (the RFC texts, not the specifications and not the
  code). What was **not** read or measured is listed in §1.3.
- **Date:** 2026-11-23
- **Authors:** Jörg (the idea, the process, the three-column screen and the
  early identification from a predecessor project, 2026-11-23:
  "Bestellportal für die Bestandsorientierte Konfiguration"), Claude (facts,
  design)
- **Depends on:** RFC-0031 (model and twin), RFC-0120 (the twin as an
  integration hub: tenant types, status, batch, events), RFC-0045 (business
  authorization), RFC-0061 / RFC-0103 / RFC-0105 (cases), RFC-0040 (the person
  behind the name), RFC-0118 (one face for all apps)
- **Related:** RFC-0032 (events), RFC-0057 (database per app), RFC-0080
  (notifications), RFC-0114 (system landscape), idea I-51 (a CMDB that grows by
  itself)
- **Changes (when accepted):** two new app packages, `sortiment`
  and `bestand` (D12); possibly `vorgaenge` (a way back from a case to the app
  that opened it, D15); possibly `oaap.data.twin` (who may read which subtree,
  D14)
- **Not part of this RFC:**
  - **Prices, scales, discounts.** The first version has a quote the provider
    writes by hand (§6). The article keeps room for prices; the rules come in
    their own RFC.
  - **Purchasing, warehouse, manufacturing, assembly as apps.** This RFC
    defines the interface they will sit behind (§8); until they exist, a case
    carries the work.
  - **Automation scripts** (set up a VM from the order's parameters). The
    route is named (§8.1), the runner is not designed here.
  - **Invoicing and contracts.**

## Summary

A service provider runs complex IT landscapes for customers across many sites.
Today the customer's stock — sites, buildings, workplaces, devices, contacts —
is collected in spreadsheets and tickets. This RFC proposes that the customer
**builds the stock themselves by ordering into it**.

Everything is an **article**: a monitor (type A, goods), setting up a
workplace (type B, service) and also a site or a contact person (type C, a
**data object**). An article is ordered **under a node of the stock**, its
**context**. A data article is produced at once — a record in the twin — and
is immediately a context for further orders. So an empty account grows into a
tree: account → site → building → floor → room → workplace → monitor.

A contact person is an article too. Producing it creates the person in the
twin, opens a login, and gives them **responsibilities** for nodes of the
tree. From then on several people extend the same stock in parallel, each in
their own part.

Two apps in the provider's tenant:

1. **Articles** (`sortiment`): the provider maintains articles, their forms,
   and the rules under which context an article can be ordered.
2. **Stock and ordering** (`bestand`): the customer's screen with three
   columns (stock, focus, articles), the cart, the order, and the lifecycle of
   every stock node.

The stock itself lives in the **twin**. Work that is not data — procurement,
services, assembly — leaves the order as **bundles** that go to cases first
and to specialised apps later; their progress writes the status of the stock
nodes forward.

## 1. Facts

### 1.1 Read 2026-11-23 (RFC texts)

| # | Fact | Source |
|---|---|---|
| F1 | The twin holds **objects** of exactly one object type, with **groups** (a named bundle of attributes with one origin — the counterpart of an AAS submodel) and **relations** that are directed, typed, **valid in time** and carry attributes of their own. A tree read exists: `GET …/objects/{id}/tree?at=&depth=`. | RFC-0031 §3 |
| F2 | A tenant can have **types of its own** (`t.<label>.<Key>` for object types), created by the tenant admin or by a client with the right binding, **additive only**. | RFC-0120 §4.5, D8, D9 |
| F3 | A type may declare a **status** with values and allowed transitions, optionally who may make which. A change is checked, appended with who, when and why, and published as an event. | RFC-0120 §4.4 (stage 4 built) |
| F4 | **Batch**: up to N operations (objects, groups, relations, status) in one transaction, all or nothing, with a caller-chosen id so that a retry does nothing twice. **Upsert by the source's own key.** **Retire** instead of delete. | RFC-0120 §4.5 |
| F5 | The twin publishes status and value events, offers signed webhooks and a change feed. | RFC-0120 §4.7 |
| F6 | Rights in the twin are **bindings per type** (`reads`, `contributes`, `owner`). Checking **per person and per object** in the twin is "a direction, not a decision". | RFC-0120 §4.1, RFC-0045 §8.3 |
| F7 | RFC-0045 knows the **contextual grant**: person X has role Y in context Z, granted by W. The app declares, the tenant grants, **the data holder checks**. | RFC-0045 Summary |
| F8 | A case has a `kind` from a closed list; an app adds **subkinds through a template** with fields and `steps` (queues in order). Templates come from the manifest (`cases.templates`) or the tenant. | RFC-0061 §1, §6 |
| F9 | A case's `context` may carry one `object`: a twin object id, **or an app-local id with the app as namespace**. | RFC-0061 §1 |
| F10 | An app's backend may open a case with its instance key, scope `oaap.cases.submit`, optionally "on behalf of" a user (recorded as the app's statement). | RFC-0061 §3.2 |
| F11 | `refs` on a case link to **other cases** only. | RFC-0061 §1 |

### 1.2 What follows

- F1–F4 carry the stock without a new store: a node is an object, its forms
  are groups, the tree is a relation, the lifecycle is a declared status, and
  an order's data articles are **one batch** — produced completely or not at
  all.
- F2 "additive only" limits article versions: a new version can add a form
  field, it cannot take one away from the twin. An article version therefore
  says which fields it **shows**; the type keeps what it ever had.
- F6 is the hard one. All customers of the provider live in **one** tenant
  (D1), and the twin does not separate them. **A customer's contact must never
  reach the twin's own doors** (portal pages, MCP, chat) — only `bestand`,
  which checks every read and write against the account (§9, D14).
- F8–F10 answer "do cases need a special type and an external number?": the
  type is a template subkind, the number is `context.object`. Both exist.
  What is **missing** is the way back: how the app that opened a case learns
  that it moved (D15).

### 1.3 Not read, not measured

- The specifications `oaap.data.twin` and `oaap.data.model` themselves, and
  the reference code — only the RFCs.
- Whether an **app** (not a client, not the tenant admin) may create tenant
  types and declare a status on them. `sortiment` needs that.
- What a person with platform role `user` sees today in the twin's portal
  pages, through the twin's MCP door and in the chat. Decides how D14 is
  built.
- Whether `vorgaenge` publishes anything when a case changes status, and
  whether `/platform/cases/submit` is in the released package (RFC-0061 names
  it with a probe app).
- How a user is created in the tenant's Keycloak **by an app**, with an
  e-mail that must be confirmed before the login opens. RFC-0055's invitation
  link is for tenant requests, not for users.
- Size: how the tree read behaves with some ten thousand nodes per account.
- The predecessor project's data model and screens (Jörg has them; not seen).

Stage 0 (§11) answers these before anything is built on them.

### 1.4 Measured 2026-11-24 (stage 0, `oaap-test`, reference 0.1.359)

A throw-away tenant `s0` with a twin, an integration client `s0-sortiment`
(`models`), a person `s0kunde` with platform role `user`. Two scripts as root
on the node, 15/18 and a second round for the three that needed one. Where a
row says *code*, it was read, not measured.

| # | Finding | How |
|---|---|---|
| S1 | A person with role **`user` reads the whole twin**: the portal's start page, the list of every object of a type, every object page; through the MCP door `twin_search` finds the objects. Only writing is refused ("darf lesen, aber nicht schreiben"); a person without a tenant role is refused. | measured: portal with a real login; MCP door called inside the twin container with the headers an MCP gateway's door sets (s0 has no gateway, so the chat was not measured end to end) |
| S2 | **An app instance cannot create types**: `POST /twin/v1/types` with an instance key answers 403 "the writes of /twin/v1 are an integration client's". An app's types come only from its manifest `data_model` at install, node-wide, fixed per package version. An integration client with `models` creates tenant types with status and relations. The platform shows that key with "for the program, never for an app". | measured (instance `raci`; client `s0-sortiment`) |
| S3 | **Relations carry no attributes.** An attribute on a relation type (`s0Rolle` on `s0Verantwortlich`) is accepted and silently dropped; a relation row is key, target and validity only. F1 holds for RFC-0031's text, not for the reference. | measured + code (`twin_write.py`) |
| S4 | A declared **status works**: `configured → ordered` in a batch passes, the jump `ordered → retired` is refused. A smaller declaration sent later answers 200 "unchanged" — additive, the removal is ignored without a word. | measured |
| S5 | **Writing 11 111 nodes** (account → 10 sites → 100 buildings → 1 000 floors → 10 000 rooms) in 23 batches of 500: **121.6 s, 10.9 ms per node**. A relation names its target by key, so the target must exist: written bottom-up. A parent → child relation lives in the **parent's** group, so adding a child writes the parent. | measured |
| S6 | **Reading the tree.** `/twin/v1/…/graph` depth 4: 0.4 s, but cut at 2 000 nodes (`truncated`). Export of the type: 1.0 s, 4 MB. Search by title: 0.56 s. The portal's tree read (one object load per node): depth 1 0.1 s, depth 2 0.8 s, depth 3 **8.2 s** (1 111 nodes), depth 4 **killed** by the worker timeout after 30 s (500). The portal itself gives up after 8 s, so its tree page fails from depth 3 on. The tree follows outgoing relations only. | measured |
| S7 | **No app can create a user**, and there is **no e-mail confirmation**. Identity's `POST /internal/users` takes only the portal's key; the Keycloak connector declares `never: users` (`idp_admin.py:268`); `oaap user add` writes the platform's own identity store, not Keycloak. `VERIFY_EMAIL` / `execute-actions-email` appear nowhere. SMTP into a realm exists (RFC-0072). | code |
| S8 | **Cases from a backend exist, the way back does not.** `/platform/cases/submit` (vorgaenge ≥ 0.2.0, manifest `cases: {submit: true}`): `kind` from the closed list, `title`, `body`, `queue`, `object {kind, id}`, `on_behalf_of`. No template, subkind or fields on this path; `cases.templates` (RFC-0061 §6) is specified, not built. vorgaenge publishes nothing on a status change, and the submit key cannot read a case back — D15's fallback (poll) is not possible either. | code |
| S9 | `oaap.core.authorization` says nothing against D13: an app that declares nothing keeps its own model (§1); RFC-0045's warning (A1, §6.3) is about derivation rules **in the platform**. | read |
| S10 | A tenant has a twin only once an app with a twin binding is installed (or the fleet/asset readers). For `s0` the schema was made with the same function an install calls. | measured |

**What follows for stage 1** (decided 2026-11-24 as D21–D26, §12.3):

1. **D14 must be built before the first contact logs in** (S1). Without it
   every contact of every customer reads every stock through the portal and
   through any assistant with the twin as source. This is platform work in
   `oaap.data.twin`.
2. **Contacts with a login need a platform capability** (S7): an app asks,
   the platform creates the user and sends a confirmation mail. Nothing of it
   exists; it is the largest gap and wants its own RFC.
3. **Types** (S2): either `sortiment` declares a few fixed types in its
   manifest (one node type, the article as an attribute) and is an ordinary
   app, or an app may hold `models` — a change to RFC-0120 D8.
4. **Responsibility** (S3, D13): one relation type per role, or a small
   responsibility object between person and node.
5. **`bestand` reads level by level** (S6) and never asks for the whole tree;
   the twin's own tree read needs a fix before the provider can look at a
   large stock in the portal (D20).
6. **Stage 2 needs D15 built in `vorgaenge`** (S8) — there is no workaround.

## 2. Words

| word | German (in the app) | meaning |
|---|---|---|
| provider | Dienstleister | owns the tenant, maintains articles, writes quotes, fulfils |
| account | Account | one customer of the provider; the root node of that customer's stock |
| stock | Bestand | the tree of nodes below an account |
| node | Bestandsposition | one object in the twin, created by an order position |
| article | Artikel | what can be ordered: type A goods, B service, C data object |
| context | Kontext | the node under which an article is ordered |
| contact | Ansprechpartner | a person of the customer: a node, a login and responsibilities |
| responsibility | Zuständigkeit | role × node, inherited down the tree |
| cart | Warenkorb | a person's draft; nobody else sees it |
| order | Auftrag | a submitted cart: positions, kept for good |
| position id | Positionskennung | cart number + position; the identity of a node from the first click |
| quote | Angebot | the provider's answer to positions that need one |
| bundle | Bündel | positions of an order that are fulfilled together |

"Katalog" is avoided on purpose: in OAAP it means the package catalog
(RFC-0050).

## 3. Articles (`sortiment`)

### 3.1 The article

| field | meaning |
|---|---|
| `key`, `title`, `text`, picture | what the customer sees |
| `class` | `A` goods · `B` service · `C` data |
| `effect` | `create` (a new node) · `act` (works on an existing node: dismantle, move, replace) |
| `object_type` | for `create`: the twin type of the node |
| `forms` | group types of the node, each `required` or `optional`, with the fields this version shows |
| `contexts` | the rule under which the article can be ordered (§3.2) |
| `context_from` | the status from which the new node is itself a context (§5.2) |
| `quote_required` | default: `C` no, `A` and `B` yes (§6) |
| `route` | how it is produced: `instant` · `procure` · `service` · `automation` (§8.1) |
| `parts` | optional bill of material: articles and quantities a service needs |
| `key_rule` | which field must be unique, and within what (a site id within the account) |
| `max_per_context` | optional (one "main contact" per account) |

Articles have **versions** with `draft → released → withdrawn`. An order
position names the version that was released when the cart was submitted; a
withdrawn article stays readable in old orders and can no longer be ordered.

### 3.2 Context rules

A context rule is deliberately small:

- **`under`**: the object types (or articles) whose nodes may be the context.
  A workplace under a room; a monitor under a workplace.
- **`needs_on_path`**: types that must exist above the context. "A workplace
  in a room on a floor in a building at a site" is `under: Room` plus the
  rules of Room, Floor and Building — the chain follows from each article's
  own `under`, it is not written twice.
- **`needs`**: other nodes that must exist under the same context and have
  reached a status (a docking station before a second monitor).
- for `act`: **`targets`**, the types and statuses the article works on.

No expression language in the first version. What these four cannot say is
collected and decided with stage 3.

### 3.3 Mirrored into the twin

`sortiment` keeps articles in its **own store** (D3): drafts, versions and
later prices do not belong in the twin. When a version is released, the app
mirrors what the twin needs: the object type, its group types (the forms),
the relation types `part_of` and `responsible`, and the status declaration of
§5. Types are tenant types (F2). The twin never holds an article; it holds
what articles produce.

### 3.4 Sortiment per customer

The first version has **one assortment for all accounts**. The article keeps
an optional list `accounts`; empty means everybody. Assortments per contract
are D17.

## 4. The stock and the screen (`bestand`)

### 4.1 Three columns

| column | shows | acts as |
|---|---|---|
| **left: stock** | everything that exists for the account, as far as the person is responsible, with the status of §5 | choose a node → it becomes the focus |
| **middle: focus** | the chosen node with its subtree **plus the cart's new nodes** in place | choose a node → it is the context for the right column |
| **right: articles** | the articles that can be ordered under the context, with the reason next to those that cannot | choose → fill in the forms → the position appears in the middle |

"Übernehmen" in the middle submits the cart (§7); the new nodes move into the
left column with their status.

The left column tells four things apart at a glance (§5.3): handed over ·
not yet usable but a context · not yet usable and no context · new in this
session. Icon and text, never colour alone (RFC-0118).

### 4.2 The first login

The provider creates an account: one node of type Account and the first
contact with the role account administrator. That person sees one node. They
focus it and the right column shows what an empty account can order: sites
and contacts.

### 4.3 The cart

- **One open cart per person and account** (D6). It is stored on the server
  and survives logout. No list of parked carts.
- A cart position has its **position id** from the first click:
  `<cart number>/<position>`, for example `W-000123/0010` (D9, D16). The
  parent of a position is either a node of the stock or **another position of
  the same cart** — never of someone else's cart (D11).
- The cart is private. Other people see nothing of it until it is submitted.

## 5. The lifecycle of a node

### 5.1 Status

Declared on every stock type in the twin (F3):

```
configured ─▶ offered ─▶ ordered ─▶ in_work ─▶ handed_over ─▶ dismantling ─▶ dismantled
     │           │          │
     └───────────┴──────────┴──▶ cancelled
```

| status | German | meaning |
|---|---|---|
| `configured` | konfiguriert | submitted, waits for the provider's quote |
| `offered` | angeboten | a quote exists, the customer has not answered |
| `ordered` | beauftragt | accepted (or no quote needed); fulfilment may start |
| `in_work` | in Arbeit | a bundle is working on it; may carry a planned date |
| `handed_over` | übergeben | produced and usable |
| `dismantling` | im Rückbau | a dismantling article is ordered for it |
| `dismantled` | rückgebaut | end; the node is retired in the twin (F4), not deleted |
| `cancelled` | storniert | never produced; retired |

A data article jumps `ordered → handed_over` in the same batch that creates
it. A draft has **no status**: it is not in the twin.

Planned and actual dates (`planned_for`, `handed_over_at`) are attributes of
a group `lifecycle` that fulfilment writes.

### 5.2 Context ability

A second, independent property (D5). A node is a context when **all** hold:

1. its status has reached the article's `context_from` (for data articles
   `handed_over`, which they reach at once; a rack may say `ordered` so that
   servers can be ordered into a rack that is still on its way);
2. its status is before `dismantling`;
3. neither the node nor any node above it is **locked** (§5.4).

Positions of the **same cart** may hang under a position that is not yet a
context — that is what a cart is for. Across carts the rule above applies
without exception (D11).

### 5.3 What the left column shows

| display | status | context |
|---|---|---|
| handed over | `handed_over` | yes (unless locked) |
| not usable yet, context | `ordered`, `in_work` | yes |
| not usable yet, no context | `configured`, `offered`, or `ordered` / `in_work` before `context_from` | no |
| being dismantled | `dismantling` | no |
| new in this session | — (cart) | within the cart |

Locked nodes carry a lock mark in addition.

### 5.4 Three ways to change the stock (D7)

1. **Direct action**, no order: lock, unlock, change form data. Done by
   whoever is responsible, recorded with who and when. A **lock** stops new
   orders under the node and everything below it; nothing that is running is
   stopped. Locking a site is how a responsible person announces its end.
2. **An article** with `effect: act` for everything that causes work or
   money: dismantle, move, replace. It goes through cart, quote and order like
   any other.
3. **Cancellation**: free up to `offered`; from `ordered` on it is a request
   to the provider, who decides.

**Dismantling a node with children** is accepted only if every child is
`dismantled` or `cancelled`, or has a dismantling position in the same cart.
The screen offers to add those positions.

Which form fields may be changed directly and which need an article (an
address that triggers a move) is a property of the form field (D18).

## 6. Quote and order

Prices come later. Until then the provider prices by hand:

1. The customer submits the cart. It becomes an **order** with positions.
2. Positions are split (D4):
   - **no quote needed** and every position above them in this cart is the
     same → produced now (§7.2);
   - **quote needed**, and everything in this cart that hangs below such a
     position → status `configured`, and the provider is told.
3. The provider checks, enters prices and dates per position, may reject
   single positions with a reason, and issues the **quote** → `offered`.
4. The customer accepts or declines the quote **as a whole** in the first
   version (D19) → `ordered`, or `cancelled`.
5. A quote has an expiry; after it the positions are cancelled.

`quote_required` is a property of the article. When prices exist in the
article, the provider switches it off per article and the same portal orders
directly.

Who of the customer may accept a quote is a right of its own (§9.2).

## 7. Submitting

### 7.1 Checks (all, before anything is written)

- every context is still a context (§5.2) — someone may have locked a node
  since the position was put into the cart;
- every article version is still released; otherwise the position is shown
  with the newer version and must be confirmed;
- `key_rule` and `max_per_context` against the stock **as it is now** — two
  people may have configured "DE01" at the same time; the second is told who
  was first;
- the person is still responsible for every context;
- required forms are complete.

One failed check stops the whole submission and marks the position. Nothing
is half submitted.

### 7.2 Producing data

All `instant` positions of the order go into **one twin batch** (F4) with the
order number as its id: objects, their groups, the `part_of` relations and
the status. All or nothing; a retry does nothing twice. The position id is
written as the object's source key, so order and node find each other in both
directions.

### 7.3 The order

Orders and positions live in the app's own store. They are never deleted. A
position knows: article and version, context, form data as submitted, status,
quote data, the bundle it went to, and the twin object once it exists.

## 8. Fulfilment

### 8.1 Routes

| route | for | what happens |
|---|---|---|
| `instant` | data (C) | the twin batch of §7.2 |
| `procure` | goods (A) | positions bundled **per supplier** |
| `service` | services, assembly (B) | positions bundled **per service team**, with the material from `parts` |
| `automation` | scripted production | a script with parameters from the order and its context, a person checks and completes (not designed here) |

### 8.2 The bundle

A **bundle** is an object of `bestand`: a number, a route, a receiver, its
positions, a status, dates. Rules decide the grouping (per supplier, per
team, per site); the provider may regroup before sending.

### 8.3 The interface

Whoever fulfils — a case today, a purchasing or assembly app later — speaks
the same three sentences:

1. `bestand` **hands over** a bundle: positions with article, forms, context
   path and the wished date.
2. The receiver **reports progress**: accepted, a planned date, per position
   or for the bundle.
3. The receiver **reports done** (or failed, with a reason), per position.

`bestand` turns these into status changes of the nodes (`in_work`,
`handed_over`) and into dates. The receiver never writes the stock itself.

### 8.4 Cases as the first receiver

- A case template per route (`cases.templates` in the manifest, F8): subkind
  `fertigung`, fields for the wished and the planned date, `steps` from the
  receiving team's queues.
- The case is opened from the backend (F10) with
  `context.object = {kind: "bundle", id: <bundle number>}` (F9). The case text
  lists the positions with their position ids; a link leads into `bestand`.
- The way back is D15.

## 9. People and rights

### 9.1 The contact

A contact is three things (D8):

1. a **node** in the stock (type Person), under the account or a site;
2. a **user** in the tenant's Keycloak, with platform role `user`;
3. **responsibilities**: relations `responsible` from the person to a node,
   with the role as attribute, valid in time (F1), inherited down the tree.

Ordering the article "Ansprechpartner" asks for name and e-mail. Producing it
creates 1, creates 2 in a state that cannot log in, sends the confirmation
mail, and writes the responsibilities that were chosen in the form. When the
mail is confirmed, the login opens. The contact's status in the stock is
`in_work` until then, `handed_over` after.

A contact can be **locked** (the login closes, node and history stay) and can
get or lose responsibilities — a direct action of an account administrator,
not a new contact.

### 9.2 Roles of the customer

First version, two roles (D8):

| role | may |
|---|---|
| **account administrator** | everything in the account: order, lock, order and change contacts, give responsibilities, accept quotes |
| **responsible** (Verantwortlicher) | see and order under their nodes, lock them; accept quotes for their own orders |

Further roles (read only; configure but not submit; accept quotes up to a
limit) are added when the pilot asks for them. The rights are named
separately from the start (`see`, `order`, `lock`, `manage_contacts`,
`accept_quote`), so a new role is a new row, not new code.

### 9.3 Roles of the provider

Declared in the manifest as RFC-0045 role templates and granted by the tenant
admin: article maintenance (`sortiment`), account management, quotes,
fulfilment.

### 9.4 Who checks

`bestand` is the data holder for everything a customer does (F7) and checks
each request against the person's responsibilities. It reads and writes the
twin **as the app**. Where the truth of a responsibility lives is D13.

## 10. Security requirements (proposed)

1. A contact reads and writes **only below nodes they are responsible for**,
   in every door of `bestand`: screen, API, export, search, MCP tools.
2. A contact of account X never learns that account Y exists — not through a
   key collision message, a count, an id sequence or an error text. Cart and
   order numbers are per account or not guessable.
3. A contact has **no way to the twin's own doors** for stock types (§1.2,
   D14). Tested with a contact's session against every twin door.
4. A person cannot give a responsibility they do not hold themselves, and not
   above their own node.
5. A login opens only after the e-mail is confirmed; the confirmation link is
   single-use and expires. A locked contact's session ends at once.
6. Every status change, lock, grant and quote decision records who and when,
   append-only.
7. What a receiver reports (§8.3) is accepted only for positions of a bundle
   that was handed to **that** receiver.
8. A cart is readable by its owner only; the provider sees orders, not
   carts.
9. Form data of contacts is personal data: it follows the twin's rules for
   person types (thin events, RFC-0120 D10) and the erasure rules of RFC-0090.

## 11. Stages

| stage | content |
|---|---|
| **0** | Measure §1.3 on `oaap-test`: tenant types and status from an app; what a `user` sees of the twin; the tree read with 10 000 nodes; a Keycloak user with confirmed e-mail created by an app; a case from the backend and what comes back. Tenant `cds` is set up by Jörg (D2). |
| **1** | `sortiment` with data articles (Account, Site, Building, Floor, Room, Workplace, Contact) and context rules. `bestand` with the three columns, the cart, submission, the twin batch. Contacts with login and two roles. No quote yet: everything in stage 1 is `instant`. |
| **2** | Quote and order (§6), locks and cancellation (§5.4). **One** service article that leaves as a bundle to a case and reports back (§8.4). |
| **3** | Goods with supplier bundles, `parts`, dismantling articles, further roles. |
| **later** | Prices, assortments per contract, automation route, purchasing and assembly as apps. |

Every stage ends on tenant `cds` with Jörg ordering as a customer.

## 12. Decisions

### 12.1 Decided 2026-11-23 (Jörg, in conversation)

| # | Decision |
|---|---|
| **D1** | The **provider** is the tenant, with its own Keycloak. Customers are accounts in it; contacts are users of that tenant. |
| **D2** | The scenario is tested in a new tenant **`cds`**, which Jörg sets up. |
| **D3** | Articles and their relations are maintained in an **app of their own**, with their own data, **mirrored** into the twin. |
| **D4** | First a cart the provider checks and prices: **quote, then order**. Split by `quote_required` per article, so that data articles are still produced at once. Prices, scales, discounts later. |
| **D5** | Usability (status) and context ability are **two properties**; "new in this session" is the cart, not a status. |
| **D6** | **One** open cart per person and account; it survives logout. |
| **D7** | Three ways to change: direct action (lock, data), article (dismantle, move), cancellation. A site has a lifecycle; a lock is how its end is announced. |
| **D8** | A contact is node + user + responsibilities, can be locked and get new responsibilities. Roles steer rights; two to begin with. |
| **D9** | **Early identification**: cart number + position, from the draft on, unique across orders. Cases carry the work first. |
| **D10** | Stage cut as in §11. |
| **D11** | A node that is `configured` or `offered` is a context only **inside its own cart**; across carts from `ordered` on (or the article's `context_from`). |

### 12.2 Decided 2026-11-23, one by one (Jörg chose the recommendation each time)

The alternatives that were on the table are named, so that nobody asks again.

| # | Question | Decision |
|---|---|---|
| **D12** | Names of the two apps. | **`sortiment`** and **`bestand`**. Not "Katalog" (taken by RFC-0050), not "Portal" (the tenant's portal). Also offered: artikel, leistungen, produkte; bestellung, konfigurator, bestellportal. |
| **D13** | Where does a responsibility live: as a relation in the twin, or as a contextual grant of RFC-0045? | **The relation in the twin** — it is valid in time, visible in the stock and can be ordered with the contact. `bestand` checks it. RFC-0045 role templates only for the provider's side. Stage 0 reads `oaap.core.authorization` to see that nothing there contradicts it. Not chosen: a grant of the platform; both with a sync. |
| **D14** | How is a customer kept away from the twin's own doors? | Stage 0 measures what a `user` sees. If anything: stock types get a mark "read only through their app" in the twin — a small, general rule — rather than per-person checking in the twin (RFC-0045 §8.3 stays reserved). Not chosen: contacts without any twin access (no assistant over their own stock); one tenant per customer (against D1). |
| **D15** | How does a case report back to the app that opened it? | The case app publishes a **status event** for cases opened from a backend, naming `context.object`; `bestand` subscribes. No new field on the case. If `vorgaenge` cannot do that soon: `bestand` reads its bundles' cases periodically (stage 2 only). Not chosen: the team reports by hand in `bestand`; a webhook per template. |
| **D16** | Format of cart and order numbers. | One number for cart and order (`W-…` stays the same when submitted), counted **per account**, positions in steps of 10. Not chosen: one counter for the tenant (tells customers the total volume); separate cart and order numbers; an account label in the number. |
| **D17** | Assortments per contract. | Not in stage 1–3; the field `accounts` on the article is enough for the pilot. Not chosen: a contract object from stage 1; article groups per account. |
| **D18** | Which form data may be changed directly? | A property per form field: `free` · `by_article` · `fixed`. Default `free`; key fields `fixed`. Not chosen: per form; everything free; every change as an order. |
| **D19** | May a quote be accepted in parts? | No in the first version: the whole quote, with positions the provider rejected already taken out. Not chosen: positions can be deselected, with or without a second round. |
| **D20** | Does the provider see a customer's stock through `bestand` or through the twin's portal? | Both: `bestand` for work on orders, the twin for everything else. The provider's people are not bound by responsibilities. Not chosen: only `bestand`; provider roles per group of accounts (too early for the pilot). |

### 12.3 Decided 2026-11-24, one by one, after stage 0 (Jörg)

Points 3 and 4 of §1.4 were answered with more than the offered options:
follow the Asset Administration Shell (AAS) and the Digital Product Passport
(DPP) as closely as possible, so that our twins can later be enriched from
outside and enrich industry twins in turn (BaSyx is already among the ideas).
What was read for that on 2026-11-24 is in §12.4.

| # | Question | Decision |
|---|---|---|
| **D21** | Order of D14 against stage 1 (S1). | **The mark "read only through their app" is built first**, as its own platform step in `oaap.data.twin`, before the first contact logs in, and tested against every twin door (§10 no. 3). Not chosen: contacts without a tenant role as a stop-gap (unmeasured whether `bestand` reaches them); both. |
| **D22** | How does a contact get a login (S7)? | **Its own RFC**: an app asks, the platform creates the user in the tenant's Keycloak and sends the confirmation mail (SMTP from RFC-0072). Stage 1 waits for it. Not chosen: the provider's team creates contacts by hand for the pilot; specifying it inside this RFC. |
| **D23** | Where do `sortiment`'s types come from (S2)? | **Fixed types in its manifest**; `sortiment` is an ordinary app, RFC-0120 D8 stays. The article's structure follows the AAS: a **bill of material per IDTA 02011** ("Hierarchical Structures enabling Bills of Material"), hierarchical and nested by reference (`SameAs` to another BOM's entry node, not a copy), with **one BOM per view** (sales, engineering, manufacturing/assembly) — an article ordered in the portal is resolved in assembly by a manufacturing BOM that holds assemblies, purchased items and services. The stock tree follows the **location aspect** of the IEC 81346 extension of 02011. Built on D25. Not chosen: an app may hold `models`. |
| **D24** | How does a responsibility carry its role (S3, D13)? | **Relations get attributes**, in the form of the AAS `AnnotatedRelationshipElement`, each attribute with a semantic ID — the role on a responsibility is the first use. A BOM does **not** put its quantity on the edge: as in 02011, a position is a node with a quantity (`BulkCount`), the edges stay plain. Built on D25. Not chosen: one relation type per role; a responsibility object between person and node; the quantity on the edge. |
| **D25** | Where does the alignment with the AAS metamodel go? | **Its own RFC** "the twin after the AAS metamodel": a semantic ID for every attribute (an own glossary as concept descriptions, or derived from ECLASS / IEC CDD); groups as submodels with substructures (lists, tables, references); a default submodel for free attributes; attributes on relations (D24); the BOM of 02011 as the first submodel template. RFC-0031's line "standard outside, own model inside" stays; the AAS door (`oaap.data.aas`) and BaSyx come later on top. Not chosen: inside this RFC; an amendment to RFC-0031. |
| **D26** | Reading the tree (S6, D20). | **`bestand` reads level by level** and never asks for the whole tree, **and the twin's tree read is fixed** (loading in bulk instead of one object per node; the portal page opens levels on demand), so the provider can look at a large stock in the portal as D20 wants. Not chosen: only level by level (would change D20). |
| **D15** (confirmed) | The way back from a case (S8). | **As decided: `vorgaenge` publishes a status event** for cases opened from a backend, naming `context.object`; built **with stage 2**, not before — stage 1 does not need it. The fallback "read periodically" does not exist (S8) and is dropped. Not chosen: reading back first, the event later. |

### 12.4 Read 2026-11-24 for D23–D25 (AAS and DPP)

Checked in the original publications (IDTA PDFs, templates on
`github.com/admin-shell-io/submodel-templates`) unless marked *inferred*.

- **IDTA 02011 v1.1** (2024-06-14), submodel
  `https://admin-shell.io/idta/HierarchicalStructures/1/1/Submodel`: one
  `EntryNode` (the shell's own asset), nested `Node`s, per level `HasPart` /
  `IsPartOf` / `SameAs` as plain `RelationshipElement`s, `BulkCount` **on the
  node**, `ArcheType` `Full` · `OneDown` · `OneUp`. Only one of HasPart and
  IsPartOf; edges stay inside the submodel; another BOM is joined by `SameAs`
  to its entry node (self-managed entity, resolved through registry/discovery).
  BOM views are explicitly **out of scope** of the template (§1.3 there);
  one submodel instance per view is *inferred*.
- **IDTA 02011-1** (IEC 81346 extension, 2025-08): aspect nodes for function
  (=), product (-), **location (+)**, type (%), other (#); one aspect per
  submodel.
- No template for a bill of process; IDTA 02031 Process Parameters combines
  with 02011 for step order; IDTA 02050 Purchase Order 1.0 exists (its
  position structure not read). Services and purchased items have no own kind
  in 02011 — a co-managed node with its own semantic ID is *inferred*.
- **DPP4.0** lists Digital Nameplate 02006 v3.0, Carbon Footprint 02023,
  Technical Data 02003, Maintenance Instructions 02018, Handover Documentation
  02004 v2.0, Recycling/End-of-Life 02077 (coming). **IDTA 02099-1 "DPP Part 1:
  Metadata"** v1.0 (2026-05-28): `DppMetadata` with `granularity` Model · Item
  · Batch — Model is the article, Item the installed piece (*inferred* fit).
  A shell is not yet a DPP; the DPP is the needed submodels plus this one.
- Identity of an article and a piece: Nameplate 3.0 semantic IDs from IEC CDD,
  e.g. ManufacturerProductDesignation `0112/2///61987#ABA567#009`, SerialNumber
  `0112/2///61987#ABA951#009`.
- Not read: 02050's positions, the battery passport templates' contents.

## Deutsche Zusammenfassung

**Worum es geht.** Ein Dienstleister betreibt IT-Landschaften für Kunden über
viele Standorte. Der Kunde baut seinen **Bestand** selbst auf, indem er
**hineinbestellt**. Alles ist ein Artikel: Ware (A), Dienstleistung (B) und
auch Datenobjekte (C) wie Standort oder Ansprechpartner. Bestellt wird immer
**unter einem Knoten des Bestands**, dem Kontext. Ein Datenartikel wird sofort
produziert (ein Datensatz im Zwilling) und ist sofort Kontext für Weiteres.

**Zwei Apps im Mandanten des Dienstleisters** (D12):

- **`sortiment`** — Artikelpflege: Artikel mit Versionen, Formularen und
  Kontextregeln („unter welchem Knoten bestellbar“). Eigene Daten; in den
  Zwilling gespiegelt werden nur Typen, Formulare und der Status.
- **`bestand`** — das Portal des Kunden: drei Spalten (Bestand, Fokus,
  Artikel), Warenkorb, Auftrag, Lebenszyklus.

Der Bestand selbst liegt **nur im Zwilling**: Knoten = Objekt, Formular =
Gruppe (Submodell), Baum = Relation, Lebenszyklus = erklärter Status.

**Lebenszyklus (§5).** Status: konfiguriert → angeboten → beauftragt → in
Arbeit → übergeben → im Rückbau → rückgebaut (dazu storniert). Daneben, davon
unabhängig, die **Kontextfähigkeit**: ab welchem Status ein Knoten Kontext
ist, sagt der Artikel; eine **Sperre** am Knoten oder darüber nimmt sie weg.
Ein Entwurf hat keinen Status, er ist der Warenkorb.

**Angebot (§6).** Beim Abschicken teilt sich der Warenkorb: Was kein Angebot
braucht (Daten), wird sofort produziert. Der Rest wartet als „konfiguriert“,
der Dienstleister prüft und bepreist von Hand, der Kunde nimmt an — erst dann
wird gefertigt. Mit Preisen im Artikel fällt die Angebotspflicht später je
Artikel weg.

**Abschicken (§7).** Erst alle Prüfungen (Kontext noch gültig, Schlüssel noch
frei, Zuständigkeit noch da), dann alle Datenartikel in **einem** Schreibvorgang
im Zwilling — ganz oder gar nicht.

**Fertigung (§8).** Positionen verlassen den Auftrag als **Bündel** (je
Lieferant, je Serviceteam, mit Stückliste). Empfänger ist zuerst ein Vorgang,
später eine Einkaufs- oder Montage-App — mit derselben Schnittstelle:
übergeben, Fortschritt melden, fertig melden. Daraus schreibt `bestand` den
Status der Knoten fort.

**Zu deiner Frage nach Vorgängen:** Den „speziellen Typ“ gibt es schon (eine
Vorlage mit Unterart), die „externe Nummer“ auch (der Objektbezug des
Vorgangs nimmt eine Nummer der App). Was **fehlt**, ist der Rückweg: Wie
erfährt `bestand`, dass der Vorgang weitergegangen ist (D15).

**Ansprechpartner (§9).** Knoten im Bestand + Benutzer im Keycloak +
**Zuständigkeiten** (Rolle × Knoten, vererbt nach unten). Login erst nach
bestätigter E-Mail. Zwei Rollen zum Start: Account-Administrator und
Verantwortlicher.

**Der wichtigste Befund (§1.2, D14).** Alle Kunden liegen in **einem**
Mandanten, und der Zwilling trennt heute nach Typen, nicht nach Teilbäumen.
Ein Ansprechpartner von Kunde X darf deshalb nie an die eigenen Türen des
Zwillings kommen (Portalseiten, MCP, Chat), sondern nur über `bestand`, das
jede Anfrage gegen seine Zuständigkeit prüft. Stufe 0 hat gemessen, dass ein
normaler Benutzer heute **alles** sieht (§1.4, S1).

**Stufen (§11).** 0: messen, was in §1.3 offen ist. 1: Datenartikel, drei
Spalten, Warenkorb, Ansprechpartner mit Login. 2: Angebot, Sperren, Storno,
ein Dienstleistungsartikel über einen Vorgang. 3: Ware, Stücklisten, Rückbau.
Später: Preise, Sortiment je Vertrag, Automatisierung, Einkauf und Montage
als Apps.

**Entschieden** sind D1–D11 (aus dem Gespräch) und D12–D20 (einzeln
durchgegangen, jeweils wie empfohlen): D12 die Apps heißen `sortiment` und
`bestand` · D13 Zuständigkeit als Relation im Zwilling, `bestand` prüft · D14
Bestandstypen bekommen im Zwilling die Marke „nur über ihre App lesbar“ · D15
die Vorgänge-App meldet Statusänderungen als Ereignis, `bestand` hört zu ·
D16 eine Nummer für Warenkorb und Auftrag, je Account gezählt · D17 erst ein
Sortiment für alle · D18 je Formularfeld: frei, nur über Artikel, fest · D19
ein Angebot wird nur ganz angenommen · D20 der Dienstleister arbeitet in
`bestand` und im Zwilling.

**Stufe 0 gemessen (24.11., oaap-test, Wegwerf-Mandant `s0`, §1.4).**
Ein Benutzer mit Rolle `user` liest heute den **ganzen** Zwilling: im Portal
und über die MCP-Tür. Nur Schreiben ist ihm verwehrt. D14 muss also gebaut
sein, bevor sich der erste Ansprechpartner anmeldet. Eine App darf keine
eigenen Typen anlegen, das darf nur ein Integrations-Client mit `models`.
Beziehungen tragen keine Attribute, die Rolle an der Zuständigkeit wird still
verworfen. Der Status funktioniert. 11 111 Knoten zu schreiben dauert gut zwei
Minuten. Den Baum liest der Zwilling bis Tiefe 3 in 8 s, Tiefe 4 bricht nach
30 s ab. `bestand` muss deshalb Ebene für Ebene lesen. Eine App kann keine
Benutzer anlegen, und eine E-Mail-Bestätigung gibt es nirgends. Das ist die
größte Lücke für Stufe 1 und braucht ein eigenes RFC. Vorgänge lassen sich aus
dem Backend öffnen, aber nichts meldet zurück, und abfragen geht auch nicht.
D15 ist damit ganz offen. Für Stufe 1 stehen sechs Punkte zur Entscheidung an
(§1.4 unten).

**Entschieden nach Stufe 0 (24.11., D21–D26, §12.3).** Die Marke „nur über
ihre App lesbar“ wird zuerst gebaut, vor dem ersten Ansprechpartner (D21).
Benutzer aus einer App mit Bestätigungsmail bekommen ein eigenes RFC (D22).
`sortiment` erklärt feste Typen; der Artikel folgt der AAS-Stückliste
IDTA 02011: hierarchisch, über Verweis verschachtelt, je Sicht (Verkauf,
Konstruktion, Fertigung) eine Stückliste; der Bestand folgt dem Ortsaspekt
nach IEC 81346 (D23). Beziehungen bekommen Attribute nach dem
`AnnotatedRelationshipElement`, mit Semantik; die Menge einer Stückliste
bleibt wie in 02011 am Knoten (D24). Der Zwilling nach dem AAS-Metamodell
(Semantik für jedes Attribut, eigenes Glossar, Teilmodelle mit
Unterstrukturen, Vorgabe-Teilmodell) wird ein eigenes RFC (D25). `bestand`
liest Ebene für Ebene, und der Baum im Zwilling wird repariert (D26). D15
bleibt: `vorgaenge` meldet Statusänderungen als Ereignis, gebaut mit Stufe 2.

**Nicht gelesen, nicht gemessen:** das Datenmodell des Vorprojekts; der Chat
Ende zu Ende als `user` (die MCP-Tür ist gemessen).

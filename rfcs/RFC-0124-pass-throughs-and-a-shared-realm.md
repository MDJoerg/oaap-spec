# RFC-0124: Pass-Throughs and a Shared Realm — A Public Name on One Node, the App on Another, One Login for Several Tenants

- **Status:** **Draft (2026-11-23)** — D1–D14 open (§12). Nothing built,
  **nothing measured**. The facts in §1.1–§1.3 were read the same day in the
  specs and in reference 0.1.358; what was **not** read or measured is listed
  in §1.5, and stage 0 (§10) answers it before anything is built on it.
- **Date:** 2026-11-23
- **Authors:** Jörg (the idea, 2026-11-23: "eine Art Proxy Instanz, die an
  einen anderen Knoten durchroutet … vom oaapx01 Knoten mit einem extern
  sichtbaren Namen auf eine App im Knoten oaapi01 … dass oaapi01 auch nur
  durchroutet: z.B. an oaap-bernd, damit oaap-bernd als Knoten nach außen
  nicht freigegeben werden muss … dass wir einen führenden tenant mit keycloak
  haben und sich andere Mandanten da ran hängen können"), Claude (facts,
  design)
- **Depends on:** RFC-0006 (edge and behind-edge mode), RFC-0033 (the
  connector, offers, exposures; its stage 4 is the ancestor of part A),
  RFC-0041 (a tenant's provider is a URL; binding to `(provider, sub)`),
  RFC-0091 (roles per realm group), RFC-0115 (a tenant's own domain)
- **Related:** RFC-0018 (an instance's own names), RFC-0022 D3 ("users are
  not shared, identity providers are"), RFC-0044 (people into instance
  networks — a different thing), RFC-0060 (the chain of AI gateways — an
  app-level chain, §2.2), RFC-0066 (the person carried through to a backend),
  RFC-0082 (node alias), RFC-0085 (fleet observation)
- **Changes (when accepted):** `oaap.net.connector` (a new offer kind and the
  pass-through; WebSocket through the tunnel), `oaap.core.gateway` (sites for
  a pass-through on the outer node; the tunnel as the trusted edge on the
  inner node; forwarding by a middle node), `oaap.core.tenant` (attaching a
  tenant to a realm another tenant leads), `oaap.core.identity` (nothing in
  the login itself; the refusals of §7.3)
- **Not part of this RFC:**
  - **A login on the outer node in front of a pass-through.** That is an
    exposure (RFC-0033 §3) and stays one. A pass-through carries; it does
    not sign anybody in (§4).
  - **One node vouching for a person to another node.** No identity header
    crosses a node. The person carried to a backend (RFC-0066) is a
    different mechanism for a different consumer.
  - **Rendezvous between two inner sites** (RFC-0033 stage 5), load
    balancing, failover across tunnels.
  - **Sharing users between tenants.** A shared realm shares the *provider*;
    every tenant keeps its own records and its own roles (§7.1).
  - **Wildcard certificates.** Names get their certificates one by one, as
    today.

## Summary

Two things that belong together because the second makes the first simple.

**Part A — the pass-through.** A node with a public address answers for a
name whose app runs on another node. Today the connector can do that only as
an *exposure*: a random name, at most seven days, behind the outer node's
login, without WebSocket. This RFC adds the durable form: a **pass-through**
is a chosen public name on the outer node that leads through the tunnel to
the node that owns the name. The outer node terminates TLS and carries; it
shows no login, adds no identity, and keeps the `Host` the visitor used. A
node in between may carry on to a third node (`oaapx01` → `oaapi01` →
`oaap-bernd`), so that one node is the only door of a home network.

**Part B — the shared realm.** If the node that runs the app also signs the
person in, no node has to trust another node's word. That needs a login
service every tenant can reach. This RFC lets one tenant **lead** a realm and
other tenants — on the same node or on another — **attach** to it. The same
person then signs in once at the realm and is a separate principal with
separate roles in each tenant.

## 1. Facts

### 1.1 The connector and the edge (read 2026-11-23)

| # | Fact | Where |
|---|---|---|
| F1 | The inner node dials out and holds the tunnel; it has no listener. The **offer list lives on the inner side** and is the only thing a tunnel carries. Each tunnel belongs to exactly one tenant on the outer node. | `oaap.net.connector` 2.1–2.3, RFC-0033 D2, D3 |
| F2 | An **exposure** is one target behind a random name `<random>.t.<node>`, behind the outer node's login unless `--public`, with a time limit: default 8 hours, **maximum 7 days**, at most 10 per owner. | reference `connect/app.py` (`EXPOSE_MAX_TTL`, `EXPOSE_PER_OWNER`) |
| F3 | **A WebSocket through the tunnel is refused with 501**, for `via` destinations and for exposures alike. | `connect/app.py`, `handle_via`, `handle_exposed` |
| F4 | The tunnel drops `Host` and all `X-Forwarded-*` as hop headers: the inner target is called under its own address and learns nothing about the name the visitor used. An exposure also takes the outer node's session cookie and platform API keys out of the request. | `connect/app.py` (`HOP`, `_strip_platform_credentials`) |
| F5 | An offer may name the node's front door (the gateway), never a platform service behind it. | `connect/app.py` (`FRONT_DOOR`, `PLATFORM_HOSTS`) |
| F6 | An **edge** forwards other platforms' hostnames, with their subtree two levels deep, to a target address; it terminates TLS, gets certificates on demand, **keeps `Host`** and sets `X-Forwarded-Proto` / `-For`. | `oaap.core.gateway`, "Edge side" |
| F7 | A platform **behind an edge** serves its external names over plain HTTP, accepts them **only from the one configured edge address**, believes that address's `X-Forwarded-*` and nobody else's, and strips and re-sets identity headers itself. | `oaap.core.gateway`, "Backend side" |
| F8 | "A whole platform through the tunnel" (the edge on the outer node, the offer a hostname subtree) is RFC-0033 stage 4. It is **not specified and not built**. | `oaap.net.connector` header |
| F9 | The fleet status document already raises an `attention` item when a tunnel is down. | RFC-0033 §2.1 |

### 1.2 Login and realms (read 2026-11-23)

| # | Fact | Where |
|---|---|---|
| F10 | A tenant's provider is a **URL** (issuer, client id, client secret). Nothing in the platform says "the local Keycloak". | RFC-0041 K2 |
| F11 | The login is started and comes back **on the tenant's own name**: `https://<label>.<node>/auth/oidc/callback`, or on the tenant's domain. The realm client must know that address to the character. | RFC-0115 §4 |
| F12 | The token is fetched over the back channel; the **channel is the proof** of the issuer. An issuer reachable from the internet over plain `http` is refused. | RFC-0041 §5.2 |
| F13 | A binding is `(kind\|issuer, sub)` within one tenant. Never matched by e-mail or name. Another issuer breaks every binding. | reference `idp.py` (`provider_key`, `find_binding`) |
| F14 | `oaap idp provision <connector> --tenant <t> --space <realm>` exists. **A realm that is already there "is used as it is"**; a client that is already there gets this node's redirect address added and nothing else touched. | reference `idp_admin.py` (`provision`), `appctl.py` |
| F15 | The client is named **after the node** (`oaap-<node>`), with the comment "a realm belongs to one tenant anyway". Two tenants of one node in one realm would therefore share one client. | `idp_admin.py` (`client_for`) |
| F16 | The connector's service account (`create-realm` only) administers the realms **it created** and gets 403 on any other. | RFC-0041 §5.3, measured 2026-09-23 |
| F17 | What a first login gives is a setting **per tenant**: `eingang` (nothing, the default), `role`, `groups`. Only a `server_admin` moves it. A realm group can give `guest`, `partner` or `user`, nothing higher. | RFC-0041 K4, RFC-0091 |
| F18 | Self-registration, the second factor and foreign brokers are settings **of the realm**. `first_login: role` together with an open way into the realm is refused. | RFC-0041 K7, RFC-0091 stage 1 |
| F19 | The built-in provider never goes away: the operator keeps a local password, a tenant may keep local users beside a realm. | RFC-0041 K2 |

### 1.3 What runs today

- `oaapi01` (`oaap-demo`) holds a tunnel to `oaapx01`; the AI gateway on
  `oaapx01` reaches the one on `oaapi01` through it (2026-11-13). That is a
  chain of **apps**, each with its own key — not a pass-through (§2.2).
- `oaapx01` runs a Keycloak (`auth.oaap.joomp.de`) with the realm `pxx` and
  others made by the connector.

### 1.4 What follows

- F2–F4 are why an exposure cannot be stretched into this: its name is
  random and expires on purpose, its login is the outer node's, it changes
  the request, and it cannot carry a chat or a video call.
- F6–F8: the two halves of a pass-through exist. The edge knows how to carry
  a name without touching it; the tunnel knows how to reach inward without a
  door. Stage 4 of RFC-0033 named their sum and stopped there.
- F10–F13: the login needs nothing from the nodes in between except that the
  callback arrives under the name the realm knows. **Login at the target is
  already the shape of the platform.**
- F14–F16: attaching to an existing realm half exists (`--space`), and
  stops at the admin credential: a second node cannot write into a realm
  another node's account made.

### 1.5 Not read, not measured

- Whether the tunnel's framing carries a long-lived, two-way stream at all,
  and what a WebSocket costs in it (F3 is a refusal, not a measurement).
- Whether a gateway in behind-edge mode can take **the local connector** as
  its trusted edge instead of an address in the LAN (F7).
- A login that starts and comes back through one hop, and through two:
  redirect, callback, session cookie, the return to the page asked for.
- Whether a tenant's domain (RFC-0115) works on a node behind an edge for
  all of §4 there (its stage 3, D8), or only for names.
- Two tenants of **one** node in one realm with the shared client of F15,
  and what the session of one means for the other.
- How long Keycloak's own session lets a person into a second attached
  tenant without asking again, and what a logout in one tenant ends.
- Which existing apps break behind a pass-through because they hold a base
  URL (Forgejo, a wiki, Keycloak's issuer).
- How `oaap-bernd` and `oaap-test` are reached inside the home network
  today (which of them sits behind `oaapi01` as an edge).

## 2. Words

### 2.1 The objects

| Word (German in the UI) | Meaning |
|---|---|
| **pass-through** (Durchleitung) | a durable public name on an outer node that is carried, unchanged, to the node that owns the name |
| **host offer** (Namensangebot) | on the inner side: "this tunnel may carry requests for these names", and where they go — this node's own front door, or the next node |
| **outer node** | terminates TLS for the name and carries. Knows the name and the tunnel, nothing behind it. |
| **middle node** | takes a pass-through from its tunnel and hands it to a node it can reach. Optional. |
| **target node** | owns the name: the tenant, the instance, the login |
| **leading tenant** (führender Mandant) | the tenant a realm was made for; its node's connector administers the realm |
| **attached tenant** (angehängter Mandant) | a tenant that signs its people in at a realm another tenant leads |

### 2.2 Four things that are not the same

| | `via` destination | Exposure | Pass-through (this RFC) | App chain (RFC-0060) |
|---|---|---|---|---|
| Who calls | an app on the outer node | a browser | a browser, a client, anybody | an app, hop by hop |
| Name | private to the tenant | public, random | **public, chosen** | each hop has its own |
| Lifetime | until revoked | hours to 7 days | **until removed** | until revoked |
| Login | the platform adds a credential | the **outer** node's | the **target** node's | a key per hop |
| `Host` and cookies | replaced | replaced, cookie removed | **untouched** | replaced |
| What the outer node knows | an offer name | an offer name | a public name | everything; it is an app |

## 3. Part A — the pass-through

### 3.1 Two declarations, one on each side

Nothing is carried that both sides did not write down (RFC-0033 D2 stays):

```sh
# inner node (the one that dials out): what the tunnel may carry
sudo oaap connector offer add x01 home --host cloud.example.org            # this node's own door
sudo oaap connector offer add x01 bernd --host werkstatt.example.org \
     --next http://10.10.10.95                                             # carry on to another node

# outer node: which public name leads into which tunnel
sudo oaap connect pass add cloud.example.org --tunnel i01 --offer home
sudo oaap connect pass list | pause <name> | resume <name> | remove <name>
```

- A host offer names **hostnames**, each with its subtree two levels deep
  (as an edge route does, F6), and exactly one of: this node's front door,
  or `--next` with the address of a node this one can reach.
- A pass-through on the outer node names one public name (with the same
  subtree), a tunnel and a host offer in it. The outer node refuses a
  pass-through whose name the offer does not cover; the inner node checks
  again on every stream, against its current list.
- Both objects are a `server_admin`'s (D2). The pass-through belongs to the
  tenant the tunnel belongs to on the outer node, and is listed there.

### 3.2 What the outer node does

1. Writes a site for the name: TLS, certificate through ACME as for any
   name of its own, the redirect from plain HTTP.
2. Carries every request into the tunnel **as it came**: method, path,
   `Host`, cookies, `Authorization`. It sets `X-Forwarded-Proto` and
   `X-Forwarded-For` (the edge's part, F6).
3. Shows **no login**, calls identity for nothing, sets no identity header
   and removes any the visitor sent.
4. Carries WebSocket and long answers without buffering (§3.6).
5. When the tunnel is down or the offer is gone, answers 503 with the
   platform's page naming the hop (§3.7).

### 3.3 What the target node does

The target is a platform behind an edge (F7) whose edge is the tunnel:

- It knows the public name as its own: a tenant's domain (RFC-0115), an
  instance's own name (RFC-0018), or the node's external name.
- It accepts requests for that name **only from its connector** (or, at the
  end of a chain, only from the middle node's address), and believes the
  `X-Forwarded-*` of that one sender. Every rule of behind-edge mode holds:
  plain HTTP inside, no ACME for the name, identity headers stripped and
  re-set here.
- Everything else is the target's ordinary work: the tenant's place, the
  login (§4), the app.

### 3.4 What a middle node does

A middle node receives a pass-through from its tunnel and forwards it to
the `--next` address, exactly as an edge forwards a routed name in the LAN
(F6): `Host` kept, `X-Forwarded-*` passed on from the tunnel, nothing
logged of the body, no login. It is not behind an edge for that name and
serves nothing under it itself.

The chain is at most **outer → middle → target** (D5). A longer one is not
refused by a counter in a header anyone could forge; it cannot be written,
because a host offer with `--next` is only carried for a tunnel this node
dialled, never for a request that itself arrived by `--next`.

### 3.5 Which names

A pass-through name MUST NOT be the outer node's external name or lie under
it (D4). Under it the visitor's browser would send the outer node's session
cookie to the target, and the target's cookie of the same name would
overwrite it. The name is therefore a domain of its own — which is also what
makes moving the app to another node an edit of one DNS record and one
pass-through, with nothing visible to its users.

Names of pass-throughs, tenant domains and instance names share one
namespace on the outer node; a collision is refused when the pass-through is
made.

### 3.6 WebSocket and long streams

The chat, LiveKit's signalling, code-server and MCP over streaming need a
connection that stays open in both directions. F3 says the tunnel refuses
it today. A pass-through without it would carry a wiki and nothing else, so
**stage 1 is not done before a WebSocket is carried** (D6). How — a stream
kind in the tunnel's own multiplexing, or one more WebSocket per stream, as
RFC-0044 already does for a TCP connection — is decided by stage 0.

### 3.7 When a hop is down

| What is down | Who answers | With |
|---|---|---|
| the tunnel | the outer node | 503: "Der Knoten hinter diesem Namen ist gerade nicht verbunden." |
| the offer was removed, or the tunnel paused | the outer node | 503, the same sentence — the visitor is not told which |
| the next node behind a middle node | the middle node | 503, passed on |
| the app | the target node | what it answers today |

Both operators see which: the pass-through carries a state on the outer
node's connector page, the host offer one on the inner node's, each with the
time of the last stream; a pass-through whose tunnel is down is an
`attention` item in the fleet status (F9) and reaches the weekly report.

### 3.8 What both sides record

As for every stream today (RFC-0033 §2.4): metadata on both sides — name,
time, bytes, result — never the body. A middle node records the same. The
outer node's record is in the audit log of the tenant the tunnel belongs to.

## 4. The login is the target's

A pass-through never changes who a person is. The request reaches the target
node as if the visitor had come directly, so the target's identity service
does what it does today (F10–F13):

- The tenant's login page is served on the public name.
- With a realm, the browser is sent to the provider and comes back to
  `https://<public name>/auth/oidc/callback` — through the same hops. The
  realm's client must know that address (F11); for a provider the connector
  made, activating the tenant's domain adds it, as today.
- The target fetches the token itself, over its own way out to the internet
  (F12). The provider must therefore be reachable **by the browser and by
  the target node under the same `https` address** (§8).
- The session cookie is the target's, on the pass-through's name. The outer
  and the middle node see it go by and have no use for it.

What this buys: **no node trusts another node's statement about a person.**
A compromised outer node can read and change traffic it carries — it
terminates TLS, as an edge does (RFC-0006 said so, and §9.3 repeats it) —
but it cannot mint a session, because it holds no key the target believes.

## 5. Where a pass-through is the right tool

| Wish | Tool |
|---|---|
| An app on node A calls a backend on node B | `via` destination (RFC-0033) |
| Show something from the LAN for an afternoon | exposure (RFC-0033 §3) |
| **An app at home, a durable public name, its own login** | **pass-through** |
| **A whole node at home without a port opened** | **pass-through for the node's name** (RFC-0033 stage 4, now specified here) |
| A person needs a port inside an instance's network | remote access (RFC-0044) |

A node that can dial out needs no middle node: `oaap-bernd` may hold its own
tunnel to `oaapx01`. The middle node is a **choice**, for a network that
should have one door: one tunnel to watch, one place to pause, and nodes
behind it that need no way out of their own (D5).

## 6. Part B — the shared realm

### 6.1 Leading and attached

- A realm is made **for one tenant**, as today. That tenant **leads** it:
  only its node's connector changes the realm's settings (self-registration,
  second factor, brokers, groups).
- Another tenant **attaches**: its provider is that realm's URL with a
  client of its own. It reads the realm's settings and shows them; it cannot
  change them.
- Attaching changes nothing about K4 and K5 of RFC-0041: the host decides
  the tenant; the person arriving at tenant B is a principal of tenant B,
  bound to `(issuer, sub)` there, with tenant B's first-login rule and tenant
  B's roles. The sentence "a realm belongs to one tenant" becomes "a realm is
  **led** by one tenant".

### 6.2 Attaching without handing over a key

The admin credential of the leading node never leaves it (F16 is then not a
problem but the rule):

```sh
# leading node: make a client for the tenant that wants in
sudo oaap idp client add auth --space home --for cds@oaap-bernd \
     --redirect https://cds.example.org/auth/oidc/callback
#   → issuer, client id, and the secret, shown once

# attaching node: enter them
sudo oaap tenant provider attach cds --issuer https://…/realms/home \
     --client-id oaap-oaap-bernd-cds --secret-stdin
```

- The client is named after **node and tenant** (changing F15 for attached
  tenants), so two tenants never share a secret and one can be cut off
  without the other.
- On the same node the two steps are one command; the rule is the same.
- The leading tenant's page lists who is attached (node, tenant, since
  when), and `oaap idp client remove` ends an attachment from the leading
  side. The attached tenant's local records stay, as when a provider is
  removed today.

### 6.3 What a first login gives

A shared realm is a wide door: everybody in it can arrive at every attached
tenant. Therefore, for an attached tenant:

- the default stays `eingang` (F17);
- `role` — one role for everybody who arrives — is **refused**, unless the
  `server_admin` sets it with a reason that is written to the tenant's log
  (the same form as `role` with self-registration, F18);
- `groups` is the intended setting: a group of the realm gives `guest`,
  `partner` or `user` in *this* tenant (RFC-0091). Which person is in which
  group is decided once, at the realm; what a group is worth is decided by
  each tenant.

### 6.4 The name of the realm

A shared realm is named after the **people** in it — a household, a firm, a
club — not after a node and not after a tenant (D10). A realm can move
(RFC-0041 K6); a tenant can be renamed (RFC-0026); the people stay who they
are.

An existing tenant realm should not be turned into a shared one by
attaching to it quietly: its settings were chosen for one tenant (F18).
Attaching to a realm that has an open way in is refused until the
`server_admin` of the leading node confirms it.

### 6.5 What it is for

Jörg's case: at home, apps sorted into several tenants — one for the family,
one for the lab, one for a project with guests — and one login for all of
them. Each tenant keeps its own apps, backups, roles and admin; the realm
holds the people once.

## 7. Where the login service stands

**A login service must not be harder to reach than the apps that depend on
it.** Two honest places:

| | On the outer node (`oaapx01`) | On the home node, published by a pass-through |
|---|---|---|
| Reachable from outside | always | when the home line is up — as the apps are |
| Home network without internet | **nobody with a realm identity signs in** | works, if the name resolves at home (below) |
| Who holds the identities | the hoster's machine | the machine at home |
| First measurement | shortest: the Keycloak exists | needs part A first |

The issuer must be **one address for the browser and for every attached
node** (F12, F13): two names for one realm are two issuers and two sets of
bindings. At home that means the public name must lead to the home node from
inside too — a local DNS answer, or the way out and back in through the
outer node. Which, and what the Fritzbox does to it, is stage 0.

The built-in provider stays in both cases (F19): the operator's own
password works when the realm does not.

## 8. Apps

- An app that builds its links from the forwarded host needs nothing: the
  `Host` it sees is the public name (§3.2), the scheme is the visitor's
  (§3.3).
- An app with a configured base URL (Forgejo, a wiki, Keycloak's own
  issuer) is given the public name by its operator, as under a tenant's
  domain (RFC-0115 §6). The RFC does not rewrite app configuration.
- An app cannot tell that it is reached through a pass-through, and must
  not have to (RFC-0033 §8).

## 9. Security requirements (proposed)

1. **Both sides declare.** A pass-through exists only if the inner node's
   current offer list covers its name. Removing the offer or pausing the
   connector cuts it at once, from inside, without asking anyone.
2. **The outer node cannot widen.** It cannot add a name to an offer, cannot
   resume a paused tunnel, and learns names, never addresses.
3. **The outer node reads what it carries.** It terminates TLS. Whoever
   runs it can read and alter the traffic of every pass-through. This is
   said on the page where a pass-through is made, and it is the reason an
   operator chooses the outer node as carefully as a hoster. Re-encryption
   inside the tunnel is a later stage (D13).
4. **No identity crosses a node.** The outer and the middle node set no
   identity header and remove any they are sent; the target strips and
   re-sets them itself (F7). A session is only ever made by the target.
5. **The target takes the name from one sender.** Requests for a
   pass-through's name are accepted only from the connector, or from the one
   configured middle node; any other client gets 403.
6. **A pass-through name is never under the outer node's name** (§3.5), so
   no cookie of one node reaches another.
7. **One name, one tunnel, one tenant.** A name cannot be passed through by
   two tunnels, and a tunnel of tenant A cannot carry a name bound for
   tenant B on the outer node.
8. **A chain cannot grow by itself** (§3.4).
9. **The admin credential of a realm stays on the leading node.** An
   attached tenant holds a client secret for its own client and nothing
   else.
10. **An attached tenant is closed by default:** `eingang`; `role` only on
    the operator's written word; a realm group never gives more than `user`.
11. **Realm settings change in one place.** An attached tenant's node has no
    command that writes into the realm.
12. Names, titles and labels that arrive from another node (offer names,
    the title of an attached tenant) are foreign content: shown as text,
    never interpreted.

## 10. Stages

| Stage | Content |
|---|---|
| **0 — measure** | On `oaap-test` (outer and inner role on one node, then `oaap-test` ↔ `oaapi01`), nothing on `oaapx01`: (a) a long two-way stream through the tunnel's framing, and one WebSocket per stream beside it — time, memory, what breaks at reconnect; (b) a gateway in behind-edge mode whose trusted edge is the connector; (c) a login with a realm that starts and returns through one hop and through two, with a tenant's domain on the target; (d) two tenants in one realm, on one node and on two: bindings, groups to roles, how often Keycloak asks, what logout ends; (e) the same issuer from inside and outside the home network; (f) three existing apps behind a hand-made pass-through: chat (WebSocket), Forgejo (base URL), help (plain pages). |
| **1 — one hop** | host offers, pass-throughs, the outer site, the tunnel as trusted edge, WebSocket, the 503 page, state on both connector pages, the fleet item. CLI and portal (`/connector`). |
| **2 — attach** | `idp client add` / `remove`, `tenant provider attach`, the refusals of §6.3 and §6.4, the list of attached tenants on the leading side. |
| **3 — the middle node** | `--next`, forwarding, state per hop, the page naming the hop. |
| **4 — later** | a whole node's name as a pass-through with the portal's help (RFC-0033 stage 4 closed); re-encryption inside the tunnel; a pass-through asked for by a `tenant_admin` and granted by the operator. |

## 11. Conformance (described; every line gets a bait)

1. A name the inner offer list does not cover is not carried, also when the
   outer node's file was edited by hand.
2. After `connector pause` and after `offer remove` the name answers 503
   within seconds; `resume` on the outer side does not exist.
3. A request with `X-OAAP-User` set by the visitor arrives at the app
   without it; a request the outer node forged with it arrives without it.
4. A pass-through under the outer node's external name cannot be saved.
5. A request for the name that reaches the target from any address but the
   connector's (or the middle node's) gets 403.
6. A WebSocket through one hop stays open for an hour and carries both
   directions; a tunnel reconnect ends it cleanly, not silently.
7. A login with a realm through the pass-through ends on the page that was
   asked for, with a cookie on the pass-through's name and none on the outer
   node's.
8. A tunnel of tenant A cannot be chosen for a pass-through of tenant B.
9. A host offer with `--next` is not carried for a request that arrived by
   `--next`.
10. A person of the shared realm who arrives at an attached tenant has no
    role there (`eingang`); with `groups`, exactly the role of their group
    and never `tenant_admin`.
11. `first_login role` on an attached tenant is refused without the
    operator's reason.
12. The attaching node has no file that holds the realm's admin credential,
    and no command of its that changes a realm setting succeeds.
13. Removing the client on the leading side ends the logins of exactly that
    tenant; the other attached tenants and the leading one sign in as before.
14. The same person has two different user ids in two attached tenants.

## 12. Decisions asked of Jörg

- **D1 — One RFC for both parts?** *Recommendation: yes.* Part A without
  §4 would have to invent trust between nodes; part B is what makes §4 a
  sentence instead of a chapter. They are built in separate stages.
- **D2 — Host offers and pass-throughs are a `server_admin`'s, on both
  nodes?** *Recommendation: yes for stages 1–3.* A public name on a shared
  node is the operator's promise. A `tenant_admin` asking for one is
  stage 4, in the form RFC-0115 §16 already has.
- **D3 — The pass-through is an object of the connector, not an app from
  the store and not an "instance without a container"?** *Recommendation:
  the connector's object.* A proxy app would be a second way to route beside
  the gateway. An instance without a container would put something into the
  instance list that has no backup, no update and no envelope, and every
  reader of that list would need an exception. It is shown on the portal
  beside the instances of its tenant, marked "Durchleitung".
- **D4 — A pass-through name is never under the outer node's own name?**
  *Recommendation: yes* (§3.5). Cost: a pass-through always needs a domain
  or a subdomain the operator controls.
- **D5 — At most one middle node; the direct tunnel per node is the normal
  case?** *Recommendation: yes.*
- **D6 — Stage 1 is not done without WebSocket?** *Recommendation: yes.*
- **D7 — The word: "pass-through" / "Durchleitung"?** *Recommendation:
  yes.* "Proxy-Instanz" says instance, and it is none (D3).
- **D8 — Login only at the target; no node vouches for a person to
  another?** *Recommendation: yes* — the rule the rest of this RFC rests on.
- **D9 — A realm is led by one tenant and others attach; the admin
  credential stays on the leading node, the attaching side gets a client of
  its own (per node and tenant)?** *Recommendation: yes.*
- **D10 — A shared realm is named after its people, and a new realm is made
  for it rather than reusing `pxx` or another tenant's?** *Recommendation:
  yes.* Reusing is possible (§6.4) and asks for a confirmation.
- **D11 — For an attached tenant `role` is refused without a written
  reason; `groups` is the intended setting?** *Recommendation: yes.*
- **D12 — Where does the first shared realm stand?** *Recommendation:
  measure on the Keycloak of `oaapx01` (stage 0 and 2); for the home network
  move it to `oaapi01` behind a pass-through once stage 1 runs and §7's
  question of the one address is measured.*
- **D13 — Re-encryption inside the tunnel is stage 4, and until then the
  page says that the outer node can read?** *Recommendation: yes.* It is
  the same trust an edge has had since RFC-0006.
- **D14 — Stage 0 only on `oaap-test` and `oaapi01`; `oaapx01` when stage 1
  is built and Jörg says so?** *Recommendation: yes.*

## Deutsche Zusammenfassung

**Worum es geht.** Zwei Dinge, die zusammengehören.

**Teil A — die Durchleitung.** Ein Knoten mit öffentlicher Adresse
(`oaapx01`) antwortet unter einem Namen, dessen App auf einem anderen Knoten
läuft (`oaapi01`). Heute kann der Connector das nur als *Freigabe*:
Zufallsname, höchstens 7 Tage, Anmeldung am äußeren Knoten, kein WebSocket.
Neu ist die dauerhafte Form: ein **selbst gewählter öffentlicher Name**, der
durch den Tunnel unverändert zu dem Knoten getragen wird, dem der Name
gehört. Der äußere Knoten beendet TLS (die Verschlüsselung zum Browser) und
reicht durch — keine Anmeldung, keine Identität, derselbe `Host`. Ein Knoten
dazwischen darf an einen dritten weiterreichen (`oaapx01` → `oaapi01` →
`oaap-bernd`), damit das Heimnetz genau eine Tür hat.

**Teil B — der gemeinsame Realm.** Wenn der Knoten anmeldet, auf dem die App
läuft, muss kein Knoten dem Wort eines anderen trauen. Dafür braucht es einen
Anmeldedienst, den alle erreichen. Ein Mandant **führt** einen Realm, andere
Mandanten — auf demselben oder einem anderen Knoten — **hängen sich an**.
Dieselbe Person meldet sich einmal am Realm an und ist in jedem Mandanten ein
eigener Benutzer mit eigenen Rollen.

**Was ich im Bestand gefunden habe (§1).**
- **WebSocket durch den Tunnel wird heute mit 501 abgelehnt** (F3). Ohne das
  trägt eine Durchleitung ein Wiki, aber keinen Chat. Stufe 1 gilt deshalb
  erst mit WebSocket als fertig.
- Der Tunnel **ersetzt `Host`** und nimmt Cookies heraus (F4) — richtig für
  Freigaben, falsch für eine Durchleitung.
- Die zwei Hälften gibt es schon: der **Rand** (RFC-0006) reicht einen Namen
  unverändert weiter, der **Tunnel** kommt ohne offene Tür nach innen. Ihre
  Summe stand als RFC-0033 Stufe 4 im Plan und wurde nie spezifiziert.
- `oaap idp provision --space <realm>` gibt es, und ein vorhandener Realm
  wird „benutzt, wie er ist“ (F14). Es scheitert am Verwaltungskonto: Ein
  zweiter Knoten darf in einen fremden Realm nicht schreiben (F16).
- Der Client heißt nach dem **Knoten** (F15); zwei Mandanten eines Knotens
  im selben Realm würden sich ein Geheimnis teilen.

**Wie es laufen soll.**
- **Beide Seiten schreiben es auf (§3.1).** Innen ein *Namensangebot* („der
  Tunnel darf diese Namen tragen“), außen die *Durchleitung* („dieser Name
  geht in diesen Tunnel“). Wer innen das Angebot streicht oder den Connector
  pausiert, trennt sofort.
- **Der Zielknoten** läuft wie hinter einem Rand, nur ist der Rand der
  Tunnel (§3.3). Er kennt den Namen als eigene Mandanten-Domain (RFC-0115).
- **Der Name liegt nie unter dem Namen des äußeren Knotens** (§3.5), sonst
  schickt der Browser das Sitzungs-Cookie von `oaapx01` an den Zielknoten.
  Eine Durchleitung braucht also immer eine eigene (Sub-)Domain.
- **Anmeldung nur am Ziel (§4).** Der Rücksprung von Keycloak kommt durch
  dieselben Etappen zurück. Ein gekaperter äußerer Knoten kann mitlesen
  (er beendet TLS, wie jeder Rand), aber keine Sitzung ausstellen.
- **Mittlerer Knoten (§3.4):** höchstens einer. Der Normalfall bleibt der
  direkte Tunnel je Knoten; die Kette ist die bewusste Wahl für „eine Tür“.
- **Ausfall (§3.7):** 503 mit lesbarer Seite; beide Betreiber sehen, an
  welcher Etappe es hängt; Eintrag in der Flottenbeobachtung.
- **Anhängen ohne Schlüsselübergabe (§6.2):** Der führende Knoten legt für
  den anderen Mandanten einen eigenen Client an und zeigt das Geheimnis
  einmal; der andere Knoten trägt es ein. Das Verwaltungskonto des Realms
  verlässt seinen Knoten nie.
- **Erstanmeldung im angehängten Mandanten (§6.3):** Vorgabe `eingang`;
  `role` nur mit schriftlicher Begründung; gedacht ist `groups` (Realm-Gruppe
  → Rolle in *diesem* Mandanten, höchstens `user`).
- **Realm-Name (§6.4):** nach den Menschen (Haushalt, Firma), nicht nach
  Knoten oder Mandant. Für den gemeinsamen Realm einen neuen anlegen statt
  `pxx` mitzubenutzen.
- **Wo der Anmeldedienst steht (§7):** Er darf nicht schlechter erreichbar
  sein als seine Apps. Auf `oaapx01`: stabil, aber ohne Internet meldet sich
  zu Hause niemand über den Realm an. Zu Hause hinter einer Durchleitung:
  läuft ohne Internet, braucht aber **eine** Adresse von innen und außen.
  Dein lokales Passwort als Betreiber bleibt in beiden Fällen.

**Stufen (§10).** 0 Messen auf `oaap-test` und `oaapi01` (WebSocket im
Tunnel, Tunnel als Rand, Anmeldung über eine und zwei Etappen, zwei Mandanten
in einem Realm, eine Adresse innen/außen, drei echte Apps) · 1 eine Etappe ·
2 Anhängen · 3 mittlerer Knoten · 4 ganzer Knoten als Durchleitung,
Verschlüsselung im Tunnel, Antrag durch den Mandantenverwalter.

**Offen für dich (§12), jeweils mit Empfehlung:** D1 ein RFC für beides ·
D2 nur server_admin · D3 Objekt des Connectors, keine App und keine „Instanz
ohne Container“ (anders als ich im Gespräch zuerst vorschlug: so eine Instanz
hätte keine Sicherung, kein Update, keinen Umschlag — jede Liste bräuchte
eine Ausnahme) · D4 Name nie unter dem äußeren Knoten · D5 höchstens ein
mittlerer Knoten · D6 Stufe 1 nur mit WebSocket · D7 Wort „Durchleitung“ ·
D8 Anmeldung nur am Ziel · D9 führen/anhängen, eigener Client je Knoten und
Mandant · D10 neuer Realm, benannt nach den Menschen · D11 `role` nur mit
Begründung · D12 erst am Keycloak von `oaapx01` messen, fürs Heimnetz später
nach `oaapi01` · D13 Verschlüsselung im Tunnel später, bis dahin steht es
auf der Seite · D14 `oaapx01` erst auf dein Wort.

**Nicht gemessen (§1.5).** Alles. Insbesondere, ob das Tunnelformat lange
Zwei-Wege-Verbindungen trägt, ob der Connector als „Rand“ taugt, und wie
`oaap-bernd` und `oaap-test` heute im Heimnetz erreicht werden.

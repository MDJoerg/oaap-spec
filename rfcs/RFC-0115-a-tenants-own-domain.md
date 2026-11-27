# RFC-0115: A Tenant's Own Domain

- **Status:** **Accepted (2026-11-20)** — Jörg: „Wie empfohlen“ for D1–D9.
  Stage 0 measured 2026-11-20 (§11); stage 1 built and measured 2026-11-20
  (§12, reference 0.1.331, `oaap.core.tenant` 1.17); live for `bec` on `oaapx01`
  2026-11-20 (§13, reference 0.1.332); stage 2 built and measured 2026-11-21
  (§14, reference 0.1.333, `oaap.core.tenant` 1.18); §15 (Jörg's two wishes, portal and
  hidden instances) built and measured 2026-11-21 (reference 0.1.334, 1.19); stage 3 in part
  (§16: a `tenant_admin` asks for a domain) built and measured 2026-11-21 (reference 0.1.339, 1.22).
  §17 (a website on the domain, two gaps) written 2026-11-27, D10–D12 decided as recommended the same
  day (Jörg: „Wie empfohlen“), nothing built.
- **Date:** 2026-11-20
- **Authors:**
  - Jörg (the need, 2026-11-20): the tenant `bec` on `oaapx01` has the
    domain `*.bec.brandeis.de`. "Wie erreiche ich, dass der gesamte
    Mandant und seine Apps richtig erkannt wird und das OAAP weiß, dass
    sich diese Domaine auf den Mandanten bezieht und die Tenant-Anmeldung
    zeigt?"
  - Claude: facts from reference 0.1.330, design.
- **Depends on:** RFC-0005 (external hostname), RFC-0009/RFC-0018 (an
  instance's own names and aliases), RFC-0026 (tenant labels and former
  labels), RFC-0042 (the tenant as a place), RFC-0091 (a tenant's
  provider through Keycloak, the connector).
- **Related:** idea I-1 (a domain per tenant), RFC-0006 (behind an edge),
  RFC-0075 (sandbox origins of MCP App views), RFC-0047 option B (routing
  by e-mail domain), FAQ „Mehrmandanten-Knoten“ F4.
- **Changes:** `oaap.core.tenant` (a tenant's domain), `oaap.core.gateway`
  (sites for it), `oaap.core.identity` (place resolution, session cookie,
  login on it), `oaap.apps.runtime` (the addresses an app is told).

## Summary

Today every public name on a node is built from the node's external
hostname: the tenant's place is `<label>.<node>` (`bec.oaap.joomp.de`),
an instance is `<instance>.<label>.<node>`. A customer's own domain
exists only per instance, as an alias (RFC-0018). That does not carry a
whole tenant:

- the tenant's place, its start page and its login, have no alias at all;
- an alias on an app with login does not log anybody in: the session
  cookie is widened to the node's hostname only, and the login page is
  found through the node's names;
- every new instance needs its alias by hand.

This RFC gives a tenant **one own domain**. Once the operator has entered
it and DNS points to the node, the node answers

- `<domain>` with the tenant's place: its start page and its login;
- `<instance>.<domain>` with each of the tenant's instances, without any
  per-instance step;

and treats the domain exactly like the tenant's label: the host says
which tenant, for everybody reached through it, and nothing else is
served there. The node's own names keep answering, so nothing that works
today breaks.

## 1. Facts (read 2026-11-20, reference 0.1.330)

| Place | Today |
|---|---|
| **Names** | `tenant_place_hosts` and `instance_auto_hosts` in `appctl.py` compose every automatic public name from the node's external hostname and the tenant's label (plus unexpired former labels). Both say: composed here and nowhere else, the gateway and every message read from it. |
| **Gateway sites** | `write_external_caddy` writes one TLS site per place and per instance name; certificates per name through ACME (HTTP challenge); a plain-HTTP redirect per name pattern. `write_instance_address_caddy` writes the sites of an instance's own names (RFC-0018) with the same body. |
| **Place resolution** | `place.host_place(host, ext, ...)` (identity and portal): the node's apex or a foreign name means no tenant; `<label>.<node>` means that tenant for everyone, a server_admin included; an unknown label means nothing (fail closed). |
| **Session** | identity's `DomainAwareSessionInterface` widens the session cookie to the node's external hostname for hosts under it; any other host gets a host-only cookie. |
| **Tenant login** | the tenant's provider (RFC-0091) is started at `https://<label>.<node>/auth/oidc/start` and returns to `https://<label>.<node>/auth/oidc/callback`; this redirect URI is what the tenant's realm client knows. |
| **Instance login** | every instance site reserves `/auth/*`; identity's `/verify` sends an unknown visitor to the relative `/auth/login`, and after login back to the same instance. |
| **Apps** | an app is told some addresses (`OAAP_UI_SANDBOX_ORIGINS` for the chat's sandbox, internal URLs of platform doors). Most apps build absolute links from the forwarded host. |
| **Tenant record** | label, former labels, title, colours, logo, provider, first-login rule, `tenant_admin_may` (`oaap.core.tenant` 1.16). No domain. |

## 2. The tenant's domain

A tenant record gets one field `domain`:

| Field | Content |
|---|---|
| `name` | the domain, lower case, e.g. `bec.brandeis.de`; never the node's hostname or a name under it, never another tenant's domain |
| `state` | `pending` (entered, DNS not yet seen), `active` (DNS points here, sites written), `off` (switched off by the operator) |
| `checked` | when DNS was last read, and what it said |
| `canonical` | `domain` or `node`: which names the platform prints (§5) |

Only a `server_admin` sets it (D1):

```sh
sudo oaap tenant domain set bec bec.brandeis.de
sudo oaap tenant domain check bec          # reads DNS, activates when it fits
sudo oaap tenant domain off bec            # names stop answering, record stays
sudo oaap tenant domain remove bec
```

**The DNS check** (D2). Activation needs both the domain and one random
name below it (`oaap-check-<random>.<domain>`) to resolve to the node's
public address (IPv4, and IPv6 if the node has one). That proves the
wildcard too, and that ACME can reach the node for every name. A
`pending` domain is checked again daily and by `check`; nothing is
served before it is `active`.

## 3. Names and sites

When the domain is active, the two composers gain the domain as a
second base, for this tenant only:

| Name | Answers with |
|---|---|
| `<domain>` | the tenant's place: the portal scoped to the tenant (RFC-0042), its login |
| `<instance>.<domain>` | the instance, the same site body as `<instance>.<label>.<node>` |
| `<sandbox>.<instance>.<domain>` | not used: one DNS wildcard covers one label. Sandbox hosts (RFC-0075) stay on the node's names (D6). |

- The gateway writes these sites in `write_external_caddy`, from the same
  composers, so every message and the gateway agree.
- Certificates per name, through ACME as today. No wildcard certificate
  is needed. Let's Encrypt limits new certificates per registered domain
  (50 per week); a tenant with many instances meets it only on day one.
- The HTTP redirect covers `http://<domain>` and `http://*.<domain>`.
- A name `<x>.<domain>` that is no instance of the tenant gets no site,
  so the node answers it with nothing. An instance of another tenant is
  never reachable under this domain.
- Behind an edge (RFC-0006) the edge must route the domain too; that is
  stage 3 (D8).

## 4. Place, session and login

- **Place resolution.** `host_place` learns the domain: a host equal to
  an active tenant domain names that tenant, for everyone reached
  through it, a server_admin included; a host under it that is not an
  instance names nothing. A `pending` or `off` domain names nothing.
- **Operator pages.** Pages that only make sense on the node (node
  administration, other tenants, fleet) are not served on a tenant
  domain; they answer with a link to the node's apex (D5).
- **Session cookie.** For hosts under an active tenant domain the cookie
  is widened to that domain. A login at `bec.brandeis.de` therefore
  covers every `<instance>.bec.brandeis.de`; it does not cover the node's
  names, and a login on the node's names does not cover the domain
  (D4). The cookie never spans two tenants.
- **Login page.** `<domain>/auth/login` is the tenant's login, as on
  `<label>.<node>` today: the tenant's provider button, its title,
  colours and logo.
- **Tenant provider.** The provider is started and called back on the
  domain: `https://<domain>/auth/oidc/callback`. The realm client of the
  tenant must know this redirect URI in addition to the old one:
  - for a provider made by the connector (RFC-0091, Keycloak), the
    connector adds it when the domain becomes active and removes it
    when the domain is removed;
  - for a provider the platform does not manage, `domain check` names
    the URI the operator must add, and the login on the domain is
    refused with that sentence until the provider accepts it.
- **Instance login.** Unchanged: `/auth/*` on every instance site, the
  relative `/auth/login`, back to the instance after login.

## 5. Which name the platform prints

Many places print an address: the portal's tiles, the CLI, mails
(RFC-0072/0080), help pages, the chat's links, the MCP gateway's
connection hints, setup recipes. They read from the composers, so the
composers decide.

- With `canonical: domain` (the default once active, D3) the first name
  of every list is the domain name; the node's names follow.
- The node's names keep answering (D3). Nothing a person bookmarked,
  no MCP client registered with an old URL, no recipe that stored an
  address breaks.
- A switch per tenant can later redirect the node's names to the
  domain; not in stage 1.

## 6. Apps

- An app that builds links from the forwarded host needs nothing.
- `OAAP_UI_SANDBOX_ORIGINS` (RFC-0075) lists the origins that may frame
  the sandbox; it gains the instance's domain name, so the chat on
  `chat.bec.brandeis.de` can show MCP App views (stage 2).
- An app with a configured base URL (a Git platform, a wiki, Keycloak's
  own issuer) keeps its node name until its operator changes it; the
  RFC does not rewrite app configuration (D7).

## 7. Security requirements

1. **Only the operator binds a domain to a tenant**, and only after DNS
   shows it points here. A tenant cannot claim a domain, and a domain
   cannot name two tenants.
2. **The domain names exactly one tenant.** No operator page, no other
   tenant's instance, no node apex view is served under it.
3. **Fail closed.** Unknown names under the domain, a `pending` or `off`
   domain, a tenant the node does not have: nothing is served.
4. **The session stays inside the tenant.** The cookie of a tenant
   domain covers that domain only.
5. **Roles do not change.** The domain is an address, not a source of
   rights; who may do what is decided as before (RFC-0041).
6. **Bait tests:** a host `<instance-of-tenant-B>.<domain-of-A>` serves
   nothing; a `pending` domain serves nothing; the cookie set on
   `<domain>` is not sent to `<node>`; an operator page on the domain
   answers with the link to the node; a domain under the node's
   hostname or another tenant's domain is refused at `set`.

## 8. For `bec` on `oaapx01`

What Jörg can do now, before anything is built:

```
bec.brandeis.de      A     <public IPv4 of oaapx01>
*.bec.brandeis.de    A     <public IPv4 of oaapx01>
```

(and `AAAA` if `oaapx01` has a public IPv6). Then, with stage 1 on
`oaapx01`: `oaap tenant domain set bec bec.brandeis.de`,
`oaap tenant domain check bec`; `bec.brandeis.de` shows the bec login,
`chat.bec.brandeis.de` and the others the apps. `bec.oaap.joomp.de`
keeps working.

## 9. Decisions

All nine decided by Jörg on 2026-11-20 as recommended.

- **D1 Who binds a domain.** *Recommendation:* only the `server_admin`
  (CLI, later a page); a `tenant_admin` asks through a request to the
  operator (RFC-0109 requests).
  - Alternative: the `tenant_admin` sets it, guarded by the DNS check.
    The check proves where DNS points, not that the tenant owns the
    domain; two tenants of one node could point the same name here.
- **D2 Proof.** *Recommendation:* the DNS check of §2 (apex and a random
  name below it resolve to the node).
  - Alternative: an additional TXT record with a token. Stronger against
    a domain that already points here for another reason; one more step
    for the customer. Worth it if D1 ever goes to the tenant.
- **D3 Old names.** *Recommendation:* keep the node's names answering;
  the domain is printed first.
  - Alternative: redirect the node's names to the domain. Cleaner, but
    breaks registered MCP clients and OIDC clients until they are
    changed; as a later switch per tenant.
- **D4 Session.** *Recommendation:* one cookie per tenant domain, separate
  from the node's. A person who uses both logs in twice.
  - Alternative: a central login on the node that hands a session to the
    domain (a token exchange across domains). Single sign-on across both,
    but a new mechanism with its own attack surface; the tenant's
    provider already gives single sign-on at the provider.
- **D5 Operator pages on a tenant domain.** *Recommendation:* not served;
  a link to the node's apex.
- **D6 Sandbox hosts.** *Recommendation:* stay on the node's names (a
  second wildcard level would need its own DNS entry per instance).
- **D7 App configuration.** *Recommendation:* not rewritten; the operator
  changes base URLs of apps that have them.
- **D8 Edge mode.** *Recommendation:* stage 3; a node behind an edge
  refuses `domain set` with that sentence until then.
- **D9 How many domains.** *Recommendation:* one per tenant.
  - Alternative: several (a customer with two brands). Adds a choice of
    canonical name and of the cookie; later, if asked.

## 10. Stages and tests

| Stage | Content | Measured by (bait in brackets) |
|---|---|---|
| 0 | Measure on `oaap-test` with a second DuckDNS name (its subnames resolve by themselves): an instance alias with login today, the cookie, the tenant login | what breaks today, written down; nothing built |
| 1 | Domain field and CLI, DNS check, sites for place and instances, certificates, place resolution, session cookie, login page, provider callback on the domain (connector adds the redirect URI), canonical names | `oaap-test`: a tenant on the second name, login through its provider, an app with login, the old names still answer (an instance of another tenant under the domain: nothing; `pending`: nothing; cookie not on the node; operator page: link only) |
| 2 | Sandbox origins, mails, help, recipes and the MCP gateway's hints print the domain; a page for the operator | the chat on the domain shows an MCP App view; a notification mail links the domain |
| 3 | Behind an edge; a `tenant_admin` request for a domain; optional redirect of the node's names | a node behind an edge serves a tenant domain |

## 11. Stage 0 measured (2026-11-20, `oaap-test`, tenant `vuebung`)

**Set-up.** `oaap-test` sits behind the edge on `oaap-demo` (10.10.10.75),
and every name below `oaap-demo.duckdns.org` resolves there, so
`dom0.oaap-demo.duckdns.org` served as the tenant's domain. The edge was
not changed: the requests were sent from `oaap-demo` to `oaap-test`
exactly as the edge forwards them (plain HTTP to port 80, Host
unchanged, `X-Forwarded-Proto: https`), which passes the edge guard.
`vuebung-vorgaenge` got the own name `vorgaenge.dom0.oaap-demo.duckdns.org`
(`oaap app address set`), and a local test user of `vuebung` was created.
`vuebung` has a provider („Mit dem Vereinskonto anmelden“). Everything was
removed afterwards.

| Name | Asked | Answer |
|---|---|---|
| `vuebung.<node>` (the place) | `GET /auth/login` | the tenant's login: title „Verein Uebung“, the provider button |
| `vorgaenge.dom0…` (own name) | `GET /` | 303 to `/auth/login?tenant=<vuebung>`, cookie **host-only** |
| `vorgaenge.dom0…` | `GET /auth/login` | the **node's** login „Anmelden — OAAP“: no tenant title, **no provider button** |
| `vorgaenge.dom0…` | `GET /auth/oidc/start` | **404**: the tenant's provider cannot be started there |
| `vorgaenge.dom0…` | local login, forced password change, `GET /` and `/neu` | 303, 303, then the app (200), cookie host-only |
| `vuebung.<node>` | local login | cookie `Domain=oaap-test.oaap-demo.duckdns.org`: it does not reach `vorgaenge.dom0…` |
| the session of `vorgaenge.dom0…` sent to `vuebung.<node>` | `GET /` | 200: the server accepts a session on any host; only the browser keeps it apart |
| `dom0…` (the domain's apex, no site) | `GET /` | 303 to the **node's** login |
| `chat.dom0…` (no own name) | `GET /` | 303 to the **node's** login |
| `vuebung.<node>` | `GET /auth/oidc/start` | to the provider, `redirect_uri=https://vuebung.<node>/auth/oidc/callback` |

**Findings.**

1. **A member with only the tenant's provider cannot log in on an own
   name at all.** The page shows the node's login without the provider
   button, even with `?tenant=` in the address, and the provider's start
   is 404. Only local accounts of the node get in. For `bec`, whose
   people log in through their provider, an alias is useless for apps
   with login.
2. **One login per name.** On an own name the session cookie is
   host-only, so every alias needs its own login, and a login on the
   node's names does not carry over. The cookie widening of §4 is the
   fix.
3. **Names without a site reach the node's login.** The apex of the
   domain and any name below it that is no instance get a 303 to the
   node's generic login page, not nothing. Behind an edge that is the
   catch-all on port 80; nothing is leaked, but it is the wrong door, and
   §7.3 (fail closed) must hold for the domain from stage 1 on: a site
   for `*.<domain>` that answers unknown names with 404.
4. **A session is not bound to a host.** The server accepted the alias's
   session on the place. That is no privilege gain (same person, same
   tenant checks), but stage 1 should decide whether a session made on a
   tenant domain is refused on other hosts (a bait test either way).
5. **The app is told `http://` names behind an edge.** `oaap app address
   show` prints `OAAP_INSTANCE_NAMES` as `http://…` while the CLI says
   „still reachable at https://…“. Apps that build absolute links from
   this list would link plain HTTP; to check in stage 1.
6. **For a real browser test** with TLS, the edge on `oaap-demo` needs a
   route for the domain (`oaap edge add <domain> <oaap-test>`), which
   gives certificates on demand for names below it. Not done in stage 0:
   it changes a fleet node.

## 12. Stage 1 built and measured (2026-11-20)

**Built** (reference 0.1.331, `oaap.core.tenant` 1.17 §2.4.1).

- `place.py` holds the judgement once, for portal, identity and `appctl`: `tenant_domain`,
  `domain_of_host`, `domain_refusal`, `cookie_scope`, `place_host_of`; `host_place` names the tenant
  for its active domain and no place below it.
- `appctl`:
  - `oaap tenant domain <label> [<domain>|check|off|remove]`. The CLI shape differs from §2's
    sketch (`domain set bec …`): the existing verb takes the label first, and a domain name and the
    words `check|off|remove` cannot be confused (a domain has dots).
  - the DNS check compares with the addresses of the node's OWN external name rather than with an
    address the node believes it has. Directly and behind an edge alike, that name points at the
    entry the world uses (§2 said "the node's public address").
  - sites: the place on the domain (the same portal body), every instance of the tenant as
    `<instance>.<domain>` (from `instance_auto_hosts`, the domain first while canonical), behind an
    edge `*.<domain>` → 404 (stage 0 finding 3), the http redirect for both;
  - sandbox origins filtered to the node's names (D6). **Correction:** §3 gave as the reason that a
    sandbox host would need a second label; it does not (`<instance>--ui.<domain>` is one label). D6
    holds as decided; extending sandboxes to the domain is a small step for stage 2.
  - `oaap idp provision` registers `https://<domain>/auth/oidc/callback` too; activation prints that
    sentence. **Deviation:** §4 said the connector adds it by itself on activation; stage 1 asks the
    operator to run `provision` again (it adds the missing URI and changes nothing else).
- identity: the session cookie follows `cookie_scope`; a return address must share the scope of the
  place; a login from a host below the domain is handed to the domain's place; the logout's return
  goes to the domain's place.
- portal: a tile prints `<instance>.<domain>` while the domain is canonical (`instance_view.auto_host`).
- **D8 narrowed.** Behind an edge the node side needed nothing new (the gateway already writes plain
  sites with the edge guard), so stage 1 does not refuse a node behind an edge; `check` names the
  edge's step (`oaap edge add <domain> <node>`), an existing command. What remains of D8 for stage 3:
  the edge command itself does not check the domain.

**Tests.** `test_tenant_domain.py` (new, 46): place rules, the CLI with a DNS stand-in, the gateway
file directly and behind an edge, the identity service on the domain. Baits: domains below, above or
equal to the node's name and overlapping another tenant's are refused; a pending and a switched-off
domain name nothing and get no site; `check` does not switch an `off` domain back on; the domain's
cookie never covers the node and the node's never the domain; a return address in another scope is
refused; no instance of another tenant below the domain. Two mutations caught (the domain ignored in
`host_place`; the domain's cookie widened to the node). Fifteen neighbouring test files green in the
Linux runner (`test_tenant_place`, `test_tenant_idp`, `test_login_page_idp`, `test_rename`,
`test_tenant_boundary`, `test_ui_sandbox`, `test_idp_connector`, `test_edge_trust`, …, `test_cli_reference`).

**Measured on `oaap-test`** (reference 0.1.330 + these changes staged with `stage.sh`, tenant `vuebung`,
domain `dom0.oaap-demo.duckdns.org`, requests sent from the edge node as the edge forwards them, a
local test user; everything removed afterwards). 9/9:

| Asked | Stage 0 | Stage 1 |
|---|---|---|
| `oaap tenant domain vuebung dom0…` | – | DNS fits (IPv6 and IPv4 as the node's name), active, sites written, the edge step and the provider's URI printed |
| the provider started on the domain | 404 | 303 to Keycloak, `redirect_uri=https://dom0…/auth/oidc/callback`, cookie `Domain=dom0…` |
| Keycloak on that request, before / after `oaap idp provision auth --tenant vuebung` | – | 400 / 200 with the login form |
| `/auth/login` on the domain | the node's login | „Verein Uebung“ with „Mit dem Vereinskonto anmelden“ |
| an app below the domain, not logged in | the node's login | to the domain's place, `back=` the app |
| `nix.dom0…` | the node's login | 404 |
| local login at the domain, then the app below it with the same cookie | one login per name | the app opens, no second login |
| the place's tiles | – | `https://vorgaenge.dom0…/` |
| a login on the node's place | – | cookie `Domain=oaap-test.oaap-demo.duckdns.org`, not the domain |

**Findings.**

1. **Re-provisioning touches more than the redirect URI.** `oaap idp provision` also re-wrote the
   realm's mailbox (the same values). Harmless here; worth a sentence in the activation text, or a
   narrower `--redirects-only`, before an operator runs it on `bec`.
2. **Not measured:** a real browser with TLS through an edge route (`oaap edge add` on `oaap-demo`,
   a fleet node) and a full provider login with a person of the realm. Both belong on the first real
   domain.
3. **Not built in stage 1:** the daily re-check of a pending domain (§2), the operator page, mails and
   help printing the domain (stage 2).

## 13. Live for `bec` on `oaapx01` (2026-11-20, Jörg: „Ja, oaapx01“)

- Backup, then 0.1.331; all 54 public names answered as before, the gateway was not restarted.
- **Finding:** activating `bec.brandeis.de` made the gateway refuse the reload: `chat.bec.brandeis.de`
  was already an instance's own name (RFC-0018), and the automatic name was written a second time.
  The gateway kept its running config; the file on disk was wrong until the domain was switched off a
  minute later. Nobody saw a change.
- 0.1.332: an own name keeps its site and the automatic one is left out; if the gateway still refuses,
  the domain goes back to pending and the files are written without it (two tests, one mutation).
  Backup, update, names unchanged.
- `oaap tenant domain bec bec.brandeis.de`: active, „Already an instance's own name: chat.bec.brandeis.de“.
  `oaap idp provision auth --tenant bec` registered `https://bec.brandeis.de/auth/oidc/callback`
  (and re-wrote the realm's mailbox with the same values).
- Measured from the internet, real certificates: `bec.brandeis.de/auth/login` 200 with „Mit dem
  BEC-Konto anmelden“; `vorgaenge.`, `tools.`, `chat.bec.brandeis.de` 303 to the login; an app's login
  handed to `https://bec.brandeis.de/auth/oidc/start?back=vorgaenge.bec.brandeis.de`; the provider
  start goes to Keycloak with the domain's callback and Keycloak shows its login form (200);
  `nix.bec.brandeis.de` gets no certificate; `bec.oaap.joomp.de` unchanged.
- Not measured: a person actually logging in through the realm on the domain.

## 14. Stage 2 built and measured (2026-11-21)

**Read first: where the platform prints a place.** Besides the two composers of stage 1, three places
built `<label>.<node>` by hand: the link in notification mails (`appctl.notify_link`), the address in
the tenant's face (`place.theme_of`, shown on the login page and in the portal), and the portal's
„Einrichten“ link after a build. The server_admin's tenant menu keeps the node's names on purpose: the
operator's session lives there, a domain has its own cookie (D4).

**Built** (reference 0.1.333, `oaap.core.tenant` 1.18).

- `place.canonical_place_host`: the place as printed -- the domain while canonical. Mails, the face and
  the portal's link read it.
- Portal, the tenant's health page: „Adresse“ (the printed place) and „Eigene Domain“ with its state,
  when it was checked and, while not active, what DNS said. That is the page for the operator and the
  tenant administrator; the CLI stays the door that changes it (D1).
- `oaap tenant domains` and the timer `oaap-domain-check` (daily 04:50, `migrate.sh` and `install.sh`):
  a pending domain becomes active once its DNS fits; an active one is checked and written down, never
  switched off by the timer (a DNS hiccup must not take an address away); a refused reload takes the
  activated domains back to pending, as `check` does.
- Activation names every instance of the tenant with `sudo oaap app restart <key>`: an app learns the
  new names (`OAAP_INSTANCE_NAMES`, domain first) only when its container is recreated, and the platform
  does not restart a tenant's apps on its own.
- **Not changed, on purpose:**
  - `OAAP_INSTANCE_NAMES` says `http://` behind an edge (stage 0 finding 5): RFC-0043 §2.1 defines it as
    the scheme the gateway serves; the browser-facing variant is `OAAP_UI_SANDBOX_ORIGINS` (always https).
  - Sandbox origins stay on the node's names (D6). The sandbox site's `frame-ancestors` already lists the
    instance's domain name, so a chat on the domain may frame its views from the node's name.
  - Recipes and the MCP gateway's connection hints build their URLs from the request's host or from
    `OAAP_INSTANCE_NAMES`; they follow without a change.
- Help (RFC-0078/0094) prints no absolute place address; nothing to change.

**Tests.** `test_tenant_domain.py` 61 (13 new): the printed place, the face, the mail link, the restart
list, the daily check (waits quietly, activates when DNS fits, never switches an active domain off), the
timer in both scripts, the portal's link, health facts and tile on the domain. Two mutations caught (the
timer switching off; the printed place ignoring the domain). Eighteen files green in the Linux runner,
among them `test_migrate`, `test_tenant`, `test_tenant_face`, `test_access_portal`, `test_notify`,
`test_portal_navigation`.

**Measured on `oaap-test`** (0.1.332 + these changes staged, tenant `vuebung`, domain
`dom0.oaap-demo.duckdns.org`; removed afterwards):

| Asked | Answer |
|---|---|
| `migrate.sh` through `stage.sh` | timer `oaap-domain-check` enabled, next run 04:50 |
| `oaap tenant domain vuebung dom0…` | active; the 14 instances listed with `oaap app restart` |
| `notify_link(vuebung, "/health")` | `https://dom0.oaap-demo.duckdns.org/health` |
| `instance.env` of the chat | `OAAP_INSTANCE_NAMES=http://chat.dom0…,http://chat.vuebung.<node>` (domain first) |
| the chat's sandbox site | `frame-ancestors https://chat.dom0… https://chat.vuebung.<node> …` |
| `systemctl start oaap-domain-check` | exit 0; `checked` and DNS's answer written |
| `/health` on the domain as a tenant administrator (test account) | 200: „Adresse dom0…“, „Eigene Domain dom0… · aktiv“ |

**Not measured:** a real mail (no event was due), an MCP App view rendered in a browser on the domain
(needs an edge route on `oaap-demo`).

## 15. The portal, and hiding an instance under the domain (2026-11-21)

**Jörg, after testing `bec.brandeis.de`:** „Das Zuordnen der Domain aus dem Portal für den server_admin:
am besten in den Mandanteneinstellungen“, and: tenant and instances stay reachable under the node's
names (yes, D3) -- „dann möchte ich, dass bei einer solchen zugeordneten Sub-Domain einzelne Instanzen
‚versteckt' werden können. Also nur über die Knoten-Domain-Auflösung zugänglich sind.“

**Decided while building** (no D-number, each the narrow choice):

- Hiding is the server_admin's, like binding (D1): it changes what a tenant publishes under a name the
  operator bound.
- A hidden instance keeps an own name (RFC-0018) below the domain: that is an explicit choice, and the
  answer says how to remove it.
- The flag stays on the instance when the domain is switched off or removed; it takes effect again
  under the next domain.

**Built** (reference 0.1.334, `oaap.core.tenant` 1.19).

- Registry field `domain_hidden` on an instance; `instance_auto_hosts` and the portal's `auto_host` leave
  the domain name out for it. Behind an edge `*.<domain>` answers 404 for it; directly it has no
  certificate.
- `instance_set_domain_hidden` (CLI `oaap app address <instance> domain-hide|domain-show`), written to
  the tenant's log (`instance.domain`).
- Portal: Mandanten → **Domain** (`/tenant/domain?tenant=<label>`), server_admin only, not for the default
  tenant. It shows the domain with state and DNS's answer, binds a domain, checks, switches off, removes,
  and lists the tenant's instances with their name under the domain and under the node and a button to
  hide or show each.
- Host worker: actions `tenant-domain` and `instance-domain`, accepted from a server_admin only, judged
  from the actor's record. `tenant-domain` runs the CLI's own function and answers with its sentences
  (`_run_captured`), so portal and CLI cannot drift apart.

**Tests.** `test_tenant_domain.py` 78 (17 new): hiding and showing (names, gateway file, portal link, the
log, unchanged twice, refused without a domain, the CLI), the real worker with a server_admin and a
tenant_admin (who is refused for both actions, nothing changes), the CLI's sentences as answers, the
portal page (content; a tenant_admin and the default tenant are sent away). Two mutations caught (the
worker's role check removed; the flag ignored). Fourteen files green in the Linux runner, among them
`test_access_portal`, `test_administer_portal`, `test_care_portal`, `test_tenant_face`.

**Measured on `oaap-test`** (staged, tenant `vuebung`, through the node's real queue watcher
`oaap-deployd.path`; removed afterwards): 5/5 -- the tenant_admin `vuebung.carl` is refused for both
actions; `oaap-admin` binds `dom0.oaap-demo.duckdns.org` (answer: the CLI's sentences) and hides
`vorgaenge`; the portal page shows the domain active and `vorgaenge` hidden. From the edge node:
`vorgaenge.dom0…` 404, `vorgaenge.vuebung.<node>` 303 to the login, `chat.dom0…` 303.

**Not measured:** the page clicked in a browser by a person (rendered inside the portal container with
the gateway's headers).

## 16. Stage 3, in part: a `tenant_admin` asks for a domain (2026-11-21)

**What was left of stage 3** (§10): behind an edge; a `tenant_admin` request for a domain; an optional
redirect of the node's names.

- **Behind an edge** needs nothing new: stage 1 found the node side complete (§12, D8 narrowed), and §15
  measured from the edge node (`chat.<domain>` 303, a hidden instance 404). What D8 still names -- the
  edge command does not check the domain -- stays open: the edge would have to ask the node, a door
  across nodes for a check the node already makes.
- **The redirect** of the node's names stays open, on purpose: D3 keeps them answering because MCP
  clients, OIDC clients and stored recipe addresses use them. A switch is cheap to build and expensive
  to undo for whoever relied on it; it waits until a tenant asks.
- **The request** is built.

**Built** (reference 0.1.339, `oaap.core.tenant` 1.22).

- `tenant_domain_request`: a `tenant_admin` of a tenant without a domain asks for one -- judged by the
  rules of `domain set` (`place.domain_refusal`), refused for another tenant, the default tenant, a
  tenant that has a domain and while one request for a domain is open. DNS is checked at once
  (`domain_dns_check`) and its sentence opens the request's text. It is a request of RFC-0109 §13
  (`values: {domain}`): a case in the operator's inbox, else a message; its state on *Einrichten*.
  The case says how to bind (portal *Mandanten → Domain* or `oaap tenant domain <label> <domain>`),
  not how to release a recipe.
- Portal: on the tenant's health page, for the `tenant_admin` only, *Beim Betreiber anfragen* (domain,
  an optional note) while the tenant has no domain, the requested domain while one is open; the host job
  `domain-request` (action `tenant-recipe`, the actor's own tenant).
- When a domain becomes active (`check`, `set`, the portal, the daily check), the platform answers its
  open requests: done, „Die Domain … ist gebunden und aktiv.“, the case closed with that sentence.

**Tests.** `test_tenant_domain.py` 97 (19 new): five refusals (other tenant, default tenant, a tenant
with a domain, below the node, below another tenant's domain), the request with the domain and the DNS
sentence, the case text naming the binding, a second request refused (also through the portal's job),
the view naming the domain, activation answering the request, the portal's card for the `tenant_admin`
only, the form, the job with the actor's own tenant, a server_admin refused. Thirteen files green in the
Linux runner, among them `test_recipe_request`, `test_tenant_request_page`, `test_tenant_recipe_page`,
`test_recipe_sap_sso`, `test_access_portal`.

**Measured on `oaap-test`** (0.1.339 staged, tenant `vuebung` as its `tenant_admin` through the job the
portal calls, the node's real inbox `vorgaenge`), 9/9: a name below the node refused; the request
became case `V-2026-0024` with „DNS beim Anfragen: passt“; a second one refused; the portal's view names
it; the case's text names `sudo oaap tenant domain vuebung dom0.oaap-demo.duckdns.org` and no recipe;
`oaap tenant domain vuebung dom0…` made it active and the request was done by itself; the case closed
with „Die Domain … ist gebunden und aktiv.“; the domain removed again.

**Not measured:** the card clicked in a browser.

## 17. A website on the domain (2026-11-27)

**The question** (Jörg, 2026-11-27): an instance is the tenant's website and should answer on the
main domain or on `www.<domain>`. Does that work? And instances that answer under the node's names
only, not under the domain, exist already?

**Facts** (read in reference 0.1.388, not measured):

| Place | Today |
|---|---|
| **Own names** | `oaap app address <instance> set|alias-add <host>` (RFC-0009/0018) accepts any valid hostname that is not the node's own name, not below it, not under an edge route and not held by another instance (`check_instance_address`). It does **not** look at tenant domains. |
| **The domain's apex** | `write_external_caddy` writes the tenant's place on `<domain>`, **unless** an instance holds `<domain>` as its own name: then the instance keeps it and the place gets no site. The only trace is a comment in `external.caddy` (`held as an instance's own name; no place site`). This was built in 0.1.332 for `chat.bec.brandeis.de`, a name below the domain; the apex itself was never measured. |
| **`www.<domain>`** | an instance named `www` of the tenant gets it automatically (`<instance>.<domain>`); any instance can take it as an own name. |
| **Cookie** | `place.cookie_scope` widens the session cookie to the domain for **every** host at or below it (D4). An instance site passes `Cookie` on to its app; only sandbox sites remove it. |
| **Hidden instances** | §15: `domain_hidden` keeps an instance under the node's names only. It exists and answers the second question. |

**Findings.**

- **F1 The website works.** `www.<domain>` as an own name of the website instance, `<domain>` as its
  alias (or the other way round), DNS as today (`<domain>` and `*.<domain>` already point to the node).
  A name outside the domain (`www.brandeis.de`) works as any own name does.
- **F2 The place disappears without a word.** If the website holds the apex, the tenant's start page
  is no longer on the domain. Nobody is told: not the CLI that set the name, not the portal's
  *Mandanten → Domain*, not the health page. Mails and tiles that print the domain (§5) keep pointing at
  `https://<domain>/`, which is now the website. The login itself still works there, because `/auth/*`
  is reserved on every instance site and `host_place(<domain>)` names the tenant.
- **F3 An instance of another tenant can take a name under the domain.** `check_instance_address`
  lets the server_admin give an instance of tenant B the name `www.<domain-of-A>`. That breaks §7.2
  ("the domain names exactly one tenant"), and because of the cookie scope the browser of every person
  logged in at A sends A's session cookie to B's app. Only a server_admin can set an own name, so this
  is an operator mistake waiting to happen, not a door for a tenant. It is still a gap, and §7.6's bait
  tests did not cover own names.

**Proposal.**

1. **Own names follow the domain's tenant** (closes F3). A host at or below an active or pending tenant
   domain becomes an own name only of an instance of that tenant: `check_instance_address` refuses it
   otherwise, naming the tenant the domain belongs to. The same rule runs where a domain is bound or
   activated: `domain set` / `check` / the portal refuse a domain while an instance of another tenant
   holds a name under it, and name that instance. The gateway writer leaves out a foreign own name under
   a domain (and says so in the log), so a registry written before the rule cannot serve it.
2. **The website on the apex is a stated choice** (closes F2). Setting the domain itself as an own name
   says what happens: "the tenant's place moves to `<place host>`". The tenant's domain record gains
   `place_host`: `<domain>` by default, else a name below it. While an instance holds the apex the
   place is served on `place_host`, and every printed address (§5) uses it. The portal's
   *Mandanten → Domain* and the health page show where the place is and which instance holds the apex.
3. **`www` is nothing special.** No automatic `www` → apex redirect: whoever wants both names gives the
   website both, as an own name and an alias.
4. **Hiding (§15) stays as it is.** An instance that should answer under the node's names only is
   hidden; an own name below the domain is still allowed for it (decided in §15), now only for an
   instance of the domain's tenant (item 1).

**Decisions** (Jörg, 2026-11-27: „Wie empfohlen“ for D10–D12).

- **D10 Foreign own names under a domain.** *Recommendation:* refused (item 1), also when the domain is
  bound later.
  - Alternative: allowed, with a warning. Keeps every operator choice open, but the cookie of tenant A
    then reaches tenant B's app; the cookie would have to be stripped for that site, a special case in
    the gateway.
- **D11 Where the place goes when the website holds the apex.** *Recommendation:* to `place_host`, a
  name below the domain the operator chooses, proposed as `portal.<domain>`; refused while an instance
  of the tenant is named `portal`.
  - Alternative A: the place stays only on `<label>.<node>` (today's accidental behaviour, now said
    out loud). Nothing to build, but a login on the domain then always runs through the website's
    host, and the start page carries the node's name.
  - Alternative B: the apex is never an own name; the website gets `www.<domain>` only and the apex
    redirects there. Simplest rule, but customers who print `bec.brandeis.de` on their letters land on
    the login instead of the website.
- **D12 Order.** *Recommendation:* item 1 first (a gap, small), item 2 when a tenant really puts its
  website on the apex.

**Tests** (when built, bait in brackets): an own name `www.<domain>` for an instance of the tenant
accepted (for an instance of another tenant: refused, also through the portal's job; binding a domain
under which a foreign instance has a name: refused, naming it; a registry with a foreign own name under
a domain: no site written); the apex as an own name answers with the website, `place_host` with the
place, the login on both; mails, tiles and the health page print `place_host` (no address still points
at the apex for the place).

**Not measured:** nothing of §17. Item 1 and F3 are read from the code; whether the website on the
apex behaves as F2 says needs a measurement on `oaap-test` with `dom0.oaap-demo.duckdns.org`.

## Zusammenfassung auf Deutsch

**Worum es geht:** Heute baut der Knoten jeden öffentlichen Namen aus
seinem eigenen Hostnamen: Der Mandant heißt `bec.oaap.joomp.de`, eine App
`chat.bec.oaap.joomp.de`. Eine eigene Domain gibt es nur je Instanz als
Alias. Für die Startseite und Anmeldung des Mandanten gibt es keinen, und
die Anmeldung trägt auf einer fremden Domain nicht, weil das
Anmelde-Cookie nur für den Knotennamen gilt.

**Vorschlag:** Ein Mandant bekommt **eine eigene Domain**.
- Der Betreiber trägt sie ein (`oaap tenant domain set bec bec.brandeis.de`).
- Sie gilt erst, wenn DNS nachweislich auf den Knoten zeigt: die Domain
  selbst und ein zufälliger Name darunter.
- Dann antwortet `bec.brandeis.de` mit Startseite und Anmeldung des
  Mandanten und `<instanz>.bec.brandeis.de` mit jeder App des Mandanten,
  ohne Handgriff je App.
- Die Domain zeigt genau diesen Mandanten, für alle, auch für
  Betreiber. Fremde Apps, Betreiberseiten und unbekannte Namen darunter
  liefern nichts.
- Das Anmelde-Cookie gilt für die Mandanten-Domain; der Anbieter des
  Mandanten (Keycloak) bekommt die neue Rücksprungadresse dazu.
- Die alten Namen unter dem Knoten antworten weiter, damit nichts bricht.
  Gedruckt wird zuerst die Domain.

**Für bec jetzt schon möglich:** DNS einrichten, `bec.brandeis.de` und
`*.bec.brandeis.de` als A-Eintrag auf die Adresse von oaapx01.

**Entscheidungen D1–D9: am 20.11.2026 von Jörg wie empfohlen entschieden („Wie empfohlen“):**
- D1: Nur der Betreiber bindet eine Domain; der tenant_admin fragt per
  Anfrage.
- D2: Nachweis über DNS (Domain und ein Zufallsname darunter).
- D3: Alte Namen bleiben, die Domain wird zuerst gedruckt.
- D4: Ein Cookie je Mandanten-Domain; wer beide Namen nutzt, meldet sich
  zweimal an.
- D5: Betreiberseiten gibt es auf der Mandanten-Domain nicht.
- D6: Sandbox-Namen der Chat-Ansichten bleiben unter dem Knoten.
- D7: Feste Basisadressen von Apps ändert der Betreiber selbst.
- D8: Knoten hinter einem Edge erst in Stufe 3.
- D9: Eine Domain je Mandant.

**Stufe 0 gemessen (20.11.2026):**
- Auf oaap-test mit `dom0.oaap-demo.duckdns.org` als Domain des Mandanten
  vuebung, ohne den Edge zu ändern.
- Wer nur das Vereinskonto hat, kommt über einen eigenen Namen gar nicht
  hinein: Dort steht die Anmeldung des Knotens ohne Vereins-Knopf, und
  der Start des Anbieters liefert 404.
- Mit einem lokalen Konto geht es, aber das Cookie gilt nur für genau
  diesen einen Namen: jede App eine eigene Anmeldung.
- Namen ohne eigene Seite unter der Domain landen bei der Anmeldung des
  Knotens statt bei „nichts“.
- Daraus für Stufe 1: Cookie je Mandanten-Domain, Anmeldung und Anbieter
  auf der Domain, unbekannte Namen darunter mit 404.

**Stufe 1 gebaut und gemessen (20.11.2026, Referenz 0.1.331):**
- `oaap tenant domain <kürzel> <domain>` bindet die Domain; `check`, `off`, `remove`.
- Die Domain gilt, sobald sie und ein Zufallsname darunter dorthin zeigen, wohin der Name
  des Knotens zeigt. Das geht auch hinter einem Edge; dort sagt der Befehl, welche Route
  der Edge braucht (D8 damit enger als entschieden).
- Ort, Anmeldung mit Vereins-Knopf und alle Apps des Mandanten antworten unter der Domain,
  unbekannte Namen darunter mit 404. Das Cookie gilt für die ganze Domain.
- Der Anbieter kommt auf der Domain zurück; `oaap idp provision` trägt die Adresse in Keycloak ein.
- Gemessen auf oaap-test: 9 von 9, und Keycloak nimmt die neue Adresse nach `provision` an.
- Offen: echter Browsertest mit Zertifikat über eine Edge-Route, eine Anbieter-Anmeldung mit
  einer echten Person, tägliche Nachprüfung, Mails und Hilfe (Stufe 2).

**Live für bec auf oaapx01 (20.11.2026, Referenz 0.1.332):** `bec.brandeis.de` zeigt die
Anmeldung von bec mit „Mit dem BEC-Konto anmelden“, die Apps antworten unter
`<app>.bec.brandeis.de`, Keycloak nimmt die neue Rücksprungadresse an. Unterwegs lehnte das Gateway
einmal ab, weil `chat.bec.brandeis.de` schon eigener Name einer App war; behoben in 0.1.332, ohne
dass jemand etwas bemerkt hat.

**Stufe 2 gebaut und gemessen (21.11.2026, Referenz 0.1.333):**
- Mails, die Adresse auf Anmeldeseite und Portal und der Link „Einrichten“ nennen die Domain.
- Die Gesundheitsseite des Mandanten zeigt Adresse und Domain mit Zustand.
- Eine wartende Domain prüft der Knoten jeden Morgen um 04:50 und schaltet sie frei, sobald DNS
  passt; eine aktive schaltet der Zeitgeber nie ab.
- Beim Aktivieren nennt der Befehl die Apps, die die neuen Namen erst nach einem Neustart kennen.
- Gemessen auf oaap-test; nicht gemessen: eine echte Mail und eine Chat-Ansicht im Browser.

**Zwei Wünsche von Jörg, gebaut und gemessen (21.11.2026, Referenz 0.1.334):**
- Im Portal unter Mandanten → **Domain** ordnet der Server-Admin die Domain zu, prüft, schaltet ab
  und entfernt sie. Der Knoten nimmt das nur vom Server-Admin an.
- Auf derselben Seite lässt sich jede App **unter der Domain verbergen**: Sie antwortet dann nur
  unter dem Namen des Knotens, unter der Domain mit nichts. Auch per CLI:
  `oaap app address <app> domain-hide` / `domain-show`.
- Gemessen auf oaap-test über die echte Warteschlange: 5 von 5; von außen 404 unter der Domain,
  Anmeldung unter dem Knoten.

**Stufen:** 0 auf oaap-test messen, was heute bricht (mit einem zweiten
DuckDNS-Namen); 1 Domain, Namen, Zertifikate, Anmeldung; 2 Chat-Ansichten,
Mails, Hilfe, Rezepte; 3 Edge, Anfrage des Mandanten, Umleitung der
alten Namen.

**Stufe 3, zum Teil (21.11., §16):** Ein tenant_admin fragt auf der Gesundheitsseite eine eigene Domain
beim Betreiber an. Geprüft wird wie beim Binden, das DNS gleich mit. Die Anfrage landet im Posteingang
des Betreibers und schließt sich selbst, sobald die Domain aktiv ist. Auf oaap-test 9/9. Hinter einem
Edge braucht der Knoten nichts Neues. Offen bleiben mit Absicht: die Prüfung im Edge-Befehl und die
Umleitung der Knotennamen auf die Domain (D3, erst wenn ein Mandant sie will).

**Webseite auf der Domain (27.11., §17, nichts gebaut):**
- Jörgs Frage: Kann eine Instanz als Webseite auf `bec.brandeis.de` oder `www.bec.brandeis.de`
  antworten? Ja, heute schon, als eigener Name der Instanz (`oaap app address <instanz> set …`,
  `alias-add …`). Instanzen nur unter dem Knotennamen gibt es auch schon (§15, „verbergen“).
- Lücke 1: Nimmt die Webseite die Domain selbst, verschwindet die Startseite des Mandanten dort,
  ohne dass es jemand erfährt; Mails und Kacheln zeigen weiter auf die Domain.
- Lücke 2: Eine Instanz eines **anderen** Mandanten kann einen Namen unter der Domain bekommen.
  Dann schickt der Browser ihr das Anmelde-Cookie des Mandanten. Setzen kann das nur der
  Server-Admin, es ist also ein Bedienfehler, der möglich ist, kein Weg für Mandanten.
- Vorschlag: Eigene Namen unter einer Mandanten-Domain nur für Instanzen dieses Mandanten (auch
  beim späteren Binden geprüft). Hält die Webseite die Domain selbst, zieht die Startseite auf
  einen Namen darunter um (Vorschlag `portal.<domain>`), und Portal, Mails und Kacheln sagen das.
- Entschieden am 27.11. von Jörg wie empfohlen („Wie empfohlen“): D10 fremde Namen unter der Domain
  werden abgelehnt, D11 die Startseite zieht nach `portal.<domain>`, D12 erst Lücke 2 schließen,
  Umzug der Startseite erst, wenn ein Mandant seine Webseite auf die Domain legt.
- Alles aus dem Code gelesen, nichts gemessen.

# RFC-0115: A Tenant's Own Domain

- **Status:** **Accepted (2026-11-20)** — Jörg: „Wie empfohlen“ for D1–D9.
  Nothing built yet; stage 0 (the measurement) comes first.
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

**Stufen:** 0 auf oaap-test messen, was heute bricht (mit einem zweiten
DuckDNS-Namen); 1 Domain, Namen, Zertifikate, Anmeldung; 2 Chat-Ansichten,
Mails, Hilfe, Rezepte; 3 Edge, Anfrage des Mandanten, Umleitung der
alten Namen.

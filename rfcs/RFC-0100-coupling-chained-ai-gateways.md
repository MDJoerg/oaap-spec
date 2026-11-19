# RFC-0100: Coupling Chained AI Gateways — a Ticket Across Nodes, a Declaration on the Same Node

- **Status:** Draft (2026-11-19). Requirement by Jörg in conversation on
  2026-11-19. Open decisions D1–D9 below, each with a recommendation.
  Nothing built. Fulfils the "own RFC" promised by RFC-0022 D8.
- **Date:** 2026-11-19
- **Authors:** Jörg (the requirement: in multi-tenant systems and OAAP
  landscapes AI gateways will be chained; a simple way to couple the called
  gateway to the calling one by download and upload — a wizard where one
  ticks the current models, downloads a "key" and uploads it in the calling
  node within a certain time; a special path on the same OAAP node, where
  the tenant itself declares which app instances are visible across tenant
  borders and routes/destinations follow from that), Claude (reading of
  `oaap.ai.gateway`, design)
- **Depends on:** `oaap.ai.gateway` 0.5.3 (§2 keys, §3 aliases, §4
  suppliers and chains, §5 each gateway keeps its own books, §7 the light —
  "a chain may only ever get more dangerous"), RFC-0022 (tenant as boundary;
  D8 chained gateway; "across tenants, only what someone declared"; §6
  audit), RFC-0033 (destinations), RFC-0085 stage 3 (coupling FleetView with
  a one-time key — the same pattern), RFC-0050 (`visible_to` in the
  catalog)
- **Not part of this RFC:** chaining MCP gateways (same pattern, named in
  §6, own section later); billing (RFC-0022: measured, not invoiced)

## Summary

The spec already treats another gateway as an ordinary supplier: an
OpenAI-compatible endpoint plus a credential, with the light inherited and
never improved (§4, §7). What is missing is a **safe, simple way to set
the link up**. Today an operator issues a key on the called gateway, copies
it by hand into a supplier record on the calling gateway, types the address
and the aliases, and sets the light — five chances to get it wrong, and a
secret travelling through clipboards and chats.

This RFC adds two ways:

- **A — coupling ticket (any two nodes).** On the **called** gateway a
  wizard: tick the aliases to offer, name the consumer, download a ticket.
  The ticket holds the address, the aliases with their lights and a
  **one-time code** valid for a short time — **not** the key. On the
  **calling** gateway: upload the ticket; it redeems the code at the called
  gateway, receives the key directly, seals it in its vault and creates the
  supplier with its aliases. The file is worthless afterwards.
- **B — declaration (same node).** The tenant that owns a gateway
  instance declares it visible to named tenants of the same node (or of the
  same account). The platform creates the destination in each consuming
  tenant; the consuming gateway offers it as a supplier with one click. A
  key per consumer still exists, so metering and revocation work as in A.

## 1. Facts (read 2026-11-19)

- `oaap.ai.gateway` §4: "a gateway has an upstream side and a downstream
  side, and an upstream may be another gateway"; a chain proxies, every
  layer meters (§5).
- §7: upstream light is read from the called gateway and may not be
  improved; downstream `/v1/models` reports the worst reachable light.
- §2: the API key is the identity of a consumer; keys can name aliases and
  have a light ceiling.
- The reference AI gateway reaches outside the tenant only through
  destinations of the platform (`OAAP_DESTINATION_<NAME>_URL`).
- RFC-0085 stage 3 coupled FleetView instances with a one-time key that
  becomes worthless after use — measured on the fleet.

## 2. Way A — the coupling ticket

### 2.1 On the called gateway

Wizard on the operator's page, "Couple a consumer":

1. Name the consumer (free text, e.g. "Tenant bec on oaapx01").
2. Tick aliases (current list from §3, each shown with its light).
3. Optional: light ceiling, request/volume limits (as for any key).
4. Validity of the ticket: default 30 minutes (D2).
5. Download `<consumer>.oaap-coupling.json`.

The gateway creates the key **in state `pending`**, bound to the ticket's
code. Nothing can be called with it yet.

### 2.2 The ticket

```json
{
  "kind": "oaap.ai.gateway.coupling",
  "v": 1,
  "issuer": {"title": "KI-Gateway oaap-web", "url": "https://ai.oaap-web.oaap.joomp.de"},
  "aliases": [{"name": "standard", "light": "green"}, {"name": "code", "light": "yellow"}],
  "code": "<one-time code, 128 bit>",
  "expires": "2026-11-19T15:30:00Z",
  "fingerprint": "<TLS fingerprint of the issuer, for pinning>"
}
```

No key, no upstream credential, no supplier names of the called gateway.

### 2.3 On the calling gateway

Operator's page, "Add supplier from ticket":

1. Upload; the gateway shows issuer, aliases, lights, expiry — nothing is
   stored yet.
2. Confirm. The gateway calls `POST <issuer>/v1/coupling/redeem` with the
   code (TLS, pinned to the fingerprint), receives the key once, seals it.
3. It creates the supplier (address, credential from the vault, light =
   the reported light — never greener, §7) and proposes local aliases with
   the same names; the operator can rename.
4. The called gateway sets the key `active`, records who redeemed it
   (address, time) and shows the consumer as coupled.

A second redemption, an expired code or a wrong fingerprint is refused
with a sentence. The calling gateway needs a route to the called one
(destination or public name); without it the wizard says so before upload.

### 2.4 Afterwards

- **Model list changes** on the called side: the calling gateway's probe
  (§4.2) already reads `/v1/models`; new aliases the key may reach are
  offered, removed ones marked.
- **Revocation:** one click on the called gateway; the calling gateway's
  next request gets 401 and the supplier is shown as "revoked by the
  supplier".
- **Renewal:** a new ticket for the same consumer replaces the key
  (D6).

## 3. Way B — declaration on the same node

### 3.1 The declaration

On the tenant's page (`tenant_admin` of the **offering** tenant), per app
instance:

```yaml
exposed_to:
  - tenant: bec           # or account: <id>
    routes: [/v1/]        # what the consumer may reach
```

Same idea as `visible_to` in the catalog: absent = only the own tenant.
RFC-0022's rule holds literally: **across tenants, only what someone
declared** — and the declaration is named, audited and visible in both
tenants.

### 3.2 What the platform does

- Creates in each consuming tenant a destination `<offering-tenant>-<instance>`
  that routes inside the node (no public detour), audited in both tenants.
- The consuming tenant's `tenant_admin` sees "offered by tenant X" and
  accepts it (D7) — nothing appears in a tenant without its consent.
- The AI gateway of the consuming tenant offers "Add supplier from a
  declared gateway": it runs the same redemption as in A, but the code is
  exchanged by the platform between the two instances, without a file.

### 3.3 Generality

The declaration is a platform feature for **any app instance**, not only AI
gateways (MCP gateway, help, a shared ticket system). Each app decides what
it does with a consumer from another tenant; for the AI gateway that is a
key per consumer.

## 4. Security requirements

1. The ticket never contains a key or an upstream credential.
2. The code is single use, short lived, and bound to the pending key.
3. Redemption is pinned to the issuer's TLS fingerprint.
4. The light of a coupled supplier is the issuer's reported light or worse
   (§7 unchanged).
5. Every step (issue, redeem, revoke, declare, accept) is audited on both
   sides.
6. A declaration across tenants requires consent of the consuming tenant.
7. A closed tenant (RFC-0068) can consume only suppliers whose light is
   allowed for it; a declaration does not lift that.

## 5. Decisions

- **D1 Ticket carries a code, not the key.** *Recommendation:* yes — the
  file may travel through mail and chats; the key never does.
- **D2 Validity.** *Recommendation:* 30 minutes, adjustable 5 minutes to
  24 hours.
- **D3 File format.** *Recommendation:* JSON as above, kind
  `oaap.ai.gateway.coupling` v1.
- **D4 Redemption route.** *Recommendation:* `POST /v1/coupling/redeem` on
  the called gateway, reachable without a key, rate-limited.
- **D5 Aliases on the calling side.** *Recommendation:* proposed with the
  same names, renamable; failover groups (§3) are built by the operator,
  not by the ticket.
- **D6 Renewal.** *Recommendation:* a new ticket for an existing consumer
  replaces its key after redemption; the old key stays valid until then.
- **D7 Consent on the same node.** *Recommendation:* the consuming
  `tenant_admin` accepts; `server_admin` may declare on behalf of both
  (operator setup), audited.
- **D8 Account scope.** *Recommendation:* `account: <id>` allowed only
  inside one node in stage 2; cross-node account declarations later.
- **D9 MCP gateway.** *Recommendation:* the same ticket pattern for
  chained MCP gateways in a later section, kind `oaap.ai.mcp-gateway.coupling`.

## 6. Stages and tests

| stage | content | done when |
|---|---|---|
| 1 | way A: wizard, ticket, redemption, supplier from ticket, revocation | the ticket file contains no key (bait: search the file for the key value); a second redemption is refused; a red alias arrives red even if the caller sets green; revoke → next request 401 |
| 2 | way B: `exposed_to` on the tenant, destination inside the node, consent, redemption without file | without consent nothing appears in the consuming tenant; after revoking the declaration the destination is gone and audited on both sides |
| 3 | MCP gateway, same pattern | — |

Spec changes: `oaap.ai.gateway` (§4.3 coupling, §9 tests), `oaap.core.tenant`
(`exposed_to`), `oaap.net.destinations` (destinations from declarations).

## Zusammenfassung auf Deutsch

Die Spec behandelt ein anderes Gateway schon heute als gewöhnliche
Bezugsquelle, und die Ampel wird in der Kette nie grüner (§4, §7). Es fehlt
der **einfache und sichere Weg, die Kopplung einzurichten**. Bisher kopiert
man Schlüssel, Adresse und Aliasse von Hand.

- **Weg A, Kopplungs-Ticket (beliebige Knoten):** Im **aufgerufenen**
  Gateway Aliasse anklicken, den Verbraucher benennen und ein Ticket
  herunterladen. Das Ticket enthält Adresse, Aliasse mit Ampelfarbe und
  einen **Einmal-Code** mit kurzer Gültigkeit (Vorschlag 30 Minuten),
  **nicht** den Schlüssel. Im **aufrufenden** Gateway hochladen: Es löst
  den Code beim aufgerufenen Gateway ein, bekommt den Schlüssel direkt,
  legt ihn im Tresor ab und legt die Bezugsquelle an. Danach ist die Datei
  wertlos. Widerruf geht mit einem Klick beim aufgerufenen Gateway. Das
  Muster kennen wir aus der FleetView-Kopplung (RFC-0085).
- **Weg B, Erklärung (gleicher Knoten):** Der anbietende Mandant erklärt
  an seiner Instanz `exposed_to: [tenant: bec]`. Die Plattform legt im
  verbrauchenden Mandanten eine Destination innerhalb des Knotens an,
  sobald dessen `tenant_admin` zustimmt. Der Code wird ohne Datei
  getauscht, aber auch hier gibt es einen Schlüssel je Verbraucher, damit
  Verbrauch und Widerruf funktionieren. Die Erklärung gilt für jede
  App-Instanz, nicht nur fürs KI-Gateway. Das erfüllt RFC-0022 („über
  Mandanten hinweg nur, was jemand erklärt hat“) wörtlich.

Das RFC löst das in RFC-0022 D8 versprochene eigene RFC ein. Offen sind
D1–D9 mit Empfehlungen. Dasselbe Muster für MCP-Gateways folgt später.

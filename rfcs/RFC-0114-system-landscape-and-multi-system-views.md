# RFC-0114: System Landscape and Multi-System Views in the MCP Gateway

- **Status:** **Accepted (2026-11-20)** — Jörg: "Wie empfohlen" for
  D1–D10. Nothing built, nothing measured for this RFC; stage 1 on
  Jörg's word. The facts in §1 were read the same day
  in `oaap.ai.mcp-gateway` 0.29.0 and `mcp-gateway` 0.31.0.
- **Date:** 2026-11-20
- **Authors:** Jörg (the need, 2026-11-20, while setting up SAP SSO for a
  second SAP system in `bec`: "ich würde gern im MCP Gateway meine
  Systemlandschaft als Liste erfassen, weil ich diese auch später im Chat
  auslesen muss … Titel, Rolle (z.B. Produktion), aktiv Flag usw. Dann
  würde ich der Sicht nur diese Systeme zuordnen und einen MCP Server –
  immer den gleichen – zuweisen"; the process: a multi-system view, a
  first system as the reference, shaped by deselecting tools, resources
  and prompts, then further systems with their MCP servers), Claude
  (facts, design)
- **Depends on:** RFC-0065 (views, bundles, default deny, pinned
  descriptions), RFC-0066 (principal propagation, `sap_user_<x>`),
  RFC-0095 (`/me`, procedure U), RFC-0097 (assistants in the gateway),
  RFC-0109 (the recipe "SAP SSO einrichten", one destination per system).
- **Related:** RFC-0031 (digital twin) and idea I-51 (a self-growing
  CMDB) -- where a landscape might live one day (D3); RFC-0111
  (credentials in one place).
- **Changes:** `oaap.ai.mcp-gateway` (new objects *target system* and
  *multi-system view*, the routing argument, a read for the chat);
  nothing in an existing view.

## Summary

The same MCP service often runs on several systems: an SAP MCP service
on development, quality and production, or on two customers' systems.
Today a view binds each entry to ONE server. For two systems the
operator puts both servers into one view and every second tool gets a
prefixed name (`sap-abap2025_find_users`); for five systems the view has
five copies of every tool, and the chat must guess from names which
system is which.

This RFC adds two things to the MCP gateway:

1. a **system landscape**: a list of **target systems** with title,
   role (development, quality, production, …), an active flag, a kind
   and, per system, the MCP server(s) that reach it;
2. a **multi-system view**: ONE selection of tools, resources and prompts,
   shaped once on a **reference system**, applied to every system the
   view names. The chat sees each tool once and chooses the system with
   an argument (D2, recommended), and it can **read the landscape** of the
   view (title, role, active -- never an address or a credential).

## 1. Facts (2026-11-20)

- A view (`oaap.ai.mcp-gateway` §5) holds entries; each entry is one
  catalog entry of ONE server under a name of the view. Entries of
  several servers form a bundle; the client never learns which server
  answers which call.
- Names: a tool's default name in the view is the server's name, else
  `<server>_<name>`; a taken name is refused, never resolved silently
  (§5.1). Changing the server of an entry is not possible (§5.1).
- Copying a view (§5.4) copies its entries -- bound to the SAME servers.
  There is no "the same selection on another server".
- An assistant names exactly ONE view (`oaap.ai.assistants` §2).
- The recipe `sap-sso` (RFC-0109 §12) makes one destination, one server,
  one view, one profile and one assistant per SAP system.
- In `bec` (2026-11-20): server `sap-abap2023-bc-support` through
  destination `sap-a4h`, and a second system `abap2025` set up by the
  recipe through destination `sap-abap2025`; both run the same MCP
  service `zmcp2/bc/access-support` (25 tools on the first).
- Nothing in the gateway knows what a system IS: a server has a name, an
  address, a procedure and a light; "production" exists nowhere.

## 2. Words

- **Target system** (*Zielsystem*): anything a tool call reaches through
  an MCP server -- an SAP system, a Jira site, a wiki. Not an OAAP node,
  not an instance.
- **System landscape** (*Systemlandschaft*): the list of target systems of
  one MCP gateway (one tenant). "Landschaft" alone already names the
  fleet of nodes (FleetView) and a tenant's set of instances
  ("Mandantenlandschaft"); the compound keeps them apart (D1).
- **Multi-system view** (*Multi-System-Sicht*): a view whose entries are
  defined once and served for several target systems.

## 3. The target system

| Field | Meaning |
|---|---|
| `id` | `[a-z0-9-]`, stable, e.g. `a4h`, `abap2025` |
| `title` | shown to people and to the chat, e.g. "A4H Entwicklung" |
| `role` | one of a fixed list (D4): `development`, `quality`, `production`, `sandbox`, `training`, `other` |
| `active` | an inactive system is listed as such and never routed to |
| `kind` | free word: `sap`, `jira`, `wiki`, … (for the chat and filters) |
| `facts` | optional, kind-specific and **never secret**: for SAP `sid`, `client` |
| `servers` | the gateway's servers that reach this system (usually one) |
| `light` | the system's light; by default from its role (D5) |
| `description` | free text for the chat |

- The landscape is the gateway's, per tenant, edited on its operator page
  and through its setup door (a new setup kind `system`, so a recipe can
  add a system -- `sap-sso` would then add one per run).
- A server may belong to at most one system (a server reaches one place).
- Removing a system that a view names is refused with the views named.

## 4. The multi-system view

### 4.1 Shaping on a reference

1. The operator creates a multi-system view and names its **reference
   system**.
2. They shape it from the reference system's servers exactly as a view
   today: choose entries, names, descriptions, effect classes, fixed
   arguments and bounds (§5.1–5.3). The result is the view's **template**:
   per entry the server-side name, the kind and the approved snapshot.
3. They **add further systems**. For each, the gateway lays the template
   over that system's server catalog and shows, per entry:
   - *gleich* -- same name, same schema and description as the reference
     (fingerprint equal): served without a new approval;
   - *abweichend* -- same name, different schema or description: shown
     side by side, needs its own approval, else not served for that system;
   - *fehlt* -- the system's server does not offer it: the entry is not
     available for that system, and says so.
   Nothing is taken over silently (the RFC-0065 default deny stays).

### 4.2 How the chat chooses the system (D2)

**Recommended (B): one tool, one argument.** Each entry appears ONCE.
The gateway adds a required argument `system` to the listed schema of
every tool (an `enum` of the **active** systems for which the entry is
*gleich* or approved), takes it out before forwarding, and sends the call
to that system's server. Resources and prompts get the system as a URI
prefix or argument in the same way (D6).

Alternative (A): one entry per system, named `<name>@<system>`. Simpler
to build, but n systems multiply the tool list by n, and an inactive
system changes the names the chat already knows.

### 4.3 Reading the landscape

The view offers a tool (and a resource) of the gateway itself, e.g.
`systeme` / `oaap://landscape`: the systems of THIS view with `id`,
`title`, `role`, `kind`, `active`, `light`, `description` and, per
system, which entries are available. Never an address, a destination, a
credential. An assistant's instructions can tell the model to ask "in
which system?" or to prefer a role.

### 4.4 Lights and refusals

- A call's light is the target system's light (D5): with a production
  system yellow or red, a conversation on green can still use the
  development systems of the same view.
- A call naming an inactive or unknown system, or a system for which the
  entry is *fehlt* or not approved, is refused with a sentence before
  anything goes out.
- The usage row records the target system (new column), `/me` and the
  report show it.

## 5. Identity per system

- Procedure P (RFC-0066): each SAP system has its own destination with
  its own pinned certificate and CERTRULE -- exactly what the recipe
  makes per run. The person's SAP user may differ per system: the
  destination names its claim (`sap_user` or `sap_user_<x>`, already
  supported); the system record can say which (D7).
- Procedure U (RFC-0095): a personal credential is per server, so per
  system already.
- The landscape never holds a credential (RFC-0111 is where they live).

## 6. Security requirements

- S1: The landscape read (§4.3) carries no address, destination, user or
  credential; tested with a system whose server has a credential set.
- S2: A call is routed only to a server of an **active** system of THIS
  view, for an entry that is *gleich* or approved for that system; the
  `system` argument is checked like a fixed argument's bound -- a value
  outside the enum never reaches a server.
- S3: An approval stays per server: a template never approves an entry on
  a server whose snapshot differs.
- S4: The client still never learns which server answered; it learns the
  system it chose.
- S5: A system's light is never looser than the light of any of its
  servers.

## 7. Decisions (Jörg, 2026-11-20: all as recommended)

- **D1 — Words.** Recommended: *Zielsystem* / *Systemlandschaft* in
  German, *target system* / *system landscape* in English.
  Alternatives: "System", "Landschaft".
- **D2 — How the chat chooses.** Recommended: (B) one tool with a
  `system` argument. Alternative (A): one tool per system.
- **D3 — Where the landscape lives.** Recommended: in the MCP gateway now,
  with a read door so it can move later (to the twin, RFC-0031, or a
  CMDB, I-51). Alternative: a platform-wide landscape per tenant now.
- **D4 — Roles.** Recommended: a fixed list (`development`, `quality`,
  `production`, `sandbox`, `training`, `other`) -- assistants and lights
  need words they know. Alternative: free text.
- **D5 — Light per system.** Recommended: from the role by default
  (`production` → yellow, else as the server), changeable by the
  operator, never looser than a server (S5).
- **D6 — Resources and prompts.** Recommended: in stage 1 tools only;
  resources and prompts of a multi-system view stay per server (one entry
  per system). Stage 2: the system as a URI prefix.
- **D7 — A person's user per system.** Recommended: the destination's
  claim as today; the system record only shows it. Alternative: a field
  per system.
- **D8 — Drift.** When a server later changes a tool that was *gleich*,
  recommended: that entry stops for that system until approved again (as
  the pinned description rule already does for a single server).
- **D9 — Existing views.** Recommended: unchanged; a multi-system view is
  a new kind beside them; a "convert" assistant later.
- **D10 — Assistants.** Recommended: unchanged (one view); a multi-system
  view is that one view.

## 8. Stages and tests

- **Stage 1** -- the landscape (§3, operator page, setup kind `system`,
  the read §4.3) and the multi-system view for **tools** with routing (B),
  lights per system, usage column. Test: two systems with the same
  25 tools, one tool with a changed schema on the second -- *abweichend*,
  not served there until approved; the enum lists only active systems;
  deactivating a system removes it from the enum at once; a call with a
  forged `system` is refused before anything goes out; the read carries
  no address. Measured in `bec` with `a4h` and `abap2025` (Jörg's word).
- **Stage 2** -- resources and prompts (D6), the recipe `sap-sso` adds its
  system to the landscape, a "convert" from a view with prefixed names.

## 9. Out of scope

- Discovering systems automatically (that is RFC-0113's question for MCP
  sources, not for target systems).
- A landscape across tenants or nodes.
- Transport routes between systems (SAP TMS) or any write across systems.

## Deutsche Zusammenfassung

Derselbe MCP-Dienst läuft oft auf mehreren Systemen (SAP Entwicklung,
Qualität, Produktion). Heute bindet eine Sicht jedes Werkzeug an genau
einen Server; bei mehreren Systemen gibt es umbenannte Kopien jedes
Werkzeugs, und der Chat muss aus Namen raten.

**Vorschlag:**

- **Systemlandschaft im MCP-Gateway:** eine Liste von **Zielsystemen** mit
  Titel, Rolle (Entwicklung, Qualität, Produktion …), aktiv, Art (SAP,
  Jira …), bei SAP SID und Mandant, dem MCP-Server dahinter und einer
  Ampel (Produktion standardmäßig strenger).
- **Multi-System-Sicht:** Auswahl der Werkzeuge **einmal** am
  Referenzsystem ausprägen; weitere Systeme zuordnen – das Gateway legt
  dieselbe Auswahl darüber und zeigt je Eintrag *gleich*, *abweichend*
  (braucht eigene Freigabe) oder *fehlt*. Nichts wird still übernommen.
- **Im Chat:** jedes Werkzeug nur einmal, mit einem Argument `system`
  (nur aktive Systeme); das Gateway leitet weiter. Der Chat kann die
  Landschaft der Sicht lesen (Titel, Rolle, aktiv) – nie Adresse oder
  Zugang.
- **SSO:** je System eigene Destination und eigener Fingerabdruck (wie das
  Rezept es anlegt); der SAP-Benutzer kann je System verschieden sein.

**Entschieden (Jörg, 20.11.: „Wie empfohlen“):** D1 die Wörter (Empfehlung *Zielsystem* /
*Systemlandschaft*), D2 Systemwahl über ein Argument (Empfehlung) oder je
System ein Werkzeug, D3 wo die Liste lebt (Empfehlung: erst im Gateway),
D4 feste Rollen, D5 Ampel je System aus der Rolle, D6 erst nur Werkzeuge,
D7 SAP-Benutzer je System über die Destination, D8 Abweichung später →
Eintrag pausiert bis zur Freigabe, D9 bestehende Sichten unverändert,
D10 Assistenten unverändert.

**Stufe 1:** Landschaft, Multi-System-Sicht für Werkzeuge mit Systemwahl,
Ampel je System, Protokoll je System; gemessen in bec mit a4h und
abap2025.

# RFC-0111: Credentials in One Place — What a Person and a Tenant Hold for Other Systems

- **Status:** **Draft (2026-11-20)** — D1–D12 open. Nothing built, nothing
  measured for this RFC.
- **Date:** 2026-11-20
- **Authors:** Jörg (the need, 2026-11-20: "we need a platform-wide way to
  keep secrets. A user maintains SAP user/password, API tokens and so on
  for themselves and can use them in other apps too. If something changes,
  exactly one place to change. Admins can manage technical secrets here as
  well."), Claude (design)
- **Depends on:** RFC-0033 (destinations: the proxy that sets a credential
  an app never sees), RFC-0066 (the platform's assertion of a person, bound
  to the calling instance), RFC-0040 (the person's UUID), RFC-0095 (the MCP
  gateway's personal credentials, procedure U — the first, app-local form of
  this idea), RFC-0080 (notifications), RFC-0068 (the closed tenant)
- **First consumer:** RFC-0112 (stdio MCP servers as an app)
- **Not part of this RFC:**
  - **OAuth on behalf of a person** (authorization-code flow, refresh
    tokens the platform renews) — a different mechanism with its own
    consent screens; a later RFC. This RFC keeps values a person can type.
  - **Secrets of the platform itself** (identity-provider secrets, the CA
    of principal propagation, instance keys) — they stay where
    `oaap.core.tenant` and RFC-0062 put them.
  - **Single sign-on.** Where a system can trust the tenant's identity
    provider or the tenant's CA (procedures X and P), that is the better
    way and no secret is stored at all. This RFC is for the systems that
    cannot.

## Summary

Today a secret for another system lives where it is used: in a
destination (set by `server_admin`), in a server record of the MCP gateway,
in the gateway's vault per person (procedure U), in an instance's
configuration, in a `.mcp.json` in someone's home. A password that changes
has to be changed in each of them, and nobody can say where it is.

This RFC gives a tenant **one place**:

1. A **slot** names a credential a tenant uses: `sap-a4h`, `github`,
   `jira`. A slot is either **personal** (every person stores their own
   value) or **technical** (one value, stored by an administrator).
2. A person fills their slots on **one page** ("Meine Zugangsdaten"). A
   value is written, never shown again, replaced or deleted there — and
   nowhere else.
3. An app never asks a person for such a value. It is **granted a slot**
   and uses it in one of two ways: the platform **injects** it into the
   app's call to a destination (the app never sees it), or — a separate,
   stronger grant — the app **receives** it for one person at a time.

The rule that shapes the rest: **injected is the normal case, received is
the exception**, because an app that receives a value can send it
anywhere.

## 1. Facts (read from the specs and the code, 2026-11-20)

| # | Fact |
|---|---|
| F1 | A destination's secret is stored on the host, root only, mounted into no container; set by `server_admin`; **not encrypted at rest** and **not in the backup** (`oaap.net.destinations` §2.5). |
| F2 | The MCP gateway keeps server credentials and, since 0.16, **a credential per person and server** in its own vault (`gwcore/vault.py`, key `MCPGW_MASTER_KEY`), entered on `/me`, write only (RFC-0095 stage 2). Another app cannot use them. |
| F3 | The platform can tell an app who the person is, signed and bound to the calling instance (`X-OAAP-User-Assertion`, `oaap.core.identity` 2.11); the destination proxy already checks it for principal propagation (`oaap.net.destinations` §2.7). |
| F4 | The AI gateway keeps provider keys in its own vault of the same kind. |
| F5 | The webtop workplace expects `SAP_USER`/`SAP_PASSWORD` typed into `.mcp.json` in the person's home (`apps/webtop/projekte/abap-exercises`). |

## 2. The objects

### 2.1 Slot

A slot belongs to **one tenant**.

| Field | Meaning |
|---|---|
| `name` | short name, unique in the tenant (`sap-a4h`) |
| `scope` | `personal` or `technical` |
| `shape` | `token` (one value), `basic` (user and password) or `fields` (a named list, at most 8, each marked secret or not — e.g. `user`, `password`, `client`) |
| `hint`, `link` | one sentence and a link for the person: where to get the value, which rights it needs |
| `targets` | optional: the destinations this slot may be injected into; empty = none (receive only) |
| `expires_hint` | optional: whether the page asks the person for an end date |

A slot is created by the `tenant_admin` of the tenant (D2), by hand or
from a **template** ("SAP user and password", "GitHub token", "Jira
token") that fills shape, hint and link. An app's manifest may *name* the
slots it would like (`credentials:`), which the setup recipes (RFC-0109)
turn into a proposal; a manifest never creates one.

### 2.2 Value

- A **personal** value belongs to (slot, person). Only that person writes
  it. Nobody reads it back — not the person, not an administrator.
- A **technical** value belongs to the slot. A `tenant_admin` writes it
  (D2); nobody reads it back.
- A value carries: stored when, by whom, optionally "valid until", last
  used when and by which instance, and a **version** that counts up at
  every change. None of these is secret.

### 2.3 Grant

A grant connects **one instance** with **one slot** and names the use:

| Use | What the instance gets | Who grants |
|---|---|---|
| `inject` | nothing. A destination bound to the instance carries `auth: credential:<slot>`; the proxy sets the value on the way out (§3.1). | `tenant_admin` |
| `receive` | the value, for one person per call (§3.2). | `tenant_admin`, as a **separate grant with a warning**, shown on the instance's page and on the slot's page (as with `--propagate`, RFC-0066 D3) |

Without a grant an instance learns nothing about a slot, not even that it
exists.

## 3. Using a value

### 3.1 Injected (the normal case)

A destination may name a slot instead of holding its own secret:
`auth: credential:<slot>`. For a technical slot the proxy sets the slot's
value. For a personal slot the app copies the person's assertion onto its
call, exactly as for principal propagation; the proxy checks it (signature,
lifetime, audience = the calling instance) and sets **that person's**
value. No value: `403` with a sentence that names the page (§4), never
another person's value and never a technical fallback.

The shapes map as destinations already do: `token` → `bearer` or a named
header, `basic` → `Authorization: Basic`. `fields` cannot be injected.

### 3.2 Received (the exception)

A door on the instance's **own site**, like the other platform doors:

```
GET /platform/credentials/<slot>
Authorization: Bearer <instance key>
X-OAAP-User-Assertion: <assertion>        (personal slots only)
```

Answer: the fields, the version, `Cache-Control: no-store`. The platform
checks the instance's key, the grant with use `receive`, and for a
personal slot the assertion (audience = this instance). Every answer is
one line in the tenant's audit log: instance, slot, person as UUID, time —
never the value.

What an app that receives MUST do (declared in the manifest, checked in
review, not enforceable by the platform):

- keep the value in memory only — no file, no database, no log, no
  environment of a long-lived process shared between persons;
- fetch it again rather than keep it beyond the work it was fetched for;
- never pass it to another instance.

### 3.3 Ready or not (both uses)

```
GET  /platform/credentials/_readiness?slots=a,b     → per slot: ready | needs_value | rejected | expired, version, hint, link, page
POST /platform/credentials/<slot>/rejected          → "the target refused this value" (with the assertion for a personal slot)
```

`_readiness` never returns a value and needs only a grant of either use.
`rejected` lets the one page show "the system refused your value — renew
it"; the next stored value clears it. The MCP gateway's readiness
(RFC-0095 stage 3) and the chat's "check setup" read from here.

## 4. The one place

**For the person — "Meine Zugangsdaten" in the portal**, in the context of
a tenant: every personal slot of that tenant that is granted to at least
one instance the person can see. Per slot: the hint, state (missing /
stored on … / rejected / expires on …), last used when and by which app,
*which apps use it*, and three actions: store, replace, delete. A value
field is always empty when the page opens.

**For the `tenant_admin` — "Zugangsdaten" in the tenant's administration:**
slots, grants per instance, technical values (write only). For a personal
slot: **how many** persons have stored a value, never which value; an
administrator may **delete** one person's value (someone left, a leak),
which is audited and tells the person (RFC-0080).

**Notifications:** a value that expires in 14 days, a value a target
refused, a value an administrator deleted — to the person. A technical
value that expires or was refused — to the tenant's administrators.

## 5. Where the values live

- In a store of the platform on the node, per tenant, **encrypted** with a
  key of the node that lies in a different root-only directory than the
  data (D5). Unlike a destination secret (F1) these are many values of
  many persons; encrypted, the data can go into the backup while the key
  does not (D6).
- Read only by the two services that hand values out: the destination
  proxy (inject) and the door (receive).
- Never in an instance's environment written by the platform, never in a
  URL, a command-line argument, a log line or a notification.
- Honest limit: whoever is root on the node can read the key and the
  data. The promise is about the platform's interfaces and its backups,
  not about the machine's owner.

## 6. What happens to today's places

| Today | With this RFC |
|---|---|
| Destination secret (F1) | stays. From stage 4 a destination may name a technical slot instead, and then the tenant's administrator changes it in one place. |
| MCP gateway, procedure U (F2) | stage 3: a `personal` server names a slot; the gateway asks the platform instead of its vault. Existing values are moved once (the gateway can decrypt its own vault), then removed there. `/me` links to the one page. |
| MCP gateway and AI gateway server/provider keys (F2, F4) | stay in their vaults until stage 4; then technical slots with `receive`. |
| `.mcp.json` in the webtop home (F5) | RFC-0112: the server runs behind the gateway and takes the value from the slot. |

## 7. Security requirements (proposed)

1. A value is never returned to a browser, a CLI or an administrator.
2. A personal value is used only with that person's valid assertion for
   the calling instance. No assertion, no value — never a technical
   substitute.
3. `inject` sends a value only to destinations the slot lists.
4. `receive` is a grant of its own; every hand-out is audited.
5. Slots, grants and audit lines never cross tenants.
6. Deleting a person from the tenant deletes their values in it (D8).
7. A restore without the key yields no value; the page then says
   "missing", and nothing is called with an empty credential.
8. Accepted input for injectable shapes is what a header can carry
   without interpretation (`oaap.net.destinations` §2.5); a value outside
   that set is refused, never escaped.

## 8. Stages

| Stage | What | Proof |
|---|---|---|
| **1** | Store, slots, personal and technical values, both pages, the `receive` door, readiness and `rejected`, notifications; spec `oaap.core.credentials` 0.1 | two persons store a value for one slot; an instance with the grant gets each person's own value with their assertion, a second instance without the grant gets 403; nothing in backup, logs, environment |
| **2** | `inject`: destinations with `auth: credential:<slot>`, personal and technical | an app calls a paper server through the destination as two persons; the server sees two credentials, the app none |
| **3** | The MCP gateway's procedure U on slots; values moved once | a person's token stored on the one page works in the chat and in Claude Code; changed once, both follow |
| **4** | Destinations and the gateways' own secrets may name technical slots | one change by the `tenant_admin` reaches every user of the slot |

## 9. Decisions

- **D1 — Where it lives:** a platform capability (`oaap.core.credentials`),
  or an app? *Recommendation: platform.* An app could not make the
  destination proxy inject, and "every other app trusts this app with
  everyone's passwords" is the wrong shape.
- **D2 — Who creates slots and sets technical values:** `tenant_admin` in
  their tenant, or only `server_admin`? *Recommendation: `tenant_admin`.*
  The tenant knows its systems; a destination that carries a slot still
  needs its target approved as today.
- **D3 — Two uses, `inject` and `receive`:** *Recommendation: both, with
  `receive` as a separate grant.* Without `receive`, a stdio server that
  needs `SAP_PASSWORD` in its environment cannot work (RFC-0112).
- **D4 — Shapes:** `token`, `basic`, `fields`. *Recommendation: yes;*
  `fields` only for `receive`.
- **D5 — Encrypted at rest with a node key:** *Recommendation: yes*, key
  apart from the data.
- **D6 — In the backup:** the encrypted values yes, the key no?
  *Recommendation: yes.* Otherwise every restore makes every person type
  everything again. The key is saved the way the node's other keys are.
- **D7 — The person's page:** in the portal, per tenant? *Recommendation:
  yes* — it is the one page every app links to.
- **D8 — A person leaves the tenant:** their values there are deleted at
  once. *Recommendation: yes.*
- **D9 — An administrator may delete a person's value, never read it:**
  *Recommendation: yes*, with a notification to the person.
- **D10 — "Valid until" and reminders:** optional per slot.
  *Recommendation: yes, optional.*
- **D11 — Technical values without a person from an agent or a schedule:**
  an instance with a grant may use a *technical* slot without an
  assertion; a *personal* slot never. *Recommendation: yes.*
- **D12 — Order with RFC-0112:** stage 1 here before RFC-0112 stage 2.
  *Recommendation: yes.*

## Deutsche Zusammenfassung

**Worum es geht:** Ein Mandant bekommt **eine Stelle** für Zugangsdaten zu
fremden Systemen. Heute liegt so ein Geheimnis dort, wo es gebraucht wird:
in einer Destination, im MCP-Gateway (je Server und seit 0.16 je Person),
in der Konfiguration einer Instanz, in einer `.mcp.json` im Home. Ändert
sich ein Passwort, muss man es an jeder Stelle ändern.

**Drei Begriffe:**

1. **Fach** (slot): ein benannter Zugang des Mandanten, etwa `sap-a4h`
   oder `github`. Entweder **persönlich** (jede Person hinterlegt ihren
   eigenen Wert) oder **technisch** (ein Wert, vom Verwalter hinterlegt).
   Form: ein Token, Benutzer + Passwort, oder benannte Felder.
2. **Wert:** wird geschrieben und nie wieder angezeigt, auch nicht dem
   Verwalter. Ersetzen und löschen geht jederzeit.
3. **Freigabe:** verbindet eine Instanz mit einem Fach und nennt die Art
   der Nutzung.

**Zwei Arten der Nutzung:**

- **Einsetzen** (der Normalfall): Die App ruft über eine Destination, und
  die Plattform setzt den Wert der Person auf dem Weg nach draußen ein. Die
  App sieht ihn nie.
- **Aushändigen** (die Ausnahme, eigene Freigabe mit Warnung): Die App
  bekommt den Wert für genau eine Person, mit deren Zusicherung. Nötig
  etwa für stdio-Server, die `SAP_PASSWORD` in ihrer Umgebung erwarten.
  Jede Aushändigung steht in der Prüfspur.

**Die eine Seite:** „Meine Zugangsdaten“ im Portal, je Mandant. Dort
steht, was fehlt, was abgelehnt wurde, was abläuft, wann und von welcher
App ein Wert zuletzt benutzt wurde. Der Verwalter des Mandanten pflegt
Fächer, Freigaben und technische Werte; bei persönlichen Fächern sieht er
nur, wie viele Personen einen Wert haben, und kann einen löschen.

**Ablage:** verschlüsselt mit einem Schlüssel des Knotens, der getrennt
von den Daten liegt. Die verschlüsselten Werte dürfen in die Sicherung,
der Schlüssel nicht. Ehrliche Grenze: Wer root auf dem Knoten ist, kann
beides lesen.

**Was mit den heutigen Stellen passiert:** Destinations bleiben, können
später ein technisches Fach nennen. Das Verfahren U des MCP-Gateways zieht
in Stufe 3 auf Fächer um, vorhandene Werte werden einmal übernommen.

**Nicht Teil:** OAuth im Namen einer Person (Refresh-Tokens), die
Geheimnisse der Plattform selbst, und Single Sign-on — wo ein System dem
Anmeldedienst oder der CA des Mandanten vertrauen kann, ist das der
bessere Weg, und es wird gar kein Geheimnis gespeichert.

**Stufen:** (1) Ablage, Fächer, beide Seiten, Aushändigen, Bereitschaft;
(2) Einsetzen über Destinations; (3) MCP-Gateway Verfahren U auf Fächer;
(4) Destinations und die Gateways nennen technische Fächer.

**Entscheidungen D1–D12** sind offen; die Empfehlungen stehen in §9. Die
wichtigsten: Plattformfähigkeit statt App (D1); der `tenant_admin` pflegt
Fächer und technische Werte (D2); beide Nutzungsarten, Aushändigen als
eigene Freigabe (D3); verschlüsselt und in der Sicherung ohne Schlüssel
(D5, D6); wer den Mandanten verlässt, verliert seine Werte dort (D8).

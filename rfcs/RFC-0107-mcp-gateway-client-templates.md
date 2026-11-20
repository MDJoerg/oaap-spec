# RFC-0107: Client Templates in the MCP Gateway

- **Status:** **Accepted (2026-11-20)** — Jörg: "Angenommen. Los" (D1–D10 as
  recommended). **Both stages built the same day** in one release:
  `mcp-gateway` 0.28.0, `oaap.ai.mcp-gateway` 0.26.0, `ai-gateway` 0.11.1;
  not deployed. See §7.
- **Date:** 2026-11-20
- **Authors:**
  - Jörg: idea I-57, 2026-11-17. A view of the MCP gateway should give a
    ready configuration for a tool such as VS Code, Claude or goose, with
    the address, the way of signing in, and a placeholder instead of the
    secret. On 2026-11-20 he chose this as the next build after RFC-0106.
  - Claude: read `oaap.ai.mcp-gateway` 0.25 and the reference app 0.27.0,
    read the client formats on 2026-11-20, and wrote the design.
- **Depends on:**
  - `oaap.ai.mcp-gateway` 0.25: §2.1 keys, §2.2 sign-in, §2.3 access
    profiles, §1a `/me`, §1b readiness, §3.12 procedure U.
  - RFC-0106, for the template pattern: templates as data shipped with the
    app, a placeholder for the key, a format date on each template.
- **Not part of this RFC:**
  - **Personal sign-ins at outside services**, the second half of I-57: a
    person connects their own account at Jira or Google by OAuth, and the
    gateway keeps the token. Today a person can only paste a token, which
    is procedure U. Connecting an account by OAuth needs its own RFC.
  - Templates for the platform's own chat. The chat reaches the gateway
    through procedure A and needs no file.

## Summary

To use a view of the MCP gateway in a tool, a person needs three facts:
the address `https://<gateway>/mcp/<view>`, the way in (a key, or a
sign-in at the tenant's realm), and, for a sign-in, the client id and the
callback port. Today the gateway shows these in two places:

- When a key is issued, it shows the `claude mcp add` command once,
  **with the key's value in it**.
- The tab "Anmeldung" shows a `.mcp.json` for Claude Code with
  `clientId` and `callbackPort`.

Other tools get nothing, and each one has its own format. This RFC applies
the pattern of RFC-0106 to the MCP gateway:

1. **Templates** (stage 1). A new tab "Vorlagen" on the operator's page.
   The operator chooses a tool and the views, by hand or from a key. The
   gateway writes the file for that tool with a placeholder instead of
   the key. The first tools are Claude Code, VS Code and opencode. The
   templates are data shipped with the app, each with the date its format
   was checked. The template engine of the AI gateway moves into the shared
   library `gwcore`, so both gateways fill templates the same way.
2. **Self-service** (stage 2). With the key alone,
   `GET /mcp/_client-config?target=` returns the file for that key's views.
   On `/me`, a person gets the file for the sign-in views that are open to
   them, by the same rule as readiness.

## 1. Situation

### 1.1 What the gateway already knows

- **A view** has a name, one or more ways in (`key`, `signin`,
  `platform`), a light, and its entries.
- **A key** has a label, the list of its views, a ceiling class and a
  light. Only its hash is stored, so the value exists only at the moment
  it is issued.
- **Sign-in** has the issuer, the audience, the public client for persons
  (`MCPGW_SIGNIN_CLIENT`) and the fixed callback port 33418 (RFC-0065 D15).
  The realm accepts exactly `http://localhost:33418/callback`.
- **Procedure U** servers additionally need the person's own credential on
  `/me` before a call goes out. Readiness (§1b) tells per server whether a
  view is set up for the person.

### 1.2 Client formats, read on 2026-11-20

| Tool | File | Key way | Sign-in way |
|---|---|---|---|
| Claude Code | `.mcp.json`, key `mcpServers` | `type: http`, `url`, `headers.Authorization: "Bearer ${OAAP_MCP_KEY}"` (variable from the environment) | `oauth: {clientId, callbackPort}` |
| VS Code, Copilot's own format | `.mcp.json` in the folder or `~/.copilot/mcp-config.json`, key `mcpServers` | same as Claude Code, `${NAME}` from the environment, no input prompt | `oauthClientId` (a flat field); **no callback port** in the format |
| VS Code, editor format | `.vscode/mcp.json`, key `servers`, with `inputs` | `headers.Authorization: "Bearer ${input:oaapMcpKey}"`; VS Code asks once and keeps the value in its secret store | `oauth: {clientId}` |
| opencode | `opencode.jsonc`, `mcp.servers.<name>` (format "V2") | `type: remote`, `url`, `oauth: false`, `headers` with `{env:OAAP_MCP_KEY}` | `oauth: {client_id, callback_port, redirect_uri}` |

**VS Code is moving.** Its documentation from 2026-11-18 calls the editor
format the "local harness" and says it will be removed in February 2027.
New configurations should use Copilot's own format, which is the same file
as Claude Code's. That format cannot ask for a secret, and it has no field
for the callback port. Which redirect address VS Code uses for a sign-in
is **not documented**, and our realm accepts only
`http://localhost:33418/callback`. Whether a VS Code sign-in works against
the realm therefore has to be **measured** before the VS Code template
offers the sign-in way (D5).

**opencode** has an older form (`mcp.<name>` with `enabled`) next to the
"V2" form. The template follows V2 and carries the date it was checked.

## 2. Stage 1: templates

### 2.1 The tab "Vorlagen"

On the operator's page (role `admin`), next to "Anmeldung":

1. **Choose the tool:** Claude Code, VS Code or opencode. The list is the
   set of templates shipped with the app.
2. **Choose the views**, in one of two ways:
   - **From a key:** choose a key by its label. The views are that key's
     views, and the way in is `key`.
   - **By hand:** tick views and choose the way in per view, from the ways
     the view has.
3. **Result:** the file as text, with buttons to copy and download. Under
   it, short notes for the tool:
   - where the file goes;
   - which environment variable to set, without its value;
   - for a sign-in, "sign in once in the tool";
   - for a view with a procedure-U server, "first enter your own access on
     `/me`".

A view that has neither the `key` nor the `signin` way (only `platform`)
cannot be chosen. A tool cannot reach it, and the tab says why.

### 2.2 Templates as data

`templates/<tool>.json` in the app. A template has these fields:

- `id`, `name`, `file` (the suggested file name) and `checked` (the date
  and the documentation the format was read from);
- `ways`: which ways the template offers, `key`, `signin` or both;
- `document`: the frame of the file, with `{servers}` as a whole value;
- `entry`: the object per view, with one form per way (`key` and
  `signin`);
- `inputs`: only for VS Code's editor format, the input prompt for the key;
- `notes`: the notes from §2.1, as text with placeholders.

Placeholders, as in RFC-0106, are text placeholders or whole values:

| Placeholder | Value |
|---|---|
| `{name}` | the view's name, used as the server name in the tool |
| `{url}` | `https://<gateway>/mcp/<view>` |
| `{gateway}` | the gateway's address |
| `{client_id}` | `MCPGW_SIGNIN_CLIENT` |
| `{callback_port}` | 33418, as an integer |
| `{redirect_uri}` | `http://localhost:33418/callback` |
| `{key_var}` | the name of the key variable, `OAAP_MCP_KEY` (D4) |
| `{servers}` | the entries, as a whole value |

Rules carried over from RFC-0106:

- An unknown placeholder makes the template invalid. The app refuses it at
  start, and the tab names it.
- A template is never uploaded by an operator (RFC-0106 D6).
- **The key's value is never in a file**, on any path: not in the tab, not
  in the download, not in self-service, and not even right after the key
  is issued (D3). The test searches every output for the value and for
  `mcp-oaap-`.
- If the sign-in way is chosen but `MCPGW_SIGNIN_CLIENT` is not set, the
  tab names the gap, and the file is not offered.

### 2.3 One engine in `gwcore`

`templates.py` from the AI gateway moves into `oaap-apps/lib/gwcore` and
learns entry forms per way. The AI gateway imports it from there.
`check-shared.py` keeps both copies equal, as for the other `gwcore` files.
The templates themselves stay with each app, because each app has its own.

### 2.4 The key box after issuing

The box that shows a new key once keeps the value and the `claude mcp add`
command. The command is the one place where the value appears next to
configuration, and only because it appears only once. The box gains a link
to the tab "Vorlagen" with this key already chosen, where the files carry
the placeholder (D3).

### 2.5 The tab "Anmeldung"

The tab keeps its `claude mcp add` command. Its `.mcp.json` is replaced by
a link to the template "Claude Code, sign-in". One generator instead of
two keeps them from drifting apart (*one rule, one function*).

## 3. Stage 2: self-service

### 3.1 With the key

`GET /mcp/_client-config?target=<tool>` with
`Authorization: Bearer mcp-oaap-…`:

- **200:** the file for the key's views, the way `key`, sent as an
  attachment with `Cache-Control: no-store`.
- **401:** a wrong key, the same `401` as everywhere under `/mcp`.
- **400:** an unknown tool.
- A revoked key or an expired key gets `401`.
- The call is counted in the audit trail with the key's id and the tool.
  It is not a call to a server, so it is not counted as usage.

The person already has the key. The path saves them from asking the
operator which views it opens.

### 3.2 On `/me`

On `/me` ("Meine Werkzeuge"), a new box "In meinem Werkzeug einrichten":

- It shows the views that take sign-in and that the person may open: an
  access profile whose groups fit the person (the rule of readiness, §1b,
  `not_for_you` is left out).
- The person chooses the tool and gets the file, the way `signin`.
- Next to a view with a procedure-U server whose credential is missing, the
  box shows "erst Zugang hinterlegen", linked to the box on the same page.
- Views reachable only by key are not shown: the person does not hold the
  key, and the gateway does not know who does.

## 4. What stays the same

- `/mcp/<view>`, the keys, the sign-in, access profiles, procedure U.
- The light, the ceilings, usage rows. A template changes nothing a call
  can do.
- No secret leaves the gateway that did not leave it before.

## 5. Tests (described)

1. Each shipped template loads; one with an unknown placeholder is refused
   with its name.
2. Claude Code, key: a key with two views gives two entries with `url` and
   `Authorization: Bearer ${OAAP_MCP_KEY}`, and no value.
3. Claude Code, sign-in: `oauth.clientId` equals `MCPGW_SIGNIN_CLIENT` and
   `callbackPort` is 33418 as an integer.
4. Sign-in without `MCPGW_SIGNIN_CLIENT`: no file, the gap is named.
5. A view with only `platform` cannot be chosen.
6. opencode, key: `oauth: false` and `{env:OAAP_MCP_KEY}`; sign-in: the
   three snake_case fields.
7. VS Code: the file follows the format chosen in D5.
8. Self-service with a key: 200 with that key's views; a wrong, revoked or
   expired key gives 401; an unknown tool gives 400; no-store; an audit
   row.
9. `/me`: a person in the profile's group sees the view, a person outside
   does not; procedure U without a credential shows the hint.
10. No output on any path contains a key's value or `mcp-oaap-`.
11. The AI gateway's template tests pass unchanged with the engine from
    `gwcore`, and `check-shared.py` is green.

**Measurement after the build:**

- On `oaap-test`, Claude:
  - Claude Code with a generated `.mcp.json` and a measurement key
    reaches a view: `tools/list` answers.
  - The key is revoked afterwards.
- Jörg:
  - opencode with the key file.
  - VS Code with the key file.
  - A sign-in in VS Code against a realm: which redirect it sends, and
    whether the realm accepts it.

## 6. Decisions

- **D1 Same pattern as RFC-0106.** *Recommendation:* yes. Templates are
  data shipped with the app, a placeholder stands for the key, each
  template has a format date, and a tab "Vorlagen".
- **D2 One template engine in `gwcore`.** *Recommendation:* yes (§2.3).
  The alternative is a second copy in the MCP gateway, which would drift
  apart from the first.
- **D3 Never the value in a file, even right after issuing.**
  *Recommendation:* yes. The `claude mcp add` command in the key box stays
  the only place, because it appears only once. The alternative is
  offering a file with the value once: comfortable, but such a file ends
  up in a repository.
- **D4 One fixed variable name, `OAAP_MCP_KEY`.** *Recommendation:* yes,
  for the key way of all tools. A person with keys from two gateways
  renames it in the file. The alternative is a name per instance
  (`OAAP_MCP_KEY_<INSTANZ>`): clash-free, but longer, and the name changes
  when the instance is renamed.
- **D5 VS Code: which format.** *Recommendation:* Copilot's own format
  (`.mcp.json`, `mcpServers`, `${OAAP_MCP_KEY}`), because the editor format
  is to be removed in February 2027, and it is the same file as Claude
  Code's. Sign-in for VS Code only after the measurement (§1.2); until
  then the VS Code template offers only the key way. The alternative is
  the editor format with `${input:…}`, which asks for the key once and
  keeps it in VS Code's secret store. That is more comfortable today, but
  will soon be gone.
- **D6 First tools: Claude Code, VS Code, opencode.** *Recommendation:*
  yes. goose and Claude Desktop come later, when someone uses them.
- **D7 Views from a key or by hand.** *Recommendation:* both (§2.1).
- **D8 Self-service with the key.** *Recommendation:* yes (§3.1), at
  `/mcp/_client-config`, next to `_views` and `_readiness`.
- **D9 Sign-in files on `/me`.** *Recommendation:* yes (§3.2), with
  readiness's rule. Key views are not shown there.
- **D10 Both stages in one release.** *Recommendation:* yes, as with
  RFC-0106. Spec `oaap.ai.mcp-gateway` 0.26.0, reference `mcp-gateway`
  0.28.0, AI gateway 0.11.1 (engine from `gwcore`, no visible change).

## 7. Built (2026-11-20)

- **`gwcore/fill.py`** (in `oaap-apps/lib`, copied into both gateways by
  `check-shared.py`): text placeholders, whole-value placeholders, `OMIT`,
  `check_names`, `load_dir`. The AI gateway's `templates.py` now only says
  what its names mean; its 92 template and property tests pass unchanged.
- **MCP gateway 0.28.0:** `clientfiles.py`, `templates/claude-code.json`,
  `vscode.json` and `opencode.json`. The tab "Vorlagen", the link in the key
  box, the sign-in tab's `.mcp.json` from the Claude Code template,
  `/mcp/_client-config` and `/me/client-config` with the box "In meinem
  Werkzeug einrichten".
- **Deviation from §3.1:** MCP gateway keys have no expiry date, so the
  "expired key" case does not exist. A key that only opens views a tool
  cannot reach gets `409` with the reasons.
- **Deviation from §3.2:** readiness's rule (§1b) is for persons carried by
  a chat and matches `@<chat>` groups. On `/me` the gateway does not know
  the person's groups at the realm: the platform gives apps no groups
  (`oaap.core.identity` §2). The box therefore lists the sign-in views that
  some access profile opens, says "alle mit Anmeldung" for a profile with
  `*`, and for other profiles says that the sign-in decides. Nothing secret
  is in such a file, and the realm and the gateway still check every call.
- **Tests:**
  - `test_templates.py` 54/54 (new).
  - `lib/test_gwcore.py` 21/21.
  - mcp-gateway: `test_gateway` 547/548. The one failure, "Report zählt
    jede Zeile", fails the same way without this change.
  - mcp-gateway: setup 48, signin 28, compose 54, argcheck 29, sources and
    platform settings green.
  - ai-gateway: props 92, gateway 283, setup 108 (after two Windows socket
    aborts), assets 27.
  - `check-shared` and `check-store` green.
  - Targeted tests only; the full suite was not run.
- **Measured on `oaap-test` (2026-11-20).** `mcpgw-test` was raised from
  0.9.3 to 0.28.0, installed from a staged copy (`~/mcpgw-0280`), not from
  Git.
  - A measurement key for the views `ref` and `buendel`.
  - `/mcp/_client-config` through the node's gateway (port 8127, `Host` =
    the external name): `200` for all three tools, as an attachment with
    `no-store`. The key's value and `mcp-oaap-` were in none of the files.
    A wrong key got `401`. Three audit rows `client.config`.
  - With `url` and `headers` from the generated `.mcp.json`, and
    `${OAAP_MCP_KEY}` taken from the environment as Claude Code does:
    `initialize` and `tools/list` answered for both views (8 and 7 tools).
  - The keys were revoked afterwards. The first three runs did not reach
    the gateway (the duckdns name lands on the Fritzbox's rebind
    protection, and on port 80 of the node the name is unknown). Each of
    those runs revoked its key too: four revoked rows `messung-rfc0107*`.
- **Not measured yet:**
  - The real tools: Claude Code is not installed on this computer, so the
    client side was simulated with curl.
  - opencode and VS Code with the key file (Jörg).
  - Which redirect VS Code sends for a sign-in (Jörg).
- **Seen in passing, not changed:** `endpoint()` always writes `https://`.
  Behind the platform with TLS that is right; on a LAN port site without
  TLS the file's address would be wrong. The `claude mcp add` command has
  had the same rule since 0.3.

## Deutsche Zusammenfassung

**Worum es geht:** Wer eine Sicht des MCP-Gateways in einem Werkzeug
nutzen will, braucht drei Angaben: die Adresse, den Zugangsweg (Schlüssel
oder Anmeldung im Realm) und bei der Anmeldung die Client-ID und den Port
für den Rücksprung. Heute zeigt das Gateway nur zweierlei: nach dem
Ausstellen einmal den `claude mcp add`-Befehl samt Schlüssel, und auf dem
Reiter „Anmeldung“ eine `.mcp.json` für Claude Code. Für andere Werkzeuge
gibt es nichts.

**Vorschlag:** dasselbe Muster wie RFC-0106.

- **Stufe 1:** Neuer Reiter „Vorlagen“:
  - Werkzeug wählen: Claude Code, VS Code oder opencode.
  - Sichten wählen: aus einem Schlüssel oder von Hand.
  - Ergebnis: die Datei zum Kopieren und Herunterladen, mit Hinweisen.
  - Statt des Schlüssels steht die Umgebungsvariable `OAAP_MCP_KEY` in
    der Datei, bei Anmeldung die Client-ID und der Port 33418.
  - Die Vorlagen sind Daten in der App, jede mit dem Datum, an dem ihr
    Format geprüft wurde.
  - Die Vorlagen-Maschine des KI-Gateways wandert nach `gwcore`, damit
    beide Gateways dieselbe benutzen.
- **Stufe 2:** Selbstbedienung:
  - Mit dem eigenen Schlüssel liefert `GET /mcp/_client-config?target=`
    die Datei für dessen Sichten.
  - Auf `/me` bekommt eine Person die Datei für die Anmelde-Sichten, die
    für sie offen sind.

**Befund zu VS Code:** VS Code stellt laut seiner Doku vom 18.11. sein
bisheriges Format `.vscode/mcp.json` im Februar 2027 ein. Das neue Format
ist dieselbe `.mcp.json` wie bei Claude Code. Es kann aber nicht nach
einem Geheimnis fragen und kennt keinen Rücksprung-Port. Ob die Anmeldung
aus VS Code an unserem Realm klappt, ist nicht dokumentiert und muss
gemessen werden. Bis dahin bietet die VS-Code-Vorlage nur den
Schlüsselweg.

**Nicht Teil dieses RFC:** dass eine Person ihr eigenes Konto bei Jira
oder Google per OAuth verbindet, die zweite Hälfte von I-57. Heute geht
dort nur ein eingefügter Token (Verfahren U). Das bekommt ein eigenes RFC.

**Zu entscheiden sind D1–D10.** Meine Empfehlungen:

- Muster wie RFC-0106.
- Eine Maschine in `gwcore`.
- Nie der Schlüsselwert in einer Datei.
- Fester Variablenname `OAAP_MCP_KEY`.
- VS Code im neuen Format, zuerst nur mit Schlüssel.
- Zuerst Claude Code, VS Code und opencode.
- Sichten aus einem Schlüssel oder von Hand.
- Selbstbedienung mit dem Schlüssel und auf `/me`.
- Beide Stufen in einer Fassung: Spec 0.26.0, App 0.28.0,
  KI-Gateway 0.11.1.

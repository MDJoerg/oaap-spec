# RFC-0098: Targets, Roles and Log Levels — One View for Many Systems

- **Status:** Draft (2026-11-19). Direction decided by Jörg in conversation
  on 2026-11-19: the name is **target**; every target carries a **role**
  (development, test, training, demo, production); the **tenant** carries a
  role too and **the stricter one applies**; the level of detail recorded
  per call is **configurable** (test landscapes need it, production mostly
  only in a support case, reached through feedback with the person's
  consent). Open decisions D5–D11 below, each with a recommendation.
  Nothing built.
- **Date:** 2026-11-19
- **Authors:** Jörg (the case: "I'm missing authorizations in SAP" may
  concern more than ten systems, each with several clients — ten
  assistants are not user-friendly; the idea of a placeholder in the view
  with several servers behind it and a parameter that picks the way; the
  question what the gateway knows about person, device, assistant and
  session), Claude (reading of the gateway, design)
- **Depends on:** `oaap.ai.mcp-gateway` 0.18.0 (views §5, fixed arguments
  §5.3, procedure P §3.10, readiness §1b, usage §9, never recorded §10),
  `oaap.core.tenant`, RFC-0066 (propagation), RFC-0095 (`/me`), RFC-0097
  (assistants in the gateway)
- **Related:** RFC-0099 (UI design is allowed by role), I-62 W2/W3
  (feedback), RFC-0061 (cases)
- **Not part of this RFC:** discovering a landscape automatically (SAP
  transport landscape, SLD); the feedback dialogue itself (I-62)

## Summary

Three connected pieces:

1. **Targets.** A view entry can name a **target group**: several servers
   with the same tools, each with a label ("D01/100 — S/4HANA
   development"). The gateway lists the tools **once**, adds a parameter
   `target`, and two tools `list_targets` and `describe_target`. The chat
   can set the target for a conversation in a list box; the person may, but
   need not. Without a target the gateway refuses and names the targets
   the person may use — the hint the model needs.
2. **Roles.** Every target and every tenant has a role: `development`,
   `test`, `training`, `demo`, `production`. The **stricter** of the two
   applies to a call. Roles decide what is possible: confirmation of
   writing tools, UI design (RFC-0099), the log level.
3. **Log levels.** What a usage row holds beyond today's columns is
   configurable: `lean` (today), `support`, `full`. The tenant sets the
   default, the role can only make it stricter. In production, context
   comes through **feedback with consent**, not by recording in advance.

## 1. Facts (read 2026-11-19)

- A usage row holds the person (`user_iss`/`user_sub`), `client`,
  `assistant`, `confirmed`, `procedure`, `outcome`, `reason`, `status`,
  `door`, sizes and duration. It holds **no conversation and no device**.
- §10: no argument, no result, no free text of a server or a person in any
  row.
- An MCP view today maps catalog entries one to one; the same tool from
  ten servers means ten entries with ten names, or ten views.
- In SAP, a system has several clients; with procedure P each system/client
  usually has its own destination anyway (own CA trust, own user mapping).

## 2. Targets

### 2.1 The target group

```yaml
# in a view
- group: sap-basis
  tools_from: [a4h-100, d01-100, d01-200, q01-100, p01-100]
  targets:
    a4h-100: {label: "A4H/100 — ABAP trial", role: development}
    d01-100: {label: "D01/100 — S/4HANA development", role: development}
    d01-200: {label: "D01/200 — S/4HANA development, test client", role: test}
    q01-100: {label: "Q01/100 — S/4HANA quality", role: test}
    p01-100: {label: "P01/100 — S/4HANA production", role: production}
```

- Each member is an ordinary server record of the gateway (own address,
  procedure, destination, credentials, light).
- **Same tools:** the gateway compares the members' tool lists by
  fingerprint (name, schema, effect class). A member that differs is shown
  on the operator's page with the difference and is left out of the group
  until confirmed (same mechanics as a changed description, §4.2).
- Tool names appear once, under the group's prefix.

### 2.2 The parameter

- Every tool of the group gets a parameter `target` (string; as an `enum`
  with labels in the description up to D7's limit, as free text above it).
- The gateway **removes** `target` before forwarding and routes to the
  member; the server never sees it.
- `list_targets` returns the targets **this person** may use, with label
  and role; `describe_target` returns the label, the role and a free
  description the operator wrote (e.g. "D01 is where development happens;
  roles are transported via Q01").
- A target the person may not use is not listed and refused like a target
  that does not exist (no oracle).

### 2.3 Who sets the target

- **The chat:** a list box per conversation (only for assistants whose
  view has a target group). Set by the person, the chat fills `target` in
  every call; the model cannot override it (the chat replaces a different
  value and says so).
- **The model:** if no target is set, the model fills it. A call without
  `target` is refused with a sentence such as *"This tool needs a target.
  Call `list_targets` or ask the person which system is meant. Targets you
  may use: D01/100, Q01/100, …"*.
- **External clients** (RFC-0097 channel, Claude Code): same parameter,
  same refusal.

### 2.4 Rights per target

- Readiness (RFC-0095 stage 3) is answered per target: a person may be
  ready in D01 (credential, user mapping) and not in P01.
- Effective = view ∩ the person's rights ∩ the target's rights.

## 3. Roles

### 3.1 Where roles are set

- **Target:** in the target group (above), by the gateway's operator.
- **Tenant:** a field `role` in the tenant record (`oaap.core.tenant`),
  set by `server_admin`, visible to `tenant_admin`; default `production`
  (the safe side — a new tenant that nobody classified is treated as
  production).

### 3.2 The rule

The **stricter** role applies to every call. Order from strict to loose:
`production` > `training` > `demo` > `test` > `development`. (D5:
whether `training` and `demo` are stricter than `test` because real persons
use them.)

### 3.3 What roles decide

| | development / test | demo / training | production |
|---|---|---|---|
| writing tools | per view | confirmation required | confirmation required, always |
| UI design (RFC-0099) | allowed with the grant | allowed with the grant | never |
| log level, at most | `full` | `support` | `support` (only via feedback, §4.3) |
| shown in the chat | grey | blue | red label on the list box and the call card |

The table is the default; the tenant may make it stricter, never looser.

## 4. Log levels

### 4.1 Levels

- **`lean`** — today's columns.
- **`support`** — plus a random **call id** per call, generated by the
  client (chat, channel). On its own it links nothing: one id, one row.
- **`full`** — plus a random **conversation id** and a **device class**
  (`browser`, `desktop`, `cli`, `app`) per call.

All three are **statements of the client**, recorded for information;
no decision depends on them (like `assistant` today). None is content: a
random id and a word from a fixed list (§10 stays literally true).

### 4.2 Who sets the level

- The tenant sets the default (setting of the gateway instance,
  `tenant_admin`).
- The role of §3 caps it per call.
- The usage row records the level it was written with, so a reader knows
  what is missing on purpose.

### 4.3 Feedback with consent

In `support`, the chat keeps the list of call ids per conversation in the
person's own history (which only the person reads). When the person sends
feedback (I-62 W2), the chat asks for consent and hands over the list. Only
then can the support see which usage rows belong to that conversation — for
that conversation alone. No profile is recorded in advance; the context is
complete the moment the person wants it.

### 4.4 Who sees what

- The person: their own rows with call and conversation ids on `/me`.
- The operator: rows as today; the conversation id is shown only after
  stating a reason, and that look is audited (RFC-0022 §6: looking is
  visible).
- Feedback hands over a list; the support case (RFC-0061) holds it.

## 5. Decisions

- **D1 Name.** *Decided (Jörg, 2026-11-19):* target.
- **D2 Roles.** *Decided:* development, test, training, demo, production —
  on targets and on tenants.
- **D3 Combination.** *Decided:* the stricter one applies.
- **D4 Log detail.** *Decided:* configurable; production mostly only via
  feedback with consent.
- **D5 Order of training and demo.** *Recommendation:* stricter than test
  (real persons, sometimes real data).
- **D6 Default role of an unclassified tenant.** *Recommendation:*
  production.
- **D7 Enum or free text.** *Recommendation:* enum up to 30 targets, free
  text plus `list_targets` above.
- **D8 Can the model override the person's choice?** *Recommendation:* no;
  the chat replaces and says so in the call card.
- **D9 Retention of call and conversation ids.** *Recommendation:* the
  usage row's window (30 days on `/me`, RFC-0095 D4); in a support case
  the case keeps the list as long as the case lives.
- **D10 Device class.** *Recommendation:* the four words above, nothing
  finer (no user agent, no IP).
- **D11 Green models in demo/training.** *Recommendation:* later; a tenant
  setting "only green models with role demo/training" fits here but is not
  part of stage 1.

## 6. Stages and tests

| stage | content | done when |
|---|---|---|
| 1 | target groups, `target` parameter, `list_targets`/`describe_target`, refusal with hint, fingerprint comparison | a call without target is refused with the person's targets; a member with a different tool list is held out; a target the person may not use is refused like a non-existent one (bait) |
| 2 | roles on targets and tenants, stricter wins, confirmation rule, label in the chat | a tenant `test` calling P01 asks for confirmation on a writing tool; a tenant `production` calling D01 does too |
| 3 | log levels, call id, conversation id, device class, level per row, `/me` shows them | in `lean` no id is stored; in `support` one id per row and no conversation id; the role caps `full` to `support` |
| 4 | feedback hands over call ids with consent (with I-62) | without consent the support case holds no ids; with consent exactly the conversation's rows |

Spec changes: `oaap.ai.mcp-gateway` (§5.5 target groups, §9 columns
`call_id`, `conversation_id`, `device`, `log_level`, `target`, §10 note),
`oaap.core.tenant` (field `role`), `oaap.ai.assistants` (nothing — the
target is per conversation, not per assistant; D: a default target per
assistant could come later).

## Zusammenfassung auf Deutsch

Drei Teile, die zusammengehören:

1. **Ziele:** Ein Sichteintrag kann eine **Zielgruppe** nennen, also
   mehrere Server mit denselben Tools, jeder mit einem Etikett („D01/100 –
   S/4HANA Entwicklung“). Das Gateway zeigt die Tools nur einmal, ergänzt
   den Parameter `target` und die Tools `list_targets`/`describe_target`.
   Im Chat setzt eine Listbox das Ziel für das Gespräch, wenn die Person
   das will. Sonst füllt die KI das Ziel. Fehlt es, lehnt das Gateway ab
   und nennt die Ziele, die diese Person benutzen darf. Das Gateway
   vergleicht die Tool-Listen der Mitglieder und hält Abweichler zurück.
   Bereitschaft und Rechte gelten je Ziel.
2. **Rollen:** Ziel und Mandant haben je eine Rolle (Entwicklung, Test,
   Schulung, Demo, Produktiv). **Die strengere gilt.** Daran hängen
   Bestätigung schreibender Tools, UI-Design (RFC-0099), die
   Protokollstufe und die Farbe im Chat. Ein nicht eingestufter Mandant
   gilt als produktiv.
3. **Protokollstufen:** `knapp` (heute), `support` (zufällige Aufruf-ID je
   Aufruf) und `voll` (zusätzlich Gesprächs-ID und Geräteklasse).
   Vorgabe am Mandanten, die Rolle kann nur verschärfen. Im Produktivbetrieb
   kommt der Zusammenhang über **Feedback mit Einwilligung**: Der Chat
   kennt die Aufruf-IDs eines Gesprächs und übergibt sie erst, wenn die
   Person zustimmt. So entsteht kein Profil auf Vorrat. Alle Angaben dienen
   nur zur Auskunft, und §10 (keine Inhalte im Protokoll) bleibt wörtlich
   wahr.

Entschieden sind D1–D4 (Jörg, 19.11.), offen D5–D11 mit Empfehlungen.

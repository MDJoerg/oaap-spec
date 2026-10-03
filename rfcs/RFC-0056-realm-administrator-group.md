# RFC-0056: The Realm Administrator Group — A Narrow Door for the Customer's Own Administrator

- **Status:** **Accepted (2026-10-03)** — decided by Jörg in the rights session
  (decision sheet `program/auftraege/rollen-rechte-entscheidungsvorlage.md`,
  points 1–4 "as recommended"). Stage 1 (connector verb) and stage 2 (the jump
  in the portal) are built with this RFC; stage 3 (groups as the source of
  business roles) is RFC-0045 stage 3 and is not built here.
- **Date:** 2026-10-03
- **Authors:** Jörg (the need: customers maintain their own people), Claude
  (measurement and write-up)
- **Depends on:** RFC-0041 (identity provider per tenant, connector contract,
  K3.3 "nothing deletes, no people"), RFC-0045 (business authorization, §5 the
  provider's groups), RFC-0048 (member care, service account), RFC-0055 (build
  profile — this verb becomes one of its steps later)
- **Idea:** I-28 (jump + narrow administrator), I-29 (groups as source of roles)

## Summary

A customer tenant has its own realm. Its administrator must be able to create
and block people and keep their groups **without** the Keycloak console that
shows the whole realm. OAAP prepares one thing in the realm: a **group**
`oaap-verwalter` that carries exactly four `realm-management` client roles —
`manage-users`, `view-users`, `query-users`, `query-groups`. Whoever the club
puts into that group can administer people and groups of that one realm and
nothing else.

**It is a group, not a user.** The connector contract says `users` is `never`
(RFC-0041 K3.3): OAAP does not create people in somebody's realm. A group with
roles is not a person, so the rule stays true; who sits in it is the club's
business.

## 1. Measured (2026-10-03, Keycloak 26.7.4, `oaap-test`)

Script `program/messungen/keycloak-verwalter-messung.py`; a human holding the
four roles:

- may list, search, count, create people, set a temporary password, create
  groups, put people into groups, set group attributes;
- gets 403 on the master realm, clients, identity providers, client scopes,
  components, event configuration, realm settings; may not create a client;
- may **not** give anyone (or a group, or itself) the client roles `realm-admin`
  or `manage-clients` (403);
- **may assign an existing realm role that is a composite over `realm-admin`**
  (204, to a person and to a group). It cannot *create* realm roles. The hole
  exists only if such a role exists in the realm;
- the admin console loads for such a person (Jörg, browser): people, groups and
  role assignment work, creating or changing roles does not.

### 1.1 Measured with the built verb (2026-10-03, `oaap-test`, connector account with `create-realm` only)

Script `program/messungen/keycloak-verwaltergruppe-messung.py`:

- the connector account creates the group and gives it the four roles (the
  `realm-management` roles are reachable for it in a realm it made);
- a second run writes nothing; the read-back names the four roles;
- with a trap role (`falle`, composite over `realm-admin`) in the realm the verb
  **refuses and writes nothing**; after the role is removed the same call succeeds;
- a person in the group lists people and groups, gets 403 on clients, identity
  providers and the master realm, and 403 when giving **itself** or **the group**
  `realm-admin` or `manage-clients`;
- a person in the group **can remove a role from the group** (204). That weakens
  the group and widens nothing; running the verb again adds the missing role
  ("gave the group: view-users"). It is the repair, and it is why §2.2 says
  "add".

## 2. The verb `admin_group`

The connector table gains an optional verb (`OPTIONAL_VERBS`):

| field | Keycloak |
|---|---|
| name | `oaap-verwalter` (derived from the table, never typed by an operator) |
| client of the roles | `realm-management` |
| roles | `manage-users`, `view-users`, `query-users`, `query-groups` |

Rules, each one a rule and not a setting:

1. **Refuse before touching.** If the realm holds a realm role that is a
   composite reaching any role of `realm-management` (directly or through
   another realm role), the verb refuses and writes nothing — the group would
   carry a measured escalation. The sentence names the roles.
2. **Add, never remove, never replace.** An existing group keeps whatever it
   has; missing roles are added; extra roles are reported (never removed — it
   may be somebody's arrangement).
3. **Nothing deletes** (unchanged `method_refusal`) and **no person is created.**
4. **Version first** (unchanged plan rule): the plan starts with the version
   check; nothing is written before it passed.
5. **Read back.** What is recorded is what the realm answered after the change
   (the roles the group holds now), not what was asked.
6. The space must exist — this verb makes no realm (`provision` does).

CLI: `oaap idp admin-group <connector> --tenant <label> [--dry-run]
[--accept-version V]`. It is not part of `provision`, so the build profile
(RFC-0055) takes it as an own step later without changing the run of
`provision`.

## 3. The jump in the portal (stage 2)

In the tenant administration page, for a tenant whose provider is a connector
space (`space` known), a link **"Benutzer im Anmeldedienst verwalten"** to
`<provider base>/admin/<space>/console/`. The address comes from the
tenant's provider object (issuer `…/realms/<space>`), never typed. Visible to
`tenant_admin` of that tenant and `server_admin`. A tenant without a provider,
or with an issuer that does not look like `…/realms/<space>`, shows nothing.
The page says plainly that the person must be in the group `oaap-verwalter`
(or hold equivalent roles) — OAAP does not create that person.

## 4. The group claim (added 2026-10-03)

The client the connector makes now carries a group-membership mapper
(`oaap-groups`: claim `groups`, full path, ID and access token); `provision`
adds it to a client it **found**, only if missing, and refuses with a sentence
if a mapper of that name does something else. Before this, the token carried no
groups at all. See `oaap.core.authorization` 0.2 §2.9.

## 5. What this does not do

- It does not map groups to OAAP roles (that is RFC-0045 stage 3, with the
  rules decided 2026-10-03: evaluated at every login; mapped by group **path**,
  because the token carries the path and not an id — measured; a renamed group
  fails closed; `server_admin`, `support`, `tenant_admin` never from the realm).
- It does not put anybody into the group.
- It does not touch realm roles. OAAP creates none.

## Deutsche Zusammenfassung

Ein Kundenmandant hat einen eigenen Realm. Sein Verwalter soll Personen und
Gruppen pflegen, ohne die volle Keycloak-Konsole. OAAP legt dafür **eine
Gruppe `oaap-verwalter`** an, mit genau vier Rechten (`manage-users`,
`view-users`, `query-users`, `query-groups`). Wer darin sitzt, verwaltet
Personen und Gruppen dieses einen Realms, sonst nichts.

**Gruppe statt Benutzer**, weil OAAP nie Menschen in einem fremden Realm
anlegt (RFC-0041 K3.3). **Gemessen:** Das schmale Recht reicht für Personen
und Gruppen, andere Bereiche liefern 403, `realm-admin` kann er niemandem
geben — aber eine **bereits vorhandene** Realm-Rolle mit Verbund über
`realm-admin` kann er zuweisen. Darum **verweigert** der neue Befehl
`oaap idp admin-group`, wenn es im Realm eine solche Rolle gibt, und schreibt
dann nichts. Er fügt nur hinzu, entfernt nie, legt keinen Menschen an und
liest nachher nach, was die Gruppe wirklich trägt. Im Portal gibt es auf der
Mandantenverwaltung einen Absprung zur Konsole, dessen Adresse aus dem
Anbieter-Objekt kommt. Die Abbildung Gruppe → Fachrolle bleibt RFC-0045
Stufe 3.

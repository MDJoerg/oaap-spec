# RFC-0072: Mail From the Node — One SMTP Mailbox for the Realms, Later One per Tenant

- **Status:** Proposed (2026-11-06)
- **Date:** 2026-11-06
- **Authors:** Jörg (the need, the stages, a mail server for it), Claude
  (facts read in the reference code and the specs, design)
- **Depends on:** RFC-0041 (identity provider per tenant, OAAP provisions the
  realm), RFC-0033 / `oaap.net.destinations` (a tenant's way out, the secret
  store no container mounts), RFC-0055 (tenant build), RFC-0068 (closed egress)
- **Related, not decided here:** OAAP creating the first administrator and
  sending the set-password mail (the "b" of 2026-11-06 — needs this RFC first),
  platform notifications to the operator (backup failed, reboot due)
- **Driver:** The first handball tenant on `oaapx02` is to be built in one go
  and used at once. A realm OAAP makes today **cannot send a single mail**: no
  "forgot password", no e-mail verification, no invitation. Somebody would have
  to type SMTP settings into every realm's console by hand.

## Summary

The operator records **one SMTP mailbox per node** once (host, port, TLS mode,
sender, user and password). Every realm OAAP provisions gets it written in;
existing realms get it with one command. The password lives in the node's
secret store and, because Keycloak sends the mail itself, in the realm. Stage 2
lets a tenant bring **its own mailbox** (its own sender domain), which then
replaces the node's for that tenant's realm. Stage 3 lets **apps** send through
a tenant's mailbox by the binding that already exists for TCP destinations.

## 1. Facts (read 2026-11-06)

- `idp_admin._keycloak_space_body` creates a realm with `registrationAllowed`,
  `loginWithEmailAllowed`, `duplicateEmailsAllowed`, `sslRequired` — **no
  `smtpServer`**, no language. Nothing in the reference writes SMTP anywhere.
- Keycloak keeps SMTP per realm (`smtpServer`: `host`, `port`, `from`,
  `fromDisplayName`, `replyTo`, `ssl`, `starttls`, `auth`, `user`, `password`)
  and sends verification, reset and "execute actions" mails itself. The narrow
  service account (`create-realm`) manages the realms it made, so it may write
  this (to be measured, §6).
- RFC-0048 measured: a fresh realm's settings read shows no SMTP block; what a
  read returns once SMTP is set is **not measured** (Keycloak masks secrets in
  general).
- `oaap.net.destinations`: a destination belongs to **exactly one tenant**,
  kinds `http` and `tcp`; a `tcp` destination is handed to the app as
  environment values named by the manifest (example in the spec: `mail` with
  `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`). The secret lives in a
  store no container mounts. There is no "sender" and no TLS mode.
- A tenant build (RFC-0055) has `idp.provision`; a step for mail does not exist.

## 2. Proposal

### Stage 1 — the node's mailbox, written into the realms

- `oaap mail set --host … --port 587 --tls starttls|tls|none --from
  noreply@<domain> [--from-name …] --user … [--password-file …]` (server_admin,
  CLI; the portal's node page later). The password is read from a file or the
  terminal, never from the command line. Stored like a destination's secret:
  0600, in no container.
- `oaap mail test <address>`: the host sends one plain test mail and prints the
  server's answers (no password in the output).
- **Every realm OAAP provisions** gets the mailbox written in, with
  `fromDisplayName` = the tenant's title. `oaap idp mail <connector> --tenant
  <label>` writes it into an existing realm; `--all` into every realm of that
  connector made by OAAP (needed when the password changes).
- The connector declares a new verb `mail` (realm update, only the
  `smtpServer` block); a product without it says so.
- Audit: setting, changing, writing into a realm — node log and the tenant's.

### Stage 2 — a mailbox per tenant

- A tenant (its `tenant_admin`, or the operator for it) records its own
  mailbox — its own domain as sender. Its realm then uses that one instead of
  the node's. Removing it falls back to the node's.

### Stage 3 — apps send mail

- A tenant's mailbox becomes bindable to an instance like a `tcp` destination
  (handover of host, port, user, password, plus sender). The **node's** mailbox
  is not offered to apps (D7).

## 3. Decisions asked of Jörg

- **D1 — Where the mailbox lives.** (a) A new destination kind `smtp`
  (fields host, port, tls, from; secret in the existing store): the node's
  mailbox is the `smtp` destination of the default tenant, a tenant's own is
  its `smtp` destination, an app binds it in stage 3 — one object, one secret
  store. (b) A separate node setting now, destinations later.
  **Recommended: (a)** — stage 2 and 3 then cost almost nothing.
- **D2 — Which realms.** Every realm OAAP makes gets the node's mailbox
  automatically, unless the tenant has its own. **Recommended: yes**; the build
  needs no extra step and no extra tick.
- **D3 — Sender.** One sender address for the whole node (as the mail server
  allows it), the display name per tenant ("Handballverein X"), optional
  Reply-To per tenant. **Recommended**, because a mail server usually accepts
  only senders of its own domain (SPF/DKIM are the mail provider's business).
- **D4 — The password in the realm.** Keycloak needs it to send, so it is
  stored in Keycloak's database and in a realm export (a tenant moving away
  takes it along). **Recommended: accept, and say so** where a realm is
  exported; a changed password is rewritten with `--all`.
- **D5 — Language.** With the mailbox, the realm's language is set to German
  (`defaultLocale: de`, German and English offered) — the mails and the login
  page are then German. **Recommended: yes**, as a node default.
- **D6 — Who sets it.** Stage 1: `server_admin` only. Stage 2: the tenant's
  own mailbox also by its `tenant_admin`. **Recommended.**
- **D7 — Apps and the node's mailbox.** Not offered to apps: a spamming app
  would burn the node's sender for every tenant. Apps get mail only from a
  tenant's own mailbox (stage 3). **Recommended.**
- **D8 — Egress.** The Keycloak instance must reach the mail server; a closed
  default tenant (RFC-0068) needs the mail server named there. Stated, no
  choice.

## 4. Out of scope

- Receiving mail, mailboxes to read, newsletters.
- OAAP creating a person (the first administrator). After stage 1 it can be
  decided on its own: "execute actions" mail needs exactly this.
- Notifications of the node to its operator.

## 5. Stages and what is measured

1. Stage 1 on `oaap-test` against Jörg's mail server: `mail test`, a realm
   provisioned with the mailbox, a test person's "forgot password" arrives;
   what the realm read returns afterwards (is the password masked?); an
   existing realm with `idp mail`; the narrow account may write `smtpServer`.
2. Stage 2, stage 3 — after stage 1 is in use.

## 6. Open measurements

- May the `create-realm` account write `smtpServer` and read it back masked?
- Does Keycloak's own "test connection" work for the service account (it
  sends to the calling user's address, which a service account has not)?

## Zusammenfassung (deutsch)

**Anlass:** Der Handballmandant auf oaapx02 soll in einem Zug entstehen und
sofort nutzbar sein. Ein Realm, den OAAP anlegt, kann heute **keine einzige
Mail** verschicken: kein „Passwort vergessen“, keine Bestätigung der Adresse,
keine Einladung.

**Vorschlag in drei Stufen (wie von Jörg gewünscht):**

1. **Ein Postfach je Knoten.** Der Betreiber trägt einmal Server, Port,
   Verschlüsselung, Absender, Benutzer und Passwort ein (`oaap mail set`, Test
   mit `oaap mail test`). Jeder Realm, den OAAP anlegt, bekommt es
   eingetragen; bestehende Realms mit `oaap idp mail … --tenant` bzw. `--all`.
2. **Ein Postfach je Mandant** (eigene Absender-Domain); es ersetzt das des
   Knotens für diesen Realm.
3. **Apps verschicken Mail** über das Postfach ihres Mandanten — über die
   Bindung, die es für TCP-Ziele schon gibt.

**Entscheidungen für Jörg (Empfehlung jeweils „ja“):** D1 das Postfach als
neue Ziel-Art `smtp` (ein Objekt, ein Geheimnisspeicher, Stufen 2 und 3
fast geschenkt); D2 jeder neue Realm bekommt es automatisch; D3 ein Absender
je Knoten, Anzeigename je Mandant; D4 das Passwort steht zwangsläufig auch im
Realm (Keycloak verschickt selbst) und reist bei einem Umzug mit; D5 der Realm
wird dabei auf Deutsch gestellt; D6 Stufe 1 nur `server_admin`; D7 das
Knotenpostfach bekommen Apps nie; D8 Keycloak muss den Mailserver erreichen.

**Nicht hier:** das automatische Anlegen des ersten Verwalters (Jörgs „b“) —
geht erst, wenn Mail geht, und wird danach eigens entschieden.

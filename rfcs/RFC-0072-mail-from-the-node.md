# RFC-0072: Mail From the Node — One SMTP Mailbox for the Realms, Later One per Tenant

- **Status:** **Accepted (2026-11-06)** for stage 1; **stage 2 with the portal page
  "Nachrichten" proposed (§8, D9-D16 asked)** -- -- Jörg: "Mach alles so wie empfohlen"
  (D1-D8 as recommended). **Stage 1 built (reference 0.1.233, §7).**
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

## 7. Stage 1 built and measured (2026-11-06, reference 0.1.233)

- `oaap.net.destinations` 0.8 §2.11 (kind `smtp`), `oaap.core.tenant` 1.4
  (criterion 22). `oaap mail set|show|test|clear`; `oaap idp mail <connector>
  --tenant | --all`; `idp provision` writes the mailbox (D2) and says so when the
  node has none; a new realm is German (D5). Connector verb `mail` (Keycloak:
  a partial `PUT` of the realm -- name, `smtpServer`, language -- read back).
- **Measured on oaap-test against Jörg's mail server** (port 465, TLS):
  `oaap mail test` -> login 235, accepted, in the inbox one second later (read over
  IMAP). `oaap idp mail auth --tenant vuebung` -> written by the narrow
  `create-realm` account, **the password reads back masked** (§6 answered).
  A throwaway person in `vuebung` (made and deleted by a measuring script, not by
  OAAP) was sent Keycloak's "update your account" mail -> it arrived, **in
  German** ("Aktualisieren Sie Ihr Konto").
- **Not measurable on oaap-test:** a NEW realm through `idp provision` (the node
  has no external name, finding of 2026-10-18) -- the automatic write of D2 is
  tested without a node only; it wants a node with a name.
- Found while measuring: `test/vm.sh` sources `test/.env` as shell; an unquoted
  value with a space there runs part of it as a command.

## Zusammenfassung Stufe 1 (deutsch)

**Gebaut und auf oaap-test gegen Jörgs Mailserver gemessen:** Testmail kommt an;
das Postfach steht im Realm `vuebung`, Keycloak zeigt das Passwort verdeckt; eine
Mail von Keycloak selbst („Aktualisieren Sie Ihr Konto“) kam an, auf Deutsch.
**Nicht messbar auf oaap-test:** ein neuer Realm über `idp provision` (kein
Außenname) -- dafür braucht es oaapx01 oder oaapx02.

## 8. Stage 2 — the portal page "Nachrichten" and a mailbox per tenant (proposed 2026-11-06)

Jörg, 2026-11-06: the mailbox is configured **in the portal, by the tenant
administrator** -- "we need that anyway" -- under a new menu entry
**"Nachrichten"**, because incoming mail and real-time messaging (Telegram)
will follow.

### 8.1 What stands in the way, read in the specs

`oaap.net.destinations` §2.7: destinations are written by `server_admin`
only, because whoever writes a target decides where the platform connects,
and a name that later resolves inward is a way into the node's own networks.
A tenant's mailbox is such a target: Keycloak, on the platform network, sends
through it; `oaap mail test` connects from the host. Stage 2 therefore needs a
rule that makes a tenant-written mailbox safe enough (D10).

### 8.2 The page

- **Menu "Nachrichten"** for `server_admin` and `tenant_admin`, beside the
  others. One page per tenant (at a tenant's place: that tenant; at the node's
  address: the node).
- **Section "Postausgang"** (outgoing mail), today:
  - Which mailbox this tenant's realm sends with: *its own* (address, sender,
    login, "password set") or *the node's* (only its sender is shown).
  - A form for the tenant's own mailbox: address (`smtps://` or `smtp://`),
    sender, sender's name, reply-to, login, password. **Save** checks the login
    at the server first (D11), then stores it and writes it into the tenant's
    realm. **Test mail** sends one mail to an address the admin types.
    **Remove** falls back to the node's mailbox (D12).
  - At the node's address, the `server_admin` edits **the node's mailbox** the
    same way (D15) and sees a list: which tenant sends with which mailbox.
- **Later sections, each with its own RFC and only once built:** "Posteingang"
  (incoming mail, mailboxes to read) and "Messenger" (e.g. Telegram). No
  placeholders before (D16).

### 8.3 Decisions asked of Jörg

- **D9 -- The menu.** "Nachrichten", for `server_admin` and `tenant_admin`.
  **Recommended.**
- **D10 -- May a `tenant_admin` write a mailbox target?** (a) **Yes, with
  checks that fit mail:** only ports 465 (TLS) and 587 (STARTTLS); the host
  must resolve to **public addresses only** at save, at test and at every
  write into a realm (no private, loopback, link-local or Docker range); TLS
  is required, and Keycloak verifies the server certificate -- a service
  inside the node has no certificate for a public name, so the handshake fails
  before anything is said. What stays: a name that resolves inward only
  *after* the check (DNS rebinding) could make Keycloak start a TLS handshake
  there; it learns nothing back. (b) The tenant enters, the `server_admin`
  releases. (c) The `server_admin` keeps a list of allowed mail servers, the
  tenant chooses one and enters only the login. **Recommended: (a)** -- it is
  the "tenant admins do it themselves" Jörg asked for, and the protocol plus
  TLS keep the remaining door narrow; `destinations` §2.7 stays as it is for
  HTTP and TCP.
- **D11 -- Save means "the login works".** The host logs in at the server
  (no mail is sent) before it stores anything. **Recommended.**
- **D12 -- Remove falls back.** The realm gets the node's mailbox again
  (or none, said so). **Recommended.**
- **D13 -- What a tenant sees of the node's mailbox:** its sender only, never
  server or login. **Recommended.**
- **D14 -- The password through the portal.** A password field; the value
  travels in the spool request to the host, which moves it into the secret
  store and deletes the request; it is never shown again ("set"), changing it
  means typing it again; nothing about it is logged. The portal keeps nothing.
  **Recommended.**
- **D15 -- The node's mailbox in the portal too**, for `server_admin` at the
  node's address (the CLI stays). **Recommended.**
- **D16 -- Incoming mail and messengers** come as further sections of the same
  page, each specified on its own first; nothing is shown before it is built.
  **Recommended.**

Stage 3 (apps send through the tenant's mailbox) follows on this page as a
third part of "Postausgang": which instances may use it.

## Zusammenfassung Stufe 2 (deutsch, Vorschlag)

**Jörgs Wunsch:** Das Postfach richtet der **Mandanten-Admin im Portal** ein,
unter einem neuen Menü **„Nachrichten“** -- dort kommen später Posteingang und
Messenger (Telegram) dazu.

**Die Seite:** Abschnitt **„Postausgang“** zeigt, mit welchem Postfach der Realm
des Mandanten verschickt (eigenes oder das des Knotens -- von dem nur der
Absender zu sehen ist), und hat ein Formular für das eigene Postfach:
Speichern prüft erst die Anmeldung am Server, dann wird es gespeichert und in
den Realm geschrieben; Testmail; Entfernen fällt auf das Postfach des Knotens
zurück. Am Knoten pflegt der Server-Admin dort das Knotenpostfach und sieht,
welcher Mandant womit verschickt.

**Die eine echte Frage (D10):** Heute dürfen Mandanten-Admins keine Ziele
anlegen, weil ein Ziel bestimmt, wohin die Plattform sich verbindet. Für Mail
empfehlen wir: **ja, mit Prüfungen** -- nur Port 465/587, der Name muss auf
öffentliche Adressen zeigen (bei jedem Speichern, Testen, Schreiben), TLS
Pflicht, Keycloak prüft das Zertifikat. Alternativen: der Server-Admin gibt
frei, oder er führt eine Liste erlaubter Mailserver.

**Weitere Empfehlungen (D9, D11-D16):** Menüname „Nachrichten“; Speichern =
Anmeldung klappt; Entfernen fällt zurück; Passwort über das Portal nur einmal
eingegeben, danach nie wieder angezeigt; Knotenpostfach auch im Portal;
Posteingang und Messenger erst, wenn sie gebaut sind.

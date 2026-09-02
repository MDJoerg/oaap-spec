# RFC-0028: The Terminal and the Person In Front Of It

- **Status:** Draft — seven decisions open (§8)
- **Date:** 2026-09-02
- **Authors:** Claude (analysis & proposal), Jörg (direction)
- **Depends on:** RFC-0027 (machine principals), RFC-0007 (visibility
  groups), RFC-0008 (`server_admin`), RFC-0022 (tenant as boundary)
- **Driver:** Jörg, 2026-09-02: *"Der 3D-Viewer im cls-Tenant wird
  beispielsweise als Terminal in der Produktion betrieben … Wir wollen
  das so machen, dass man sich mit einem OAAP-Admin-Account einloggen
  muss, danach aber dieses Terminal konfiguriert und es dann mit einer
  Art 'Terminal'-Account weiterarbeitet. … Zusätzlich könnte es
  notwendig sein, dass Benutzer dem Terminal zugeordnet werden, die
  sich beispielsweise per PIN oder RFID-Token am Terminal entsperren.
  … Das Thema Produktion und Logistik habe ich mit im Scope und dort
  wird das oft benötigt."*

## Summary

A screen on a shop floor has **two identities, and they must not be
equal**.

The **terminal** is a thing: it stands in a known place, it runs
unattended, it must survive a reboot without anyone typing an admin
password into a kiosk. It is authenticated — a machine principal with
a real credential (RFC-0027).

The **person in front of it** holds a PIN or a badge. That is not a
credential. A four-digit PIN is ten thousand guesses; the common RFID
card types are copied in seconds with a thirty-euro reader, out of a
jacket in the break room. If that produced an OAAP session with roles,
we would have built a careful boundary — tenant, roles, gateway
default deny — and then put a fifty-cent key under the doormat.

So the rule this RFC exists to write down:

> **The badge opens nothing. It only signs.**

The terminal's roles are the **ceiling**: everything possible after
someone badges in was possible before. The operator identity travels
alongside so an app can **attribute** an action and **narrow** a view —
never widen one. And because "then nobody can approve anything"
would be the obvious objection, §4.6 gives the escape hatch up front:
an action that needs a real person asks for a real login, once, for
that action.

Whether the platform should own this at all is a fair question, and
§4.7 draws the line: the platform owns the **plumbing**, which is
identical in every plant; the app owns the **meaning**, which never is.

## 1. What the scenario actually needs

1. The terminal is set up **once**, by a human with authority, at the
   machine.
2. Afterwards it runs for months without that human.
3. It shows what that location may see — and not the rest of the
   tenant.
4. Anyone standing in front of it can use it, without a login.
5. What they do can be attributed to a named person, weakly.
6. A stolen or scrapped terminal can be cut off **alone**.

Points 4 and 5 together are the whole difficulty. They say: *no
authentication, but attribution* — which is a coherent requirement only
if nothing security-relevant depends on the attribution.

## 2. What blocks it today

**The session cookie is browser-lived.** `session.permanent` is never
set in `platform/services/identity/app.py`, so the cookie dies with the
browser process. A kiosk is therefore logged out by every reboot, power
cut and browser crash, and someone must walk over with an admin
password. This was measured on the code, not assumed.

The naive fix — make sessions permanent — is the wrong one. It would
extend every person's session too, and it would still leave the
terminal holding a *human's* credential, which is the thing we are
trying to stop.

**There is no non-human principal.** Every user in the store is a
person with a password. A terminal today can only be a person's
account, which means it inherits that person's roles, appears as them
in every log, and dies when they leave the company.

## 3. Why the badge must not grant

Stated once, so it does not have to be re-argued in every project:

- A PIN chosen by a warehouse worker is four digits, shared with a
  colleague within a week, and written on the frame of the screen
  within a month.
- MIFARE Classic and the 125 kHz cards still common in industry are
  readable and clonable with commodity hardware. Newer cards are not,
  but the customer's existing badges are the ones they will want to use.
- The reader is on a shop-floor network, and shop-floor networks are
  flat.

None of that makes badges useless. It makes them **identification**,
which is what they are for: *who did this pick*, not *may this person
pick*. The design must state which of the two it is, because a system
that quietly treats identification as authentication is worse than one
with no badges at all — it produces an audit trail everyone trusts and
nobody should.

**Consequence, and it is the important one:** because the terminal's
roles are the ceiling, the terminal must be given **few**. A terminal
principal that holds `admin` is a terminal where the badge does not
matter, because everything was already open.

## 4. Proposal

### 4.1 A terminal is a machine principal

One machine principal per terminal (RFC-0027 §3.1), in the tenant that
owns it:

```json
{ "username": "cls-terminal-3", "kind": "machine",
  "tenant": "<cls-uuid>", "roles": ["user"],
  "groups": ["packstation"], "active": true }
```

Its visibility groups (RFC-0007) do the location work: the terminal at
the packing station reaches the packing apps and nothing else. That
mechanism exists and is enforced at the gateway, not in a menu.

**One principal per terminal, not one for all** (§8 D1). Cost is near
zero; the return is that a stolen terminal is revoked alone, the audit
log says *which* screen, and groups can differ by location.

### 4.2 Enrolment: one admin login, once

Jörg's flow, made precise:

1. A `tenant_admin` logs in at the terminal, normally.
2. Portal → *"Make this browser a terminal"* → picks a name, a
   location label, visibility groups, an idle timeout.
3. The platform creates the machine principal, issues a key
   (RFC-0027), and stores it in that browser.
4. The admin's own session is ended on that machine.

From then on the browser presents the terminal's credential, not a
person's. A reboot changes nothing.

The credential must be **bound to that browser** — stored so that
copying the URL is not enough — and re-enrolment must be possible from
the portal without a site visit, because the alternative is a support
call from a plant at 06:00.

### 4.3 The operator roster lives in the tenant

Operators are **not OAAP users** (§8 D7). Five hundred warehouse staff
who never log in anywhere should not be five hundred accounts with
passwords, sessions and role assignments.

They are tenant data:

```json
{ "id": "op-4711", "name": "M. Berger", "tenant": "<cls-uuid>",
  "tags": ["<hash of tag id>"], "pin": "<hash>",
  "active": true, "valid_until": null }
```

Stored by the platform rather than by each app, for a reason that runs
against the usual instinct: an app that keeps PIN hashes itself will
keep them badly. This is the rare case where centralising a weak
secret **reduces** risk — hashed once, rate-limited once, revoked once,
and never copied into the next app.

### 4.4 Presence: who is at terminal X

The platform keeps one small piece of state per terminal:

```json
{ "terminal": "cls-terminal-3", "operator": "op-4711",
  "since": "...", "expires": "..." }
```

- Set by an **unlock**: a tag or PIN arrives, the platform resolves it
  to an operator **on its own side** and records presence.
- Cleared by an explicit lock, by an idle timeout, or by expiry.
- The idle timeout logs out the **operator**, never the terminal. The
  screen stays usable at the terminal's own level; only the attribution
  ends.

The resolution happening on the platform side is not a detail. If the
mapping tag→operator lived in the message, anyone who can reach the
ingress could claim to be anyone.

### 4.5 What the app receives

Alongside the existing two headers, on routes of a terminal session:

```
X-OAAP-User:        cls-terminal-3
X-OAAP-Roles:       user
X-OAAP-Operator:    op-4711
X-OAAP-Operator-Name: M. Berger
```

Set and stripped by the gateway exactly like the existing pair — an
app can never forge them, and an app that is not on a terminal session
simply does not see them.

Contract for the app, stated so it can be tested:

- **May** attribute an action to the operator.
- **May** narrow what it shows.
- **Must not** grant anything the terminal principal does not already
  hold. The platform enforces the ceiling anyway; this is the rule that
  stops an app from *feeling* like it enforces more than it does.

### 4.6 Step-up, for the actions that really need a person

Some actions need accountability a badge cannot carry: cancelling an
order, signing off a quality step, overriding a safety interlock.

The app asks the platform for a **step-up**: a real login, at the
terminal, for that one action. It returns a short-lived assertion
naming a real OAAP user — and does **not** replace the terminal
session.

This is in the RFC from the start deliberately. If we leave it out,
the first customer with a supervisor-only action gets a bolted-on
answer, and the bolted-on answer is always "let the PIN mean
permission".

Whether it ships in v1 is §8 D6; whether it is *designed for* in v1 is
not negotiable.

### 4.7 What the platform does not own

| Platform | App |
| --- | --- |
| terminal principal, credential, enrolment | what an operator may see and do |
| operator roster, per tenant | domain meaning of an operator |
| presence state, idle lock | display, workflow, attribution in its data |
| the ingress that sets presence | |
| step-up assertion | when to demand one |

The same split the platform already uses: **the platform
authenticates, the app authorises its own domain.**

## 5. Ingress: the event first, the transport later

At Jörg's request MQTT is **deferred** — it belongs with the wider
messaging and digital-twin discussion he wants to have first. What this
RFC fixes now is the **event**, so that transports are adapters:

> *terminal T reports tag X at time t*

Two rules that hold for every transport:

1. **The reader is a principal.** It presents its own credential
   (RFC-0027). Without this, anyone who can reach the ingress can badge
   anyone in — and on a flat shop-floor network, that is everyone.
2. **The mapping is resolved on the platform.** The message carries the
   raw tag id and nothing else.

**Version 1 needs no infrastructure at all.** The cheap RFID readers in
industry are USB **keyboard emulators**: they type the tag id into
whatever field has focus. The terminal's browser reads it and posts it.
MQTT, when it comes, is a second adapter to the same event — not a
second design.

## 6. What this costs

- **A weak secret store we now own.** PIN hashes and tag ids are
  customer data of a kind we have not held before. They need hashing,
  rate limiting, an expiry story and a line in the backup discussion.
- **A new header pair that apps will over-trust.** Some app, someday,
  will treat `X-OAAP-Operator` as permission. The ceiling in §4.5
  makes that harmless rather than catastrophic — which is the reason
  the ceiling exists.
- **Physical assumptions we inherit.** This design is honest only where
  the terminal is physically controlled. On a screen in a public
  reception area it is wrong, and the portal should say so at enrolment
  rather than in a document nobody opens.
- **Support surface.** Terminals get lost, re-imaged and replaced.
  Re-enrolment from the portal is not optional.

## 7. What it buys

- Jörg's scenario works as described, and the 3D viewer at cls can run
  as a kiosk without a person's account behind it.
- Production and logistics — explicitly in scope — get as a platform
  capability what is otherwise project work every single time.
- Attribution without accounts: five hundred operators, zero
  passwords, zero sessions.
- A stolen terminal is one revocation.

## 8. Decisions asked for

**D1 — One principal per terminal, or one for all terminals?**
*Recommendation: per terminal.* Revocation, audit and per-location
visibility groups all want it, and principals cost nothing. One shared
principal only wins where there is no tooling to manage many — so the
answer is to ship `oaap terminal add`.

**D2 — Does the operator reach the app as a header, or must the app
ask?** *Recommendation: header for identity, plus a small read API for
detail.* The header is what makes the common case free.

**D3 — Roster on the platform or in the app?**
*Recommendation: platform, tenant-scoped.* §4.3 — this is the one place
where centralising a weak secret lowers risk.

**D4 — PIN as well as RFID, or RFID only?**
*Recommendation: both, both hashed, both rate-limited.* PIN is the
weaker of the two and customers will insist on it; refusing means they
build it in the app, worse. What must not happen is a PIN that grants.

**D5 — Idle auto-lock: default on, and what timeout?**
*Recommendation: on, per-terminal, default 5 minutes, and it ends the
operator only.* A terminal that keeps a name attached for a whole shift
attributes the night shift's work to whoever came in at six.

**D6 — Step-up in v1, or designed-for only?**
*Recommendation: designed for in v1, implemented when the first real
case appears.* Naming it now costs one section; retrofitting it costs
the rule in §3.

**D7 — Are operators OAAP users?**
*Recommendation: no.* They are tenant data with no login, no session
and no roles. If a person needs to log in, they get a normal account —
the two are different things about possibly the same human, and
conflating them is how the badge starts granting.

## Non-goals

- **MQTT and messaging** — deferred to the digital-twin discussion
  (§5).
- **Making sessions permanent** for people. The kiosk problem is solved
  by a machine principal, not by weakening everyone's session.
- **Kiosk-mode browser packaging** (autostart, locked-down shell,
  screen management). Real work, someone else's layer, and it changes
  per hardware.
- **Offline operation.** A terminal that cannot reach the platform
  cannot resolve a badge. Queueing scans through an outage is a
  separate problem and probably a separate RFC.
- **Biometrics.** No.

## Zusammenfassung auf Deutsch

Ein Bildschirm in der Halle hat **zwei Identitäten, und sie dürfen
nicht gleichwertig sein.**

Das **Terminal** ist authentifiziert: ein Maschinen-Prinzipal mit
eigenem Geheimnis (RFC-0027), einer je Terminal. Seine
Sichtbarkeitsgruppen aus RFC-0007 machen die Ortsarbeit — das Terminal
an der Packstation erreicht die Packstations-Apps und sonst nichts.
Einrichtung einmalig durch einen `tenant_admin` am Gerät; danach läuft
es monatelang, auch über Neustarts. **Heute geht das nicht:** Der
Sitzungs-Cookie stirbt mit dem Browser, ein Kiosk ist nach jedem
Neustart abgemeldet (am Code nachgesehen, nicht vermutet).

Der **Mensch davor** wird **erkannt, nicht authentifiziert**. Vier
Ziffern sind 10 000 Möglichkeiten, gängige RFID-Karten kopiert man in
Sekunden. Deshalb die Regel, für die dieser RFC existiert: **Der
Ausweis öffnet nichts, er schreibt nur mit.** Die Rollen des Terminals
sind die **Obergrenze** — was nach dem Badgen geht, ging vorher schon.
Die Werkerkennung reist als zusätzlicher Header mit; die App darf damit
**zuschreiben und einschränken, nie erweitern**. Und weil sonst sofort
die Frage kommt, wer denn dann noch etwas freigeben kann: Für
Handlungen, die einen echten Menschen brauchen, gibt es die
**Aufwertung** — eine echte Anmeldung für genau diese eine Handlung.

**Werker sind keine OAAP-Benutzer.** Fünfhundert Hallenmitarbeiter, die
sich nirgends anmelden, sollen keine fünfhundert Konten sein. Sie sind
Mandantendaten (Name, Tag-Nummern, PIN — alles gehasht). Das ist der
seltene Fall, in dem **Zentralisieren eines schwachen Geheimnisses das
Risiko senkt**: einmal gehasht, einmal gebremst, einmal entzogen.

**MQTT ist auf Deinen Wunsch zurückgestellt** — es gehört zum Gespräch
über Digitale Zwillinge und Messaging. Festgelegt wird hier nur das
**Ereignis** („Terminal T meldet Tag X um t"), damit MQTT später ein
Adapter ist und kein zweiter Entwurf. Zwei Regeln gelten für jeden
Transport: Der **Leser ist selbst ein Prinzipal**, und die Auflösung
Tag → Werker passiert **auf der Plattform**. Version 1 braucht gar
keine Infrastruktur: Die billigen RFID-Leser sind
Tastatur-Emulatoren.

Sieben Entscheidungen liegen bei Jörg (§8) — ein Prinzipal je Terminal,
Werkerkennung als Header, Verzeichnis auf der Plattform, PIN und RFID
beide gehasht, Zeitsperre für den Werker statt fürs Terminal,
Aufwertung in Version 1 mitgedacht, und Werker sind keine Benutzer.

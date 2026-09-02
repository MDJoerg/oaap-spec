# RFC-0028: The Terminal and the Person In Front Of It

- **Status:** Accepted (2026-09-02) — D1 and D7 decided by Jörg;
  D1's answer changed the model (see §4.1). D2–D6 taken as
  recommended. Step-up (D6) and MQTT (§5) are staged, not built.
  Enrolment (§4.1/4.2) implemented in reference 0.1.64; operator
  presence (§4.4/4.5) is the next stage.
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

### 4.1 A device is not a principal

The first draft of this RFC said "one machine principal per terminal".
Jörg answered D1 with **"sowohl als auch — Entscheidung des
Anwenders"**, and that answer is better than either option offered,
because it forces apart two things the draft had welded together.

- A **device** is an enrolled screen. It has an id, a name, a location,
  and **its own credential**.
- A **principal** is what that device authenticates *as* — a machine
  principal in the sense of RFC-0027 §3.1, carrying tenant, roles and
  visibility groups.

Several devices may share a principal. **No two devices ever share a
credential.** That is the line that makes the operator's choice safe:
even with ten terminals on one principal, a lost screen is revoked
**alone** (its key is revoked, the others keep working), and the audit
log still names *which* screen, because the key id identifies the
device.

```json
// principal (RFC-0027 §3.1)
{ "username": "cls-terminal", "kind": "machine",
  "tenant": "<cls-uuid>", "roles": ["user"],
  "groups": ["packstation"], "active": true }

// device — one per screen, each with its own key
{ "id": "k7f3a91c", "label": "Packstation 3", "principal": "cls-terminal",
  "terminal": true, "expires": "...", "last_used": "..." }
```

**The device record IS the key record.** Written as two things in the
draft, built as one — a device is a named credential, and every field
the draft wanted (id, name, principal, enrolled by, last seen) is
already in a key. Giving it a separate store would have meant two
things to create, two to revoke and two to keep in step, in exchange
for nothing. When presence arrives (§4.4) it gets its own small file,
keyed by this same id.

**What the operator gains by sharing a principal:** one set of roles
and groups to maintain, one thing to change when the location's apps
change.

**What they give up, and it is the whole decision:** visibility differs
per *principal*, not per device (RFC-0007). A packing station that must
see different apps than goods-in needs its own principal. The portal
should say exactly that at enrolment, in one line, rather than leaving
it to be discovered.

**Default: a new principal per terminal.** Sharing is the deliberate
choice, not the path of least resistance — because the failure mode of
sharing (everyone sees the packing apps) is silent, and the failure
mode of not sharing (more principals to maintain) is merely tedious.

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

**What implementation changed here.** The draft said the browser
"presents the key". It cannot: **a browser puts no `Authorization`
header on an ordinary navigation.** A script can; a kiosk following a
link cannot. So a terminal needs a **cookie**, not a header — and step
3 above is really an *exchange*: the key is posted once to
`/auth/terminal`, which returns a long-lived session cookie naming the
machine principal **and the key it came from**.

That last part is what keeps the exchange honest. Every request
re-checks the named key, so:

- `oaap key revoke` ends the terminal **within seconds**, not at the
  next reboot. A cookie that outlived its credential would make
  revoking the same as doing nothing.
- deactivating the principal does the same, through the check that was
  already there.
- the key's expiry is the session's expiry.

The key travels from the portal to identity in a **hidden form field**
on a page rendered once, for the administrator standing at the machine
— never in a URL, and it is never displayed. It does not need to be
written down anywhere: it goes into this browser and stays there.

**And a terminal does not log out.** The button is refused for a
terminal session, because one stray tap in a warehouse would otherwise
leave a dead screen until somebody with an administrator password walks
over — and the person who tapped it would have no way to know that is
what happened. Ending a terminal is revoking its key, from the portal,
without being there.

Re-enrolment must be possible from the portal without a site visit,
because the alternative is a support call from a plant at 06:00.

### 4.3 The operator roster lives in the tenant

Operators are **not OAAP users** (§8 D7, decided). Five hundred warehouse staff
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

The platform keeps one small piece of state **per device**, never per
principal — otherwise one operator badging in at Packstation 3 would
appear to be standing at every screen that shares the principal:

```json
{ "device": "dev-a91c", "operator": "op-4711",
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

## 8. Decisions

D1 and D7 were put to Jörg and decided; D1's answer changed §4.1.
D2–D6 are taken as recommended until he says otherwise.

**D1 — One principal per terminal, or one for all terminals?**
**Decided (Jörg, 2026-09-02): both — the operator chooses.** This
rejected the framing rather than the options: it separates *device*
from *principal* (§4.1). Every device keeps its own credential either
way, so revocation and audit survive sharing; only visibility groups
are tied to the principal, and that is the trade the operator is
choosing. Default is a new principal per terminal.

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
**Decided (Jörg, 2026-09-02): no.** They are tenant data with no login, no session
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
eigenem Geheimnis (RFC-0027). Jörgs Entscheidung zu D1 — *sowohl als
auch, der Anwender wählt* — hat den Entwurf verbessert, weil sie
**Gerät und Prinzipal trennt**: Mehrere Geräte dürfen sich einen
Prinzipal teilen, **niemals aber ein Geheimnis**. Jedes Gerät bekommt
bei der Einrichtung seinen eigenen Schlüssel, also wird ein verlorener
Bildschirm auch bei geteiltem Prinzipal **allein** entzogen, und das
Protokoll sagt trotzdem welcher. Verloren geht genau eines, und das ist
die eigentliche Entscheidungsfrage: **unterschiedliche Sichtbarkeit je
Ort** hängt am Prinzipal. Vorgabe ist deshalb ein eigener Prinzipal je
Terminal; Teilen ist die bewusste Wahl. Die Sichtbarkeitsgruppen aus
RFC-0007 machen die Ortsarbeit — das Terminal
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

**Beim Bauen kam ein Befund dazu (§4.2):** Ein Browser setzt bei einer
normalen Navigation **keine `Authorization`-Kopfzeile**. Ein Skript kann
das, ein Kiosk, der einem Link folgt, nicht. Ein Terminal braucht also
ein **Cookie**, kein Kopfzeilen-Verfahren — die Einrichtung *tauscht*
den Schlüssel einmal gegen eine langlebige Sitzung, und diese Sitzung
**nennt weiterhin den Schlüssel**. Jede Anfrage prüft ihn nach: Damit
beendet `oaap key revoke` das Terminal in Sekunden statt beim nächsten
Neustart. Ein Cookie, das seinen Nachweis überlebt, machte Entziehen zu
Nichtstun. Der Schlüssel reist dabei in einem **versteckten
Formularfeld** auf einer Seite, die genau einmal gerendert wird — nie in
einer Adresse, und angezeigt wird er nie. **Und ein Terminal meldet sich
nicht ab:** Ein Fehltipp in der Halle darf keinen toten Bildschirm
hinterlassen, den nur jemand mit Administratorpasswort wiederbelebt.

**MQTT ist auf Deinen Wunsch zurückgestellt** — es gehört zum Gespräch
über Digitale Zwillinge und Messaging. Festgelegt wird hier nur das
**Ereignis** („Terminal T meldet Tag X um t"), damit MQTT später ein
Adapter ist und kein zweiter Entwurf. Zwei Regeln gelten für jeden
Transport: Der **Leser ist selbst ein Prinzipal**, und die Auflösung
Tag → Werker passiert **auf der Plattform**. Version 1 braucht gar
keine Infrastruktur: Die billigen RFID-Leser sind
Tastatur-Emulatoren.

**Entschieden (Jörg, 02.09.):** D1 — Gerät und Prinzipal getrennt, der
Anwender wählt. D7 — Werker sind keine Benutzer. Die übrigen fünf
(Werkerkennung als Header, Verzeichnis auf der Plattform, PIN und RFID
beide gehasht, Zeitsperre für den Werker statt fürs Terminal,
Aufwertung in Version 1 mitgedacht) nehme ich wie empfohlen — jede ist
eine Zeile, keine davon ein Umbau.

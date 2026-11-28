# RFC-0142: The Situation On the Go — One Picture per Role, a PWA, and Actions That Cannot Wait

- **Status:** **Accepted (2026-11-28)** — direction decided by Jörg the
  same day, D1–D8 all as recommended („Ja, wie empfohlen“).
  **Stage 0, server half, measured 2026-11-28 (§11)**; the phone half
  needs Jörg's devices.
- **Date:** 2026-11-28
- **Authors:** Jörg (the need: „eine mobile Oberfläche … als icon auf dem
  home screen … gemäß seiner Rolle … Auffälligkeiten sehen und darauf
  reagieren“; „Ja PWA“; „Wir sollten nicht davon ausgehen, dass unsere
  Zielgruppe immer am Rechner sitzt“), Claude (design)
- **Depends on:** RFC-0143 (people bound to instances — the third audience),
  RFC-0144 (short links of a tenant — campaigns in the picture), RFC-0080
  (notifications, matters), RFC-0083 (weekly report), RFC-0141 (site check),
  I-81 (page statistics), RFC-0108 (history per instance), RFC-0059
  (maintenance, standby), RFC-0092 (login required), RFC-0136 (coupling by
  QR), I-41 (an assistant has no rights of its own)
- **Changes (when accepted):** `oaap.core.portal` (the PWA under `/m`, a
  page *Geräte*), `oaap.core.identity` (device credentials), 
  `oaap.core.notifications` (a delivery channel *push*), a new capability
  `oaap.core.situation` (the picture), later `oaap.ai.mcp-gateway` (reading
  tools over the picture)

## Summary

The people the platform is for — the owner of a server, a tenant's
administrator, the person who looks after a club's web site — are not at a
desk when something happens. Today they get a mail and have to open a
laptop to understand it and to act.

This RFC adds **one picture of the situation per role** — what is unusual
now, what changed this week, what is open — computed on the node, and a
**progressive web app** (PWA, an installable web page) that shows it on a
phone's home screen. A phone is **paired** with a person's account from the
portal. The app shows only what the person's role lets them see: the node
for a `server_admin`, the tenant for a `tenant_admin`, their instances for a
person bound to instances (RFC-0143). **Notifications arrive as push**
besides mail. A short list of **actions that cannot wait** — maintenance on
and off, require login, restart, back to the previous version, test to
production, shut out AI fetchers, pause a short link, postpone a planned
reboot — can be taken from the phone, each confirmed with the phone's
fingerprint or face. Later the same picture is the AI chat's reading
material: „Was war heute los?“.

The phone gets **no rights of its own**: every action is the request the
portal already sends to the node, and the node judges it again.

## 1. Why one picture, not three screens

The mobile view, the weekly report and the chat need the same facts. Built
three times they will disagree. So the platform gets one module that
answers, for a person and a scope, *what is the situation*:

- **Unusual now** — open matters (RFC-0080), red points of the site check,
  instances down or in maintenance, a disk filling, a planned reboot.
- **Different from usual** — today and this week against the weekly mean of
  the weeks before, for the numbers the node already keeps: page views and
  visits, 404s, search engines, CPU and memory per instance (RFC-0108),
  short-link clicks (RFC-0144). Only deviations a person would act on are
  shown („3× so viele 404 wie üblich“), never a table.
- **What happened** — actions of the week from the audit logs (who put what
  into maintenance, promoted, restarted), backups, updates.
- **What is coming** — a planned reboot, a certificate that ends soon, a
  waiting promotion.

The rule that already makes `site.notfound` quiet is the rule here:
compare with the person's own history, and say nothing when nothing is
unusual.

## 2. The picture — `oaap.core.situation`

- Computed **on the host** by the minute job's slow branch (every 5
  minutes, cheap: it reads files the node writes anyway), written as one
  view per scope: `apps/situation/node.json` and
  `apps/situation/<tenant>.json` (0644 for the portal, like `space.json`).
  No new collection of data — only the joining of what exists.
- **Shape:** `{measured, scope, unusual: [...], deviations: [...],
  happened: [...], coming: [...], instances: {name: {state, lights,
  views_today, views_week, cpu, mem, check, links}}}`. Each entry carries
  `instance` (or none), `level` (red/yellow/info), a German sentence, and a
  link into the portal.
- **Filtered by the reader:** the portal (and later the chat's tool) reads
  the scope's view and keeps only what the person may see: a `tenant_admin`
  the tenant's view, a bound person (RFC-0143) the entries of their
  instances. The filter is one function, used by every surface (the rule
  „zwei Wege, eine Regel“).
- Nothing in the picture is a secret: no content of an app, no addresses,
  no names of visitors. The same sentence-level facts a mail carries.

## 3. The PWA

- **Where:** `/m` on the node's address and on a tenant's place (its own
  domain, RFC-0115), served by the portal: a manifest, a service worker, a
  few kilobytes of HTML/JS of our own, no framework, no external font or
  script. Installable on Android (Chrome) and iOS (Safari, „Zum
  Home-Bildschirm“).
- **Screens:**
  1. **Lage** — the start: unusual entries first, red before yellow, each a
     tap into its instance; „Alles ruhig“ when nothing is.
  2. **Instanzen** — the person's instances with state, a light, today's
     views against usual, CPU/memory; one instance opens its detail: page
     statistics of 7 days, site check, short links, recent actions, and the
     action buttons the person may use.
  3. **Kampagnen** — the person's short links and campaigns (RFC-0144),
     clicks per day as a small chart.
  4. **Woche** — what happened and what was different, the weekly report in
     short.
- **Offline:** the last picture is kept on the phone and shown with its age
  („Stand 14:32“); actions need a connection.
- Light and dark, large touch targets, German.

## 4. Pairing a phone

- In the portal a person opens **Geräte** (their own menu) and „Handy
  koppeln“: the page shows a **QR code and a short code** valid for 10
  minutes. The person opens `/m` on the phone, installs it, opens it from
  the home screen and scans the code (or types it). The phone then creates
  a **device key** — a passkey (WebAuthn) bound to that phone, with
  fingerprint or face to use it — and the node records it under the
  person: `{device, name, created, last_seen, by}`.
- **Why the installed app scans, not the camera:** on iOS an installed web
  app keeps its own storage, separate from Safari; a pairing finished in
  Safari would not reach it (to measure, stage 0).
- The device opens a **session of its own**, short (hours), renewed with the
  device key; the portal's session is not shared. **Geräte** lists every
  paired phone with its last use and a button „Trennen“; a `server_admin`
  may separate any device of the node, a `tenant_admin` those of the
  tenant's people. Losing a phone = one tap in the portal.
- A person leaving the tenant (account disabled) loses every device at
  once.

## 5. Push

- A new delivery channel **push** beside mail (`oaap.core.notifications`):
  for the matters and events that already exist, routed as today; a person
  with a paired device may switch push on per type for themselves.
- **Web Push with the node's own VAPID key** (the platform already makes
  such keys, `oaap.apps.runtime` 2.8). The message passes through the
  phone's vendor (Apple, Google), end-to-end encrypted by the Web Push
  standard; still, the **payload is short** (D5): subject only, e.g.
  „[bec] Instanz ausgefallen: shop“, the detail is fetched when the app
  opens.
- A node without an external name, or a phone that has not been seen for
  30 days, gets no push; the mail stays the reliable channel.

## 6. Actions on the phone

Jörg: the people the platform is for are often not at a computer, and
**time-critical actions** belong on the phone. Claude's recommendation —
what cannot wait, can be undone, and already exists as a request the node
judges:

| Action | Why it cannot wait | Who may | Exists as |
|---|---|---|---|
| **Wartung an / aus** (with a sentence for visitors) | a broken release, an embarrassing page | instance admins, bound *Betreuer* | `maintenance` |
| **Anmeldung erzwingen / freigeben** | something is public that should not be | instance admins, bound *Betreuer* | `login-required` |
| **Neu starten** | the app hangs | instance admins, bound *Betreuer* | `restart` |
| **Aufwecken** | a sleeping instance is needed now | instance admins, bound *Betreuer* | `wake` |
| **Zurück zur vorigen Version** | the last update broke it | instance admins, bound *Verantwortliche* | `rollback` / `oaap-prev` (stage 0 confirms the door) |
| **Test → Produktion** | the fix is ready, the event starts tonight | instance admins, bound *Verantwortliche* | `promote` |
| **KI-Abrufer sperren** | a crawler takes the site down | instance admins, bound *Betreuer* | `ai-fetchers` |
| **Seiten-Check: Jetzt prüfen** | did the fix work? | as the check | `site-check` |
| **Kurzlink pausieren / Ziel ändern** | a printed campaign points to a dead page | link owner, bound *Verantwortliche* | RFC-0144 |
| **Geplanten Neustart verschieben** | it would hit the club's live event | `server_admin` | `reboot at … / cancel` |
| **Lage gesehen** | the others need to know someone is on it | anyone who receives it | new: an acknowledgement on a matter, shown to the others, mails nothing |

**Never on the phone** (D6): removing an instance or data, users and roles,
tenants, domains, keys and secrets, the server's package updates, backups
and restores. They are rare, hard to undo, and need a screen.

**How:** each button sends the request the portal sends today, through the
same spool and the same host judgment, with the device's person as actor
and `via: mobile` in the audit. Before it is sent the phone asks for the
fingerprint or face again (a WebAuthn assertion with user verification, not
just the session) — a stolen unlocked phone does not suffice. A promotion
or a rollback shows what it will do (version from → to) and asks once more.

## 7. The chat (last stage)

The picture becomes a reading tool of the MCP gateway: `lage_heute`,
`lage_woche`, `instanz_lage(name)`, `kampagnen(...)`, filtered by the same
function as the PWA for the person who asks. The chat answers „Was war
heute los? Was war anders? Welche Aktion lief diese Woche gut?“ from it.
It **proposes** actions and links to the button; it never triggers one
(I-41). In the PWA a small „Frag den Assistenten“ opens the tenant's chat
with the question prefilled, when the tenant has one.

## 8. Stages

| Stage | Content | Done when |
|---|---|---|
| 0 | Measure: install `/m` (a test manifest + service worker) on Android and iOS behind the gateway's login; whether the installed app keeps its own storage on iOS; WebAuthn in the installed app; a Web Push from oaap-test through Apple and Google; the rollback door; the size and time of computing the picture on oaapx01 | a table in this RFC |
| 1 | The picture (§2) for node and tenants; the PWA read-only (§3, Lage + Instanzen + Woche) for `server_admin` and `tenant_admin`, signed in with the normal login | Jörg sees oaap-test and oaapx01 on his phone; the picture's deviations are plausible for a week |
| 2 | Pairing and device sessions (§4), *Geräte* in the portal; push (§5) | a phone paired, separated, a matter arrives as push |
| 3 | Actions (§6) with the second confirmation, „Lage gesehen“; bound persons (RFC-0143) see their instances | maintenance on and off from the phone on oaap-test, the audit says `via: mobile` |
| 4 | Campaigns in the PWA (RFC-0144); the chat's reading tools (§7) | „Was war heute los?“ answered from the picture |

## 9. Non-goals

- A native app, an app store, an SDK.
- Administration on the phone (§6 „never“).
- New data collection: the picture joins what the node has.
- A second login system: pairing adds a device key to an existing person.

## 10. Decisions

*Decided by Jörg 2026-11-28 (the direction):*

- **P1 — PWA**, not a store app („Ja PWA“).
- **P2 — Time-critical actions belong on the phone**; Claude recommends
  which (§6, D6 below).
- **P3 — People are bound to instances with roles** (RFC-0143) and see
  their instances on the phone.
- **P4 — The short-link service belongs to the tenant and the platform
  knows it** (RFC-0144); campaigns appear in the picture by role.
- The order of §8 („Deine Empfehlungen passen“).

*Decided by Jörg 2026-11-28 („Ja, wie empfohlen“) — D1–D8 all as recommended:*

- **D1 — Where is the picture computed?** Recommended: **on the host, as a
  view file per scope** (§2) — the portal stays a reader, as for `space`
  and `upgrade`. Alternative: the portal computes on each request.
- **D2 — Pairing.** Recommended: **QR + short code from the portal,
  scanned in the installed app, passkey on the phone** (§4). Alternative:
  the normal login inside the app, then „remember this device“ — simpler,
  but a login on a small screen with the realm's full flow.
- **D3 — Session length on the phone.** Recommended: **8 hours, renewed
  silently with the device key; actions always confirmed again**.
- **D4 — Push for whom?** Recommended: **each person switches it on for
  themselves per type**; the tenant's routing decides what exists, the
  person what reaches their phone.
- **D5 — What does a push say?** Recommended: **the subject line only**
  (tenant, type, instance) — the vendor's service sees no detail.
  Alternative: no content at all („Neue Meldung“).
- **D6 — The actions.** Recommended: **the table of §6, and „never“ as
  listed.**
- **D7 — „Lage gesehen“.** Recommended: **yes** — an acknowledgement on an
  open matter, visible to everyone who received it, mailing nothing; it
  does not close the matter.
- **D8 — The PWA also at a tenant's own domain?** Recommended: **yes**
  (`/m` at the tenant's place), so a club's people install „their“ app,
  not the node's.

## 11. Stage 0, the server's half (2026-11-28, reference 0.1.405)

**The cost of the picture.** The files a run would read (per-instance
metrics, page statistics, site checks, the node's `apps/*.json`): oaap-test
134 files, 0.7 MB, read in 0.02 s; oaapx01 163 files, 1.0 MB, 0.01 s. Every
five minutes is no load — D1 holds.

**F1 — „Zurück zur vorigen Version“ exists for few instances.** The
request `rollback` reinstalls a *retained package* — only instances that
came as an artifact keep them. Production instances with an older
retained package: oaapx01 **7 of 50** (the other 42 came from Git or the
store), oaap-test 2 of 37. For a Git or store instance the previous image
is kept (`oaap-prev/<instance>:prev`, RFC-0128), but no request goes back
to it. The phone shows the button only where a way back exists; a way back
for Git and store instances (the previous version from the store, or the
kept image) is a gap of its own, to be closed before stage 3.

**The worker judges the role now** (RFC-0143 §9, F1, fixed in 0.1.405):
the actions of §6 are requests the worker itself refuses to anyone who is
not an administrator of the instance — the precondition for sending them
from a phone.

**Not measured — needs a phone (Jörg):** installing `/m` on iOS and
Android behind the gateway's login; whether the installed app on iOS keeps
its own storage (pairing inside the app, §4); a passkey created in the
installed app; a Web Push from oaap-test arriving through Apple and
Google. Stage 0 finishes with these; a test page on oaap-test is the next
step.

## Deutsche Zusammenfassung

**Worum es geht:** Wer für einen Server, einen Mandanten oder eine Webseite
zuständig ist, sitzt nicht immer am Rechner. Er soll Auffälliges sofort auf
dem Handy sehen und zeitkritisch reagieren können.

**Vorschlag:**
- **Ein Lagebild je Rolle**, auf dem Knoten berechnet: was jetzt auffällig
  ist (offene Lagen, rote Punkte, ausgefallene Instanzen), was anders ist
  als sonst (Zugriffe, 404, Auslastung, Kurzlink-Klicks gegen das
  Wochenmittel), was passiert ist (Aktionen der Woche) und was kommt
  (geplanter Neustart, Zertifikat). Dasselbe Lagebild speist die mobile
  Oberfläche, den Wochenbericht und später den Chat.
- **Eine PWA** unter `/m`, als Symbol auf dem Startbildschirm, Bildschirme
  Lage, Instanzen, Kampagnen, Woche. Sie zeigt nur, was die Rolle sehen
  darf: server_admin den Knoten, tenant_admin den Mandanten, gebundene
  Personen ihre Instanzen (RFC-0143).
- **Koppeln** im Portal per QR-Code; das Handy bekommt einen Passkey.
  Unter „Geräte“ lässt sich jedes Handy einzeln trennen.
- **Push** zusätzlich zur Mail, nur mit der Betreffzeile.
- **Zeitkritische Aktionen**, jede mit Fingerabdruck oder Face-ID bestätigt:
  Wartung an/aus, Anmeldung erzwingen, Neustart, Aufwecken, zurück zur
  vorigen Version, Test → Produktion, KI-Abrufer sperren, Jetzt prüfen,
  Kurzlink pausieren oder umleiten, geplanten Neustart verschieben, „Lage
  gesehen“. **Nie vom Handy:** Löschen, Benutzer und Rollen, Mandanten,
  Domains, Schlüssel, Server-Updates, Sicherungen.
- Das Handy bekommt **keine eigenen Rechte**: Jede Aktion ist der Auftrag,
  den das Portal heute schon schickt, und der Knoten prüft ihn erneut.
- **Chat** zuletzt: lesende Werkzeuge über das Lagebild; der Chat schlägt
  vor, der Mensch löst aus.

**Stufen:** 0 messen (PWA auf Android/iOS hinter der Anmeldung, Passkey,
Push über Apple/Google, Rückweg-Tür), 1 Lagebild und PWA nur lesend für
server_admin und tenant_admin, 2 Koppeln und Push, 3 Aktionen und
gebundene Personen, 4 Kampagnen und Chat.

**Entschieden (Jörg, 28.11.):** PWA; zeitkritische Aktionen aufs Handy;
Personen an Instanzen mit Rollen; Wegweiser im Mandanten, die Plattform
kennt ihn; Reihenfolge wie empfohlen. **Entschieden (Jörg, 28.11., „Ja, wie empfohlen“): D1–D8 wie empfohlen:**
Lagebild auf dem Host, Koppeln per QR + Passkey, 8 Stunden Sitzung, Push je
Person einschaltbar, Push nur mit Betreff, die Aktionsliste, „Lage gesehen“
ja, PWA auch an der Domain des Mandanten.

Stufe 0, Serverhälfte (28.11.): Das Lagebild liest je Lauf etwa 1 MB aus
rund 150 Dateien in 0,02 s — alle fünf Minuten keine Last. **Befund:**
„Zurück zur vorigen Version“ gibt es nur für Instanzen, die als Paket kamen
(oaapx01: 7 von 50 Produktivinstanzen); für Git- und Store-Instanzen liegt
zwar das vorige Abbild bereit, aber kein Auftrag führt dorthin — eine Lücke,
die vor Stufe 3 zu schließen ist. Der Worker prüft die Rolle jetzt selbst
(RFC-0143 F1). **Offen, braucht ein Handy:** PWA auf iOS/Android hinter der
Anmeldung, eigener Speicher der installierten App auf iOS, Passkey, Push
über Apple und Google.

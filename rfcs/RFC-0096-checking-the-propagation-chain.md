# RFC-0096: Checking the Propagation Chain — a Test Login Without a Person

- **Status:** **Accepted (2026-11-19)** — Jörg: "D1–D8 wie empfohlen".
  **Stage 1 built** (reference 0.1.312, spec `oaap.net.destinations` 0.14,
  2026-11-19), tested against a local TLS target; not yet measured against a4h
  (needs the user `OAAP_CHECK` there). Stage 2 (schedule) open.
- **Date:** 2026-11-19
- **Authors:** Jörg (the need: L23 of the bec landscape, 2026-11-18 — the
  certificate login into a4h depended on a parameter set only in RZ11;
  after a restart of a4h it was 0 and SAP answered 401, and the first to
  notice was a person in the chat), Claude (reading of connect and
  appctl, design)
- **Depends on:** `oaap.net.destinations` 0.13 (2.9 principal propagation,
  2.7.2 portal), RFC-0066 (propagation), RFC-0065 D8 (never a technical
  user instead of the person), RFC-0080 (distribution lists, for stage 2)
- **Not part of this RFC:** checking destinations of other kinds (bearer,
  basic — their check is "call it", a later generalisation); CA rollover
  (RFC-0066 §5)

## Summary

A principal propagation destination is a chain: the platform issues a
certificate of the tenant's CA → TLS reaches the target's ICM with the
pinned server certificate → the target trusts the CA (SAP: STRUST) →
a rule maps the certificate to a user (SAP: CERTRULE, and the profile
parameter `login/certificate_mapping_rulebased`) → the user exists and is
not locked. Today the only way to see that the chain holds is a real
person calling through a real app. A broken link is found by the people,
not by the operator.

This RFC adds a **chain test**: `oaap destination check <tenant>/<name>`
and a button "Kette prüfen" on the portal's destination row. It logs in to
the target **as a fixed, reserved test user** (`OAAP_CHECK`) with a
certificate of the tenant's own CA, makes **one GET** to a fixed check path,
and reports **which link holds and which breaks** — never the target's
answer itself. Stage 2 repeats it on a schedule and tells the tenant's
operators when the result changes.

## 1. Why not with a person

The test must not log in as Jörg or anyone else. A certificate for a
person may be issued only on a signed assertion of that person
(spec 2.9.4); the chain test has none, and must not fake one. So the test
user is **not a person**: a name reserved by the platform, the same on every
node, that the target's administrator creates **without any
authorisations**. Its only use is to prove "a certificate of this CA,
for this user name, gets through to a login".

This does not contradict RFC-0065 D8 ("never a technical user instead of
the person"): the check never carries an app's request and never stands in
for a person who cannot be carried. It is a separate path that apps cannot
reach (§3.1).

## 2. What the check reports

Each link is judged in order; the first that breaks ends the check.

| Link | Holds when | Breaks as | The doc's error picture |
|---|---|---|---|
| 1. Reach | TCP to host:port within 15 s | timeout / refused | target down, firewall |
| 2. Server certificate | presented certificate's SHA-256 = the pin | other fingerprint (shown) | STRUST renewed → compare and pin again |
| 3. CA trusted | the target accepts the client certificate in the handshake | TLS alert (certificate unknown / bad certificate) | STRUST: CA missing, wrong PSE, another tenant's CA |
| 4. Mapping | the answer is not 401 | 401 | RZ11/RZ10 `login/certificate_mapping_rulebased`, CERTRULE filter or issuer, user missing in this client |
| 5. User | 2xx, and — where the check path names the user — it is `OAAP_CHECK` | 403 / other user / 5xx (status shown) | user locked, path not active in SICF |

The result is one line per link (held / broke / not reached), the time, the
certificate's serial, and on a break the doc's sentence for it. The body of
the target's answer is read only as far as link 5 needs (the user name) and
is neither shown nor stored.

## 3. Design

### 3.1 Where it runs — inside connect, no new door

connect is the only service that holds the tenant's CA key. The check runs
there the same way the sample certificate already does
(`propagation_sample`): appctl runs a short script in the connect container
with `docker exec`. **connect gets no new HTTP route** — an app on an
instance network cannot reach the check at all, so the test user can never
be borrowed for an app's call.

The script issues the certificate (`propagate.issue`, lifetime 1 minute,
not put in the certificate cache), builds the same client context as a real
call (`propagate.client_context` with the pinned server certificate), makes
the GET with no cookies, no reuse, no redirects, and prints a small JSON
result. The key never leaves the process.

### 3.2 The certificate

`O=OAAP, OU=<tenant label>, CN=OAAP_CHECK` — the same subject form as a
person's, so the target's existing rule (filter on `OU`, `O`; CN = user)
maps it with no extra rule. Instead of a person's UUID it carries the SAN
URI `urn:oaap:check`, so the target's own security log shows that this was
the platform's test, not a person.

### 3.3 The check path

Stored per destination as `auth.check_path`, a GET path below the target.
Default for `name_check: sap`: `/sap/bc/ui2/start_up?sap-client=<client>`
— it answers JSON with the logged-on user (`id`), which link 5 compares.
For other targets the path is optional; without one, link 5 judges the
status only. Set when the destination is made (portal step 2, CLI
`--check-path`) and changeable like the secret.

### 3.4 Audit

Every check: `destination.propagation.check` with tenant, destination, who
started it (or "schedule"), the serial, and the result line — the same
place as every issued certificate (spec 2.9.9).

### 3.5 Stage 2: on a schedule

Daily, and once a few minutes after the node starts, for every
propagation destination that has a check path. The last result is kept with
the destination and shown in the list ("Kette: in Ordnung, heute 06:00" /
"Kette: bricht bei Zuordnung (401) seit 06:00"). A **change** of the result
(holds → breaks, breaks → holds) is sent to the tenant's operators through
the distribution list of RFC-0080; an unchanged result sends nothing.

## 4. Decisions

- **D1 — a reserved test user, never a person.** The check logs in as
  `OAAP_CHECK`, fixed by the platform, not chosen per destination or per
  call. *Recommended.* Alternative: a name chosen per destination — more
  flexible, but whoever may set it can name any SAP user (e.g. an
  administrator), and the check would log in as them.
- **D2 — the name.** `OAAP_CHECK` (10 characters, fits SAP's 12, says
  what it is). *Recommended.*
- **D3 — inside connect via `docker exec`, no new HTTP route** (§3.1).
  *Recommended.* Alternative: an internal route in connect — reachable from
  the platform network, one more door to guard.
- **D4 — one GET to a stored check path, the answer not shown.**
  *Recommended.* Alternative: show the answer — more diagnosis, but a
  request result of a backend would then be shown on a platform page.
- **D5 — who may start it:** `server_admin` (CLI and portal) and the
  tenant's `tenant_admin` (portal), the same people who see the
  destination's pin and load the CA (2.7.2). *Recommended* — the result
  says nothing a tenant_admin could not learn from SAP's own log.
- **D6 — stage 1 on demand, stage 2 on a schedule** with a message only on
  a change of the result. *Recommended.*
- **D7 — the SAN `urn:oaap:check`** instead of a person's UUID (§3.2).
  *Recommended.*
- **D8 — no check path, no scheduled check**: a destination without
  `check_path` is checked on demand up to link 4 and is left out of the
  schedule. *Recommended.*

## 5. Stages

1. **On demand** (reference, spec `oaap.net.destinations` 0.14):
   `auth.check_path`, `oaap destination check`, the portal button, audit.
   Measured against a4h with a user `OAAP_CHECK` created there.
2. **Scheduled** (reference): daily and after start, the result in the
   list, message on change.

## 6. Open questions to measure

- Which SAP user type `OAAP_CHECK` needs for a certificate login over
  HTTP without a dialog (expected: type "Service" or "System"; measure on
  a4h) — the doc names the measured one.
- Whether `/sap/bc/ui2/start_up` answers 200 for a user without any role
  (expected yes; otherwise link 5 counts 403 as "mapping holds, user
  logged in" and the doc says so).
- How the TLS alert of a rejected client certificate shows in Python's
  `ssl` module against SAP's ICM (link 3 must tell it apart from link 2 and
  from a timeout).

## Tests (described)

1. `check` on a propagation destination whose target is down → link 1
   breaks, nothing else is tried, audit line written.
2. The target presents another certificate than the pin → link 2 breaks,
   the new fingerprint is shown, no client certificate was issued.
3. The target does not trust the CA → link 3 breaks.
4. The target answers 401 → link 4 breaks with the RZ10/CERTRULE sentence.
5. The target answers 200 with `id` = `OAAP_CHECK` → all five hold.
6. 200 with another user in `id` → link 5 breaks ("the target mapped the
   certificate to another user").
7. The issued certificate has `CN=OAAP_CHECK`, `OU=<tenant label>`, SAN
   `urn:oaap:check`, lifetime ≤ 1 minute, and is not in the certificate
   cache afterwards.
8. connect has no HTTP route that issues a certificate without an
   assertion (the route list is unchanged).
9. The target's answer body does not appear in the result, the audit line
   or the portal page.
10. A `tenant_admin` of another tenant cannot start the check; a `user`
    cannot.
11. (Stage 2) Two scheduled checks with the same result send nothing; a
    change sends one message to the tenant's operators.

## Deutsche Zusammenfassung

**Problem (L23):** Ob die Kette einer Destination „Person durchreichen“
hält, sieht man heute nur, wenn eine echte Person über eine echte App
aufruft. Als a4h nach einem Neustart den nur in RZ11 gesetzten Parameter
verloren hatte, merkte es zuerst eine Person im Chat (401).

**Vorschlag:** ein **Kettentest** — `oaap destination check <mandant>/<name>`
und ein Knopf „Kette prüfen“ in der Liste der Destinationen. Er meldet sich
am Ziel als **fester, reservierter Prüfbenutzer `OAAP_CHECK`** an (nie als
eine Person, nie mit einer gefälschten Zusicherung), mit einem Zertifikat
der CA des Mandanten, macht **einen GET** auf einen festen Prüfpfad (SAP:
`/sap/bc/ui2/start_up`) und sagt, **welches Glied hält und welches
bricht**: erreichbar → Serverzertifikat = Pin → CA vertraut (STRUST) →
Zuordnung (kein 401: RZ10/CERTRULE) → Benutzer stimmt. Die Antwort des
Ziels wird nicht gezeigt.

**Sicherheit:** Der Test läuft in connect (dort liegt der CA-Schlüssel) per
`docker exec`, wie heute schon das Musterzertifikat — **keine neue Tür**,
eine App kann den Prüfbenutzer nicht ausleihen. Der Benutzer `OAAP_CHECK`
wird im SAP-System **ohne jede Berechtigung** angelegt; die bestehende
CERTRULE-Regel (Filter OU, O; CN = Benutzer) ordnet ihn ohne neue Regel zu.
Das Zertifikat trägt `urn:oaap:check` statt einer Personen-UUID, damit SAPs
Protokoll den Test erkennt. Jeder Test steht im Audit.

**Stufen:** 1. auf Knopfdruck (Spec 0.14); 2. täglich und nach dem Start
des Knotens, mit Nachricht an die Betreiber des Mandanten **nur bei einer
Änderung** des Ergebnisses (RFC-0080).

**Entscheidungen D1–D8**, alle mit Empfehlung: fester Name statt frei
wählbar (D1, D2), in connect ohne neue Route (D3), Antwort nicht zeigen
(D4), server_admin und tenant_admin dürfen (D5), erst Knopf, dann Zeitplan
(D6), SAN `urn:oaap:check` (D7), ohne Prüfpfad kein Zeitplan (D8).

**Zu messen an a4h:** welcher Benutzertyp (Service/System) die
Zertifikatsanmeldung ohne Dialog kann; ob `start_up` einem Benutzer ohne
Rolle 200 gibt; wie Python einen abgelehnten Client-Zertifikat-Handshake
von einem falschen Pin und einem Timeout unterscheidet.

**Was du in a4h tun müsstest:** den Benutzer `OAAP_CHECK` ohne Rollen
anlegen (und RZ10, das ohnehin offen ist).

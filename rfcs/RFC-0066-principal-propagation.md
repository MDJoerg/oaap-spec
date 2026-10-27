# RFC-0066: Principal Propagation Through Destinations — The Signed-In Person Arrives at the Backend as Themselves

- **Status:** **Accepted (2026-10-27)** — Jörg took D1–D6 and D8 as
  recommended; **D7 changed** to *measure first, then choose* (§10).
  Q1–Q3 answered (§11): a4h runs on the internet, client 001, Jörg may
  configure much but **may not restart**; demo users follow later.
  Phase A reworked accordingly (§8). **Phase A0 measured from outside
  the same day (§8.1): TLS ends at the ICM, which asks for a client
  certificate → x509 first.** **Phase A measured the same day with a
  hand-made CA: certificate `CN=ACCX_T_DEV` → logged on as ACCX_T_DEV
  without password; unknown user → 401; foreign CA → handshake
  aborted; no restart needed** (§8.1). Nothing built.
- **Date:** 2026-10-27
- **Authors:** Claude (analysis & proposal), Jörg (requirement, decides)
- **Depends on:** RFC-0033 (destinations and connector — §1.4 named
  principal propagation as the retrofit case, waiting for real use
  cases), RFC-0040 (user identity, the UUID), RFC-0041 (Keycloak as an
  app, the tenant as the place of sign-in), RFC-0042 (the tenant as a
  place), RFC-0064 §4.1 / `oaap.ai.gateway` §4.1 (credentials encrypted
  under a key outside the app's storage)
- **Consumers:** RFC-0065 (MCP gateway, procedure P); CAP apps on OAAP
  calling ABAP OData as the user (`oaap-lab/cap-spike` is the
  precedent); any app with a destination to SAP
- **Changes:** `oaap.net.destinations` — a new `auth.type`
  `principal_propagation`; `oaap.core.identity` — a user assertion for
  apps on the way out; a per-tenant **issuer**

## Summary

RFC-0033 gave apps destinations: the platform adds the credential, the
app never holds it. It deliberately left one case open — *the logged-in
person arriving at the backend as themselves* — until a real use case
came. Two arrived on 2026-10-27: the MCP gateway (RFC-0065) must reach
an MCP server inside ABAP as the person at the client, and CAP apps on
OAAP should call ABAP OData personalised.

Both need what the **SAP Cloud Connector** does on BTP: the cloud side
knows the user from a token; the connector issues a **short-lived X.509
certificate** for that user; SAP trusts the connector's CA and maps the
certificate to a SAP user. This RFC makes that a platform function,
reached through an ordinary destination.

The decisive point from RFC-0065 §6.1 carries over: **neither Keycloak
nor Entra reliably issues a credential SAP accepts** (Keycloak's token
exchange does not produce SAML; Entra does so only on its old v1
endpoint, with reported defects). So:

> **The IdP authenticates the person. The platform issues the backend
> credential.** The path is the same for Keycloak and Entra.

## 1. The requirement (Jörg, 2026-10-27)

- The token exchange known from the SAP Cloud Connector, available on
  OAAP.
- Needed beyond MCP: **perspectively in the IdP or other platform
  functions** — keyword CAP apps calling ABAP OData personalised.
- The SAP user name: **one IdP attribute `sap_user`, used by n
  connected systems**. Maintaining names per system elsewhere costs too
  much and needs several people and roles.
- The trust is set up **per SAP system and per tenant**.
- Built and measured **together on a4h**, Claude guiding, as the demo
  landscape.

## 2. Where it lives: the destination, not the IdP

Two homes were possible:

| Home | For | Against |
|---|---|---|
| **In the IdP** (a Keycloak extension that issues certificates or SAML) | "the IdP does identity" | Java extension inside a product we run but do not own; **does nothing for Entra**; every tenant's Keycloak would carry SAP knowledge |
| **In the destination** (the platform's outgoing proxy) | already holds the credential on the app's behalf (RFC-0033 D1); already knows *which app* calls (by network); IdP-agnostic | the proxy must learn *which user* the call is for — §3 |

**Decided (D1): the destination.** It is the BTP model Jörg
knows — *destination with authentication `PrincipalPropagation`, proxy
type on-premise* — and it keeps the IdP a pure identity product, which
is what lets Entra replace Keycloak without touching SAP.

## 3. How the proxy learns the user — without trusting the app

The danger is obvious: if an app could simply *say* "this call is for
MÜLLER", every app could act as anyone. The proxy therefore accepts
only **proof the app cannot forge**, in one of two forms:

### 3.1 Form A — platform assertion (apps behind the platform login)

Most OAAP apps never see a token: the platform signs the person in and
passes headers (RFC-0040). For them, the platform adds one more header
on every incoming request of a signed-in person:

```
X-OAAP-User-Assertion: <compact JWS>
```

- signed by the **node**, lifetime **5 minutes**;
- claims: user UUID, tenant, the attributes the tenant marked as
  propagatable (here `sap_user`), and the **audience = this instance**.

The app copies the header onto its call to the destination. The proxy
checks signature and lifetime and that **the audience equals the
instance the call comes from** — which the proxy knows from the network
(RFC-0033 §1.3), not from anything the app says. An assertion leaked
from app A is therefore useless to app B.

### 3.2 Form B — the user's IdP token (apps that sign people in themselves)

The MCP gateway (RFC-0065 §5.1) and an app with its own OIDC hold the
person's access token from the tenant's IdP. They send it as

```
X-OAAP-User-Token: <access token>
```

The proxy validates it against the **tenant's** issuer (Keycloak now,
Entra later), and requires its audience or authorized party to be the
**calling instance's** client. Same principle: proof plus the network.

### 3.3 Who may propagate at all

Acting on behalf of users toward SAP is a strong right. A binding of an
instance to a destination with `principal_propagation` is a **separate
grant** (D3), shown as such on both object pages, given by the
`tenant_admin` and audited. A plain binding to the same destination
does not include it.

## 4. The destination

```json
{ "name": "a4h",
  "kind": "http",
  "target": { "direct": "https://a4h.example:50001/" },
  "auth": {
    "type": "principal_propagation",
    "issuer": "tenant",                  // the tenant's issuer, §5
    "credential": "x509",                // x509 | saml2_bearer (stage 3)
    "user": [                            // ordered rules, first hit wins
      { "rule": "claim", "name": "sap_user" },
      { "rule": "claim", "name": "sap_user_a4h" }
    ],
    "name_check": "sap",                 // 12 chars, upper case
    "lifetime_minutes": 10
  } }
```

- **User rules** (RFC-0065 §7, normative here): `claim` (default:
  `sap_user`), `derive` (e.g. local part of `email`, upper case),
  `table` (exception), `sap` (the certificate carries the UUID or
  e-mail and `CERTRULE` maps it — the basis team keeps the mapping).
  The normal case is the first: **one attribute, n systems**; a
  per-system attribute (`sap_user_<SID>`) is only for people whose
  name differs in one system.
- **No hit → refused** with a readable reason; **never** a fallback to a
  technical credential (RFC-0065 D8).
- The proxy is the **TLS client toward SAP** and presents the
  certificate; the app speaks plain HTTP to the proxy as with every
  `kind: http` destination. For a `via` target the TLS connection runs
  through the tunnel unopened (§6, stage 2).

## 5. The issuer

- **One issuer per tenant** (Jörg: per tenant and per SAP system): a CA
  key pair, created on demand, stored encrypted like every credential
  (the key never in plain text, never readable back).
- **Per SAP system** the trust is set up once: the tenant's CA
  certificate goes into that system's `STRUST`, a rule into
  `CERTRULE`. A system trusting tenant A's issuer cannot be reached with
  tenant B's users — that is the tenant border, enforced by SAP itself.
- The CA certificate (public part) is downloadable from the tenant's
  destination page, with a short checklist for the basis team (§8).
- Issued certificates: `CN=<SAP user>`, plus the user UUID in a
  separate attribute for the audit trail on the SAP side; lifetime
  minutes; cached per user and destination for TLS reuse, never longer
  than its lifetime.
- **Audit:** every issue (time, destination, instance, user UUID, SAP
  name, serial). Never the request or response.
- Rotation: a new CA is added next to the old one, both trusted in
  `STRUST` for a transition, then the old one removed — the procedure
  is written down before the first CA expires.

## 6. Where the issuer sits when SAP is inside a company

With a `via` target (RFC-0033 connector inside the company network), two
placements are possible:

- **on the node** (stage 1–2): the CA key is on the OAAP node; the
  certificate travels through the tunnel inside TLS;
- **in the connector** (later): the CA key never leaves the company —
  what the SAP Cloud Connector does, and what a security department may
  require.

This RFC builds the first and names the second, because the a4h demo
needs only the first, and the second wants a real customer's security
department to say so.

## 7. CAP apps

A CAP app on OAAP reaches ABAP OData through the destination's URL
(`OAAP_DESTINATION_A4H_URL`) and must pass on Form A or B. What is not
yet measured and therefore not promised: how CAP's own destination
handling (`forwardAuthToken`, SAP Cloud SDK) is best pointed at the
proxy and made to carry `X-OAAP-User-Assertion`. A stage of its own
(stage 4), after the mechanism stands.

## 8. The demo scenario on a4h — built together

Jörg sets up the SAP side with Claude's guidance; every phase ends with
a measurement before the next starts. **Phase A needs no OAAP code**:
it proves that a4h trusts a CA we control, using a hand-made
certificate.

**Constraints since 2026-10-27:** a4h runs **on the internet**, client
001; Jörg may configure much but **may not restart** the system or the
ICM. Therefore phase A is split: first look without touching anything
(A0), then change only what takes effect without a restart, and name
everything else as a request to whoever may restart.

| Phase | What | Measured by |
|---|---|---|
| **A0 — look, touch nothing** | from outside: does a4h's HTTPS port **ask for a client certificate**, and is it SAP's ICM that answers, or something in front of it (load balancer, Web Dispatcher, cloud proxy)? From inside (read only): `RZ11` values of `icm/HTTPS/verify_client`, `icm/server_port_*`, `login/certificate_mapping_rulebased`; `SMICM` services; `SOAUTH2` / `SAML2` present? | `openssl s_client -connect <host>:<port>` — a *CertificateRequest* with SAP-looking CA names means the certificate path is open; no request, or a non-SAP server certificate, means TLS ends before SAP → **SAML bearer first** (D7) |
| **A — SAP trusts a certificate** (if A0 says the path is open) | a4h: HTTPS port requests a client certificate (`icm/server_port_<n>` with `VCLIENT=1`); `login/certificate_mapping_rulebased = 1`; a test CA (openssl, by hand) imported into `STRUST`, SSL server PSE; a `CERTRULE` rule *subject CN → user ID*; two test users | `curl --cert` with a hand-made certificate `CN=<user>` against a service that reports the logged-on user (candidate: `/sap/bc/ui2/start_up` — to be checked on a4h); two certificates → two different users; a certificate from a foreign CA → refused |
| **B — Keycloak knows the SAP user** | in the demo tenant's realm: attribute `sap_user` declared in the user profile, maintained for the two test persons; a mapper puts it into the token | a token for a test person shows `sap_user` |
| **C — the platform issues** | stage 1 built: issuer per tenant, destination type `principal_propagation`, Form A; the hand-made CA from phase A replaced by the tenant's CA in `STRUST` | a small test app behind the platform login calls the destination; two people signed in → two SAP users in the answer; a third person without `sap_user` → readable refusal; app without the propagation grant → refused |
| **D — MCP gateway** | RFC-0065 stage 4 with Form B | an MCP client signed in at Keycloak calls `whoami` in an ABAP MCP handler → `SY-UNAME` is the person |
| **E — CAP** | stage 4 below | a CAP service reads ABAP OData as the signed-in person |

### 8.1 Phase A0 measured from outside (2026-10-27)

a4h is `demo.brandeis.de:50001` (194.164.48.224), system **A4H**,
client 001. Measured from Jörg's workstation with `openssl s_client`
and three unauthenticated `curl` requests — nothing changed on the
system:

- **TLS ends at SAP's ICM itself.** The server certificate is the ABAP
  default (`O=SAP Trust Community, OU=SAP Web AS, OU=IDEMOSYSTEM,
  CN=*.dummy.nodomain`, self-signed), and the answer to an empty
  request is an error page "generated by ICM". No load balancer or
  Web Dispatcher in front.
- **The ICM asks for a client certificate** (*CertificateRequest*,
  optional). The list of acceptable CA names contains only the
  system's own certificate — i.e. the SSL server PSE trusts nothing
  else yet. That is exactly the place our CA goes (`STRUST`, phase A).
- `/sap/bc/ui2/start_up?sap-client=001` exists and answers `401` with
  `Basic realm="SAP NetWeaver Application Server [A4H/001]"`;
  `/sap/public/info` and `/sap/bc/ping` are deactivated (`403`).

**Consequence for D7: the certificate path is open — x509 first**, SAML
bearer as the following stage. Not yet known: whether importing into
the SSL server PSE takes effect without an ICM restart, and whether
rule-based mapping is switched on (phase A, read from inside first).

**Read from inside by Jörg (2026-10-27, nothing changed):**

- `login/certificate_mapping_rulebased` = **0** (kernel default),
  **dynamic, system-wide** → can be switched to 1 in `RZ11` without a
  restart; lost at the next restart unless also entered in the default
  profile (`RZ10`, takes effect at that restart).
- `icm/HTTPS/verify_client` = **1** (kernel default: request, not
  require), not dynamic — and needs no change.
- `icm/server_port_*` not found in `RZ11` (indexed parameter; the ports
  are visible in `SMICM` → services). Not needed: A0 already showed
  50001 requesting a certificate.
- `STRUST`, SSL server standard: certificate list empty (matches A0).
- `CERTRULE` opens; no rules yet.
- `SICF` `/sap/bc/ui2/start_up`: logon procedure *standard*, which
  includes the client certificate.

**Phase A, step 2 measured (2026-10-27): a CA added to the SSL server
PSE takes effect without an ICM restart.** Jörg imported a hand-made
demo CA (`CN=OAAP Demo Aussteller pxx`, RSA 2048, kept outside every
repository) into the certificate list of the SSL server standard PSE
and saved; minutes later, without any restart, the ICM listed it among
the acceptable client CA names next to its own certificate. A call
with a certificate `CN=MUSTER` from that CA completes the TLS handshake
and gets `401` with the Basic challenge — the expected baseline while
rule-based mapping is still off and no rule exists.

**Phase A measured (2026-10-27): a4h logs a person on by a certificate
from our CA, without password and without restart.** Jörg set
`login/certificate_mapping_rulebased = 1` in `RZ11` (dynamic, all
servers) and created one `CERTRULE` rule from the sample `CN=MUSTER`:
entry *subject*, attribute *CN*, log on as *user name*, **subject
filter `OU,O,C`** — the rule only applies to certificates whose
`OU`, `O` and `C` equal the sample's (`OU=Mandant pxx, O=OAAP Demo,
C=DE`). Then, against `/sap/bc/ui2/start_up?sap-client=001`:

| Certificate | Answer |
|---|---|
| `CN=ACCX_T_DEV` from the demo CA | **`200`, user `ACCX_T_DEV`, client 001** — no password |
| `CN=MUSTER` from the demo CA (user does not exist) | `401` with the Basic challenge |
| `CN=ACCX_T_DEV` from a **foreign** CA | **TLS handshake aborted** by the ICM (`certificate unknown`) — never reaches the logon |

Second round the same day, two more users Jörg named:

| Certificate | Answer |
|---|---|
| `CN=ACCX_T_MON1` | **`200`, user `ACCX_T_MON1`** — a second person, a second answer |
| `CN=ACCX_T_LOCKE` (user **locked** in SAP) | `401`, page "Anmeldung fehlgeschlagen" — identical to the non-existent `MUSTER` |
| `CN=ACCX_T_DEV` again | `200`, `ACCX_T_DEV` |

So **SAP keeps its own say**: a valid certificate from a trusted issuer
does not override a lock in `SU01`. The platform issues *who*, SAP
decides *whether* — which is the division this RFC wants. Toward the
caller SAP does not say *why* (locked and unknown look the same); the
proxy therefore cannot tell them apart either and must report a `401`
from the backend as "the backend refused this user", never guess a
reason. **Phase A is complete.**

**Finding for the design (§5): the subject filter is the tenant
border inside SAP.** A tenant's issuer writes the tenant into the
subject (`OU=<tenant>`), and the rule in `CERTRULE` filters on it. A
certificate issued for another tenant — even by a CA the system also
trusts — falls under no rule of this tenant. So the platform MUST put
the tenant into the subject of every issued certificate, fixed, never
taken from the app or the user.

Note for the probe: Windows `curl` (Schannel) cannot load PEM client
certificates; the measurement uses a small Python client on OpenSSL,
which also needs a lowered security level for a4h's 1024-bit key.

**Finding for the build:** the server key is **RSA 1024 bit** under
TLS 1.2; OpenSSL refuses it at its default security level ("EE
certificate key too weak"). The proxy must **pin** the destination's
server certificate (stored with the destination) and accept a weak key
only for a pinned certificate — never by switching verification off.
The destination page shows the weakness as a warning.

## 9. Stages

| Stage | Content |
|---|---|
| **0** | phase A and B by hand on a4h and in Keycloak — no code |
| **1** | issuer per tenant, `principal_propagation` with x509 for `direct` targets, Form A, separate grant, audit, CA download with checklist |
| **2** | Form B (IdP token); `via` targets through the connector |
| **3** | `saml2_bearer` for systems with SAP OAuth; Entra as issuer of Form B tokens |
| **4** | CAP integration, measured |
| later | issuer inside the connector (§6) |

## 10. Decisions

| # | Proposal | Recommendation |
|---|---|---|
| **D1** | Propagation lives in the **destination**, not in the IdP | yes (§2) |
| **D2** | The platform issues the backend credential; the IdP only authenticates | yes — the only path equal for Keycloak and Entra |
| **D3** | Propagation is a **separate grant** per binding | yes |
| **D4** | Proof from the app: Form A (platform assertion, audience = instance) and Form B (IdP token, audience = instance's client); never a bare user name | yes |
| **D5** | One issuer per tenant; trust per SAP system in `STRUST` | yes |
| **D6** | User name: rule list, default one claim `sap_user` for n systems | yes (Jörg, Q4) |
| **D7** | x509 first, SAML bearer later | yes |
| **D8** | Issuer on the node first, in the connector later | yes |

**Decided (Jörg, 2026-10-27, by form):** D1–D6 and D8 as recommended.
**D7 changed:** *measure first, then choose.* Phase A0 (§8) decides
whether x509 or SAML bearer is built first; the other follows. Reason:
a4h runs on the internet, and a TLS endpoint in front of SAP would
swallow the client certificate.

Still to measure, not to assume (for the case of no restart): whether
importing a CA into the SSL server PSE in `STRUST` takes effect
without an ICM restart, and whether `login/certificate_mapping_rulebased`
can be switched dynamically in `RZ11`. If either needs a restart, it
becomes a request to the a4h operator — or the reason to take SAML
first.

## 11. Questions to Jörg

Answers of 2026-10-27:

- **Q1:** a4h runs **on the internet** → `direct` target, no connector.
- **Q2:** client **001**; demo users Jörg creates, not immediately.
- **Q3:** Jörg may configure much, but **may not restart** → §8 A0.

The original questions:

- **Q1 — a4h:** where does it run, and which release? Does the OAAP node
  that will host the issuer reach its HTTPS port directly (LAN), or
  only through a connector?
- **Q2 — demo tenant:** which tenant and which Keycloak (`auth` on
  `oaap-test`, port 8113)? Which two test persons?
- **Q3 — basis rights on a4h:** do you have `RZ10`/`SMICM`, `STRUST`,
  `CERTRULE` and `SU01` there, i.e. may the instance profile be
  changed and the ICM restarted?

## Deutsche Zusammenfassung

**Worum es geht:** Der Token-Tausch, den du vom **SAP Cloud Connector**
kennst, wird eine Funktion der Plattform. Die Cloud-Seite kennt den
Benutzer; der Connector stellt ein **Zertifikat mit Minuten-Laufzeit**
aus; SAP vertraut der Zertifizierungsstelle des Connectors und ordnet
das Zertifikat per `CERTRULE` dem SAP-Benutzer zu. Abnehmer sind das
MCP-Gateway (RFC-0065) und CAP-Apps auf OAAP, die ABAP-OData
personalisiert aufrufen.

**Wo es hingehört:** in die **Destination** (RFC-0033), nicht in den
IdP. Das RFC-0033 hatte genau diesen Fall offen gelassen, „bis echte
Usecases kommen" — jetzt sind zwei da. Eine Keycloak-Erweiterung würde
für Entra nichts bringen und SAP-Wissen in jeden Mandanten-Keycloak
tragen. So bleibt die Arbeitsteilung sauber: **Der IdP sagt, wer jemand
ist. Die Plattform stellt den SAP-Nachweis aus.** Das ist das
BTP-Modell: Destination mit Authentifizierung `PrincipalPropagation`.

**Der Sicherheitskern:** Eine App darf nicht einfach *behaupten* „dieser
Aufruf ist für MÜLLER". Der Proxy nimmt deshalb nur einen Nachweis an,
den die App nicht fälschen kann:
- **Form A:** Die Plattform gibt einer App bei jeder Anfrage einer
  angemeldeten Person eine **unterschriebene Zusicherung** mit
  (5 Minuten gültig, adressiert an genau diese Instanz).
- **Form B:** Apps mit eigener Anmeldung (wie das MCP-Gateway) reichen
  das **Keycloak-Token** der Person weiter.

In beiden Fällen prüft der Proxy zusätzlich, dass der Nachweis an die
Instanz adressiert ist, von der der Aufruf **über das Netz** kommt. Ein
abgegriffener Nachweis nützt einer anderen App nichts. Und: Im Namen von
Benutzern handeln darf eine App nur mit einer **eigenen Freigabe** des
Mandanten-Admins.

**SAP-Benutzer:** wie von dir gewünscht ein Attribut `sap_user` im IdP
für n Systeme; Ausnahmen über weitere Regeln (Attribut je System,
Ableitung aus der E-Mail, Tabelle, oder Zuordnung in SAP selbst).
Findet keine Regel einen Namen, wird abgelehnt — nie ein technischer
Benutzer.

**Vertrauen:** eine Zertifizierungsstelle **je Mandant**; **je
SAP-System** wird sie einmal in `STRUST` eingespielt und eine Regel in
`CERTRULE` angelegt. Ein System, das Mandant A vertraut, ist mit
Benutzern von Mandant B nicht erreichbar — die Mandantengrenze setzt SAP
selbst durch.

**Der gemeinsame Aufbau auf a4h** (§8), Phase für Phase, jede mit einer
Messung:
- **A:** a4h vertraut einem von Hand gebauten Zertifikat. Das braucht
  noch keinen OAAP-Code; geprüft wird mit `curl`, ob zwei Zertifikate
  zwei verschiedene SAP-Benutzer ergeben.
- **B:** Keycloak kennt `sap_user`.
- **C:** Die Plattform stellt die Zertifikate selbst aus.
- **D:** das MCP-Gateway.
- **E:** CAP.

**Entschieden 27.10. (Formular):** D1–D6 und D8 wie empfohlen. D7
geändert: **erst messen, dann wählen.** a4h läuft im Internet,
Mandant 001, du darfst viel einstellen, aber nicht neu starten. Deshalb
beginnt der Aufbau mit **Phase A0**: von außen nachsehen, ob a4h
überhaupt ein Client-Zertifikat anfordert, und von innen die
Profilwerte nur lesen. Kommt das Zertifikat bis zum ICM durch, bauen wir
zuerst den Zertifikatsweg. Endet TLS vorher (Load Balancer, Web
Dispatcher), kommt zuerst der SAML-Weg über den OAuth-Server von SAP —
der braucht weder Neustart noch durchgehendes TLS. Was doch einen
Neustart verlangt, wird eine Bitte an den, der a4h betreibt.

**A0 von außen gemessen (27.10., §8.1):** a4h ist
`demo.brandeis.de:50001`, System A4H, Mandant 001. Die TLS-Verbindung
endet **direkt im ICM** (SAP-Standardzertifikat, Fehlerseite „generated
by ICM"), und der ICM **fordert ein Client-Zertifikat an**. Bisher
vertraut er dabei nur seinem eigenen Zertifikat — dort kommt unsere
Zertifizierungsstelle hinein. **Damit ist der Zertifikatsweg offen und
kommt zuerst**, SAML danach. `/sap/bc/ui2/start_up` antwortet mit der
Anmeldeaufforderung. Befund fürs Bauen: Das Serverzertifikat hat nur
1024 Bit; der Proxy muss es fest hinterlegen (pinnen), statt die
Prüfung abzuschalten.

**Phase A gemessen (27.10.), ohne Neustart:** Demo-Zertifizierungsstelle
in `STRUST` übernommen (der ICM nennt sie sofort als Aussteller),
Schalter in `RZ11` auf 1, eine Regel in `CERTRULE` (Subjekt, CN →
Benutzername, Inhaberfilter `OU,O,C`). Ergebnis: Ein Zertifikat
`CN=ACCX_T_DEV` meldet a4h **ohne Passwort als ACCX_T_DEV** an;
`CN=MUSTER` (gibt es nicht) → 401; derselbe Name von einer fremden
Zertifizierungsstelle → der ICM bricht schon den TLS-Aufbau ab. Der
**Inhaberfilter ist die Mandantengrenze in SAP**: Die Plattform muss
den Mandanten fest in den Inhaber jedes Zertifikats schreiben.

**Zweite Runde:** `ACCX_T_MON1` → angemeldet als ACCX_T_MON1 (zweite
Person, zweite Antwort); der **gesperrte** `ACCX_T_LOCKE` → 401, genau
wie ein unbekannter Benutzer. SAP behält also das letzte Wort: Ein
gültiges Zertifikat hebelt keine Sperre aus. Die Plattform sagt *wer*,
SAP entscheidet *ob*. **Phase A ist abgeschlossen.**

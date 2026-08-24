# oaap.ai.gateway — AI Supply Behind One Keyed Endpoint

- **ID:** `oaap.ai.gateway`
- **Version:** 0.2 (the traffic light of §7 replaces the geographic
  classification of 0.1 — breaking, and free: nothing is installed yet)
- **Maturity:** draft
- **Based on:** RFC-0023 (supply, placement, entitlement); RFC-0022
  (account and tenant); RFC-0002 (default deny); RFC-0010 (public
  route brake); RFC-0019 (token hygiene: shown once, stored hashed,
  revocable); RFC-0021 (fleet key precedent for machine endpoints)

## Purpose

A gateway offers **one OpenAI-compatible endpoint** downstream and
draws from one or more **suppliers** upstream: a local model runtime,
an external provider, or **another gateway**. It exists so that a
consumer — an app, a tenant, a laptop — asks for a *purpose*
(`chat-default`, `code`, `embedding-default`) and never for a vendor,
a model name or a URL.

Everything else in this document follows from that one property.
Rerouting, failover, data-protection routing and metering are all only
possible because the consumer does not name the model.

## 1. The route

An AI gateway is an ordinary OAAP app instance. Its API route is
declared `roles: [public]`, which means: the platform authenticates
nothing and strips client-sent identity headers; the app authorizes
every request itself (RFC-0002). The platform's per-client brake of
RFC-0010 applies and is charged **once per request**, so a streamed
answer is charged at setup, not per token.

| Method | Path                   | Purpose                                                       |
| ------ | ---------------------- | ------------------------------------------------------------- |
| `GET`  | `/v1/models`           | the **aliases** this key may use — never upstream model names |
| `POST` | `/v1/chat/completions` | completion, streaming and non-streaming                       |
| `POST` | `/v1/embeddings`       | embeddings                                                    |
| `GET`  | `/healthz`             | liveness, no key required, says nothing about suppliers       |

`GET /v1/models` returning aliases is what makes an off-the-shelf
client (LM Studio, an IDE plugin, a library) usable without adaptation:
the user picks `chat-default` from a list and never learns which
supplier served it.

A gateway **has no session, no cookie and no roles**, and it does not
consult the platform's identity service. It is a machine endpoint —
the third of the family named in RFC-0023 §3, alongside the deploy
hook (writes) and the fleet status (reads).

## 2. The API key is the identity

> For AI consumption, the identity is the **API key** — not the OAAP
> user, not the tenant.

- **Whoever operates a gateway issues its keys.** A right is given, not
  held (RFC-0019). A gateway that draws from an upstream holds exactly
  **one** key there, of its own; that key never reaches a consumer.
- The key value is shown **exactly once** at issue time; only its
  SHA-256 digest is stored. Listing shows labels and metadata, never
  key material.
- Every key carries **metadata**: label, responsible person, cost
  centre or project, and its account/tenant assignment — `default`
  where RFC-0022 stage 2 has not been reached. Metadata exists to make
  usage filterable and billable, and is free text to the operator.
- A key may be **restricted to a subset of aliases**.
- A key carries a **budget** and a **rate limit**. These are hard: they
  protect against a runaway bill, which an invoice afterwards does not.
- A key carries the **worst light it may use** and a **release for
  personal data** (§7). Both are decided when the key is issued.
- Issue and revoke are **audited**; requests are metered (§5) but their
  content is never recorded (§6).
- Every failure of authorization answers the **same 403 without
  detail**. Repeated failures are braked per client address.

## 3. Aliases, and failover inside a declared group

An **alias** names a purpose and maps to one or more suppliers. The
mapping is the operator's configuration, not the consumer's business.

- **Failover happens only inside an equivalence group declared by an
  administrator.** LLMs are not interchangeable the way web servers
  behind a load balancer are; silent substitution changes behaviour,
  sometimes subtly enough that nobody notices for weeks.
- A switch is **visible in the telemetry**: which supplier actually
  served a request is recorded per request and shown to the consumer
  who made it.
- A request naming something that is not an alias of this key is
  refused with the list of aliases it may use — a wrong model name is
  a configuration mistake, and configuration mistakes deserve an
  answer that fixes them.

## 4. Suppliers, and chains

A supplier is **an OpenAI-compatible HTTP endpoint plus a
credential** — that is the entire model. A local runtime, an external
provider, a customer's own endpoint and another gateway are the same
kind of thing; they differ in address, credential and light (§7), not
in code. There is deliberately **no adapter framework** in this
version: a plugin architecture built before its second real case is a
guess wearing an interface.

A chain is therefore not a special construction either: **a gateway
has an upstream side and a downstream side, and an upstream may be
another gateway.**

A chain **proxies; it does not refer** (RFC-0023 A1). Traffic passes
through every layer, because every layer logs the access and meters
the consumption, and a layer that does not see the traffic can do
neither. Consequences, all accepted deliberately:

- latency adds up, and every layer is a point of failure for
  everything below it — therefore **chain length is the consumer's
  own trade-off**: keep it short, or host the supply yourself;
- **binding a gateway is never compulsory.** An external inferencing
  service is an equally legitimate supply for a tenant, and the
  platform is not on the path to it.

Upstream credentials live in the gateway's secret configuration and
**never leave it** — not in an error message, not in telemetry, not in
a response header.

## 5. Metering: each gateway keeps its own books

> Each gateway keeps the books for **the keys it issued**. An
> upstream's numbers are the upstream's truth and are not reconciled
> automatically.

Anything else invites silent double counting across three layers. A
tenant sees what its keys consumed; the node operator sees what the
tenant's gateway consumed from them; the two need not agree to the
token, and pretending they must would cost more than it is worth.

Recorded per request: time, key, alias, **supplier actually used**,
input and output token counts, latency, an optional cost estimate, and
the outcome. Where a supplier reports no token counts, the record says
so rather than guessing.

**Every consumer sees their own consumption, and only their own.** With
RFC-0022 in place, usage rolls up tenant → account, which is the view
RFC-0022 §7 measures.

## 6. What a gateway must never record

**No prompt content, and no completion content, in any log — ever.**
Telemetry counts; the audit log records who routed where and when.
Prompts are the most sensitive payload this platform will ever carry,
and a log that holds them turns every backup and every support case
into a disclosure risk.

This is a conformance requirement, not a recommendation.

## 7. The traffic light: what a supplier does to your data

Every supplier carries a **light**. It does not describe quality,
speed or price — it describes **what can happen to the data you send**:

| light    | what it means                                                             | what may be sent                                                              |
| -------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `green`  | the data does not leave the organisation — the model runs on its own hardware | anything the consumer is otherwise allowed to hold; personal data **with an explicit release** |
| `yellow` | the data may leave the organisation, but to a provider under a binding commitment (contract, EU data centre, no training on the data) | company information; personal data **with an explicit release**                |
| `red`    | an external provider — the data can flow away                              | **no company information, no personal data** — public or synthetic input only  |

The light replaces a purely geographic classification on purpose:
where a machine stands is the *reason* for a light, never its
*meaning*. What an operator needs to decide is not "is this in the
EU?" but "what happens to my data here?"

### The light is enforced on declarations, never on content

The gateway **cannot see what a request contains** — §6 forbids it to
look, and that rule is not negotiable. Therefore the light can only be
enforced against **properties the consumer declared in advance**:

- every key carries the **worst light it may use** (default `yellow`,
  so `red` is a deliberate extra permission);
- every key carries a **release for personal data**, granted by
  whoever issued the key.

From those two the rule follows that the platform can actually keep:
**a key released for personal data may never use `red`.** Not because
red is forbidden in principle, but because we cannot tell one request
from another — and a rule that depends on the gateway recognising
personal data would be a promise it cannot keep.

Everything beyond that stays where it belongs: with the person who
sends the prompt. The platform is honest about the difference between
what it *enforces* and what it *documents*.

### A chain may only ever get more dangerous

> A declared light is a **ceiling, never a floor**. What a gateway
> offers downstream can never be greener than the worst link in the
> path it will actually use.

This is the rule that keeps a chain honest, and it is the reason the
light exists in both directions:

- **downstream**, `GET /v1/models` reports for every alias the light
  the *requesting key* would actually get — the worst light among the
  candidates that key may reach. An alias that can fail over from a
  green model to a red provider is **not green**;
- **upstream**, a gateway that draws from another gateway **reads that
  gateway's declared light and may not improve it**. Configuring
  `green` for a supplier that reports `red` does not make it green; the
  worse of the two wins.

Without this, a gateway becomes a laundry: put one in front of an
external provider, label it `green`, and every consumer downstream is
lied to by construction. The rule costs nothing and closes that.

### What the consumer must be able to see

The consumer must be able to see **the light of the alias it is using
and the supplier that actually served a request** (`GET /v1/usage`). A
policy the customer cannot verify is a promise, not a control.

Within an equivalence group a gateway prefers `green` before `yellow`
before `red`, and an operator who wants otherwise says so explicitly.
**Sovereignty is thus what happens when nobody configures anything** —
which is the only form of it that survives daily use.

## 8. Errors

| Situation                          | Answer                                                            |
| ---------------------------------- | ----------------------------------------------------------------- |
| missing, unknown, revoked key      | `403`, no detail, braked                                          |
| alias not permitted for this key   | `400` with the permitted aliases                                  |
| rate limit hit                     | `429` with `Retry-After`                                          |
| budget exhausted                   | `429` **without** `Retry-After` — waiting does not help, only a new budget |
| no supplier in the group available | `503`, naming the alias, never the upstream credential            |
| upstream failed                    | `502`, with the supplier's own status where it is safe to pass on |

## 9. Conformance tests

1. A request without a key, with an unknown key and with a revoked key
   receive the identical 403.
2. A key restricted to `chat-default` is refused `code`, and the
   refusal lists what it may use.
3. `GET /v1/models` returns aliases only; no upstream model name and
   no supplier name appears in the response.
4. A streamed answer is charged once by the RFC-0010 brake.
5. Budget exhaustion answers 429 and does **not** reach the supplier.
6. A failover inside a declared group is recorded with the supplier
   actually used; a failover to a light the consumer forbids does not
   happen.
6a. `GET /v1/models` reports for each alias the worst light the
   requesting key would actually reach — an alias that may fail over
   to `red` is not reported as `green`.
6b. A key released for personal data is refused every `red` supplier,
   even when its own ceiling says `red`.
6c. A supplier configured `green` that reports `red` upstream is
   treated as `red`; the worse of the two wins.
7. No log file produced by the gateway contains prompt or completion
   text, in any operating mode.
8. An upstream credential appears in no response, no error and no
   telemetry record.
9. Key issue and revoke appear in the audit log; individual requests
   do not.
10. A gateway drawing from another gateway holds exactly one key
    there; that key never appears downstream.

## 10. Dependencies

- `oaap.apps.runtime` — the gateway is an app instance with a public
  route, declared configuration and declared mounts;
- `oaap.core.gateway` — default deny and the RFC-0010 brake;
- RFC-0022 stage 2 for account/tenant metadata on keys. Until then the
  assignment reads `default`, which is a real value, not a placeholder
  to be filled in later by hand.

## Non-goals (version 0.1)

- No training, no fine-tuning, no model management beyond aliases.
- No cost reconciliation across layers (§5).
- No prompt content anywhere (§6).
- No automatic failover outside a declared equivalence group (§3).
- No entitlement derived from an OAAP session — the key is the
  identity (§2).

## Zusammenfassung auf Deutsch

Ein KI-Gateway bietet **einen OpenAI-kompatiblen Endpunkt** an und
bedient sich bei einer oder mehreren **Bezugsquellen**: lokales
Modell, externer Anbieter oder **ein anderes Gateway**. Der Verbraucher
fragt nach einem **Zweck** (`chat-default`, `code`) und nie nach einem
Hersteller, Modellnamen oder einer URL. Alles Weitere folgt daraus:
Umleiten, Ausweichen, Datenschutz-Routing und Abrechnung sind nur
möglich, weil der Verbraucher das Modell nicht benennt.

**Technisch ist es eine gewöhnliche OAAP-App** mit einer `public`-Route
— die Plattform authentifiziert nichts, entfernt gefälschte
Identitäts-Kopfzeilen und bremst je Client (RFC-0010, einmal pro
Anfrage, Streaming also unbelastet). Die App prüft selbst: **Der
API-Key ist die Identität**, keine Sitzung, keine Rollen, kein Kontakt
zum Identitätsdienst. Damit ist das Gateway der dritte Vertreter der
Maschinen-Endpunkt-Familie neben Deploy-Hook und Flotten-Auskunft.

`GET /v1/models` liefert **die Aliasse**, nicht die Modellnamen der
Quelle — genau das macht LM Studio oder ein IDE-Plugin ohne Anpassung
benutzbar: Man wählt `chat-default` aus einer Liste und erfährt nie,
wer geantwortet hat.

**Schlüssel:** ausgestellt von dem, der das Gateway betreibt, einmal
angezeigt, nur als SHA-256 gespeichert, jederzeit widerrufbar; mit
Metadaten (Verantwortlicher, Kostenstelle, Account/Mandant — bis
RFC-0022 Stufe 2 schlicht `default`), optional auf einzelne Aliasse
beschränkt, mit **Budget und Rate-Limit als harter Grenze**. Ein
Gateway, das sich bei einem anderen bedient, hält dort **genau einen
eigenen** Schlüssel, der nie nach unten durchgereicht wird.

**Die Ampel (§7) sagt, was mit den Daten geschehen kann** — nicht, wo
ein Rechner steht: **grün** die Daten verlassen das Unternehmen nicht;
**gelb** sie verlassen es vielleicht, aber zu einem Anbieter unter
verbindlicher Zusage; **rot** externer Anbieter, Daten können
abfließen — keine Unternehmensinformationen, keine personenbezogenen
Daten. Der Standort ist der *Grund* für eine Farbe, nie ihre
*Bedeutung*.

**Durchgesetzt wird an Erklärungen, nie am Inhalt.** Das Gateway darf
nicht hineinsehen (§6), also kann es nur prüfen, was vorher erklärt
wurde: je Schlüssel die **schlechteste erlaubte Farbe** (voreingestellt
gelb, rot ist Zusatzerlaubnis) und eine **Freigabe für personenbezogene
Daten**. Daraus folgt die eine Regel, die die Plattform wirklich halten
kann: **Ein für personenbezogene Daten freigegebener Schlüssel darf
niemals rot benutzen.** Alles Weitere bleibt bei dem, der den Prompt
abschickt — und die Spec ist ehrlich über den Unterschied zwischen dem,
was sie *durchsetzt*, und dem, was sie *dokumentiert*.

**Eine Kette kann nur gefährlicher werden, nie ungefährlicher.** Eine
erklärte Farbe ist eine **Obergrenze, nie eine Untergrenze**: Was ein
Gateway nach unten anbietet, kann nie grüner sein als das schlechteste
Glied der Kette, die es tatsächlich benutzt. Deshalb wirkt die Ampel in
beide Richtungen — nach unten meldet `GET /v1/models` je Alias die
Farbe, die *dieser Schlüssel* wirklich bekäme (ein Alias, der von einem
grünen Modell auf einen roten Anbieter ausweichen kann, ist nicht
grün), und nach oben liest ein Gateway die Farbe seiner Bezugsquelle
und darf sie **nicht verbessern**. Ohne diese Regel wird ein Gateway
zur Wäscherei: eins davorstellen, `grün` dranschreiben, und alle
darunter sind von Bauart wegen belogen.

**Souveränität ist die Standard-Reihenfolge, kein bloßer Filter:**
Innerhalb einer Ausweich-Gruppe gilt grün vor gelb vor rot — wer es
anders will, sagt es ausdrücklich. Souveränität ist damit das, was
passiert, wenn niemand etwas einstellt; jede andere Form überlebt den
Alltag nicht. Eine Bezugsquelle ist dabei **immer dasselbe**: ein
OpenAI-kompatibler Endpunkt plus Zugangsdaten — lokal, extern, beim
Kunden oder ein anderes Gateway. Einen Adapter-Baukasten gibt es
bewusst nicht, solange wir den zweiten echten Fall nicht kennen.

**Ausweichen nur innerhalb einer erklärten Gruppe** — LLMs sind nicht
austauschbar wie Webserver hinter einem Lastverteiler; stilles
Ersetzen ändert das Verhalten, manchmal so leise, dass es wochenlang
niemand merkt. Welche Quelle tatsächlich geantwortet hat, steht in der
Telemetrie und ist für den Verbraucher sichtbar.

**Abrechnung:** Jedes Gateway führt Buch über die Schlüssel, die es
selbst ausgegeben hat; die Zahlen der Bezugsquelle sind deren Wahrheit
und werden nicht abgeglichen. Alles andere lädt zu stiller
Doppelzählung über drei Schichten ein.

**Und die härteste Regel:** In keinem Protokoll stehen jemals Prompts
oder Antworten. Gezählt wird, nicht mitgeschrieben — sonst wird jede
Sicherung und jeder Supportfall zum Datenleck. Das ist eine
Konformitätsbedingung, keine Empfehlung.

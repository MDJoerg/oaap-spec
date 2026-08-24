# oaap.ai.gateway — AI Supply Behind One Keyed Endpoint

- **ID:** `oaap.ai.gateway`
- **Version:** 0.1 (first specification; nothing implemented yet)
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

A supplier is a local runtime, an external provider, or another
gateway. There is no third case, and a chain is not a special
construction: **a gateway has an upstream side and a downstream side,
and an upstream may be another gateway.**

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

## 7. Data classification is a routing policy

Each supplier carries a **class** (`internal`, `eu`, `external`). A
consumer — a tenant, or a key — declares which classes it may use.
Failover respects that boundary; a route the policy forbids does not
exist for that consumer, and no fallback may cross the line silently.

The consumer must be able to **see which supplier currently serves an
alias**. A policy the customer cannot verify is a promise, not a
control.

## 8. Errors

| Situation                          | Answer                                                            |
| ---------------------------------- | ----------------------------------------------------------------- |
| missing, unknown, revoked key      | `403`, no detail, braked                                          |
| alias not permitted for this key   | `400` with the permitted aliases                                  |
| budget exhausted or rate limit hit | `429` with `Retry-After`                                          |
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
   actually used; a failover to a class the consumer forbids does not
   happen.
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

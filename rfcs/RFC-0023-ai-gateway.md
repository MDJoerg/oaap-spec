# RFC-0023: The AI Gateway — Supply, Placement, Entitlement

- **Status:** Draft — sorting the concept, decisions open (2026-08-24)
- **Date:** 2026-08-24
- **Authors:** Claude (analysis & proposal), Jörg (requirements &
  decisions)
- **Depends on:** RFC-0011 (node profiles), RFC-0015 (non-HTTP /
  machine endpoints), RFC-0019 (deploy hook — the bearer-token
  precedent), RFC-0021 (fleet status, management node), RFC-0022
  (account and tenant)
- **Driver:** Jörg wants to run this on `oaapx01` as a mix of local
  Ollama models and external inferencing providers, later including the
  hosting partner's services, with usage monitoring and API-key
  administration — and to use the same gateway from his laptop as a
  replacement for LM Studio. The requirement catalogue has been in the
  idea store since 2026-08-23; this RFC's job is to **sort** it before
  anything is built.

## Why this document exists

Jörg's description (2026-08-24) contains at least four different
gateways: one on a node, one inside a tenant, one account-wide across
tenants, and one on dedicated hardware serving the management node. All
four are right. They read as a tangle only because three independent
questions are being answered at once.

Separated, they stop competing:

| Dimension | Question | Answers |
| --- | --- | --- |
| **Supply** | Where does capacity come from? | local models (Ollama), external provider (IONOS, Telekom, a hyperscaler), the hosting partner, **another gateway** |
| **Placement** | Where does the gateway component run? | any node, the management node, a dedicated AI node on special hardware |
| **Entitlement** | Who may consume, and how is it counted? | an API key — which *may* belong to a tenant, and need not |

Every statement Jörg made is a point in that space, not a variant of a
single design. The rest of this RFC follows the three dimensions.

## 1. Supply: a gateway has an upstream and a downstream

A gateway offers **one OpenAI-compatible API** downstream and draws
from one or more **suppliers** upstream. A supplier is a local model
runtime, an external provider — or **another gateway**.

That single sentence is the whole chaining story:

```text
AI node (2 GPUs, Ollama)  ─┐
external provider (EU)    ─┼─→  gateway on the management node
partner's service         ─┘         │
                                     ├─→ gateway on node oaapx01 ─→ apps
                                     ├─→ gateway of account "Meier" ─→ its tenants
                                     └─→ Jörg's laptop (API key, no tenant)
```

**Model aliases by purpose, never model names** — `chat-default`,
`code`, `embedding-default`. This was already the single most important
point in the requirement catalogue and it is what makes every other
feature possible: rerouting, failover, and the data-protection policy
below all depend on the consumer *not* naming a specific model.

**Failover only inside equivalence groups declared by an
administrator.** LLMs are not interchangeable the way web servers
behind a load balancer are; silent substitution changes behaviour.
Switching is automatic, but only within a declared group, and it is
visible in the telemetry.

## 2. Placement: a gateway is a service on a node, and one node may specialise

A gateway is an ordinary OAAP service. What differs is where it sits:

- **on a normal node** — the common case: the operator runs it, the
  node's apps consume it;
- **inside a tenant** — when a `tenant_admin` wants their own (RFC-0022
  gives them that right); its upstream is usually the node's gateway;
- **account-wide** — one gateway for all tenants of an account; lives
  where the account lives, i.e. on the management node (RFC-0022 Q1);
- **on a dedicated AI node** — special hardware (Jörg's contact is
  building one from a retired gaming PC with two GPUs). This is a
  **node profile** in the sense of RFC-0011, alongside `dev` and
  `exposed` — proposed name `ai`. It offers its gateway upstream and
  runs no customer apps.

### The management node gains a data path

RFC-0021 built the management node as a **strictly read-only observer**
of the fleet. Passing AI capacity from an AI node on to other nodes and
tenants makes it, for the first time, something traffic flows
*through*.

This is a deliberate extension and needs saying plainly, because it
looks like a contradiction and is not: RFC-0021's rule is that no node
accepts **control** from outside. A relayed inference request is a
**data path** — it changes nothing on the receiving node, spends no
right, and installs nothing. The prohibition on a cross-node *write*
path stands untouched.

## 3. Entitlement: the API key is the identity

This is the point that makes Jörg's laptop work, and it deserves to be
stated as a rule:

> **For AI consumption, the identity is the API key — not the OAAP
> user, not the tenant.**

Consequences, all of them intended:

- A consumer **need not be modelled** as an account or tenant. Jörg's
  laptop gets a key and is done; the key lives in the default tenant,
  and everything else runs on key metadata. Replacing local LM Studio
  is then a configuration line, not an integration project.
- A key **may** belong to a tenant. Then its usage rolls up: tenant →
  account, exactly the view RFC-0022 §7 measures.
- **Whoever operates a gateway issues its keys** — the same "a right is
  given, not held" pattern as the deploy token (RFC-0019). A gateway
  that draws from an upstream holds *one* key there, of its own.
- **Every consumer sees their own consumption**, and only their own.

### This endpoint is the third of a family we already have

| | Auth | Session | Purpose |
| --- | --- | --- | --- |
| Deploy hook (RFC-0019) | bearer token | none | write: deploy an artifact |
| Fleet status (RFC-0021) | fleet key | none | read: node status |
| **AI gateway** (this RFC) | **API key** | **none** | **use: inference** |

All three are **machine endpoints**: bearer-authenticated, no cookie,
throttled per client, revocable, with issue and revoke audited. Naming
the family matters, because someone will otherwise ask whether the AI
gateway breaks the contract rule that *an app never builds its own
login*. It does not: that rule governs **frontend apps serving humans**
through the gateway. This is not one.

### Key metadata, budgets, and where the books are kept

From the requirement catalogue, unchanged: key metadata for filtering
and billing (cost centre, project, account, tenant, responsible user),
plus **budgets and hard rate limits on the key** — protection against a
runaway bill, not just an invoice afterwards.

The metering rule for chains, which is where this usually goes wrong:

> **Each gateway keeps the books for the keys it issued.** An upstream's
> numbers are the upstream's truth and are not reconciled
> automatically.

Anything else invites silent double counting across three layers. A
tenant sees what its keys consumed; the node operator sees what the
tenant's gateway consumed from them; the two need not match to the
token, and pretending they must would cost more than it is worth.

## 4. Data protection is a routing policy

The catalogue's **data classification per route** (`internal` /
`EU provider` / `external`) is what turns "our data must not go to a US
provider" from a sales promise into a configuration. A tenant declares
which classes its data may use; failover then respects that boundary,
and a route the policy forbids simply does not exist for that tenant.

Two additions:

- **The tenant must be able to see which supplier currently serves an
  alias.** A policy the customer cannot verify is a promise, not a
  control.
- **Telemetry and audit stay separate.** Telemetry counts (tokens,
  latency, cost) for dashboards and billing. The audit log records who
  routed where and when — **never prompt content**. The idea store
  already drew this line for partner tracing; it holds here for the
  same reason, and more strongly: prompts are the most sensitive
  payload the platform will ever carry.

## Decisions to make (Jörg)

**A1 — Does a chain proxy, or refer?** Chaining as described means each
layer holds its own keys in both directions, so traffic **flows
through** every layer. That is simple and consistent, and it is what
makes central metering possible — but it makes each layer a bottleneck
and adds latency to a streaming response. The alternative ("referral":
the upstream's address plus a short-lived key handed to the consumer,
who then connects directly) is faster and cannot keep the books.
*Recommendation: proxy in stage 1, referral only if a real latency
problem appears.*

**A2 — What happens when the management node is down?** If Jörg's
laptop consumes through it, an outage there takes away his local
alternative to LM Studio. *Recommendation: allow a consumer to hold
keys at more than one gateway* — the laptop keeps a direct key at the
AI node as a fallback. Cheap, and it removes a single point of failure
from a convenience feature.

**A3 — `ai` as a node profile (RFC-0011)?** *Recommendation: yes* — it
is exactly what profiles are for, and it lets a node say "I run models,
I host no customer apps".

**A4 — Which comes first: the gateway, or a second tenant?** Jörg is
weighing whether to pull the AI gateway forward as the real scenario
for RFC-0022 stage 3, against making BDT multi-tenant. Worth noting:
the gateway exercises **accounts, keys, metering and the management
node** but barely touches tenant isolation; BDT exercises **isolation**
and barely touches metering. They test different halves.

**A5 — Reference implementation.** The catalogue names LiteLLM as a
candidate, and the capability stays tool-neutral as always.
*Recommendation: confirm LiteLLM as the reference and keep the spec
free of it* — same relationship as Docker to ADR-0004.

## Non-goals (stage 1)

- No training, no fine-tuning, no model management beyond aliases.
- No cost reconciliation across layers (§3).
- No prompt content in any log, ever.
- No automatic failover outside a declared equivalence group.

## Zusammenfassung auf Deutsch

Jörgs Beschreibung enthält mindestens vier Gateways — am Knoten, im
Mandanten, account-weit und auf eigener Hardware. **Alle vier sind
richtig**; sie wirken nur verworren, weil drei unabhängige Fragen
gleichzeitig beantwortet werden. Getrennt lösen sie sich auf:

1. **Herkunft** — woher kommt die Leistung? Lokale Modelle (Ollama),
   externe Anbieter, der Hosting-Partner, **oder ein anderes Gateway**.
2. **Ort** — wo läuft die Komponente? Auf einem gewöhnlichen Knoten, im
   Mandanten, account-weit auf dem Management-Knoten, oder auf einem
   **KI-Knoten** mit besonderer Hardware (neues Knotenprofil `ai`).
3. **Berechtigung** — wer darf verbrauchen, und wie wird gezählt? Über
   einen **API-Key**, der zu einem Mandanten gehören *kann*, aber nicht
   muss.

Daraus folgt die Verkettung von selbst: Ein Gateway hat eine
Bezugsseite und eine Abgabeseite, und ein Bezug darf ein anderes
Gateway sein. Damit ist Jörgs Kette KI-Knoten → Management-Knoten →
Knoten/Mandant genau ein Fall dieser einen Regel.

Der Satz, der Jörgs Laptop erklärt: **Für den KI-Verbrauch ist der
API-Key die Identität** — nicht der OAAP-Benutzer, nicht der Mandant.
Deshalb muss ein Verbraucher gar nicht als Account oder Mandant
gepflegt sein; der Schlüssel liegt im Default-Mandanten, alles Weitere
läuft über Key-Metadaten. Damit ist der Ersatz für lokales LM Studio
eine Konfigurationszeile.

Zwei Einordnungen, damit später niemand einen Widerspruch vermutet:
Der Management-Knoten bekommt hier zum ersten Mal einen **Datenpfad**
(RFC-0021 verbietet einen Steuerkanal — ein durchgereichter
Inferencing-Aufruf ändert auf dem Zielknoten nichts, das Verbot steht
unberührt). Und das Gateway ist der **dritte Vertreter einer Familie,
die es schon gibt**: Deploy-Hook (schreibend), Flotten-Auskunft
(lesend), KI-Gateway (nutzend) — alle drei Maschinen-Endpunkte mit
Bearer-Token, ohne Sitzung, gebremst und widerrufbar. Die Vertragsregel
„eine App baut nie einen Login" gilt für Oberflächen-Apps und ist hier
nicht berührt.

Abrechnungsregel für Ketten: **Jedes Gateway führt Buch über die
Schlüssel, die es selbst ausgegeben hat.** Die Zahlen der Bezugsquelle
sind deren Wahrheit und werden nicht automatisch abgeglichen — alles
andere lädt zu stiller Doppelzählung über drei Schichten ein.

**Fünf Entscheidungen liegen bei Jörg** (A1–A5): durchreichen oder
vermitteln; was gilt, wenn der Management-Knoten ausfällt; `ai` als
Knotenprofil; ob das Gateway oder ein zweiter Mandant der erste reale
Fall wird (beide prüfen verschiedene Hälften — das Gateway Accounts,
Schlüssel und Messung, BDT die Mandanten-Trennung); und LiteLLM als
Referenz-Implementierung.

# RFC-0023: The AI Gateway — Supply, Placement, Entitlement

- **Status:** Accepted (2026-08-24) — the sorting stands; A1 and A4
  decided, A2/A3/A5 are open detail decisions that block nothing
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

### Every layer is a real hop (decision A1)

A chain **proxies**; it does not refer. Traffic flows through every
layer, every layer logs the access and meters the consumption, and a
consumer's key is always a key of the layer they are talking to — never
a key handed down from further up.

Jörg's reasoning, which is now the rule: a `tenant_admin` who binds our
gateway as their supply **knows what they are taking on**, and nothing
compels them — an external inferencing service is an equally legitimate
supply, and we are not on the path to it. Performance therefore becomes
a question of **how long the chain is**: keep it short, or host the
supply yourself. That is a trade-off we make visible, not a cost we
hide.

The price is accepted deliberately: latency adds up, and each layer is
a point of failure for everything below it. What is bought with it is
that every layer can answer *"what did this key consume?"* without
asking anyone else — which is the reason the chain exists at all.

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

## Decisions (Jörg, 2026-08-24)

- **A1 — a chain proxies, it does not refer.** Decided against the
  caveats: every layer logs and meters, so the traffic has to pass
  through it (§1). Chain length is the consumer's own performance
  trade-off, and our gateway is never compulsory.
- **A4 — the AI gateway goes first**, ahead of a second tenant. It is
  immediately useful in Jörg's daily work, which BDT-multi-tenant would
  not have been — and Jörg named the stronger reason: **BDT runs in
  public mode with no authentication at all**, so making it
  multi-tenant would have exercised isolation on an app that has no
  login to isolate. The tenant with authentication becomes real with
  the **CRM application**, which is also the intended first source for
  the digital twin (RFC-0022 §5).

This re-orders RFC-0022's staging: the gateway is stage 5 there and now
overtakes stages 3 and 4. It can, because of §3 — stage 1 of the
gateway needs no tenant isolation whatsoever. The identity is the key.

### Still open — none of them blocks the start

- **A2 — fallback when the management node is down.** Recommendation
  unchanged: let a consumer hold keys at more than one gateway, so the
  laptop keeps a direct key at the AI node. Becomes real only once Jörg
  actually consumes through the management node.
- **A3 — `ai` as a node profile (RFC-0011).** Recommendation: yes.
  Decide when the first dedicated hardware exists.
- **A5 — LiteLLM as the reference implementation**, spec staying
  tool-neutral. Decide at the start of stage 2 below — it is the first
  question that stage asks.

## Staging

1. **RFC-0022 stage 2** — account- and tenant-aware plumbing, invisible
   to everyone. A key has to hang somewhere; this is that somewhere.
   Already decided (RFC-0022 Q4), independent of everything here.
2. **One gateway on `oaapx01`** — aliases over local Ollama plus one
   external provider, keys with metadata, per-key metering, a usage
   view. First consumer: Jörg's laptop, replacing LM Studio.
3. **Chaining** — a second gateway draws from the first, each keeping
   its own books (§3). This is where A1 is proved.
4. **Tenant-facing** — a tenant's own gateway, data-classification
   routing (§4), consumption visible to the tenant. Needs RFC-0022
   stage 3.

RFC-0022 stages 3 and 4 (`tenant_admin`, federated login) leave this
RFC's critical path and return with the CRM application.

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

**Zwei Entscheidungen sind getroffen** (2026-08-24):

**A1 — die Kette reicht durch.** Jeder Layer protokolliert Zugriffe und
misst Verbräuche, also muss der Verkehr durch ihn hindurch. Wer unser
Gateway als Bezugsquelle anbindet, weiß, was er in Kauf nimmt — und ist
zu nichts gezwungen: Ein externer Inferencing-Dienst ist eine genauso
legitime Bezugsquelle, und dort liegen wir nicht im Weg. Performance
wird damit zur Frage der **Kettenlänge**: kurz halten oder selbst
hosten. Der Preis ist bewusst genommen (Latenz summiert sich, jede
Schicht ist ein Ausfallpunkt für alles darunter); dafür kann jede
Schicht ohne Rückfrage sagen, was ein Schlüssel verbraucht hat.

**A4 — das KI-Gateway kommt vor dem zweiten Mandanten.** Es ist sofort
im Alltag einsetzbar; BDT wäre das nicht gewesen. Jörgs Argument ist
dabei stärker als meine Fragestellung: **BDT läuft im public-Modus ganz
ohne Authentifizierung** — BDT mehrmandantenfähig zu machen hätte also
Trennung an einer App geübt, die gar keinen Login hat, den man trennen
könnte. Der Mandant mit Anmeldung wird mit der **CRM-Anwendung** real,
auf die auch der digitale Zwilling aufsetzt. Das überholt in RFC-0022
die Stufen 3 und 4 — möglich, weil Stufe 1 des Gateways keinerlei
Mandanten-Trennung braucht: Die Identität ist der Schlüssel.

**Offen, aber nicht im Weg** (A2/A3/A5): Verhalten bei Ausfall des
Management-Knotens (Empfehlung: ein Verbraucher darf Schlüssel an
mehreren Gateways halten), `ai` als Knotenprofil (Empfehlung: ja, wenn
die erste Hardware da ist) und LiteLLM als Referenz — letzteres ist die
erste Frage der Bau-Stufe 2.

**Reihenfolge:** RFC-0022 Stufe 2 (Account/Mandant unsichtbar) → ein
Gateway auf `oaapx01` mit Aliassen, Schlüsseln und Verbrauchssicht
(erster Verbraucher: Jörgs Laptop statt LM Studio) → Verkettung →
mandantenseitig.

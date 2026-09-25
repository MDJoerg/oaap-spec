# oaap.net.destinations — Reaching Outward Without Holding the Key

- **ID:** `oaap.net.destinations`
- **Version:** 0.2
- **Maturity:** draft (0.1 was RFC-0033 stage 1: destinations with
  `direct` targets, bindings as grants, the HTTP proxy and the TCP
  handover, no bindings in a rehearsal. 0.2 adds stage 2's `via`
  targets — HTTP through a tunnel, `oaap.net.connector` 0.1. Exposures
  are stage 3 and named as the frontier, not specified)
- **Based on:** RFC-0033 (§1, D1, D5), RFC-0016 (instance networks, the
  shape a binding copies from app-to-app links), RFC-0015 (declaration
  is not publication), RFC-0022 / `oaap.core.tenant` (a destination
  belongs to exactly one tenant), RFC-0030 / `oaap.apps.runtime` 2.15
  (a rehearsal reaches nothing outward)

## 1. Purpose

An app that calls somebody else's system (an ERP, a webhook receiver,
a mail server) today carries that system's credential in its own
environment, in the clear, and in every backup. And the instance
decides for itself where it may call.

A **destination** is a named target that belongs to a tenant. The
operator **binds** an instance to it. For HTTP the app calls a local
address, and the platform adds the authentication and forwards the
call. **The app never holds the credential** (RFC-0033 D1).

What the app knows is a name (`erp`). What the operator maintains is
an object (`meier-erp-prod`, target, credential). The binding joins
the two, and the operator can revoke it.

## 2. Interface

### 2.1 The destination object

A destination belongs to **exactly one tenant** and is unique by name
within it. Fields:

| field | meaning |
| --- | --- |
| `name` | `[a-z0-9][a-z0-9-]{0,38}[a-z0-9]`, unique per tenant |
| `kind` | `http` or `tcp` |
| `target` | `{direct: <address>}`, or `{via: "<tunnel>/<offer>"}` for an HTTP destination reached through a tunnel this node accepts (0.2, `oaap.net.connector` 2.5) |
| `auth` | `none`, `basic` (user + secret), `bearer` (secret), `header` (header name + secret); for `tcp` only `none` and `basic` |
| `created`, `created_by`, `changed` | who and when, as everywhere |

- **A `direct` HTTP target** is an absolute `http://` or `https://`
  URL with a host, an optional port and an optional base path. It has
  no user info, no query and no fragment. **A `direct` TCP target** is
  `tcp://<host>:<port>`.
- **The target MUST NOT name the platform itself.** The gateway, which
  performs the call, sits on the platform network and on every instance
  network (`oaap.apps.runtime` 2.11). A target that names a container
  or service there would turn the proxy into a way around the gateway's
  own login and around the isolation of other tenants' apps. The
  implementation MUST refuse at least: a host without a dot (container
  and compose service names), `localhost` and loopback addresses,
  link-local addresses, and any literal address inside a network
  the container runtime currently manages. §4 names what this check
  cannot cover.
- **The secret is not part of the object.** It lives in a store that
  no container mounts (2.5). The object records only *whether* a
  secret is set.
- **Removing a destination that still has bindings is refused**, and
  the refusal names the instances. Removing it would otherwise cut a
  running app off without anybody having decided to cut that app off.

### 2.2 Binding is a grant, declaring is a need

- **Default: no destination.** An instance reaches no destination
  through the platform until an operator binds one.
- A binding joins **one instance** to **one destination of the same
  tenant** under a **need name**, which defaults to the destination's
  name (`--as` chooses another). An instance cannot be bound to a
  destination of another tenant; the refusal is the one
  `oaap.core.tenant` 2.3 prescribes for an object that does not exist.
- Bindings are recorded in the instance's registry record, **survive a
  redeploy** like visibility and address do, are shown with the
  instance, and are revocable. Binding and unbinding are written to the
  tenant's audit log.
- **The manifest may declare needs** (manifest 0.5, section
  `destinations`):

  ```yaml
  destinations:
    - name: erp
      kind: http
      purpose: "order lookup"
    - name: mail
      kind: tcp
      purpose: "notification e-mail"
      env: { host: SMTP_HOST, port: SMTP_PORT, user: SMTP_USER, password: SMTP_PASSWORD }
  ```

  A declaration grants nothing. It tells the operator what the app can
  use. Install output and the instance view show every declared need
  and whether it is bound.
- An `http` destination MAY be bound under a need the manifest does not
  declare. The app then learns it only from its environment (2.3).
  A `tcp` destination MUST be bound to a **declared** `tcp` need,
  because only the declaration names the fields the app reads.

### 2.3 How the app reaches an HTTP destination — the proxy

For every binding of kind `http`, the runtime sets **one** variable in
the instance's platform-owned environment:

```text
OAAP_DESTINATION_<NEED>_URL=http://oaap-gateway-1:8098/destinations/<need>/
```

`<NEED>` is the need name upper-cased, with `-` written as `_`. The
gateway's name is the reference's; the variable is the contract.

The gateway serves this path on a **dedicated listener that is not
published** on the host. It decides which instance is calling by **the
network the connection arrives from**: the only members of an instance
network are that instance's containers and the gateway itself. Then it:

1. refuses (403, with a sentence) any need the calling instance has not
   bound, and anything that arrives from no instance network;
2. removes every identity header (`oaap.core.gateway`) and every
   forwarding header the platform would otherwise add. The target has
   no use for the node's internal addresses;
3. adds the destination's authentication, **replacing** any
   `Authorization` (or named header) the app sent;
4. forwards to the target, with the part of the path after
   `/destinations/<need>` appended to the target's base path, the query
   unchanged, and the target's own host name as `Host`.

The app sees plain HTTP and no secret. Rules for implementations:

- **Caller identity is the connection's source address, never a
  header.** A header can be typed by the app. The source address of a
  TCP connection on an instance network cannot be made to look like
  another network's: a forged address gets no answer back, so no
  connection is ever established.
- **The listener MUST NOT be published on the host.** Container runtimes
  allocate instance networks from private ranges that include
  `192.168.0.0/16`, and a published port with a preserved client
  address would let a LAN machine whose address falls inside some
  instance's range act as that instance. Measured on `oaap-test`
  2026-09-25: two of fifteen instance networks were already in
  `192.168.0.0/20` and `192.168.16.0/20`.
- **The mapping from network to instance MUST be rewritten whenever an
  instance network is created or removed, and the gateway reloaded.**
  The runtime reuses a freed address range for the next network it
  creates. A stale mapping would hand one instance's bindings to
  whichever instance inherits the range. That fails open, and it
  fails silently.
- **The gateway MUST apply the steps in the order written here**:
  strip, then rewrite the path, then forward. See `oaap.core.gateway`
  0.2.12: Caddy reorders directives inside a plain `handle`, and the
  first live call went to the wrong path.
- **A binding whose destination no longer exists** (a restore, a
  tenant adopted from another node) yields neither a variable nor a
  route, and is shown as missing. An address that only ever leads to
  a refusal is a worse answer than no address.

**A `via` target (0.2).** Steps 1–3 are the same. Step 4 forwards to
the node's connector service instead of the target, which carries the
call into the tunnel (`oaap.net.connector` 2.5): the path after
`/destinations/<need>` goes behind `/via/<tunnel>/<offer>`, and the
gateway adds three headers of its own — a key only it holds, the
calling instance, the destination with its tenant — overwriting
anything the app sent under those names. `Host` is set on the inner
side, to the backend's. **The app's variable and the app's call do not
change**: an app MUST NOT be able to tell a tunnelled destination from a
direct one (RFC-0033 §8).

- `via` is for `kind: http` only in 0.2. A TCP destination through a
  tunnel is refused at creation.
- The tunnel MUST belong to the destination's tenant. Another tenant's
  tunnel is answered as one that does not exist.
- A tunnel that is not connected answers 502 with a sentence; an offer
  the inner side does not offer answers 404 with a sentence.

### 2.4 Non-HTTP — the handover, said out loud

A `tcp` destination cannot pass an HTTP proxy. For a binding of kind
`tcp`, the runtime **hands the values over** through the instance's
environment, into the fields the declared need names: `host` and
`port` from the target, and `user` and `password` from the
authentication.

- **The credential travels into the container.** That is the
  difference from 2.3, and every surface that shows the binding MUST
  say `handover` beside it, so nobody assumes the proxy guarantee
  where it does not hold (RFC-0033 §1.4).
- The handed-over fields are platform-owned for the duration of the
  binding. `app config set` cannot change them, and unbinding removes
  them. A field name that collides with a declared `config` key or a
  platform-owned variable makes the manifest invalid.

### 2.5 Where the secret lives

- The secret is stored on the host, readable by root only, in a
  directory that **no container mounts**. It is not in the registry,
  not in the destination object, and not in any instance's environment
  (except in handover mode, 2.4).
- For HTTP, the only reader is the gateway, and only through the
  configuration the host writes for it. The implementation MUST keep
  that configuration readable by root only.
- Accepted input is limited to what a header can carry without
  interpretation. For `bearer` and `header` the secret is printable
  ASCII without whitespace, quotes, backslashes or braces; `basic` is
  encoded by the platform. A secret outside that set is refused, never
  escaped. An escaping rule that is wrong once turns a password into a
  configuration directive.
- The secret is entered hidden or from standard input, **never as a
  command-line argument**: an argument ends up in the shell history.
- **No encryption at rest in 0.1.** RFC-0033 §1.1 asks for encryption
  with the node key. Two facts decided against it for now: the gateway
  needs the clear value on the same disk anyway, and a key kept beside
  the ciphertext protects nothing. 0.1 therefore follows the posture
  the node already uses for identity-provider secrets
  (`oaap.core.tenant`, RFC-0041 §3): its own root-only directory, and
  no reader beyond the one that needs it.
- **The secret is not in the backup**, like the identity-provider
  secrets are not: a secret in a backup is a secret in every copy of
  it. The destination object is. After a restore the object is back
  without its secret, and the proxy then answers **503 with a
  sentence** instead of calling the target without the credential. A
  `server_admin` sets it again. A handed-over value (2.4) lives in the
  instance's environment and therefore IS in the backup — one more
  reason handover says what it is.

### 2.6 The rehearsal has none

- **Bindings are not carried into a rehearsal** (`oaap.apps.runtime`
  2.15.2). The copied environment is scrubbed of every
  `OAAP_DESTINATION_*` variable and every handed-over field *before*
  any container starts. The install then computes the environment
  again from the rehearsal's own record, which has no bindings.
- An operator MAY bind a destination to a rehearsal, **explicitly**
  (`--rehearsal-exception`). The binding is written to the tenant's
  audit log as a rehearsal exception, like every other deliberate
  deviation from RFC-0030 D3.
- An unbound call from a rehearsal gets the proxy's 403, which says
  that it came from a rehearsal.

### 2.7 Who maintains what (0.1)

- **Destinations and their secrets are maintained by `server_admin`**
  (on the reference: the CLI as root). RFC-0033 §1.1 gives this to the
  tenant's `tenant_admin` as well. That part waits until the check in
  2.1 happens at connection time rather than at creation (§4). Before
  then, a target a tenant can write is a way into the node's own
  networks.
- **Bindings are maintained by `server_admin`** in 0.1. The portal
  shows destinations and bindings but cannot change them yet.

## 3. Configuration

None beyond the objects. The listener port (8098 in the reference) is
internal and not an operator setting.

## 4. Security requirements

- **The binding, not the manifest, grants.** Declaring a need reaches
  nothing.
- **A tenant sees and binds only its own destinations.** One tenant
  cannot learn whether another tenant has a destination of a given
  name.
- **No credential in the container for HTTP.** The app never sees a
  destination secret. Handover mode says what it is on every surface.
- **Caller identity by network, on an unpublished listener,** with the
  mapping rewritten on every network change (2.3).
- **A rehearsal has no bindings** unless somebody chose one and the
  tenant's log says so.
- **Whatever joins an instance network acts as that instance.** That
  is the price of identifying the caller by network. Nothing but the
  instance's own containers and the gateway may join one. Any future
  way for a person into an instance network (RFC-0044, draft) MUST
  exclude the gateway's address on that network. Otherwise the person
  would call the instance's destinations with the platform adding the
  credential for them.
- **Known limit of the target check (2.1):** it judges the name and the
  literal address at creation time. A host name that later **resolves**
  to an internal address (DNS rebinding) is not caught. With
  `server_admin` as the only author this is the operator deceiving
  themselves. Before a tenant may author targets, the check MUST move to
  the moment of connection, or the gateway's outbound path MUST be
  filtered.

## 5. Conformance tests (described)

1. An instance with no binding calls `/destinations/x/` → 403 with a
   sentence; the target receives nothing.
2. After `bind`, the instance's container environment carries
   `OAAP_DESTINATION_<NEED>_URL`, and a call through it reaches the
   target with the destination's `Authorization` and the target's own
   `Host`; the `Authorization` the app sent is not the one that
   arrives.
3. A second instance, not bound, calling the first one's path from its
   own network → 403.
4. The listener does not answer on the host's addresses.
5. A binding across tenants is refused as "no such destination".
6. `remove` of a bound destination is refused and names the instances.
7. A redeploy keeps the bindings; `unbind` removes the variable and the
   container is recreated without it.
8. A rehearsal of a bound instance comes up without the variable and
   without the handed-over fields, and its call → 403.
9. A `tcp` binding writes the declared fields; binding it to an
   undeclared need is refused.
10. Removing an instance and creating another one that inherits its
    network range does not hand over the first one's bindings.
11. Targets `http://portal:8000/`, `http://localhost/`, and an address
    inside a current instance network are refused.

## 6. Dependencies

`oaap.core.gateway` (the listener), `oaap.apps.runtime` (2.3 platform
environment, 2.11 instance networks, 2.15 rehearsal), `oaap.core.tenant`
(ownership, audit log).

## 7. Maturity

Draft. Built in the reference 0.1.128 and measured end to end on
`oaap-test` 2026-09-25: a bound app's call arrived at an echo server
with the platform's credential, the target's own `Host`, path and
query intact, and without the `Authorization`, `X-OAAP-User` and
`X-Forwarded-For` the app had sent; another app's network on the same
path got 403; the container environment held the address and never
the secret; unbinding took the variable out of the running container.
0.2 (`via`) was built in the reference 0.1.129 and measured the same
way through a tunnel between `oaap-test` and `oaap-demo`
(`oaap.net.connector` §7): the app's variable and call were the same as
for a direct destination (RFC-0033 §8).

## Deutsche Zusammenfassung

**Was das ist.** Stufe 1 von RFC-0033. Eine **Destination** ist ein
benanntes Ziel eines Mandanten, etwa das ERP eines Kunden oder ein
Webhook-Empfänger. Der Betreiber **bindet** eine Instanz daran. Für
HTTP ruft die App eine lokale Adresse
(`OAAP_DESTINATION_ERP_URL=http://oaap-gateway-1:8098/destinations/erp/`).
Das Gateway ergänzt die Anmeldung und leitet weiter. **Die App sieht
das Geheimnis nie.** In SAP-Begriffen ist das die Destination aus dem
BTP Destination Service, nur dass die App sie nicht nachschlägt: Die
Plattform führt den Aufruf selbst aus.

**Woran das Gateway den Aufrufer erkennt.** Am Netz, aus dem die
Verbindung kommt. In jedem Instanznetz sitzen nur die Container dieser
Instanz und das Gateway. Eine Kopfzeile könnte die App frei eintippen,
die Absenderadresse einer TCP-Verbindung nicht. Gemessen auf
`oaap-test` am 25.09.: Aus dem Wegweiser-Netz passt die Anfrage, aus
dem RACI-Netz nicht, ein gefälschtes `X-Forwarded-For` ändert nichts.
Zwei Regeln sichern das ab:
- Der Port wird **nicht nach außen veröffentlicht**. Docker vergibt
  Instanznetze inzwischen auch aus `192.168.x.x`, und ein LAN-Rechner
  mit passender Adresse könnte sich sonst als Instanz ausgeben.
- Die Zuordnung Netz → Instanz wird **bei jedem Anlegen und Entfernen
  eines Netzes neu geschrieben**. Docker vergibt einen freigewordenen
  Adressbereich wieder, und eine veraltete Zuordnung würde die
  Bindungen der alten Instanz an die neue vererben.

**Nicht-HTTP (SMTP, Postgres …): Übergabe.** Die Werte kommen über die
Instanzumgebung in die Felder, die das Manifest nennt. Dabei wandert
das Geheimnis in den Container. Überall, wo die Bindung angezeigt
wird, steht deshalb „Übergabe“.

**Generalprobe.** Bindungen werden nicht mitkopiert. Die kopierte
Umgebung wird vor dem Start bereinigt. Wer trotzdem bindet, tut das
ausdrücklich, und es steht im Prüfprotokoll des Mandanten.

**Drei bewusste Abweichungen vom RFC**, jeweils mit Grund:
1. **Keine Verschlüsselung der Geheimnisse im Ruhezustand.** Das
   Gateway braucht den Klartext ohnehin auf derselben Platte, und ein
   Schlüssel direkt neben dem Chiffrat schützt nichts. Stattdessen gilt
   dieselbe Haltung wie bei den Geheimnissen der Identitätsanbieter:
   ein eigenes Verzeichnis nur für root, das kein Container einbindet.
2. **Pflege nur durch `server_admin`, noch nicht durch
   `tenant_admin`.** Ein Ziel, das ein Mandant selbst eintragen darf,
   wäre ohne eine Prüfung zum Zeitpunkt der Verbindung ein Weg in die
   internen Netze des Knotens (etwa über `http://portal:8000/`). Die
   Prüfung beim Anlegen fängt Namen und Adressen ab, aber keinen
   DNS-Namen, der später auf eine interne Adresse zeigt.
3. **Das Portal zeigt an, ändert aber noch nichts.** Binden geht in
   0.1 über die Kommandozeile.

**Neu in 0.2: `via`-Ziele.** Eine HTTP-Destination kann über einen
Tunnel laufen (`--target via:<tunnel>/<angebot>`, siehe
`oaap.net.connector`). Für die App ändert sich nichts: gleiche
Variable, gleicher Aufruf. Das Gateway reicht den Aufruf an den
Verbindungsdienst weiter statt an das Ziel. Nur HTTP, und nur über
einen Tunnel des eigenen Mandanten.

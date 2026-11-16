# RFC-0089: Commands to a Node over the Fleet Path — Signed, Named Verbs the Node Accepts, Answers on the Way Back

- **Status:** **Draft (2026-11-16)** — decisions D1–D6 (§4) are Jörg's.
  Nothing is built.
- **Date:** 2026-11-16
- **Authors:** Jörg (the need: reboot, backup, later a service portal for
  tenant owners, "on the same event-broker path the health data comes to
  us"), Claude (facts read in the reference code, design)
- **Depends on:** RFC-0085 (pairing, hub, entry, bridge, the reserved control
  tree), RFC-0052 (the node's sender and outbox), RFC-0054 (broker keys and
  ACL), RFC-0069 (reboot plan, protection, urgency), RFC-0081 (backup classes
  and tenant backup), RFC-0080 (notifications), RFC-0088 (tenant universe on
  the hub), RFC-0022 (tenant as boundary)

## Summary

The fleet path carries health data **from** every node **to** the hub. Jörg
asked whether the same path can carry commands the other way — reboot,
backup — and later let a tenant owner trigger such things for their own
tenant from a service portal.

It can, and RFC-0085 already reserved the place: the bridge carries exactly
one tree outward, `oaap-fleet/control/<entry>/#`, and nothing uses it yet.
This RFC fills it with **commands**: a closed list of named **verbs** without
free arguments or a shell, each command **signed** by the hub with a secret
only the hub and that node share, **expiring**, **never retained**, and
executed only if the **node itself accepts that verb**. The node answers on
its own branch, the way its health data already travels, and both sides keep
an audit line. A reboot is never executed remotely as such: a command can
only create a reboot **plan** under RFC-0069, so an instance's protection
and the urgency rules hold exactly as they do on the node.

The governing sentence mirrors RFC-0085 §4.4:

> **The hub decides what it asks. The node decides what it does.
> Neither can widen the other's decision.**

## 1. Facts (read in the reference code, 2026-11-16)

1. **The outward tree exists and is empty.** The entry's bridge key holds
   write `oaap-fleet/control/<entry>/#` (RFC-0085 §4.3, "the hub's commands");
   the hub-to-entry bridge maps only this tree outward (§5.3). The one planned
   use, revoking a node, moved to HTTPS (§17, "the branch stays reserved").
   `mqtt_acl.py` names `oaap-fleet` "the hub's commands" for later.
2. **A node key cannot subscribe at all** (`mqtt_acl.py`: "a stolen node key
   reads nothing, not even its own branch"). Receiving needs a new, narrow
   read grant.
3. **The node has no listener.** The sender (`metrics_sender.py`, its own
   minimal MQTT client, no library) connects, publishes the outbox (QoS 1)
   and disconnects on each minute run of `oaap-instance-watch`. A command
   therefore reaches a node at its next run — within about a minute — if it
   waits in a persistent session.
4. **What the verbs would call exists:** a reboot plan by hand
   (`oaap node care reboot at … --reason …`, RFC-0069 2.7.1: announced,
   protection and urgency applied, cancel), a node backup and a tenant backup
   (`oaap backup`, RFC-0081), restart / standby / wake of an instance.
5. **No asymmetric signatures without a new dependency:** the standard
   library has HMAC-SHA256 (already used for pairing codes), not Ed25519.
6. **Pairing already gives hub and node a moment of shared trust** (the
   node code, HMAC with the pairing secret, RFC-0085 §17). A per-node secret
   can be handed over at the same moment.

## 2. Proposal

### 2.1 The way

- The hub publishes a command on
  `oaap-fleet/control/<entry>/cmd/<node>/<command-id>`, **QoS 1, never
  retained** (a retained command would be replayed at every reconnect). For a
  node paired directly with the hub, `<entry>` is the hub itself.
- The bridge carries it to the entry, unchanged (it does today for this tree).
- The node key gains **one** read grant: subscribe
  `oaap-fleet/control/<entry>/cmd/<node>/#` — its own commands, nothing else.
  The sender connects with a **persistent session** (clean session off), so a
  command published while the node was away arrives at its next run.
- **No new port, no listener, no long-lived connection.** Latency is the
  sender's minute.

### 2.2 The command

```json
{"id": "c-20261116-2d1f", "verb": "backup.run", "args": {},
 "scope": "node", "by": "joerg (server_admin, hub oaap-demo)",
 "issued": "2026-11-16T21:04:00Z", "expires": "2026-11-16T21:19:00Z",
 "nonce": "9f2c…", "sig": "hmac-sha256:…"}
```

- `sig` is HMAC-SHA256 over the canonical JSON without `sig`, with the
  **command secret** of this node. The secret is created at pairing (the
  claim answer, RFC-0085 §17.2), stored 0600 on both ends, never sent again.
  The entry carries commands but **cannot forge** one; a hub can only sign
  for nodes it paired.
- The node refuses — and says so (§2.5) — a command whose signature does not
  verify, that has expired (clock tolerance 2 min), whose `id` it has seen
  (journal of the last 7 days), whose verb it does not accept (§2.4), whose
  `args` are not exactly the verb's, or whose `scope` it does not allow.

### 2.3 The verbs — a closed list

| Stage | Verb | Args | What the node does |
|---|---|---|---|
| 1 | `ping` | — | answers with version, uptime, clock |
| 2 | `status.send` | — | sends the status class now instead of at the next change |
| 2 | `backup.run` | — | a node backup now (RFC-0081), result in the answer |
| 2 | `reboot.plan` | `at`, `reason` | a reboot **plan** as by hand (RFC-0069 2.7.1): announced, protection and urgency apply; `at` no sooner than the plan's minimum lead |
| 2 | `reboot.cancel` | `reason` | cancels the stored plan |
| 3 | `backup.tenant` | `tenant` | that tenant's backup now |
| 3 | `instance.restart` / `.standby` / `.wake` | `instance` | the instance verb, within the command's scope |

**Never a verb:** a shell, a script, a file, a configuration value, a secret,
an installation, a platform update. Anything that would need free text is
not a command — it is work for a person on the node. (A remote *update*
would be its own RFC: it changes what runs, not when.)

### 2.4 The node decides

In *Flotte → Kopplung*, beside the classes it offers, the node lists the
verbs it **accepts**. Default: `ping` and `status.send` only. Everything else
is switched on by the node's server_admin, per verb. The hub reads the
accepted list from the status class and shows a verb the node does not accept
as *nicht angenommen*, not as a button that would fail. The hub cannot widen
the list; a refused verb is answered, not silently dropped.

### 2.5 The answer

The node answers on its own branch, through its outbox (RFC-0052, QoS 1):
`oaap-node/<node>/cmd/<command-id>` — it reaches the hub through the bridge
as `oaap-via/<entry>/<node>/cmd/<command-id>` like every other value.

```json
{"id": "c-20261116-2d1f", "state": "done", "at": "…", "text": "backup 2.1 GB, 4 min"}
```

`state` is one of `accepted`, `refused` (with the reason: signature, expired,
seen, verb not accepted, scope), `done`, `failed` (with the reason). The hub
shows each command with its last state; **no answer within the expiry is
shown as "keine Antwort", never as refused** — the lesson of RFC-0019 (no
answer is not a refusal).

### 2.6 The record

- **Hub:** audit line per command (who, verb, node, scope, id), and per
  answer.
- **Node:** audit line per command received, with its verdict; a
  tenant-scoped verb also in that tenant's audit (RFC-0022 spec 1.7).
- **Notifications** (RFC-0080) as the node already sends them: a reboot plan
  made by command is announced exactly like one made by hand, naming the hub
  and the person.

### 2.7 The tenant owner's service portal (stage 4)

The command carries `scope: "tenant:<label>"` for tenant verbs. The node
checks that the instance or backup belongs to that tenant **and** that its
operator allows that verb for that tenant (a per-tenant list beside §2.4).
Who may issue a tenant command on the hub — the tenant owner's identity on
the hub and its link to the tenant object of RFC-0088 — is the open part and
is left to stage 4 (D5). Until then only the hub's server_admin issues
commands.

## 3. Threats, and what stops them

| Threat | Stopped by |
|---|---|
| stolen node key | reads only its own commands, which are signed and expiring; cannot answer for another node (writes only its branch) |
| compromised entry | can drop or delay commands (shown as "keine Antwort"), cannot forge or change one (HMAC) |
| replay | expiry, id journal, never retained |
| compromised hub | can only send verbs the node accepts; no shell; a reboot only as a plan with protection; every command in the node's own audit |
| wrong node | the node's name is in the topic and in the signed body; a body for another node is refused |

## 4. Decisions for Jörg

- **D1 — The broker path.** Commands go over the fleet broker (the reserved
  tree), not as an HTTPS pull from the hub. *Recommended:* yes — the path
  exists end to end, also through the bridge to oaapx01; external nodes
  cannot be reached from the hub anyway, and a pull would need a second
  channel and a second key.
- **D2 — HMAC with a per-node secret** instead of Ed25519. *Recommended:*
  HMAC — standard library, the same mechanism as pairing codes; Ed25519 would
  be the first cryptography dependency of the platform.
- **D3 — Default: only `ping` and `status.send` accepted;** every other verb
  switched on per node. *Recommended:* yes (the node decides, §2.4).
- **D4 — A reboot only as a plan** (RFC-0069), never an immediate reboot by
  command. *Recommended:* yes; "now" stays a decision of a person on the node.
- **D5 — The tenant owner's portal is stage 4,** after a hub-side identity
  for tenant owners (RFC-0088). Until then the hub's server_admin only.
  *Recommended:* yes.
- **D6 — Expiry 15 minutes by default, at most 24 hours.** *Recommended:*
  yes; a command that arrives late is refused and reported, never executed.

## 5. Stages

1. **Transport, `ping`, answer, audit** — the grant, the persistent session,
   signature and journal; measured oaap-demo (hub) → oaap-test (direct) and
   → oaapx01 (through the entry bridge), including a hub restart and a node
   away for an hour with a command waiting.
2. **`status.send`, `backup.run`, `reboot.plan`, `reboot.cancel`** with the
   accepted list in the node portal and the hub's command view (FleetView).
3. **Tenant and instance verbs** with `scope`.
4. **The tenant owner's service portal.**

## 6. Out of scope

Remote software updates (their own RFC), free commands or scripts, file
transfer, commands between nodes (only hub → node), a live connection with
sub-second latency.

## Zusammenfassung (deutsch)

**Kommandos auf dem Flottenweg zum Knoten.** Heute fließen Gesundheitsdaten
vom Knoten zur Zentrale. Jörg fragte, ob derselbe Weg Kommandos zurück
tragen kann (Neustart, Sicherung, später ein Serviceportal für
Mandanten-Besitzer). Ja, und der Platz ist schon reserviert: Die Brücke trägt
genau einen Baum nach außen, `oaap-fleet/control/<entry>/#`, ungenutzt.

**Vorschlag:**

- Die Zentrale veröffentlicht ein Kommando dort, nie „retained“, mit Ablaufzeit.
- Es ist signiert mit einem Geheimnis, das nur Zentrale und dieser Knoten
  kennen (HMAC, beim Koppeln vereinbart). Die Zwischenstation (Eingang
  oaapx01) kann es weiterleiten, aber nicht fälschen.
- Der Knoten holt es bei seinem minütlichen Lauf ab, er braucht dafür keinen
  offenen Port.
- Es gibt nur **benannte Verben** ohne freie Eingaben und ohne Shell: `ping`,
  `status.send`, `backup.run`, `reboot.plan`, `reboot.cancel`, später Mandanten-
  und Instanzverben.
- **Der Knoten entscheidet**, welche Verben er annimmt. Voreingestellt sind
  nur `ping` und `status.send`, alles andere schaltet sein Betreiber frei.
- Ein Neustart ist **immer ein Plan nach RFC-0069**: angekündigt, und der
  Schutz einer Instanz gilt.
- Die Antwort (angenommen, abgelehnt mit Grund, erledigt, fehlgeschlagen)
  kommt auf dem gewohnten Weg zurück. „Keine Antwort“ heißt nie „abgelehnt“.
- Beide Seiten protokollieren jedes Kommando.

**Zu entscheiden (D1–D6),** jeweils mit Empfehlung:

- D1: Broker-Weg statt HTTPS.
- D2: HMAC statt neuer Kryptobibliothek.
- D3: Standard nur `ping` und `status.send`.
- D4: Neustart nur als Plan.
- D5: Serviceportal für Mandanten-Besitzer erst Stufe 4.
- D6: Ablauf 15 Minuten, höchstens 24 Stunden.

**Stufen:** 1 Transport und `ping`, 2 Sicherung und Neustartplan, 3 Mandanten-
und Instanzverben, 4 Serviceportal.

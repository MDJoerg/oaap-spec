# RFC-0082: Node Alias and Place — How a Node Names Itself Inside the Fleet

- **Status:** Draft (2026-11-12)
- **Date:** 2026-11-12
- **Authors:** Jörg (the need: "every OAAP node gets a configurable alias, like
  oaapx01 — not a name known outside, but how we keep it internally; an
  identifier for health data, errors and events distributed in real time over
  the broker; maybe groups or a prefix when thinking in topics, e.g.
  de/datacenter1/group3/<nodeid>; maybe useful in mails too"), Claude (facts
  read in reference 0.1.259, design)
- **Depends on:** `oaap.fleet.status` 0.8, RFC-0052 (metrics sender),
  RFC-0054 / `oaap.events.broker` (topic tree, ACL), RFC-0069 (care events),
  RFC-0080 (notifications, `{knoten}`), `oaap.data.backup` (archive names)
- **Not part of this RFC:** a fleet registry that assigns aliases centrally;
  the content of health or event messages (they get their own RFCs; this one
  gives them an address).

## Summary

Today a node has **no identity of its own**. Each feature picks one of four
stand-ins: the external host name, the OS hostname, a name typed into the
metrics sender, or whatever the fleet poller addressed. This RFC gives every
node three things it declares about itself:

- an **alias** — `oaapx01` — short, stable, internal, the node's identifier in
  topics, mails, archives and the fleet;
- a **place** — an ordered path such as `de/datacenter1/group3` — the prefix
  under which the node appears in a topic tree;
- **tags** — flat labels such as `kunde-cls` or `test` — for grouping that is
  not a hierarchy.

## 1. Facts (read 2026-11-12, reference 0.1.259)

| Where | Identifies the node by |
|---|---|
| notifications `{knoten}`, mail test subject, default sender name | external host, else OS hostname (`appctl.py` `_notify_values`) |
| backup archives `oaap-backup-<hostname>-…`, manifest `hostname`, tenant archives | OS hostname |
| backup pull (`ops/backup-pull.sh`), `/mnt/backup/<node>/`, `apps/backup-pulls/<node>.json` | `--node`, default `hostname` |
| metrics sender (RFC-0052) | name typed with `oaap metrics sender set --node`, default hostname; topic `<root>/<node>/metrics/<series>`, root `oaap-node` |
| care events (RFC-0069) | OS hostname, topic `oaap/<tenant-id>/node/<hostname>` |
| broker node keys | `--node N`, "the node's name on the wire" |
| fleet status document `"node"` | external host, else the host the poller addressed — assigned by nobody |
| FleetView | the watcher's own label for the node |

- No `location`, `site`, `group` or `region` setting exists anywhere.
- The tenant topic tree is `oaap/<tenant-id>/<type>/<object>/<group>`; a
  location-shaped tree (site/area/line) was rejected **for tenants' objects**
  (`oaap.events.broker`); nothing was decided for the platform's own messages.
- Node settings live in `apps/*.json`; `oaap node show` prints only profiles.
- Consequence today: oaapx01 is "oaap.joomp.de" in mails, "oaapx01" (OS
  hostname) in archive names, whatever was typed in the metrics sender, and
  the requested host in the fleet document. Renaming a host or changing the
  external name silently changes the node's identity in all of them.

## 2. Proposal

### 2.1 The three declarations

- **Alias:** `[a-z0-9][a-z0-9-]{0,38}[a-z0-9]` (the metrics sender's rule,
  already in use). Default when unset: the OS hostname, normalized — so
  nothing changes on a node until someone sets one.
- **Place:** 0–6 segments, each `[a-z0-9][a-z0-9-]{0,30}`, written
  `de/datacenter1/group3`. Empty by default.
- **Tags:** up to 10, same segment rule, unordered.
- Kept in `apps/node-identity.json` (0644, nothing secret, the portal reads
  it), written only on a change, every change in the node's log.

### 2.2 Who reads them

- **Mails (RFC-0080):** `{knoten}` becomes the alias; a new placeholder
  `{ort}` is the place; the body says "Server: oaapx01 (oaap.joomp.de)".
- **Fleet status:** the document gains `alias`, `place`, `tags` beside the
  existing `node`; FleetView shows the alias, groups by place and tags, and
  warns when two nodes report the same alias.
- **Archives:** `oaap-backup-<alias>-…`, manifest `alias`; pull directories
  default to the alias.
- **Health page and `oaap node show`:** alias, place, tags in the head.
- **Topics (stage 2):** one platform tree
  `<place>/<alias>/<kind>/…` — kinds `metrics`, `health`, `events`. Without a
  place the root stays `oaap-node` (today's metrics root), so existing
  subscribers keep working. The metrics sender's node defaults to the alias;
  care events move from `oaap/<tenant-id>/node/<hostname>` to
  `<place>/<alias>/events/care` (published to both during a transition). A
  node key may publish only under its own `<place>/<alias>/#`.

### 2.3 Uniqueness

Nothing on one node can know the others. Uniqueness is the operator's,
**checked where the nodes meet**: FleetView warns on a duplicate alias; a
broker refuses a node key for an alias another key already holds.

## 3. Decisions asked of Jörg

- **D1 — alias rule and default:** the rule above, default = normalized OS
  hostname. *Recommendation: yes.*
- **D2 — place as a path of up to six segments** (`de/datacenter1/group3`),
  the prefix of the platform topic tree. *Recommendation: yes.*
- **D3 — tags in addition** (flat, several per node, not in topics; for
  FleetView and later for notification routing). *Recommendation: yes — a
  hierarchy alone cannot say "customer X" across data centres.*
- **D4 — mails show the alias:** subject `[oaapx01] Backup fehlgeschlagen`
  instead of `[oaap.joomp.de] …`, the body names both. *Recommendation: yes —
  this changes the subject of every existing notification once the alias is
  set; nothing changes before.*
- **D5 — the alias travels with the node archive** (a relocation keeps its
  identity); the restore prints "this node calls itself oaapx01 — change it if
  this is a copy". *Recommendation: yes.*
- **D6 — set by `server_admin`:** CLI `oaap node alias|place|tags …` and a
  card on the health page. *Recommendation: yes.*
- **D7 — order:** stage 1 declarations + mails + fleet document + archives +
  health page; stage 2 the platform topic tree (metrics sender, care events,
  ACL); stage 3 FleetView grouping and duplicate warning. *Recommendation: as
  listed.*

## 4. Stages and what is measured

1. **Declarations** — oaap-test set to alias `oaap-test`, place
   `de/home/lab`: a notification mail shows `[oaap-test]`, the fleet document
   carries alias/place/tags, the next archive is named by the alias; a node
   without an alias behaves exactly as before.
2. **Topic tree** — the metrics sender publishes under
   `de/home/lab/oaap-test/metrics/…`; a node key cannot publish under another
   node's alias; care events arrive under the new and the old topic.
3. **Fleet** — FleetView groups by place and tags; two nodes with one alias
   are flagged.

## 5. Out of scope

Central assignment of aliases; renaming the OS host; the message formats of
health and event data (own RFCs — this RFC gives them their address).

## Zusammenfassung (deutsch)

Heute hat ein Knoten **keine eigene Identität**: Mails nennen den externen
Namen, Archive den Rechnernamen, der Metrik-Sender einen eingetippten Namen,
der Flottenstatus den angefragten Host. Vorschlag: Jeder Knoten erklärt drei
Dinge über sich.

- **Alias** (z. B. `oaapx01`): kurz, stabil, intern — Kennung in Topics,
  Mails, Archiven und der Flotte. Ohne Eintrag gilt der Rechnername, es ändert
  sich also nichts.
- **Ort** (z. B. `de/datacenter1/group3`): bis zu sechs Stufen, das Präfix im
  Topic-Baum: `de/datacenter1/group3/oaapx01/metrics|health|events/…`.
- **Tags** (z. B. `kunde-cls`, `test`): flache Gruppen quer zur Hierarchie.

Mails zeigen dann `[oaapx01] …` und im Text beide Namen; der Flottenstatus
trägt Alias, Ort und Tags; FleetView gruppiert und warnt bei doppeltem Alias.
Der Alias reist mit dem Archiv mit (Umzug behält die Identität). Stufen:
1 Erklärung + Mails + Flottenstatus + Archive, 2 Topic-Baum, 3 FleetView.
Entscheidungen D1–D7 in §3, je mit Empfehlung.

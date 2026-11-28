# oaap.core.situation — The Situation Picture

- **ID:** `oaap.core.situation`
- **Version:** 0.1
- **Maturity:** draft (RFC-0142 stage 1: the picture per scope, read by
  the portal's phone app; the weekly report and the chat as readers are
  later stages)
- **Based on:** RFC-0142 §2 (D1: computed on the host), `oaap.core.notifications`
  (open matters), RFC-0141 (site check), I-81 (page statistics), RFC-0108
  (history per instance), `oaap.core.tenant` 1.7 (the audit log),
  `oaap.core.updates` 2.6 (the planned reboot)

## 1. Purpose

**One answer to "what is the situation", for a person and a scope.** The
phone, the weekly report and the chat need the same facts; built three
times they would disagree. This capability joins what the node already
keeps — it collects nothing new.

## 2. The view

- **Where:** `apps/situation/node.json` and `apps/situation/<tenant id>.json`,
  mode 0644 (the portal reads them through its read-only registry mount).
  A tenant that is gone loses its file at the next run.
- **When:** every 300 s from the minute job's `metrics sample`, never while
  the node backup copies `apps/`. `oaap metrics situation` writes it at
  once and prints the node's view.
- **Shape:** `{schema: "oaap.situation/0.1", measured, scope, label,
  unusual[], deviations[], happened[], coming[], instances{}, tenants{}}`.
  An entry is `{level: red|yellow|info, text, instance, tenant, link,
  kind}` — a German sentence and a link into the portal; `since` on a
  matter, `when` and `who` on an action.
- **unusual:** every open matter (level from its category: critical and
  health red, security and operations yellow; a matter of scope `node`
  only in the node's view; a summary matter such as "10 Instanzen" names
  no instance); a production instance whose services do not all run
  (unless `instance.down` is open); an instance in maintenance; red points
  of the last site check (unless `site.check` is open).
- **deviations** (the rule of `site_stats.notfound_rising`: against the
  person's own history, nothing when nothing is unusual; without seven
  days of history no judgment):
  - views so far today against the mean of the same UTC hours on up to
    28 earlier days — from 06 UTC, at least 50 and twice as many (info),
    or under a third of a usual of at least 50 (yellow);
  - the last 7 full days against the weekly mean of up to 28 days before
    — at least 100 and twice, or half of a usual of at least 100 (info);
  - people's 404 in 7 days: at least 20 and twice the mean (yellow);
  - CPU of the last hour at least 30 % of a core and three times the
    week's mean (yellow).
- **happened:** the audit actions of 7 days the picture names (instance
  actions — maintenance on/off, restart, rebuild, wake, standby,
  promotion, delivery, rollback, install, remove, login required, AI
  fetchers — and the weekly report's node events), newest first, at most
  40; a failed one yellow.
- **coming:** a planned reboot (in every view — it stops every tenant's
  apps), a certificate ending within 14 days (yellow, red within 3).
- **instances:** per instance `{tenant, label, state (running, standby,
  waking, maintenance, down, unknown), state_text, channel, light (red,
  yellow, green, grey), views_today, views_usual, views_week,
  views_week_usual, days7 [(day, views)], cpu, mem, check {red, yellow,
  at, lights}}`.
- **Scopes:** `node` holds everything; a tenant's view its instances, its
  matters and actions, and the planned reboot. `tenants` (id → label) only
  in the node's view of a node with more than one tenant.

Nothing in the view is a secret: no content of an app, no address of a
visitor, no secret value — the sentence-level facts a mail carries.

## 3. Who reads which view

One function, `situation.pick(role, own tenant, place tenant)`, used by
every surface:

| Caller | At the node's address | At a tenant's place (RFC-0042, RFC-0115) |
|---|---|---|
| `server_admin` | `node` | that tenant's view |
| `tenant_admin` | their tenant's view | their tenant's view; another tenant's place: refused |
| anyone else | refused | refused |

## Deutsche Zusammenfassung

Das **Lagebild** beantwortet „Wie ist die Lage?“ für eine Person und einen
Bereich. Der Knoten berechnet es alle fünf Minuten aus dem, was er ohnehin
schreibt: offene Meldungen, Zustand der Instanzen, Seiten-Check,
Seitenstatistik, CPU, Audit, geplanter Neustart. Er schreibt eine Datei je
Bereich nach `apps/situation/` (`node.json` und eine je Mandant). Darin:
**auffällig** (offene Meldungen, Produktiv-Instanz läuft nicht, Wartung,
rote Punkte), **anders als üblich** (Aufrufe heute und diese Woche, 404,
CPU – immer gegen die eigene Geschichte, ohne eine Woche Geschichte kein
Urteil), **passiert** (Aktionen der Woche), **kommt** (Neustart,
Zertifikat) und eine Zeile je Instanz. Der server_admin liest den Knoten,
ein tenant_admin seinen Mandanten. Am Ort eines Mandanten liest jeder
dessen Sicht, und ein fremder tenant_admin nichts. Die Regel steht in einer
Funktion. `oaap metrics situation` schreibt das Lagebild sofort.

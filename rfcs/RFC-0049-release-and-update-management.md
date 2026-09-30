# RFC-0049: Releases and Updates for Many Tenants Running the Same Solution

- **Status:** **Proposed (2026-09-30)** — design only; Jörg to decide the
  questions in §6. Nothing built.
- **Date:** 2026-09-30
- **Authors:** Jörg (the need), Claude (facts measured on the reference
  node, design)
- **Depends on:** RFC-0019 (artifact deployment), RFC-0020 (promotion),
  RFC-0021 (fleet status), RFC-0022 (tenant as boundary), RFC-0029
  (backups, tenant archives), RFC-0046 (the cohort — a template applied
  to many tenants)
- **Driver:** A dedicated multi-tenant node will carry many tenants that
  all run the same, non-store application (an association solution). The
  package is produced elsewhere; it is not an official store app.

## Summary

Ship **packages, not images**; treat "released" as *what runs in
production on the reference node*; make **versions per tenant visible**;
then add a **rolled update** with rings, a backup first, rollback, and a
**per-tenant policy** whose limits the operator sets.

## 1. Facts (measured 2026-09-30 on the reference node)

- The production instance is an **artifact** (RFC-0019): one ZIP of about
  2 MB, built on the node from a Dockerfile, one service, one storage
  mount, five config keys, no extra containers, no node profile needed.
  Its data is about 2 MB.
- The **test instance is ahead of production** (0.0.141 against 0.0.134).
  "Released" therefore cannot mean "newest tested": it means "promoted".
- The node keeps the current package and three predecessors; rollback
  exists (`oaap app artifact rollback`), and the package can be exported.
- The two nodes are on different platform versions (0.1.150 and 0.1.146).
  Versions of nodes belong in the same overview as versions of packages.

## 2. Stage 0 — by hand (no platform work)

Export the promoted package, copy, verify the checksum, install as a test
instance in the tenant, promote. See the scenario *Ein getestetes Paket
vom Referenzknoten einspielen*. Keep a register by hand.

## 3. Stage 1 — see what runs where

A read-only table per node: tenant × instance × package × version ×
checksum × channel × node platform version, as `oaap app versions` and in
the fleet view. Cheap, and it turns the mass-update question into a
question about a list.

## 4. Stage 2 — a release source

A read-only place both sides can reach (HTTP or object storage; a Git
forge's release list is enough) holding **released packages with their
checksums**. An entry is created only by a promotion on the reference
node. The tenant node fetches from it instead of from a laptop. It never
fetches anything not listed there, and it verifies the checksum before it
unpacks (as RFC-0019 already requires).

## 5. Stage 3 — updating

- **Run:** "put version X on tenants A, B, C" as one operation, with a
  dry run and a log line per tenant; the same operation for one tenant.
- **Rings:** a test tenant first; the rest after a wait and a green health
  check. A failed check stops the run.
- **Before each:** a tenant archive (RFC-0029, needs the per-tenant
  schedule idea) — and **after a failure:** roll back to the predecessor
  package.
- **Per-tenant policy:** `automatic` (default) · `hold` (with an expiry
  date, so nobody forgets) · `window` (days and hours, time zone). The
  operator sets limits: a security release can be held at most N days.
- **Package metadata** that stops automation: `breaking`,
  `data_migration`, `min_from_version`. A migration never runs unattended.
- **Tenant administrator view:** installed version, what is available,
  history, and the policy — within the operator's limits.

## 6. Questions for Jörg

1. Where does the release source live: on the reference node, on the
   Git forge in the shared tenant, or with the data-centre operator?
2. New tenants start with an empty data set, or is data migrated from the
   existing production instance?
3. Which rule sets the *ring* order: a named test tenant, or "first N by
   creation date"?
4. Is a tenant allowed to refuse a security release at all, or only to
   choose the window?

## Zusammenfassung (deutsch)

Für viele Mandanten mit derselben Lösung, die nicht im Store liegt:
**Pakete statt Images** übertragen (ZIP, Prüfsumme). „Freigegeben" heißt
**auf dem Referenzknoten produktiv gesetzt**, nicht „neueste getestete"
(gemessen: der Teststand ist dort neuer als Produktion). Stufe 0 von Hand
(Szenario liegt vor), Stufe 1 Übersicht Version je Mandant und Knoten,
Stufe 2 Freigabequelle, Stufe 3 Sammellauf mit Ringen, Sicherung davor,
Rückfall danach, Richtlinie je Mandant (automatisch, angehalten mit
Ablaufdatum, Zeitfenster) mit Grenzen des Betreibers, und Paketvermerke
(`breaking`, `data_migration`), die die Automatik stoppen. Vier Fragen an
Jörg in §6. Nichts gebaut.

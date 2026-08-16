# RFC-0020: Promotion to Production — Shipping Exactly What Was Tested

- **Status:** Accepted (2026-08-16)
- **Date:** 2026-08-16
- **Authors:** Jörg (direction and decision to build), Claude (design and
  write-up)
- **Depends on:** RFC-0011 (node profiles), RFC-0012 (store sources),
  RFC-0019 (artifact deployment)
- **Extends:** `oaap.apps.runtime` 2.3 (channels), 2.6 (portal installs),
  2.14 (artifact deployment). Nothing here is withdrawn.
- **Driver:** `bdt-hub` has reached the maturity for a production
  instance on the same node as its test instance. Its source is a
  private repository, so the package arrives as a ZIP (RFC-0019).
  Today a production instance from such a package can only be installed
  and updated **on the machine**, over SSH — which turns every routine
  release into an administration act.

## Summary

A `server_admin` may **promote** a tested artifact from a test instance
to a production instance of the same app, from the portal, with one
deliberate action.

Promotion moves **bytes, not permissions**: the artifact already lies on
the node (RFC-0019 retention), was accepted by this node once, and is
installed again — unchanged, verified by its checksum — into the
production instance. Nothing is fetched, nothing is uploaded, no
credential is involved.

The rule this exists for: **what goes to production is exactly what was
tested.** Not "the same version", not "a rebuild of the same commit" —
the same bytes.

## Motivation

### Re-uploading is not the same as promoting

The obvious alternative is: upload the ZIP a second time, to the
production instance. It works, and it is subtly wrong. Between the test
upload and the production upload sits a human, a file manager and a
download folder — three places where "the file I tested" can quietly
become "a file". A promotion cannot get this wrong, because there is
nothing to pick: the running artifact of the test instance is named by
its checksum, and that is what installs.

It is also less work at exactly the moment when work is most dangerous:
the release.

### Why not a deploy token for production

Because that is a different question, and its answer stays no
(RFC-0019 non-goal, `oaap.apps.runtime` 2.5): a token lets a **machine**
replace what runs in a business, unattended, repeatedly. A promotion is
the opposite shape — a person, at a screen, pointing at one artifact
that already exists, once. Every promotion has a human in it, and that
is not a formality: it is the whole compensating control.

### Why the portal and not the CLI

The CLI can already do it (`oaap app install <zip> --channel production`)
and keeps that ability. But an operator who has to open a terminal for
every release will either do it rarely or automate it badly. The portal
is where the decision belongs, because that is where the person is who
is allowed to make it.

## Design

### The act

- **Who:** `server_admin` only. Not a deploy token, not an app, not a
  grant of the RFC-0019 kind: promotion cannot be delegated to a
  spendable permission, because it is exactly the decision that the
  spendable permissions are careful *not* to include.
- **From:** a **test-channel** instance whose source is an artifact
  (`kind: "artifact"`, RFC-0019) with its running package retained.
- **To:** a **production-channel** instance of the **same app id** —
  existing (an update) or a new one (the first production rollout).
- **What is copied:** the artifact file. Nothing else.

### What the target keeps

A promotion is an installation into an existing instance, so everything
that already survives a redeploy survives a promotion, and for the same
reason — it belongs to the *instance*, not to the package:

- its **own data** (separate storage; nothing is copied from test),
- its **own configuration values** (a test secret must never travel to
  production, which is why config is not part of a promotion),
- its **address(es)**, visibility groups, tile setting, rate brake,
  granted endpoints and app-to-app links.

Stating this is part of the design, not documentation polish: the fear a
promotion has to answer is "will this overwrite my production data or my
production settings", and the answer must be verifiably no.

### What is checked, on the host

The portal offers the action; the **host** decides. The spool is data,
not trust — so every rule below is re-checked where the work happens,
even when the button already checked it:

1. The source instance exists, is on the **test** channel, and its
   running artifact is present.
2. The target's **app id matches** the artifact's manifest. Promotion
   never turns instance A into app B.
3. For an existing target: the artifact's version is **higher** than
   what production runs. Equal or lower is refused with the sentence
   that says what to do instead — going back is a **rollback**
   (RFC-0019 retention), which is a different, deliberate act.
4. For a new target: the name is free and well-formed, and it is created
   **on the production channel**.
5. **Envelope review against the target** (RFC-0019 §3), not against the
   test instance. A package may be unremarkable next to its test
   instance and still widen what production is allowed to do. Widening
   is not refused here — a `server_admin` is present, which is the human
   the envelope rule asks for — but it MUST be **shown and explicitly
   confirmed** before the promotion runs. An unread confirmation is
   worse than a refusal, so the reasons are named in full.
6. Production instances **never** receive a deploy token as a side
   effect (2.5 unchanged).

### What is recorded

The target's source becomes an artifact source that names its origin:
the test instance it came from, the checksum, and the time. Two things
follow, both of them the point of the exercise:

- The portal and `oaap app list` can answer **"where does what runs in
  production come from?"** with a test instance and a checksum, not with
  a hopeful "v1.4.2".
- Retention applies as always (current plus three predecessors), so the
  way back from a bad release is the existing rollback, one click, with
  the same guarantee about bytes.

The promotion itself is logged like every other change (who, when, from
which instance, which checksum, accepted or refused).

### Interfaces

- **Portal:** on the test instance's object page, section *Deployment*:
  target (an existing production instance of the same app, or a new
  name), the envelope notes if any, an explicit confirmation, one
  button. On the production instance the origin is visible under
  *Überblick → Herkunft*.
- **CLI:** `oaap app promote <test-instance> [--to <name>] [--confirm]`,
  for the machine and for scripts that a human runs.

## Non-goals

- **No automatic promotion.** No "promote when tests pass", no schedule,
  no hook. The gate is a person.
- **No promotion from a Git-installed test instance.** There the source
  is a repository and the production path is the store or the CLI; the
  identity guarantee of this RFC ("the same bytes") is only provable for
  a retained artifact.
- **No blue/green or traffic splitting.** Two instances plus a name swap
  (RFC-0018) already allow a staged rollout, and a visibility group
  (RFC-0007) already allows a pilot audience. Deciding *automatically*
  between two live versions would need per-instance telemetry, which
  this platform does not have and which is a capability of its own.
- **No config or data migration.** Promotion moves a package. Anything
  that has to move with it is a decision, not a copy.
- **No new spendable permission.** Promotion stays with `server_admin`.

## Consequences

- `oaap.apps.runtime` 2.14 gains promotion as a named path, and 2.6's
  rule "the portal creates test instances" gains its one exception: a
  production instance MAY be created by promoting an artifact this node
  already accepted, by a `server_admin`, by name.
- The reference implementation reuses the RFC-0019 machinery unchanged
  (retention, extraction, envelope review, the spool worker). Promotion
  is deliberately not new machinery — it is a new *decision* on top of
  machinery that already carries the risk.

## Open for later

- **Promotion across nodes** (test on the workbench, production on the
  customer's machine). The same idea, but it needs the artifact to
  travel and therefore an authenticated node-to-node path. Not now.
- **A record of what was tested** (who tested, against which checklist).
  Today the promotion says "this was the tested artifact"; it does not
  say what testing meant. That belongs to a Studio-side notion of a
  release, not here.

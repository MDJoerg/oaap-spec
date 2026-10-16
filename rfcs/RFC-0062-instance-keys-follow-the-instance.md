# RFC-0062: Instance Keys Follow the Instance — Revoked at Removal, Reissued at Rename, Renewed Before They Expire

- **Status:** Proposed (2026-10-16) — four decisions for Jörg (D1–D4),
  each with a recommendation. Nothing built.
- **Date:** 2026-10-16
- **Authors:** Claude (found while building RFC-0061 stage 2, measured on
  `oaap-test`), Jörg (decides)
- **Depends on:** RFC-0027 (machine principals and API keys, D3 maximum
  lifetime, D5 instance scoping), RFC-0026 (the instance id that never
  changes), RFC-0031 (the twin key), RFC-0045 (the authorization keys),
  RFC-0061 §3.2 (the case-submission key)

## Summary

The platform mints up to four API keys for an app instance's machine
principal `instance:<name>`:

- the twin key, `oaap.twin`;
- the authorization key, `oaap.authz`;
- the administration key, `oaap.authz.admin`;
- since 0.1.201, the case-submission key, `oaap.cases.submit:<name>`.

The keys live in the instance's environment and are valid for 365 days.
Nothing else about their life is managed:

- removing the instance does not revoke them;
- renaming it does not move them;
- nothing renews them.

Because identity and the twin derive the instance **from the principal's
name**, a key outlives its instance and **speaks for whatever instance
carries that name next** — measured, not inferred (§1). This RFC lets the
keys follow the instance's life:

- revoked at removal;
- reissued at rename;
- renewed before they expire;
- and the orphans already on the nodes cleaned up once.

## 1. What was measured (oaap-test, 2026-10-16, 0.1.201)

A throw-away app `keyprobe-a` was installed under the name `keyprobe`
with an authorization declaration and `cases.submit`. Its keys were saved
from the container's environment.

| step | result |
| --- | --- |
| `oaap app remove keyprobe --purge`, then the old authorization key against `/authz/effective` | **200**, answering for app `keyprobe-a`, which no longer exists |
| a **different** app `keyprobe-b` installed under the same name, old key again | **200, `app = keyprobe-b`**: the old key reads the new app's grants |
| the old case-submission key at the new instance's `/platform/cases/submit` | **201**: the case is recorded as coming from `keyprobe-b` |

Why: identity's authorization doors look the instance up as
`load_authz()["instances"][<principal name minus "instance:">]`. The twin
does the same in the registry (`resolve_instance(name)`). The record of a
removed instance stays in `authorization.json`, and a reinstall under the
same name overwrites it with the new app. The old key's principal is still
active, and the key itself is not revoked.

The twin path was **read, not measured**: it resolves the same way, so an
old twin key would write twin objects with the new app's origin. That is
the most serious of the four, because it writes data under another app's
ownership.

**Rename** (`rekey_instance`, read, not measured) moves containers,
network, deploy token and grants, but not the principal, not the
authorization record and not the case key's scope:

- After a rename, the twin refuses the instance; it looks up the old name.
- The case key fails at its door (403), because the scope names the old
  key.
- A later instance under the old name finds the old principal and gets a
  key **for the same principal** as the renamed one.

**On the nodes** (read-only scan, 2026-10-16):

- **oaap-test:**
  - 11 valid instance keys;
  - **one valid key without an instance** (`cap-bookshop-store`, `oaap.authz`);
  - 2 authorization records without an instance;
  - 6 principals without an instance, their other keys revoked by hand in
    earlier sessions;
  - first expiry **2027-09-10**.
- **oaapx01:** 4 keys, no orphans, first expiry **2027-10-04**.
- **raspberrypi, oaap-bernd, oaap-demo:** no key file at all.

**Who could use an old key:** the removed app itself. It held the key in
its environment, and so does anyone who could read that environment, for
example the author of a third-party app that a tenant removed and replaced
under the same name. No outsider learns a key from this gap alone.

**What happens at expiry:** every call fails closed. An app that checks
business authorization then denies every person, without saying why, on
the day its key turns one year old.

## 2. Proposal

### 2.1 Removal revokes (D1)

`remove_instance` revokes every key of `instance:<name>` and deletes the
principal. Identity refuses to delete a user that still holds a valid
key, so the revocation comes first. It also removes the instance's
record from `authorization.json`. This happens with **and without**
`--purge`.

Without `--purge` the instance's `instance.env` is kept for a reinstall
under the same name (RFC-0026 3.2). Its platform-owned key variables are
removed from that file:

- `OAAP_PLATFORM_KEY`,
- `OAAP_AUTHZ_KEY`,
- `OAAP_AUTHZ_ADMIN_KEY`,
- `OAAP_CASES_KEY`.

The reinstall then mints fresh keys; its install path already does so
when a variable is absent. Data ownership is not affected: the twin
derives ownership from the registry (`app:<app_id>`), and authorization
grants hang off the app and the tenant, not off a key.

Best effort, like `_authz_close_admin_door` today: if identity is down,
the removal still completes, says which keys are still valid, and the
step in §2.4 catches them at the next update.

### 2.2 Rename reissues (D2)

`rekey_instance` already recreates the instance's containers from
`instance.env`. Before it does, it:

1. revokes the old principal's keys and deletes that principal;
2. moves the authorization record to the new name;
3. mints new keys for `instance:<new name>`, including the case key with
   the new scope.

The recreated containers start with the new keys. The old name is then
free in identity too, and nothing a later instance under that name gets
is shared with the renamed one.

### 2.3 Renewal before expiry (D3)

A key that expires breaks its app silently. The daily run that already
exists for cohorts and idle instances checks every instance key. If one
expires within **30 days**, the run:

1. mints a new key;
2. writes it to `instance.env`;
3. recreates the instance's containers in the **night window** (the
   backup's stop at 03:33 on `oaapx01` is the natural moment);
4. revokes the old key once the new container is healthy.

That is one restart per instance per year, at a time the node already
takes apps down.

**Not chosen:** exempting instance keys from RFC-0027 D3's maximum
lifetime. With §2.1 and §2.2 a key's life is bounded by its instance,
which is the argument for an exemption. But a key that never expires is
the one thing D3 rules out, and the renewal costs one restart.

### 2.4 Cleaning up what already lies on the nodes (D4)

A migration step, run at `oaap update` like the others:

- revoke the valid keys of `instance:*` principals whose instance is
  gone;
- delete those principals;
- drop authorization records without an instance;
- print what it did.

It is silent when there is nothing to do. On today's fleet this touches
`oaap-test` only: one key, six principals, two records.

## 3. Not part of this RFC

- **Principals named by the instance id** (RFC-0026) instead of the name.
  That would close the name-reuse class at the root, but it is a
  migration of identity, the twin, authorization and the gateway's
  scopes. §2.1–§2.3 close the measured gaps without it.
- **Keys a person issued** (the portal's "Zugänge", RFC-0027) to a
  machine principal of their own, such as a partner's inbox key in
  RFC-0061 §5.3. Those are the tenant's to manage. They are limited to an
  instance by its key, and the same reuse question applies to them, but
  the tenant decides about them.

## 4. Security requirements

1. After `oaap app remove` (with or without `--purge`), no key of
   `instance:<name>` is valid. A test presents each one and expects a
   refusal.
2. After a rename, no key of the old principal is valid, and every
   platform key the app holds works.
3. A reinstall under a removed name never receives, or is reachable by,
   a key minted for the earlier instance.
4. No instance key expires while its instance exists; the renewal is
   logged.

## Decisions for Jörg

| | question | recommendation |
| --- | --- | --- |
| **D1** | Does removal (also without `--purge`) revoke the instance's keys, delete its principal and its authorization record, and strip the key variables from the kept `instance.env`? | **Yes.** It closes A–C of §1. |
| **D2** | Rename: reissue the keys under the new name, or rename the principal and move its keys? | **Reissue.** The containers are recreated anyway; renaming a principal would have to touch keys, the authorization record and the case scope, each a place to forget. |
| **D3** | Expiry: renew 30 days ahead with a container recreate in the night window, or exempt instance keys from the maximum lifetime? | **Renew.** One restart a year, and D3 of RFC-0027 stays without exception. |
| **D4** | Clean up existing orphans with an update step? | **Yes**, silent when nothing is found. |

## Deutsche Zusammenfassung

Die Plattform stellt jeder App-Instanz bis zu vier Schlüssel aus:

- Zwilling,
- Fachrechte,
- Verwaltung der Fachrechte,
- seit 0.1.201 die Vorgänge.

Die Schlüssel gehören dem Maschinenprinzipal `instance:<Name>` und gelten
365 Tage. Mehr regelt die Plattform an ihnen nicht: Beim Entfernen werden
sie nicht zurückgezogen, beim Umbenennen nicht umgezogen, und nichts
erneuert sie.

Weil Identity und Zwilling die Instanz **aus dem Namen des Prinzipals**
ableiten, überlebt ein Schlüssel seine Instanz und spricht für die
nächste Instanz mit demselben Namen. Das ist auf oaap-test **gemessen**:

- Nach `remove --purge` beantwortet der alte Fachrechte-Schlüssel weiter
  Anfragen (200).
- Ist unter demselben Namen eine **andere** App installiert, liest der
  alte Schlüssel deren Fachrechte (200, `app = keyprobe-b`).
- Der alte Vorgangs-Schlüssel legt einen Vorgang an, der als „aus der
  neuen App“ gespeichert wird (201).

Für den Zwilling ist es gelesen, nicht gemessen: Ein alter Schlüssel
würde Objekte im Namen der neuen App schreiben.

Beim Umbenennen bricht der Zwilling ab, der Vorgangs-Schlüssel ebenso,
und der alte Name hängt weiter an einem Prinzipal.

Am **10.09.2027** (oaap-test) bzw. **04.10.2027** (oaapx01) laufen die
ersten Schlüssel ab. Ab dann verweigern die betroffenen Apps ohne
Erklärung jede Fachberechtigung.

**Vorschlag:**

- **D1:** Entfernen zieht alle Schlüssel zurück, löscht Prinzipal und
  Fachrechte-Eintrag und nimmt die Schlüssel aus der aufbewahrten
  `instance.env`.
- **D2:** Umbenennen stellt die Schlüssel unter dem neuen Namen neu aus.
- **D3:** 30 Tage vor dem Ablauf erneuern, mit einem Neustart in der
  Nacht.
- **D4:** Ein Update-Schritt räumt die heutigen Waisen ab. Das betrifft
  nur oaap-test: einen gültigen Schlüssel, sechs Prinzipale, zwei
  Fachrechte-Einträge.

Nicht Teil davon: Prinzipale nach der unveränderlichen Instanz-ID zu
benennen. Das wäre die Wurzel-Lösung, aber eine große Migration.

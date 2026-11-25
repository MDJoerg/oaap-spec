# RFC-0130: Security Advisories Said Plainly, and Healed by the Node

- **Status:** **Draft (2026-11-25)** — D1–D7 asked of Jörg (§9). Nothing built.
  The facts in §1 were read the same day on `oaapx01` (reference 0.1.376).
- **Date:** 2026-11-25
- **Authors:** Jörg (the need, 2026-11-25, on a screenshot of the store on
  oaapx01: "Diese Meldungen verwirren mich. Müssen wir als OAAP aktiv werden
  oder was soll jemand machen, der genau diesen Screen im Store bekommt? Wir
  müssen hier klarer kommunizieren."), Claude (facts, design)
- **Depends on:** RFC-0071 (rebuild; this RFC is its stage 3 plus two repairs
  of its stage 1), RFC-0069 (the node's window, protections), RFC-0070 (the DSA
  reader), RFC-0080/RFC-0083 (mails, weekly report), RFC-0128 (which images a
  node keeps)
- **Related:** RFC-0085 addendum A4, D-A4.1 (c) (a newer Mosquitto), idea I-73
- **Changes (when accepted):** `oaap.apps.runtime` (the image an instance runs
  is named per instance), `oaap.core.updates` (host care: the reading, the
  rebuild by itself), `oaap.core.portal` (store cards, the instance card
  "Abbild", the instance list), `oaap.core.notifications` (one matter for a
  failed self-heal)
- **Not part of this RFC:** advisories of the host itself (RFC-0069 handles
  them); foreign apps' own code; a CVE database beyond Debian's list.

## Summary

On 2026-11-25 the store on oaapx01 showed "1 Sicherheitsmeldung" on almost
every app the platform ships. Behind it was **one** Debian advisory (DSA-6657-1,
libzstd) in the shared base `python:3.13-slim`, already fixed upstream — a
**rebuild heals it**, and the apps had promised that the node may rebuild them
(`care.rebuild: self`). Nobody had to act except the node, and the node never
did: the rebuild by itself (RFC-0071 stage 3) was never built. Worse, the count
was too small (29 containers could not be read) and right after the rebuilds the
reading said "behind upstream" for 28 instances that were not.

This RFC (1) repairs the reading — one image name per instance, a fresh upstream
answer after every build; (2) says on every card **what it means, who acts and
what happens next**, by role; (3) lets the node rebuild by itself in its window
what an author promised is safe; and (4) gives the platform's own images that
upstream no longer rebuilds a way out.

## 1. Facts (read 2026-11-25 on `oaapx01`, `oaap node care images`)

| # | Fact |
|---|---|
| F1 | 9 instances "open 1" — all **DSA-6657-1** (libzstd `1.5.7+dfsg-1`, fixed in `+deb13u1`) in `python:3.13-slim`; "will a rebuild help: likely". 29 more "unknown", 3 "behind". |
| F2 | The store card shows `open_count` = the sum of open advisories over the caller's instances of that app (`store_view.annotate_care`), labelled "N Sicherheitsmeldung(en)" — no word on what it is, who acts or whether anything happens by itself. The footnote says only "kommen aus der Abbild-Lesung des Knotens (RFC-0071)". |
| F3 | **Stage 3 not built**: every platform app declares `care.rebuild: self`, `host_care.self_heal` answers "possible", but nothing calls it on a schedule. A person had to rebuild 29 instances by hand (CURRENT_STATE 848, 16–39 s each, all healthy, then 0 open). |
| F4 | **29 containers "unknown"** with "the image this container runs was removed (a newer build took its tag)". Instances of the same app and version in several tenants run the **same tag** `oaap-app/<id>[-<svc>]:<version>`; a rebuild or install of one moves the tag. On a node with the containerd image store (oaapx01: `io.containerd.snapshotter.v1`) the untagged image is gone at once; its container runs on, but nothing can be read from it (first measured 2026-11-06, oaap-test). After the rebuilds of F3 every chat instance runs a different image and only the last one keeps the tag — the others turn "unknown" again at the next advisory list. |
| F5 | **"behind" right after a rebuild**: the reading compares the recorded base digest (`7249d558…`, what the rebuild used, equal to Docker Hub's index digest asked by hand the same minute) with an upstream answer cached since 2026-11-24 12:37 (`1b5c0692…`); upstream is asked every 24 h (`ASK_EVERY`). The rebuild did not refresh it. |
| F6 | Platform containers: `oaap-portal-1` open 1 (DSA-6657-1, heals with the next platform update); `oaap-broker-1` (`iegomez/mosquitto-go-auth:3.0.0-mosquitto_2.0.18`, Debian 12) open 5 since 2025-05-29, **= upstream** — upstream does not rebuild it, a rebuild cannot help. |
| F7 | 14 instances stay "unknown" for a reason that is not a fault: no dpkg (Alpine: BDT, Keycloak), or a base never recorded (built before 0.1.227, foreign apps without `self`). |

## 2. The reading, repaired (stage 1)

### 2.1 One image name per instance (D2)

A container runs the image **of its instance**: after the build the node tags
the result `oaap-inst/<instance-key>[-<svc>]:<version-tag>` and creates the
container from that tag. `oaap-app/<id>[-<svc>]:<version-tag>` stays as the
build's name (and its layer cache); moving it touches no running instance.

- A rebuild re-tags only its own instance; `oaap-prev/<name>[-<svc>]:prev`
  (RFC-0071) is unchanged.
- Bytes are not doubled: two tags of one image, or two images sharing all
  layers, cost the layers once.
- RFC-0128 class B counts per instance tag; class A (dangling) shrinks, because
  no running image is ever left without a name.
- Existing instances get their tag at the next recreate (update, rebuild,
  restart through the platform) — no recreate for this alone.

### 2.2 A fresh upstream answer after every build (D3)

A build that resolved its base (`base_record`) writes that digest as the
upstream answer for the reference with `asked = now`, unless a newer answer is
already there. "behind" then means what it says: upstream moved **after** the
build.

### 2.3 "unknown" is split

The word stays, the reason becomes one of three, each with its own sentence:
*nicht lesbar (kein Paketverzeichnis)* — normal for Alpine, nothing to do;
*Basis nicht erfasst* — a rebuild records it; *Abbild nicht mehr da* — should
not occur after 2.1, and if it does it is a fault the card says so.

## 3. Said plainly (stage 2)

### 3.1 One sentence per state and role (D4)

The card shows the **state**, **what it means**, **who acts** and **what
happens next**. Wording (German UI):

| State of an instance | `server_admin` | `tenant_admin` / user |
|---|---|---|
| open, rebuild helps, `self`, stage 3 on | „Basis-Update verfügbar – wird in der nächsten Pflegenacht (TT.MM., hh:mm) automatisch neu gebaut." + [Jetzt neu bauen] | „Wird vom Betreiber gepflegt – Update ist eingeplant." |
| open, rebuild helps, no `self` | „Basis-Update verfügbar – ein Neubau behebt es. Der Autor hat nicht zugesagt, dass er nur die Basis ändert: bitte erst die Testinstanz." + [Neu bauen] | „Wird vom Betreiber gepflegt." |
| open, rebuild does not help (base = upstream, no upgrade in the build) | „Wartet auf den Hersteller des Basisabbilds (seit TT.MM.). Ein Neubau hilft noch nicht." | „Wird vom Betreiber beobachtet." |
| open, foreign app | „Wartet auf den Autor der App (seit TT.MM.) – eine neue Version im Store behebt es." | same |
| healed by itself last night | „Heute Nacht neu gebaut – keine offene Meldung." (7 days) | — |
| self-heal failed | „Neubau heute Nacht fehlgeschlagen – läuft auf dem Vorgänger weiter. [Protokoll]" | „Wird vom Betreiber gepflegt." |

The store card says it once for the app, from the most urgent instance:
„1 Basis-Update – wird heute Nacht automatisch neu gebaut" instead of
„1 Sicherheitsmeldung". A filter "Pflege" keeps its values.

### 3.2 What the advisory is (D5)

The card names the package and the Debian advisory with a link to
`security-tracker.debian.org`, and its age. **No invented severity**: Debian's
list carries none; where the tracker states an urgency it may be shown later.

## 4. Healed by the node (stage 3, RFC-0071's stage 3) (D1, D7)

- **Who:** instances whose app declares `care.rebuild: self`, with a source the
  rebuild can use (`host_care.self_heal`), not held (RFC-0069), not a rehearsal.
- **When:** in the node's window, never on the day of a planned reboot, one
  instance at a time, a test instance before the production instance of the same
  app in the same tenant (RFC-0071 §4); a production instance whose test sibling
  failed tonight waits.
- **Trigger:** an open advisory **and** "rebuild helps: likely" (the base moved
  upstream, or the build upgrades OS packages — RFC-0071 §16). This widens
  RFC-0071 D3, which asked only for a moved base.
- **Afterwards:** the image is read again at once; healthy → `-prev` kept, the
  card says "heute Nacht neu gebaut"; unhealthy → back to `-prev` (RFC-0071 §5),
  a matter `care.selfheal.failed` to the node's list (D7).
- **Report:** one line in the weekly report: „N Instanzen selbst neu gebaut,
  M offene Meldungen behoben, K fehlgeschlagen."
- **By hand** stays: [Jetzt neu bauen], `oaap app rebuild`, and the store's
  „Alle neu bauen".

## 5. The platform's own images that upstream does not rebuild (stage 4) (D6)

`oaap-broker-1` runs an image upstream stopped rebuilding. A rebuild cannot heal
it. The platform builds its own: `oaap-broker` on Debian 13 with a current
Mosquitto and go-auth (RFC-0070's image step), measured against the RFC-0085 A4
findings (go-auth cache, bridge watchdog, `start_type` options). Until then the
card says „Wartet auf ein eigenes Broker-Abbild (geplant)" and the open count of
platform containers is shown apart from the apps'.

## 6. Who may do what

| Who | May |
|---|---|
| the node | rebuild by itself what §4 allows, in the window |
| `server_admin` | everything; rebuild now; switch self-heal off per node or per instance (a hold, RFC-0069) |
| `tenant_admin` | see the sentence for their instances; ask the operator (RFC-0109 requests) |
| user | nothing changes for them; the card is for administrators |

## 7. Security requirements

1. Self-heal only with the author's promise (`self`) and only from the recorded
   source; never from a moved Git ref.
2. Never two rebuilds at once on a node; never during a deploy of the same
   instance (the deploy lock).
3. A failed self-heal leaves the instance on its predecessor and says so.
4. Per-instance tags never let one instance's rebuild change what another runs.
5. The wording never claims more than the reading knows: "unknown" stays
   unknown, no invented severity.

## 8. Stages

| Stage | What | Measured by |
|---|---|---|
| **1** | per-instance tag (2.1), fresh upstream after a build (2.2), three reasons for "unknown" (2.3) | `oaap-test`: two instances of one app version, rebuild one — the other still readable after a new advisory list; "fresh" right after a rebuild |
| **2** | wording by state and role (3.1), package and DSA link (3.2) | portal as server_admin and tenant_admin on `oaap-test` |
| **3** | self-heal in the window, matter, weekly line (§4) | `oaap-test` with a real window night: an image with an open advisory healed by itself; a forced failure falls back and mails |
| **4** | own broker image (§5) | `oaap-test` broker swapped, fleet bridge and go-auth cache measured |

## 9. Decisions asked of Jörg

- **D1 — The node rebuilds by itself in its window (stage 3)?**
  (a) yes, for every instance with `self`, on by default, `server_admin` can
  switch it off per node or per instance (recommended);
  (b) yes, but only after the `server_admin` switches it on per node;
  (c) no — the node only mails "Neubau empfohlen".
- **D2 — One image name per instance?**
  (a) yes, `oaap-inst/<instance>[-<svc>]:<tag>` (recommended — the only fix for
  F4 on a containerd node);
  (b) no, rebuild all instances of an app version together (touches other
  tenants outside their window);
  (c) no, accept "unknown" for siblings.
- **D3 — A build refreshes the upstream answer of its base?** (a) yes
  (recommended); (b) ask upstream again after every build (a network call per
  build).
- **D4 — The wording of §3.1 by state and role?** (a) as in the table
  (recommended); (b) only for `server_admin`, tenants see nothing; (c) changes
  to the table (Jörg's words).
- **D5 — Show package and Debian link, no severity?** (a) yes (recommended);
  (b) also a severity from the Debian tracker where it has one.
- **D6 — An own broker image (stage 4)?** (a) yes, together with D-A4.1 (c)
  (recommended); (b) wait for upstream, show "wartet auf Hersteller".
- **D7 — A failed self-heal mails?** (a) yes, one matter `care.selfheal.failed`
  to the node's list, plus the weekly line; success only in the weekly report
  (recommended); (b) every self-heal mails; (c) only the weekly report.

## Deutsche Zusammenfassung

**Anlass:** Am 25.11. zeigte der Store auf oaapx01 bei fast allen unseren Apps
„1 Sicherheitsmeldung“. Dahinter stand **eine** Debian-Meldung (libzstd) im
gemeinsamen Python-Basisabbild, upstream schon behoben. Ein Neubau heilt sie.
Unsere Apps erlauben dem Knoten das Neubauen (`self`), aber der Knoten tut es
nie, weil RFC-0071 Stufe 3 fehlt. Dazu kam: Die Zahl war zu klein (29 Container
nicht lesbar), und direkt nach dem Neubau stand fälschlich „hinter upstream“.

**Ursachen:**
- **Geteilte Abbild-Namen:** Instanzen derselben App-Version in mehreren
  Mandanten teilen einen Namen. Baut eine neu, verliert die andere ihren Namen,
  und auf oaapx01 (containerd) ist das Abbild dann sofort weg. Die Prüfung sieht
  nichts mehr. Nach unseren heutigen Neubauten kommt das mit der nächsten
  Meldungsliste wieder.
- **Veralteter Upstream-Vergleich:** Der Upstream-Stand wird nur alle 24 Stunden
  gefragt, ein Neubau aktualisiert ihn nicht.

**Vorschlag:**
1. **Prüfung reparieren:** ein Abbild-Name je Instanz, nach jedem Bau den
   Upstream-Stand mitschreiben, „unbekannt“ mit drei klaren Gründen.
2. **Klartext je Rolle:** Statt „1 Sicherheitsmeldung“ steht zum Beispiel
   „Basis-Update – wird heute Nacht automatisch neu gebaut“. Mandanten lesen
   „Wird vom Betreiber gepflegt“. Paket und Debian-Link werden genannt, ein
   Schweregrad wird nicht erfunden.
3. **Selbstheilung:** Der Knoten baut nachts im Pflegefenster selbst neu, Test
   vor Produktiv, Rückfall auf den Vorgänger. Ein Fehlschlag wird gemailt, im
   Wochenbericht steht eine Zeile.
4. **Eigenes Broker-Abbild:** Das Mosquitto-Abbild wird upstream nicht mehr neu
   gebaut. Wir bauen ein eigenes, zusammen mit D-A4.1 (c).

**Deine Entscheidungen:** D1–D7 (§9), jeweils mit Empfehlung (a). Gebaut ist
nichts.

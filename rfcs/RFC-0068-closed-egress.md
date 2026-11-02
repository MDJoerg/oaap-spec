# RFC-0068: Closed Egress — A Tenant's Instances Start No Connection of Their Own

- **Status:** **Accepted (2026-11-02, D1–D7 as recommended).** Stages 0, 1 and 2 measured
  on `oaap-test` (§11, §12), reference 0.1.217, not rolled out. Stages 3 and 4 open.
- **Date:** 2026-11-01
- **Authors:** Claude (measurement, proposal), Jörg (requirement, decides)
- **Depends on:** RFC-0016 (instance networks; its Q4 left egress on and named this as a
  later capability), RFC-0033 (destinations), RFC-0015 (non-HTTP endpoints), RFC-0030
  (rehearsal), RFC-0029 D5b (an exception needs a reason), RFC-0044 (remote access),
  `oaap.ai.gateway` (the light), RFC-0060 (tunnel)
- **Changes:** `oaap.core.tenant` and `oaap.apps.runtime`: a tenant rule and an exception
  per instance; `oaap.net.destinations`: a closed instance binds only allowed targets
- **Origin:** idea I-34, third step of the order proposed in I-38. Also for Bernd's
  complaints and anything else holding personal data.

## Summary

Today an instance can reach everything its node can. An operator who promises "this
tenant's data stays here" has nothing to hold that promise with.

This RFC gives a tenant one rule, **closed egress**: its instances start no connection
of their own. What they need outside goes through a named, listed door, a destination.
One page says every way data can still leave. That page is half of the proposal: the
rule closes one way out, and an operator must not take it for closing all of them.

## 1. What an instance can do today (measured, 2026-11-01)

`oaap-test`, instance `vuebung-kp`, from inside the container:

| Target | Normal network | `docker network create --internal` |
|---|---|---|
| Internet, `1.1.1.1:443` | **open** | no route |
| Router, `10.10.10.1:53` | **open** | no route |
| Neighbouring node, `10.10.10.75:22` | **open** | no route |
| The node's LAN address, SSH and a gateway port | **open** | no route |
| Docker's default bridge, `172.17.0.1:22` (the node's SSH) | **open** | no route |
| The instance bridge's own address, `192.168.208.1:22` (the node's SSH) | **open** | **open** |
| DNS of an outside name | answers | **no answer** |
| DNS of the gateway; a platform door through the gateway | works | **works** |
| Request from outside through the gateway | works | **works** |

Three results decide the design:

1. **An internal network does almost all of it**, without a firewall rule, and it also
   stops DNS, the usual way to smuggle data past a port rule. The platform's doors stay
   usable because an app reaches them through the gateway's name on its own network.
2. **The node stays reachable through the bridge address.** An internal network has no
   route out, but that one address is the node itself. Every service listening on all
   interfaces can be reached; SSH was. It needs a rule of its own (§3.2).
3. **A second ordinary network opens everything again.** Attached as an app-to-app link
   is attached today, the same container reached the internet, the router and the
   neighbour at once. Every network a closed instance joins must be internal (§3.3).

IPv6 had no route in either case on this node; that is not a finding about other nodes.

## 2. The rule

- A tenant is **open** (default, as today) or **closed**.
- A closed tenant's instances start no connection of their own: not to the internet,
  not to the LAN, not to the node.
- **An instance may be excepted**, by name, with a reason, visible on the page, as with
  a backup exclusion (RFC-0029 D5b). A workstation with a cloud assistant is the typical
  case. An exception never hides: it is the first line of §5.
- The rule is **not in the manifest**. An app cannot ask for it and cannot ask out of it.

There is only one level, not "node" and "LAN" apart. A target in the LAN is an allowed
destination (§4) like any other, and that is the distinction I-34 asked for.

## 3. The mechanism

### 3.1 The instance network

`ensure_app_network` is the one place that creates an instance network. For a closed
instance it creates it `--internal`. Docker's `Internal` flag cannot be changed, so
closing a running instance means removing and recreating its network: stop, swap, start,
reconnect the gateway. Measured: a few seconds of downtime. The act asks for confirmation
and names the instances it stops.

The flag is read back from Docker, not remembered: `oaap status` and §5 say what Docker
says. A closed instance on an open network is shown as a fault, and the instance does
**not start** on the wrong network (fail closed).

### 3.2 The node

One rule on the node drops what arrives on a closed bridge: `INPUT -i oaapc+ -j DROP`, for
IPv4 and IPv6. Every closed network, instance or link, gets a bridge named `oaapc<hash>`.

This replaces a rule per subnet, which this RFC first proposed. Docker starts these
containers at boot on its own, before anything of ours could list subnets, and a subnet
can change. The rule stays one line, and the unit `oaap-egress.service` sets it before
`docker.service` on every node. Without a closed tenant no bridge carries the prefix and
the rule matches nothing.

Since Docker restarts containers without asking anyone, "cannot be set" has two answers:
a door that starts a closed instance refuses, and a sweep every minute stops one that is
running while the rule or a network is wrong. A rule that disappears is set again and
said in the tenant log, because the bridge was open for that time. So a closed instance
can be exposed for up to about a minute after someone with root on the node removes the
rule or attaches a network by hand. That is the honest limit of this mechanism.

The same reach exists for **every open** instance on every node today; closing that for
all is a separate question and not part of this RFC.

### 3.3 Everything else an instance can join

| Way | With a closed instance |
|---|---|
| App-to-app link (`setup_link_network`) | the link network is internal; a link to an open instance is allowed and shown, since that instance can pass data on |
| Non-HTTP endpoint (`-p`, RFC-0015) | refused while closed: it does not work on an internal network, and it is a way in that bypasses the gateway |
| Tunnel, `tun`, `through` (RFC-0060) | refused while closed, unless excepted: it is a route out by construction |
| Remote-access peer (RFC-0044) | allowed and shown: a person in the instance network can carry data out. An open access blocks moving the instance to another network; close it first |
| Rehearsal (RFC-0030) | **inherits the rule**: it holds a copy of the production data |
| New instance in a closed tenant | closed from the first start |

An app that needs the internet at runtime then simply fails at that call. That is the
rule working; the page says which instance is closed. Building an image is not affected:
it happens outside the instance network and holds no instance data.

## 4. What an instance may still reach

**Only destinations** (`oaap.net.destinations`). A destination is already a named target
behind the gateway, with its credential held by the platform, bound per instance. So the
allowed list exists and needs no new concept: the local AI node is one destination.

- A closed instance binds a destination only if its target is **allowed for the tenant**.
  Allowing one is an act by `server_admin` with a reason.
- Closing a tenant whose instances already hold bindings lists them, and each must be
  settled first: allowed or unbound. Nothing is silently kept or silently cut.
- **A `tcp` destination cannot be used by a closed instance, and cannot be allowed.** It is
  a handover (`oaap.net.destinations` 2.4): the app gets host, port and credential and
  connects by itself, and a closed instance has no route for that. No credential goes into
  its container. Something that needs SMTP or a database outside goes through an http
  service, or the instance needs an exception. A `through` destination is refused for the
  reason of §3.3.
- The rule is asked at the moment of use too. A binding can be older than the closing,
  restored or adopted, so the listener answers such a call with 403 and a sentence.
- **The AI gateway.** A key's light (`oaap.ai.gateway`) already caps what a consumer may
  use. A closed instance's key must be `green`, the only light where data stays. How the
  platform enforces that against a gateway that is an ordinary app is to be measured in
  stage 3, not assumed here.

## 5. The page: every way out

`oaap tenant egress <label>` and the same in the portal, for the tenant's admin and the
server admin, each read from its source at that moment:

1. instances with an exception, with their reason
2. allowed destination targets, with the instances bound to them
3. links to instances of another tenant or to open instances
4. public routes: whoever asks gets an answer, without a login
5. remote-access peers
6. AI: which instance uses which light
7. backups that leave the node, and where to
8. the faults: a closed instance whose network is not internal, a missing node rule

**What this rule does not do, and the page says so:** a person can copy out what they can
read. A public route serves whatever the app serves. A cooperating instance reached
through a public route or a link can pass data on. An off-site backup leaves the node.
The gateway cannot tell what a request carries (`oaap.ai.gateway`, RFC-0065 §9.3).

## 6. Who may do what

| Act | Who | Why |
|---|---|---|
| Close a tenant | `tenant_admin` or `server_admin` | tightening is safe, and it is their data |
| Open a tenant, except an instance, allow a target | `server_admin`, with a reason | the promise must not be undone by the one account most likely to be asked to |
| Read the page | both | a promise one cannot check is not a control |

All of it in the tenant log.

## 7. Stages

| Stage | Content | Measured on |
|---|---|---|
| **0** | Does an internal network hold? (§1) | done, `oaap-test` |
| **1** | Spec; tenant rule, exception, internal network, node rule, links, rehearsal, refusals, CLI | done, `oaap-test` (§11); `oaap update` itself after the push |
| **2** | Destinations: allowed targets, existing bindings settled first; a real LAN target | done, `oaap-test` (§12) |
| **3** | The AI gateway's light for a closed instance | `oaap-test`, local model only |
| **4** | The page in the portal (the CLI of §5 grows along stages 1–3) | `oaap-test`, real browser |

Nothing goes to another node without Jörg's word.

## 8. Not part of this RFC

- Closing the node's reach for **open** instances (§3.2).
- Inspecting content, or data-loss prevention of any kind.
- Egress rules per port or domain. A list of domains is a proxy with a policy, and it
  would need its own reasons. Destinations are the one door for now.
- An audit trail per document (I-36).

## 9. Decisions (Jörg)

| # | Question | Recommendation |
|---|---|---|
| **D1** | One rule per tenant, with named exceptions per instance, not in the manifest | yes |
| **D2** | One level, closed or open; a LAN target is an allowed destination | yes |
| **D3** | Mechanism: internal network plus node rule, read back from Docker, fail closed | yes |
| **D4** | Destinations are the only way out; no list of domains or ports | yes |
| **D5** | `tenant_admin` may close; only `server_admin` opens, excepts or allows, with a reason | yes |
| **D6** | Backups: the rule does not change them; the page names any that leave the node | yes, but see below |
| **D7** | A rehearsal inherits the rule; tunnels and non-HTTP endpoints are refused while closed | yes |

**On D6.** It is the one decision where the rule's name promises more than it does. A
tenant called closed whose backups go off-site does hold data elsewhere. Blocking that
automatically would trade a promise for lost data, so the recommendation is to show it
and let the operator decide per tenant with the existing exclusion.

**Checked in the code (2026-11-02), not on a target:** a node's archives are unencrypted
at the source. `ops/backup-push.sh` encrypts before sending only with `--age-recipient`.
A vault (RFC-0053) is protected by its mode: `luks` encrypts the disk, `luks+age` and
`age` the archives. The node cannot see an arrangement made by hand elsewhere, and the
page says so. The copies on the Synology of `oaapx01` have not been looked at. So a closed
tenant's off-site data is only as protected as that one arrangement, and the operator has
to look at it.

## 10. Security requirements (additions)

1. A closed instance MUST NOT start on a network Docker does not report as internal.
2. Every network a closed instance joins MUST be internal.
3. Without the node rule a closed instance MUST NOT start.
4. Opening, an exception and an allowed target MUST carry a reason and appear in the
   tenant log.
5. A rehearsal of a closed instance MUST be closed.
6. Nothing in a manifest can change any of this.

## 11. Stage 1 as measured (2026-11-02)

`oaap-test`, reference 0.1.217 by hand copy, tenant `abfl`, instance `abfl-a`. Every line of
§1 was measured again from inside the container.

| Target | Open | Closed | After a real reboot |
|---|---|---|---|
| Internet, router, neighbouring node | open | no route | no route |
| The node's LAN address, Docker's default bridge | open | no route | no route |
| Own bridge address, SSH | open | **dropped by the rule** | dropped |
| Own bridge address, ports 80 and the instance's own | open | dropped | dropped |
| DNS of an outside name | answers | no answer | no answer |
| DNS of the gateway, platform door (identity answers) | works | works | works |
| Request from outside through the gateway | works | works | works |

- **The rule does the work.** With the rule deleted by hand, the bridge's SSH is open again;
  with it, dropped. Published ports on the bridge stay dropped without it, by Docker.
- **Bait.** A second ordinary network attached by hand reached the internet, the router and
  the neighbour at once. `oaap status` said FAULT, and the real timer stopped the instance
  after 30 s, logged. `--close --yes` brought it back.
- **Boot.** Rule set at 07:17:12, `dockerd` started at 07:17:13, the instance at 07:17:16. All
  29 instances up. Other instances of open tenants keep the internet.
- **Doors that recreate.** Restart, redeploy with a new version and a package install stay
  internal. Closing took 1.9 s to the end of the command. A hand-made wrong network:
  restart refused, instance down, `oaap status` DEGRADED, `--close --yes` heals.
- **Update path.** Gateway recreated and `migrate.sh` run: 27 gateway links restored, the
  instance reached again, still internal. No container of an open tenant changed when
  `migrate.sh` first ran on this version. **`oaap update` itself is not measured**, because
  it pulls from Git and this is not pushed.
- **Rehearsal.** A real rehearsal of an **excepted** source: source on an open network,
  rehearsal internal with every line of §1 closed, and an exception for it refused. Its
  archive was made by hand and holds only that instance, not a node backup.
- **Link.** To an instance of an open tenant: the link network is internal, the closed end
  stays closed, the partner answers by its name (the app's own 401) and keeps its internet.
- **Remote access, `forward`.** The connect service joins, the closed end stays closed, the
  page names the access, moving the instance is refused until it is closed.
  The `wireguard` shape on an internal network is **not measured**.
- **Tests.** `test_closed_egress.py` drives a replica of Docker that keeps networks; 38
  mutations of the code all turn it red, after a run without mutation stayed green.

**Not measured:** other nodes, IPv6 with a real route (this node has none), `tenant_admin`
closing through a door of its own (stage 4; the function holds the rule, only the CLI
reaches it, and the CLI is root), endpoints and tunnels on the real node (refused in the
test; the measuring package declares neither), an adopted tenant staying closed (its
record travels whole, read in the code), the page in a browser.

**Found on the way, not part of this RFC.** Docker's default address pools hold 31 networks
(15 × /16 and 16 × /20), and `bridge` and `oaap_default` take two. So **no node holds more
than 29 instances and links**: the next `docker network create` fails with "all predefined
address pools have been fully subnetted". `oaap-test` has one network left. A cohort
(RFC-0046) or a closed tenant with many links reaches it first. It needs
`default-address-pools` in `daemon.json`, which is a node decision.

Also seen: `oaap app restart` calls the recreate without the instance's endpoints, so a granted
non-HTTP endpoint looks lost after a restart. Read in the code, not measured, not changed.

## 12. Stage 2 as measured (2026-11-02)

`oaap-test`, same instance, closed. The target is `http://10.10.10.136/`, the gateway of the
`raspberrypi` node in the LAN, asked only for `/`.

| Call from inside the closed instance | Answer |
|---|---|
| Directly to the target | no route |
| Through the destination, not bound | 403 from the gateway |
| Binding it, not allowed | refused, names the way to allow |
| Through the destination, allowed and bound | **303 from the target's own service** (`gunicorn`, `/auth/login`) |
| Directly to the target, at that moment | no route |
| Internet, router, another LAN node, at that moment | no route |
| Through a need not bound | 403 from the gateway |
| Allowance taken out of the file by hand, binding left | 403 with the sentence; the page names it as a fault |

- **Taking it back** is refused while a closed instance is bound. Allowing needs a reason
  and is in the tenant log with the target and the reason.
- **Existing bindings.** An excepted instance bound to a destination that is not allowed: ending
  the exception is refused and names the binding, the network stays as it was. Unbound, it
  goes through.
- **A `tcp` destination:** binding refused, allowing refused.
- **After moving the instance and after recreating the gateway** the call still works. Docker gave
  the freed range back to the same network, so a **changed range was not seen here**;
  `test_destinations.py` covers that with a replica.
- **Tests.** 134 checks, and all 18 new mutations turn them red, as do the 38 of stage 1.

**Not measured:** a target behind `via`, a destination with a credential or carrying the
person on a closed instance (the check comes first and does not depend on the kind of
authentication, read in the code), the portal's bind button (it calls the same function).

**What an allowed target means.** The instance can send that target whatever it holds. Allowing
a target is the decision that this data may go there, which is why it has a reason and stands
on the page.

## Deutsche Zusammenfassung

**Der Befund.** Heute erreicht eine Instanz alles, was ihr Knoten erreicht: Internet,
Router, Nachbarknoten, sogar den SSH-Port des Knotens. Wer zusagt „die Daten dieses
Mandanten bleiben hier“, hat nichts, womit er das halten kann.

**Der Vorschlag.** Ein Mandant kann **geschlossen** sein: Seine Instanzen bauen von sich
aus keine Verbindung auf. Was sie draußen brauchen, läuft über eine benannte Destination,
etwa den KI-Knoten im LAN. Einzelne Instanzen können mit Begründung ausgenommen werden.
Eine Seite nennt alle Wege, auf denen Daten trotzdem hinauskommen. Sie ist die Hälfte des
Vorschlags, denn die Regel schließt nur einen Weg.

**Gemessen.** Ein internes Docker-Netz sperrt Internet, LAN, Nachbarn und auch DNS nach
außen; Plattformtüren und der Weg von außen durchs Gateway gehen weiter. Zwei Lücken
bleiben: Über die eigene Bridge-Adresse ist der Knoten erreichbar, das braucht eine eigene
Regel, die noch nicht gemessen ist. Und ein normales zweites Netz, so wie App-Links heute
angelegt werden, macht alles wieder auf. Darum muss jedes Netz einer geschlossenen Instanz
intern sein.

**Was die Regel nicht tut.** Ein Mensch kann kopieren, was er lesen darf. Eine öffentliche
Route liefert, was die App liefert. Eine Sicherung außer Haus verlässt den Knoten. Das
alles steht auf der Seite, damit niemand „geschlossen“ für mehr hält, als es ist.

**Deine Entscheidungen, D1–D7 (Empfehlung jeweils ja).** D1 eine Regel je Mandant,
Ausnahmen je Instanz, nicht im Manifest. D2 nur offen oder geschlossen, ein LAN-Ziel ist
eine erlaubte Destination. D3 internes Netz plus Knotenregel, aus Docker zurückgelesen,
im Zweifel startet die Instanz nicht. D4 Destinations sind der einzige Weg hinaus, keine
Domainlisten. D5 schließen darf der Mandanten-Admin, öffnen, ausnehmen und Ziele erlauben
nur der Server-Admin, mit Begründung. D6 Sicherungen ändert die Regel nicht, die Seite
nennt jede, die den Knoten verlässt. Das ist die heikelste Entscheidung: Ob Kopien außer
Haus verschlüsselt sind, habe ich noch nicht geprüft. D7 eine Generalprobe erbt die
Regel, Tunnel und Nicht-HTTP-Endpunkte werden abgelehnt, solange geschlossen ist.

**Stufen.** 0, 1 und 2 gemessen · 3 KI-Licht · 4 Seite im Portal. Nichts geht ohne dein Wort
auf einen anderen Knoten.

**Stufe 2 (gemessen).** Eine geschlossene Instanz erreicht ein Ziel nur noch über eine erlaubte
Destination. Direkt zum Pi im LAN hatte sie keine Route, durch die Destination antwortete sein
Dienst, und Internet und andere LAN-Knoten blieben zu. Erlauben darf nur der Server-Admin, mit
Begründung. Eine alte Bindung ohne Erlaubnis lehnt das Gateway im Moment des Aufrufs ab.
**Folge, die du kennen solltest:** TCP-Destinations gehen auf einer geschlossenen Instanz nicht,
also auch kein SMTP und keine Datenbank draußen. Die App würde sich selbst verbinden, und dafür
hat sie keine Route. So etwas läuft über einen HTTP-Dienst oder braucht eine Ausnahme.

**Angenommen am 02.11. (D1–D7 wie empfohlen), Stufe 1 gemessen.** Die Knotenregel ist anders
als zuerst vorgeschlagen: eine einzige Zeile für alle geschlossenen Netze, gesetzt vor dem
Docker-Start, weil Docker die Container beim Booten selbst startet. Eine Prüfung jede Minute
stoppt eine Instanz, die nicht wirklich geschlossen ist. Wer Root auf dem Knoten hat, kann eine
Instanz also für bis zu etwa eine Minute öffnen, das ist die ehrliche Grenze. Sicherungen
außer Haus (D6): An der Quelle sind die Archive unverschlüsselt. Die Kopien auf der Synology
von `oaapx01` habe ich nicht angesehen.

**Nebenbefund.** Kein Knoten fasst mehr als 29 Instanzen und Links, dann gehen Docker die
Adressbereiche aus. `oaap-test` hat noch ein freies Netz.

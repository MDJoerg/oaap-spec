# oaap.core.host — Platform Installer & Node Baseline

- **ID:** `oaap.core.host`
- **Version:** 0.1.0
- **Maturity:** draft
- **Based on:** RFC-0001 (initial capability set), RFC-0002 (bootstrap
  security), RFC-0003 (installer modes, node health)

## 1. Purpose

`oaap.core.host` takes a **prepared operating environment** to a
**running OAAP platform** and hands over to the web portal for all
further setup. The hard prerequisite is only a supported Linux with
administrative access (provider-defined, e.g. Debian stable for the
reference); the container runtime is either already present or — with
explicit consent — installed by the installer itself. Onboarding MUST be as simple as
consumer NAS or router setup: run one installer, open one URL, create the
first admin. The capability also provides the minimal node-local baseline
(health status, version) that every node of a platform carries.

## 2. Interface

### 2.1 Installer modes

Per RFC-0003 the installer has three modes:

| Mode          | Meaning                                             | Status in 0.1 |
| ------------- | --------------------------------------------------- | ------------- |
| `bootstrap`   | Create a new platform on this machine (controller)  | specified     |
| `join`        | Attach this machine to a platform as a worker       | reserved      |
| `remote join` | Controller provisions a worker over SSH, from the portal | reserved |

An installer MUST reject reserved/unknown modes with a clear,
human-readable message. `bootstrap` is the default mode.

### 2.2 Bootstrap flow

A conformant installer MUST perform these steps in order:

1. **Runtime provisioning (optional)** — if the container runtime is
   missing, the installer SHOULD offer to install it (interactive
   confirmation or an explicit configuration flag; never silently).
   Without consent, the missing runtime is a preflight failure. This
   keeps the effective prerequisite down to "supported Linux with
   administrative access". Which runtimes can be provisioned is
   provider-defined (reference: Docker Engine; Podman is a candidate,
   see ADR-0004).
2. **Preflight** — verify the operating environment: OS baseline
   present, container runtime available, sufficient resources (providers
   MUST document their minimums), required ports free. On failure:
   report all problems in human-readable form and terminate **without
   changing the system** (a runtime installed in step 1 with consent
   remains — it is an explicitly requested change).
3. **Install core** — install and start the core capabilities
   `oaap.core.gateway`, `oaap.core.identity`, `oaap.core.portal`. These
   ship with the installer; they are never fetched from an app store
   (bootstrap problem — the store itself needs the core).
4. **Generate secrets** — all platform secrets are generated locally and
   randomly, unique per installation. There are **no default
   credentials** of any kind.
5. **Hand over** — print the setup URL together with a **one-time setup
   token** to the console. The portal's first-run wizard requires this
   token and creates the first admin user; until that user exists the
   platform serves nothing else (RFC-0002).

Running `bootstrap` on a machine that already hosts a platform MUST NOT
destroy or reconfigure anything; the installer terminates with a clear
message.

### 2.3 Node commands

Every node provides a local command-line entry point (reference name:
`oaap`; providers MAY rename but MUST provide equivalents):

- `oaap status` — one-screen health summary of **this node**: core
  services up/down, disk space, platform version, and (on workers, later)
  connection state to the controller. Intended for technicians and
  service partners; end users consume health through the portal, which
  is responsible for whole-landscape health (RFC-0003).
- `oaap version` — platform version of this node.
- `oaap setup-token` — print the setup URL and one-time setup token
  again, for finishing an interrupted installation (e.g. over SSH when
  the console output was lost). Only valid while the first admin does
  not yet exist; once setup is completed the command MUST refuse and
  say so. Requires local administrator privileges.
- `oaap uninstall [--purge] [--yes]` — remove the platform from **this
  node**: stop and remove all core services and platform artifacts so
  that a fresh `bootstrap` is possible afterwards. User data is
  **kept** by default; `--purge` additionally deletes all platform
  data. The command MUST require an explicit confirmation unless
  `--yes` is given, and MUST require local administrator privileges.
- `oaap update` — **reserved**. Platform updates are performed by a
  single update engine on the node (specified in a future update
  capability) with three triggers: the portal (default for end users),
  a scheduler (automatic updates), and this command (technicians,
  service partners, and recovery when the portal is unavailable).
  Until that capability exists, implementations MUST reject the
  command with a clear message.

### 2.4 Handover contract

After successful bootstrap, **all** further administration happens in
the portal. The installer performs no post-setup configuration and is
not needed again until a `join` or reinstall.

## 3. Configuration

Configurable at install time (sensible defaults for everything):

- HTTP/HTTPS ports of the gateway (default 80/443)
- Data directory for all platform state (provider-defined default)
- Hostname/IP used in the printed setup URL

Everything else is configured in the portal after setup.

## 4. Security requirements

- No default passwords or preshared secrets; every secret is generated
  locally at install time.
- Until the first admin exists, only the setup wizard route is reachable
  and it requires the one-time setup token; every other route is denied
  (default deny, RFC-0002).
- The setup token is invalidated the moment the first admin is created;
  the wizard is disabled afterwards.
- The installer MUST NOT transmit any data off the machine (no
  telemetry, no registration) — the platform works fully offline after
  the installation artifacts are available.

## 5. Conformance tests (described)

1. **Happy path**: on a freshly prepared machine, `bootstrap` exits
   successfully, prints setup URL and token; the wizard is reachable at
   the URL.
2. **Default deny before admin**: before the first admin exists, every
   route except the wizard is denied.
3. **Token required**: the wizard refuses to run without the valid
   setup token.
4. **Wizard closes**: after admin creation, login works and both wizard
   and token are permanently invalid.
5. **Idempotence**: re-running `bootstrap` on an installed system
   changes nothing and says so.
6. **Preflight safety**: with a missing prerequisite (e.g. no container
   runtime), the installer reports the problem and leaves the system
   unchanged.
7. **Node status**: after bootstrap, `oaap status` reports all core
   services healthy; stopping a core service is reflected on the next
   invocation.
8. **Offline**: bootstrap and operation succeed without internet access,
   given locally available installation artifacts.
9. **Uninstall round-trip**: `oaap uninstall --yes` removes the platform;
   a subsequent `bootstrap` on the same machine succeeds. Without
   `--purge`, platform data survives the round-trip; with `--purge`,
   no platform data remains.
10. **Token recovery**: before the first admin exists, `oaap setup-token`
    prints the valid setup URL and token; after setup is completed it
    refuses with a clear message.
11. **Runtime provisioning**: on a supported Linux without a container
    runtime, the installer offers to install one; with consent the
    subsequent bootstrap succeeds, without consent preflight fails and
    the system is unchanged.

## 6. Dependencies

None — `oaap.core.host` is the foundation. It **bootstraps**
`oaap.core.gateway`, `oaap.core.identity`, and `oaap.core.portal`, which
MUST be part of every provider's installer distribution.

## 7. Maturity

`draft` — becomes `beta` once the reference implementation passes the
described conformance tests end-to-end.

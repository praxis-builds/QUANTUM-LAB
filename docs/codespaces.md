# Running the dashboard in GitHub Codespaces

Click **Open in GitHub Codespaces** in the README (or go to
<https://codespaces.new/praxis-builds/QUANTUM-LAB?quickstart=1>). `.devcontainer/devcontainer.json`
builds Python 3.12 + Node 20, installs the core extra plus `cryptography`, starts the dashboard on
port 8765 with `--codespaces`, and opens it in your browser. The first build takes a few minutes.
If the tab doesn't open, use the **Ports** panel (globe icon next to 8765). To restart:

```bash
.venv/bin/python -m praxis_quantum_lab.dashboard_server --port 8765 --codespaces
```

## What `--codespaces` changes (and doesn't)

- The server still binds `127.0.0.1` only.
- It reads `CODESPACES`, `CODESPACE_NAME` and `GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN` and refuses
  to start outside a codespace or on unexpected values.
- It then accepts two extra Hosts: this codespace's own forwarded name,
  `<codespace-name>-8765.<forwarding-domain>`, and `localhost:8765` (the loopback name the port
  forwarder may connect with), plus the forwarded `https://` Origin. Every other host, every
  foreign origin, any `X-Forwarded-Host` other than this codespace's, and cross-site fetches are
  still rejected (`tests/test_dashboard_codespaces.py`). A rejected Host is printed to the server
  log (`/tmp/dashboard.log`), never in the response, so a mismatch can be diagnosed.
- Codespaces forwards ports **privately** by default (only the codespace owner can open them).
  Keep it that way: the dashboard is built for one trusted user, not public hosting.

**First real run (2026-10-02):** the forwarded name alone was refused ("Only the local dashboard
host is allowed"), so the forwarder does not pass the public host name through as `Host`. The
loopback name is now accepted as well. If it still fails, `cat /tmp/dashboard.log` shows the Host
that arrived.

## The static showcase (GitHub Pages)

`tools/build_site.py` renders the 33 lessons, the case study and the tool guides, and copies the
committed scanner and readiness reports. `.github/workflows/pages.yml` publishes it on every push
to `main` to <https://praxis-builds.github.io/QUANTUM-LAB/>. One-time setup by the repo owner:
**Settings → Pages → Build and deployment → Source: GitHub Actions**.

The site also has a **live Circuit Playground** at `/playground/` with the Mosca calculator. It is the
dashboard's own UI code (`playground.js`, `security.js`) with a browser backend instead of the
Python server: `circuit_sim.js`, a JavaScript port of `circuit_playground.py` whose states match
the Python ones to 1e-12 (`tests/js/circuit_sim.test.js`), and presets exported from Python when the
site is built. Shots come from a seeded browser random generator and are labelled "browser
sampling, not Aer", so counts differ from the dashboard's for the same seed. No script is loaded
from anywhere else, and nothing is sent anywhere. Bell Lab and the Security Lab's Aer simulations
still need Python.

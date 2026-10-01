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
- It then accepts exactly **one** extra Host, `<codespace-name>-8765.<forwarding-domain>`, and only
  with its `https://` Origin. Every other host and origin is still rejected
  (`tests/test_dashboard_codespaces.py`).
- Codespaces forwards ports **privately** by default (only the codespace owner can open them).
  Keep it that way: the dashboard is built for one trusted user, not public hosting.

**Not yet verified inside a real codespace.** The mode is tested with simulated requests carrying
the forwarded Host and Origin headers; the first real run is the end-to-end check.

## The static showcase (GitHub Pages)

`tools/build_site.py` renders the 33 lessons, the case study and the scanner guide, and copies the
committed before/after scanner reports. `.github/workflows/pages.yml` publishes it on every push
to `main` to <https://praxis-builds.github.io/QUANTUM-LAB/>. One-time setup by the repo owner:
**Settings → Pages → Build and deployment → Source: GitHub Actions**. No simulation runs there.

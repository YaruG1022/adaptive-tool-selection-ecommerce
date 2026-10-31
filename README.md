# Little Signal Shop — 小信号商店

A browser-based e-commerce simulation prototype with an animated warehouse, a research workbench, and read-only business replay.

## Run

Open `index.html` in a current Edge, Chrome, or Firefox browser. No package installation, build step, account, or API key is required. Keep all four web files (`index.html`, `styles.css`, `i18n.js`, and `app.js`) together.

The interface starts in English. Use the header's `中文` / `English` button to change languages, including during playback. The switch translates the interface, recorded messages, chart labels, and accessible names without resetting the simulation, experiment settings, or playback. Reloading starts a fresh session in English.

Lucide 1.17.0 icons load from a pinned unpkg URL. If that resource is unavailable, icons may be absent; business logic and controls still run. This version has no dependency on a ChatGPT host or visualization runtime.

## Screens

- Warehouse: investigate demand, run a business day, watch picking, packing, shipping, and due replenishments. Playback supports pause, speed changes, skipping, and reduced motion.
- Research workbench: compare no investigation, two tool calls per day, and a fixed threshold rule over matched market seeds. Change forecast reliability, volatility, and tool cost. Research pause is independent of warehouse playback.
- Replay: inspect recorded information, cash movements, stockouts, and after-the-fact market demand; replay the original receipt without changing the current store.

## Project status

This is a prototype, not the completed course research system. The initial three-seed comparison is computed in the browser. DQN training is not implemented, and the displayed curves are business trajectories, not learning curves. Simulation assumptions and comparisons have not been scientifically validated.

All state and histories live in browser memory and reset on refresh. There is no backend, database, LLM integration, or saved model. The warehouse session starts on day 28; research trials run day 1 through day 90.

## Files

- `index.html`: page structure and entry point.
- `styles.css`: layout, colors, and warehouse artwork.
- `app.js`: shared simulation, tools, animation, experiments, and replay.
- `i18n.js`: English/Chinese presentation catalog and state-preserving language switch.
- `FINAL_PROJECT_PLAN.md`: the agreed English project plan, separating implemented prototype features from planned research.
- `CODEX_SETUP_INSTRUCTIONS.md`: instructions for setting up the local checkout and a GitHub repository.
- `.nojekyll`: static publishing marker for GitHub Pages.

## GitHub

Upload the contents of this folder to a repository, or copy them into a local checkout and commit them. Do not upload only the ZIP if you want the files to be browseable and runnable as a website.

For GitHub Pages, publish the branch/folder that contains `index.html`; this prototype uses only static browser files. No deployment has been performed by this export.

The repository owner should choose a project license before distributing the project under an open-source license. No project license has been selected automatically.

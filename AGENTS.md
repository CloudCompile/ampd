# tonearm — agent working rules

## E2B sandboxes FIRST (user directive, 2026-11-13)

The production box (`InferencePort-F-N`) is a small shared VPS (2 cores / 8GB)
that also runs ComfyUI, opencode, and the user's own work. **Do not run
tonearm (or its tests, CI repro, browser automation, pipelines) on it.**
Running the live server here nearly killed the box once (idle ffmpeg +
renderer at ~100% of a core).

From now on:

1. **All tonearm execution happens in e2b sandboxes.** Spin one up with the
   e2b CLI (`~/.npm-global/bin/e2b` — export PATH or call it by full path),
   clone the repo / mount the branch under test, and run tests, the server,
   chrome/audio pipelines, and live-account testing there.
2. The VPS is for **editing files, git, gh, and lightweight inspection only**
   (grep/read/status). Unit tests are cheap (`python3 -m unittest discover
   -s tests`, ~6s) and may run locally, but anything that spawns chrome,
   ffmpeg, Xvfb, watchers, or long-lived servers goes to the sandbox.
3. Sandbox needs for tonearm: python3.12+, ffmpeg, pulseaudio, Xvfb,
   google-chrome (see `Dockerfile` / `.github/workflows` for the install
   recipe the CI already uses).
4. Long-lived things on the VPS (the deployed tonearm server itself, tunnels)
   stay the user's call — ask before starting anything that persists.

Live-account testing against the user's real Apple Music account is fine
*from* a sandbox, using the keys in `~/.config/tonearm/` — never commit them.

## House flow (unchanged)

- feature branch → PR → smoke CI → squash-merge
- `python3` not `python`; hermetic tests: `python3 -m unittest discover -s tests`
- untracked `launch/` dir = user's marketing work — never commit
- PRs: #198 (sidebar player plugin, CI green), #199 (VPS savings)

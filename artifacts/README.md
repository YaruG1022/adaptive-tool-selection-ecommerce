# Generated artifacts

Local output belongs here: experiment runs, checkpoints, exported episodes, plots, browser screenshots, and verification reports. Contents are ignored by Git except this README. Future scripts should create their output subdirectories as needed.

Suggested layout once those commands exist:

```text
artifacts/
  runs/<run-id>/
  checkpoints/<run-id>/
  exports/<run-id>/
  figures/<run-id>/
```

Ignored does not mean backed up or published. Define a separate retention/archive procedure when research runs begin; preserve raw metrics, configuration, seeds, versions, and model identities needed to reproduce reported results. Small curated compatibility examples belong in tracked `tests/fixtures/`. Final report documents may be tracked intentionally under `docs/`.

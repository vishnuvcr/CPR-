# CPR GitHub Pages Dashboard

## Purpose

The Phase 9I prospective-validation results are now published as a static GitHub Pages dashboard.

Dashboard URL:

https://vishnuvcr.github.io/CPR-/

## Publication design

- Source branch: `cpr-v1.0-phase9i-prospective-validation`
- Pages workflow: `.github/workflows/cpr-phase9i-pages.yml` on the default `main` branch.
- Dashboard source: `site/index.html`
- Published research data: `docs/phase9i/data/`
- Latest human-readable status: `docs/phase9i/latest_status.md`
- Run history: `docs/phase9i/run_log.md`

The default-branch Pages workflow is triggered after successful Phase 9I workflow completion (`workflow_run`), on changes to the Pages workflow itself, on a weekday schedule, and manually. It checks out the active Phase 9I branch and publishes the persisted state. It copies the current machine-readable validation outputs and key protocol/continuity documents into the Pages artifact.

## Scientific boundary

The dashboard is a presentation layer only. It does not refit, select, optimize, or alter the frozen Phase 9I candidate.

The frozen candidate remains:

**LEAF_4 / SHORT / 10-session swing / ATR 1R stop + 2R target**

Fresh-holdout cutoff:

**2026-09-17 15:30 Asia/Kolkata**

The Pages dashboard must therefore never be interpreted as a live recommendation merely because the displayed performance changes; the pre-registered Phase 9I maturity and review criteria remain authoritative.

## Continuity record

This Pages setup is infrastructure for the active Phase 9I phase and does not change the scientific plan or candidate.

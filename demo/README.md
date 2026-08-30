# Demo

Run the Phase 4 end-to-end HTTP smoke path against the locally processed real public dataset:

```powershell
python -m demo.phase4_smoke
```

The script calls health, panel validation, promotion discovery, and promotion audit endpoints. It
writes compact reproducibility evidence to `reports/phase-04/demo-smoke.json`; no raw or processed
dataset is committed to Git.


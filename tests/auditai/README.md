# AuditAI guerrilla scaffold — minhtridinh-kayden/viparse

Dataset: **20** cases · **40** doc chunks · **0** TODOs

- [ ] Spot-check `dataset.json` (all from public docs; no private data)
- [ ] Mock adapter is **intentionally weak** (one SEED) — expect FAIL with real judge
- [ ] Prefer real HTTP target for meaningful product metrics
- [ ] For PR numbers: `judge.provider` = `xai` or `openai` (not mock)
- [ ] Never invent metric numbers — use `auditai-report.json` only
- [ ] Badge only if maintainer wants it

Commands:

```bash
python tests/auditai/mock_adapter.py &
export XAI_API_KEY=...   # or OPENAI_API_KEY
# edit auditai.yml judge.provider = xai|openai
auditai run --config tests/auditai/auditai.yml
```

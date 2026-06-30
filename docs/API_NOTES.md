# Cognee API Notes (fill in after running smoke_test.py on a real machine)

> The old scaffold *guessed* these from docs. This file records what's actually true
> once the live SDK runs. Update every `# VERIFY` in `backend/memory_service.py` to match.

| Question | Doc guess | Verified (fill in) |
|---|---|---|
| `SearchType` import path | one of 3 fallbacks tried | |
| Enum member names (`GRAPH_COMPLETION`, `RAG_COMPLETION`, `INSIGHTS`) | as named | |
| `cognee.add` dataset kwarg | `dataset_name=` | |
| `cognee.cognify` datasets arg | `datasets=[name]` | |
| Dataset status API + "done" sentinel | `cognee.datasets.get_status([name])` | |
| `recall`/`search` query kwarg | `query_text=` | |
| Shape of `search()` return (list? objects? `.text`?) | unknown — printed by smoke_test | |
| `remember` session kwargs | `session_id=`, `self_improvement=` | |
| `improve` args | `dataset=`, `session_ids=` | |
| `forget` arg | `dataset=` | |
| `prune` methods | `prune_data()`, `prune_system()` | |

## Raw smoke_test output (paste here)

```
(paste the printed types/reprs so the team has them)
```

# Hero Case — the Daniel Marsh burglary series (SYNTHETIC)

> ⚠️ Entirely fictional data created for a hackathon demo. No real persons, cases, or
> departments. Illustrative only — not an operational tool.

**The story the demo tells.** Three home burglaries, two police departments in different
counties with **no shared records system**. Same offender the whole time. Caught after
**~23 months** only because, on the third job, the doorbell camera wasn't fully obscured
and captured a plate — *luck, not investigation*.

Every department already held a piece of the truth:

| Doc ID | Jurisdiction | Date | Holds the clue... |
|---|---|---|---|
| MH-0312-NARR | Maple Heights | 2023-03-03 | MO: rear slider, 02:00–04:00, doorbell cam obscured |
| MH-0312-FOR | Maple Heights | 2023-03-05 | **Tool marks: 8 mm flat blade, nick on left edge**; *"recommend regional check — not actioned"* |
| MH-0312-WIT | Maple Heights | 2023-03-03 | **Dark blue sedan, partial plate 8K·** |
| RV-0788-NARR | Riverside | 2023-11-19 | Same MO, different county |
| RV-0788-FOR | Riverside | 2023-11-21 | **Same 8 mm blade + left-edge nick**; *"regional database check recommended — pending"* |
| RV-0788-WIT | Riverside | 2023-11-19 | Dark blue sedan seen leaving |
| MH-0102-NARR | Maple Heights | 2025-02-04 | Same MO again, ~23 months later |
| MH-0102-FOR | Maple Heights | 2025-02-06 | Same tool signature a third time |
| MH-0102-ARR | Maple Heights | 2025-02-10 | Doorbell cam caught plate **8K·**; arrest of Daniel R. Marsh; pry bar recovered matches 8 mm + nick; confession to all three |

**Why graph beats vector here:** answering *"are these the same offender?"* requires
connecting the **forensic** tool-mark dims (docs A) + the **witness** vehicle (docs B) +
the **narrative** MO (docs C) **across two jurisdictions**. Vector search retrieves the
single most-similar chunk; it cannot assemble a cross-document, cross-county chain.
Cognee's graph traversal can.

# UAT Execution Sheet

| ID | Area | Scenario | Expected | Result | Evidence |
|---|---|---|---|---|---|
| BR-01 | Branch | A-only opens B record | denied | ☐ | |
| BR-02 | API | A-only requests branch B | ACCESS_DENIED | ☐ | |
| EV-01 | Event | same hall/day/period twice | second rejected | ☐ | |
| EV-02 | Event | same hall/day different periods | allowed | ☐ | |
| EV-03 | Event | concurrent same slot | exactly one succeeds | ☐ | |
| ST-01 | Stay | exact overlap | rejected | ☐ | |
| ST-02 | Stay | contained/contains overlap | rejected | ☐ | |
| ST-03 | Stay | left/right overlap | rejected | ☐ | |
| ST-04 | Stay | checkout = next checkin | allowed | ☐ | |
| ST-05 | Stay | concurrent overlap, different start | exactly one succeeds | ☐ | |
| FI-01 | Finance | duplicate draft invoice capacity | rejected | ☐ | |
| FI-02 | Finance | partial/full/refund/reversal | net exposure correct | ☐ | |
| OP-01 | Ops | required blocker open | event start denied | ☐ | |
| AU-01 | Auth | reuse rotated refresh token | denied | ☐ | |
| AU-02 | Auth | wrong bound device | denied | ☐ | |
| AU-03 | Auth | logout then token reuse | denied | ☐ | |
| MG-01 | Migration | execute twice | no duplicates | ☐ | |
| UI-01 | UI | Arabic RTL critical flows | no runtime/layout errors | ☐ | |

Final decision: GO / NO-GO
Business approval:
Accounting approval:
Operations approval:
Technical approval:
Date:

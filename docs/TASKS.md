# Task dependencies

| Range | Depends on | Deliverable |
|---|---|---|
| 1–10 | User product goal | Requirements and release gates |
| 11–20 | 4, 7, 9 | Reproducible package and contracts |
| 21–30 | 16–20 | Skill and execution coordinator |
| 31–40 | 28–30 | API checks and deterministic test data |
| 41–50 | 28–30, 31 | Web checks and UX observations |
| 51–58 | 28–30 | Local aiogram tests |
| 59–60 | 51–58; test-user credentials and network | Real Telegram integration |
| 61–70 | 28–30; Android runner and installable build | Native application checks |
| 71–80 | 31–50 | Performance and security |
| 81–90 | Implemented modules | Benchmark, report and CI |
| 91–97 | Verified capabilities | Documentation and presentation assets |
| 98 | Independent person | First-use validation |
| 99 | Installation and mandatory runtime prerequisites | Clean release validation |
| 100 | All release gates | Full rehearsal and release |

Each completed step is committed and pushed independently. Unavailable external prerequisites remain unchecked while independent implementation continues. docs/PROGRESS.md records concrete evidence, not a completion percentage invented from file counts.

# Critical scenarios and oracles

| ID | Target | Preconditions and actions | Expected result | Failure impact |
|---|---|---|---|---|
| API-LOGIN | API | Valid test user signs in, reads profile, signs out | Identity matches; revoked session cannot read profile | Account access |
| API-OWNERSHIP | API | User B reads user A's object | Access denied without exposing content | Data disclosure |
| WEB-SAVE | Web | Enter a value, save, reopen | Persisted value matches input | Lost work |
| WEB-ERROR | Web | Submit invalid input or simulate API failure | Actionable feedback; no false success | User confusion |
| TG-DIALOG | Telegram | Start, enter value, confirm, cancel | Correct transitions and isolated user state | Wrong bot actions |
| TG-DUPLICATE | Telegram | Deliver the same update twice | At most one intended side effect | Duplicate actions |
| APP-SAVE | Android | Sign in, save data, reopen screen | UI and API show the same persisted state | Lost work |
| APP-OFFLINE | Android | Interrupt network during action, reconnect | Honest failure and recoverable flow | Inconsistent state |

Every executable check references one of these requirements or an explicit project-specific oracle. An inferred expectation is labeled as an assumption until accepted.

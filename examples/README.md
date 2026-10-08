# Reviewed examples

Start the owned fixture with `autotest demo --port 8765`, then use `autotest validate`, `plan` and `run` on API/web/performance/security examples. All credentials in the fixture are synthetic and have no validity outside that process. Authorization is captured in memory and removed from persisted evidence.

`telegram.yaml` uses real aiogram handlers and a recording transport without network. `telegram-live.yaml` requires protected credentials and an owned test bot; absent bindings produce a blocked result rather than live success. Never paste credentials into these files.

`android.yaml` needs the signed APK, explicit isolated emulator-5554, host Appium 127.0.0.1:4723 and demo API 8765 (guest sees host through 10.0.2.2). It resets only its owned app and forces installation of the supplied build. Start a fresh demo process for this example: its exact list oracle includes the seeded Alice item, so prior web/native mutations must not share its dataset. It does not establish iOS/desktop support or general Android compatibility.

`performance.yaml` requires k6 and runs a bounded workload. Compatible baselines are explicit reviewed inputs. `security.yaml` tests exactly one response-header policy; it does not certify the site.

Examples are starting points. Bind real secrets via environment references, change origins only to authorized test targets, and replace demo requirements with your project's actual contracts. Profile exclusions and unavailable prerequisites remain visible.

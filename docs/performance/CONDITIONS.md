# Reproducible performance measurements

Performance checks are bounded experiments, not production capacity estimates. Use an explicitly allowed staging origin and synthetic data. Built-in HTTP measurements and k6 have separate baselines and cannot be compared across engines.

The initial reference environment is Linux x86_64, Python 3.12, 5 vCPUs and 32 GiB memory. The loopback demo uses a thread-per-request Python HTTP server. Native emulator load can contend with the measurements; stop it for benchmark reference runs and record other load separately. Versions, hardware, engine, target origin/path, warm-up count, measured requests, concurrency, response status oracle and timeout belong in each artifact.

The default smoke experiment uses two warm-up requests followed by ten measured GET /health requests, concurrency one. The example k6 run uses five warm-up iterations, twenty measured iterations and two virtual users. Thresholds are per-project inputs: the demo smoke allows p95 below 1000 ms and zero non-200 responses. Such a loose threshold checks operation, not a service-level objective.

Retain p50/p95, errors, samples and elapsed time. Never include warm-up samples in the measured summary. Disable redirects and refuse destinations outside the allowlist. A budget exhaustion or empty sample set blocks the experiment. Percentiles on small samples are explicitly marked exploratory.

A baseline must come from a reviewed previous artifact and have identical engine, target path, hardware/runtime, workload and response oracle. Compare ratios only after the absolute thresholds pass. Repeat a suspected regression in the same conditions; report the two measured values and preserve both artifacts. Tools never write or replace approved baselines automatically.

Browser timings include navigation DOMContentLoaded/load and measured semantic actions, using the recorded Chromium version, viewport and headless mode. They are laboratory timings, not field Core Web Vitals. No score claims UX correctness.

# Installable alpha

Version `0.1.0a1` uses the MIT license for this project's code. Vendored axe-core retains its MPL-2.0 license in the wheel; dependencies retain their own licenses. See [third-party notices](THIRD-PARTY.md). This alpha is not published to PyPI.

From the source checkout, run `uv build --no-sources`, then `.venv/bin/python scripts/check_distribution.py`. The latter checks the wheel and source archive for required skill guides, examples, schemas, the CLI, demo resources and licenses. It rejects local caches, runtime credentials, Telegram sessions and Android signing keys. Build outputs stay in ignored `dist/`.

To test the wheel independently of the checkout, create a fresh Python 3.12 environment and install the local artifact:

```bash
uv venv --python 3.12 /tmp/autotest-wheel-review
uv pip install --python /tmp/autotest-wheel-review/bin/python \
  'dist/autotest_agent_skill-0.1.0a1-py3-none-any.whl[web,telegram]'
cd /tmp
/tmp/autotest-wheel-review/bin/autotest --version
/tmp/autotest-wheel-review/bin/autotest skill
/tmp/autotest-wheel-review/bin/autotest doctor --probe-browser
/tmp/autotest-wheel-review/bin/autotest benchmark --output /tmp/autotest-wheel-evidence
```

Install Chromium through the environment's Playwright CLI when no compatible browser is already available. The `skill` command prints the installed SKILL.md and resource directory. Read those files as agent instructions; supplying a wheel to an agent does not automatically register a skill in its host application.

The wheel contains executable Python adapters and agent references. Native fixture source and development setup scripts are distributed in the source archive and repository. Local source installation uses the committed `uv.lock`; a wheel installation resolves dependencies within the declared ranges. For release review, retain the actual installed versions alongside the archive SHA256 and run evidence.

Archive integrity and a passing bundled corpus do not close the live Telegram or independent first-use release gates. Current external prerequisites remain in [BLOCKERS.md](BLOCKERS.md).

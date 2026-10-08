"""Trusted DOM inspection; discovered actions do not grant permission to submit them."""

from .errors import Blocked
from .policy import require_url


def inspect_page(page, context):
    elements = page.evaluate("""() => ({
      links: [...document.querySelectorAll('a[href]')].slice(0,50).map(a=>({name:a.textContent.trim(),url:a.href})),
      buttons: [...document.querySelectorAll('button')].slice(0,100).map(b=>({name:b.textContent.trim(),type:b.type,disabled:b.disabled})),
      forms: [...document.querySelectorAll('form')].slice(0,30).map(f=>({id:f.id,method:f.method,fields:[...f.elements].map(e=>({name:e.name||e.id,type:e.type}))}))
    })""")
    visited = []
    original = page.url
    for link in elements["links"][:20]:
        try:
            require_url(context.config, link["url"])
        except (Blocked, ValueError):
            link["status"] = "excluded_by_policy"
            continue
        context.consume("actions")
        page.goto(
            link["url"], wait_until="domcontentloaded", timeout=min(10, context.remaining()) * 1000
        )
        visited.append({"url": page.url, "title": page.title()})
    if page.url != original:
        context.consume("actions")
        page.goto(
            original, wait_until="domcontentloaded", timeout=min(10, context.remaining()) * 1000
        )
    return {
        "elements": elements,
        "visited_pages": visited,
        "note": "Forms and unknown buttons were inventoried, not submitted.",
    }


def ux_observations(page):
    snapshot = page.evaluate("""() => ({
      text: document.body.innerText.slice(0,30000),
      main: document.querySelectorAll('main,[role="main"]').length,
      unexplained: [...document.querySelectorAll('button:disabled')].filter(b=>!b.title&&!b.getAttribute('aria-describedby')).map(b=>b.textContent.trim()).slice(0,20)
    })""")
    observations = []
    import re

    for pattern in ("TODO", "lorem ipsum", "undefined", "[object Object]"):
        if re.search(re.escape(pattern), snapshot["text"], re.IGNORECASE):
            observations.append(
                {
                    "category": "placeholder_copy",
                    "reason": f"Visible copy contains {pattern}; review whether it belongs in the product.",
                    "confirmed_defect": False,
                }
            )
    if not snapshot["main"]:
        observations.append(
            {
                "category": "navigation",
                "reason": "No main landmark was found; review page structure.",
                "confirmed_defect": False,
            }
        )
    for name in snapshot["unexplained"]:
        observations.append(
            {
                "category": "feedback",
                "reason": f"Disabled button {name} has no explicit explanation binding.",
                "confirmed_defect": False,
            }
        )
    return observations

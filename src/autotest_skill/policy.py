"""Targets are explicit origins; redirects do not expand authority."""

from urllib.parse import urlsplit

from .config import origin
from .errors import Blocked


def require_url(config, url):
    parsed = urlsplit(url)
    if parsed.username or parsed.password or parsed.fragment:
        raise Blocked("Target URL contains unsupported credentials or a fragment")
    candidate = origin(f"{parsed.scheme}://{parsed.netloc}")
    if candidate not in config.allowed_origins:
        raise Blocked("Request target is outside the configured origin allowlist")
    return url


def request_url(config, base_url, path):
    if not path.startswith("/") or path.startswith("//") or "\\" in path:
        raise Blocked("Unsafe target-relative path")
    return require_url(config, origin(base_url) + path)

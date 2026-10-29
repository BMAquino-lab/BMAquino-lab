"""Refresh the profile's public GitHub statistics without external services."""

from __future__ import annotations

import datetime as dt
import html
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request


ACCOUNT = "BMAquino-lab"
ROOT = Path(__file__).resolve().parent.parent
START = "<!-- profile-stats:start -->"
END = "<!-- profile-stats:end -->"

CONTRIBUTIONS_QUERY = """\
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions }
    }
  }
}
"""


def github_json(url: str, token: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "bmaquino-profile-stats",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API returned HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise RuntimeError("GitHub API request failed") from None


def collect_metrics(token: str, fetch=github_json, now: dt.datetime | None = None):
    """Count public owned repositories, their stars, and public contributions."""
    repositories = []
    for page in range(1, 1001):
        url = (
            f"https://api.github.com/users/{ACCOUNT}/repos?"
            + urllib.parse.urlencode({"type": "owner", "per_page": 100, "page": page})
        )
        batch = fetch(url, token)
        if not isinstance(batch, list):
            raise RuntimeError("GitHub returned an unexpected repository response")
        for repo in batch:
            if (
                isinstance(repo, dict)
                and repo.get("private") is False
                and str(repo.get("owner", {}).get("login", "")).lower() == ACCOUNT.lower()
            ):
                stars = repo.get("stargazers_count")
                if not isinstance(stars, int) or isinstance(stars, bool) or stars < 0:
                    raise RuntimeError("GitHub returned an invalid star count")
                repositories.append(repo)
        if len(batch) < 100:
            break
    else:
        raise RuntimeError("GitHub repository pagination exceeded its safety limit")

    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("The metric time must have a timezone")
    now = now.astimezone(dt.timezone.utc).replace(microsecond=0)
    timestamp = lambda value: value.isoformat().replace("+00:00", "Z")
    payload = {
        "query": CONTRIBUTIONS_QUERY,
        "variables": {
            "login": ACCOUNT,
            "from": timestamp(now - dt.timedelta(days=365)),
            "to": timestamp(now),
        },
    }
    result = fetch("https://api.github.com/graphql", token, payload)
    try:
        if result.get("errors"):
            raise ValueError
        contributions = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    except (AttributeError, KeyError, TypeError, ValueError):
        raise RuntimeError("GitHub returned an unexpected contributions response") from None
    if not isinstance(contributions, int) or isinstance(contributions, bool) or contributions < 0:
        raise RuntimeError("GitHub returned an invalid contribution count")
    return {
        "repositories": len(repositories),
        "stars": sum(repo["stargazers_count"] for repo in repositories),
        "contributions": contributions,
    }


def render_stats(metrics: dict, *, mobile: bool = False) -> str:
    width = 480 if mobile else 1200
    height = 160 if mobile else 180
    value_size = 42 if mobile else 58
    label_size = 14 if mobile else 19
    value_y = 69 if mobile else 78
    label_y = 103 if mobile else 118
    sub_y = 127 if mobile else 145
    xs = [width // 6, width // 2, width * 5 // 6]
    labels = ["PUBLIC REPOS", "PUBLIC STARS", "CONTRIBUTIONS"]
    keys = ["repositories", "stars", "contributions"]
    chunks = []
    for x, label, key in zip(xs, labels, keys):
        value = f"{metrics[key]:,}"
        chunks.append(
            f'<text x="{x}" y="{value_y}" text-anchor="middle" fill="#ffd45a" '
            f'font-family="Segoe UI,Arial,sans-serif" font-size="{value_size}" '
            f'font-weight="700">{value}</text>\n'
            f'<text x="{x}" y="{label_y}" text-anchor="middle" fill="#e6e1d5" '
            f'font-family="Segoe UI,Arial,sans-serif" font-size="{label_size}" '
            f'font-weight="600">{label}</text>'
        )
    chunks.append(
        f'<text x="{xs[2]}" y="{sub_y}" text-anchor="middle" fill="#a9a293" '
        f'font-family="Segoe UI,Arial,sans-serif" font-size="{12 if mobile else 16}">PUBLIC · LAST YEAR</text>'
    )
    description = html.escape(
        f"{metrics['repositories']} public repositories, {metrics['stars']} stars on public repositories, "
        f"and {metrics['contributions']} public contributions in the last 12 months."
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">Public GitHub activity</title><desc id="desc">{description}</desc>
  <defs>
    <radialGradient id="glow"><stop stop-color="#e6b22f" stop-opacity=".30"/><stop offset="1" stop-color="#e6b22f" stop-opacity="0"/></radialGradient>
    <clipPath id="clip"><rect width="{width}" height="{height}" rx="16"/></clipPath>
  </defs>
  <style>
    @keyframes glow {{0%,100%{{opacity:.45;transform:translateX(-40px)}}50%{{opacity:1;transform:translateX(40px)}}}}
    @media (prefers-reduced-motion: no-preference){{.glow{{animation:glow 11s ease-in-out infinite}}}}
  </style>
  <g clip-path="url(#clip)">
    <rect width="{width}" height="{height}" fill="#101110"/>
    <ellipse class="glow" cx="{width // 2}" cy="{height + 12}" rx="{width // 3}" ry="{height // 2}" fill="url(#glow)"/>
    <path d="M{width // 3} 31v{height - 62}M{width * 2 // 3} 31v{height - 62}" stroke="#8b7650" stroke-opacity=".3"/>
    {''.join(chunks)}
  </g>
</svg>
'''


def stats_block(metrics: dict) -> str:
    description = html.escape(
        f"Public GitHub activity: {metrics['repositories']} repositories, "
        f"{metrics['stars']} stars, and {metrics['contributions']} contributions in the last 12 months. "
        "Refreshed daily.",
        quote=True,
    )
    return (
        '<picture>\n'
        '  <source media="(max-width: 600px)" srcset="assets/profile-stats-mobile.svg">\n'
        f'  <img src="assets/profile-stats.svg" alt="{description}">\n'
        '</picture>'
    )


def update_readme(text: str, metrics: dict) -> str:
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("README must contain exactly one pair of profile statistics markers")
    begin = text.index(START) + len(START)
    end = text.index(END)
    if begin > end:
        raise ValueError("Profile statistics markers are in the wrong order")
    return text[:begin] + "\n" + stats_block(metrics) + "\n" + text[end:]


def write_if_changed(path: Path, value: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == value:
        return False
    path.write_text(value, encoding="utf-8", newline="\n")
    return True


def update_files(root: Path, metrics: dict) -> bool:
    readme_path = root / "README.md"
    updated_readme = update_readme(readme_path.read_text(encoding="utf-8"), metrics)
    assets = root / "assets"
    desktop = render_stats(metrics)
    mobile = render_stats(metrics, mobile=True)
    changed = write_if_changed(assets / "profile-stats.svg", desktop)
    changed = write_if_changed(assets / "profile-stats-mobile.svg", mobile) or changed
    changed = write_if_changed(readme_path, updated_readme) or changed
    return changed


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required to refresh statistics.", file=sys.stderr)
        return 1
    try:
        metrics = collect_metrics(token)
        changed = update_files(ROOT, metrics)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"Profile statistics were not updated: {exc}", file=sys.stderr)
        return 1
    print(f"Public stats: {metrics['repositories']} repositories, {metrics['stars']} stars, "
          f"{metrics['contributions']} contributions in the past 12 months; "
          + ("updated." if changed else "unchanged."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

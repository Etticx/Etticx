"""Generate the profile's terminal cards using public GitHub data only.

Python's standard library is sufficient. GITHUB_TOKEN is optional locally;
GitHub Actions supplies its own token. No private repository data is queried.
"""

import argparse
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
THEMES = {
    "dark": {
        "bg": "#161b22", "bar": "#21262d", "border": "#30363d",
        "text": "#c9d1d9", "muted": "#7d8590", "key": "#ffa657",
        "value": "#a5d6ff", "accent": "#7ee787", "portrait": "#c9d1d9",
    },
    "light": {
        "bg": "#f6f8fa", "bar": "#eaeef2", "border": "#d0d7de",
        "text": "#24292f", "muted": "#57606a", "key": "#953800",
        "value": "#0550ae", "accent": "#116329", "portrait": "#24292f",
    },
}


def api(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Etticx-profile-card",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/{path}", headers=headers)
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError("GitHub did not return a response")


def collect_stats(username, request=api):
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", username):
        raise ValueError("Invalid GitHub username")
    user = request(f"users/{username}")
    repos = []
    page = 1
    while True:
        batch = request(
            f"users/{username}/repos?type=owner&sort=full_name&per_page=100&page={page}"
        )
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    # Explicitly exclude private repositories even if a different token is supplied.
    public = [repo for repo in repos if not repo.get("private", False)]
    query = urlencode({"q": f"author:{username} is:public", "per_page": 1})
    commits = request(f"search/commits?{query}")
    if commits.get("incomplete_results", False):
        raise RuntimeError("GitHub returned an incomplete commit count; keeping the previous cards")
    return {
        "public_repos": len(public),
        "stars": sum(repo["stargazers_count"] for repo in public if not repo["fork"]),
        "followers": user["followers"],
        "commits": commits["total_count"],
        "joined": user["created_at"][:10],
        "updated": datetime.now(timezone.utc).date().isoformat(),
    }


def render(config, stats, portrait, theme):
    color = THEMES[theme]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="630" '
        'viewBox="0 0 1100 630" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(config["name"])} — GitHub terminal profile</title>',
        '<desc id="desc">ASCII portrait of Alif with parted hair and a smile, biography, contact details, and public GitHub statistics. '
        'Commit count is GitHub public indexed search results; stars exclude forked repositories.</desc>',
        '<style>text{font-family:Consolas,"Liberation Mono",Menlo,monospace;'
        'font-size:14px;white-space:pre} .portrait{font-size:9px}</style>',
        f'<rect x="1" y="1" width="1098" height="628" rx="14" fill="{color["bg"]}" '
        f'stroke="{color["border"]}"/>',
        f'<path d="M15 1 H1085 Q1099 1 1099 15 V43 H1 V15 Q1 1 15 1" fill="{color["bar"]}"/>',
    ]
    for x, fill in [(24, "#ff5f57"), (46, "#febc2e"), (68, "#28c840")]:
        parts.append(f'<circle cx="{x}" cy="22" r="6" fill="{fill}"/>')

    def text(x, y, value, fill="text", extra=""):
        parts.append(f'<text x="{x}" y="{y}" fill="{color[fill]}" {extra}>{escape(str(value))}</text>')

    text(550, 27, "Etticx / README", "muted", 'text-anchor="middle"')
    text(26, 76, "$ neofetch --github Etticx", "accent")
    lines = portrait.splitlines()
    if len(lines) > 48 or any(len(line) > 76 for line in lines):
        raise ValueError("ASCII portrait must fit within 76 columns and 48 rows")
    for index, line in enumerate(lines):
        text(28, 102 + index * 9.5, line, "portrait", 'class="portrait" xml:space="preserve"')

    x = 464

    def heading(y, label):
        text(x, y, label, "accent")
        text(x, y + 18, "─" * 70, "muted")

    def row(y, label, value):
        # Keep all biography rows within the card at 14px monospace.
        dots = "." * max(2, 15 - len(label))
        content = f'{label} {dots} {value}'
        if len(content) > 71:
            raise ValueError(f"Profile row is too long: {label}")
        parts.append(
            f'<text x="{x}" y="{y}" xml:space="preserve">'
            f'<tspan fill="{color["key"]}">{escape(label)}</tspan>'
            f'<tspan fill="{color["muted"]}"> {dots} </tspan>'
            f'<tspan fill="{color["value"]}">{escape(str(value))}</tspan></text>'
        )

    heading(106, config["prompt"])
    row(150, "Name", config["name"])
    for index, (label, value) in enumerate(config["about"]):
        row(172 + index * 22, label, value)
    heading(306, "Currently / previously")
    for index, (label, value) in enumerate(config["now"]):
        row(348 + index * 22, label, value)
    heading(430, "Contact")
    for index, (label, value) in enumerate(config["contact"]):
        row(472 + index * 22, label, value)
    heading(532, "GitHub / public stats")
    row(574, "Repos / stars", f'{stats["public_repos"]:,} / {stats["stars"]:,}')
    row(596, "Commits / followers", f'{stats["commits"]:,} indexed / {stats["followers"]:,}')

    joined = datetime.fromisoformat(stats["joined"]).strftime("%b %Y")
    text(28, 583, f"on GitHub since {joined}", "muted")
    for index, fill in enumerate(["#ff7b72", "#ffa657", "#e3b341", "#7ee787", "#79c0ff", "#d2a8ff"]):
        parts.append(f'<rect x="{28 + index * 30}" y="602" width="30" height="9" fill="{fill}"/>')
    text(225, 611, f'updated {stats["updated"]}', "muted")
    parts.append("</svg>\n")
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Render from the saved public stats snapshot")
    args = parser.parse_args()
    directory = ROOT / "profile"
    config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    portrait = (directory / "avatar.txt").read_text(encoding="utf-8")
    stats = (
        json.loads((directory / "stats.json").read_text(encoding="utf-8"))
        if args.offline else collect_stats(config["username"])
    )
    # Render both completely before writing so validation failures preserve the cards.
    cards = {theme: render(config, stats, portrait, theme) for theme in THEMES}
    for theme, content in cards.items():
        (directory / f"{theme}.svg").write_text(content, encoding="utf-8")
    (directory / "stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(f'Generated light and dark cards for {config["username"]}: {stats}')


if __name__ == "__main__":
    main()

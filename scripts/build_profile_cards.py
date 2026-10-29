"""Build the profile's responsive technology and contact artwork from local SVGs."""

from __future__ import annotations

import html
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "assets" / "tech-icons"
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

GROUPS = [
    ("Languages", "code", [("Python", "python"), ("C", "c"), ("JavaScript", "javascript"), ("Dart", "dart"), ("TypeScript", "typescript"), ("Java", "java"), ("SQL", None)]),
    ("Web & mobile", "monitor", [("React", "react"), ("CSS", "css3"), ("Vite", "vitejs"), ("Flutter", "flutter"), ("HTML", "html5")]),
    ("Backend & data", "database", [("Node.js", "nodejs"), ("MariaDB", "mariadb"), ("Express", "express"), ("MongoDB", "mongodb"), ("Flask", "flask"), ("Firebase", "firebase")]),
    ("Tools", "wrench", [("Git", "git"), ("GitHub", "github"), ("Docker", "docker"), ("Google Apps Script", "googleappsscript")]),
]

SVG_START = '<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'


def inline_logo(name: str, x: int, y: int, size: int) -> str:
    root = ET.parse(ICONS / f"{name}.svg").getroot()
    if root.tag != f"{{{SVG_NS}}}svg":
        raise ValueError(f"{name}: expected an SVG")
    allowed = {"svg", "g", "path", "rect", "circle", "ellipse", "polygon", "polyline", "line", "defs", "linearGradient", "radialGradient", "stop", "title"}
    ids = {}
    for node in root.iter():
        if node.tag.split("}")[-1] not in allowed:
            raise ValueError(f"{name}: unsupported SVG element")
        if "id" in node.attrib:
            old = node.attrib["id"]
            ids[old] = f"logo-{name}-{old}"
            node.set("id", ids[old])
    for node in root.iter():
        for key, value in list(node.attrib.items()):
            if key.lower().startswith("on") or "http://" in value or "https://" in value:
                raise ValueError(f"{name}: external or executable SVG attribute")
            for old, new in ids.items():
                value = value.replace(f"url(#{old})", f"url(#{new})")
                if value == f"#{old}":
                    value = f"#{new}"
            node.set(key, value)
        if node.tag.endswith("path"):
            if name in {"express", "flask", "github"}:
                node.set("fill", "#eef1f2")
            elif name == "mariadb":
                node.set("fill", "#c7a285")
            elif name == "googleappsscript":
                node.set("fill", "url(#apps-gradient)")
    root.set("x", str(x))
    root.set("y", str(y))
    root.set("width", str(size))
    root.set("height", str(size))
    root.set("aria-hidden", "true")
    return ET.tostring(root, encoding="unicode")


def category_icon(kind: str, x: int, y: int) -> str:
    shapes = {
        "code": '<path d="M10 5 3 13l7 8M18 5l7 8-7 8M16 3l-4 20"/>',
        "monitor": '<rect x="3" y="4" width="22" height="16" rx="1"/><path d="M14 20v4M9 24h10"/>',
        "database": '<ellipse cx="14" cy="6" rx="10" ry="4"/><path d="M4 6v14c0 2 4.5 4 10 4s10-2 10-4V6M4 13c0 2 4.5 4 10 4s10-2 10-4"/>',
        "wrench": '<path d="M24 4a7 7 0 0 1-9 9L6 23a3 3 0 1 1-4-4l10-9a7 7 0 0 1 9-9l-4 4 1 3 3 1Z"/>',
    }
    return f'<g transform="translate({x} {y})" fill="none" stroke="#f4d34d" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">{shapes[kind]}</g>'


def sql_icon(x: int, y: int) -> str:
    return (f'<g transform="translate({x} {y})" fill="none" stroke="#ddb96a" stroke-width="2">'
            '<ellipse cx="15" cy="7" rx="10" ry="4"/><path d="M5 7v15c0 2 4.5 4 10 4s10-2 10-4V7M5 14c0 2 4.5 4 10 4s10-2 10-4"/></g>')


def section_heading(title: str, caption: str, width: int, *, mobile: bool = False) -> str:
    pieces = [
        '<circle cx="15" cy="20" r="13" fill="url(#dot-glow)"/>',
        '<circle cx="15" cy="20" r="5" fill="#ffdd55"/>',
        f'<text x="40" y="26" fill="#e5e5e2" font-family="Segoe UI,Arial,sans-serif" font-size="{16 if mobile else 15}" letter-spacing="3">{html.escape(title)}</text>',
    ]
    if not mobile:
        pieces.append(f'<path d="M{width-350} 20h43" stroke="#d8af3d" stroke-width="1.5"/>')
        pieces.append(f'<text x="{width-295}" y="24" fill="#8f9290" font-family="Segoe UI,Arial,sans-serif" font-size="10" letter-spacing="1.4">{html.escape(caption)}</text>')
    return "".join(pieces)


def render_tech_cards(*, mobile: bool = False) -> str:
    width = 480 if mobile else 1200
    card_width = 480 if mobile else 288
    card_heights = [72 + ((len(items) + 1) // 2) * 42 + 10 for _, _, items in GROUPS] if mobile else [270] * len(GROUPS)
    gap = 16
    top = 53
    height = top + (sum(card_heights) + gap * (len(GROUPS) - 1) if mobile else card_heights[0])
    desc = "; ".join(f"{group}: " + ", ".join(label for label, _ in items) for group, _, items in GROUPS)
    parts = [
        SVG_START.format(width=width, height=height),
        f'<title id="title">Tech stack</title><desc id="desc">{html.escape(desc)}</desc>',
        '<defs><radialGradient id="dot-glow"><stop stop-color="#ffdf58" stop-opacity=".55"/><stop offset="1" stop-color="#ffdf58" stop-opacity="0"/></radialGradient><linearGradient id="apps-gradient" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#4285f4"/><stop offset=".36" stop-color="#34a853"/><stop offset=".67" stop-color="#fbbc05"/><stop offset="1" stop-color="#ea4335"/></linearGradient></defs>',
        section_heading("TECH STACK", "TOOLS FOR IDEAS, DATA AND PEOPLE.", width, mobile=mobile),
    ]
    for index, (title, kind, items) in enumerate(GROUPS):
        card_x = 0 if mobile else index * (card_width + gap)
        card_height = card_heights[index]
        card_y = top + sum(card_heights[:index]) + index * gap if mobile else top
        parts.append(f'<rect x="{card_x}" y="{card_y}" width="{card_width}" height="{card_height}" rx="15" fill="#101415" stroke="#292e30"/>')
        parts.append(category_icon(kind, card_x + 22, card_y + 22))
        parts.append(f'<text x="{card_x+63}" y="{card_y+43}" fill="#f2f3f1" font-family="Segoe UI,Arial,sans-serif" font-size="{21 if mobile else 20}" font-weight="600">{html.escape(title)}</text>')
        for position, (label, icon) in enumerate(items):
            col = position % 2
            row = position // 2
            x = card_x + (22 + col * (235 if mobile else 136))
            y = card_y + (72 if mobile else 78) + row * (42 if mobile else 46)
            parts.append(inline_logo(icon, x, y, 30) if icon else sql_icon(x, y))
            text_x = x + 40
            font = 20 if mobile else 19
            if label == "Google Apps Script":
                parts.append(f'<text x="{text_x}" y="{y+12}" fill="#e9eae7" font-family="Segoe UI,Arial,sans-serif" font-size="{font if mobile else 18}"><tspan x="{text_x}">Google</tspan><tspan x="{text_x}" dy="{font+3}">Apps Script</tspan></text>')
            else:
                parts.append(f'<text x="{text_x}" y="{y+22}" fill="#e9eae7" font-family="Segoe UI,Arial,sans-serif" font-size="{font}">{html.escape(label)}</text>')
    parts.append('</svg>\n')
    return "".join(parts)


def render_connect_heading(*, mobile: bool = False) -> str:
    width = 480 if mobile else 1200
    return (SVG_START.format(width=width, height=42)
            + '<title id="title">Let\'s connect</title><desc id="desc">Links to Brian\'s portfolio, LinkedIn, and email.</desc>'
            + '<defs><radialGradient id="dot-glow"><stop stop-color="#ffdf58" stop-opacity=".55"/><stop offset="1" stop-color="#ffdf58" stop-opacity="0"/></radialGradient></defs>'
            + section_heading("LET’S CONNECT", "OPEN TO PROJECTS AND COLLABORATION.", width, mobile=mobile)
            + '</svg>\n')


def render_contact(title: str, detail: str, kind: str) -> str:
    if kind == "portfolio":
        icon = '<g transform="translate(34 38)" fill="none" stroke="#f2e5b8" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22l-3 3a8 8 0 0 1-11-11l6-6a8 8 0 0 1 11 0M11 14l3-3a8 8 0 0 1 11 11l-6 6a8 8 0 0 1-11 0"/></g>'
    elif kind == "linkedin":
        icon = inline_logo("linkedin", 30, 34, 34)
    elif kind == "email":
        icon = '<g transform="translate(31 39)" fill="none" stroke="#f1f2f0" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><rect width="32" height="24" rx="2"/><path d="m1 2 15 12L31 2"/></g>'
    else:
        raise ValueError("unknown contact type")
    return (SVG_START.format(width=370, height=105)
            + f'<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(detail)}</desc>'
            + '<rect x=".5" y=".5" width="369" height="104" rx="14" fill="#101415" stroke="#292e30"/>'
            + icon
            + f'<text x="83" y="44" fill="#f2f3f1" font-family="Segoe UI,Arial,sans-serif" font-size="20" font-weight="600">{html.escape(title)} ↗</text>'
            + f'<text x="83" y="72" fill="#adb0ad" font-family="Segoe UI,Arial,sans-serif" font-size="15">{html.escape(detail)}</text>'
            + '</svg>\n')


def main() -> None:
    assets = ROOT / "assets"
    files = {
        "tech-cards.svg": render_tech_cards(),
        "tech-cards-mobile.svg": render_tech_cards(mobile=True),
        "connect-heading.svg": render_connect_heading(),
        "connect-heading-mobile.svg": render_connect_heading(mobile=True),
        "contact-portfolio.svg": render_contact("Portfolio", "See my work and other projects.", "portfolio"),
        "contact-linkedin.svg": render_contact("LinkedIn", "Let’s connect.", "linkedin"),
        "contact-email.svg": render_contact("Email", "aquinobrianmichael@gmail.com", "email"),
    }
    for name, contents in files.items():
        ET.fromstring(contents)
        (assets / name).write_text(contents, encoding="utf-8", newline="\n")
    print(f"Generated {len(files)} profile assets.")


if __name__ == "__main__":
    main()

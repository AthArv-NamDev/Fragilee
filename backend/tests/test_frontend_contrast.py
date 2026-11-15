"""WCAG AA checks for the foreground/background pairs used by the shared UI tokens."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "app" / "globals.css"


def _tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})\s*;", block))


def _linear(channel: float) -> float:
    value = channel / 255
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    rgb = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    r, g, b = (_linear(channel) for channel in rgb)
    return .2126 * r + .7152 * g + .0722 * b


def _ratio(a: str, b: str) -> float:
    light, dark = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (light + .05) / (dark + .05)


def test_core_foreground_and_control_pairs_meet_wcag_aa():
    css = CSS.read_text()
    light_block = re.search(r":root,\s*html\[data-theme=\"light\"\]\s*\{([^}]*)\}", css, re.S).group(1)
    dark_block = re.search(r"html\[data-theme=\"dark\"\]\s*\{([^}]*)\}", css, re.S).group(1)
    light, dark = _tokens(light_block), _tokens(dark_block)

    pairs = {
        "body text": ("text", "bg"),
        "muted text": ("muted", "bg"),
        "coral text": ("coral", "bg"),
        "violet selected text": ("coral-ink", "violet"),
        "coral selected text": ("coral-ink", "coral"),
        "green primary button": ("sage-ink", "sage"),
        "delete confirmation button": ("critical-ink", "critical"),
    }
    for theme_name, theme in (("light", light), ("dark", dark)):
        for label, (foreground, background) in pairs.items():
            ratio = _ratio(theme[foreground], theme[background])
            assert ratio >= 4.5, f"{theme_name} {label} contrast is {ratio:.2f}:1"


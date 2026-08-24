from __future__ import annotations

from fastapi.templating import Jinja2Templates

from app.core.config import get_settings

templates = Jinja2Templates(directory="app/templates")


def _signal_badge_class(level: str) -> str:
    return {
        "critical": "badge badge-critical",
        "high": "badge badge-high",
        "medium": "badge badge-medium",
        "low": "badge badge-low",
        "noise": "badge badge-noise",
    }.get(level, "badge badge-noise")


templates.env.filters["signal_badge_class"] = _signal_badge_class
templates.env.globals["settings"] = get_settings()
templates.env.globals["app_name"] = "ChangeLens Analytics"

"""HTTP Basic Auth guard for admin/write actions (Settings page, site creation,
manual monitoring triggers). Credentials come from environment variables --
never hardcoded -- and comparisons use secrets.compare_digest to avoid
timing-attack leakage.

This intentionally protects *configuration-changing* actions (adding/editing
tracked sites and pages, triggering monitoring runs) rather than every
read/interactive endpoint -- marking an alert as reviewed/dismissed stays
open since that's a core part of the demo experience for any visitor.
"""

from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import get_settings

_security = HTTPBasic()


def require_admin_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    settings = get_settings()
    correct_username = secrets.compare_digest(credentials.username, settings.admin_username)
    correct_password = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

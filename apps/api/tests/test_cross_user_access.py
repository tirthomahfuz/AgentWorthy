"""Cross-user access control tests."""

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from agentworthy.auth import get_site_for_user
from agentworthy.models import Site, User


def test_cross_user_site_access_returns_403() -> None:
    user_a = User(id=uuid.uuid4(), email="a@example.com")
    user_b = User(id=uuid.uuid4(), email="b@example.com")
    site = Site(id=uuid.uuid4(), user_id=user_b.id, root_url="https://example.com", verified=False)

    db = MagicMock()
    db.get.return_value = site

    with pytest.raises(HTTPException) as exc:
        get_site_for_user(db, site.id, user_a)
    assert exc.value.status_code == 403
    assert "denied" in exc.value.detail.lower()


def test_cross_user_site_not_found_returns_404() -> None:
    user_a = User(id=uuid.uuid4(), email="a@example.com")
    db = MagicMock()
    db.get.return_value = None

    with pytest.raises(HTTPException) as exc:
        get_site_for_user(db, uuid.uuid4(), user_a)
    assert exc.value.status_code == 404

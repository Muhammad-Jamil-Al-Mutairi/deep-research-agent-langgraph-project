"""Shared fixtures. All tests run offline; nothing here calls an LLM."""

from __future__ import annotations

import pytest

from hermes.demo import delivery_robot_spec
from hermes.tools.research.component_db import get_db


@pytest.fixture(scope="session")
def db():
    return get_db()


@pytest.fixture
def spec():
    return delivery_robot_spec()

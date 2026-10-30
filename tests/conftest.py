"""Shared fixtures: src on sys.path, one MASPY Admin and a seeded Map."""

import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from maspy import Admin, Belief, Any

from Map_Env import Map
from Walker_Ag import Walker


# Admin must exist before the Map (same order as Walker_Main).
@pytest.fixture(scope="session")
def admin():
    return Admin()


@pytest.fixture
def env(admin):
    random.seed(0)
    return Map((10, 10), 0.2)


# Walker without training (episodes=None), connected to the map.
@pytest.fixture
def make_walker(env):
    def _make():
        return Walker("wk", env, None)
    return _make


# The update_walls body exactly as MASPY registered it for Sent_Walls.
@pytest.fixture(scope="session")
def update_walls_plan():
    plans = [p for p in Walker._plans if p.trigger.data.name == "Sent_Walls"]
    assert len(plans) == 1, f"expected one Sent_Walls plan, got {len(plans)}"
    return plans[0].body


def wall_set(agent):
    return agent.get(Belief("Wall_Set", Any)).values

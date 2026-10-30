"""update_walls: a walker must absorb every wall another walker sends.

Unit tests drive the plan body with a fake agent; integration tests use real
Walker agents on a real Map, calling the plan MASPY registered for Sent_Walls.
"""

import pytest

from conftest import wall_set


# Minimal stand-in for the agent: Wall_Set belief + print.
class FakeBelief:
    def __init__(self, values):
        self.values = values
        self.changes = 0

    def change(self, values):
        self.values = values
        self.changes += 1


class FakeAgent:
    def __init__(self, walls):
        self.wall_belief = FakeBelief(walls)
        self.logs = []

    def get(self, _belief):
        return self.wall_belief

    def print(self, msg):
        self.logs.append(msg)


# --- unit ---------------------------------------------------------------

def test_adds_single_new_wall(update_walls_plan):
    agent = FakeAgent([(1, 1)])
    update_walls_plan(agent, "wk_2", [(5, 5)])
    assert agent.wall_belief.values == [(1, 1), (5, 5)]
    assert agent.wall_belief.changes == 1


def test_adds_every_new_wall_in_one_message(update_walls_plan):
    agent = FakeAgent([])
    update_walls_plan(agent, "wk_2", [(1, 0), (2, 0), (3, 0)])
    assert agent.wall_belief.values == [(1, 0), (2, 0), (3, 0)]


def test_new_wall_in_the_middle_of_the_list(update_walls_plan):
    # Neither [0] nor [-1] is the unknown wall here.
    agent = FakeAgent([(1, 0), (3, 0)])
    update_walls_plan(agent, "wk_2", [(1, 0), (2, 0), (3, 0)])
    assert sorted(agent.wall_belief.values) == [(1, 0), (2, 0), (3, 0)]


def test_known_walls_are_not_duplicated(update_walls_plan):
    agent = FakeAgent([(1, 0), (2, 0)])
    update_walls_plan(agent, "wk_2", [(2, 0), (1, 0)])
    assert agent.wall_belief.values == [(1, 0), (2, 0)]


def test_nothing_new_changes_nothing(update_walls_plan):
    agent = FakeAgent([(1, 0)])
    update_walls_plan(agent, "wk_2", [(1, 0)])
    assert agent.wall_belief.changes == 0
    assert agent.logs == []


def test_keeps_own_walls_first(update_walls_plan):
    agent = FakeAgent([(9, 9)])
    update_walls_plan(agent, "wk_2", [(0, 0), (9, 9), (0, 1)])
    assert agent.wall_belief.values == [(9, 9), (0, 0), (0, 1)]


def test_empty_message_is_harmless(update_walls_plan):
    agent = FakeAgent([(1, 0)])
    update_walls_plan(agent, "wk_2", [])
    assert agent.wall_belief.values == [(1, 0)]
    assert agent.wall_belief.changes == 0


def test_logs_the_absorbed_walls(update_walls_plan):
    agent = FakeAgent([])
    update_walls_plan(agent, "wk_2", [(4, 4), (5, 5)])
    assert len(agent.logs) == 1
    assert "(4, 4)" in agent.logs[0] and "(5, 5)" in agent.logs[0]
    assert "wk_2" in agent.logs[0]


# --- integration (real Walker + Map) ------------------------------------

def test_plan_is_registered_for_sent_walls(update_walls_plan):
    assert update_walls_plan.__name__ == "update_walls"


def test_real_walker_absorbs_all_walls(make_walker, update_walls_plan):
    receiver = make_walker()
    update_walls_plan(receiver, "wk_x", [(0, 1), (2, 3), (-1, 4)])
    assert wall_set(receiver) == [(0, 1), (2, 3), (-1, 4)]


def test_sender_list_mutated_before_delivery(make_walker, update_walls_plan):
    """The race the PR's [-1] loses.

    MASPY hands the receiver the sender's own list (no copy). Here the
    sender A bumps into w_a and broadcasts its list; before B reads that
    message, A merges w_c from a third walker into the same list. B must
    still learn w_a.
    """
    sender, receiver = make_walker(), make_walker()
    w_a, w_c = (3, 3), (7, 7)

    sent = wall_set(sender)
    sent.append(w_a)                                # A found w_a and broadcast `sent`
    update_walls_plan(sender, "wk_c", [w_c])        # A absorbs w_c into the same list
    assert sent is wall_set(sender) and sent[-1] == w_c

    update_walls_plan(receiver, sender.my_name, sent)  # B finally reads A's message
    assert w_a in wall_set(receiver)
    assert w_c in wall_set(receiver)


def test_two_discoveries_before_delivery(make_walker, update_walls_plan):
    # A finds two walls before B processes either message; both arrive.
    sender, receiver = make_walker(), make_walker()
    sent = wall_set(sender)
    sent.extend([(1, 1), (2, 2)])
    for _ in range(2):  # two Sent_Walls events, same live list
        update_walls_plan(receiver, sender.my_name, sent)
    assert wall_set(receiver) == [(1, 1), (2, 2)]


def test_receiver_list_stays_its_own(make_walker, update_walls_plan):
    # Merging must not alias the receiver's list to the sender's.
    sender, receiver = make_walker(), make_walker()
    sent = wall_set(sender)
    sent.append((1, 1))
    update_walls_plan(receiver, sender.my_name, sent)
    sent.append((2, 2))
    assert wall_set(receiver) == [(1, 1)]

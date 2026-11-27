from hearsay.control.ks import KnowledgeSource, Activation
from hearsay.board.board import Board
from hearsay.protocol.events import (
    Event, ClaimEvent, JustifyEvent, RetractClaimEvent, RetractJustifyEvent, ChallengeEvent
)
from hearsay.control.scheduler import Scheduler
from hearsay.control.ks import KnowledgeSource, Activation

BUDGET = 10
GOAL_THRESHOLD = 0.0

class AndKS(KnowledgeSource):
    '''
    If claims A and B are in, then C in.
    '''
    name = "and"

    def condition(self, board):
        in_set = board.jtms.in_set()
        claims = board.jtms.claims

        if 'A' in in_set and 'B' in in_set:
            if 'C' not in claims:
                activation = Activation(ks=self, trigger_claims=('A', 'B'))
                return [activation]
        
        return []
    
    async def action(self, activation, board):
        claim_event = ClaimEvent(author=self.name, claim_id='C', text='A and B is in. So make C in.',
        kind='hypothesis', level=1, credibility=0.5)

        justify_event = JustifyEvent(author=self.name, justification_id='jC', conclusion='C', premises=('A', 'B'))

        return [claim_event, justify_event]


class ImpliesKS(KnowledgeSource):
    '''
    If C is in, D is in.
    '''
    name = 'implies'

    def condition(self, board):
        in_set = board.jtms.in_set()
        claims = board.jtms.claims

        if 'C' in in_set:
            if 'D' not in claims:
                activation = Activation(ks=self, trigger_claims=('C', ))
                return [activation]
        
        return []
        
    async def action(self, activation, board):
        claim_event = ClaimEvent(author=self.name, claim_id='D', text='C is in, so make D in',
        kind='hypothesis', level=2, credibility=0.3)

        justify_event = JustifyEvent(author=self.name, justification_id='jD', conclusion='D', premises=('C', ))

        return [claim_event, justify_event]

async def test_scheduler():
    # Create Knowledge sources
    and_ks= AndKS()
    implies_ks = ImpliesKS()
    knowledge_sources = [and_ks, implies_ks]

    # Create board and seed raw premises A and B
    board = Board()
    claim_a = ClaimEvent(author='Human', claim_id='A', text='premise A', kind='evidence', level=0, credibility=1.0)
    claim_b = ClaimEvent(author='Human', claim_id='B', text='premise B', kind='evidence', level=0, credibility=1.0)

    board.apply(claim_a)
    board.apply(claim_b)

    budget = BUDGET

    scheduler = Scheduler(knowledge_sources=knowledge_sources, board=board, budget=budget, goal_threshold=GOAL_THRESHOLD)

    await scheduler.run()

    assert board.jtms.in_set() == frozenset({'A', 'B', 'C', 'D'})


# --- scoring / determinism (property 9) ---------------------------------------

class ChoiceKS(KnowledgeSource):
    """Proposes one activation per candidate claim id, so _pick has a real choice.
    Each run it offers activations triggered by each still-unprocessed candidate; running
    one marks it processed by creating a derived claim, so the KS eventually goes quiet.
    """
    name = "choice"

    def __init__(self, candidate_ids):
        self.candidate_ids = candidate_ids

    def condition(self, board):
        in_set = board.jtms.in_set()
        acts = []
        for cid in self.candidate_ids:
            if cid in in_set and f"d_{cid}" not in board.claim_events:
                acts.append(Activation(ks=self, trigger_claims=(cid,)))
        return acts

    async def action(self, activation, board):
        src = activation.trigger_claims[0]
        claim = ClaimEvent(author=self.name, claim_id=f"d_{src}", text=f"derived from {src}",
                           kind="hypothesis", level=1, credibility=0.5)
        justify = JustifyEvent(author=self.name, justification_id=f"jd_{src}",
                               conclusion=f"d_{src}", premises=(src,))
        return [claim, justify]


def _board_with(cred_map):
    """Board seeded with evidence claims {id: credibility}."""
    board = Board()
    for cid, cred in cred_map.items():
        board.apply(ClaimEvent(author="t", claim_id=cid, text=cid,
                               kind="evidence", level=0, credibility=cred))
    return board


async def test_pick_prefers_higher_credibility():
    # Two candidates, different credibility; the first chosen should be the more credible.
    board = _board_with({"lo": 0.2, "hi": 0.9})
    ks = ChoiceKS(["lo", "hi"])
    sched = Scheduler(knowledge_sources=[ks], board=board, budget=1)
    await sched.run()
    # With budget 1, only one activation ran. The high-credibility one should have won.
    assert "d_hi" in board.claim_events
    assert "d_lo" not in board.claim_events


async def test_pick_is_deterministic_across_identical_schedulers():
    # Property 9: identical boards -> identical choices. Run two independent schedulers on
    # separate but identical boards and assert they produce the same final claim set.
    results = []
    for _ in range(2):
        board = _board_with({"a": 0.5, "b": 0.5, "c": 0.5})
        ks = ChoiceKS(["a", "b", "c"])
        sched = Scheduler(knowledge_sources=[ks], board=board, budget=10)
        await sched.run()
        results.append(frozenset(board.claim_events))
    assert results[0] == results[1]


def test_pick_tie_break_is_stable_regardless_of_activation_order():
    # Equal scores must break ties by (ks.name, sorted triggers), not list order.
    # Use a FRESH scheduler for each call: _pick mutates novelty memory, so calling it
    # twice on one instance would not be an apples-to-apples comparison.
    board = _board_with({"a": 0.5, "b": 0.5})
    ks = ChoiceKS(["a", "b"])
    acts = ks.condition(board)

    forward = Scheduler([ks], board, budget=1)._pick(list(acts))
    backward = Scheduler([ks], board, budget=1)._pick(list(reversed(acts)))
    assert forward.trigger_claims == backward.trigger_claims
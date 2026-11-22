from hearsay.control.ks import KnowledgeSource, Activation
from hearsay.board.board import Board
from hearsay.protocol.events import (
    Event, ClaimEvent, JustifyEvent, RetractClaimEvent, RetractJustifyEvent, ChallengeEvent
)
from hearsay.control.scheduler import Scheduler

BUDGET = 10

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
    
    def action(self, activation, board):
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
        
    def action(self, activation, board):
        claim_event = ClaimEvent(author=self.name, claim_id='D', text='C is in, so make D in',
        kind='hypothesis', level=2, credibility=0.3)

        justify_event = JustifyEvent(author=self.name, justification_id='jD', conclusion='D', premises=('C', ))

        return [claim_event, justify_event]

def test_scheduler():
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

    scheduler = Scheduler(knowledge_sources=knowledge_sources, board=board, budget=budget)

    scheduler.run()

    assert board.jtms.in_set() == frozenset({'A', 'B', 'C', 'D'})
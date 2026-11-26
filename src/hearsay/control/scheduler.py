from hearsay.control.ks import KnowledgeSource, Activation
from hearsay.board.board import Board

class Scheduler:
    def __init__(self, knowledge_sources: list[KnowledgeSource], board: Board, budget: float, goal_threshold: float = 0.0):
        self.knowledge_sources = knowledge_sources
        self.board = board
        self.budget = budget
        self.goal_threshold = goal_threshold
    
    def run(self):
        all_events = []
        while self.budget > 0:
            # Get a list of all possible activations
            activations = []
            for ks in self.knowledge_sources:
                activations.extend(ks.condition(self.board))
            
            if not activations:
                break
                
            # Pick an activation to run
            chosen_activation = self._pick(activations)
            chosen_ks = chosen_activation.ks

            events = chosen_ks.action(chosen_activation, self.board)
            all_events = all_events + events

            # Apply the outlined events from the KS to the board
            for event in events:
                self.board.apply(event)

            # Check if goal is IN
            in_set = self.board.jtms.in_set()
            for claim_id in in_set:
                claim_event = self.board.claim_events[claim_id]

                if claim_event.kind == 'goal' and claim_event.credibility >= self.goal_threshold:
                    return all_events

            self.budget -=1
        
        return all_events
    
    def _pick(self, activations: list[Activation]):
        #TODO: More comprehensive pick
        return activations[0]
    


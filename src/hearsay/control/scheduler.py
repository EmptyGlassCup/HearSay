from hearsay.control.ks import KnowledgeSource, Activation
from hearsay.board.board import Board

class Scheduler:
    def __init__(self, knowledge_sources: list[KnowledgeSource], board: Board, budget: float):
        self.knowledge_sources = knowledge_sources
        self.board = board
        self.budget = budget
    
    def run(self):
        #TODO: also implement break when a goal claim is IN
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
                
            self.budget -=1
        
        return all_events
    
    def _pick(self, activations: list[Activation]):
        #TODO: More comprehensive pick
        return activations[0]
    


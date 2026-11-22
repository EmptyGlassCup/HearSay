from dataclasses import dataclass, field
from abc import ABC, abstractmethod

class KnowledgeSource(ABC):
    name: str

    @abstractmethod
    def condition(self, board):
        '''Return a list of activations which the Knowledge Source can choose from'''
    
    @abstractmethod
    def action(self, activation, board):
        '''Execute the parameter activation and return the list of events produced'''
        

@dataclass(frozen=True)
class Activation:
    ks: KnowledgeSource
    trigger_claims: tuple[str, ...]
    payload: dict = field(default_factory=dict)


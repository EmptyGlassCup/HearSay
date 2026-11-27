from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio

class KnowledgeSource(ABC):
    name: str
    cost: float = 1.0   # relative cost of running this KS; the scheduler penalises by it.
                        # Classical KSs ~1.0; LLM-backed KSs should override higher (e.g. 5.0).

    @abstractmethod
    def condition(self, board) -> list['Activation']:
        '''Return a list of activations which the Knowledge Source could choose to do'''
    
    @abstractmethod
    async def action(self, activation, board) -> list['Event']:
        '''Execute the parameter activation and return the list of events produced'''
        

@dataclass(frozen=True)
class Activation:
    ks: KnowledgeSource
    trigger_claims: tuple[str, ...]
    payload: dict = field(default_factory=dict)


from dataclasses import dataclass

@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    kind: str

@dataclass(frozen=True)
class Justification:
    id: str
    conclusion: str
    premises: tuple[str, ...]

#Justification Based Truth System
class JTMS:
    def __init__(self):
        self.claims = {}
        self.justifications = {}
        self.retracted_claims = set()
        self.retracted_justifications = set()
    
    def add_claim(self, claim: Claim):
        if claim.id in self.claims:
            raise ValueError(f"Claim {claim.id} already exists")

        self.claims[claim.id] = claim
    
    def add_justification(self, justification: Justification):
        if justification.id in self.justifications:
            raise ValueError(f"Justification {justification.id} already exists")

        for premise_id in justification.premises:
            if premise_id not in self.claims:
                raise ValueError(f"Premise claim {premise_id} does not exist")

        if justification.conclusion not in self.claims:
            raise ValueError(f"Conclusion claim {justification.conclusion} does not exist")
        
        self.justifications[justification.id] = justification
    
    def retract_claim(self, claim: Claim):
        if claim.id not in self.claims:
            raise ValueError(f"Claim {claim.id} does not exist")
        
        self.retracted_claims.add(claim.id)

    def retract_justification(self, justification: Justification):
        if justification.id not in self.justifications:
            raise ValueError(f"Justification {justification.id} does not exist")
        
        self.retracted_justifications.add(justification.id)

    def in_set(self):
        # Find all unretracted claims and justifications
        active_claims = {claim_id for claim_id in self.claims if claim_id not in self.retracted_claims}
        
        active_justifications = {justification_id for justification_id in self.justifications if justification_id not in self.retracted_justifications}

        # Get the claims dependant on justifications
        dependant_claims = set()
        for justification_id in active_justifications:
            justification = self.justifications[justification_id]
            dependant_claims.add(justification.conclusion)
        
        # Initialise supported claims with root claims
        supported_claims = active_claims - dependant_claims

        # Build up all supported claims
        while True:
            claim_added = False
            for justification_id in active_justifications:
                justification = self.justifications[justification_id]

                if justification.conclusion in active_claims and justification.conclusion not in supported_claims:
                    if set(justification.premises).issubset(supported_claims):
                        claim_added = True
                        supported_claims.add(justification.conclusion)
                
            
            if not claim_added:
                break
        
        return frozenset(supported_claims)


            



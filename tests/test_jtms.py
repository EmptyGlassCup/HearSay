from hypothesis import given, strategies as st
from hearsay.tms.jtms import JTMS, Claim, Justification

MAX_CLAIMS = 10
MAX_PREMISES = 5

'''
We should test six properties:
    1. Soundness     - DONE: every IN claim is a raw premise, or has a justification with all premises IN
    2. Completeness  - TODO: IN set equals a naive from-scratch oracle (catches missing claims)
    3. Incremental   - TODO: skip until an incremental relabeler exists
    4. Order indep.  - TODO: same assertions/retractions in any order -> same IN set
    5. Revival       - TODO: retract then re-assert a premise -> original labeling restored
    6. No self-support - TODO: cyclic justifications alone never make claims IN
'''

@st.composite
def jtms_strategy(draw):
    # Generate a random number of claim
    n_claims = draw(st.integers(min_value=0, max_value=MAX_CLAIMS))
    claim_ids = [f'c{i}' for i in range(n_claims)]

    claims = [Claim(claim_id, text=claim_id, kind='evidence') for claim_id in claim_ids]


    # Generate a random number of justifications
    justifications = []

    if claim_ids:
        n_justifications = draw(st.integers(min_value=0, max_value=MAX_CLAIMS))

        for i in range(n_justifications):

            conclusion = draw(st.sampled_from(claim_ids))
            premises = draw(st.lists(st.sampled_from(claim_ids), max_size=MAX_PREMISES, unique=True))
            
            justifications.append(Justification(f'j{i}', conclusion=conclusion, premises=tuple(premises)))

    return claims, justifications
        




@given(jtms_strategy())
def test_soundness(data):
    claims, justifications = data
    truth_system = JTMS()

    for claim in claims:
        truth_system.add_claim(claim)
    for justification in justifications:
        truth_system.add_justification(justification)

    in_set = truth_system.in_set()

    for supported_claim_id in in_set:
        supporting_justifications = [j for j in justifications if supported_claim_id == j.conclusion]

        # If the claim has justifications (not raw premise), check at least one of the justifications is valid
        if supporting_justifications:
            assert any(all(premise in in_set for premise in j.premises) for j in supporting_justifications), \
                f"None of the justifications for claim {supported_claim_id} has all premise claims as IN"
        


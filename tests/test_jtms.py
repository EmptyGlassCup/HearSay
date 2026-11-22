from hypothesis import given, strategies as st
from hearsay.tms.jtms import JTMS, Claim, Justification

MAX_CLAIMS = 10
MAX_PREMISES = 5

'''
Six properties (protocol.md):
    1. Soundness       - DONE: every IN claim is a raw premise, or has a justification with all premises IN
    2. Completeness    - DONE: IN set equals a naive from-scratch oracle (catches missing claims)
    3. Incremental     - N/A: no incremental relabeler; in_set() always recomputes from scratch
    4. Order indep.    - DONE: same assertions/retractions in any order -> same IN set
    5. Revival         - DONE: retraction is permanent; a ghosted claim revives when a NEW
                         justification with all-IN premises is added (not by un-retracting)
    6. No self-support - DONE: cyclic justifications alone never make claims IN
'''

@st.composite
def jtms_strategy(draw):
    # Generate a random number of claim
    n_claims = draw(st.integers(min_value=0, max_value=MAX_CLAIMS))
    claim_ids = [f'c{i}' for i in range(n_claims)]

    claims = [Claim(claim_id, text=claim_id, kind='evidence') for claim_id in claim_ids]

    retracted_claim_ids = []
    if claims:
        retracted_claim_ids = draw(st.lists(st.sampled_from(claim_ids), max_size=MAX_CLAIMS, unique=True))


    # Generate a random number of justifications
    justifications = []

    if claim_ids:
        n_justifications = draw(st.integers(min_value=0, max_value=MAX_CLAIMS))

        for i in range(n_justifications):

            conclusion = draw(st.sampled_from(claim_ids))
            premises = draw(st.lists(st.sampled_from(claim_ids), max_size=MAX_PREMISES, unique=True))
            
            justifications.append(Justification(f'j{i}', conclusion=conclusion, premises=tuple(premises)))

    justification_ids = [j.id for j in justifications]
    retracted_justification_ids = []
    if justifications:
        retracted_justification_ids = draw(st.lists(st.sampled_from(justification_ids), max_size=MAX_PREMISES, unique=True))

    return claims, justifications, retracted_claim_ids, retracted_justification_ids





@given(jtms_strategy())
def test_soundness(data):
    claims, justifications, retracted_claim_ids, retracted_justification_ids = data
    truth_system = JTMS()

    for claim in claims:
        truth_system.add_claim(claim)
    for justification in justifications:
        truth_system.add_justification(justification)

    for claim_id in retracted_claim_ids:
        truth_system.retract_claim(claim_id)
    for justification_id in retracted_justification_ids:
        truth_system.retract_justification(justification_id)

    in_set = truth_system.in_set()

    for supported_claim_id in in_set:
        supporting_justifications = [j for j in justifications
        if supported_claim_id == j.conclusion and j.id not in retracted_justification_ids]

        # If the claim has justifications (not raw premise), check at least one of the justifications is valid
        if supporting_justifications:
            assert any(all(premise in in_set for premise in j.premises) for j in supporting_justifications), \
                f"None of the justifications for claim {supported_claim_id} has all premise claims as IN"
        


@given(jtms_strategy())
def test_completeness(data):
    claims, justifications, retracted_claim_ids, retracted_justification_ids = data
    truth_system = JTMS()

    for claim in claims:
        truth_system.add_claim(claim)
    for justification in justifications:
        truth_system.add_justification(justification)

    for claim_id in retracted_claim_ids:
        truth_system.retract_claim(claim_id)
    for justification_id in retracted_justification_ids:
        truth_system.retract_justification(justification_id)

    active_claims = [c for c in claims if c.id not in retracted_claim_ids]
    active_justifications = [j for j in justifications if j.id not in retracted_justification_ids]


    # Independantly rebuild the IN claim
    in_set = set()
    while True:
        new_in = set()

        # Iteratively build up the claims
        for claim in active_claims:
            supporting_justifications = [j for j in active_justifications if j.conclusion == claim.id]

            if not supporting_justifications:
                new_in.add(claim.id)
            elif any(all(premise in in_set for premise in j.premises) for j in supporting_justifications):
                new_in.add(claim.id)
        
        # Nothing added
        if new_in == in_set:
            break
        
        in_set = new_in
    
    assert frozenset(in_set) == truth_system.in_set()



@given(jtms_strategy(), st.data())
def test_order_independance(data, draws):
    claims, justifications, retracted_claim_ids, retracted_justification_ids = data
    truth_system = JTMS()

    # Build first in set
    for claim in claims:
        truth_system.add_claim(claim)
    for justification in justifications:
        truth_system.add_justification(justification)

    for claim_id in retracted_claim_ids:
        truth_system.retract_claim(claim_id)
    for justification_id in retracted_justification_ids:
        truth_system.retract_justification(justification_id)

    in_set_1 = truth_system.in_set()

    # Shuffle the data
    claims = draws.draw(st.permutations(claims))
    justifications = draws.draw(st.permutations(justifications))
    retracted_claim_ids = draws.draw(st.permutations(list(retracted_claim_ids)))
    retracted_justification_ids = draws.draw(st.permutations(list(retracted_justification_ids)))

    # Build second in set
    truth_system = JTMS()

    for claim in claims:
        truth_system.add_claim(claim)
    for justification in justifications:
        truth_system.add_justification(justification)

    for claim_id in retracted_claim_ids:
        truth_system.retract_claim(claim_id)
    for justification_id in retracted_justification_ids:
        truth_system.retract_justification(justification_id)

    in_set_2 = truth_system.in_set()

    assert in_set_1 == in_set_2



def test_revival():
    truth_system = JTMS()

    # Initial claims
    claims = [Claim(id='c0', text='c0', kind='evidence'), Claim(id='c1', text='c1', kind='evidence'), Claim(id='c2', text='c2', kind='hypothesis')]
    justifications = [Justification(id='j0', conclusion='c2', premises=('c0', 'c1'))]

    for claim in claims:
        truth_system.add_claim(claim)
    for justification in justifications:
        truth_system.add_justification(justification)

    assert truth_system.in_set() == frozenset({'c0', 'c1', 'c2'})

    # Retract a premise claim
    truth_system.retract_claim('c1')
    assert truth_system.in_set() == frozenset({'c0'})

    # Reintroduce an identical claim\
    truth_system.add_claim(Claim(id='c1b', text='c1b', kind='evidence'))
    truth_system.add_justification(Justification(id='j0b', conclusion='c2', premises=('c0', 'c1b')))

    assert truth_system.in_set() == frozenset({'c0', 'c1b', 'c2'})




def test_self_support():
    truth_system = JTMS()

    # Case 1: Self justification
    claims = [Claim(id='c1', text='c1', kind='hypothesis')]
    justifications = [Justification(id='j1', conclusion='c1', premises=('c1', ))]

    for claim in claims:
        truth_system.add_claim(claim)
    for justification in justifications:
        truth_system.add_justification(justification)
    
    assert truth_system.in_set() == frozenset()

    # Case 2: Two-cycle
    truth_system = JTMS()

    claims = [Claim(id='c1', text='c1', kind='hypothesis'), Claim(id='c2', text='c2', kind='hypothesis')]
    justifications = [Justification(id='j1', conclusion='c2', premises=('c1', )), Justification(id='j2', conclusion='c1', premises=('c2', ))]

    for claim in claims:
        truth_system.add_claim(claim)
    for justification in justifications:
        truth_system.add_justification(justification)
    
    assert truth_system.in_set() == frozenset()

    # Case 3: Cycle + Ground
    truth_system = JTMS()

    claims = [Claim(id='c0', text='c0', kind='evidence'), Claim(id='c1', text='c1', kind='hypothesis'), Claim(id='c2', text='c2', kind='hypothesis')]
    justifications = [Justification(id='j1', conclusion='c2', premises=('c0', 'c1')), Justification(id='j2', conclusion='c1', premises=('c2', ))]

    for claim in claims:
        truth_system.add_claim(claim)
    for justification in justifications:
        truth_system.add_justification(justification)
    
    assert truth_system.in_set() == frozenset({'c0'})


    



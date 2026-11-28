"""
Test that !goal (via kernel.set_goal) reconfigures the LLM agents' question, duck-typed.
"""
from hearsay.control.kernel import Kernel
from hearsay.experts.llm_hypothesis import LLMHypothesisKS


class DummyLLM:
    def complete(self, prompt): return '{"done": true}'


class NoQuestionKS:
    name = "nq"
    cost = 1.0
    def condition(self, board): return []
    async def action(self, activation, board): return []


def _kernel(knowledge_sources):
    # Construct without connecting — we only touch set_goal / scheduler state.
    return Kernel(knowledge_sources=knowledge_sources, host="127.0.0.1", port=6667,
                  nickname="hearsay", budget=5, goal_threshold=0.0)


def test_set_goal_updates_llm_agents():
    a1 = LLMHypothesisKS(llm=DummyLLM(), name="a1", id_prefix="a")
    a2 = LLMHypothesisKS(llm=DummyLLM(), name="a2", id_prefix="b")
    k = _kernel([a1, a2])

    applied = k.set_goal("What broke the deploy?")
    assert applied == 2
    assert a1.question == "What broke the deploy?"
    assert a2.question == "What broke the deploy?"


def test_set_goal_skips_sources_without_question():
    a = LLMHypothesisKS(llm=DummyLLM(), name="a", id_prefix="a")
    nq = NoQuestionKS()
    k = _kernel([a, nq])

    applied = k.set_goal("root cause?")
    assert applied == 1                 # only the LLM agent has a `question`
    assert a.question == "root cause?"

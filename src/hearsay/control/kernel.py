import asyncio
from hearsay.protocol.codec import encode, decode, decode_human_command, HELP_TEXT
from hearsay.protocol.events import ClaimEvent
from hearsay.irc.parser import IRCMessage, serialize
from hearsay.irc.client import IRCClient
from hearsay.board.board import Board
from hearsay.control.scheduler import Scheduler
from hearsay.ui.server import UIServer

class Kernel:
    def __init__(self, knowledge_sources, host, port, nickname, budget, goal_threshold,
                 llm_key_present=True):
        self.board = Board()
        self.scheduler = Scheduler(knowledge_sources=knowledge_sources, board=self.board, budget=budget, goal_threshold=goal_threshold)
        self.budget = budget
        self.client = IRCClient(host=host, port=port, nickname=nickname, on_message=self.on_message)
        self.nickname = nickname
        self.ui = UIServer(self.board, on_command=self.run_analysis, status_provider=self.status)
        self._human_claim_counter = 0   # assigns ids to human-typed !claim commands
        self._goal = None               # the explicitly-set goal (None until !goal)
        self._llm_key_present = llm_key_present
        self._last_error = None         # last analysis failure, surfaced to the UI

    def status(self) -> dict:
        """Live kernel status for the UI: explicit goal, LLM key presence, last error."""
        return {
            "goal": self._goal,
            "llm_key_present": self._llm_key_present,
            "last_error": self._last_error,
        }

    def _allocate_human_id(self) -> str:
        self._human_claim_counter += 1
        return f"h{self._human_claim_counter}"

    def set_goal(self, question: str) -> int:
        """Set the question LLM agents reason toward. Returns how many agents received it.
        Duck-typed: any knowledge source with a `question` attribute is updated."""
        self._goal = question
        applied = 0
        for ks in self.scheduler.knowledge_sources:
            if hasattr(ks, "question"):
                ks.question = question
                applied += 1
        return applied

    async def on_message(self, msg: IRCMessage):
        if msg.prefix and msg.prefix.split('!')[0] == self.nickname:
            return

        # !help: reply with the command syntax, no board change.
        text = msg.params[-1].strip() if msg.params else ""
        if text.lower().startswith("!help"):
            self.client.send(serialize(IRCMessage(
                command="PRIVMSG", params=["#control", HELP_TEXT])))
            return

        # !goal <text>: set the question the LLM agents reason toward. Not a board event —
        # it reconfigures the agents, so it is handled here, not in decode_human_command.
        if text.lower().startswith("!goal"):
            question = text[len("!goal"):].strip()
            if question:
                applied = self.set_goal(question)
                reply = f"goal set for {applied} agent(s): {question}" if applied else \
                        "no LLM agents to receive a goal"
                self.client.send(serialize(IRCMessage(
                    command="PRIVMSG", params=["#control", reply])))
            return

        # Tagged machine event first (always a single event); fall back to a human-typed
        # !command, which may produce several events (a grounded claim -> claim + justify).
        tagged = decode(msg)
        events = [tagged] if tagged is not None else \
                 decode_human_command(msg, self._allocate_human_id, self.board)
        if not events:
            return

        for event in events:
            self.board.apply(event)
            # Echo back the assigned id for a human claim, so they can retract it later.
            if isinstance(event, ClaimEvent) and event.author != self.nickname:
                self.client.send(serialize(IRCMessage(
                    command="PRIVMSG",
                    params=["#control", f"added {event.claim_id}: {event.text}"])))

        await self.ui.broadcast()

    async def run_analysis(self, cmd=None):
        # Always broadcast at the end — even if the scheduler or an LLM call throws — so the
        # UI's "analysing..." button re-enables instead of hanging forever.
        try:
            self.scheduler.budget = self.budget
            ks_events = await self.scheduler.run()
            for ks_event in ks_events:
                ks_msg = encode(ks_event, self.board)
                if ks_msg is None:
                    continue
                self.client.send(serialize(ks_msg))
            self._last_error = None          # clear on a clean run
        except Exception as exc:
            # Surface the failure both to IRC and (persistently) to the UI status bar.
            self._last_error = str(exc)
            self.client.send(serialize(IRCMessage(
                command="PRIVMSG",
                params=["#control", f"analysis failed: {exc}"])))
        finally:
            await self.ui.broadcast()
    
    async def start(self):
        await self.client.connect()

        # Start web UI
        await self.ui.start(host="127.0.0.1", port=8000)

        # Loop forever
        await asyncio.Event().wait()






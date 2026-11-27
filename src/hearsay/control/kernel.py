import asyncio
from hearsay.protocol.codec import encode, decode, decode_human_command, HELP_TEXT
from hearsay.protocol.events import ClaimEvent
from hearsay.irc.parser import IRCMessage, serialize
from hearsay.irc.client import IRCClient
from hearsay.board.board import Board
from hearsay.control.scheduler import Scheduler
from hearsay.ui.server import UIServer

class Kernel:
    def __init__(self, knowledge_sources, host, port, nickname, budget, goal_threshold):
        self.board = Board()
        self.scheduler = Scheduler(knowledge_sources=knowledge_sources, board=self.board, budget=budget, goal_threshold=goal_threshold)
        self.budget = budget
        self.client = IRCClient(host=host, port=port, nickname=nickname, on_message=self.on_message)
        self.nickname = nickname
        self.ui = UIServer(self.board, on_command=self.run_analysis)
        self._human_claim_counter = 0   # assigns ids to human-typed !claim commands

    def _allocate_human_id(self) -> str:
        self._human_claim_counter += 1
        return f"h{self._human_claim_counter}"

    async def on_message(self, msg: IRCMessage):
        if msg.prefix and msg.prefix.split('!')[0] == self.nickname:
            return

        # !help: reply with the command syntax, no board change.
        text = msg.params[-1].strip() if msg.params else ""
        if text.lower().startswith("!help"):
            self.client.send(serialize(IRCMessage(
                command="PRIVMSG", params=["#control", HELP_TEXT])))
            return

        # Tagged machine event first; fall back to a human-typed !command.
        event = decode(msg)
        if event is None:
            event = decode_human_command(msg, self._allocate_human_id)
        if event is None:
            return

        self.board.apply(event)

        # Echo back the assigned id for a human claim, so they know how to retract it later.
        if isinstance(event, ClaimEvent) and event.author != self.nickname:
            self.client.send(serialize(IRCMessage(
                command="PRIVMSG",
                params=["#control", f"added {event.claim_id}: {event.text}"])))

        await self.ui.broadcast()

    async def run_analysis(self, cmd=None):
        self.scheduler.budget = self.budget
        ks_events = await self.scheduler.run()


        for ks_event in ks_events:
            ks_msg = encode(ks_event, self.board)

            if ks_msg is None:
                continue

            ks_str = serialize(ks_msg)
            self.client.send(ks_str)

        await self.ui.broadcast()
    
    async def start(self):
        await self.client.connect()

        # Start web UI
        await self.ui.start(host="127.0.0.1", port=8000)

        # Loop forever
        await asyncio.Event().wait()






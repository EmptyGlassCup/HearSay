import asyncio
from hearsay.protocol.codec import encode, decode
from hearsay.protocol.events import Event
from hearsay.irc.parser import IRCMessage, serialize
from hearsay.irc.client import IRCClient
from hearsay.board.board import Board
from hearsay.control.scheduler import Scheduler

class Kernel:
    def __init__(self, knowledge_sources, host, port, nickname, budget, goal_threshold):
        self.board = Board()
        self.scheduler = Scheduler(knowledge_sources=knowledge_sources, board=self.board, budget=budget, goal_threshold=goal_threshold)
        self.client = IRCClient(host=host, port=port, nickname=nickname, on_message=self.on_message)
        self.nickname = nickname

    async def on_message(self, msg: IRCMessage):
        # Apply Event to the Board
        event = decode(msg)
        if event == None:
            return

        print(f"APPLYING: {event.claim_id if hasattr(event, 'claim_id') else event}")

        try:
            self.board.apply(event)
        except Exception as e:
            print(f"APPLY FAILED: {e}")
            return
        print(f"IN SET NOW: {self.board.jtms.in_set()}")

        # Run the scheduler
        self.scheduler.budget = BUDGET
        ks_events = self.scheduler.run()
        print(f"SCHEDULER PRODUCED: {[getattr(e, 'claim_id', e) for e in ks_events]}")

        # send out all the KS events to the IRC
        for ks_event in ks_events:
            ks_msg = encode(ks_event, self.board)
            if ks_msg.prefix == self.nickname:
                continue
            
            ks_str = serialize(ks_msg)
            if ks_str == None:
                continue

            self.client.send(ks_msg)
    
    async def start(self):
        await self.client.connect()

        # Loop forever
        await asyncio.Event().wait()






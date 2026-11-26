import asyncio
from hearsay.protocol.codec import encode, decode
from hearsay.protocol.events import Event
from hearsay.irc.parser import IRCMessage, serialize
from hearsay.irc.client import IRCClient
from hearsay.board.board import Board
from hearsay.control.scheduler import Scheduler

KNOWLEDGE_SOURCES = []
HOST = '127.0.0.1'
PORT = 6667
BUDGET = 10
NICKNAME = 'tester'

class Kernel:
    def __init__(self, knowledge_sources, host, port, nickname, budget):
        self.board = Board()
        self.scheduler = Scheduler(knowledge_sources=knowledge_sources, board=self.board, budget=budget)
        self.client = IRCClient(host=host, port=port, nickname=nickname, on_message=self.on_message)

    async def on_message(self, msg: IRCMessage):
        #Re-broadcast the event
        # self.client.send(serialize(msg))

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
            ks_msg = serialize(encode(ks_event, self.board))
            self.client.send(ks_msg)
    
    async def start(self):
        await self.client.connect()

        # Loop forever
        await asyncio.Event().wait()


async def main():
    kernel = Kernel(
        knowledge_sources=KNOWLEDGE_SOURCES,
        host=HOST,
        port=PORT,
        nickname=NICKNAME,
        budget=BUDGET
    )
    await kernel.start()

if __name__ == "__main__":
    asyncio.run(main())






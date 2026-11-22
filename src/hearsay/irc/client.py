import asyncio
from hearsay.irc.parser import parse, IRCMessage, serialize

SERVER_CMDS = ('CAP', '001', '002', '003', '004', '005', '221', '251', '252', '253', '254', '255', '265', '266', '372', '375', '376', '353', '366')

class IRCClient:
    def __init__(self, host: str, port: int, nickname: str, on_message):
        """
        host        : IRC server address, e.g. '127.0.0.1'
        port        : IRC server port, e.g. 6667
        on_message  : async function called with each received IRCMessage,
                    after PING/PONG is handled. Signature: async def f(msg: IRCMessage)
        """
        self.host = host
        self.port = port
        self.queue = asyncio.Queue()
        self.reader = None
        self.writer = None
        self.on_message = on_message
        self.nickname = nickname
        self._read_task = None
        self._write_task = None

    def handshake(self):
        self.send(serialize(IRCMessage(command='CAP', params=['REQ', 'message-tags'])))
        self.send(serialize(IRCMessage(command='NICK', params=[self.nickname])))
        self.send(serialize(IRCMessage(command='USER', params=[self.nickname, '0', '*', self.nickname])))
        self.send(serialize(IRCMessage(command='CAP', params=['END'])))
        self.send(serialize(IRCMessage(command='JOIN', params=['#evidence,#hypotheses,#conclusions,#control'])))

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        self._read_task = asyncio.create_task(self._read_loop())
        self._write_task = asyncio.create_task(self._write_loop())

        self.handshake()

    async def disconnect(self):
        self._read_task.cancel()
        self._write_task.cancel()
        self.writer.close()
        await self.writer.wait_closed()

    def send(self, line: str):
        self.queue.put_nowait(line)

    async def _read_loop(self):
        while True:
            raw = await self.reader.readline()
            if not raw:
                break

            msg = parse(raw.decode('utf-8', errors='replace'))

            # Don't pass PING messages to kernal
            if msg.command == 'PING':
                return_msg = serialize(IRCMessage(command='PONG', params=[msg.params[0]]))
                self.send(return_msg)

                continue

            # Don't pass CAP or numeric commands to kernal
            if msg.command in SERVER_CMDS:
                continue
            
            await self.on_message(msg)

    async def _write_loop(self):
        while True:
            line = await self.queue.get()
            self.writer.write(line.encode())
            await self.writer.drain()
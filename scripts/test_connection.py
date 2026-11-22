"""
Manual connection test. Run with:
    python scripts/test_connection.py

Expects Ergo running on 127.0.0.1:6667.
Connects, registers, joins channels, prints received messages for 10 seconds, then disconnects.
"""
import asyncio
from hearsay.irc.client import IRCClient


async def on_message(msg):
    print(f"[{msg.command}] prefix={msg.prefix} params={msg.params} tags={msg.tags}")


async def main():
    client = IRCClient(
        host="127.0.0.1",
        port=6667,
        nickname="hearsay-test",
        on_message=on_message,
    )

    print("Connecting...")
    await client.connect()
    print("Connected. Listening for 10 seconds...")

    await asyncio.sleep(10)

    print("Disconnecting...")
    await client.disconnect()
    print("Done.")


asyncio.run(main())

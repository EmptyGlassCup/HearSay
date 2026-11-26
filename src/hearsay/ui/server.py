"""
Web UI server: FastAPI + WebSocket.

Read-only window onto a Board. Serves a single HTML page (the Cytoscape graph) and a
WebSocket that pushes the current board snapshot to every connected browser. The kernel
calls `broadcast()` after it applies events, so the graph updates live.

The UI never mutates the board — it only renders snapshots.

Usage (wired by the kernel):
    ui = UIServer(board)
    await ui.start(host="127.0.0.1", port=8000)   # runs uvicorn in the background
    ...
    await ui.broadcast()                            # after board changes
"""
import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

from hearsay.ui.snapshot import board_snapshot

_WEB_DIR = Path(__file__).parent / "web"


class UIServer:
    def __init__(self, board):
        self.board = board
        self.app = FastAPI()
        self._clients: set[WebSocket] = set()
        self._server: uvicorn.Server | None = None
        self._register_routes()

    def _register_routes(self):
        @self.app.get("/")
        async def index() -> HTMLResponse:
            return HTMLResponse((_WEB_DIR / "index.html").read_text(encoding="utf-8"))

        @self.app.websocket("/ws")
        async def ws(websocket: WebSocket):
            await websocket.accept()
            self._clients.add(websocket)
            # Send the current state immediately on connect.
            await websocket.send_json(board_snapshot(self.board))
            try:
                while True:
                    # We don't expect client messages; keep the socket open.
                    await websocket.receive_text()
            except WebSocketDisconnect:
                pass
            finally:
                self._clients.discard(websocket)

    async def broadcast(self):
        """Push the current board snapshot to every connected browser."""
        if not self._clients:
            return
        snapshot = board_snapshot(self.board)
        dead = set()
        for client in self._clients:
            try:
                await client.send_json(snapshot)
            except Exception:
                dead.add(client)
        self._clients -= dead

    async def start(self, host: str = "127.0.0.1", port: int = 8000):
        config = uvicorn.Config(self.app, host=host, port=port, log_level="warning")
        self._server = uvicorn.Server(config)
        # Run the server as a background task so the caller's event loop keeps going.
        asyncio.create_task(self._server.serve())

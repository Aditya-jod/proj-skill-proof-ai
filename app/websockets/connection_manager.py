from typing import List
import logging

from fastapi import WebSocket


logger = logging.getLogger("skillproof.websocket")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            logger.debug("Attempted to remove unknown websocket connection")

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Websocket send failed", exc_info=exc)
                self.disconnect(connection)


manager = ConnectionManager()

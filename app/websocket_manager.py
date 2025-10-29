from typing import List, Dict
from fastapi import WebSocket, WebSocketDisconnect
import json

class ConnectionManager:
    """
    Clase para gestionar las conexiones de WebSockets.
    Solo almacena conexiones activas y permite enviar mensajes.
    """
    def __init__(self):
        # Lista de conexiones WebSocket activas
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Añade una nueva conexión activa."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WS conectado. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remueve una conexión inactiva."""
        self.active_connections.remove(websocket)
        print(f"WS desconectado. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Envía un mensaje a un cliente específico."""
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        """Envía un mensaje a todos los clientes conectados."""
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

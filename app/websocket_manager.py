# websocket_manager.py
from typing import List
from fastapi import WebSocket, WebSocketDisconnect
import json

class ConnectionManager:
    """
    Clase para gestionar las conexiones WebSocket activas.
    Las meseras se conectarán aquí para recibir notificaciones.
    """
    def __init__(self):
        # Almacenará las conexiones activas
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Añade una nueva conexión a la lista."""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Nueva conexión WebSocket activa: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        """Remueve una conexión inactiva."""
        self.active_connections.remove(websocket)
        print(f"Conexión WebSocket cerrada: {websocket.client}")

    async def broadcast(self, message: str):
        """Envía un mensaje a todas las conexiones activas."""
        # Se usa 'broadcast' porque todas las meseras necesitan saber 
        # que hay una orden lista, independientemente de la mesa.
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                # Limpiar conexiones desconectadas si ocurre un error
                self.disconnect(connection)
            except Exception as e:
                print(f"Error al enviar broadcast: {e}")

# Instancia global del Manager (solo una)
manager = ConnectionManager()
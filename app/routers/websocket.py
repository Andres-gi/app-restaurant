from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket_manager import manager

router = APIRouter(
    prefix="/ws",
    tags=["WebSockets"]
)

@router.websocket("/notifications")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint de WebSocket para recibir notificaciones en tiempo real.
    (Usado principalmente por el rol 'mesero' para saber cuándo un pedido está listo).
    """
    await manager.connect(websocket)
    try:
        # Loop que mantiene la conexión abierta
        while True:
            # Esperamos recibir un mensaje del cliente, aunque no lo usemos. 
            # Si el cliente cierra la conexión, esto lanza WebSocketDisconnect.
            data = await websocket.receive_text()
            # Opcional: si quisieras recibir comandos del cliente:
            # await manager.send_personal_message(f"Mensaje recibido: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

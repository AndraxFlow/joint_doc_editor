from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Хранилище активных соединений: {document_id: {user_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Хранилище операций для каждого документа
        self.document_operations: Dict[str, List[dict]] = {}

    async def connect(self, websocket: WebSocket, document_id: str, user_id: str):
        """Подключение пользователя к документу"""
        await websocket.accept()
        logger.info(f"WebSocket accepted for user {user_id} on document {document_id}")
        
        if document_id not in self.active_connections:
            self.active_connections[document_id] = {}
            self.document_operations[document_id] = []
            logger.info(f"Created new document session for {document_id}")
        
        self.active_connections[document_id][user_id] = websocket
        logger.info(f"User {user_id} added to active connections for document {document_id}")
        
        try:
            # Отправляем приветственное сообщение
            welcome_message = {
                "type": "connected",
                "data": {
                    "document_id": document_id,
                    "user_id": user_id,
                    "active_users": list(self.active_connections[document_id].keys())
                }
            }
            await websocket.send_text(json.dumps(welcome_message))
            logger.info(f"Sent welcome message to user {user_id}")
            
            # Уведомляем других пользователей о новом подключении
            await self.broadcast_to_document(document_id, {
                "type": "user_joined",
                "data": {
                    "user_id": user_id,
                    "active_users": list(self.active_connections[document_id].keys())
                }
            }, exclude_user=user_id)
            
            logger.info(f"User {user_id} successfully connected to document {document_id}")
        except Exception as e:
            logger.error(f"Error during connection setup for user {user_id}: {e}")
            raise

    def disconnect(self, document_id: str, user_id: str):
        """Отключение пользователя от документа"""
        if document_id in self.active_connections:
            if user_id in self.active_connections[document_id]:
                del self.active_connections[document_id][user_id]
            
            # Если нет больше подключений к документу, очищаем данные
            if not self.active_connections[document_id]:
                del self.active_connections[document_id]
                if document_id in self.document_operations:
                    del self.document_operations[document_id]
        
        logger.info(f"User {user_id} disconnected from document {document_id}")

    async def broadcast_to_document(self, document_id: str, message: dict, exclude_user: str = None):
        """Рассылка сообщения всем пользователям документа"""
        if document_id not in self.active_connections:
            return
        
        message_json = json.dumps(message)
        disconnected_users = []
        
        for user_id, websocket in self.active_connections[document_id].items():
            if exclude_user and user_id == exclude_user:
                continue
            
            try:
                await websocket.send_text(message_json)
            except:
                disconnected_users.append(user_id)
        
        # Удаляем отключенных пользователей
        for user_id in disconnected_users:
            self.disconnect(document_id, user_id)

    async def handle_operation(self, document_id: str, user_id: str, operation: dict):
        """Обработка операции редактирования"""
        # Добавляем операцию в историю
        if document_id not in self.document_operations:
            self.document_operations[document_id] = []
        
        self.document_operations[document_id].append(operation)
        
        # Рассылаем операцию другим пользователям
        await self.broadcast_to_document(document_id, {
            "type": "operation",
            "data": operation
        }, exclude_user=user_id)
        
        logger.info(f"Operation from {user_id} broadcasted to document {document_id}")

    def get_document_state(self, document_id: str) -> dict:
        """Получение текущего состояния документа"""
        if document_id not in self.document_operations:
            return {"content": "", "version": 0}
        
        # Для простоты, возвращаем последнюю операцию замены или пустое состояние
        operations = self.document_operations[document_id]
        for op in reversed(operations):
            if op.get("type") == "replace":
                return {"content": op.get("content", ""), "version": op.get("version", 0)}
        
        return {"content": "", "version": 0}

manager = ConnectionManager()

@router.websocket("/collaboration/documents/{document_id}/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, document_id: str, user_id: str):
    """WebSocket эндпоинт для совместного редактирования"""
    await manager.connect(websocket, document_id, user_id)
    
    try:
        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "operation":
                # Обработка операции редактирования
                operation = message.get("data")
                operation["user_id"] = user_id
                operation["timestamp"] = asyncio.get_event_loop().time()
                
                await manager.handle_operation(document_id, user_id, operation)
                
            elif message_type == "cursor":
                # Обработка движения курсора
                cursor_data = message.get("data")
                cursor_data["user_id"] = user_id
                
                await manager.broadcast_to_document(document_id, {
                    "type": "cursor",
                    "data": cursor_data
                }, exclude_user=user_id)
                
            elif message_type == "ping":
                # Ответ на ping для поддержания соединения
                await websocket.send_text(json.dumps({"type": "pong"}))
                
            elif message_type == "sync_request":
                # Запрос синхронизации состояния документа
                state = manager.get_document_state(document_id)
                await websocket.send_text(json.dumps({
                    "type": "sync_response",
                    "data": state
                }))
                logger.info(f"Sent sync response to user {user_id} for document {document_id}")
                
    except WebSocketDisconnect:
        manager.disconnect(document_id, user_id)
        # Уведомляем других пользователей об отключении
        await manager.broadcast_to_document(document_id, {
            "type": "user_left",
            "data": {
                "user_id": user_id,
                "active_users": list(manager.active_connections.get(document_id, {}).keys())
            }
        })
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(document_id, user_id)
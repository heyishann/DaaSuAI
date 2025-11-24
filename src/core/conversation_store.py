"""ConversationStore - Persists and retrieves chat context for sessions."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from datetime import datetime


class ConversationStore:
    """Lightweight persistence layer for conversational context."""

    def __init__(self, db_client, table_name: str = "conversation_history"):
        self.db_client = db_client
        self.table_name = table_name
        self._table_ready = False
        self._fallback_memory: Dict[str, Dict[str, Any]] = {}

    async def save_entry(
        self,
        session_id: Optional[str],
        user_query: str,
        final_result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist the latest interaction for a session."""
        if not session_id:
            return

        response_payload = final_result.get("answer")
        if response_payload is None and final_result.get("response_type") == "database_query":
            response_payload = final_result.get("data")

        if isinstance(response_payload, (dict, list)):
            try:
                response_payload = json.dumps(response_payload)
            except (TypeError, ValueError):
                response_payload = str(response_payload)

        payload = {
            "session_id": session_id,
            "user_query": user_query,
            "response_type": final_result.get("response_type", "unknown"),
            "response_text": response_payload,
            "sql_query": final_result.get("sql_query"),
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }

        if await self._can_use_database():
            await self._ensure_table()
            json_metadata = json.dumps(payload["metadata"]) if payload["metadata"] else None
            sql = f"""
                INSERT INTO {self.table_name}
                (session_id, user_query, response_type, response_text, sql_query, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (
                payload["session_id"],
                payload["user_query"],
                payload["response_type"],
                payload["response_text"],
                payload["sql_query"],
                json_metadata,
            )
            await self.db_client.execute_write(sql, params)
        else:
            self._fallback_memory[session_id] = payload

    async def fetch_last_entry(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Return the latest stored exchange for a session."""
        if not session_id:
            return None

        if await self._can_use_database():
            await self._ensure_table()
            sql = f"""
                SELECT session_id, user_query, response_type, response_text, sql_query, metadata, created_at
                FROM {self.table_name}
                WHERE session_id = %s
                ORDER BY id DESC
                LIMIT 1
            """
            row = await self.db_client.fetch_one(sql, (session_id,))
            if row:
                metadata = row.get("metadata")
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = {"raw": metadata}
                return {
                    "session_id": row.get("session_id"),
                    "user_query": row.get("user_query"),
                    "response_type": row.get("response_type"),
                    "response_text": row.get("response_text"),
                    "sql_query": row.get("sql_query"),
                    "metadata": metadata or {},
                    "created_at": row.get("created_at"),
                }

        return self._fallback_memory.get(session_id)

    async def _ensure_table(self) -> None:
        """Create persistence table if it does not yet exist."""
        if self._table_ready or not await self._can_use_database():
            return

        sql = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(128) NOT NULL,
                user_query JSON NULL,
                response_type JSON NULL,
                response_text JSON NULL,
                sql_query JSON NULL,
                metadata JSON NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_session_id_created_at (session_id, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        await self.db_client.execute_write(sql)
        self._table_ready = True

    async def _can_use_database(self) -> bool:
        """Quickly determine if we can talk to the database."""
        return bool(self.db_client and self.db_client.connected and self.db_client.pool)


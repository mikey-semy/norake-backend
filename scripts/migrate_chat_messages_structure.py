"""
Скрипт для миграции структуры сообщений в ai_chats.

Преобразует старую структуру:
{
    "role": "...",
    "content": "...",
    "metadata": {"timestamp": "...", "model": "...", ...}
}

В новую структуру:
{
    "role": "...",
    "content": "...",
    "message_metadata": {"model": "...", ...},
    "timestamp": "..."
}

Запуск:
    uv run python scripts/migrate_chat_messages_structure.py
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.settings.base import settings
from src.models.v1.ai_chats import AIChatModel


async def migrate_messages():
    """Мигрирует структуру сообщений во всех чатах."""
    engine = create_async_engine(settings.database_url, echo=True)

    async with engine.begin() as conn:
        # Получаем все чаты с сообщениями
        result = await conn.execute(
            select(AIChatModel.id, AIChatModel.chat_id, AIChatModel.messages).where(
                text("jsonb_array_length(messages) > 0")
            )
        )
        chats = result.fetchall()

        print(f"\n🔄 Найдено {len(chats)} чатов с сообщениями")

        migrated_count = 0
        skipped_count = 0

        for chat_row in chats:
            chat_id = chat_row[0]
            readable_id = chat_row[1]
            messages = chat_row[2]

            new_messages = []
            needs_migration = False

            for msg in messages:
                # Проверяем формат сообщения
                if "metadata" in msg and "timestamp" not in msg:
                    # Старый формат - нужна миграция
                    needs_migration = True
                    metadata = msg.get("metadata", {})
                    timestamp = metadata.pop("timestamp", None)

                    new_msg = {
                        "role": msg["role"],
                        "content": msg["content"],
                        "message_metadata": metadata,
                        "timestamp": timestamp or "",
                    }
                    new_messages.append(new_msg)
                    print(
                        f"  ✅ Мигрировано сообщение в чате {readable_id}: {msg['role']}"
                    )

                elif "message_metadata" in msg and "timestamp" in msg:
                    # Новый формат - оставляем как есть
                    new_messages.append(msg)

                else:
                    # Неизвестный формат - пытаемся добавить недостающие поля
                    print(f"  ⚠️ Неизвестный формат в чате {readable_id}: {msg}")
                    new_msg = {
                        "role": msg.get("role", "unknown"),
                        "content": msg.get("content", ""),
                        "message_metadata": {},
                        "timestamp": "",
                    }
                    new_messages.append(new_msg)
                    needs_migration = True

            if needs_migration:
                # Обновляем messages в БД
                await conn.execute(
                    text(
                        "UPDATE ai_chats SET messages = :messages::jsonb WHERE id = :chat_id"
                    ),
                    {"messages": new_messages, "chat_id": chat_id},
                )
                migrated_count += 1
                print(f"  💾 Обновлён чат {readable_id}")
            else:
                skipped_count += 1

        print(f"\n✅ Миграция завершена:")
        print(f"   - Мигрировано чатов: {migrated_count}")
        print(f"   - Пропущено (уже новый формат): {skipped_count}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate_messages())

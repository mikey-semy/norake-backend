#!/usr/bin/env python3
"""
Скрипт для создания Developer Issue Template через NoRake Backend API.

Использование:
    python create_developer_template.py --workspace-id UUID --username admin --password pass

Requirements:
    pip install httpx rich
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

try:
    import httpx
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("❌ Требуется установить зависимости: pip install httpx rich")
    sys.exit(1)

console = Console()


def login(base_url: str, username: str, password: str) -> Optional[str]:
    """Авторизация и получение JWT токена."""
    console.print(f"[cyan]Логин в {base_url}...[/cyan]")
    
    try:
        response = httpx.post(
            f"{base_url}/api/v1/auth/login",
            data={"username": username, "password": password},
            timeout=10.0
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        console.print("[green]✅ Авторизация успешна[/green]")
        return token
    except httpx.HTTPStatusError as e:
        console.print(f"[red]❌ Ошибка авторизации: {e.response.status_code}[/red]")
        console.print(f"[red]   {e.response.text}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]❌ Ошибка: {e}[/red]")
        return None


def load_template_data(json_path: Path) -> Optional[Dict]:
    """Загрузка JSON-шаблона из файла."""
    console.print(f"[cyan]Загрузка шаблона из {json_path}...[/cyan]")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        console.print(f"[green]✅ Шаблон загружен: {data['template_name']}[/green]")
        console.print(f"   Категория: {data['category']}")
        console.print(f"   Полей: {len(data['fields'])}")
        return data
    except FileNotFoundError:
        console.print(f"[red]❌ Файл не найден: {json_path}[/red]")
        return None
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Ошибка парсинга JSON: {e}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]❌ Ошибка: {e}[/red]")
        return None


def create_template(
    base_url: str,
    workspace_id: str,
    token: str,
    template_data: Dict
) -> Optional[Dict]:
    """Создание шаблона через API."""
    console.print(f"[cyan]Создание шаблона для workspace {workspace_id}...[/cyan]")
    
    try:
        response = httpx.post(
            f"{base_url}/api/v1/templates/{workspace_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=template_data,
            timeout=30.0
        )
        response.raise_for_status()
        result = response.json()
        console.print("[green]✅ Шаблон создан успешно![/green]")
        return result["data"]
    except httpx.HTTPStatusError as e:
        console.print(f"[red]❌ Ошибка создания: {e.response.status_code}[/red]")
        console.print(f"[red]   {e.response.text}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]❌ Ошибка: {e}[/red]")
        return None


def display_template_info(template: Dict):
    """Отображение информации о созданном шаблоне."""
    table = Table(title="Созданный шаблон", show_header=True, header_style="bold magenta")
    table.add_column("Параметр", style="cyan", width=20)
    table.add_column("Значение", style="green")
    
    table.add_row("ID", template["id"])
    table.add_row("Название", template["template_name"])
    table.add_row("Категория", template["category"])
    table.add_row("Видимость", template["visibility"])
    table.add_row("Активен", "✅ Да" if template["is_active"] else "❌ Нет")
    table.add_row("Использований", str(template["usage_count"]))
    table.add_row("Полей", str(len(template["fields"])))
    
    console.print(table)
    
    # Таблица полей
    fields_table = Table(title="Поля шаблона", show_header=True, header_style="bold cyan")
    fields_table.add_column("#", justify="right", width=3)
    fields_table.add_column("Field Name", style="yellow", width=25)
    fields_table.add_column("Type", style="blue", width=12)
    fields_table.add_column("Required", justify="center", width=10)
    
    for i, field in enumerate(template["fields"], 1):
        required = "✅" if field.get("validation_rules", {}).get("required") else "❌"
        fields_table.add_row(
            str(i),
            field["field_name"],
            field["field_type"],
            required
        )
    
    console.print(fields_table)


def main():
    parser = argparse.ArgumentParser(
        description="Создать Developer Issue Template через NoRake API"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL NoRake Backend (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="UUID workspace для создания шаблона"
    )
    parser.add_argument(
        "--username",
        required=True,
        help="Имя пользователя для авторизации"
    )
    parser.add_argument(
        "--password",
        required=True,
        help="Пароль пользователя"
    )
    parser.add_argument(
        "--template-json",
        default="developer-issue-template.json",
        help="Путь к JSON файлу шаблона (default: developer-issue-template.json)"
    )
    
    args = parser.parse_args()
    
    console.print("[bold cyan]NoRake: Developer Issue Template Creator[/bold cyan]")
    console.print("=" * 60)
    
    # 1. Авторизация
    token = login(args.base_url, args.username, args.password)
    if not token:
        sys.exit(1)
    
    # 2. Загрузка шаблона
    template_path = Path(__file__).parent / args.template_json
    template_data = load_template_data(template_path)
    if not template_data:
        sys.exit(1)
    
    # 3. Создание шаблона
    created_template = create_template(
        args.base_url,
        args.workspace_id,
        token,
        template_data
    )
    if not created_template:
        sys.exit(1)
    
    # 4. Отображение результата
    console.print()
    display_template_info(created_template)
    
    # 5. Инструкции по использованию
    console.print()
    console.print("[bold green]🎉 Шаблон готов к использованию![/bold green]")
    console.print()
    console.print("[cyan]Как использовать:[/cyan]")
    console.print(f"1. Создайте Issue через API с template_id: {created_template['id']}")
    console.print("2. Заполните поля template_data согласно структуре")
    console.print("3. Issue автоматически категоризируется через n8n workflow")
    console.print()
    console.print("[cyan]Пример curl:[/cyan]")
    console.print(f"""
curl -X POST {args.base_url}/api/v1/issues \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "workspace_id": "{args.workspace_id}",
    "title": "FastAPI OAuth2 возвращает 401",
    "description": "Проблема с авторизацией",
    "category": "software",
    "template_id": "{created_template['id']}",
    "template_data": {{
      "goal": "Интегрировать OAuth2 через Google",
      "current_behavior": "Возвращается HTTP 401",
      "code_example": "```python\\nfrom fastapi import FastAPI\\n...```",
      "environment": "Python 3.11.5, FastAPI 0.104.1",
      "attempts": "Читал документацию, пробовал изменить URL",
      "checklist": ["Попытался решить сам", "Код минимизирован", ...]
    }}
  }}'
    """)


if __name__ == "__main__":
    main()

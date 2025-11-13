#!/usr/bin/env python3
"""
Скрипт для создания обоих шаблонов через NoRake Backend API:
- Developer Issue Template (Программирование)
- Drive Engineer Template (Приводчики)

Использование:
    python create_templates.py --workspace-id UUID --username admin --password pass

Requirements:
    pip install httpx rich
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    import httpx
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
except ImportError:
    print("❌ Требуется установить зависимости: pip install httpx rich")
    sys.exit(1)

console = Console()


def login(base_url: str, username: str, password: str) -> Optional[str]:
    """Авторизация и получение JWT токена."""
    console.print(f"[cyan]🔐 Логин в {base_url}...[/cyan]")
    
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
    console.print(f"[cyan]📄 Загрузка шаблона из {json_path.name}...[/cyan]")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        console.print(f"[green]   ✓ {data['template_name']}[/green]")
        console.print(f"   📂 Категория: {data['category']}")
        console.print(f"   📊 Полей: {len(data['fields'])}")
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
    template_name = template_data["template_name"]
    console.print(f"\n[cyan]🚀 Создание шаблона: {template_name}[/cyan]")
    
    try:
        response = httpx.post(
            f"{base_url}/api/v1/templates/{workspace_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=template_data,
            timeout=30.0
        )
        response.raise_for_status()
        result = response.json()
        
        template_id = result["data"]["id"]
        usage_count = result["data"]["usage_count"]
        
        console.print(f"[green]✅ Шаблон создан успешно![/green]")
        console.print(f"   🆔 ID: {template_id}")
        console.print(f"   📈 Использований: {usage_count}")
        
        return result["data"]
    except httpx.HTTPStatusError as e:
        console.print(f"[red]❌ Ошибка создания: {e.response.status_code}[/red]")
        console.print(f"[red]   {e.response.text}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]❌ Ошибка: {e}[/red]")
        return None


def display_summary(templates: List[Dict]):
    """Отображение итоговой таблицы созданных шаблонов."""
    table = Table(title="\n✨ Созданные шаблоны", title_style="bold green")
    
    table.add_column("Название", style="cyan", no_wrap=False)
    table.add_column("Категория", style="magenta")
    table.add_column("Полей", justify="center", style="yellow")
    table.add_column("ID", style="blue")
    
    for t in templates:
        table.add_row(
            t["template_name"],
            t["category"],
            str(len(t["fields"])),
            t["id"][:8] + "..."
        )
    
    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Создание шаблонов для NoRake Backend"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="UUID рабочего пространства (workspace ID)"
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
        "--templates-dir",
        default=".",
        help="Каталог с JSON-шаблонами (default: текущий)"
    )
    
    args = parser.parse_args()
    
    # Заголовок
    console.print(Panel.fit(
        "[bold cyan]NoRake Templates Creator[/bold cyan]\n"
        "[dim]Создание шаблонов для Issues[/dim]",
        border_style="cyan"
    ))
    
    # Авторизация
    token = login(args.base_url, args.username, args.password)
    if not token:
        sys.exit(1)
    
    templates_dir = Path(args.templates_dir)
    template_files = [
        templates_dir / "developer-issue-template.json",
        templates_dir / "drive-engineer-template.json"
    ]
    
    created_templates = []
    
    # Создание шаблонов
    console.print("\n[bold]📦 Загрузка и создание шаблонов...[/bold]")
    
    for template_file in template_files:
        # Загрузка JSON
        template_data = load_template_data(template_file)
        if not template_data:
            console.print(f"[yellow]⚠️  Пропускаем {template_file.name}[/yellow]")
            continue
        
        # Создание через API
        created = create_template(
            args.base_url,
            args.workspace_id,
            token,
            template_data
        )
        
        if created:
            created_templates.append(created)
    
    # Итоговая сводка
    if created_templates:
        display_summary(created_templates)
        console.print("\n[bold green]🎉 Все шаблоны успешно созданы![/bold green]")
        console.print("\n[dim]Используйте их при создании Issues через API или UI[/dim]")
    else:
        console.print("\n[bold red]❌ Не удалось создать ни одного шаблона[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

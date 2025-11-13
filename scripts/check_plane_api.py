#!/usr/bin/env python3
"""
Скрипт для проверки подключения к Plane API.

Использование:
    python scripts/check_plane_api.py

Требуется:
    - PLANE_API_KEY в переменных окружения
    - requests библиотека (pip install requests)
"""

import os
import sys
from typing import Optional

try:
    import requests
except ImportError:
    print("❌ Требуется установить библиотеку requests: pip install requests")
    sys.exit(1)


class PlaneAPIChecker:
    """Класс для проверки работоспособности Plane API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        host_url: str = "https://plane.equiply.ru",
        workspace_slug: str = "projects",
    ):
        """
        Инициализация проверки Plane API.

        Args:
            api_key: API ключ Plane (если None, берется из PLANE_API_KEY env)
            host_url: URL Plane инстанса
            workspace_slug: Slug workspace
        """
        self.api_key = api_key or os.getenv("PLANE_API_KEY")
        self.host_url = host_url.rstrip("/")
        self.workspace_slug = workspace_slug
        self.base_url = f"{self.host_url}/api/v1"

        if not self.api_key:
            print("⚠️  PLANE_API_KEY не установлен в переменных окружения")
            print("   Попытка проверить публичный доступ...")

    @property
    def headers(self) -> dict:
        """Возвращает заголовки для HTTP запросов."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    def check_connection(self) -> bool:
        """
        Проверка базового подключения к Plane API.

        Returns:
            True если подключение успешно, False иначе
        """
        print(f"\n🔍 Проверка подключения к {self.host_url}...")

        try:
            response = requests.get(
                f"{self.base_url}/",
                headers=self.headers,
                timeout=10,
            )
            print(f"   Статус: {response.status_code}")

            if response.status_code == 200:
                print("   ✅ Базовое подключение успешно")
                return True
            elif response.status_code == 401:
                print("   ⚠️  Требуется авторизация (401)")
                return False
            else:
                print(f"   ❌ Неожиданный статус: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"   ❌ Ошибка подключения: {e}")
            return False

    def check_workspace(self) -> bool:
        """
        Проверка доступа к workspace.

        Returns:
            True если workspace доступен, False иначе
        """
        print(f"\n🔍 Проверка workspace '{self.workspace_slug}'...")

        try:
            response = requests.get(
                f"{self.base_url}/workspaces/{self.workspace_slug}/",
                headers=self.headers,
                timeout=10,
            )
            print(f"   Статус: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Workspace найден: {data.get('name', 'N/A')}")
                print(f"      ID: {data.get('id', 'N/A')}")
                return True
            elif response.status_code == 401:
                print("   ⚠️  Требуется API ключ для доступа")
                return False
            elif response.status_code == 404:
                print("   ❌ Workspace не найден")
                return False
            else:
                print(f"   ❌ Неожиданный статус: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"   ❌ Ошибка запроса: {e}")
            return False

    def list_projects(self) -> bool:
        """
        Получение списка проектов в workspace.

        Returns:
            True если проекты получены, False иначе
        """
        print(f"\n🔍 Получение списка проектов в workspace '{self.workspace_slug}'...")

        try:
            response = requests.get(
                f"{self.base_url}/workspaces/{self.workspace_slug}/projects/",
                headers=self.headers,
                timeout=10,
            )
            print(f"   Статус: {response.status_code}")

            if response.status_code == 200:
                projects = response.json()
                print(f"   ✅ Найдено проектов: {len(projects)}")

                for project in projects[:5]:  # Показываем первые 5
                    print(f"      - {project.get('name')} ({project.get('identifier')})")
                    print(f"        ID: {project.get('id')}")

                return True
            elif response.status_code == 401:
                print("   ⚠️  Требуется API ключ")
                return False
            else:
                print(f"   ❌ Неожиданный статус: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"   ❌ Ошибка запроса: {e}")
            return False

    def check_project(self, project_id: str) -> bool:
        """
        Проверка доступа к конкретному проекту.

        Args:
            project_id: UUID проекта

        Returns:
            True если проект доступен, False иначе
        """
        print(f"\n🔍 Проверка проекта {project_id}...")

        try:
            response = requests.get(
                f"{self.base_url}/workspaces/{self.workspace_slug}/projects/{project_id}/",
                headers=self.headers,
                timeout=10,
            )
            print(f"   Статус: {response.status_code}")

            if response.status_code == 200:
                project = response.json()
                print(f"   ✅ Проект найден: {project.get('name')}")
                print(f"      Identifier: {project.get('identifier')}")
                print(f"      Description: {project.get('description', 'N/A')[:100]}")
                return True
            elif response.status_code == 401:
                print("   ⚠️  Требуется API ключ")
                return False
            elif response.status_code == 404:
                print("   ❌ Проект не найден")
                return False
            else:
                print(f"   ❌ Неожиданный статус: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"   ❌ Ошибка запроса: {e}")
            return False

    def list_project_states(self, project_id: str) -> bool:
        """
        Получение списка статусов проекта.

        Args:
            project_id: UUID проекта

        Returns:
            True если статусы получены, False иначе
        """
        print(f"\n🔍 Получение статусов проекта {project_id}...")

        try:
            response = requests.get(
                f"{self.base_url}/workspaces/{self.workspace_slug}/projects/{project_id}/states/",
                headers=self.headers,
                timeout=10,
            )
            print(f"   Статус: {response.status_code}")

            if response.status_code == 200:
                states = response.json()
                print(f"   ✅ Найдено статусов: {len(states)}")

                for state in states:
                    print(f"      - {state.get('name')}: {state.get('id')}")

                return True
            elif response.status_code == 401:
                print("   ⚠️  Требуется API ключ")
                return False
            else:
                print(f"   ❌ Неожиданный статус: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"   ❌ Ошибка запроса: {e}")
            return False

    def run_full_check(self, project_id: Optional[str] = None) -> dict:
        """
        Запуск полной проверки Plane API.

        Args:
            project_id: UUID проекта для детальной проверки

        Returns:
            Словарь с результатами проверки
        """
        print("=" * 60)
        print("🚀 ПРОВЕРКА PLANE API")
        print("=" * 60)
        print(f"Host: {self.host_url}")
        print(f"Workspace: {self.workspace_slug}")
        print(f"API Key: {'✅ Установлен' if self.api_key else '❌ Не установлен'}")

        results = {
            "connection": self.check_connection(),
            "workspace": self.check_workspace(),
            "projects": self.list_projects(),
        }

        if project_id:
            results["project"] = self.check_project(project_id)
            results["states"] = self.list_project_states(project_id)

        print("\n" + "=" * 60)
        print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
        print("=" * 60)

        for check, result in results.items():
            status = "✅ Успешно" if result else "❌ Не удалось"
            print(f"{check.capitalize()}: {status}")

        all_passed = all(results.values())
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 Все проверки пройдены успешно!")
        else:
            print("⚠️  Некоторые проверки не прошли.")
            if not self.api_key:
                print("\n💡 Совет: Установите PLANE_API_KEY для полного доступа")
        print("=" * 60)

        return results


def main():
    """Главная функция скрипта."""
    # Конфигурация из copilot-instructions.md
    PROJECT_ID = "c4ea1c3f-97d2-4f56-8aaa-5cce4b185f58"
    WORKSPACE_SLUG = "projects"  # Из copilot-instructions.md
    HOST_URL = "https://plane.equiply.ru"

    checker = PlaneAPIChecker(
        host_url=HOST_URL,
        workspace_slug=WORKSPACE_SLUG,
    )

    # Запуск полной проверки
    checker.run_full_check(project_id=PROJECT_ID)


if __name__ == "__main__":
    main()

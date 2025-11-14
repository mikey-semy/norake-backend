"""Тест API document-services с параметром tags."""

import requests

# Тест 1: Запрос с пустыми тегами
print("=== Тест 1: Запрос БЕЗ тегов ===")
response = requests.get("http://localhost:8003/api/v1/document-services")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

# Тест 2: Запрос с тегом "test"
print("=== Тест 2: Запрос с тегом 'test' ===")
response = requests.get("http://localhost:8003/api/v1/document-services?tags=test")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

# Тест 3: Запрос с кириллическим тегом
print("=== Тест 3: Запрос с тегом 'Параметрирование' ===")
response = requests.get("http://localhost:8003/api/v1/document-services", params={"tags": "Параметрирование"})
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

# Тест 4: Запрос с несколькими тегами
print("=== Тест 4: Запрос с тегами 'test,demo' ===")
response = requests.get("http://localhost:8003/api/v1/document-services?tags=test,demo")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

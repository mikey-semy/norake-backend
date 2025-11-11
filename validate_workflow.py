"""Валидация n8n workflow JSON."""
import json
from pathlib import Path

workflow_path = Path("docs/n8n_workflows/auto-categorize-issues.json")

try:
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)
    
    print("✅ Workflow JSON валиден!")
    print(f"📋 Имя: {workflow.get('name')}")
    print(f"🔧 Nodes: {len(workflow.get('nodes', []))}")
    print(f"🔗 Connections: {len(workflow.get('connections', {}))}")
    print("\n📝 Node types:")
    for node in workflow.get("nodes", []):
        print(f"  - {node['name']}: {node['type']}")
    
    print("\n🔗 Connections:")
    for src, targets in workflow.get("connections", {}).items():
        print(f"  {src} →", end=" ")
        for target_list in targets.get("main", []):
            for target in target_list:
                print(target["node"], end=" ")
        print()
    
    # Проверка критичных параметров
    print("\n🔍 Проверка критичных параметров:")
    
    # Webhook node
    webhook_node = next((n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.webhook"), None)
    if webhook_node:
        print(f"  ✅ Webhook: path={webhook_node['parameters'].get('path')}, responseMode={webhook_node['parameters'].get('responseMode')}")
    
    # HTTP Request nodes
    http_nodes = [n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.httpRequest"]
    for http_node in http_nodes:
        auth = http_node["parameters"].get("authentication", "none")
        print(f"  ✅ {http_node['name']}: method={http_node['parameters'].get('method')}, auth={auth}")
    
    # Set nodes
    set_nodes = [n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.set"]
    for set_node in set_nodes:
        values = set_node["parameters"].get("values", {})
        print(f"  ✅ {set_node['name']}: values={list(values.keys())}")
    
    print("\n🎉 Все проверки пройдены!")
    
except json.JSONDecodeError as e:
    print(f"❌ Ошибка парсинга JSON: {e}")
except Exception as e:
    print(f"❌ Ошибка: {e}")

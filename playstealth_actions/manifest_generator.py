import json
import os
import importlib.metadata
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from .plugins.loader import load_plugins

MANIFEST_PATH = Path(os.getenv("PLAYSTEALTH_MANIFEST_PATH", ".playstealth_manifest.json"))


def _get_cli_version() -> str:
    try:
        return importlib.metadata.version("playstealth-cli")
    except Exception:
        return "dev"


def _load_tool_registry() -> Dict[str, Any]:
    """Lädt dynamisch die Tool-Registry, falls vorhanden."""
    try:
        from .tool_registry import list_all_tools
        categories = list_all_tools()
        total = sum(len(tools) for tools in categories.values())
        all_names = []
        for cat, names in categories.items():
            all_names.extend(names)
        return {"count": total, "names": all_names, "by_category": categories}
    except ImportError as e:
        print(f"Warning: Could not load tool registry: {e}")
        pass
    return {"count": 0, "names": []}


async def generate_enhanced_manifest(stealth_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    plugins = load_plugins()
    plugin_meta = []
    for p in plugins:
        plugin_meta.append({
            "name": p.__name__,
            "module": p.__module__,
            "doc": (p.__doc__ or "").strip().split("\n")[0],
            "capabilities": [m for m in dir(p) if not m.startswith("_") and callable(getattr(p, m))]
        })

    tools = _load_tool_registry()
    
    manifest = {
        "cli": {
            "name": "playstealth-cli",
            "version": _get_cli_version(),
            "generated_at": datetime.now().isoformat(),
            "architecture": "modular_plugin_based"
        },
        "plugins": {
            "count": len(plugins),
            "loaded": plugin_meta
        },
        "stealth": stealth_data or {"status": "not_benchmarked", "score": "0/8", "percentage": 0.0},
        "tools": tools,
        "config": {
            "state_dir": os.getenv("PLAYSTEALTH_STATE_DIR", ".playstealth_state"),
            "headless_default": os.getenv("PLAYSTEALTH_HEADLESS", "false"),
            "proxy_pool_enabled": os.getenv("PLAYSTEALTH_PROXY_POOL", "false"),
            "manifest_path": str(MANIFEST_PATH)
        }
    }
    return manifest


async def save_manifest(stealth_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = await generate_enhanced_manifest(stealth_data)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def load_manifest() -> Dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {}
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def print_manifest_cli(data: Dict[str, Any]):
    """Pretty-Print für Terminal-Output"""
    print("\n📜 PlayStealth Manifest")
    print(f"   CLI Version : {data.get('cli', {}).get('version', '?')}")
    print(f"   Generated   : {data.get('cli', {}).get('generated_at', '?')}")
    print(f"   Plugins     : {data.get('plugins', {}).get('count', 0)} loaded")
    for p in data.get('plugins', {}).get('loaded', []):
        print(f"      • {p['name']} ({p['module']})")
    s = data.get('stealth', {})
    print(f"   Stealth     : {s.get('score', '?')} ({s.get('percentage', 0)}%)")
    if s.get('warnings'):
        print(f"      ⚠️  {', '.join(s['warnings'])}")
    t = data.get('tools', {})
    print(f"   Tools       : {t.get('count', 0)} registered")
    print(f"   State Dir   : {data.get('config', {}).get('state_dir', '?')}")
    print(f"   Manifest    : {data.get('config', {}).get('manifest_path', '?')}\n")

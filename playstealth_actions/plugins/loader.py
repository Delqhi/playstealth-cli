import importlib
import pkgutil
from pathlib import Path
from typing import List, Type
from .base_platform import BasePlatform


def load_plugins() -> List[Type[BasePlatform]]:
    """Lädt alle Platform-Plugins dynamisch aus dem plugins/-Verzeichnis."""
    plugins = []
    plugin_dir = Path(__file__).parent
    for _, module_name, _ in pkgutil.iter_modules([str(plugin_dir)]):
        if module_name.startswith("_") or module_name in ("base_platform", "loader"):
            continue
        try:
            mod = importlib.import_module(f".{module_name}", package=__package__)
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, BasePlatform) and attr is not BasePlatform:
                    plugins.append(attr)
        except Exception as e:
            print(f"⚠️ Plugin load warning ({module_name}): {e}")
    return plugins


async def detect_platform(page, plugins: List[Type[BasePlatform]]) -> BasePlatform:
    """Führt detect() auf allen Plugins aus und gibt das erste Match zurück."""
    for plugin_cls in plugins:
        instance = plugin_cls()
        if await instance.detect(page):
            return instance
    raise ValueError("🔍 No matching survey platform detected. Add a plugin or check URL/DOM.")

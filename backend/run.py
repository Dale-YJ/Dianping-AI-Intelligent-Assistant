"""Backend entry point - uses module manager for flexible module execution."""
import sys
import types
from pathlib import Path

# Add backend to path
BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Also add parent directory for 'backend.app.*' imports
BACKEND_PARENT = BACKEND_ROOT.parent
if str(BACKEND_PARENT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PARENT))

# Create 'backend' module stub to support 'from backend.app.*' imports
# This allows code that imports from backend.app to work without modification
if 'backend' not in sys.modules:
    backend_module = types.ModuleType('backend')
    backend_module.__path__ = [str(BACKEND_ROOT)]
    backend_module.__file__ = str(BACKEND_ROOT / '__init__.py')
    sys.modules['backend'] = backend_module

# Import module manager and run
from module_manager import main

if __name__ == "__main__":
    main()
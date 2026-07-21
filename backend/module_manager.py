"""Module Manager - Central registry for all backend modules.

This module provides a unified way to manage and run different backend modules.
Each module can be run independently or together as a unified application.

Usage:
    # Run specific module
    python run.py --module analysis
    python run.py --module chat

    # Run all modules
    python run.py --all

    # List available modules
    python run.py --list
"""
import argparse
import importlib
import sys
from pathlib import Path

# ── Path Setup ───────────────────────────────────────────────────

# Add backend root to sys.path for 'backend.app.*' imports
BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Also add parent directory for 'app.*' imports
BACKEND_PARENT = BACKEND_ROOT.parent
if str(BACKEND_PARENT) not in sys.path:
    sys.path.insert(0, str(BACKEND_PARENT))

# Add base_config for shared modules (opensearch_client, retrieve, etc.)
BASE_CONFIG = BACKEND_PARENT / "base_config"
if str(BASE_CONFIG) not in sys.path:
    sys.path.insert(0, str(BASE_CONFIG))

import logging
import traceback
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ModuleInfo:
    """Module information container."""
    def __init__(
        self,
        name: str,
        description: str,
        module_path: str,
        app_variable: str = "app",
        port: Optional[int] = None
    ):
        self.name = name
        self.description = description
        self.module_path = module_path
        self.app_variable = app_variable
        self.port = port or 8000


class ModuleManager:
    """Central module registry and manager."""

    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}
        self._register_default_modules()

    def _register_default_modules(self):
        """Register default backend modules."""
        # Analysis module - Review sentiment analysis
        self.register(
            ModuleInfo(
                name="analysis",
                description="评价分析模块 - 口碑摘要、情感分析、特征提取",
                module_path="app.modules.analysis.main",  # Current main.py
                app_variable="app",
                port=8000
            )
        )

        # Chat module - Conversational shop recommendation (future)
        self.register(
            ModuleInfo(
                name="chat",
                description="探店对话模块 - 智能推荐、对话式交互",
                module_path="app.modules.chat.main",
                app_variable="app",
                port=8001
            )
        )

        # Reputation module - Business reputation analysis
        self.register(
            ModuleInfo(
                name="reputation",
                description="商家口碑分析模块 - 关键特征词提取、评价情感分析",
                module_path="app.modules.reputation.main",
                app_variable="app",
                port=8002
            )
        )

    def register(self, module: ModuleInfo):
        """Register a module."""
        self._modules[module.name] = module

    def get_module(self, name: str) -> Optional[ModuleInfo]:
        """Get module by name."""
        return self._modules.get(name)

    def list_modules(self) -> List[ModuleInfo]:
        """List all registered modules."""
        return list(self._modules.values())

    def get_app(self, module_name: str):
        """Get FastAPI app for a specific module."""
        module = self.get_module(module_name)
        if not module:
            raise ValueError(f"Module '{module_name}' not found")

        try:
            module_obj = importlib.import_module(module.module_path)
            return getattr(module_obj, module.app_variable)
        except Exception as e:
            logger.error("Failed to load module '%s': %s\n%s", module_name, e, traceback.format_exc())
            raise RuntimeError(f"Failed to load module '{module_name}': {e}") from e

    def create_unified_app(self):
        """Create a unified FastAPI app combining all modules."""
        from contextlib import asynccontextmanager
        from pathlib import Path
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware

        # Import settings from base_config
        from app.core.config import settings, PROJECT_ROOT

        @asynccontextmanager
        async def unified_lifespan(app: FastAPI):
            """Compose startup checks from all three modules."""
            # ── Analysis module startup ──
            try:
                from app.services.analysis_services.review_service import ensure_user_review_index
                if ensure_user_review_index():
                    print("  [analysis] User review index ready")
                else:
                    print("  [analysis] WARNING: User review index not ready")
            except Exception as e:
                print(f"  [analysis] User review index check failed: {e}")

            try:
                from app.services.analysis_services.retrieval import get_all_businesses
                businesses = get_all_businesses()
                print(f"  [analysis] Data loaded: {len(businesses)} businesses")
            except Exception as e:
                print(f"  [analysis] Data loading failed: {e}")

            # ── Chat module startup ──
            try:
                sys.path.insert(0, str(PROJECT_ROOT / "base_config"))
                from retrieve import embed_query
                embed_query("")
                print("  [chat] Embedding model preloaded")
            except Exception as e:
                print(f"  [chat] Embedding model preload failed: {e}")

            # ── Reputation / shared: LLM connectivity ──
            try:
                from app.services.llm_client import get_llm
                llm = get_llm()
                model_name = getattr(llm, "model_name", "unknown")
                print(f"  [llm] LLM ready: {model_name}")
            except Exception as e:
                print(f"  [llm] LLM not ready: {e}")

            try:
                from base_config.opensearch_client import get_opensearch_client
                client = get_opensearch_client()
                count = client.count(index=settings.business_index)["count"]
                print(f"  [data] OpenSearch ready: {count} businesses")
            except Exception as e:
                print(f"  [data] OpenSearch check failed: {e}")

            yield

        # Create unified app
        app = FastAPI(
            title="大众点评 AI 智能助手 - 统一入口",
            description="集成所有模块的统一API网关",
            version="1.0.0",
            lifespan=unified_lifespan,
        )

        # Add CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Import and include routers from each module
        # Analysis module
        try:
            from app.api.analysis import router as analysis_router
            app.include_router(analysis_router)
            print(f"  [OK] Loaded module: analysis")
        except Exception as e:
            logger.error("Failed to load module '%s': %s\n%s", 'analysis', e, traceback.format_exc())
            print(f"  [FAIL] Failed to load module 'analysis': {e}")

        # Chat module
        try:
            from app.api.chat import router as chat_router
            app.include_router(chat_router)
            print(f"  [OK] Loaded module: chat")
        except Exception as e:
            logger.error("Failed to load module '%s': %s\n%s", 'chat', e, traceback.format_exc())
            print(f"  [FAIL] Failed to load module 'chat': {e}")

        # Reputation module
        try:
            from app.api.reputation import router as reputation_router
            app.include_router(reputation_router)
            print(f"  [OK] Loaded module: reputation")
        except Exception as e:
            logger.error("Failed to load module '%s': %s\n%s", 'reputation', e, traceback.format_exc())
            print(f"  [FAIL] Failed to load module 'reputation': {e}")

        # ── Static files ────────────────────────────────────────
        from pathlib import Path
        from fastapi.staticfiles import StaticFiles
        from app.core.config import PROJECT_ROOT

        static_dir = PROJECT_ROOT / "static"
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/")
        async def root():
            return {
                "service": "大众点评 AI 智能助手",
                "modules": [m.name for m in self.list_modules()],
                "docs": "/docs"
            }

        @app.get("/api/health")
        async def health():
            return {"status": "ok", "modules": len(self._modules)}

        return app


# Global manager instance
manager = ModuleManager()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Backend module manager")

    parser.add_argument(
        "--module",
        type=str,
        help="Run specific module (e.g., 'analysis', 'chat')"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all modules in unified app"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List available modules"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run on (default: 8000)"
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # List modules
    if args.list:
        print("\n可用的模块:")
        print("-" * 60)
        for module in manager.list_modules():
            print(f"  - {module.name:12s} - {module.description}")
            print(f"               路径: {module.module_path}")
            print(f"               端口: {module.port}")
        print()
        return

    # Run specific module
    if args.module:
        module = manager.get_module(args.module)
        if not module:
            print(f"错误: 模块 '{args.module}' 未找到")
            print("使用 --list 查看可用模块")
            return

        print(f"\n启动模块: {module.name}")
        print(f"描述: {module.description}")
        print(f"端口: {args.port}")

        import uvicorn
        app = manager.get_app(module.name)

        # Directly pass app object if not reloading
        if args.reload:
            # Use string path for reload mode
            uvicorn.run(
                module.module_path + ":app",
                host="0.0.0.0",
                port=args.port,
                reload=True
            )
        else:
            # Use app object for normal mode
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=args.port
            )
        return

    # Run all modules
    if args.all:
        print("\n启动所有模块（统一入口）")
        print(f"端口: {args.port}")

        import uvicorn
        app = manager.create_unified_app()

        # Directly pass app object if not reloading
        if args.reload:
            # For reload mode, we need to use a different approach
            # Save app to a separate module and use string reference
            import tempfile
            import os

            # Create temporary module with app reference
            temp_file = BACKEND_ROOT / "_unified_app.py"
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write("""
from module_manager import manager
app = manager.create_unified_app()
""")
            try:
                uvicorn.run(
                    "_unified_app:app",
                    host="0.0.0.0",
                    port=args.port,
                    reload=True
                )
            finally:
                # Clean up temporary file
                if temp_file.exists():
                    os.remove(temp_file)
        else:
            # Use app object for normal mode
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=args.port
            )
        return

    # No arguments - show help
    print("\n使用方法:")
    print("  python run.py --module <name>    运行指定模块")
    print("  python run.py --all              运行所有模块")
    print("  python run.py --list             列出可用模块")
    print("\n示例:")
    print("  python run.py --module analysis --port 8000")
    print("  python run.py --module chat --port 8001")
    print("  python run.py --all --port 8000 --reload")


if __name__ == "__main__":
    main()
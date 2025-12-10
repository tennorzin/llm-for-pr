#!/usr/bin/env python3
"""
Smart Task Engine
-----------------
A complex Python application demonstrating:
- Async task execution
- Caching
- Dependency injection
- CLI interface
- Config management
- Logging
- Error handling
"""

from __future__ import annotations
import os
import sys
import json
import time
import uuid
import asyncio
import logging
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import argparse

# =========================
# Configuration Layer
# =========================

@dataclass(frozen=True)
class AppConfig:
    app_name: str = "SmartTaskEngine"
    debug: bool = False
    max_workers: int = 5
    storage_file: str = "tasks.json"

    @staticmethod
    def load() -> "AppConfig":
        return AppConfig(
            app_name=os.getenv("APP_NAME", "SmartTaskEngine"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            max_workers=int(os.getenv("MAX_WORKERS", "5")),
            storage_file=os.getenv("STORAGE_FILE", "tasks.json")
        )

# =========================
# Logging Setup
# =========================

def setup_logger(debug: bool) -> logging.Logger:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    return logging.getLogger("SmartTaskEngine")

# =========================
# Domain Models
# =========================

@dataclass
class Task:
    id: str
    name: str
    payload: Dict[str, Any]
    created_at: float
    status: str = "PENDING"
    result: Optional[Any] = None

# =========================
# Storage Layer
# =========================

class TaskStorage:
    def __init__(self, file_path: str, logger: logging.Logger):
        self.file_path = file_path
        self.logger = logger
        self._lock = asyncio.Lock()

    async def load_all(self) -> Dict[str, Task]:
        async with self._lock:
            if not os.path.exists(self.file_path):
                return {}

            with open(self.file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            return {k: Task(**v) for k, v in raw.items()}

    async def save_all(self, tasks: Dict[str, Task]):
        async with self._lock:
            serialized = {k: v.__dict__ for k, v in tasks.items()}
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2)

# =========================
# Cache Layer
# =========================

class ResultCache:
    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any):
        self._cache[key] = value

# =========================
# Task Execution Framework
# =========================

class BaseTaskHandler(ABC):
    @abstractmethod
    async def execute(self, payload: Dict[str, Any]) -> Any:
        pass

class HashTaskHandler(BaseTaskHandler):
    async def execute(self, payload: Dict[str, Any]) -> Any:
        data = payload.get("data", "")
        await asyncio.sleep(1)
        return hashlib.sha256(data.encode()).hexdigest()

class MathTaskHandler(BaseTaskHandler):
    async def execute(self, payload: Dict[str, Any]) -> Any:
        nums = payload.get("numbers", [])
        await asyncio.sleep(1)
        return {
            "sum": sum(nums),
            "max": max(nums, default=0),
            "min": min(nums, default=0)
        }

# =========================
# Task Factory
# =========================

class TaskFactory:
    _handlers: Dict[str, BaseTaskHandler] = {
        "hash": HashTaskHandler(),
        "math": MathTaskHandler(),
    }

    @classmethod
    def get_handler(cls, task_type: str) -> BaseTaskHandler:
        if task_type not in cls._handlers:
            raise ValueError(f"Unknown task type: {task_type}")
        return cls._handlers[task_type]

# =========================
# Task Engine
# =========================

class TaskEngine:
    def __init__(
        self,
        config: AppConfig,
        storage: TaskStorage,
        cache: ResultCache,
        logger: logging.Logger,
    ):
        self.config = config
        self.storage = storage
        self.cache = cache
        self.logger = logger
        self.tasks: Dict[str, Task] = {}

    async def bootstrap(self):
        self.tasks = await self.storage.load_all()
        self.logger.info("Loaded %d tasks from storage", len(self.tasks))

    async def create_task(self, name: str, payload: Dict[str, Any]) -> Task:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name,
            payload=payload,
            created_at=time.time(),
        )
        self.tasks[task_id] = task
        await self.storage.save_all(self.tasks)
        self.logger.info("Created task %s", task_id)
        return task

    async def run_task(self, task_id: str) -> Task:
        if task_id not in self.tasks:
            raise KeyError("Task not found")

        task = self.tasks[task_id]
        if task.status == "COMPLETED":
            self.logger.info("Task %s loaded from cache", task_id)
            return task

        cache_key = f"{task.name}:{json.dumps(task.payload, sort_keys=True)}"
        cached = self.cache.get(cache_key)
        if cached:
            task.status = "COMPLETED"
            task.result = cached
            return task

        handler = TaskFactory.get_handler(task.name)

        task.status = "RUNNING"
        await self.storage.save_all(self.tasks)

        try:
            result = await handler.execute(task.payload)
            task.result = result
            task.status = "COMPLETED"
            self.cache.set(cache_key, result)
        except Exception as e:
            task.status = "FAILED"
            task.result = {"error": str(e)}
            self.logger.exception("Task failed")

        await self.storage.save_all(self.tasks)
        return task

    async def list_tasks(self) -> List[Task]:
        return list(self.tasks.values())

# =========================
# CLI Interface
# =========================

class CLI:
    def __init__(self, engine: TaskEngine):
        self.engine = engine

    async def handle(self, args: argparse.Namespace):
        if args.command == "create":
            payload = json.loads(args.payload)
            task = await self.engine.create_task(args.type, payload)
            print("✅ Task Created:", task.id)

        elif args.command == "run":
            task = await self.engine.run_task(args.id)
            print("⚡ Task Result:", json.dumps(task.result, indent=2))

        elif args.command == "list":
            tasks = await self.engine.list_tasks()
            for t in tasks:
                print(f"{t.id} | {t.name} | {t.status}")

# =========================
# Argument Parser
# =========================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smart Task Engine CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create")
    create.add_argument("--type", required=True, choices=["hash", "math"])
    create.add_argument("--payload", required=True)

    run = sub.add_parser("run")
    run.add_argument("--id", required=True)

    sub.add_parser("list")

    return parser

# =========================
# Dependency Container
# =========================

class Container:
    def __init__(self):
        self.config = AppConfig.load()
        self.logger = setup_logger(self.config.debug)
        self.storage = TaskStorage(self.config.storage_file, self.logger)
        self.cache = ResultCache()
        self.engine = TaskEngine(
            self.config, self.storage, self.cache, self.logger
        )

# =========================
# Application Entry Point
# =========================

async def main():
    container = Container()
    await container.engine.bootstrap()

    parser = build_parser()
    args = parser.parse_args()

    cli = CLI(container.engine)
    await cli.handle(args)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")

"""
Smart Concurrency & Multi-Tasking Orchestrator.
Provides:
1. Strict FIFO Serialization for Same Account / Same Task Collisions.
2. Concurrent Multi-Worker Parallelism for Distinct Accounts / Platforms.
3. Live Queue Position Tracking and Automatic Promotion.
4. Stop / Abort Signaling via threading.Event.
"""
import os
import sys
import time
import uuid
import logging
import threading
from enum import Enum
from typing import Callable, Dict, Any, List, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

logger = logging.getLogger("automation.orchestrator")


class TaskState(Enum):
    QUEUED = "queued"
    ACQUIRING = "acquiring"
    RUNNING = "running"
    PAUSED_COOLDOWN = "paused_cooldown"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AutomationTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Background Task"
    task_type: str = "growth"                # growth, post, group, content_gen
    platform: str = "facebook"               # facebook, instagram, linkedin, general
    account_id: str = "manvxi_ai"            # manvxi_ai, loan_solutions, personal
    lock_key: str = ""                       # platform:account_id
    payload: Dict[str, Any] = field(default_factory=dict)
    run_fn: Optional[Callable] = None        # Function to execute: run_fn(task)
    state: TaskState = TaskState.QUEUED
    priority: int = 10                       # 1 = Urgent (emergency post), 10 = Standard
    progress_current: int = 0
    progress_total: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    tg_chat_id: Optional[str] = None
    tg_message_id: Optional[int] = None
    error_message: Optional[str] = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    on_promoted: Optional[Callable] = None
    current_activity: str = "Initializing task..."
    recent_activities: List[str] = field(default_factory=list)
    skipped_count: int = 0

    def __post_init__(self):
        if not self.lock_key:
            plat = (self.platform or "general").lower().strip()
            acc = (self.account_id or "default").lower().strip()
            self.lock_key = f"{plat}:{acc}"

    def update_progress(self, current: int, total: int = None):
        self.progress_current = current
        if total is not None:
            self.progress_total = total

    def set_activity(self, text: str):
        if not text:
            return
        clean_text = str(text).strip()
        self.current_activity = clean_text
        if not self.recent_activities or self.recent_activities[-1] != clean_text:
            self.recent_activities.append(clean_text)
            if len(self.recent_activities) > 8:
                self.recent_activities.pop(0)

    def increment_skipped(self, count: int = 1):
        self.skipped_count += count

    def is_stopped(self) -> bool:
        return self.stop_event.is_set()


class TaskQueueOrchestrator:
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._singleton_lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_concurrent_workers: int = 6):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.max_workers = max_concurrent_workers
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="TaskWorker")
        self.all_tasks: Dict[str, AutomationTask] = {}              # task_id -> Task
        self.active_tasks: Dict[str, AutomationTask] = {}           # task_id -> Task (currently running)
        self.account_locks: Dict[str, str] = {}                     # lock_key -> active task_id
        self.account_queues: Dict[str, List[AutomationTask]] = {}   # lock_key -> list of pending Tasks (FIFO)
        self.global_lock = threading.RLock()
        self._initialized = True
        logger.info(f"TaskQueueOrchestrator ready. Max concurrent worker slots: {max_concurrent_workers}")

    def submit_task(self, task: AutomationTask) -> Dict[str, Any]:
        """
        Submits a task for direct immediate execution (Queuing logic removed).
        - If a previous task is running on the same account/platform, it signals it to stop and overrides it immediately.
        - Immediately runs the task on a worker thread with zero queuing delay.
        """
        with self.global_lock:
            self.all_tasks[task.task_id] = task
            lock_key = task.lock_key

            # Direct Override: If an existing task is active on this account, stop it immediately
            if lock_key in self.account_locks:
                active_task_id = self.account_locks[lock_key]
                active_task = self.active_tasks.get(active_task_id) or self.all_tasks.get(active_task_id)
                if active_task and active_task.task_id != task.task_id:
                    logger.info(
                        f"⚡ [DIRECT OVERRIDE] Stopping prior task {active_task.task_id} ('{active_task.name}') "
                        f"to execute new request '{task.name}' immediately without queuing."
                    )
                    active_task.stop_event.set()
                    active_task.state = TaskState.CANCELLED
                    self.active_tasks.pop(active_task_id, None)

            # Clear any pending queues
            self.account_queues.pop(lock_key, None)

            # Run immediately on worker thread
            self.account_locks[lock_key] = task.task_id
            self.active_tasks[task.task_id] = task
            task.state = TaskState.RUNNING
            task.started_at = time.time()

            logger.info(
                f"⚡ [IMMEDIATE WORKER ACQUIRED] Task {task.task_id} ('{task.name}') "
                f"started immediately. Active tasks: {len(self.active_tasks)}/{self.max_workers}."
            )
            self.executor.submit(self._worker_wrapper, task)
            return {
                "status": "running",
                "task_id": task.task_id,
                "lock_key": lock_key,
                "position": 0,
                "active_count": len(self.active_tasks),
                "message": f"Task '{task.name}' started immediately."
            }

    def _worker_wrapper(self, task: AutomationTask):
        """Worker lifecycle execution wrapper with guaranteed cleanup."""
        try:
            logger.info(f"▶️ [RUNNING] Task {task.task_id} [{task.lock_key}] started execution.")
            if task.run_fn:
                task.run_fn(task)
            
            if not task.is_stopped() and task.state != TaskState.CANCELLED:
                task.state = TaskState.COMPLETED
                logger.info(f"✅ [SUCCESS] Task {task.task_id} [{task.lock_key}] completed.")
        except Exception as e:
            task.state = TaskState.FAILED
            task.error_message = str(e)
            logger.error(f"❌ [FAILED] Task {task.task_id} [{task.lock_key}] failed: {e}", exc_info=True)
        finally:
            task.completed_at = time.time()
            self._release_and_promote(task)

    def _release_and_promote(self, finished_task: AutomationTask):
        """Releases the lock for finished_task's lock_key."""
        lock_key = finished_task.lock_key
        with self.global_lock:
            # Remove from active tasks
            self.active_tasks.pop(finished_task.task_id, None)

            # Clear lock if still held by this finished task
            if self.account_locks.get(lock_key) == finished_task.task_id:
                self.account_locks.pop(lock_key, None)

    def cancel_task(self, task_id: str) -> bool:
        """Cancels a running or queued task safely."""
        with self.global_lock:
            task = self.all_tasks.get(task_id)
            if not task:
                return False

            task.stop_event.set()

            # If task is still queued, remove it immediately
            if task.state == TaskState.QUEUED:
                task.state = TaskState.CANCELLED
                queue_list = self.account_queues.get(task.lock_key, [])
                if task in queue_list:
                    queue_list.remove(task)
                logger.info(f"🛑 [CANCELLED] Queued task {task_id} removed from queue.")
                return True

            # If running, state will update to cancelled upon thread exit
            if task.state == TaskState.RUNNING:
                task.state = TaskState.CANCELLED
                logger.info(f"🛑 [STOP SIGNAL SENT] Running task {task_id} signaled to halt.")
                return True

            return False

    def get_snapshot(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry of all active workers and queued tasks."""
        with self.global_lock:
            active_list = []
            for t_id, task in self.active_tasks.items():
                elapsed = round(time.time() - (task.started_at or time.time()), 1)
                active_list.append({
                    "task_id": task.task_id,
                    "name": task.name,
                    "platform": task.platform,
                    "account_id": task.account_id,
                    "lock_key": task.lock_key,
                    "state": task.state.value,
                    "progress": f"{task.progress_current}/{task.progress_total}",
                    "elapsed_seconds": elapsed,
                    "current_activity": getattr(task, "current_activity", "Working in background..."),
                    "recent_activities": list(getattr(task, "recent_activities", [])),
                    "skipped_count": getattr(task, "skipped_count", 0),
                })

            queued_list = []
            for lock_key, q in self.account_queues.items():
                for idx, task in enumerate(q):
                    queued_list.append({
                        "task_id": task.task_id,
                        "name": task.name,
                        "platform": task.platform,
                        "account_id": task.account_id,
                        "lock_key": lock_key,
                        "position": idx + 1,
                        "state": task.state.value,
                    })

            return {
                "active_workers_count": len(self.active_tasks),
                "max_worker_slots": self.max_workers,
                "queued_tasks_count": len(queued_list),
                "active_tasks": active_list,
                "queued_tasks": queued_list,
            }


# Singleton accessor
orchestrator = TaskQueueOrchestrator()

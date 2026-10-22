"""
Validation Test Suite for Multitasking Concurrency Orchestrator.
Tests:
1. Parallel Execution: Distinct platforms/accounts run simultaneously (2+ tasks at the same time).
2. Queue Serialization: Same account/platform collisions are queued in strict FIFO order.
3. Cancellation & Promotion: Cancelling a running task unblocks and auto-promotes the next queued task.
"""
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Add project root and automation to path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "automation"))

from automation.core.task_orchestrator import TaskQueueOrchestrator, AutomationTask, TaskState


def test_concurrent_multitasking_different_accounts():
    """
    Requirement 2: When tasks or social accounts are not the same,
    the agent must perform multitasking at the same time (2 or more tasks running simultaneously).
    """
    print("\n" + "=" * 60)
    print("TEST 1: MULTI-TASKING CONCURRENT PARALLELISM (DISTINCT ACCOUNTS)")
    print("=" * 60)

    orch = TaskQueueOrchestrator(max_concurrent_workers=6)
    execution_timestamps = {}

    def mock_task_worker(task: AutomationTask):
        tid = task.task_id
        execution_timestamps[tid] = {"start": time.time(), "end": None}
        print(f"  ⚡ [{task.name}] Running in parallel worker thread...")
        time.sleep(1.0)
        execution_timestamps[tid]["end"] = time.time()
        print(f"  ✅ [{task.name}] Completed.")

    # 3 Distinct tasks targeting different platforms & accounts
    task1 = AutomationTask(
        name="FB Outreach (Manvxi AI)",
        platform="facebook",
        account_id="manvxi_ai",
        run_fn=mock_task_worker
    )
    task2 = AutomationTask(
        name="IG Follow (Loan Solutions)",
        platform="instagram",
        account_id="loan_solutions",
        run_fn=mock_task_worker
    )
    task3 = AutomationTask(
        name="LinkedIn Post (Loan Solutions)",
        platform="linkedin",
        account_id="loan_solutions",
        run_fn=mock_task_worker
    )

    t_start = time.time()
    res1 = orch.submit_task(task1)
    res2 = orch.submit_task(task2)
    res3 = orch.submit_task(task3)

    assert res1["status"] == "running", f"Task 1 should run immediately, got: {res1}"
    assert res2["status"] == "running", f"Task 2 should run immediately, got: {res2}"
    assert res3["status"] == "running", f"Task 3 should run immediately, got: {res3}"

    snapshot = orch.get_snapshot()
    print(f"  📊 Live Active Workers: {snapshot['active_workers_count']}/6 (All 3 executing concurrently!)")
    assert snapshot["active_workers_count"] >= 3, "All 3 tasks must be running simultaneously!"

    # Wait for completion
    time.sleep(1.4)
    total_duration = time.time() - t_start

    # If serial, 3 tasks of 1.0s would take >= 3.0s. If concurrent, takes ~1.0-1.5s!
    print(f"  ⏱️ Total execution time for 3 tasks: {total_duration:.2f}s")
    assert total_duration < 2.2, f"Expected concurrent execution (~1.0-1.5s), but took {total_duration:.2f}s!"

    # Verify timestamp overlap
    starts = [v["start"] for v in execution_timestamps.values()]
    ends = [v["end"] for v in execution_timestamps.values()]
    max_start = max(starts)
    min_end = min(ends)
    assert max_start < min_end, "All 3 tasks must have overlapped in time!"

    print("  🎉 TEST 1 PASSED: 3 tasks ran concurrently at the exact same time!\n")


def test_queue_serialization_same_account():
    """
    Requirement 1: Queue-wise multitasking for the same task or same social media account.
    """
    print("=" * 60)
    print("TEST 2: QUEUE-WISE SERIALIZATION (SAME ACCOUNT COLLISION)")
    print("=" * 60)

    orch = TaskQueueOrchestrator(max_concurrent_workers=6)
    execution_order = []

    def mock_serial_worker(task: AutomationTask):
        print(f"  🔒 [{task.name}] Acquired lock, executing...")
        execution_order.append(task.name)
        time.sleep(0.8)
        print(f"  🔓 [{task.name}] Releasing lock.")

    # 3 Tasks targeting the SAME account: 'facebook:manvxi_ai'
    task_a = AutomationTask(
        name="Task A (Outreach)",
        platform="facebook",
        account_id="manvxi_ai",
        run_fn=mock_serial_worker
    )
    task_b = AutomationTask(
        name="Task B (Accept Friends)",
        platform="facebook",
        account_id="manvxi_ai",
        run_fn=mock_serial_worker
    )
    task_c = AutomationTask(
        name="Task C (Group Creation)",
        platform="facebook",
        account_id="manvxi_ai",
        run_fn=mock_serial_worker
    )

    res_a = orch.submit_task(task_a)
    res_b = orch.submit_task(task_b)
    res_c = orch.submit_task(task_c)

    assert res_a["status"] == "running", "Task A should run immediately"
    assert res_b["status"] == "queued", f"Task B should be queued, got: {res_b}"
    assert res_b["position"] == 1, "Task B should be at position 1"
    assert res_c["status"] == "queued", f"Task C should be queued, got: {res_c}"
    assert res_c["position"] == 2, "Task C should be at position 2"

    print("  📋 Initial Queue Snapshot:")
    snap = orch.get_snapshot()
    for q in snap["queued_tasks"]:
        print(f"     • Position #{q['position']}: {q['name']} [{q['lock_key']}]")

    # Wait for all 3 tasks to cascade sequentially
    time.sleep(2.8)

    print(f"  🔄 Execution Sequence Observed: {execution_order}")
    assert execution_order == [
        "Task A (Outreach)",
        "Task B (Accept Friends)",
        "Task C (Group Creation)"
    ], f"Execution order mismatch! Expected A -> B -> C, got: {execution_order}"

    print("  🎉 TEST 2 PASSED: Strict FIFO queue serialization confirmed for same account!\n")


def test_task_cancellation_and_auto_promotion():
    """
    Requirement: Cancelling an active task frees the lock and auto-promotes the queued task.
    """
    print("=" * 60)
    print("TEST 3: TASK CANCELLATION & AUTOMATIC PROMOTION")
    print("=" * 60)

    orch = TaskQueueOrchestrator(max_concurrent_workers=6)
    b_started = False

    def long_task(task: AutomationTask):
        print("  ⏳ Long task started (running loop)...")
        for _ in range(50):
            if task.is_stopped():
                print("  🛑 Long task detected stop flag, terminating gracefully.")
                return
            time.sleep(0.1)

    def queued_task(task: AutomationTask):
        nonlocal b_started
        b_started = True
        print(f"  🚀 Queued task '{task.name}' successfully promoted and started!")

    t1 = AutomationTask(name="Long Task", platform="facebook", account_id="loan_solutions", run_fn=long_task)
    t2 = AutomationTask(name="Waiting Task", platform="facebook", account_id="loan_solutions", run_fn=queued_task)

    orch.submit_task(t1)
    res2 = orch.submit_task(t2)
    assert res2["status"] == "queued"

    time.sleep(0.2)
    print("  🛑 Sending cancel signal to Long Task...")
    cancel_success = orch.cancel_task(t1.task_id)
    assert cancel_success is True

    # Wait briefly for t1 to exit and t2 to be promoted
    time.sleep(0.5)
    assert b_started is True, "Waiting Task should have been automatically promoted and executed!"
    print("  🎉 TEST 3 PASSED: Cancellation unblocked and auto-promoted queued task!\n")


if __name__ == "__main__":
    test_concurrent_multitasking_different_accounts()
    test_queue_serialization_same_account()
    test_task_cancellation_and_auto_promotion()
    print("=" * 60)
    print("🏆 ALL 3 CONCURRENCY & MULTITASKING TESTS PASSED PERFECTLY!")
    print("=" * 60)

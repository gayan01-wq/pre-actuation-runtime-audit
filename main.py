"""
Hardware-Isolated, Sub-Millisecond Runtime Audit Architecture
for Autonomous Multi-Agent Systems via Pre-Actuation State Dissolution

A standalone reference implementation and verification harness.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional


# ==============================================================================
# Data Models & System States
# ==============================================================================

class AuditResult(Enum):
    APPROVED = "APPROVED"
    DISSOLVED_INVARIANT_VIOLATION = "DISSOLVED_INVARIANT_VIOLATION"
    DISSOLVED_TIMEOUT = "DISSOLVED_TIMEOUT"


@dataclass(frozen=True)
class ProposedAction:
    """Immutable action payload dispatched by an untrusted agent execution plane."""
    agent_id: str
    action_type: str
    payload: Dict[str, float]
    timestamp_ns: int = field(default_factory=time.perf_counter_ns)


# ==============================================================================
# Pre-Actuation Staging Buffer (Volatile Execution Interceptor)
# ==============================================================================

class StagedStateBuffer:
    """
    Volatile pre-actuation memory buffer simulating dual-port BRAM / DMA isolation.
    Actions staged here cannot affect physical actuator lines until formal verification commits.
    """

    def __init__(self, transaction_id: str, actions: List[ProposedAction]):
        self.transaction_id: str = transaction_id
        self.actions: List[ProposedAction] = list(actions)
        self.is_committed: bool = False
        self.is_dissolved: bool = False

    def dissolve(self, reason: str = "") -> None:
        """Active state dissolution: instantaneously purges volatile memory and drops pointers."""
        self.actions.clear()
        self.is_dissolved = True
        self.is_committed = False


# ==============================================================================
# Hardware-Isolated Invariant Audit Enclave
# ==============================================================================

class IsolatedInvariantEnclave:
    """
    Simulates a hardware-isolated invariant coprocessor (e.g., FPGA verifier / secure enclave).
    Evaluates proposed multi-agent state vectors against non-negotiable safety rules
    under a strict microsecond latency deadline.
    """

    def __init__(self, latency_budget_us: float = 800.0):
        self.latency_budget_us: float = latency_budget_us  # Hard cut-off (0.8 ms default)
        self.invariants: List[Callable[[ProposedAction], bool]] = []
        self._register_default_invariants()

    def add_invariant(self, rule: Callable[[ProposedAction], bool]) -> None:
        self.invariants.append(rule)

    def _register_default_invariants(self) -> None:
        # Invariant 1: Dynamic power/force magnitude upper bound
        self.invariants.append(lambda a: a.payload.get("magnitude", 0.0) <= 100.0)
        # Invariant 2: Positive allocation/reserve lower bound
        self.invariants.append(lambda a: a.payload.get("allocation", 0.0) >= 0.0)

    def audit_pre_actuation(self, staged_buffer: StagedStateBuffer) -> AuditResult:
        """
        Deterministic audit loop.
        Guarantees fail-closed pre-actuation state dissolution upon breach or timeout.
        """
        t_start = time.perf_counter_ns()

        for action in staged_buffer.actions:
            # Deterministic check across registered invariants
            for invariant in self.invariants:
                if not invariant(action):
                    staged_buffer.dissolve(reason=f"Invariant breach detected by {action.agent_id}")
                    return AuditResult.DISSOLVED_INVARIANT_VIOLATION

                # Enforce sub-millisecond execution budget
                elapsed_us = (time.perf_counter_ns() - t_start) / 1_000.0
                if elapsed_us > self.latency_budget_us:
                    staged_buffer.dissolve(reason=f"Timeout ceiling breached: {elapsed_us:.2f} µs")
                    return AuditResult.DISSOLVED_TIMEOUT

        return AuditResult.APPROVED


# ==============================================================================
# Physical Actuator Interface
# ==============================================================================

class PhysicalActuatorPlane:
    """Physical hardware register latch (e.g., motor drivers, trading API, I/O bus)."""

    @staticmethod
    def commit(staged_buffer: StagedStateBuffer) -> bool:
        if staged_buffer.is_dissolved or not staged_buffer.actions:
            return False
        staged_buffer.is_committed = True
        return True


# ==============================================================================
# Verification Suite & Live Demonstration
# ==============================================================================

def run_demonstration():
    print("=" * 70)
    print("HARDWARE-ISOLATED PRE-ACTUATION RUNTIME AUDIT SUITE")
    print("=" * 70)

    enclave = IsolatedInvariantEnclave(latency_budget_us=800.0)
    actuator = PhysicalActuatorPlane()

    # --- Scenario 1: Safe Multi-Agent Action Vector ---
    tx1_id = uuid.uuid4().hex
    valid_batch = [
        ProposedAction("Agent-Alpha", "MOTOR_STEP", {"magnitude": 45.0, "allocation": 12.0}),
        ProposedAction("Agent-Beta", "RESOURCE_DISPATCH", {"magnitude": 15.0, "allocation": 5.0}),
    ]
    buf1 = StagedStateBuffer(tx1_id, valid_batch)

    t0 = time.perf_counter_ns()
    res1 = enclave.audit_pre_actuation(buf1)
    committed1 = actuator.commit(buf1)
    latency1_us = (time.perf_counter_ns() - t0) / 1_000.0

    print(f"\n[Test 1] Nominal Action Vector")
    print(f"  Transaction ID   : {tx1_id[:12]}...")
    print(f"  Audit Result     : {res1.value}")
    print(f"  Physical Commit  : {committed1}")
    print(f"  Latency Elapsed  : {latency1_us:.2f} µs (Budget: {enclave.latency_budget_us} µs)")
    print(f"  Buffer Dissolved : {buf1.is_dissolved}")

    # --- Scenario 2: Adversarial Action Vector (Invariant Violation) ---
    tx2_id = uuid.uuid4().hex
    adversarial_batch = [
        ProposedAction("Agent-Gamma", "OVERRIDE_THROTTLE", {"magnitude": 185.0, "allocation": 2.0}),
    ]
    buf2 = StagedStateBuffer(tx2_id, adversarial_batch)

    t0 = time.perf_counter_ns()
    res2 = enclave.audit_pre_actuation(buf2)
    committed2 = actuator.commit(buf2)
    latency2_us = (time.perf_counter_ns() - t0) / 1_000.0

    print(f"\n[Test 2] Adversarial Invariant Breach")
    print(f"  Transaction ID   : {tx2_id[:12]}...")
    print(f"  Audit Result     : {res2.value}")
    print(f"  Physical Commit  : {committed2} (Actuation Intercepted)")
    print(f"  Latency Elapsed  : {latency2_us:.2f} µs")
    print(f"  Buffer Dissolved : {buf2.is_dissolved} (Volatile Memory Purged)")
    print(f"  Staged Actions   : {len(buf2.actions)} items remaining")

    # --- Scenario 3: High-Frequency Benchmark (10,000 Iterations) ---
    print("\n" + "-" * 70)
    print("Executing 10,000-cycle latency distribution benchmark...")
    iterations = 10_000
    latencies = []

    for _ in range(iterations):
        test_buf = StagedStateBuffer(
            uuid.uuid4().hex,
            [ProposedAction("BenchAgent", "PULSE", {"magnitude": 25.0, "allocation": 1.0})]
        )
        t_bench_start = time.perf_counter_ns()
        enclave.audit_pre_actuation(test_buf)
        latencies.append((time.perf_counter_ns() - t_bench_start) / 1_000.0)

    latencies.sort()
    p50 = latencies[int(iterations * 0.50)]
    p95 = latencies[int(iterations * 0.95)]
    p99 = latencies[int(iterations * 0.99)]

    print(f"  P50 (Median) : {p50:.2f} µs")
    print(f"  P95          : {p95:.2f} µs")
    print(f"  P99          : {p99:.2f} µs")
    print("=" * 70)


if __name__ == "__main__":
    run_demonstration()

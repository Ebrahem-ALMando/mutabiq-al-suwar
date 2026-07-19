"""Explicit processing lifecycle states shared by the GUI and tests."""

from __future__ import annotations

from enum import StrEnum


class OperationState(StrEnum):
    IDLE = "idle"
    VALIDATING = "validating"
    SCANNING = "scanning"
    MATCHING = "matching"
    COPYING = "copying"
    GENERATING_REPORT = "generating_report"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


TERMINAL_STATES = {
    OperationState.COMPLETED,
    OperationState.PARTIAL_SUCCESS,
    OperationState.FAILED,
    OperationState.CANCELLED,
}

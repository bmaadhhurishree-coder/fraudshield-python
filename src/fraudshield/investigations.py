"""Temporal fraud review workflow; only risk review cases start a workflow."""
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow


@dataclass
class InvestigationRequest:
    transaction_id: str
    risk_score: int
    reasons: list[str]


@workflow.defn
class InvestigationWorkflow:
    def __init__(self):
        self._decision: str | None = None

    @workflow.run
    async def run(self, request: InvestigationRequest) -> str:
        # Human decision may arrive asynchronously from an authorized API.
        try:
            await workflow.wait_condition(
                lambda: self._decision is not None,
                timeout=timedelta(hours=24),
            )
        except TimeoutError:
            return "expired"
        return self._decision or "expired"

    @workflow.signal
    def analyst_decision(self, decision: str) -> None:
        if decision not in ("allow", "decline"):
            raise ValueError("invalid analyst decision")
        if self._decision is None:
            self._decision = decision

    @workflow.query
    def status(self) -> str:
        return self._decision or "pending"
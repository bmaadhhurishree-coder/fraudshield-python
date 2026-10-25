from unittest.mock import AsyncMock

import pytest

from fraudshield.worker import handle_event


@pytest.mark.asyncio
async def test_review_starts_investigation():
    client = AsyncMock()
    event = {"event_type": "transaction.scored.v1",
             "payload": {"transaction_id": "tx-1", "score": 70,
                         "decision": "review", "reasons": ["new_device"]}}
    await handle_event(client, event)
    client.start_workflow.assert_awaited_once()
    assert client.start_workflow.await_args.kwargs["id"] == "investigation-tx-1"


@pytest.mark.asyncio
async def test_allow_does_not_start_investigation():
    client = AsyncMock()
    await handle_event(client, {"event_type": "transaction.scored.v1",
                               "payload": {"decision": "allow"}})
    client.start_workflow.assert_not_awaited()
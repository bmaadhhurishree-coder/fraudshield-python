"""Kafka consumer starts deduplicated Temporal investigations for review decisions."""
import asyncio
import json
import logging
import os

from confluent_kafka import Consumer
from temporalio.client import Client
from temporalio.worker import Worker

from .investigations import InvestigationRequest, InvestigationWorkflow
from .outbox import TOPIC

log = logging.getLogger(__name__)
TASK_QUEUE = "fraudshield-investigations"


async def handle_event(client: Client, event: dict) -> None:
    if event.get("event_type") != "transaction.scored.v1":
        return
    data = event["payload"]
    if data["decision"] != "review":
        return
    transaction_id = data["transaction_id"]
    try:
        await client.start_workflow(
            InvestigationWorkflow.run,
            InvestigationRequest(transaction_id, data["score"], data["reasons"]),
            id=f"investigation-{transaction_id}",
            task_queue=TASK_QUEUE,
        )
    except Exception as exc:
        from temporalio.client import WorkflowAlreadyStartedError
        from temporalio.service import RPCError

        if isinstance(exc, WorkflowAlreadyStartedError):
            log.info("Investigation already exists for %s", transaction_id)
            return
        if isinstance(exc, RPCError):
            raise
        raise


async def run():
    client = await Client.connect(os.getenv("TEMPORAL_ADDRESS", "localhost:7233"))
    consumer = Consumer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        "group.id": "fraudshield-investigations-v1",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([TOPIC])

    async with Worker(client, task_queue=TASK_QUEUE, workflows=[InvestigationWorkflow]):
        try:
            while True:
                message = await asyncio.to_thread(consumer.poll, 1.0)
                if message is None:
                    continue
                if message.error():
                    raise RuntimeError(str(message.error()))
                event = json.loads(message.value())
                await handle_event(client, event)
                await asyncio.to_thread(consumer.commit, message, asynchronous=False)
        finally:
            consumer.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
"""A2A 1.0 SDK adapter patterned after blocksnet-agent's executor/card split."""
import asyncio
import json
import uuid

from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.fastapi_routes import add_a2a_routes_to_fastapi
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (AgentCard, Artifact, Message, Part, Role, Task, TaskArtifactUpdateEvent,
                       TaskState, TaskStatus, TaskStatusUpdateEvent)
from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.struct_pb2 import Value
from google.protobuf.timestamp_pb2 import Timestamp
from starlette.requests import Request
from starlette.routing import Route

from .jobs import TERMINAL
from .schemas import EstimateRequest, OptimizationRequest


def build_card(settings):
    base = settings.public_url.rstrip("/")
    properties = {
        "operation": {"type": "string", "enum": ["estimate_land_value", "optimize_district"],
                      "description": "Choose land valuation or district scenario optimization."},
        "dataset_id": {"type": "string", "description": "Exact registered dataset id. Never infer it from a city name."},
        "target_id": {"type": "string", "description": "Exact block id from the dataset, as a string. Never invent an id."},
        "constraints_json": {"type": "string", "description": 'For optimization: JSON object of explicit bounds, e.g. {"l":{"min":1,"max":8}}. Do not invent limits. Omitted variables stay fixed.'},
        "strategy": {"type": "string", "description": "User's scenario evaluation strategy (soft preferences)."},
        "use_llm": {"type": "boolean", "description": "Default true. False explicitly disables strategy scoring."},
        "pop_size": {"type": "integer", "minimum": 4, "maximum": 100},
        "n_gen": {"type": "integer", "minimum": 1, "maximum": 200},
        "seed": {"type": "integer", "minimum": 0},
    }
    card = {
        "name": "Urbanomy", "description": "Land valuation and constrained NSGA-II district optimization with LLM strategy scoring.",
        "version": "0.1.0", "supportedInterfaces": [{"url": base + "/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}],
        "capabilities": {"streaming": True, "extensions": [{
            "uri": base + "/extensions/urbanomy-input/v1", "required": True,
            "description": "Structured Urbanomy input; constraints_json supports Codesynapse scalar parameter extraction.",
            "params": {"type": "object", "properties": properties,
                       "required": ["operation", "dataset_id", "target_id"], "additionalProperties": False},
        }]},
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [
            {"id": "estimate_land_value", "name": "Оценка земли", "description": "Predict target and dataset land value from registered spatial data.", "tags": ["land", "valuation"]},
            {"id": "optimize_district", "name": "Оптимизация квартала", "description": "Evaluate constrained scenarios and return a Pareto front with economic metrics and optional LLM scores.", "tags": ["urban", "optimization", "strategy"]},
        ],
    }
    if settings.token:
        card["securitySchemes"] = {"bearer": {"httpAuthSecurityScheme": {"scheme": "bearer"}}}
        card["securityRequirements"] = [{"schemes": {"bearer": {"list": []}}}]
    return ParseDict(card, AgentCard())


def parse_input(message):
    payload, texts = {}, []
    for part in message.parts:
        if part.HasField("data"):
            data = MessageToDict(part.data)
            if not isinstance(data, dict):
                raise ValueError("DataPart must contain a JSON object.")
            if payload.keys() & data.keys():
                raise ValueError("Duplicate input fields in DataParts.")
            payload.update(data)
        elif part.HasField("text"):
            texts.append(part.text)
        else:
            raise ValueError("Use text/data parts; upload datasets on the server before calling the agent.")
    operation = payload.pop("operation", None)
    if operation not in ("estimate_land_value", "optimize_district"):
        raise ValueError("DataPart.operation must be estimate_land_value or optimize_district.")
    if "constraints_json" in payload:
        if "constraints" in payload:
            raise ValueError("Provide constraints OR constraints_json, not both.")
        payload["constraints"] = json.loads(payload.pop("constraints_json"))
    if operation == "optimize_district" and not any(key in payload for key in ("strategy", "prompt")):
        payload["strategy"] = "\n".join(texts).strip()
    # Protobuf Value represents all JSON numbers as doubles; restore integer fields only.
    for key in ("target_id", "pop_size", "n_gen", "seed"):
        if isinstance(payload.get(key), float) and payload[key].is_integer():
            payload[key] = int(payload[key])
    schema = OptimizationRequest if operation == "optimize_district" else EstimateRequest
    return operation, schema.model_validate(payload).model_dump(mode="json")


def status(state, text):
    timestamp = Timestamp()
    timestamp.GetCurrentTime()
    return TaskStatus(state=state, timestamp=timestamp,
        message=Message(message_id=uuid.uuid4().hex, role=Role.ROLE_AGENT,
                        parts=[Part(text=text, media_type="text/plain")]))


class UrbanomyExecutor(AgentExecutor):
    def __init__(self, service):
        self.service = service
        self.jobs_by_task = {}

    async def execute(self, context, event_queue):
        task_id, context_id = context.task_id, context.context_id
        owner = "a2a:" + context.tenant
        key = (context.tenant, task_id)
        await event_queue.enqueue_event(Task(id=task_id, context_id=context_id,
            status=status(TaskState.TASK_STATE_SUBMITTED, "Проверяю параметры расчёта.")))
        try:
            operation, payload = parse_input(context.message)
            job = self.service.submit(operation, payload, owner)
            self.jobs_by_task[key] = job["job_id"]
            previous = None
            while job["status"] not in TERMINAL:
                progress = job.get("progress", {})
                if progress != previous:
                    await event_queue.enqueue_event(TaskStatusUpdateEvent(task_id=task_id, context_id=context_id,
                        status=status(TaskState.TASK_STATE_WORKING, f"Выполняется расчёт. Оценено сценариев: {progress.get('evaluations', 0)}.")))
                    previous = progress
                await asyncio.sleep(0.5)
                job = self.service.jobs.get(job["job_id"], owner)
            result = self.service.jobs.result(job["job_id"], owner)
            if job["status"] == "completed":
                result_data = result["result"]
                await event_queue.enqueue_event(TaskArtifactUpdateEvent(task_id=task_id, context_id=context_id,
                    artifact=Artifact(artifact_id="result", name="Urbanomy result", parts=[
                        Part(text=result_data["summary"], media_type="text/plain"),
                        Part(data=ParseDict(result_data, Value()), media_type="application/json"),
                    ])))
                await event_queue.enqueue_event(TaskArtifactUpdateEvent(task_id=task_id, context_id=context_id,
                    artifact=Artifact(artifact_id="spatial-result", name="scenarios.geojson", parts=[
                        Part(data=ParseDict(self.service.jobs.geojson(job["job_id"], owner), Value()), media_type="application/json"),
                    ])))
                state, text = TaskState.TASK_STATE_COMPLETED, result_data["summary"]
            elif job["status"] == "canceled":
                # cancel() has already emitted the terminal event.
                return
            else:
                state, text = TaskState.TASK_STATE_FAILED, json.dumps(result.get("error"), ensure_ascii=False)
        except asyncio.CancelledError:
            if key in self.jobs_by_task:
                await asyncio.to_thread(self.service.jobs.cancel, self.jobs_by_task[key], owner)
            raise
        except (ValueError, TypeError) as exc:
            state, text = TaskState.TASK_STATE_FAILED, f"INVALID_REQUEST: {exc}"
        finally:
            self.jobs_by_task.pop(key, None)
        await event_queue.enqueue_event(TaskStatusUpdateEvent(task_id=task_id, context_id=context_id, status=status(state, text)))

    async def cancel(self, context, event_queue):
        key = (context.tenant, context.task_id)
        job_id = self.jobs_by_task.get(key)
        if job_id:
            await asyncio.to_thread(self.service.jobs.cancel, job_id, "a2a:" + context.tenant)
        await event_queue.enqueue_event(TaskStatusUpdateEvent(task_id=context.task_id, context_id=context.context_id,
            status=status(TaskState.TASK_STATE_CANCELED, "Расчёт остановлен.")))


def add_routes(app, service):
    card = build_card(service.settings)
    executor = UrbanomyExecutor(service)
    handler = DefaultRequestHandler(agent_executor=executor,
        task_store=InMemoryTaskStore(owner_resolver=lambda context: context.tenant + ":" + context.user.user_name), agent_card=card)
    sdk_route = create_jsonrpc_routes(handler, rpc_url="/a2a")[0]

    async def rpc(request):
        # Codesynapse's prose uses these names; SDK 1.1 uses PascalCase.
        # Only method names are aliased: all payloads remain strictly A2A 1.0.
        body = await request.body()
        try:
            data = json.loads(body)
            aliases = {"message/send": "SendMessage", "message/stream": "SendStreamingMessage",
                       "tasks/get": "GetTask", "tasks/cancel": "CancelTask"}
            if isinstance(data, dict) and data.get("method") in aliases:
                data["method"] = aliases[data["method"]]
                body = json.dumps(data).encode()
        except (ValueError, TypeError):
            pass  # The SDK returns the protocol's parse error.
        delivered = False
        async def receive():
            nonlocal delivered
            if delivered:
                return await request.receive()
            delivered = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await sdk_route.endpoint(Request(request.scope, receive))

    add_a2a_routes_to_fastapi(app, agent_card_routes=create_agent_card_routes(card),
                            jsonrpc_routes=[Route("/a2a", endpoint=rpc, methods=["POST"])])
    return handler

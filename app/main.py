"""FastAPI application for persisted, deterministic capacity-planning scenarios."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.demo_data import fresh_demo_scenarios
from app.engine import calculate_capacity
from app.repository import ScenarioNotFoundError, ScenarioRecord, ScenarioRepository
from app.schemas import ScenarioCompare, ScenarioCreate

logger = logging.getLogger(__name__)
SizingFunction = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def create_app(
    *,
    database_path: str | Path | None = None,
    sizing_function: SizingFunction | None = None,
    seed_demo_data: bool = False,
) -> FastAPI:
    """Create an application with replaceable storage location and sizing engine."""

    resolved_path = Path(
        database_path
        or os.getenv("DATABASE_PATH")
        or os.getenv("CAPACITY_PLANNER_DB", "data/capacity_planner.db")
    )
    repository = ScenarioRepository(resolved_path)
    if seed_demo_data:
        _seed_fictional_scenarios(repository)
    calculate = sizing_function or calculate_capacity
    application = FastAPI(
        title="Enterprise AI Capacity & Commercial Sizing Planner",
        version="1.0.0",
        description=(
            "Deterministic first-pass indicative capacity ranges; not a final vendor quote."
        ),
    )
    application.state.repository = repository
    templates = Jinja2Templates(directory="templates")
    application.mount(
        "/static",
        StaticFiles(directory="static", check_dir=False),
        name="static",
    )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        details = jsonable_encoder(exception.errors())
        return JSONResponse(
            status_code=422,
            content=_error(
                "validation_error",
                "Request validation failed.",
                details=details,
            ),
        )

    @application.exception_handler(ScenarioNotFoundError)
    async def not_found_handler(
        _request: Request,
        exception: ScenarioNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=_error("scenario_not_found", str(exception)),
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        _request: Request,
        exception: StarletteHTTPException,
    ) -> JSONResponse:
        if exception.status_code == 404:
            code, message = "not_found", "Route was not found."
        elif exception.status_code == 405:
            code, message = "method_not_allowed", "Request method is not allowed."
        else:
            code, message = "http_error", "The HTTP request could not be completed."
        return JSONResponse(
            status_code=exception.status_code,
            content=_error(code, message),
            headers=exception.headers,
        )

    @application.exception_handler(Exception)
    async def internal_error_handler(_request: Request, exception: Exception) -> JSONResponse:
        logger.exception("Capacity calculation failed", exc_info=exception)
        return JSONResponse(
            status_code=500,
            content=_error(
                "internal_error",
                "The capacity calculation could not be completed.",
            ),
        )

    @application.get("/health")
    def health() -> dict[str, Any]:
        return _success({"status": "ok"})

    @application.get("/", include_in_schema=False)
    def index(request: Request) -> Response:
        return templates.TemplateResponse(request=request, name="index.html", context={})

    @application.get("/api/scenarios")
    def list_scenarios() -> dict[str, Any]:
        return _success([_scenario_projection(item, calculate) for item in repository.list()])

    @application.post("/api/scenarios", status_code=201)
    def create_scenario(payload: ScenarioCreate) -> dict[str, Any]:
        document = payload.model_dump(mode="json", exclude_none=True)
        result = _run_calculation(document, calculate)
        record = repository.create(document)
        return _success(_scenario_projection(record, calculate, result=result))

    @application.post("/api/scenarios/compare")
    def compare_scenarios(payload: ScenarioCompare) -> dict[str, Any]:
        scenarios = [
            _scenario_projection(repository.get(identifier), calculate)
            for identifier in payload.scenario_ids
        ]
        return _success({"scenarios": scenarios})

    @application.get("/api/scenarios/{scenario_id}/export")
    def export_scenario(
        scenario_id: int,
        format: Literal["json", "markdown"] = Query(default="json"),
    ) -> Response:
        projection = _scenario_projection(repository.get(scenario_id), calculate)
        slug = _safe_slug(projection["name"])
        if format == "json":
            body = json.dumps(projection, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            return Response(
                content=body,
                media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="{slug}.json"'},
            )
        return Response(
            content=_markdown_export(projection),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{slug}.md"'},
        )

    @application.get("/api/scenarios/{scenario_id}")
    def get_scenario(scenario_id: int) -> dict[str, Any]:
        return _success(_scenario_projection(repository.get(scenario_id), calculate))

    @application.put("/api/scenarios/{scenario_id}")
    def update_scenario(scenario_id: int, payload: ScenarioCreate) -> dict[str, Any]:
        repository.get(scenario_id)
        document = payload.model_dump(mode="json", exclude_none=True)
        result = _run_calculation(document, calculate)
        record = repository.update(scenario_id, document)
        return _success(_scenario_projection(record, calculate, result=result))

    @application.delete("/api/scenarios/{scenario_id}")
    def delete_scenario(scenario_id: int) -> dict[str, Any]:
        repository.delete(scenario_id)
        return _success({"id": scenario_id, "deleted": True})

    return application


def _scenario_projection(
    record: ScenarioRecord,
    calculate: SizingFunction,
    *,
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    projection = asdict(record)
    resolved_result = result if result is not None else _run_calculation(projection, calculate)
    projection["result"] = dict(resolved_result)
    return projection


def _run_calculation(
    scenario: Mapping[str, Any],
    calculate: SizingFunction,
) -> Mapping[str, Any]:
    engine_inputs = {
        "workload_mode": scenario["workload_mode"],
        **dict(scenario["inputs"]),
    }
    return calculate(engine_inputs)


def _seed_fictional_scenarios(repository: ScenarioRepository) -> None:
    if repository.list():
        return
    for scenario in fresh_demo_scenarios():
        validated = ScenarioCreate.model_validate(scenario)
        repository.create(validated.model_dump(mode="json", exclude_none=True))


def _success(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data, "error": None}


def _error(
    code: str,
    message: str,
    *,
    details: Any | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"success": False, "data": None, "error": error}


def _safe_slug(name: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "-" for character in name)
    return "-".join(part for part in normalized.split("-") if part) or "capacity-scenario"


def _markdown_export(projection: Mapping[str, Any]) -> str:
    inputs = projection["inputs"]
    result = projection["result"]
    lines = [
        f"# Capacity sizing: {projection['name']}",
        "",
        "> This is a deterministic first-pass indicative range, not a final vendor quote or a",
        "> replacement for benchmark validation and solution-engineering review.",
        "",
        f"- **Workload mode:** `{projection['workload_mode']}`",
        f"- **Region:** `{inputs.get('region', 'not supplied')}`",
        f"- **Updated:** `{projection['updated_at']}`",
        "",
        "## Inputs",
        "",
        "```json",
        json.dumps(inputs, indent=2, sort_keys=True, ensure_ascii=False),
        "```",
        "",
        "## Indicative result",
        "",
        "```json",
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False),
        "```",
        "",
    ]
    return "\n".join(lines)


def _environment_flag(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


app = create_app(seed_demo_data=_environment_flag("SEED_DEMO_DATA", default=True))

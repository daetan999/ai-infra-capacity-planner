"""Validated HTTP contracts for capacity-planning scenarios."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

WorkloadMode = Literal[
    "llm_training",
    "llm_inference",
    "rag_inference",
    "vision_inference",
    "batch_ai_hpc",
]
ScalarOverride = str | int | float | bool

NonBlankShortText = Annotated[str, Field(min_length=1, max_length=120)]
OptionalPositiveFloat = Annotated[float | None, Field(gt=0)]
OptionalNonNegativeFloat = Annotated[float | None, Field(ge=0)]
OptionalPositiveInt = Annotated[int | None, Field(gt=0)]


class StrictModel(BaseModel):
    """Forbid silently ignored input and normalize surrounding whitespace."""

    model_config = ConfigDict(
        allow_inf_nan=False,
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )


class CapacityInputs(StrictModel):
    """Cross-mode planning inputs; mode-specific completeness belongs to the engine."""

    model_parameters_billions: OptionalPositiveFloat = None
    model_family: Annotated[str | None, Field(min_length=1, max_length=80)] = None
    precision: Annotated[str | None, Field(min_length=1, max_length=24)] = None
    context_tokens: OptionalPositiveInt = None
    tokens_per_request: OptionalPositiveInt = None
    average_input_tokens: Annotated[int | None, Field(ge=0)] = None
    average_output_tokens: Annotated[int | None, Field(ge=0)] = None
    tokens_per_day: Annotated[int | None, Field(ge=0)] = None
    requests_per_second: OptionalPositiveFloat = None
    concurrency: OptionalPositiveInt = None
    peak_factor: Annotated[float | None, Field(ge=1)] = None
    latency_target_ms: OptionalPositiveInt = None
    availability_target_pct: Annotated[float | None, Field(gt=0, le=100)] = None
    dataset_tb: OptionalNonNegativeFloat = None
    training_window_hours: OptionalNonNegativeFloat = None
    storage_tb: OptionalNonNegativeFloat = None
    storage_growth_pct: OptionalNonNegativeFloat = None
    growth_pct: OptionalNonNegativeFloat = None
    ingress_gbps: OptionalNonNegativeFloat = None
    egress_gbps: OptionalNonNegativeFloat = None
    region: Annotated[str | None, Field(min_length=1, max_length=80)] = None
    target_utilization_pct: Annotated[float | None, Field(gt=0, le=100)] = None
    accelerator_profile: Annotated[str | None, Field(min_length=1, max_length=80)] = None
    assumption_overrides: dict[str, ScalarOverride] = Field(default_factory=dict)

    @field_validator("assumption_overrides")
    @classmethod
    def validate_override_names(
        cls,
        overrides: dict[str, ScalarOverride],
    ) -> dict[str, ScalarOverride]:
        normalized = {key.strip(): value for key, value in overrides.items()}
        if "" in normalized:
            raise ValueError("assumption override names must not be blank")
        if len(normalized) != len(overrides):
            raise ValueError("assumption override names must be unique after trimming")
        unsupported = set(normalized) - {"batch_size"}
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise ValueError(f"unsupported assumption overrides: {names}")
        batch_size = normalized.get("batch_size")
        if batch_size is not None and (
            isinstance(batch_size, bool)
            or not isinstance(batch_size, (int, float))
            or batch_size <= 0
        ):
            raise ValueError("batch_size must be a positive number")
        return normalized


class ScenarioCreate(StrictModel):
    """Create/replace payload for a sizing scenario."""

    name: NonBlankShortText
    description: Annotated[str | None, Field(min_length=1, max_length=500)] = None
    workload_mode: WorkloadMode
    inputs: CapacityInputs


class ScenarioCompare(StrictModel):
    """Ordered collection of scenario identifiers to compare."""

    scenario_ids: Annotated[list[int], Field(min_length=2, max_length=10)]

    @model_validator(mode="after")
    def reject_duplicates(self) -> ScenarioCompare:
        if len(set(self.scenario_ids)) != len(self.scenario_ids):
            raise ValueError("scenario_ids must be unique")
        if any(identifier <= 0 for identifier in self.scenario_ids):
            raise ValueError("scenario_ids must contain positive integers")
        return self

"""HTTP request validation and supported AIConfigurator systems."""

from typing import Final

from pydantic import BaseModel, Field, field_validator

from portal.adapters import RunRequest

# Keep this matrix aligned with the pinned SDK's default ``trtllm`` databases;
# CLI help names such as ``a100_pcie`` are not proof that a sweep is available.
SUPPORTED_SYSTEMS: Final[frozenset[str]] = frozenset(
    {
        "a100_sxm",
        "b200_sxm",
        "gb200",
        "gb300",
        "h100_sxm",
        "h200_sxm",
        "l40s",
    }
)


class RunSubmission(BaseModel):
    """Validated user input for one estimator run."""

    model: str = Field(min_length=1, max_length=256)
    system: str
    total_gpus: int = Field(ge=1, le=512)
    ttft: float = Field(gt=0, le=120_000)
    tpot: float = Field(gt=0, le=10_000)
    isl: int = Field(default=4000, ge=1, le=1_000_000)
    osl: int = Field(default=1000, ge=1, le=1_000_000)

    @field_validator("model")
    @classmethod
    def normalize_model(cls, value: str) -> str:
        """Reject whitespace-only values while preserving model identifiers."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("model must not be blank")
        return normalized

    @field_validator("system")
    @classmethod
    def validate_system(cls, value: str) -> str:
        """Allow only systems with a known AIConfigurator support entry."""

        normalized = value.strip().lower()
        if normalized not in SUPPORTED_SYSTEMS:
            supported = ", ".join(sorted(SUPPORTED_SYSTEMS))
            raise ValueError(f"unsupported system; choose one of: {supported}")
        return normalized

    def to_request(self) -> RunRequest:
        """Convert the HTTP model to the adapter-owned domain model."""

        return RunRequest(
            model=self.model,
            system=self.system,
            total_gpus=self.total_gpus,
            ttft_ms=self.ttft,
            tpot_ms=self.tpot,
            isl=self.isl,
            osl=self.osl,
        )

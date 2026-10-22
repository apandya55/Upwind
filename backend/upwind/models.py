from typing import Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class Point(Schema):
    latitude: float = Field(ge=-85, le=85)
    longitude: float = Field(ge=-180, le=180)


class TimedPoint(Point):
    timestamp: str
    origin: Literal["user_import", "synthetic"] = "user_import"

    @field_validator("timestamp")
    @classmethod
    def timestamp_aware(cls, value):
        from datetime import timezone

        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("Timestamp must have an explicit UTC offset")
        return dt.astimezone(timezone.utc).isoformat()


class Measurement(TimedPoint):
    sensor_id: str = Field(min_length=1, max_length=100)
    timestamp: str
    pm25_ug_m3: float
    uncertainty_ug_m3: float | None = Field(default=None, ge=0.01, le=1000)
    humidity_percent: float | None = Field(default=None, ge=0, le=100)
    temperature_c: float | None = None
    flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def review_values(self):
        if self.pm25_ug_m3 < 0 and "negative" not in self.flags:
            self.flags.append("negative")
        if self.pm25_ug_m3 > 500 and "extreme_review" not in self.flags:
            self.flags.append("extreme_review")
        return self


class Weather(TimedPoint):
    timestamp: str
    wind_speed_m_s: float = Field(ge=0, le=100)
    wind_from_deg: float = Field(ge=0, le=360)
    role: Literal["primary", "reference"] = "primary"
    source_id: str = Field(default="primary", min_length=1, max_length=100)
    upstream_id: str = Field(default="", max_length=200)
    direction_systematic_sd_deg: float | None = Field(default=None, ge=0.5, le=45)
    speed_systematic_fraction: float | None = Field(default=None, ge=0.01, le=0.5)
    direction_random_sd_deg: float = Field(default=2, ge=0.5, le=45)
    comparison_provenance: str = Field(default="", max_length=1000)

    @field_validator("wind_from_deg")
    @classmethod
    def north_equivalence(cls, value):
        return value % 360

    provenance: str = Field(
        default="User import; representativeness unverified", max_length=500
    )


class Site(Point):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["sensor", "candidate"] = "candidate"
    allowed: bool = False
    power: bool = False
    access: bool = False
    cost: float = Field(default=100, ge=0, le=1e6)
    windows: list[str] = Field(default_factory=lambda: ["steady-window"])


class Assumptions(Schema):
    steady: bool = False
    open_terrain: bool = False
    local_weather: bool = False
    constant_release_across_windows: bool = False
    note: str = Field(default="", max_length=2000)


class Settings(Schema):
    budget: float = Field(default=350, ge=0, le=1e6)
    equipment_limit: int = Field(default=2, ge=1, le=8)
    window: Literal["steady-window"] = "steady-window"
    noise_ug_m3: float = Field(default=2, ge=0.5, le=100)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    inference_limit: int = Field(default=128, ge=40, le=512)
    selection_seed: int = Field(default=0, ge=0, le=2**32 - 1)
    objective: Literal[
        "scenario_information", "spatial_coverage", "prediction_variance"
    ] = "scenario_information"
    met_direction_sd_deg: float = Field(default=20, ge=0.5, le=45)
    met_speed_fraction: float = Field(default=0.3, ge=0, le=0.5)
    met_uncertainty_provenance: str = Field(
        default="Unverified research assumption", max_length=1000
    )
    source_height_m: float = Field(default=5, ge=0, le=100)
    receptor_height_m: float = Field(default=2, ge=0, le=20)


class StudyWindow(Schema):
    id: str = Field(min_length=1, max_length=80)
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def aware_time(cls, value):
        return TimedPoint.timestamp_aware(value)

    @model_validator(mode="after")
    def bounded_period(self):
        duration = (
            datetime.fromisoformat(self.end) - datetime.fromisoformat(self.start)
        ).total_seconds()
        if not 0 < duration <= 3600:
            raise ValueError(
                "Each independently steady window must last between 0 and 3600 seconds"
            )
        return self


class ImportIssue(Schema):
    line: int = Field(ge=2)
    error: str = Field(max_length=1000)


class ImportSummary(Schema):
    total: int = Field(ge=0, le=10000)
    accepted: int = Field(ge=0, le=10000)
    invalid: int = Field(ge=0, le=10000)
    flagged: int = Field(ge=0, le=10000)
    synthetic_rows: int = Field(default=0, ge=0, le=10000)
    issues: list[ImportIssue] = Field(max_length=10000)

    @model_validator(mode="after")
    def consistent_counts(self):
        if (
            self.accepted + self.invalid != self.total
            or self.flagged > self.accepted
            or self.synthetic_rows > self.accepted
        ):
            raise ValueError("Inconsistent import quality counts")
        return self


class ImportRecord(Schema):
    id: str
    filename: str = Field(max_length=200)
    kind: Literal["measurements", "weather"]
    sha256: str
    raw_csv: str = Field(max_length=2_000_000)
    timezone: str
    column_mapping: dict[str, str] = Field(default_factory=dict)
    summary: dict
    transformations: list[str]

    @field_validator("summary")
    @classmethod
    def valid_summary(cls, value):
        return ImportSummary.model_validate(value).model_dump()

    @model_validator(mode="after")
    def raw_hash_matches(self):
        import hashlib

        if len(self.raw_csv.encode()) > 2_000_000:
            raise ValueError("Archived raw CSV exceeds 2 MB UTF-8 byte limit")
        if hashlib.sha256(self.raw_csv.encode()).hexdigest() != self.sha256:
            raise ValueError("Raw CSV SHA256 does not match archived provenance")
        return self


class Observation(TimedPoint):
    timestamp: str
    note: str = Field(min_length=1, max_length=2000)
    approximate: bool = True


class ArchivedPlan(Schema):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    method: str
    site_ids: list[str]
    cost: float = Field(ge=0)
    # Numerical mutual-information integration can have a small negative estimate.
    # Preserve it with its diagnostics instead of clipping archived evidence.
    score: float
    equipment: int = Field(ge=0, le=8)
    window: str


class ArchivedAnalysis(Schema):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    input_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: Literal["ok", "infeasible", "insufficient_data", "uninformative"]
    plans: list[ArchivedPlan]


class Investigation(Schema):
    id: str = Field(default="", max_length=80, pattern=r"^[a-zA-Z0-9_-]*$")
    name: str = Field(default="Untitled investigation", min_length=1, max_length=120)
    concern: str = Field(default="", max_length=4000)
    objective: str = Field(default="Find useful next monitoring sites", max_length=2000)
    area: list[float] = Field(
        default_factory=lambda: [-0.02, -0.02, 0.02, 0.02], min_length=4, max_length=4
    )
    synthetic: bool = False
    measurements: list[Measurement] = Field(default_factory=list, max_length=10000)
    weather: list[Weather] = Field(default_factory=list, max_length=10000)
    study_windows: list[StudyWindow] = Field(default_factory=list, max_length=6)
    sites: list[Site] = Field(default_factory=list, max_length=100)
    source_locations: list[Point] = Field(default_factory=list, max_length=25)
    assumptions: Assumptions = Field(default_factory=Assumptions)
    settings: Settings = Field(default_factory=Settings)
    imports: list[ImportRecord] = Field(default_factory=list, max_length=20)
    observations: list[Observation] = Field(default_factory=list, max_length=500)
    instruments: dict[str, str] = Field(default_factory=dict)
    result: dict | None = None
    plan_history: list[dict] = Field(default_factory=list, max_length=30)
    archived_results: list[dict] = Field(default_factory=list)
    compatibility_notes: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("plan_history")
    @classmethod
    def validate_archived_results(cls, value):
        return [ArchivedAnalysis.model_validate(row).model_dump() for row in value]

    @model_validator(mode="after")
    def valid_bounds(self):
        west, south, east, north = self.area
        if not (-180 <= west < east <= 180 and -85 <= south < north <= 85):
            raise ValueError(
                "Area must be west,south,east,north; dateline crossing is unsupported"
            )
        if len({s.id for s in self.sites}) != len(self.sites):
            raise ValueError("Site IDs must be unique")
        windows = sorted(self.study_windows, key=lambda w: w.start)
        if windows:
            if len(windows) < 2 or len({w.id for w in windows}) != len(windows):
                raise ValueError(
                    "Campaigns require two to six uniquely identified steady windows"
                )
            if any(a.end >= b.start for a, b in zip(windows, windows[1:])):
                raise ValueError(
                    "Campaign steady windows must not overlap or share endpoints"
                )
            if (
                datetime.fromisoformat(windows[-1].end)
                - datetime.fromisoformat(windows[0].start)
            ).total_seconds() > 14 * 86400:
                raise ValueError("Campaign span cannot exceed 14 days")
        if any(r.origin == "synthetic" for r in [*self.measurements, *self.weather]):
            self.synthetic = True
        return self


class ImportRequest(Schema):
    csv: str = Field(max_length=2_000_000)
    filename: str = Field(default="import.csv", max_length=200)
    kind: Literal["measurements", "weather"] = "measurements"
    timezone: str = Field(default="", max_length=80)
    units: str = "ug/m3"
    mapping: dict[str, str] = Field(default_factory=dict)

    @field_validator("csv")
    @classmethod
    def csv_byte_limit(cls, value):
        if len(value.encode("utf-8")) > 2_000_000:
            raise ValueError("CSV exceeds 2 MB UTF-8 byte limit")
        return value


def migrate_analysis(inv):
    """Lossless read/import compatibility; persisted originals change on save only."""
    from .inference import MODEL_VERSION, PROTOCOL_VERSION

    if inv.result is not None and (
        inv.result.get("model_version") != MODEL_VERSION
        or inv.result.get("protocol_version") != PROTOCOL_VERSION
    ):
        inv.archived_results = [inv.result] + inv.archived_results
        previous_model = inv.result.get("model_version", "unknown")
        previous_protocol = inv.result.get("protocol_version", "unknown")
        inv.result = None
        note = (
            "Previous analysis archived: the stored model/protocol "
            f"({previous_model}/{previous_protocol}) differs from the current "
            f"{MODEL_VERSION}/{PROTOCOL_VERSION}. Rerun the current model; "
            "comparison metadata alone cannot verify calibration. Original "
            "observations and raw imports are retained."
        )
        if note not in inv.compatibility_notes:
            inv.compatibility_notes.append(note)
    return inv

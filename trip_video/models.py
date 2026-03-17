from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Asset:
    path: str
    kind: str
    selected: bool = True
    label: str = ""
    caption: str = ""


@dataclass
class TripProfile:
    title: str
    destination: str = ""
    duration_days: int | None = None
    summary: str = ""
    highlights: list[str] = field(default_factory=list)
    target_audience: str = ""
    hotel_level: str = ""
    transportation: str = ""
    price: str = ""
    tags: list[str] = field(default_factory=list)
    call_to_action: str = ""
    cover_text: str = ""
    sub_cover_text: str = ""
    hook: str = ""
    source_notes: list[str] = field(default_factory=list)


@dataclass
class ShotPlan:
    id: str
    image_path: str
    headline: str
    overlay_lines: list[str]
    narration: str
    subtitle: str
    duration: float = 4.0
    animation: str = "slow_zoom_in"


@dataclass
class RenderConfig:
    width: int = 1080
    height: int = 1920
    fps: int = 30
    voice: str = "coral"
    voice_model: str = "gpt-4o-mini-tts"
    voice_instructions: str = "Use energetic but trustworthy Mandarin Chinese suitable for a travel promotion."
    bgm_path: str = ""
    font_file: str = ""
    title_font_size: int = 72
    subtitle_font_size: int = 42
    bottom_margin: int = 180


@dataclass
class DraftDocument:
    version: str
    trip_slug: str
    trip_dir: str
    output_dir: str
    created_at: str
    trip_profile: TripProfile
    assets: list[Asset]
    shot_plan: list[ShotPlan]
    render_config: RenderConfig
    needs_review: bool = True
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generation_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DraftDocument":
        trip_profile = TripProfile(**data["trip_profile"])
        assets = [Asset(**item) for item in data.get("assets", [])]
        shot_plan = [ShotPlan(**item) for item in data.get("shot_plan", [])]
        render_config = RenderConfig(**data.get("render_config", {}))
        return cls(
            version=data["version"],
            trip_slug=data["trip_slug"],
            trip_dir=data["trip_dir"],
            output_dir=data["output_dir"],
            created_at=data["created_at"],
            trip_profile=trip_profile,
            assets=assets,
            shot_plan=shot_plan,
            render_config=render_config,
            needs_review=data.get("needs_review", True),
            missing_fields=data.get("missing_fields", []),
            warnings=data.get("warnings", []),
            generation_notes=data.get("generation_notes", []),
        )

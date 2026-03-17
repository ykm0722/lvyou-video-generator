from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .config import default_font_file, ensure_output_dir, env
from .models import Asset, DraftDocument, RenderConfig, ShotPlan, TripProfile
from .openai_api import OpenAIClient, file_data_url, responses_output_text
from .utils import (
    IMAGE_EXTENSIONS,
    PDF_EXTENSIONS,
    deep_merge,
    dump_json,
    extract_duration_days,
    load_json,
    normalize_whitespace,
    resolve_trip_dir,
    slugify,
    split_highlights,
    strip_title_noise,
    utc_now_iso,
)


DEFAULT_MODEL = "gpt-4o-mini"


def discover_assets(trip_dir: Path) -> tuple[list[Asset], list[Path], list[Path]]:
    images: list[Path] = []
    pdfs: list[Path] = []
    assets: list[Asset] = []
    for path in sorted(trip_dir.iterdir()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            images.append(path)
            assets.append(Asset(path=str(path), kind="image", label=path.name))
        elif suffix in PDF_EXTENSIONS:
            pdfs.append(path)
            assets.append(Asset(path=str(path), kind="pdf", label=path.name))
    return assets, images, pdfs


def load_meta(trip_dir: Path) -> dict[str, Any]:
    meta_path = trip_dir / "meta.json"
    if meta_path.exists():
        return load_json(meta_path)
    return {}


def heuristic_trip_profile(images: list[Path], pdfs: list[Path], meta: dict[str, Any]) -> tuple[TripProfile, list[str]]:
    source_name = pdfs[0].name if pdfs else (images[0].stem if images else "旅游线路")
    title = meta.get("title") or strip_title_noise(source_name)
    duration_days = meta.get("duration_days") or extract_duration_days(title)
    highlights = meta.get("highlights") or split_highlights(title)
    if not highlights:
        highlights = ["热门线路", "精选住宿", "轻松出游"]

    price = meta.get("price", "")
    target_audience = meta.get("target_audience", "适合想轻松度假、家庭同行、朋友结伴出游的人群")
    transportation = meta.get("transportation", "交通安排以最终线路说明为准")
    hotel_level = meta.get("hotel_level", "舒适型酒店")
    destination = meta.get("destination") or " / ".join(highlights[:2])
    summary = meta.get("summary") or f"{title}，主打{('、'.join(highlights[:3]))}，适合想省心出游的人群。"
    hook = meta.get("hook") or f"{destination}这条线路最近很适合出发"
    call_to_action = meta.get("call_to_action") or "想要轻松、省心、拍照出片的行程，这条线路可以直接收藏。"
    cover_text = meta.get("cover_text") or (destination or title)
    sub_cover_text = meta.get("sub_cover_text") or "精选线路"

    missing_fields: list[str] = []
    for field_name, value in {
        "price": price,
        "duration_days": duration_days,
        "destination": destination,
    }.items():
        if not value:
            missing_fields.append(field_name)

    profile = TripProfile(
        title=title,
        destination=destination,
        duration_days=duration_days,
        summary=summary,
        highlights=highlights,
        target_audience=target_audience,
        hotel_level=hotel_level,
        transportation=transportation,
        price=price,
        tags=meta.get("tags", highlights[:3]),
        call_to_action=call_to_action,
        cover_text=cover_text,
        sub_cover_text=sub_cover_text,
        hook=hook,
        source_notes=meta.get("source_notes", []),
    )
    return profile, missing_fields


def build_default_shot_plan(profile: TripProfile, images: list[Path], meta: dict[str, Any]) -> list[ShotPlan]:
    if not images:
        raise RuntimeError("No images were found in the trip directory.")

    highlights = profile.highlights or ["精选线路", "轻松玩法", "舒适出行"]
    base_lines = [
        [profile.destination or profile.title, highlights[0], profile.price or "行程细节可确认"],
        [highlights[min(1, len(highlights) - 1)], profile.hotel_level or "舒适酒店", "适合轻松度假"],
        [highlights[min(2, len(highlights) - 1)], profile.transportation or "省心交通", profile.target_audience or "适合家庭/朋友同行"],
        [profile.title, "安排更省心", profile.call_to_action or "喜欢这条线路就先收藏"],
    ]

    shots: list[ShotPlan] = []
    image_cycle = images if len(images) >= 4 else images * (4 // len(images) + 1)
    count = min(max(len(images), 4), 6)
    for index in range(count):
        overlay_lines = [line for line in base_lines[index % len(base_lines)] if line]
        if index == 0:
            headline = profile.hook or profile.title
            narration = f"{profile.hook or profile.title}。{profile.summary}"
        elif index == count - 1:
            headline = "现在就收藏"
            narration = profile.call_to_action or "这条线路适合想轻松出游的人，喜欢就先收藏。"
        else:
            headline = overlay_lines[0]
            narration = "，".join(overlay_lines) + "。"
        shots.append(
            ShotPlan(
                id=f"shot-{index + 1}",
                image_path=str(image_cycle[index]),
                headline=headline,
                overlay_lines=overlay_lines[:3],
                narration=meta.get("narration_overrides", {}).get(f"shot-{index + 1}", narration),
                subtitle=narration,
                duration=4.0,
                animation=["slow_zoom_in", "slow_zoom_out", "pan_left", "pan_right"][index % 4],
            )
        )
    return shots


def extract_json_object(text: str) -> dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    candidate = fenced.group(1) if fenced else text.strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise ValueError("Model response did not contain a JSON object.")
    return json.loads(candidate[start : end + 1])


def ai_generate_draft(
    client: OpenAIClient,
    trip_dir: Path,
    images: list[Path],
    pdfs: list[Path],
    meta: dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    input_content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": (
                "You are generating structured Chinese travel short-video data for a WeChat Channels style vertical promo. "
                "Return JSON only. Keep copy punchy, commercial, and concise. "
                "If a field is uncertain, leave it empty and include it in missing_fields. "
                "Use the schema keys exactly: trip_profile, shot_plan, missing_fields, warnings. "
                "trip_profile fields: title, destination, duration_days, summary, highlights, target_audience, "
                "hotel_level, transportation, price, tags, call_to_action, cover_text, sub_cover_text, hook, source_notes. "
                "shot_plan is an array of 4 to 6 shots. Every shot needs: id, headline, overlay_lines, narration, subtitle, duration, animation. "
                "overlay_lines should be 2 to 3 short Chinese phrases. duration should be a number between 3.5 and 5.5."
            ),
        }
    ]
    for pdf in pdfs[:2]:
        input_content.append(
            {
                "type": "input_file",
                "filename": pdf.name,
                "file_data": file_data_url(pdf),
            }
        )
    for image in images[:6]:
        input_content.append(
            {
                "type": "input_image",
                "image_url": file_data_url(image),
            }
        )
    if meta:
        input_content.append(
            {
                "type": "input_text",
                "text": "Operator hints in JSON:\n" + json.dumps(meta, ensure_ascii=False, indent=2),
            }
        )

    response = client.responses_create(
        model=model,
        instructions="Prefer Mandarin Chinese output. Do not invent specific price or hotel star level unless supported.",
        input_items=[{"role": "user", "content": input_content}],
    )
    output_text = responses_output_text(response)
    return extract_json_object(output_text)


def normalize_ai_payload(
    payload: dict[str, Any],
    images: list[Path],
    fallback_profile: TripProfile,
    fallback_missing_fields: list[str],
) -> tuple[TripProfile, list[ShotPlan], list[str], list[str]]:
    profile_payload = payload.get("trip_profile") or {}
    merged_profile = {
        **fallback_profile.__dict__,
        **profile_payload,
    }
    profile = TripProfile(**merged_profile)
    shots_payload = payload.get("shot_plan") or []
    shots: list[ShotPlan] = []
    image_cycle = images if images else [Path("")]
    for index, item in enumerate(shots_payload[:6]):
        image_path = item.get("image_path") or str(image_cycle[index % len(image_cycle)])
        shots.append(
            ShotPlan(
                id=item.get("id") or f"shot-{index + 1}",
                image_path=image_path,
                headline=item.get("headline") or profile.title,
                overlay_lines=item.get("overlay_lines") or [profile.destination or profile.title],
                narration=item.get("narration") or item.get("subtitle") or profile.summary,
                subtitle=item.get("subtitle") or item.get("narration") or profile.summary,
                duration=float(item.get("duration") or 4.0),
                animation=item.get("animation") or "slow_zoom_in",
            )
        )
    if not shots:
        shots = build_default_shot_plan(profile, images, {})
    return profile, shots, payload.get("missing_fields") or fallback_missing_fields, payload.get("warnings") or []


def draft_paths(trip_dir: Path) -> tuple[Path, Path]:
    slug = slugify(trip_dir.name)
    output_dir = ensure_output_dir() / slug
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / "draft.json", output_dir / "review-data.json"


def create_draft(
    trip_dir_input: str,
    model: str = DEFAULT_MODEL,
    skip_ai: bool = False,
    voice: str = "",
) -> DraftDocument:
    trip_dir = resolve_trip_dir(trip_dir_input)
    assets, images, pdfs = discover_assets(trip_dir)
    meta = load_meta(trip_dir)
    profile, missing_fields = heuristic_trip_profile(images, pdfs, meta)
    shots = build_default_shot_plan(profile, images, meta)
    warnings: list[str] = []
    notes: list[str] = []

    client = OpenAIClient()
    if skip_ai:
        notes.append("AI analysis skipped by request.")
    elif client.enabled and (images or pdfs):
        try:
            ai_payload = ai_generate_draft(client, trip_dir, images, pdfs, meta, model=model)
            profile, shots, missing_fields, ai_warnings = normalize_ai_payload(
                ai_payload, images, profile, missing_fields
            )
            warnings.extend(ai_warnings)
            notes.append(f"AI draft generated with model {model}.")
        except Exception as exc:
            warnings.append(f"AI draft generation failed: {exc}")
            notes.append("Used heuristic fallback after AI failure.")
    else:
        notes.append("OPENAI_API_KEY missing, used heuristic draft generation.")

    config = RenderConfig(
        voice=voice or env("DEFAULT_TTS_VOICE", "coral"),
        bgm_path=env("DEFAULT_BGM_PATH", ""),
        font_file=env("DEFAULT_FONT_FILE", default_font_file()),
    )

    slug = slugify(trip_dir.name)
    output_dir = ensure_output_dir() / slug
    output_dir.mkdir(parents=True, exist_ok=True)
    draft = DraftDocument(
        version="1.0",
        trip_slug=slug,
        trip_dir=str(trip_dir),
        output_dir=str(output_dir),
        created_at=utc_now_iso(),
        trip_profile=profile,
        assets=assets,
        shot_plan=shots,
        render_config=config,
        needs_review=True,
        missing_fields=missing_fields,
        warnings=warnings,
        generation_notes=notes,
    )

    draft_path, review_path = draft_paths(trip_dir)
    dump_json(draft_path, draft.to_dict())
    if not review_path.exists():
        dump_json(review_path, draft.to_dict())
    return draft


def load_review_document(trip_dir_input: str) -> DraftDocument:
    trip_dir = resolve_trip_dir(trip_dir_input)
    draft_path, review_path = draft_paths(trip_dir)
    source = review_path if review_path.exists() else draft_path
    if not source.exists():
        raise FileNotFoundError("Draft not found. Run `./generate draft <trip_dir>` first.")
    return DraftDocument.from_dict(load_json(source))


def save_review_document(document: DraftDocument) -> Path:
    _, review_path = draft_paths(Path(document.trip_dir))
    dump_json(review_path, document.to_dict())
    return review_path


def merge_review_update(document: DraftDocument, update: dict[str, Any]) -> DraftDocument:
    merged = deep_merge(document.to_dict(), update)
    merged["needs_review"] = False
    return DraftDocument.from_dict(merged)

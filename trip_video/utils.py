from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 获取FFprobe路径
try:
    from imageio_ffmpeg import get_ffmpeg_exe
    FFMPEG_PATH = get_ffmpeg_exe()
    # imageio-ffmpeg只提供ffmpeg，用ffmpeg获取时长
    FFPROBE_PATH = FFMPEG_PATH
except ImportError:
    FFPROBE_PATH = "ffprobe"  # fallback到系统ffprobe


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PDF_EXTENSIONS = {".pdf"}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "trip"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )


def probe_duration(path: Path) -> float:
    try:
        # 尝试使用ffprobe
        result = run_command(
            [
                FFPROBE_PATH if FFPROBE_PATH != FFMPEG_PATH else "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ]
        )
        output = result.stdout.strip()
        if output == 'N/A' or not output:
            return 0.0
        return float(output)
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        # 如果ffprobe不可用，尝试用ffmpeg
        try:
            result = run_command(
                [
                    FFMPEG_PATH,
                    "-i",
                    str(path),
                    "-f",
                    "null",
                    "-"
                ]
            )
            # 从stderr中提取时长
            import re
            match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", result.stderr)
            if match:
                h, m, s = match.groups()
                return int(h) * 3600 + int(m) * 60 + float(s)
        except:
            pass
        return 0.0


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_duration_days(text: str) -> int | None:
    match = re.search(r"(\d+)\s*日", text)
    return int(match.group(1)) if match else None


def strip_title_noise(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"^\[.*?\]|^【.*?】", "", stem)
    stem = stem.replace("~", " ").replace("_", " ").replace("-", " ")
    return normalize_whitespace(stem)


def split_highlights(text: str) -> list[str]:
    parts = re.split(r"[~、,，/ ]+", text)
    results = []
    for part in parts:
        part = normalize_whitespace(part)
        if part and part not in results and len(part) <= 12:
            results.append(part)
    return results[:4]


def resolve_trip_dir(input_path: str) -> Path:
    path = Path(input_path).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Trip directory not found: {path}")
    return path

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

from .models import DraftDocument, ShotPlan
from .openai_api import OpenAIClient
from .utils import dump_json, probe_duration


def ffmpeg(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", "-y", *args], capture_output=True)
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr.decode()}", file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stderr)


def shell_quote_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def animation_filter(animation: str, width: int, height: int, fps: int, duration: float) -> str:
    frames = max(int(math.ceil(duration * fps)), 1)
    base = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    if animation == "slow_zoom_out":
        return f"{base},zoompan=z='if(lte(zoom,1.0),1.12,max(1.0,zoom-0.0012))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}"
    if animation == "pan_left":
        return f"{base},zoompan=z='1.08':x='max(0,iw-iw/zoom-(on/{frames})*(iw-iw/zoom))':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}"
    if animation == "pan_right":
        return f"{base},zoompan=z='1.08':x='(on/{frames})*(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}"
    return f"{base},zoompan=z='min(zoom+0.0012,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={fps}"


def prepare_text_file(path: Path, lines: list[str] | str) -> Path:
    text = lines if isinstance(lines, str) else "\n".join(lines)
    path.write_text(text.strip(), encoding="utf-8")
    return path


def generate_tts(client: OpenAIClient, document: DraftDocument, shot: ShotPlan, output_path: Path) -> Path | None:
    # 临时禁用 TTS - Edge TTS 在 Render 上被封禁
    print(f"TTS disabled for {shot.id}, generating video without narration", file=sys.stderr)
    return None


def render_shot(document: DraftDocument, shot: ShotPlan, temp_dir: Path, index: int) -> Path:
    image_path = Path(shot.image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Shot image not found: {image_path}")

    title_file = prepare_text_file(temp_dir / f"title-{index}.txt", shot.headline)
    subtitle_file = prepare_text_file(temp_dir / f"subtitle-{index}.txt", shot.subtitle)
    badges_file = prepare_text_file(temp_dir / f"badges-{index}.txt", shot.overlay_lines[:3])

    client = OpenAIClient()
    audio_path = generate_tts(client, document, shot, temp_dir / f"voice-{index}.mp3")
    duration = shot.duration
    has_audio = bool(audio_path and audio_path.exists())
    if has_audio:
        duration = max(duration, probe_duration(audio_path))

    width = document.render_config.width
    height = document.render_config.height
    fps = document.render_config.fps
    font = document.render_config.font_file
    title_style = (
        f"drawtext=fontfile='{shell_quote_filter_path(Path(font))}':textfile='{shell_quote_filter_path(title_file)}':"
        f"fontcolor=0xF8E8C5:fontsize={document.render_config.title_font_size}:line_spacing=10:"
        "box=1:boxcolor=0x411E0B@0.36:boxborderw=18:"
        f"x=(w-text_w)/2:y=h*0.20"
        if font
        else ""
    )
    badges_style = (
        f"drawtext=fontfile='{shell_quote_filter_path(Path(font))}':textfile='{shell_quote_filter_path(badges_file)}':"
        "fontcolor=white:fontsize=50:line_spacing=16:box=1:boxcolor=0xA6401B@0.60:boxborderw=18:"
        "x=w*0.10:y=h*0.60"
        if font
        else ""
    )
    subtitle_style = (
        f"drawtext=fontfile='{shell_quote_filter_path(Path(font))}':textfile='{shell_quote_filter_path(subtitle_file)}':"
        f"fontcolor=white:fontsize={document.render_config.subtitle_font_size}:line_spacing=12:box=1:"
        "boxcolor=0x101010@0.45:boxborderw=18:x=(w-text_w)/2:"
        f"y=h-{document.render_config.bottom_margin}"
        if font
        else ""
    )
    draw_filters = ",".join(filter(None, [animation_filter(shot.animation, width, height, fps, duration), subtitle_style]))
    clip_path = temp_dir / f"clip-{index}.mp4"
    args = [
        "-loop",
        "1",
        "-t",
        f"{duration:.2f}",
        "-i",
        str(image_path),
    ]
    if has_audio:
        args.extend(["-i", str(audio_path)])
    else:
        args.extend(["-f", "lavfi", "-t", f"{duration:.2f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])
    args.extend(
        [
            "-vf",
            draw_filters,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            "-r",
            str(fps),
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(clip_path),
        ]
    )
    ffmpeg(args)
    return clip_path


def concat_clips(clips: list[Path], concat_file: Path, output_video: Path) -> Path:
    lines = []
    for path in clips:
        escaped = str(path).replace("'", r"'\''")
        lines.append(f"file '{escaped}'")
    concat_file.write_text("\n".join(lines), encoding="utf-8")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output_video)])
    return output_video


def mix_bgm(input_video: Path, bgm_path: Path, output_video: Path) -> Path:
    ffmpeg(
        [
            "-i",
            str(input_video),
            "-stream_loop",
            "-1",
            "-i",
            str(bgm_path),
            "-filter_complex",
            "[0:a]volume=1.0[a0];[1:a]volume=0.18[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map",
            "0:v:0",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_video),
        ]
    )
    return output_video


def render_cover(document: DraftDocument, output_path: Path) -> Path:
    first_image = Path(document.shot_plan[0].image_path)
    temp_dir = output_path.parent / ".cover"
    temp_dir.mkdir(parents=True, exist_ok=True)
    title_file = prepare_text_file(temp_dir / "cover-title.txt", document.trip_profile.cover_text or document.trip_profile.title)
    sub_file = prepare_text_file(temp_dir / "cover-sub.txt", document.trip_profile.sub_cover_text or "精选线路")
    font = document.render_config.font_file
    draw = animation_filter("slow_zoom_in", document.render_config.width, document.render_config.height, 1, 1.0)
    if font:
        draw += "," + (
            f"drawtext=fontfile='{shell_quote_filter_path(Path(font))}':textfile='{shell_quote_filter_path(title_file)}':"
            "fontcolor=0xF8E8C5:fontsize=92:box=1:boxcolor=0x5C2412@0.56:boxborderw=24:x=(w-text_w)/2:y=h*0.25"
        )
        draw += "," + (
            f"drawtext=fontfile='{shell_quote_filter_path(Path(font))}':textfile='{shell_quote_filter_path(sub_file)}':"
            "fontcolor=white:fontsize=52:box=1:boxcolor=0x101010@0.42:boxborderw=18:x=(w-text_w)/2:y=h*0.75"
        )
    ffmpeg(
        [
            "-loop",
            "1",
            "-t",
            "1",
            "-i",
            str(first_image),
            "-vf",
            draw,
            "-frames:v",
            "1",
            str(output_path),
        ]
    )
    return output_path


def render_video(document: DraftDocument) -> dict[str, str]:
    output_dir = Path(document.output_dir)
    temp_dir = output_dir / ".render"
    temp_dir.mkdir(parents=True, exist_ok=True)
    clips = [render_shot(document, shot, temp_dir, index) for index, shot in enumerate(document.shot_plan)]
    base_video = concat_clips(clips, temp_dir / "concat.txt", output_dir / "final-base.mp4")
    final_video = output_dir / "final.mp4"
    bgm_path = Path(document.render_config.bgm_path) if document.render_config.bgm_path else None
    if bgm_path and bgm_path.exists():
        mix_bgm(base_video, bgm_path, final_video)
    else:
        if final_video.exists():
            final_video.unlink()
        base_video.replace(final_video)
    cover_path = render_cover(document, output_dir / "cover.jpg")
    script_path = output_dir / "script.json"
    dump_json(script_path, document.to_dict())
    return {
        "video": str(final_video),
        "cover": str(cover_path),
        "script": str(script_path),
    }

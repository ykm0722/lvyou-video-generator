from fastapi import APIRouter, HTTPException
import sys
import os
import requests
import threading
import uuid
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from trip_video.render import render_video
from trip_video.models import DraftDocument, TripProfile, ShotPlan, RenderConfig, Asset

router = APIRouter()

# In-memory task storage for async video generation
_tasks: dict[str, dict] = {}

MAX_SCENES = 5


def transform_api_to_document(script: dict, image_paths: list[str], output_dir: str,
                               copy_data: dict = None, travel_info: dict = None):
    """Transform API input to FFmpeg renderer format"""
    title = script.get('title', 'Travel Promo')
    scenes = script.get('scenes', [])

    if not scenes:
        raise ValueError("No scenes in script")

    # Limit scenes to reduce render time
    scenes = scenes[:MAX_SCENES]

    selling_points = []
    if copy_data:
        selling_points = copy_data.get('points', [])[:3]

    destination = ''
    highlights = []
    if travel_info:
        destination = travel_info.get('destination', '')
        highlights = travel_info.get('highlights', [])

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bundled_font = os.path.join(base_dir, 'resource', 'fonts', 'wqy-microhei.ttc')

    font_candidates = [
        bundled_font,  # First bundled
        '/System/Library/Fonts/STHeiti Medium.ttc',  # macOS
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # Linux
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux fallback
    ]
    font_file = next((f for f in font_candidates if os.path.exists(f)), font_candidates[-1])

    animations = ['slow_zoom_in', 'slow_zoom_out', 'pan_left', 'pan_right']

    shot_plan = []
    for idx, scene in enumerate(scenes):
        image_path = image_paths[idx % len(image_paths)]

        text = scene.get('text', '')
        duration = scene.get('duration', 3.0)

        if '\n' in text:
            lines = text.split('\n')
            headline = lines[0][:25]
            overlay_lines = [line.strip() for line in lines[1:3] if line.strip()]
        else:
            headline = text[:25]
            overlay_lines = selling_points[idx:idx+2] if idx < len(selling_points) else []

        narration = text
        subtitle = text[:40]

        shot_plan.append(ShotPlan(
            id=f'shot-{idx}',
            image_path=image_path,
            headline=headline,
            overlay_lines=overlay_lines,
            narration=narration,
            subtitle=subtitle,
            duration=duration,
            animation=animations[idx % len(animations)]
        ))

    return DraftDocument(
        version='1.0',
        trip_slug='api-video',
        trip_dir=output_dir,
        output_dir=output_dir,
        created_at=datetime.now().isoformat(),
        trip_profile=TripProfile(
            title=title,
            destination=destination,
            highlights=highlights
        ),
        assets=[Asset(path=p, kind='image', selected=True) for p in image_paths],
        shot_plan=shot_plan,
        render_config=RenderConfig(
            width=540,
            height=960,
            fps=15,
            font_file=font_file,
            bgm_path='',
            voice='coral',
            voice_model='gpt-4o-mini-tts'
        )
    )


def _render_task(task_id: str, document: DraftDocument, temp_dir: str):
    """Background render worker"""
    try:
        result = render_video(document)

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"video_{timestamp}.mp4"
        unique_path = os.path.join(temp_dir, unique_filename)

        if os.path.exists(result['video']):
            os.rename(result['video'], unique_path)

        _tasks[task_id] = {
            "status": "done",
            "path": f"/uploads/{unique_filename}",
        }
    except Exception as e:
        import traceback
        error_detail = f"Render failed: {str(e)}\n{traceback.format_exc()}"
        print(error_detail, file=sys.stderr)
        _tasks[task_id] = {
            "status": "error",
            "detail": str(e),
        }


@router.post("/video/generate")
async def generate_video(data: dict):
    """Start async video generation, return task_id immediately"""
    try:
        script = data.get('script', {})
        images = data.get('images', [])
        copy_data = data.get('copyData')
        travel_info = data.get('travelInfo')

        if not images or len(images) == 0:
            raise HTTPException(status_code=400, detail="No images available")

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        temp_dir = os.path.join(base_dir, 'uploads')
        os.makedirs(temp_dir, exist_ok=True)

        # Download images
        image_paths = []
        for idx, img_data in enumerate(images):
            image_url = img_data.get('url', '')
            image_filename = f"img_{idx}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            image_path = os.path.join(temp_dir, image_filename)

            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            if len(response.content) < 1000 or not response.headers.get('content-type', '').startswith('image/'):
                raise ValueError(f"Invalid image from {image_url}")
            with open(image_path, 'wb') as f:
                f.write(response.content)
            image_paths.append(image_path)

        document = transform_api_to_document(
            script, image_paths, temp_dir,
            copy_data=copy_data,
            travel_info=travel_info
        )

        # Create task and start background render
        task_id = str(uuid.uuid4())[:8]
        _tasks[task_id] = {"status": "pending"}

        thread = threading.Thread(
            target=_render_task,
            args=(task_id, document, temp_dir),
            daemon=True
        )
        thread.start()

        return {"status": "accepted", "task_id": task_id}
    except Exception as e:
        import traceback
        error_detail = f"Video generation failed: {str(e)}\n{traceback.format_exc()}"
        print(error_detail, file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")


@router.get("/video/status/{task_id}")
async def get_video_status(task_id: str):
    """Poll for video generation status"""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

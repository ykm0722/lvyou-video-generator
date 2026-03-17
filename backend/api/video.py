from fastapi import APIRouter, HTTPException
import sys
import os
import requests
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from trip_video.render import render_video
from trip_video.models import DraftDocument, TripProfile, ShotPlan, RenderConfig, Asset

router = APIRouter()

def transform_api_to_document(script: dict, image_paths: list[str], output_dir: str,
                               copy_data: dict = None, travel_info: dict = None):
    """将 API 输入转换为 FFmpeg 渲染器格式，充分利用所有数据"""
    title = script.get('title', '精品旅游')
    scenes = script.get('scenes', [])

    if not scenes:
        raise ValueError("脚本中没有场景内容")

    # 获取爆款文案卖点
    selling_points = []
    if copy_data:
        selling_points = copy_data.get('points', [])[:3]

    # 获取目的地和景点信息
    destination = ''
    highlights = []
    if travel_info:
        destination = travel_info.get('destination', '')
        highlights = travel_info.get('highlights', [])

    animations = ['slow_zoom_in', 'slow_zoom_out', 'pan_left', 'pan_right']

    shot_plan = []
    for idx, scene in enumerate(scenes):
        image_path = image_paths[idx % len(image_paths)]

        text = scene.get('text', '')
        duration = scene.get('duration', 4.0)

        # 智能拆分文字：标题 + 卖点
        if '\n' in text:
            lines = text.split('\n')
            headline = lines[0][:25]  # 增加到25字
            overlay_lines = [line.strip() for line in lines[1:3] if line.strip()]
        else:
            headline = text[:25]  # 增加到25字
            overlay_lines = selling_points[idx:idx+2] if idx < len(selling_points) else []

        # 旁白和字幕保持一致
        narration = text
        subtitle = text[:40]  # 增加到40字

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
            width=1080,
            height=1920,
            fps=30,
            font_file='/System/Library/Fonts/STHeiti Medium.ttc',
            bgm_path='',
            voice='coral',
            voice_model='gpt-4o-mini-tts'
        )
    )

@router.post("/video/generate")
async def generate_video(data: dict):
    """生成推广视频"""
    try:
        script = data.get('script', {})
        images = data.get('images', [])
        copy_data = data.get('copyData')
        travel_info = data.get('travelInfo')

        if not images or len(images) == 0:
            raise HTTPException(status_code=400, detail="没有可用的图片")

        temp_dir = '/Users/yuekuoming/lvyou/backend/uploads'
        os.makedirs(temp_dir, exist_ok=True)

        # 下载所有图片
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

        # 转换数据格式并渲染
        document = transform_api_to_document(
            script, image_paths, temp_dir,
            copy_data=copy_data,
            travel_info=travel_info
        )

        # 检查 TTS 配置
        if not os.getenv('OPENAI_API_KEY'):
            print("⚠️  提示：设置 OPENAI_API_KEY 环境变量可启用 TTS 旁白")

        result = render_video(document)

        # 生成唯一文件名并重命名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"video_{timestamp}.mp4"
        unique_path = os.path.join(temp_dir, unique_filename)

        # 重命名生成的视频文件
        if os.path.exists(result['video']):
            os.rename(result['video'], unique_path)

        return {"status": "success", "path": f"/uploads/{unique_filename}"}
    except Exception as e:
        import traceback
        error_detail = f"视频生成失败: {str(e)}\n{traceback.format_exc()}"
        print(error_detail, file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"视频生成失败: {str(e)}")

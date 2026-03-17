from fastapi import APIRouter
import sys
sys.path.append('..')
from copywriter import ViralCopyGenerator

router = APIRouter()
copywriter = ViralCopyGenerator()

@router.post("/copywriter/generate")
async def generate_copy(travel_info: dict):
    """生成爆火文案"""
    copy_data = copywriter.generate_video_copy(travel_info)
    return copy_data

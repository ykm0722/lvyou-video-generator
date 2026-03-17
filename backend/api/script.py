from fastapi import APIRouter
from services.script_gen import ScriptGenerator

router = APIRouter()
script_gen = ScriptGenerator()

@router.post("/script/generate")
async def generate_script(travel_info: dict, copy_data: dict):
    """生成分镜头脚本"""
    script = script_gen.generate_storyboard(travel_info, copy_data)
    return script

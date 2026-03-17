from fastapi import APIRouter
from services.image_search import ImageSearchService

router = APIRouter()
search_service = ImageSearchService()

@router.get("/images/search")
async def search_images(keyword: str, count: int = 5):
    """搜索景点高清图片"""
    images = search_service.search_images(keyword, count)
    return {"images": images}

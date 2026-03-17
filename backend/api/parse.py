from fastapi import APIRouter
from pydantic import BaseModel
import sys
sys.path.append('..')
from pdf_parser import TravelPDFParser

router = APIRouter()

class ParseRequest(BaseModel):
    filepath: str

@router.post("/parse")
async def parse_pdf(request: ParseRequest):
    """解析PDF提取旅游信息"""
    parser = TravelPDFParser()
    info = parser.extract_info(request.filepath)
    return info

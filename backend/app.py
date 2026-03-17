from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sys
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(title="旅游视频生成API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

from api import upload, parse, images, script, video, copywriter

app.include_router(upload.router, prefix="/api")
app.include_router(parse.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(script.router, prefix="/api")
app.include_router(video.router, prefix="/api")
app.include_router(copywriter.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "旅游视频生成API服务"}

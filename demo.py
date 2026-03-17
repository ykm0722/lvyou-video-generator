#!/usr/bin/env python3
"""演示视频生成（不需要API key）"""
from pdf_parser import TravelPDFParser
from video_generator import PromoVideoGenerator
import os

# 解析PDF
parser = TravelPDFParser()
info = parser.extract_info("resource/【重渡沟】天河大峡谷-双卧7日~高端康养旅居.pdf")

print("=== 提取的信息 ===")
print(f"目的地: {info['destination']}")
print(f"景点: {', '.join(info['highlights'])}")
print(f"酒店: {info['hotel_level']}")

# 模拟文案数据
copy_data = {
    'title': '洛阳康养7日游',
    'points': [
        '重渡沟+天河大峡谷',
        '四星酒店全程入住',
        '100%纯玩0购物',
        '门票表演全含'
    ]
}

print("\n=== 生成视频 ===")
print(f"标题: {copy_data['title']}")
print(f"卖点: {copy_data['points']}")

# 生成视频
os.makedirs('output', exist_ok=True)
video_gen = PromoVideoGenerator()
video_gen.generate_video(
    "resource/微信图片_2026-03-09_194743_741.jpg",
    copy_data,
    "output/demo_video.mp4"
)

print("\n✅ 视频生成完成: output/demo_video.mp4")

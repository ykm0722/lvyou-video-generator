#!/usr/bin/env python3
"""测试PDF解析功能"""
from pdf_parser import TravelPDFParser

parser = TravelPDFParser()
info = parser.extract_info("resource/【重渡沟】天河大峡谷-双卧7日~高端康养旅居.pdf")

print("=== PDF解析结果 ===")
print(f"目的地: {info['destination']}")
print(f"行程: {info['duration']}")
print(f"酒店: {info['hotel_level']}")
print(f"景点亮点: {', '.join(info['highlights'][:5])}")
print(f"特色服务: {info['features'][:2]}")

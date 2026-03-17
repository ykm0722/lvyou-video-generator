#!/usr/bin/env python3
"""测试部署后的完整视频生成流程"""
import requests
import json
import time

API_BASE = "https://lvyou-video-generator.onrender.com"

def test_api():
    print("🚀 开始测试部署的API...")

    # 1. 测试根路径
    print("\n1️⃣ 测试根路径...")
    resp = requests.get(f"{API_BASE}/")
    print(f"   状态码: {resp.status_code}")
    if resp.status_code == 200:
        print(f"   响应: {resp.json()}")

    # 2. 模拟旅游信息（通常来自PDF解析）
    print("\n2️⃣ 准备测试数据...")
    travel_info = {
        "destination": "重渡沟",
        "duration": "7天6晚",
        "highlights": ["天河大峡谷", "竹海", "瀑布群", "农家乐", "山水风光"],
        "price": "2980元"
    }
    print(f"   目的地: {travel_info['destination']}")

    # 3. 测试文案生成
    print("\n3️⃣ 测试文案生成...")
    resp = requests.post(
        f"{API_BASE}/api/copywriter/generate",
        json=travel_info,
        timeout=30
    )
    print(f"   状态码: {resp.status_code}")
    if resp.status_code == 200:
        copy_data = resp.json()
        print(f"   标题: {copy_data.get('title', '')[:50]}...")
        print(f"   卖点数量: {len(copy_data.get('points', []))}")
    else:
        print(f"   ❌ 失败: {resp.text}")
        return False

    # 4. 测试图片搜索
    print("\n4️⃣ 测试图片搜索...")
    resp = requests.get(
        f"{API_BASE}/api/images/search",
        params={"keyword": "重渡沟 天河大峡谷", "count": 3},
        timeout=30
    )
    print(f"   状态码: {resp.status_code}")
    if resp.status_code == 200:
        images_data = resp.json()
        images = images_data.get('images', [])
        print(f"   找到图片数量: {len(images)}")
        if len(images) > 0:
            print(f"   第一张图片URL: {images[0].get('url', '')[:60]}...")
    else:
        print(f"   ❌ 失败: {resp.text}")
        return False

    # 5. 测试脚本生成
    print("\n5️⃣ 测试脚本生成...")
    script_input = {
        "travel_info": travel_info,
        "copy_data": copy_data
    }
    resp = requests.post(
        f"{API_BASE}/api/script/generate",
        json=script_input,
        timeout=30
    )
    print(f"   状态码: {resp.status_code}")
    if resp.status_code == 200:
        script = resp.json()
        print(f"   场景数量: {len(script.get('scenes', []))}")
    else:
        print(f"   ❌ 失败: {resp.text}")
        return False

    # 6. 测试视频生成（这是关键测试）
    print("\n6️⃣ 测试视频生成...")
    print("   ⏳ 这可能需要1-2分钟...")
    video_input = {
        "script": script,
        "images": images[:6],  # 最多6张图片
        "copyData": copy_data,
        "travelInfo": travel_info
    }

    try:
        resp = requests.post(
            f"{API_BASE}/api/video/generate",
            json=video_input,
            timeout=180  # 3分钟超时
        )
        print(f"   状态码: {resp.status_code}")

        if resp.status_code == 200:
            result = resp.json()
            video_path = result.get('path', '')
            print(f"   ✅ 视频生成成功!")
            print(f"   视频路径: {video_path}")
            print(f"   完整URL: {API_BASE}{video_path}")

            # 验证视频文件是否可访问
            print("\n7️⃣ 验证视频文件...")
            video_resp = requests.head(f"{API_BASE}{video_path}", timeout=10)
            print(f"   视频文件状态码: {video_resp.status_code}")
            if video_resp.status_code == 200:
                print(f"   ✅ 视频文件可访问!")
                return True
            else:
                print(f"   ❌ 视频文件无法访问")
                return False
        else:
            print(f"   ❌ 视频生成失败")
            print(f"   错误信息: {resp.text}")
            return False

    except requests.Timeout:
        print(f"   ❌ 请求超时（可能是Render免费版性能限制）")
        return False
    except Exception as e:
        print(f"   ❌ 异常: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("旅游视频生成系统 - 部署测试")
    print("=" * 60)

    success = test_api()

    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过！系统部署成功！")
        print("\n前端地址: https://lvyou-video-generator.zh-cn.edgeone.cool")
        print("后端地址: https://lvyou-video-generator.onrender.com")
    else:
        print("❌ 测试失败，需要检查日志")
    print("=" * 60)

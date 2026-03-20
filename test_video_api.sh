#!/bin/bash
# 使用curl测试视频生成API

API_BASE="https://lvyou-video-generator.onrender.com"

echo "=========================================="
echo "测试视频生成API"
echo "=========================================="

# 准备测试数据
SCRIPT_DATA='{
  "script": {
    "title": "重渡沟7日游",
    "scenes": [
      {
        "text": "探索重渡沟天河大峡谷\n山水秘境等你来",
        "duration": 5,
        "image_keyword": "canyon"
      },
      {
        "text": "竹海深处\n感受大自然的宁静",
        "duration": 5,
        "image_keyword": "bamboo forest"
      },
      {
        "text": "瀑布飞流直下\n清凉一夏",
        "duration": 5,
        "image_keyword": "waterfall"
      }
    ]
  },
  "images": [
    {
      "url": "https://images.pexels.com/photos/33148688/pexels-photo-33148688.jpeg",
      "thumb": "https://images.pexels.com/photos/33148688/pexels-photo-33148688.jpeg?auto=compress&cs=tinysrgb&h=350"
    },
    {
      "url": "https://images.pexels.com/photos/1619317/pexels-photo-1619317.jpeg",
      "thumb": "https://images.pexels.com/photos/1619317/pexels-photo-1619317.jpeg?auto=compress&cs=tinysrgb&h=350"
    },
    {
      "url": "https://images.pexels.com/photos/2166711/pexels-photo-2166711.jpeg",
      "thumb": "https://images.pexels.com/photos/2166711/pexels-photo-2166711.jpeg?auto=compress&cs=tinysrgb&h=350"
    }
  ],
  "copyData": {
    "title": "重渡沟7日游",
    "points": ["天河大峡谷", "竹海", "瀑布群"]
  },
  "travelInfo": {
    "destination": "重渡沟",
    "duration": "7天",
    "highlights": ["天河大峡谷", "竹海", "瀑布群"]
  }
}'

echo ""
echo "发送视频生成请求..."
echo "这可能需要1-2分钟..."
echo ""

# 发送请求
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "$SCRIPT_DATA" \
  --max-time 180 \
  "$API_BASE/api/video/generate")

# 分离响应体和状态码
HTTP_BODY=$(echo "$RESPONSE" | head -n -1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)

echo "HTTP状态码: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 视频生成成功！"
    echo ""
    echo "响应内容:"
    echo "$HTTP_BODY" | python3 -m json.tool

    # 提取视频路径
    VIDEO_PATH=$(echo "$HTTP_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('path', ''))" 2>/dev/null)

    if [ -n "$VIDEO_PATH" ]; then
        echo ""
        echo "视频URL: $API_BASE$VIDEO_PATH"

        # 验证视频文件
        echo ""
        echo "验证视频文件..."
        VIDEO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE$VIDEO_PATH")

        if [ "$VIDEO_STATUS" = "200" ]; then
            echo "✅ 视频文件可访问！"
            echo ""
            echo "=========================================="
            echo "🎉 测试成功！系统部署完成！"
            echo "=========================================="
            exit 0
        else
            echo "❌ 视频文件无法访问 (状态码: $VIDEO_STATUS)"
            exit 1
        fi
    fi
else
    echo "❌ 视频生成失败"
    echo ""
    echo "错误信息:"
    echo "$HTTP_BODY"
    exit 1
fi

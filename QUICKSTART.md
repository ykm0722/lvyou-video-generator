# 快速使用指南

## 1. 安装依赖

```bash
# 后端
pip install fastapi uvicorn python-multipart requests

# 前端已安装
```

## 2. 启动服务

```bash
# 方式1: 使用启动脚本
./start.sh

# 方式2: 手动启动
# 终端1 - 后端
cd backend && python3 -m uvicorn app:app --reload --port 8000

# 终端2 - 前端
cd frontend && npm run dev
```

## 3. 访问应用

打开浏览器访问: http://localhost:5173

## 4. 使用流程

1. 上传PDF行程文件
2. 上传宣传图片
3. 点击"解析PDF"
4. 查看提取的信息
5. 点击"生成视频"

## 当前状态

✅ 已完成:
- 后端API框架
- 前端基础界面
- PDF解析功能
- 文件上传功能

🚧 开发中:
- 图片搜索集成
- 分镜脚本生成
- 完整视频生成流程
- 音乐和字幕功能

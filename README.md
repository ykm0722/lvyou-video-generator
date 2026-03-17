# Travel Promo Generator

本仓库现在提供一套本地化的旅游推广短视频生成流程：

1. `./generate draft <trip_dir>` 读取线路目录里的图片、PDF 和可选 `meta.json`，生成结构化草稿。
2. `./generate review <trip_dir>` 启动本地审核页，人工确认文案、镜头、图片和配音内容。
3. `./generate render <trip_dir>` 读取审核结果，用 `ffmpeg` 输出竖版短视频、封面和脚本。

## 目录约定

- 线路目录可以直接是 `resource/`，也可以是 `resource/<trip-slug>/`
- 支持的素材：
  - `*.pdf` 行程说明
  - `*.jpg` / `*.jpeg` / `*.png` / `*.webp` 宣传图
  - 可选 `meta.json`，用于补充或覆盖自动抽取结果

示例：

```json
{
  "destination": "重渡沟 / 天河大峡谷",
  "price": "成人咨询客服",
  "target_audience": "适合中老年康养、亲子休闲、朋友结伴",
  "highlights": ["双卧7日", "高端康养", "峡谷风光", "舒适酒店"],
  "cover_text": "重渡沟7日",
  "sub_cover_text": "高端康养旅居"
}
```

## 环境变量

- `OPENAI_API_KEY`：启用 PDF/图片理解和 AI TTS。
- `OPENAI_BASE_URL`：可选，自定义 API 基地址。
- `DEFAULT_TTS_VOICE`：默认音色，默认 `coral`。
- `DEFAULT_BGM_PATH`：可选，本地 BGM 文件路径。
- `DEFAULT_FONT_FILE`：可选，手动指定中文字体文件。

没有 `OPENAI_API_KEY` 时，`draft` 会退化为基于文件名的草稿生成；`render` 会保留静音/字幕能力，但不会生成 AI 配音。

## 运行

```bash
chmod +x ./generate
./generate draft resource --skip-ai
./generate review resource --port 8765
./generate render resource
```

输出文件会写到 `output/<trip-slug>/`：

- `draft.json`
- `review-data.json`
- `final.mp4`
- `cover.jpg`
- `script.json`

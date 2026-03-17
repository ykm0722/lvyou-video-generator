from __future__ import annotations

import html
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .pipeline import load_review_document, merge_review_update, save_review_document


def _textarea(name: str, value: str, rows: int = 3) -> str:
    return f'<textarea name="{name}" rows="{rows}">{html.escape(value)}</textarea>'


def _input(name: str, value: str) -> str:
    return f'<input name="{name}" value="{html.escape(value)}" />'


def render_page(document: dict) -> str:
    profile = document["trip_profile"]
    shots = document["shot_plan"]
    assets = [asset for asset in document["assets"] if asset["kind"] == "image"]
    asset_options = "".join(
        f'<option value="{html.escape(asset["path"])}">{html.escape(Path(asset["path"]).name)}</option>'
        for asset in assets
    )
    shot_forms = []
    for index, shot in enumerate(shots):
        options = asset_options.replace(
            f'value="{html.escape(shot["image_path"])}"',
            f'value="{html.escape(shot["image_path"])}" selected',
        )
        shot_forms.append(
            f"""
            <section class="card">
              <h3>镜头 {index + 1}</h3>
              <label>标题{_input(f"shot_{index}_headline", shot.get("headline", ""))}</label>
              <label>画面文案{_textarea(f"shot_{index}_overlay_lines", "\\n".join(shot.get("overlay_lines", [])), 3)}</label>
              <label>配音文案{_textarea(f"shot_{index}_narration", shot.get("narration", ""), 4)}</label>
              <label>字幕文案{_textarea(f"shot_{index}_subtitle", shot.get("subtitle", ""), 3)}</label>
              <label>时长(秒){_input(f"shot_{index}_duration", str(shot.get("duration", 4.0)))}</label>
              <label>动画{_input(f"shot_{index}_animation", shot.get("animation", "slow_zoom_in"))}</label>
              <label>图片<select name="shot_{index}_image_path">{options}</select></label>
            </section>
            """
        )
    warnings = "".join(f"<li>{html.escape(item)}</li>" for item in document.get("warnings", []))
    missing = "".join(f"<li>{html.escape(item)}</li>" for item in document.get("missing_fields", []))
    return f"""
    <!doctype html>
    <html lang="zh-CN">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>线路审核</title>
      <style>
        :root {{
          --bg: #f5efe5;
          --card: rgba(255,255,255,0.82);
          --ink: #1d1a16;
          --accent: #ba4b22;
          --muted: #6f5b4f;
          --border: rgba(29,26,22,0.12);
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          font-family: "PingFang SC", "Hiragino Sans GB", sans-serif;
          color: var(--ink);
          background:
            radial-gradient(circle at top right, rgba(223,180,91,0.35), transparent 26%),
            linear-gradient(160deg, #f7f2e8 0%, #f0e1d4 48%, #eed7b7 100%);
        }}
        main {{
          width: min(1180px, calc(100vw - 32px));
          margin: 24px auto 48px;
          display: grid;
          gap: 18px;
        }}
        .hero {{
          padding: 24px;
          border-radius: 28px;
          background: linear-gradient(135deg, rgba(16,16,16,0.9), rgba(46,24,13,0.82));
          color: white;
          box-shadow: 0 24px 60px rgba(0,0,0,0.18);
        }}
        .grid {{
          display: grid;
          grid-template-columns: 1.1fr 1.4fr;
          gap: 18px;
        }}
        .card {{
          border-radius: 22px;
          background: var(--card);
          padding: 18px;
          backdrop-filter: blur(10px);
          border: 1px solid var(--border);
          box-shadow: 0 18px 38px rgba(61, 46, 33, 0.08);
        }}
        .shots {{
          display: grid;
          gap: 16px;
        }}
        label {{
          display: grid;
          gap: 8px;
          margin-bottom: 12px;
          font-size: 14px;
          color: var(--muted);
        }}
        input, textarea, select {{
          width: 100%;
          border-radius: 14px;
          border: 1px solid rgba(29,26,22,0.12);
          padding: 12px 14px;
          font: inherit;
          color: var(--ink);
          background: rgba(255,255,255,0.92);
        }}
        textarea {{
          resize: vertical;
          min-height: 88px;
        }}
        button {{
          border: 0;
          border-radius: 999px;
          padding: 14px 20px;
          font: inherit;
          font-weight: 700;
          color: white;
          background: linear-gradient(135deg, #c44d21, #e5a93a);
          cursor: pointer;
        }}
        ul {{
          margin: 8px 0 0;
          padding-left: 18px;
        }}
        .two {{
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }}
        @media (max-width: 900px) {{
          .grid {{ grid-template-columns: 1fr; }}
          .two {{ grid-template-columns: 1fr; }}
        }}
      </style>
    </head>
    <body>
      <main>
        <section class="hero">
          <h1>{html.escape(profile.get("title", ""))}</h1>
          <p>修改草稿后直接保存，随后执行 <code>./generate render {html.escape(document["trip_dir"])}</code> 出成片。</p>
        </section>
        <form method="post" action="/save">
          <div class="grid">
            <section class="card">
              <h2>线路信息</h2>
              <label>标题{_input("profile_title", profile.get("title", ""))}</label>
              <label>目的地{_input("profile_destination", profile.get("destination", ""))}</label>
              <div class="two">
                <label>天数{_input("profile_duration_days", str(profile.get("duration_days", "")) if profile.get("duration_days") is not None else "")}</label>
                <label>价格{_input("profile_price", profile.get("price", ""))}</label>
              </div>
              <label>封面主文案{_input("profile_cover_text", profile.get("cover_text", ""))}</label>
              <label>封面副文案{_input("profile_sub_cover_text", profile.get("sub_cover_text", ""))}</label>
              <label>开头钩子{_textarea("profile_hook", profile.get("hook", ""), 2)}</label>
              <label>线路摘要{_textarea("profile_summary", profile.get("summary", ""), 4)}</label>
              <label>核心卖点(每行一个){_textarea("profile_highlights", "\\n".join(profile.get("highlights", [])), 4)}</label>
              <label>适合人群{_textarea("profile_target_audience", profile.get("target_audience", ""), 3)}</label>
              <label>住宿亮点{_input("profile_hotel_level", profile.get("hotel_level", ""))}</label>
              <label>交通亮点{_input("profile_transportation", profile.get("transportation", ""))}</label>
              <label>行动引导{_textarea("profile_call_to_action", profile.get("call_to_action", ""), 3)}</label>
            </section>
            <section class="shots">
              <section class="card">
                <h2>待确认字段</h2>
                <ul>{missing or "<li>无</li>"}</ul>
                <h2>生成警告</h2>
                <ul>{warnings or "<li>无</li>"}</ul>
              </section>
              {''.join(shot_forms)}
            </section>
          </div>
          <input type="hidden" name="trip_dir" value="{html.escape(document["trip_dir"])}" />
          <button type="submit">保存审核结果</button>
        </form>
      </main>
    </body>
    </html>
    """


def _build_update(form_data: dict[str, list[str]], shot_count: int) -> dict:
    profile = {
        "title": form_data.get("profile_title", [""])[0].strip(),
        "destination": form_data.get("profile_destination", [""])[0].strip(),
        "duration_days": int(form_data.get("profile_duration_days", ["0"])[0] or 0) or None,
        "price": form_data.get("profile_price", [""])[0].strip(),
        "cover_text": form_data.get("profile_cover_text", [""])[0].strip(),
        "sub_cover_text": form_data.get("profile_sub_cover_text", [""])[0].strip(),
        "hook": form_data.get("profile_hook", [""])[0].strip(),
        "summary": form_data.get("profile_summary", [""])[0].strip(),
        "highlights": [item.strip() for item in form_data.get("profile_highlights", [""])[0].splitlines() if item.strip()],
        "target_audience": form_data.get("profile_target_audience", [""])[0].strip(),
        "hotel_level": form_data.get("profile_hotel_level", [""])[0].strip(),
        "transportation": form_data.get("profile_transportation", [""])[0].strip(),
        "call_to_action": form_data.get("profile_call_to_action", [""])[0].strip(),
    }
    shot_plan = []
    for index in range(shot_count):
        shot_plan.append(
            {
                "id": f"shot-{index + 1}",
                "headline": form_data.get(f"shot_{index}_headline", [""])[0].strip(),
                "overlay_lines": [item.strip() for item in form_data.get(f"shot_{index}_overlay_lines", [""])[0].splitlines() if item.strip()],
                "narration": form_data.get(f"shot_{index}_narration", [""])[0].strip(),
                "subtitle": form_data.get(f"shot_{index}_subtitle", [""])[0].strip(),
                "duration": float(form_data.get(f"shot_{index}_duration", ["4"])[0] or 4),
                "animation": form_data.get(f"shot_{index}_animation", ["slow_zoom_in"])[0].strip() or "slow_zoom_in",
                "image_path": form_data.get(f"shot_{index}_image_path", [""])[0].strip(),
            }
        )
    return {
        "trip_profile": profile,
        "shot_plan": shot_plan,
        "missing_fields": [],
        "warnings": [],
    }


def serve_review(trip_dir_input: str, port: int = 8765) -> None:
    document = load_review_document(trip_dir_input)

    class Handler(BaseHTTPRequestHandler):
        def _send_html(self, body: str, status: int = HTTPStatus.OK) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:
            if urlparse(self.path).path not in {"/", "/index.html"}:
                self._send_html("<h1>Not Found</h1>", HTTPStatus.NOT_FOUND)
                return
            self._send_html(render_page(document.to_dict()))

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/save":
                self._send_html("<h1>Not Found</h1>", HTTPStatus.NOT_FOUND)
                return
            length = int(self.headers.get("Content-Length", "0"))
            payload = parse_qs(self.rfile.read(length).decode("utf-8"))
            update = _build_update(payload, len(document.shot_plan))
            updated = merge_review_update(document, update)
            save_path = save_review_document(updated)
            self._send_html(
                f"""
                <!doctype html>
                <html lang="zh-CN"><meta charset="utf-8" />
                <body style="font-family: sans-serif; padding: 24px;">
                  <h1>已保存</h1>
                  <p>审核结果已写入 <code>{html.escape(str(save_path))}</code></p>
                  <p>下一步执行 <code>./generate render {html.escape(updated.trip_dir)}</code></p>
                </body></html>
                """
            )

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Review server ready at http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

import anthropic
import os
import json

class ScriptGenerator:
    def __init__(self):
        base_url = os.getenv('ANTHROPIC_BASE_URL')
        if base_url:
            self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'), base_url=base_url)
        else:
            self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    def generate_storyboard(self, travel_info, copy_data):
        """生成分镜头脚本"""
        # 检查 API key，如果没有则返回默认脚本
        if not os.getenv('ANTHROPIC_API_KEY'):
            return self._default_script(travel_info, copy_data)

        try:
            prompt = f"""你是抖音/小红书爆款旅游视频脚本专家。为以下旅游产品生成高转化率的分镜头脚本。

【产品信息】
- 目的地：{travel_info.get('destination', '未知')}
- 景点：{', '.join(travel_info.get('highlights', []))}
- 天数：{travel_info.get('duration', '多日游')}
- 酒店：{travel_info.get('hotel_level', '标准')}
- 核心卖点：{', '.join(copy_data.get('points', []))}

【爆款脚本结构】
生成8-12个场景，遵循黄金3秒法则+情感递进：

1. 开场钩子（1场景，5秒）：
   - 必须用疑问句/数字冲击/反常识开场
   - ❌ 避免："XX旅游"、"精品线路"
   - ✅ 推荐："{travel_info.get('destination', 'XX')}这么玩才不亏！"、"999元玩7天？真的假的？"

2. 核心景点（4-5场景，各4秒）：
   - 每个景点独特的情感点，避免重复"探索XX"
   - 用具体场景和感受，不用空洞描述
   - ✅ 推荐："在XX看日出，美哭了"、"这个瀑布比XX还壮观"

3. 价值强化（2-3场景，各4秒）：
   - 突出性价比、省心、舒适
   - ✅ 推荐："四星酒店睡到自然醒"、"一分钱都不多花"

4. 行动号召（1场景，5秒）：
   - 紧迫感+具体行动
   - ❌ 避免："立即预订"
   - ✅ 推荐："仅剩20个名额，抢到就是赚到"、"点击左下角，今天下单立减200"

【输出格式】
每个场景包含：
- duration: 时长（秒）
- image_keyword: 图片搜索关键词（**必须用英文**，格式：景点英文名 + 地区英文 + scenery/landscape）
  示例："Lijiang Old Town Yunnan scenery"、"Jade Dragon Snow Mountain landscape"
- text: 场景文案（15-25字，口语化，有画面感）

返回JSON：
{{
  "title": "视频主标题",
  "scenes": [
    {{"duration": 5, "image_keyword": "destination scenery", "text": "开场钩子文案"}}
  ]
}}"""

            message = self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response_text[start:end])

            return self._default_script(travel_info, copy_data)
        except Exception:
            return self._default_script(travel_info, copy_data)

    def _default_script(self, travel_info, copy_data):
        """默认脚本"""
        title = copy_data.get('title', '精品旅游线路')
        points = copy_data.get('points', ['高品质纯玩', '0自费0购物', '全程无忧'])
        highlights = travel_info.get('highlights', [])
        destination = travel_info.get('destination', '旅游')

        scenes = []
        # 开场钩子 - 使用英文关键词
        scenes.append({"duration": 5, "image_keyword": f"{destination} China scenery", "text": f"{destination}这么玩才不亏！"})

        # 景点场景 - 差异化文案 + 英文关键词
        scene_templates = [
            "{}美到窒息，必打卡",
            "{}的景色绝了",
            "来{}不能错过这里",
            "{}比想象中更震撼",
            "{}的美景刷爆朋友圈"
        ]
        for i, spot in enumerate(highlights[:5]):
            template = scene_templates[i % len(scene_templates)]
            # 使用英文关键词
            scenes.append({"duration": 4, "image_keyword": f"{spot} {destination} China landscape", "text": template.format(spot)})

        # 卖点场景
        for point in points[:2]:
            scenes.append({"duration": 4, "image_keyword": f"{destination} travel China", "text": point})

        # 结尾CTA
        scenes.append({"duration": 5, "image_keyword": f"{destination} China scenery", "text": "限时特惠，点击左下角立即抢购"})

        return {"title": title, "scenes": scenes}

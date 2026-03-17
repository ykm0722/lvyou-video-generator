import anthropic
import os

class ViralCopyGenerator:
    def __init__(self, api_key=None):
        base_url = os.getenv('ANTHROPIC_BASE_URL')
        if base_url:
            self.client = anthropic.Anthropic(api_key=api_key or os.getenv('ANTHROPIC_API_KEY'), base_url=base_url)
        else:
            self.client = anthropic.Anthropic(api_key=api_key or os.getenv('ANTHROPIC_API_KEY'))

    def generate_video_copy(self, travel_info):
        """生成爆款视频文案"""
        # 检查 API key，如果没有则返回默认文案
        if not os.getenv('ANTHROPIC_API_KEY'):
            return {"title": "精品旅游线路", "points": ["高品质纯玩", "0自费0购物", "全程无忧"]}

        try:
            prompt = f"""你是抖音/小红书爆款旅游视频文案专家。为以下旅游产品生成高转化率的短视频文案：

【产品信息】
目的地：{travel_info.get('destination', '未知')}
行程：{travel_info.get('duration', '未知')}
景点：{', '.join(travel_info.get('highlights', [])[:3])}
特色：{', '.join(travel_info.get('features', [])[:2])}
酒店：{travel_info.get('hotel_level', '标准')}

【爆款文案公式】
参考抖音/小红书高流量旅游视频风格：
1. 主标题：钩子+利益点（用疑问句/数字冲击/反常识）
   ❌ 避免："精品旅游线路"、"XX游"
   ✅ 推荐："999元玩7天？这条线路火了！"、"去XX千万别做这3件事"

2. 卖点文案：从功能转向利益，添加情感和场景
   ❌ 避免："0自费"、"纯玩团"
   ✅ 推荐："一分钱都不多花，玩得更爽"、"睡到自然醒的舒适大床房"、"不用担心被坑，全程透明"

3. 必须包含转化元素：
   - 紧迫感："限时特惠"、"仅剩XX个名额"
   - 价格锚点：突出性价比
   - 行动号召：具体明确

【输出要求】
1. 主标题：12-18字，必须有钩子（疑问/数字/反常识）
2. 卖点：3-4个，每个12-18字，利益导向+情感共鸣
3. 风格：口语化、有画面感、能引发共鸣

请以JSON格式返回：
{{
  "title": "主标题",
  "points": ["卖点1", "卖点2", "卖点3"]
}}"""

            message = self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            import json
            response_text = message.content[0].text
            # 提取JSON
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response_text[start:end])
            return {"title": "精品旅游线路", "points": ["高品质纯玩", "0自费0购物", "全程无忧"]}
        except Exception as e:
            # 发生任何错误时返回默认文案
            return {"title": "精品旅游线路", "points": ["高品质纯玩", "0自费0购物", "全程无忧"]}

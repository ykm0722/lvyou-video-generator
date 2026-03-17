import pdfplumber
import re

class TravelPDFParser:
    def extract_info(self, pdf_path):
        """从旅游PDF中提取关键信息"""
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages[:5]:  # 只读前5页
                text += page.extract_text() + "\n"

        info = {
            'destination': self._extract_destination(text),
            'duration': self._extract_duration(text),
            'highlights': self._extract_highlights(text),
            'features': self._extract_features(text),
            'hotel_level': self._extract_hotel(text)
        }
        return info

    def _extract_destination(self, text):
        """提取目的地"""
        lines = text.split('\n')[:10]
        for line in lines:
            if '【' in line and '】' in line:
                match = re.search(r'【(.+?)】', line)
                if match:
                    return match.group(1)
        # 尝试从标题提取
        for line in lines:
            if '洛阳' in line or '栾川' in line:
                return '洛阳·栾川'
        return "精品旅游"

    def _extract_duration(self, text):
        """提取天数"""
        match = re.search(r'双卧(\d+)日|(\d+)日游', text)
        if match:
            days = match.group(1) or match.group(2)
            return f"{days}日游"
        return "多日游"

    def _extract_highlights(self, text):
        """提取景点亮点"""
        highlights = []
        # 查找明确的景点名称
        景点关键词 = ['重渡沟', '天河大峡谷', '隋唐遗址', '明堂天堂', '洛邑古城', '牡丹园']
        for kw in 景点关键词:
            if kw in text:
                highlights.append(kw)
        return highlights[:5] if highlights else ['精品景区']

    def _extract_features(self, text):
        """提取特色服务"""
        features = []
        keywords = ['纯玩', '自费', '购物', '全含', '星酒店', '星住宿']
        for line in text.split('\n'):
            for kw in keywords:
                if kw in line:
                    features.append(line.strip())
                    break
        return features[:3]

    def _extract_hotel(self, text):
        """提取酒店等级"""
        match = re.search(r'([三四五]\s*星)', text)
        if match:
            return match.group(1).replace(' ', '')
        return ""

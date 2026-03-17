import requests
import os
from duckduckgo_search import DDGS

class ImageSearchService:
    def __init__(self):
        self.api_key = os.getenv('UNSPLASH_ACCESS_KEY', '')

    def search_pexels(self, keyword, count=5):
        """使用Pexels搜索图片"""
        api_key = os.getenv('PEXELS_API_KEY')
        if not api_key:
            return None

        try:
            url = f"https://api.pexels.com/v1/search?query={keyword}&per_page={count}"
            headers = {"Authorization": api_key}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                photos = data.get("photos", [])
                print(f"Pexels搜索 '{keyword}' 返回 {len(photos)} 张图片")
                return [{'url': p['src']['large2x'], 'thumb': p['src']['medium']} for p in photos]
        except Exception as e:
            print(f"Pexels search failed: {e}")
        return None

    def search_images(self, keyword, count=5):
        """搜索图片（优先Pexels）"""
        images = self.search_pexels(keyword, count)
        if images:
            return images
        images = self.search_unsplash(keyword, count)
        if images:
            return images

        # 使用可靠的placeholder
        return [{'url': f'https://via.placeholder.com/1080x1920/667eea/ffffff?text=Image+{i+1}',
                 'thumb': f'https://via.placeholder.com/200x300/667eea/ffffff?text={i+1}'}
                for i in range(count)]

    def search_ddg(self, keyword, count=5):
        """使用DuckDuckGo搜索图片"""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.images(keywords=keyword, max_results=count, size="Large"))
                if results:
                    print(f"DuckDuckGo搜索 '{keyword}' 返回 {len(results)} 张图片")
                    return [{'url': img['image'], 'thumb': img['thumbnail']} for img in results]
        except Exception as e:
            print(f"DuckDuckGo search failed: {e}")
        return None

    def search_unsplash(self, keyword, count=5):
        """搜索Unsplash高清图片"""
        if not self.api_key:
            return self._get_placeholder_images(keyword, count)

        url = "https://api.unsplash.com/search/photos"
        params = {
            'query': keyword,
            'per_page': count,
            'client_id': self.api_key
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()
            return [{'url': img['urls']['regular'], 'thumb': img['urls']['thumb']}
                    for img in data.get('results', [])]
        except:
            return self._get_placeholder_images(keyword, count)

    def _get_placeholder_images(self, keyword, count):
        """返回占位图片"""
        return [{'url': f'https://picsum.photos/1080/1920?random={i}',
                 'thumb': f'https://picsum.photos/200/300?random={i}'}
                for i in range(count)]

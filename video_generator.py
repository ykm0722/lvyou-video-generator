from moviepy import ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import yaml
import os

class PromoVideoGenerator:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def create_text_overlay(self, text, font_size=None):
        """创建金黄色描边文字图层"""
        try:
            cfg = self.config['text_style']
            size = (self.config['video']['width'], self.config['video']['height'])
            font_size = font_size or cfg['title_size']

            img = Image.new('RGBA', size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 检查字体文件是否存在
            font_path = cfg['font_path']
            if not os.path.exists(font_path):
                raise FileNotFoundError(f"字体文件不存在: {font_path}")

            font = ImageFont.truetype(font_path, font_size)

            # 计算文字位置（居中）
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (size[0] - text_width) // 2
            y = (size[1] - text_height) // 2

            # 绘制黑色描边
            outline_width = cfg['outline_width']
            for adj_x in range(-outline_width, outline_width + 1):
                for adj_y in range(-outline_width, outline_width + 1):
                    if adj_x != 0 or adj_y != 0:
                        draw.text((x + adj_x, y + adj_y), text, font=font, fill=cfg['outline_color'])

            # 绘制金黄色主文字
            draw.text((x, y), text, font=font, fill=cfg['main_color'])

            return np.array(img)
        except Exception as e:
            raise Exception(f"创建文字图层失败: {str(e)}")

    def generate_video(self, image_path, copy_data, output_path):
        """生成推广视频"""
        try:
            # 检查图片文件是否存在
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")

            duration = self.config['video']['duration_per_scene']
            fps = self.config['video']['fps']

            # 加载背景图片
            total_duration = duration * (len(copy_data.get('points', [])) + 1)
            bg = ImageClip(image_path).with_duration(total_duration)
            bg = bg.resized(height=self.config['video']['height'])

            clips = [bg]

            # 标题场景
            title = copy_data.get('title', '精品旅游')
            title_img = self.create_text_overlay(title, self.config['text_style']['title_size'])
            title_clip = ImageClip(title_img).with_duration(duration).with_start(0).with_position('center')
            clips.append(title_clip)

            # 卖点场景
            for i, point in enumerate(copy_data.get('points', [])):
                point_img = self.create_text_overlay(point, self.config['text_style']['point_size'])
                point_clip = ImageClip(point_img).with_duration(duration)
                point_clip = point_clip.with_start((i + 1) * duration).with_position('center')
                clips.append(point_clip)

            # 合成视频
            video = CompositeVideoClip(clips)
            video.write_videofile(output_path, fps=fps, codec='libx264', audio=False)

            return {"status": "success", "path": output_path}
        except Exception as e:
            raise Exception(f"视频生成失败: {str(e)}")

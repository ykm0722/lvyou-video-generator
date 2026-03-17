import argparse
import os
from pdf_parser import TravelPDFParser
from copywriter import ViralCopyGenerator
from video_generator import PromoVideoGenerator

class VideoAutomation:
    def __init__(self):
        self.parser = TravelPDFParser()
        self.copywriter = ViralCopyGenerator()
        self.video_gen = PromoVideoGenerator()

    def process_single_product(self, pdf_path, image_path, output_path):
        """处理单个产品生成视频"""
        print(f"解析PDF: {pdf_path}")
        travel_info = self.parser.extract_info(pdf_path)
        print(f"提取信息: {travel_info['destination']} - {travel_info['duration']}")

        print("生成文案...")
        copy_data = self.copywriter.generate_video_copy(travel_info)
        print(f"标题: {copy_data['title']}")
        print(f"卖点: {copy_data['points']}")

        print(f"生成视频: {output_path}")
        self.video_gen.generate_video(image_path, copy_data, output_path)
        print("完成！")

    def batch_process(self, resource_dir, output_dir):
        """批量处理"""
        os.makedirs(output_dir, exist_ok=True)

        pdfs = [f for f in os.listdir(resource_dir) if f.endswith('.pdf')]
        images = [f for f in os.listdir(resource_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]

        for i, pdf in enumerate(pdfs):
            pdf_path = os.path.join(resource_dir, pdf)
            image_path = os.path.join(resource_dir, images[i % len(images)])
            output_path = os.path.join(output_dir, f"video_{i+1}.mp4")

            try:
                self.process_single_product(pdf_path, image_path, output_path)
            except Exception as e:
                print(f"处理失败 {pdf}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='旅游推广视频自动生成')
    parser.add_argument('--pdf', help='PDF文件路径')
    parser.add_argument('--image', help='图片文件路径')
    parser.add_argument('--output', help='输出视频路径')
    parser.add_argument('--batch', help='批量处理资源目录')
    parser.add_argument('--output-dir', default='output', help='批量输出目录')

    args = parser.parse_args()
    automation = VideoAutomation()

    if args.batch:
        automation.batch_process(args.batch, args.output_dir)
    elif args.pdf and args.image and args.output:
        automation.process_single_product(args.pdf, args.image, args.output)
    else:
        parser.print_help()

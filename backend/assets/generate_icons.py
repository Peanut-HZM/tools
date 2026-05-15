"""生成桌面应用占位图标 — 纯色圆角矩形 + 工具箱文字"""
from PIL import Image, ImageDraw
import os

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
SIZE = 1024

# 创建图标图像（RGBA 透明背景）
img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 绘制圆角矩形背景（蓝色）
radius = 180
draw.rounded_rectangle([50, 50, SIZE - 50, SIZE - 50], radius=radius, fill=(59, 130, 246, 255))

# 绘制白色工具箱文字
try:
    from PIL import ImageFont
    font_large = ImageFont.load_default()
    font_small = ImageFont.load_default()
except ImportError:
    font_large = None
    font_small = None

# 简单扳手 emoji 作为图标占位
draw.text((SIZE // 2 - 60, SIZE // 2 - 100), "🔧", fill=(255, 255, 255, 255), font=font_large)
draw.text((SIZE // 2 - 120, SIZE // 2 + 30), "ToolBox", fill=(255, 255, 255, 255), font=font_small)

# 保存 PNG 源文件
output_path = os.path.join(ASSETS_DIR, "icon-source.png")
img.save(output_path)
print(f"✅ icon-source.png 已生成: {output_path}")

# 同时生成 .ico（Windows）
ico_path = os.path.join(ASSETS_DIR, "icon.ico")
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(ico_path, format='ICO', sizes=sizes)
print(f"✅ icon.ico 已生成: {ico_path}")

"""
PPTX 预览服务 - 将 PowerPoint 文件转换为自包含 HTML

使用 python-pptx 解析 .pptx 文件，将每页幻灯片渲染为 HTML：
- 文本框：保留位置、字号、加粗/斜体、颜色、对齐方式
- 图片：base64 内嵌为 data URI
- 表格：保留行列结构与文本
- 组合形状：递归展开
- 每张幻灯片按原始宽高比缩放为固定宽度，垂直排列并标注页码

生成的 HTML 不依赖任何外部资源，可在 sandbox iframe 中安全渲染。
"""
import base64
import html as html_mod
from pathlib import Path
from typing import Optional, Tuple

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

# EMU（English Metric Unit）到像素的换算系数：914400 EMU/英寸 ÷ 96 px/英寸
EMU_PER_PX = 9525

# 幻灯片渲染固定宽度（px），高度按原始宽高比等比缩放
SLIDE_WIDTH_PX = 960


def _emu_to_px(emu: Optional[int]) -> float:
    """EMU 转像素"""
    return round(emu / EMU_PER_PX, 2) if emu else 0


def _escape(text: str) -> str:
    """HTML 转义"""
    return html_mod.escape(text, quote=False)


def _run_style_to_css(run) -> str:
    """将文本 run 的字体样式转换为 CSS 片段"""
    css = []
    font = run.font
    try:
        if font.size:
            css.append(f"font-size:{round(font.size.pt * 4 / 3, 1)}px")
    except Exception:
        pass
    try:
        if font.bold:
            css.append("font-weight:bold")
    except Exception:
        pass
    try:
        if font.italic:
            css.append("font-style:italic")
    except Exception:
        pass
    try:
        if font.underline:
            css.append("text-decoration:underline")
    except Exception:
        pass
    try:
        rgb = font.color.rgb
        if rgb:
            css.append(f"color:#{rgb}")
    except Exception:
        pass
    return ";".join(css)


def _text_frame_to_html(text_frame) -> str:
    """将文本框渲染为 HTML 段落序列"""
    paras = []
    for para in text_frame.paragraphs:
        runs_html = "".join(
            f'<span style="{_run_style_to_css(run)}">{_escape(run.text)}</span>'
            for run in para.runs
        )
        # 段落级对齐
        align_css = ""
        try:
            if para.alignment is not None:
                align_map = {1: "center", 2: "right", 3: "justify"}
                if int(para.alignment) in align_map:
                    align_css = f"text-align:{align_map[int(para.alignment)]};"
        except Exception:
            pass
        paras.append(f'<p style="margin:0;padding:0;{align_css}">{runs_html}</p>')
    return "".join(paras)


def _table_to_html(shape) -> str:
    """将表格形状渲染为 HTML 表格"""
    rows_html = []
    tbl = shape.table
    for row in tbl.rows:
        cells_html = []
        for cell in row.cells:
            cell_text = _text_frame_to_html(cell.text_frame)
            cells_html.append(
                f'<td style="border:1px solid #999;padding:4px 8px;vertical-align:top;">{cell_text}</td>'
            )
        rows_html.append(f"<tr>{''.join(cells_html)}</tr>")
    return (
        '<table style="border-collapse:collapse;width:100%;font-size:14px;">'
        f"{''.join(rows_html)}</table>"
    )


def _picture_to_data_uri(shape) -> Optional[str]:
    """将图片形状转为 base64 data URI，失败返回 None"""
    try:
        image = shape.image
        b64 = base64.b64encode(image.blob).decode("ascii")
        ext = (image.ext or "png").lower()
        mime = "jpeg" if ext in ("jpg", "jpeg") else ext
        return f"data:image/{mime};base64,{b64}"
    except Exception:
        return None


def _shape_position_style(shape) -> str:
    """形状绝对定位样式"""
    left = _emu_to_px(shape.left)
    top = _emu_to_px(shape.top)
    width = _emu_to_px(shape.width)
    height = _emu_to_px(shape.height)
    return (
        f"position:absolute;left:{left}px;top:{top}px;"
        f"width:{width}px;height:{height}px;box-sizing:border-box;overflow:hidden;"
    )


def _render_shape(shape, out: list):
    """递归渲染单个形状到 out 列表"""
    shape_type = shape.shape_type

    # 组合形状：递归展开子形状（子坐标为相对坐标，需叠加组偏移）
    if shape_type == MSO_SHAPE_TYPE.GROUP:
        for sub in shape.shapes:
            _render_shape(sub, out)
        return

    pos_style = _shape_position_style(shape)

    # 图片
    if shape_type == MSO_SHAPE_TYPE.PICTURE:
        data_uri = _picture_to_data_uri(shape)
        if data_uri:
            out.append(
                f'<div style="{pos_style}display:flex;align-items:center;justify-content:center;">'
                f'<img src="{data_uri}" style="max-width:100%;max-height:100%;" alt=""/>'
                f"</div>"
            )
        return

    # 表格
    if getattr(shape, "has_table", False) and shape.has_table:
        out.append(f'<div style="{pos_style}">{_table_to_html(shape)}</div>')
        return

    # 图表等暂不支持的类型：占位提示
    if shape_type == MSO_SHAPE_TYPE.CHART:
        out.append(
            f'<div style="{pos_style}display:flex;align-items:center;justify-content:center;'
            f'color:#999;font-size:13px;">图表（暂不支持预览）</div>'
        )
        return

    # 文本框（含标题、正文、占位符）
    if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
        text_html = _text_frame_to_html(shape.text_frame)
        if text_html.strip():
            out.append(f'<div style="{pos_style}">{text_html}</div>')


def _slide_background_style(slide, default_color: str) -> str:
    """提取幻灯片背景色，失败返回默认色"""
    try:
        fill = slide.background.fill
        rgb = fill.fore_color.rgb
        if rgb:
            return f"#{rgb}"
    except Exception:
        pass
    return default_color


def generate_pptx_html(file_path: Path) -> Tuple[str, int]:
    """将 .pptx 文件转换为自包含 HTML

    Args:
        file_path: pptx 文件路径

    Returns:
        (html, slide_count) 元组

    Raises:
        ValueError: 文件无法解析（含旧版 .ppt 二进制格式）
    """
    try:
        prs = Presentation(str(file_path))
    except Exception as e:
        raise ValueError(
            f"无法解析演示文稿：{e}。旧版 .ppt 二进制格式不支持预览，请另存为 .pptx。"
        )

    slide_count = len(prs.slides)
    if slide_count == 0:
        raise ValueError("演示文稿没有任何幻灯片")

    # 原始幻灯片尺寸（px）与缩放系数
    orig_width_px = _emu_to_px(prs.slide_width) or SLIDE_WIDTH_PX
    orig_height_px = _emu_to_px(prs.slide_height) or round(
        orig_width_px * 9 / 16, 2
    )
    scale = SLIDE_WIDTH_PX / orig_width_px
    slide_height_css = round(orig_height_px * scale, 2)

    slides_html = []
    for index, slide in enumerate(prs.slides, start=1):
        shape_out: list = []
        for shape in slide.shapes:
            _render_shape(shape, shape_out)

        bg = _slide_background_style(slide, "#ffffff")
        slides_html.append(
            f'<div class="slide" style="width:{SLIDE_WIDTH_PX}px;height:{slide_height_css}px;'
            f'background:{bg};">'
            f'<div style="transform-origin:top left;transform:scale({round(scale, 4)});'
            f'width:{orig_width_px}px;height:{orig_height_px}px;position:relative;">'
            f"{''.join(shape_out)}</div>"
            f'<div class="slide-num">{index} / {slide_count}</div>'
            f"</div>"
        )

    page = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
* {{ margin:0; padding:0; }}
body {{
  background:#3a3f44;
  font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
  padding:16px 0;
}}
.slide {{
  position:relative;
  margin:0 auto 20px;
  box-shadow:0 2px 10px rgba(0,0,0,.4);
  overflow:hidden;
}}
.slide-num {{
  position:absolute;
  bottom:6px;
  right:10px;
  font-size:12px;
  color:rgba(128,128,128,.8);
}}
</style>
</head>
<body>
{''.join(slides_html)}
</body>
</html>"""
    return page, slide_count

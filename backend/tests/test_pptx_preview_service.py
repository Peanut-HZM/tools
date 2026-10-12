"""
PPTX 预览服务单元测试

使用 python-pptx 动态生成包含标题/正文/图片/表格的演示文稿，
验证 generate_pptx_html 的输出结构。
"""
import base64
import io

import pytest
from pptx import Presentation
from pptx.util import Inches, Pt

from app.services.pptx_preview_service import generate_pptx_html


def _build_test_pptx(tmp_path, with_picture=True, with_table=True):
    """生成包含各类形状的测试 pptx 文件，返回文件路径"""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])  # 空白版式

    # 标题文本框
    title_box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(1))
    title_run = title_box.text_frame.paragraphs[0].add_run()
    title_run.text = "ZZTEST_标题文本"
    title_run.font.size = Pt(32)
    title_run.font.bold = True

    # 正文文本框
    body_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(6), Inches(1))
    body_run = body_box.text_frame.paragraphs[0].add_run()
    body_run.text = "ZZTEST_正文内容_ABC123"

    if with_table:
        tbl_shape = slide.shapes.add_table(2, 2, Inches(1), Inches(4), Inches(4), Inches(1))
        tbl_shape.table.cell(0, 0).text = "ZZTEST_表头"
        tbl_shape.table.cell(1, 1).text = "ZZTEST_单元格"

    if with_picture:
        # 生成 1x1 红色 PNG
        from PIL import Image
        img = Image.new("RGB", (4, 4), (255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        slide.shapes.add_picture(buf, Inches(7), Inches(4), Inches(1), Inches(1))

    # 第二张幻灯片
    slide2 = prs.slides.add_slide(prs.slide_layouts[5])
    box = slide2.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(1))
    box.text_frame.paragraphs[0].add_run().text = "ZZTEST_第二页"

    path = tmp_path / "ZZTEST_test.pptx"
    prs.save(str(path))
    return path


class TestGeneratePptxHtml:
    def test_basic_structure(self, tmp_path):
        """生成的 HTML 包含完整文档结构、幻灯片数量与页码"""
        pptx_path = _build_test_pptx(tmp_path)
        html, slide_count = generate_pptx_html(pptx_path)

        assert slide_count == 2
        assert "<!DOCTYPE html>" in html
        assert html.count('class="slide"') == 2
        assert "1 / 2" in html
        assert "2 / 2" in html

    def test_text_content(self, tmp_path):
        """标题与正文文本正确渲染且被转义到 HTML 中"""
        pptx_path = _build_test_pptx(tmp_path)
        html, _ = generate_pptx_html(pptx_path)

        assert "ZZTEST_标题文本" in html
        assert "ZZTEST_正文内容_ABC123" in html
        assert "ZZTEST_第二页" in html
        # 加粗样式
        assert "font-weight:bold" in html

    def test_table_content(self, tmp_path):
        """表格单元格文本正确渲染"""
        pptx_path = _build_test_pptx(tmp_path)
        html, _ = generate_pptx_html(pptx_path)

        assert "<table" in html
        assert "ZZTEST_表头" in html
        assert "ZZTEST_单元格" in html

    def test_picture_embedded_as_data_uri(self, tmp_path):
        """图片以 base64 data URI 内嵌"""
        pptx_path = _build_test_pptx(tmp_path)
        html, _ = generate_pptx_html(pptx_path)

        assert "data:image/png;base64," in html

    def test_html_escaping(self, tmp_path):
        """文本中的 HTML 特殊字符被正确转义"""
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(1))
        box.text_frame.paragraphs[0].add_run().text = "<script>alert(1)</script>"

        path = tmp_path / "ZZTEST_escape.pptx"
        prs.save(str(path))

        html, _ = generate_pptx_html(path)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_empty_presentation_raises(self, tmp_path):
        """空演示文稿抛出 ValueError"""
        prs = Presentation()
        path = tmp_path / "ZZTEST_empty.pptx"
        prs.save(str(path))

        with pytest.raises(ValueError, match="没有任何幻灯片"):
            generate_pptx_html(path)

    def test_invalid_file_raises(self, tmp_path):
        """非 pptx 文件抛出 ValueError"""
        path = tmp_path / "ZZTEST_bad.pptx"
        path.write_bytes(b"not a pptx file")

        with pytest.raises(ValueError, match="无法解析"):
            generate_pptx_html(path)


class TestConvertSlideToPdf:
    """LibreOffice PDF 转换（soffice 缺失时跳过）"""

    @pytest.mark.skipif(
        __import__("app.services.pptx_preview_service", fromlist=["find_soffice"]).find_soffice() is None,
        reason="LibreOffice 未安装",
    )
    def test_convert_pptx_to_pdf(self, tmp_path):
        """生成的 pptx 可转换为 PDF 且输出有效"""
        from app.services.pptx_preview_service import convert_slide_to_pdf, find_soffice

        pptx_path = _build_test_pptx(tmp_path, with_picture=False, with_table=False)
        pdf_path = convert_slide_to_pdf(pptx_path, soffice_path=find_soffice())

        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
        # PDF 文件头校验
        with open(pdf_path, "rb") as f:
            assert f.read(5) == b"%PDF-"

    @pytest.mark.skipif(
        __import__("app.services.pptx_preview_service", fromlist=["find_soffice"]).find_soffice() is None,
        reason="LibreOffice 未安装",
    )
    def test_convert_cache_hit(self, tmp_path):
        """相同文件二次转换命中缓存（mtime 未变返回同一文件）"""
        from app.services.pptx_preview_service import convert_slide_to_pdf, find_soffice

        pptx_path = _build_test_pptx(tmp_path, with_picture=False, with_table=False)
        first = convert_slide_to_pdf(pptx_path, soffice_path=find_soffice())
        second = convert_slide_to_pdf(pptx_path, soffice_path=find_soffice())
        assert first == second

    def test_convert_raises_without_soffice(self, tmp_path):
        """soffice 不可用时抛出 ValueError"""
        from app.services.pptx_preview_service import convert_slide_to_pdf

        pptx_path = _build_test_pptx(tmp_path, with_picture=False, with_table=False)
        with pytest.raises(ValueError, match="未安装"):
            convert_slide_to_pdf(pptx_path, soffice_path="/nonexistent/soffice")

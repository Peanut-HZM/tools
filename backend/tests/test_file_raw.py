"""
文件原始内容读取测试（支持二进制文件）
"""
import os
import pytest
import base64
from pathlib import Path
from app.services.markdown_file_service import MarkdownFileService
from app.models.file_models import FileRawContent


@pytest.fixture
def temp_files(tmp_path):
    """创建临时测试文件"""
    # 文本文件
    text_file = tmp_path / "test.py"
    text_file.write_text("print('hello')", encoding="utf-8")

    # 二进制文件
    binary_file = tmp_path / "test.bin"
    binary_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    return tmp_path, text_file, binary_file


def test_read_file_raw_text(temp_files):
    """测试读取文本文件"""
    root_path, text_file, _ = temp_files
    service = MarkdownFileService("test_user", custom_root=str(root_path))

    result = service.read_file_raw("test.py")

    assert isinstance(result, FileRawContent)
    assert result.path == "test.py"
    assert result.content_type == "text/x-python"
    assert result.text == "print('hello')"
    assert result.data is None


def test_read_file_raw_binary(temp_files):
    """测试读取二进制文件"""
    root_path, _, binary_file = temp_files
    service = MarkdownFileService("test_user", custom_root=str(root_path))

    result = service.read_file_raw("test.bin")

    assert isinstance(result, FileRawContent)
    assert result.content_type == 'application/octet-stream'
    assert result.data is not None
    assert result.text is None
    # 验证 base64 解码
    decoded = base64.b64decode(result.data)
    assert decoded == b"\x89PNG\r\n\x1a\n"


def test_read_file_raw_not_found():
    """测试文件不存在"""
    service = MarkdownFileService("test_user", custom_root="/tmp")

    with pytest.raises(FileNotFoundError):
        service.read_file_raw("nonexistent.txt")


def test_read_file_raw_image(temp_files):
    """测试读取图片文件"""
    root_path = temp_files[0]
    # 创建 PNG 文件
    png_file = root_path / "test.png"
    png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    png_file.write_bytes(png_data)

    service = MarkdownFileService("test_user", custom_root=str(root_path))
    result = service.read_file_raw("test.png")

    assert result.content_type == 'image/png'
    assert result.data is not None
    assert result.text is None
    # 验证 base64 解码后数据正确
    decoded = base64.b64decode(result.data)
    assert decoded == png_data


def test_read_file_raw_json(temp_files):
    """测试读取 JSON 文件"""
    root_path = temp_files[0]
    json_file = root_path / "data.json"
    json_content = '{"key": "value", "number": 42}'
    json_file.write_text(json_content, encoding="utf-8")

    service = MarkdownFileService("test_user", custom_root=str(root_path))
    result = service.read_file_raw("data.json")

    assert result.content_type == 'application/json'
    assert result.text == json_content
    assert result.data is None


def test_read_file_raw_metadata(temp_files):
    """测试返回的文件元数据"""
    root_path, text_file, _ = temp_files
    service = MarkdownFileService("test_user", custom_root=str(root_path))

    result = service.read_file_raw("test.py")

    # 验证元数据
    assert result.size == len("print('hello')")
    assert result.modified is not None
    assert result.path == "test.py"


def test_read_file_raw_oversized(tmp_path):
    """测试文件大小限制：超过 10MB 的文本文件应抛出 ValueError

    使用稀疏文件（sparse file）：st_size 显示为 11MB 但不占用实际磁盘空间
    """
    # 创建一个稀疏文件（APFS/ext4 均支持）
    test_file = tmp_path / "large.py"
    fd = os.open(str(test_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    try:
        os.ftruncate(fd, 11 * 1024 * 1024)  # 11MB，超过 10MB 文本限制
    finally:
        os.close(fd)

    service = MarkdownFileService("test_user", custom_root=str(tmp_path))

    with pytest.raises(ValueError, match="文件过大"):
        service.read_file_raw("large.py")


def test_read_file_raw_latin1_fallback(tmp_path):
    """测试 UTF-8 解码失败时回退到 latin-1"""
    # 创建含 latin-1 专有字节（非合法 UTF-8）的文件
    test_file = tmp_path / "latin1.txt"
    test_file.write_bytes(b"caf\xe9")  # \xe9 在 latin-1 中为 'é'，不是合法 UTF-8

    service = MarkdownFileService("test_user", custom_root=str(tmp_path))
    result = service.read_file_raw("latin1.txt")

    assert result.text == "café"  # latin-1 解码
    assert result.content_type == "text/plain"
    assert result.data is None


def test_read_file_raw_binary_allows_over_10mb(tmp_path):
    """测试二进制文件的大小限制为 50MB（而非 10MB）

    通过稀疏文件模拟 15MB 的二进制文件，验证可正常读取（二进制限制更高）。
    """
    test_file = tmp_path / "large.bin"
    fd = os.open(str(test_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    try:
        os.ftruncate(fd, 15 * 1024 * 1024)  # 15MB：超过文本限制 10MB，但在二进制限制 50MB 内
    finally:
        os.close(fd)

    service = MarkdownFileService("test_user", custom_root=str(tmp_path))
    # 不应抛出异常
    result = service.read_file_raw("large.bin")

    assert result.content_type == 'application/octet-stream'
    assert result.data is not None
    assert result.text is None
    assert result.size == 15 * 1024 * 1024

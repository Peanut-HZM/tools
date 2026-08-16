# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包规格 — 桌面工具箱应用。

用法:
    pyinstaller desktop.spec          # macOS / Windows (同命令)
"""
import sys
from pathlib import Path

block_cipher = None

# 前端 dist 目录路径 (backend/ 的父目录是 tools/)
frontend_root = Path(__file__).parent.parent / "frontend" / "dist"

# 收集 datas: Python 代码 + 前端静态文件 + 必要资源
datas = []

if frontend_root.exists():
    datas.append((str(frontend_root), "frontend_dist"))
else:
    print(f"⚠️  前端 dist 目录不存在: {frontend_root}")
    print("   请先运行: cd frontend && npm run build")

# 可选: 打包 .env 模板
env_file = Path(__file__).parent / ".env.desktop-template"
if env_file.exists():
    datas.append((str(env_file), "."))

a = Analysis(
    ["desktop_app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # FastAPI + Starlette 隐式导入
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # pywebview
        "webview",
        # passlib
        "passlib.handlers",
        "passlib.handlers.bcrypt",
        "passlib.utils",
        # cryptography
        "cryptography.hazmat",
        # SQLAlchemy
        "sqlalchemy.dialects.sqlite",
        # psycopg2 (如果打包)
        "psycopg2",
        "psycopg2.extensions",
        # paramiko
        "paramiko",
        "paramiko.transport",
        # numpy (如果被导入)
        "numpy",
        # OpenCV (如果被导入)
        "cv2",
        # PyPDF2
        "PyPDF2",
        # pdfplumber
        "pdfplumber",
        # pandas
        "pandas",
        # openpyxl
        "openpyxl",
        # PIL (图标生成)
        "PIL",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的包，减小体积
        "matplotlib",
        "tkinter",
        "jupyter",
        "IPython",
        "notebook",
        "nbconvert",
        "setuptools",
        "distutils",
        "test",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 确定图标路径
assets_dir = Path(__file__).parent / "assets"
if sys.platform == "darwin":
    icon_path = str(assets_dir / "icon.icns") if (assets_dir / "icon.icns").exists() else None
else:
    icon_path = str(assets_dir / "icon.ico") if (assets_dir / "icon.ico").exists() else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ToolBox",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 无控制台窗口
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ToolBox",
)

# macOS 使用 BUNDLE 创建 .app
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="ToolBox.app",
        icon=icon_path,
        bundle_identifier="com.example.toolbox",
        info_plist={
            "CFBundleName": "ToolBox",
            "CFBundleDisplayName": "工具箱",
            "CFBundleVersion": "1.0.0",
            "CFBundleShortVersionString": "1.0",
            "NSHighResolutionCapable": "true",
        },
    )

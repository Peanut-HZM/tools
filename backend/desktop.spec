# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包规格 — 桌面工具箱应用。

用法:
    pyinstaller desktop.spec          # macOS / Windows (同命令)
"""
import sys
from pathlib import Path

block_cipher = None

# PyInstaller 6.x 的 spec 执行环境不再提供 __file__，使用注入的 SPECPATH（spec 所在目录字符串）
spec_dir = Path(SPECPATH)

# 前端 dist 目录路径 (backend/ 的父目录是 tools/)
frontend_root = spec_dir.parent / "frontend" / "dist"

# 收集 datas: Python 代码 + 前端静态文件 + 必要资源
datas = []

if frontend_root.exists():
    datas.append((str(frontend_root), "frontend_dist"))
else:
    print(f"⚠️  前端 dist 目录不存在: {frontend_root}")
    print("   请先运行: cd frontend && npm run build")

# magika（markitdown 依赖）的包内数据文件：PyInstaller 只收集代码，不收集包内
# 数据目录；缺 models/standard_v3_3 报 "model dir not found"，
# 缺 config/content_types_kb.min.json 报 FileNotFoundError（导入 converter 时崩溃）
import importlib.util as _ilutil

_magika_spec = _ilutil.find_spec("magika")
if _magika_spec and _magika_spec.origin:
    _magika_pkg = Path(_magika_spec.origin).parent
    for _sub in ("models", "config"):
        _data_dir = _magika_pkg / _sub
        if _data_dir.exists():
            datas.append((str(_data_dir), f"magika/{_sub}"))
            print(f"✅ 已收录 magika 数据: {_data_dir}")
        else:
            print(f"⚠️  magika 数据目录不存在: {_data_dir}")

# 打包内置 .env（desktop_config frozen 三级查找的第二级：_internal/.env）。
# 本地构建产物（backend/dist/ 已被 .gitignore 忽略，绝不入库）——
# 使桌面版获得与 backend/.env 一致的 PostgreSQL/OSS/密钥配置，功能与 Web 版对齐
_backend_env = spec_dir / ".env"
if _backend_env.exists():
    datas.append((str(_backend_env), "."))
    print("✅ 已打包内置 backend/.env 到 _internal/.env（本地构建产物，不入库）")
else:
    print(f"⚠️  backend/.env 不存在，桌面版将使用默认配置（SQLite/无密钥）")

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
        # psycopg2（如果打包）——子模块是动态注册的，只列主包会导致
        # 冻结后 module 'psycopg2' has no attribute 'errors' / extras 等 AttributeError
        "psycopg2",
        "psycopg2.extensions",
        "psycopg2.errors",
        "psycopg2.extras",
        "psycopg2.pool",
        "psycopg2.sql",
        "psycopg2.tz",
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
        # 注意：Python 3.12 + PyInstaller 6 下不能 exclude distutils——
        # setuptools 钩子会再次注册它，触发 "already imported as ExcludedModule" 冲突
        "matplotlib",
        "tkinter",
        "jupyter",
        "IPython",
        "notebook",
        "nbconvert",
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
assets_dir = spec_dir / "assets"
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

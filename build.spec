# PyInstaller spec – produces dist/CrabMeasure/ (onedir)
# Build with:  pyinstaller build.spec

import sys
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)   # noqa: F821  – SPECPATH is injected by PyInstaller

a = Analysis(
    [str(ROOT / "src" / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "config.yaml"),                  "."),
        (str(ROOT / "data" / "examples"),            "data/examples"),
        (str(ROOT / "MEASUREMENT_SPEC.md"),          "."),
    ],
    hiddenimports=[
        # napari + vispy
        "napari",
        "napari._qt",
        "napari._qt.qt_main_window",
        "napari.plugins",
        "napari._vispy",
        "vispy",
        "vispy.app.backends._pyqt5",
        "vispy.backends._pyqt5",
        # image / data
        "cv2",
        "tifffile",
        "imagecodecs",
        "pandas",
        "numpy",
        "scipy",
        "scipy.spatial",
        "scipy.ndimage",
        # Qt
        "qtpy",
        "PyQt5",
        "PyQt5.QtWidgets",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        # config
        "yaml",
        # napari optional deps
        "magicgui",
        "superqt",
        "psygnal",
        "app_model",
        "npe2",
        "PIL",
        "PIL.Image",
        "skimage",
        "skimage.measure",
        "skimage.filters",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "IPython", "jupyter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CrabMeasure",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # no terminal window for end-users
    icon=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CrabMeasure",
)

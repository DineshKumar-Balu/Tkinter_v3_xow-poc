# Import necessary modules
import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

# Define paths to required binaries and data
tesseract_path = os.path.join(os.getcwd(), "Tesseract-OCR")
ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg-v1", "bin", "ffmpeg.exe")
tesseract_exe = os.path.join(tesseract_path, "tesseract.exe")
tesseract_data_path = os.path.join(tesseract_path, "tessdata")
vlc_dll_path = os.path.join(os.getcwd(), "VLC", "libvlc.dll")

# Specify binaries (executables)
binaries = [
    (ffmpeg_path, "ffmpeg-v1/bin"),  # FFmpeg binary
    (tesseract_exe, "Tesseract-OCR"),  # Tesseract binary
    (vlc_dll_path, '.')  # VLC DLL
]

# Specify data files
datas = [
    (tesseract_path, "Tesseract-OCR"),  # Full Tesseract folder
    (tesseract_data_path, "Tesseract-OCR/tessdata"),  # Tesseract data files
]

# Create PyInstaller analysis
a = Analysis(
    ['app.py'],
    pathex=[os.path.abspath('.')], 
    binaries=binaries,  
    datas=datas,  
    hiddenimports=[], 
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Build Python archive (PYZ)
pyz = PYZ(a.pure)

# Create executable (EXE)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # Binaries are handled by COLLECT
    name='app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, 
    console=True,  
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Collect everything into the final executable directory
coll = COLLECT(
    exe,
    a.binaries,  
    a.datas,  
    strip=False,
    upx=True,
    upx_exclude=[],
    name='app',
)

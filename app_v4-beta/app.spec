# Import necessary modules
import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

# Define paths to required binaries and data
tesseract_path = os.path.join(os.getcwd(), "Tesseract-OCR")
ffmpeg_path = os.path.join(os.getcwd(), "ffmpeg-v1", "bin", "ffmpeg.exe")
tesseract_exe = os.path.join(tesseract_path, "tesseract.exe")  # Path to tesseract.exe
tesseract_data_path = os.path.join(tesseract_path, "tessdata")  # Path to tessdata
vlc_dll_path = os.path.join(os.getcwd(), "VLC", "libvlc.dll")  # Path to VLC's libvlc.dll

# Specify binaries (executables)
binaries = [
    (ffmpeg_path, "ffmpeg-v1/bin"),  # FFmpeg binary
    (tesseract_exe, "Tesseract-OCR"),  # Tesseract binary
    (os.path.join(os.getcwd(), "VLC", "libvlc.dll"), "VLC")  # Include all VLC binaries
]

# Specify data files
datas = [
    (tesseract_path, "Tesseract-OCR"),  # Full Tesseract folder
    (tesseract_data_path, "Tesseract-OCR/tessdata"),  # Tesseract data files
]

# Create PyInstaller analysis
a = Analysis(
    ['app.py'],  # Main script
    pathex=[os.path.abspath('.')],  # Search path for modules
    binaries=binaries,  # Include binaries (FFmpeg, Tesseract, VLC)
    datas=datas,  # Include data files (Tesseract data files)
    hiddenimports=[],  # No additional hidden imports
    hookspath=[],  # No custom hooks
    hooksconfig={},  # No special hook configurations
    runtime_hooks=[],  # No runtime hooks
    excludes=[],  # No exclusions
    noarchive=False,  # Do not disable archive
    optimize=0,  # Optimization level 0
)

# Build Python archive (PYZ)
pyz = PYZ(a.pure)

# Create executable (EXE)
exe = EXE(
    pyz,
    a.scripts,  # Main scripts to bundle
    [],
    exclude_binaries=True,  # Exclude binaries from the EXE (handled by COLLECT)
    name='app',  # Name of the executable
    debug=False,  # No debug mode
    bootloader_ignore_signals=False,
    strip=False,  # Don't strip debug information
    upx=True,  # Use UPX compression
    console=True,  # Console application
    disable_windowed_traceback=False,  # Enable traceback in the console
    argv_emulation=False,  # No argument emulation
    target_arch=None,  # No specific architecture target
    codesign_identity=None,  # No code signing
    entitlements_file=None,  # No entitlement file
)

# Collect everything into the final executable directory
coll = COLLECT(
    exe,
    a.binaries,  # Include binaries
    a.datas,  # Include data files
    strip=False,  # Don't strip files
    upx=True,  # Use UPX compression
    upx_exclude=[],  # No exclusions from UPX
    name='app',  # Name of the final app
)

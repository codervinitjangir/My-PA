# deploy/build_desktop.py

"""
JARVIS Desktop PyInstaller Build Script
Compiles jarvis_desktop into a standalone Windows binary (dist/JARVIS.exe).
"""

import os
import sys
import subprocess

def build():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    main_script = os.path.join(root_dir, "jarvis_desktop", "app", "__main__.py")
    dist_dir = os.path.join(root_dir, "dist")
    build_dir = os.path.join(root_dir, "build_pyinstaller")

    os.makedirs(dist_dir, exist_ok=True)
    os.makedirs(build_dir, exist_ok=True)

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "JARVIS",
        "--distpath", dist_dir,
        "--workpath", build_dir,
        "--paths", root_dir,
        main_script
    ]

    print(f"[BuildDesktop] Executing PyInstaller build command:\n{' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=root_dir)

    if result.returncode == 0:
        print(f"\n✅ [BuildDesktop] SUCCESS: Standalone executable created at {os.path.join(dist_dir, 'JARVIS', 'JARVIS.exe')}")
    else:
        print(f"\n❌ [BuildDesktop] FAILED with code {result.returncode}")

if __name__ == "__main__":
    build()

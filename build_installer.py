#!/usr/bin/env python3
"""
Boony English App Build Script
Automated build system for creating installers and executables
"""

import os
import sys
import subprocess
import shutil
import platform
import argparse
from pathlib import Path
import zipfile
import tarfile

class BoonyBuilder:
    def __init__(self):
        self.system = platform.system().lower()
        self.project_root = Path.cwd()
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        self.app_name = "boony_english_app"
        
    def clean_build_dirs(self):
        """Clean previous build artifacts"""
        print("🧹 Cleaning previous build artifacts...")
        
        dirs_to_clean = [self.build_dir, self.dist_dir, "__pycache__"]
        
        for dir_path in dirs_to_clean:
            if isinstance(dir_path, str):
                dir_path = Path(dir_path)
            
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"✅ Cleaned {dir_path}")
        
        # Clean Python cache files
        for cache_dir in self.project_root.rglob("__pycache__"):
            shutil.rmtree(cache_dir)
        
        for pyc_file in self.project_root.rglob("*.pyc"):
            pyc_file.unlink()
    
    def install_build_dependencies(self):
        """Install required build dependencies"""
        print("📦 Installing build dependencies...")
        
        dependencies = [
            "pyinstaller>=5.0.0",
            "cx-freeze>=6.0.0",
            "setuptools>=60.0.0",
            "wheel>=0.37.0",
            "twine>=4.0.0"
        ]
        
        try:
            for dep in dependencies:
                print(f"Installing {dep}...")
                subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                             check=True, capture_output=True)
            print("✅ Build dependencies installed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install build dependencies: {e}")
            return False
    
    def build_pyinstaller_executable(self):
        """Build standalone executable using PyInstaller"""
        print("🔨 Building PyInstaller executable...")
        
        try:
            # Use the spec file if it exists, otherwise create command
            spec_file = self.project_root / "boony_app.spec"
            
            if spec_file.exists():
                cmd = ["pyinstaller", "--clean", str(spec_file)]
            else:
                cmd = [
                    "pyinstaller",
                    "--onedir",
                    "--windowed" if self.system == "windows" else "--console",
                    "--add-data", "templates:templates",
                    "--add-data", "static:static",
                    "--add-data", "assets:assets",
                    "--add-data", "data:data",
                    "--add-data", "core:core",
                    "--add-data", "services:services",
                    "--add-data", "migrations:migrations",
                    "--hidden-import", "flask",
                    "--hidden-import", "sqlalchemy",
                    "--hidden-import", "psycopg2",
                    "--name", self.app_name,
                    "app.py"
                ]
            
            subprocess.run(cmd, check=True)
            print("✅ PyInstaller executable built successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ PyInstaller build failed: {e}")
            return False
    
    def build_cx_freeze_executable(self):
        """Build executable using cx_Freeze"""
        print("🔨 Building cx_Freeze executable...")
        
        # Create cx_Freeze setup script
        cx_setup_content = '''
from cx_Freeze import setup, Executable
import sys

# Dependencies are automatically detected, but it might need fine tuning.
build_options = {
    'packages': [
        'flask', 'sqlalchemy', 'psycopg2', 'openai', 'pandas', 
        'werkzeug', 'jinja2', 'markupsafe', 'blinker', 'click'
    ],
    'excludes': ['tkinter'],
    'include_files': [
        ('templates/', 'templates/'),
        ('static/', 'static/'),
        ('assets/', 'assets/'),
        ('data/', 'data/'),
        ('core/', 'core/'),
        ('services/', 'services/'),
        ('migrations/', 'migrations/'),
    ]
}

base = 'Win32GUI' if sys.platform == 'win32' else None

executables = [
    Executable('app.py', base=base, target_name='boony_app')
]

setup(
    name='Boony English App',
    version='1.0.0',
    description='Interactive English Learning Application',
    options={'build_exe': build_options},
    executables=executables
)
'''
        
        cx_setup_file = self.project_root / "setup_cx.py"
        with open(cx_setup_file, 'w') as f:
            f.write(cx_setup_content)
        
        try:
            subprocess.run([sys.executable, "setup_cx.py", "build"], check=True)
            print("✅ cx_Freeze executable built successfully")
            
            # Clean up temporary setup file
            cx_setup_file.unlink()
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ cx_Freeze build failed: {e}")
            return False
    
    def build_python_package(self):
        """Build Python wheel and source distribution"""
        print("📦 Building Python package...")
        
        try:
            # Build wheel and source distribution
            subprocess.run([sys.executable, "setup.py", "sdist", "bdist_wheel"], 
                         check=True)
            print("✅ Python package built successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Python package build failed: {e}")
            return False
    
    def create_portable_archive(self):
        """Create portable archive with all necessary files"""
        print("📁 Creating portable archive...")
        
        try:
            # Create portable directory
            portable_dir = self.dist_dir / "boony_portable"
            portable_dir.mkdir(parents=True, exist_ok=True)
            
            # Files and directories to include
            items_to_copy = [
                "app.py", "config.py", "models.py", "requirements.txt",
                "setup.py", "install.py", "fetch_user_data.py",
                "templates", "static", "assets", "data", "core", 
                "services", "migrations"
            ]
            
            # Copy files
            for item in items_to_copy:
                src = Path(item)
                if src.exists():
                    dst = portable_dir / item
                    if src.is_dir():
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
            
            # Create README for portable version
            readme_content = '''
# Boony English App - Portable Version

## Quick Start
1. Install Python 3.8+ from https://python.org
2. Run: python install.py
3. Follow the installation instructions
4. Start the app using the generated launcher script

## Manual Installation
1. Install dependencies: pip install -r requirements.txt
2. Run the app: python app.py
3. Open http://localhost:5000 in your browser

## Configuration
- Copy .env.example to .env and configure your settings
- Update database credentials in .env file

## Support
For support and documentation, visit: https://github.com/angelgurus/boony-english
'''
            
            with open(portable_dir / "README.txt", 'w') as f:
                f.write(readme_content)
            
            # Create archive
            archive_name = f"boony_english_app_portable_{platform.system().lower()}"
            
            if self.system == "windows":
                archive_path = self.dist_dir / f"{archive_name}.zip"
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file_path in portable_dir.rglob('*'):
                        if file_path.is_file():
                            arcname = file_path.relative_to(portable_dir.parent)
                            zf.write(file_path, arcname)
            else:
                archive_path = self.dist_dir / f"{archive_name}.tar.gz"
                with tarfile.open(archive_path, 'w:gz') as tf:
                    tf.add(portable_dir, arcname=portable_dir.name)
            
            print(f"✅ Portable archive created: {archive_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create portable archive: {e}")
            return False
    
    def create_installer_package(self):
        """Create platform-specific installer package"""
        print(f"📦 Creating installer package for {platform.system()}...")
        
        if self.system == "windows":
            return self._create_windows_installer()
        elif self.system == "darwin":
            return self._create_macos_installer()
        else:
            return self._create_linux_installer()
    
    def _create_windows_installer(self):
        """Create Windows installer (requires NSIS or Inno Setup)"""
        print("ℹ️ Windows installer creation requires NSIS or Inno Setup")
        print("Please use the portable archive or PyInstaller executable")
        return True
    
    def _create_macos_installer(self):
        """Create macOS app bundle and DMG"""
        print("ℹ️ macOS installer creation requires additional tools")
        print("Please use the portable archive or PyInstaller executable")
        return True
    
    def _create_linux_installer(self):
        """Create Linux package (DEB/RPM)"""
        print("ℹ️ Linux package creation requires additional tools")
        print("Please use the portable archive or install via pip")
        return True
    
    def build_all(self, build_types):
        """Build all specified package types"""
        print(f"🚀 Starting build process for: {', '.join(build_types)}")
        print("="*60)
        
        # Clean previous builds
        self.clean_build_dirs()
        
        # Install build dependencies
        if not self.install_build_dependencies():
            return False
        
        success = True
        
        if "pyinstaller" in build_types:
            success &= self.build_pyinstaller_executable()
        
        if "cx_freeze" in build_types:
            success &= self.build_cx_freeze_executable()
        
        if "wheel" in build_types:
            success &= self.build_python_package()
        
        if "portable" in build_types:
            success &= self.create_portable_archive()
        
        if "installer" in build_types:
            success &= self.create_installer_package()
        
        print("="*60)
        if success:
            print("🎉 Build process completed successfully!")
            print(f"📂 Output directory: {self.dist_dir}")
        else:
            print("❌ Build process failed!")
        
        return success

def main():
    parser = argparse.ArgumentParser(description='Build Boony English App installers')
    parser.add_argument('--type', choices=['pyinstaller', 'cx_freeze', 'wheel', 'portable', 'installer', 'all'],
                       default='all', help='Type of build to create')
    parser.add_argument('--clean', action='store_true', help='Clean build directories only')
    
    args = parser.parse_args()
    
    builder = BoonyBuilder()
    
    if args.clean:
        builder.clean_build_dirs()
        print("✅ Build directories cleaned")
        return
    
    if args.type == 'all':
        build_types = ['pyinstaller', 'wheel', 'portable']
    else:
        build_types = [args.type]
    
    try:
        success = builder.build_all(build_types)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during build: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
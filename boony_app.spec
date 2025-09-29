# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Get the current directory
block_cipher = None
current_dir = os.path.abspath('.')

# Collect all data files
datas = []

# Add templates
datas += collect_data_files('jinja2')
datas += [('templates', 'templates')]
datas += [('static', 'static')]
datas += [('assets', 'assets')]
datas += [('data', 'data')]
datas += [('core/data', 'core/data')]
datas += [('migrations', 'migrations')]

# Add configuration files
if os.path.exists('.env'):
    datas += [('.env', '.')]
if os.path.exists('config.py'):
    datas += [('config.py', '.')]
if os.path.exists('models.py'):
    datas += [('models.py', '.')]

# Add service modules
if os.path.exists('services'):
    datas += [('services', 'services')]
if os.path.exists('core'):
    datas += [('core', 'core')]

# Add any database files
if os.path.exists('instance'):
    datas += [('instance', 'instance')]
if os.path.exists('offline.db'):
    datas += [('offline.db', '.')]

# Collect hidden imports
hiddenimports = [
    'flask',
    'flask_login',
    'flask_sqlalchemy',
    'flask_migrate',
    'sqlalchemy',
    'sqlalchemy.dialects.postgresql',
    'sqlalchemy.dialects.sqlite',
    'psycopg2',
    'psycopg2.extras',
    'openai',
    'pandas',
    'openpyxl',
    'python_dotenv',
    'werkzeug',
    'jinja2',
    'markupsafe',
    'blinker',
    'click',
    'colorama',
    'itsdangerous',
    'tabulate',
    'requests',
    'json',
    'base64',
    'io',
    'tempfile',
    'datetime',
    'os',
    'random',
    'sys'
]

# Add submodules
hiddenimports += collect_submodules('flask')
hiddenimports += collect_submodules('sqlalchemy')
hiddenimports += collect_submodules('werkzeug')
hiddenimports += collect_submodules('jinja2')

a = Analysis(
    ['app.py'],
    pathex=[current_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='boony_app',
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
    icon='assets/icons/app.ico' if os.path.exists('assets/icons/app.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='boony_app',
)
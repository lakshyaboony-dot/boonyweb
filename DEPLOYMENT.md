# Boony English App - Deployment Guide

This guide explains how to create installers and deploy the Boony English Learning Application on different systems.

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (optional, for development)
- Internet connection for downloading dependencies

## 🚀 Quick Start

### Option 1: Automated Installation (Recommended)
```bash
python install.py
```

### Option 2: Manual Installation
```bash
pip install -r requirements.txt
python app.py
```

## 🔧 Building Installers

### 1. Build All Package Types
```bash
python build_installer.py --type all
```

### 2. Build Specific Package Types

#### Standalone Executable (PyInstaller)
```bash
python build_installer.py --type pyinstaller
```

#### Python Wheel Package
```bash
python build_installer.py --type wheel
```

#### Portable Archive
```bash
python build_installer.py --type portable
```

#### Alternative Executable (cx_Freeze)
```bash
python build_installer.py --type cx_freeze
```

## 📦 Package Types Explained

### 1. PyInstaller Executable
- **File**: `dist/boony_app/` (directory with executable)
- **Pros**: Single executable, no Python installation required
- **Cons**: Large file size (~100-200MB)
- **Best for**: End users without Python knowledge

### 2. Python Wheel Package
- **File**: `dist/boony_english_app-1.0.0-py3-none-any.whl`
- **Pros**: Small size, easy to install with pip
- **Cons**: Requires Python installation
- **Best for**: Python developers, server deployment

### 3. Portable Archive
- **File**: `dist/boony_english_app_portable_[os].zip/tar.gz`
- **Pros**: Contains installer script, cross-platform
- **Cons**: Requires Python installation
- **Best for**: Distribution to multiple systems

### 4. cx_Freeze Executable
- **File**: `build/exe.[platform]/`
- **Pros**: Alternative to PyInstaller
- **Cons**: Platform-specific
- **Best for**: When PyInstaller doesn't work

## 🖥️ Platform-Specific Instructions

### Windows

#### Method 1: Using PyInstaller Executable
1. Build: `python build_installer.py --type pyinstaller`
2. Navigate to: `dist/boony_app/`
3. Run: `boony_app.exe`

#### Method 2: Using Installer Script
1. Extract portable archive
2. Run: `python install.py`
3. Use generated batch file: `start_boony.bat`

#### Method 3: Manual Setup
```cmd
pip install -r requirements.txt
python app.py --production
```

### macOS

#### Method 1: Using PyInstaller
```bash
python build_installer.py --type pyinstaller
cd dist/boony_app/
./boony_app
```

#### Method 2: Using Installer Script
```bash
python install.py
# Use generated script: ./start_boony.sh
```

### Linux

#### Method 1: System-wide Installation
```bash
sudo python install.py
# Creates installation in /opt/boony-english-app/
```

#### Method 2: User Installation
```bash
python install.py
# Creates installation in user directory
```

#### Method 3: Using Python Package
```bash
pip install dist/boony_english_app-1.0.0-py3-none-any.whl
boony-app --production
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file with:
```env
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
```

### Database Setup

#### Option 1: Supabase (Recommended)
1. Create account at [supabase.com](https://supabase.com)
2. Create new project
3. Copy database URL to `.env` file
4. Run migrations: `flask db upgrade`

#### Option 2: Local SQLite
- Automatically created if Supabase unavailable
- File location: `offline.db`
- No additional setup required

## 🚀 Running the Application

### Development Mode
```bash
python app.py --debug
```

### Production Mode
```bash
python app.py --production
```

### Custom Host/Port
```bash
python app.py --host 0.0.0.0 --port 8080
```

### Using Gunicorn (Linux/macOS)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📁 Directory Structure

```
boony_web/
├── app.py                 # Main application
├── config.py             # Configuration
├── models.py             # Database models
├── requirements.txt      # Dependencies
├── setup.py             # Python packaging
├── install.py           # Cross-platform installer
├── build_installer.py   # Build automation
├── boony_app.spec      # PyInstaller configuration
├── templates/          # HTML templates
├── static/            # CSS, JS, images
├── assets/           # Application assets
├── data/            # Application data
├── core/           # Core modules
├── services/      # Service modules
└── migrations/   # Database migrations
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Python Version Error
```
Error: Python 3.8 or higher is required
```
**Solution**: Install Python 3.8+ from [python.org](https://python.org)

#### 2. Database Connection Error
```
Failed to connect to Supabase database
```
**Solutions**:
- Check internet connection
- Verify DATABASE_URL in .env file
- Ensure Supabase project is active
- Check IP whitelist in Supabase dashboard

#### 3. Missing Dependencies
```
ModuleNotFoundError: No module named 'flask'
```
**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Port Already in Use
```
Address already in use
```
**Solution**: Use different port
```bash
python app.py --port 8080
```

#### 5. PyInstaller Build Fails
**Solutions**:
- Update PyInstaller: `pip install --upgrade pyinstaller`
- Try cx_Freeze: `python build_installer.py --type cx_freeze`
- Use portable archive instead

### Build Issues

#### Clean Build Cache
```bash
python build_installer.py --clean
```

#### Verbose PyInstaller Output
```bash
pyinstaller --log-level DEBUG boony_app.spec
```

## 📊 Performance Optimization

### Production Deployment

1. **Use Production WSGI Server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Enable Database Connection Pooling**
   - Configure in `config.py`
   - Adjust pool_size based on expected load

3. **Use Reverse Proxy**
   - Nginx or Apache for static files
   - SSL termination
   - Load balancing

### Resource Requirements

- **Minimum**: 512MB RAM, 1GB disk space
- **Recommended**: 2GB RAM, 5GB disk space
- **Database**: PostgreSQL 12+ or SQLite 3.35+

## 🔐 Security Considerations

1. **Change Default Secret Key**
   ```env
   SECRET_KEY=generate-strong-random-key
   ```

2. **Use HTTPS in Production**
   - Configure SSL certificates
   - Use secure database connections

3. **Environment Variables**
   - Never commit .env files
   - Use secure credential storage

4. **Database Security**
   - Use strong passwords
   - Enable SSL connections
   - Regular backups

## 📞 Support

- **Documentation**: This file and inline code comments
- **Issues**: Create GitHub issues for bugs
- **Email**: support@angelgurus.com
- **Website**: https://angelgurus.com

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

---

**Happy Learning with Boony! 🎓**
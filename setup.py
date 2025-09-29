from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "Boony English Learning Web Application"

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

# Additional requirements for packaging and deployment
additional_requirements = [
    'psycopg2-binary>=2.9.0',
    'gunicorn>=20.1.0',
    'python-dotenv>=0.19.0',
    'requests>=2.28.0',
    'sqlalchemy>=1.4.0',
    'alembic>=1.8.0',
    'tabulate>=0.9.0'
]

# Combine requirements
all_requirements = list(set(requirements + additional_requirements))

setup(
    name="boony-english-app",
    version="1.0.0",
    author="Angel Gurus AI",
    author_email="support@angelgurus.com",
    description="An interactive English learning web application with AI-powered features",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/angelgurus/boony-english",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Topic :: Education :: Computer Aided Instruction (CAI)",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Framework :: Flask",
    ],
    python_requires=">=3.8",
    install_requires=all_requirements,
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-flask>=1.2.0',
            'black>=22.0.0',
            'flake8>=4.0.0',
        ],
        'deployment': [
            'pyinstaller>=5.0.0',
            'cx-freeze>=6.0.0',
            'nuitka>=1.0.0',
        ]
    },
    include_package_data=True,
    package_data={
        'boony_english_app': [
            'templates/*',
            'templates/**/*',
            'static/*',
            'static/**/*',
            'assets/*',
            'assets/**/*',
            'data/*',
            'data/**/*',
            'core/data/*',
            'core/data/**/*',
            'migrations/*',
            'migrations/**/*',
            '*.json',
            '*.xlsx',
            '*.db',
        ],
    },
    entry_points={
        'console_scripts': [
            'boony-app=app:main',
            'boony-fetch-data=fetch_user_data:main',
        ],
    },
    zip_safe=False,
)
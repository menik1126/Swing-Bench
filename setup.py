import setuptools
import os
import subprocess
import sys
import platform
from setuptools import setup
from setuptools.command.install import install

def read_requirements(filename):
    """Read requirements from requirements.txt file"""
    requirements = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#') and not line.startswith('-'):
                    requirements.append(line)
    return requirements

def install_ci_tools():
    """Install CI tools like act for GitHub Actions simulation"""
    print("Installing CI tools...")
    
    try:
        # Install act (GitHub Actions local runner)
        system = platform.system().lower()
        
        if system == "linux":
            # For Linux, use curl to install act
            subprocess.run([
                "curl", "-s", 
                "https://raw.githubusercontent.com/nektos/act/master/install.sh", 
                "|", "sudo", "bash"
            ], shell=True, check=True)
            print("✅ act installed successfully via install script")
            
        elif system == "darwin":  # macOS
            try:
                # Try to install via brew
                subprocess.run(["brew", "install", "act"], check=True)
                print("✅ act installed successfully via Homebrew")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("❌ Homebrew not found. Please install Homebrew first or install act manually:")
                print("   curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash")
                
        elif system == "windows":
            try:
                # Try to install via chocolatey
                subprocess.run(["choco", "install", "act-cli"], check=True)
                print("✅ act installed successfully via Chocolatey")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("❌ Chocolatey not found. Please install manually:")
                print("   Visit: https://github.com/nektos/act/releases")
                
        else:
            print(f"❌ Unsupported system: {system}")
            print("   Please install act manually: https://github.com/nektos/act")
            
    except Exception as e:
        print(f"❌ Failed to install act: {e}")
        print("   Please install manually: https://github.com/nektos/act")

    # Install other useful CI tools
    ci_tools = [
        "pre-commit",  # Already in base requirements, but ensure it's there
    ]
    
    for tool in ci_tools:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", tool], check=True)
            print(f"✅ {tool} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {tool}: {e}")

class CustomInstallCommand(install):
    """Custom installation command that installs CI tools when the ci-tools extra is used"""
    def run(self):
        install.run(self)
        # Check if ci-tools extra was requested
        if 'ci-tools' in sys.argv or any('ci-tools' in arg for arg in sys.argv):
            install_ci_tools()

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

# Read base requirements from requirements.txt
base_requirements = [
    'beautifulsoup4',
    'chardet',
    'datasets',
    'docker',
    'ghapi',
    'GitPython',
    'modal',
    'pre-commit',
    'python-dotenv',
    'requests',
    'rich',
    'tenacity',
    'tqdm',
    'unidiff',
]

# Add requirements from requirements.txt if it exists
requirements_txt_deps = read_requirements('requirements.txt')
all_requirements = base_requirements + requirements_txt_deps

setuptools.setup(
    name='Swingbench',
    author='Anonymous',
    author_email='anonymous@anonymous.com',
    description='The official Swingbench package - a benchmark for evaluating LMs on software engineering',
    keywords='nlp, benchmark, code',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=all_requirements,
    extras_require={
        'inference': [
            'anthropic',
            'flash_attn',
            'jedi',
            'openai',
            'peft',
            'protobuf',
            'sentencepiece',
            'tiktoken',
            'torch',
            'transformers',
            'triton',
        ],
        'test': [
            'pytest',
            'pytest-cov',
        ],
        'ci-tools': [
            # Additional Python packages for CI tools
            'pre-commit>=3.0.0',
            'docker>=6.0.0',
            'pyyaml>=6.0',
            'jsonschema>=4.0.0',
            # Note: act and other system-level CI tools will be installed via post-install hooks
        ],
        'all': [
            # All optional dependencies
            'anthropic',
            'flash_attn',
            'jedi',
            'openai',
            'peft',
            'protobuf',
            'sentencepiece',
            'tiktoken',
            'torch',
            'transformers',
            'triton',
            'pytest',
            'pytest-cov',
            'pre-commit>=3.0.0',
            'docker>=6.0.0',
            'pyyaml>=6.0',
            'jsonschema>=4.0.0',
        ]
    },
    cmdclass={
        'install': CustomInstallCommand,
    },
    include_package_data=True,
)
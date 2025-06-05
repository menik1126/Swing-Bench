import setuptools
import os
import subprocess
import sys
import platform
import shutil
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

def check_command_exists(command):
    """Check if a command exists in the system PATH"""
    return shutil.which(command) is not None

def install_docker():
    """Install or check Docker availability"""
    print("🔧 Checking Docker installation...")
    
    if check_command_exists("docker"):
        print("✅ Docker is already installed")
        return True
    
    system = platform.system().lower()
    print(f"🐳 Docker not found. Attempting to install Docker for {system}...")
    
    try:
        if system == "linux":
            # For Ubuntu/Debian systems
            if os.path.exists("/etc/debian_version"):
                print("📥 Installing Docker on Debian/Ubuntu...")
                commands = [
                    "sudo apt-get update",
                    "sudo apt-get install -y ca-certificates curl gnupg",
                    "sudo install -m 0755 -d /etc/apt/keyrings",
                    "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
                    "sudo chmod a+r /etc/apt/keyrings/docker.gpg",
                    'echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
                    "sudo apt-get update",
                    "sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
                ]
                
                for cmd in commands:
                    subprocess.run(cmd, shell=True, check=True)
                
                # Add user to docker group
                subprocess.run(f"sudo usermod -aG docker {os.getenv('USER')}", shell=True, check=True)
                print("✅ Docker installed successfully on Debian/Ubuntu")
                print("⚠️  Please log out and back in for docker group changes to take effect")
                return True
                
            # For CentOS/RHEL systems
            elif os.path.exists("/etc/redhat-release"):
                print("📥 Installing Docker on CentOS/RHEL...")
                commands = [
                    "sudo yum install -y yum-utils",
                    "sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo",
                    "sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
                    "sudo systemctl start docker",
                    "sudo systemctl enable docker"
                ]
                
                for cmd in commands:
                    subprocess.run(cmd, shell=True, check=True)
                
                subprocess.run(f"sudo usermod -aG docker {os.getenv('USER')}", shell=True, check=True)
                print("✅ Docker installed successfully on CentOS/RHEL")
                print("⚠️  Please log out and back in for docker group changes to take effect")
                return True
            else:
                print("❌ Unsupported Linux distribution for automatic Docker installation")
                print("   Please install Docker manually: https://docs.docker.com/engine/install/")
                return False
                
        elif system == "darwin":  # macOS
            print("❌ Docker Desktop for macOS cannot be installed automatically")
            print("   Please download and install Docker Desktop from:")
            print("   https://docs.docker.com/desktop/mac/install/")
            return False
            
        elif system == "windows":
            print("❌ Docker Desktop for Windows cannot be installed automatically")
            print("   Please download and install Docker Desktop from:")
            print("   https://docs.docker.com/desktop/windows/install/")
            return False
            
        else:
            print(f"❌ Unsupported system: {system}")
            print("   Please install Docker manually: https://docs.docker.com/get-docker/")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Docker: {e}")
        print(f"   Please install Docker manually for {system}:")
        if system == "linux":
            print("   https://docs.docker.com/engine/install/")
        elif system == "darwin":
            print("   https://docs.docker.com/desktop/mac/install/")
        elif system == "windows":
            print("   https://docs.docker.com/desktop/windows/install/")
        return False

def install_act():
    """Install act (GitHub Actions local runner)"""
    print("🔧 Installing act (GitHub Actions local runner)...")
    
    if check_command_exists("act"):
        print("✅ act is already installed")
        return True
    
    system = platform.system().lower()
    
    try:
        if system == "linux":
            # For Linux, download and install act binary
            print("📥 Downloading act for Linux...")
            
            # Determine architecture
            arch = platform.machine().lower()
            if arch == "x86_64":
                arch = "x86_64"
            elif arch in ["aarch64", "arm64"]:
                arch = "arm64"
            else:
                print(f"❌ Unsupported architecture: {arch}")
                return False
            
            # Download and install act
            download_commands = [
                f"curl -s https://api.github.com/repos/nektos/act/releases/latest | grep 'browser_download_url.*Linux_{arch}' | cut -d '\"' -f 4 | head -n 1 | xargs -I {{}} curl -L {{}} -o /tmp/act.tar.gz",
                "tar -xzf /tmp/act.tar.gz -C /tmp/",
                "sudo mv /tmp/act /usr/local/bin/",
                "sudo chmod +x /usr/local/bin/act",
                "rm -f /tmp/act.tar.gz"
            ]
            
            for cmd in download_commands:
                subprocess.run(cmd, shell=True, check=True)
                
            print("✅ act installed successfully")
            return True
            
        elif system == "darwin":  # macOS
            if check_command_exists("brew"):
                subprocess.run(["brew", "install", "act"], check=True)
                print("✅ act installed successfully via Homebrew")
                return True
            else:
                print("❌ Homebrew not found. Please install Homebrew first or install act manually:")
                print("   curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash")
                return False
                
        elif system == "windows":
            if check_command_exists("choco"):
                subprocess.run(["choco", "install", "act-cli", "-y"], check=True)
                print("✅ act installed successfully via Chocolatey")
                return True
            elif check_command_exists("winget"):
                subprocess.run(["winget", "install", "nektos.act"], check=True)
                print("✅ act installed successfully via winget")
                return True
            else:
                print("❌ Neither Chocolatey nor winget found.")
                print("   Please install manually from: https://github.com/nektos/act/releases")
                return False
                
        else:
            print(f"❌ Unsupported system: {system}")
            print("   Please install act manually: https://github.com/nektos/act")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install act: {e}")
        print("   Please install manually: https://github.com/nektos/act")
        return False

def install_ci_tools():
    """Install CI tools like Docker and act for GitHub Actions simulation"""
    print("🚀 Installing CI tools for Swing-Bench...")
    
    success_count = 0
    total_tools = 3
    
    # Check/Install Git (prerequisite)
    print("🔧 Checking Git installation...")
    if check_command_exists("git"):
        print("✅ Git is already installed")
        success_count += 1
    else:
        print("❌ Git not found. Please install Git first:")
        print("   https://git-scm.com/downloads")
    
    # Install Docker
    if install_docker():
        success_count += 1
    
    # Install act
    if install_act():
        success_count += 1
    
    # Install Python packages for CI operations
    print("🔧 Installing Python packages for CI operations...")
    ci_packages = [
        "pre-commit>=3.0.0",
        "docker>=6.0.0", 
        "pyyaml>=6.0",
        "jsonschema>=4.0.0",
    ]
    
    package_success = True
    for package in ci_packages:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], 
                         check=True, capture_output=True)
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            package_success = False
    
    print(f"\n📊 Installation Summary: {success_count}/{total_tools} system tools ready")
    
    if success_count == total_tools and package_success:
        print("🎉 All CI tools installed successfully!")
        print("\n💡 You can now run Swing-Bench evaluations with CI integration:")
        print("   export CI_TOOL_NAME=act")
        print("   python swingarena/harness/agent_battle.py --ci_tool_name act ...")
    else:
        print("⚠️  Some tools failed to install. Please install them manually.")
        print("   Check the error messages above for specific instructions.")

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
    name='SwingArena',
    version='0.1.0',
    author='Anonymous',
    author_email='anonymous@anonymous.com',
    description='The official SwingArena package - a benchmark for evaluating LMs on software engineering',
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
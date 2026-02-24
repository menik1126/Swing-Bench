#!/usr/bin/env python3
"""
CI Tools Installation Script for Swing-Bench

This script installs necessary CI tools for Swing-Bench evaluation framework,
including 'act' for GitHub Actions simulation and other related tools.

Usage:
    python install_ci_tools.py
    python install_ci_tools.py --force     # Force reinstall
    python install_ci_tools.py --check     # Check if tools are installed
"""

import subprocess
import sys
import platform
import shutil
import argparse
import os

def check_command_exists(command):
    """Check if a command exists in the system PATH"""
    return shutil.which(command) is not None

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
            
            # Create temp directory and download act
            download_commands = [
                f"curl -s https://api.github.com/repos/nektos/act/releases/latest | grep 'browser_download_url.*Linux_{arch}' | cut -d '\"' -f 4 | head -n 1 | xargs -I {{}} curl -L {{}} -o /tmp/act.tar.gz",
                "tar -xzf /tmp/act.tar.gz -C /tmp/",
                "sudo mv /tmp/act /usr/local/bin/",
                "sudo chmod +x /usr/local/bin/act",
                "rm -f /tmp/act.tar.gz"
            ]
            
            for cmd in download_commands:
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
                
            print("✅ act installed successfully")
            return True
            
        elif system == "darwin":  # macOS
            if check_command_exists("brew"):
                subprocess.run(["brew", "install", "act"], check=True)
                print("✅ act installed successfully via Homebrew")
                return True
            else:
                print("❌ Homebrew not found. Installing via curl...")
                # Fallback to direct installation
                arch = "arm64" if platform.machine() == "arm64" else "x86_64"
                download_commands = [
                    f"curl -s https://api.github.com/repos/nektos/act/releases/latest | grep 'browser_download_url.*Darwin_{arch}' | cut -d '\"' -f 4 | head -n 1 | xargs -I {{}} curl -L {{}} -o /tmp/act.tar.gz",
                    "tar -xzf /tmp/act.tar.gz -C /tmp/",
                    "sudo mv /tmp/act /usr/local/bin/",
                    "sudo chmod +x /usr/local/bin/act",
                    "rm -f /tmp/act.tar.gz"
                ]
                
                for cmd in download_commands:
                    subprocess.run(cmd, shell=True, check=True)
                    
                print("✅ act installed successfully")
                return True
                
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
    except Exception as e:
        print(f"❌ Unexpected error installing act: {e}")
        return False

def install_docker():
    """Ensure Docker is available"""
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
                
                # Start and enable Docker service
                subprocess.run("sudo systemctl start docker", shell=True, check=True)
                subprocess.run("sudo systemctl enable docker", shell=True, check=True)
                
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
                
            # For Arch Linux
            elif os.path.exists("/etc/arch-release"):
                print("📥 Installing Docker on Arch Linux...")
                commands = [
                    "sudo pacman -Syu --noconfirm",
                    "sudo pacman -S --noconfirm docker docker-compose",
                    "sudo systemctl start docker",
                    "sudo systemctl enable docker"
                ]
                
                for cmd in commands:
                    subprocess.run(cmd, shell=True, check=True)
                
                subprocess.run(f"sudo usermod -aG docker {os.getenv('USER')}", shell=True, check=True)
                print("✅ Docker installed successfully on Arch Linux")
                print("⚠️  Please log out and back in for docker group changes to take effect")
                return True
                
            # For other Linux distributions, try generic installation
            else:
                print("📥 Attempting generic Docker installation for Linux...")
                # Try the convenience script
                subprocess.run("curl -fsSL https://get.docker.com -o get-docker.sh", shell=True, check=True)
                subprocess.run("sudo sh get-docker.sh", shell=True, check=True)
                subprocess.run("rm get-docker.sh", shell=True, check=True)
                
                # Add user to docker group and start service
                subprocess.run(f"sudo usermod -aG docker {os.getenv('USER')}", shell=True, check=True)
                subprocess.run("sudo systemctl start docker", shell=True, check=True)
                subprocess.run("sudo systemctl enable docker", shell=True, check=True)
                
                print("✅ Docker installed successfully using convenience script")
                print("⚠️  Please log out and back in for docker group changes to take effect")
                return True
                
        elif system == "darwin":  # macOS
            if check_command_exists("brew"):
                print("📥 Installing Docker Desktop via Homebrew...")
                subprocess.run(["brew", "install", "--cask", "docker"], check=True)
                print("✅ Docker Desktop installed successfully via Homebrew")
                print("⚠️  Please start Docker Desktop manually from Applications folder")
                return True
            else:
                print("❌ Homebrew not found. Docker Desktop for macOS cannot be installed automatically")
                print("   Please download and install Docker Desktop from:")
                print("   https://docs.docker.com/desktop/mac/install/")
                return False
            
        elif system == "windows":
            if check_command_exists("choco"):
                print("📥 Installing Docker Desktop via Chocolatey...")
                subprocess.run(["choco", "install", "docker-desktop", "-y"], check=True)
                print("✅ Docker Desktop installed successfully via Chocolatey")
                print("⚠️  Please restart your computer and start Docker Desktop")
                return True
            elif check_command_exists("winget"):
                print("📥 Installing Docker Desktop via winget...")
                subprocess.run(["winget", "install", "Docker.DockerDesktop"], check=True)
                print("✅ Docker Desktop installed successfully via winget")
                print("⚠️  Please restart your computer and start Docker Desktop")
                return True
            else:
                print("❌ Neither Chocolatey nor winget found.")
                print("   Docker Desktop for Windows cannot be installed automatically")
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
    except Exception as e:
        print(f"❌ Unexpected error installing Docker: {e}")
        return False

def install_git():
    """Ensure Git is available"""
    print("🔧 Checking Git installation...")
    
    if check_command_exists("git"):
        print("✅ Git is already installed")
        return True
    
    print("❌ Git not found. Please install Git first:")
    print("   https://git-scm.com/downloads")
    return False

def install_python_packages():
    """Install Python packages required for CI operations"""
    print("🔧 Installing Python packages for CI operations...")
    
    packages = [
        "pre-commit>=3.0.0",
        "docker>=6.0.0", 
        "pyyaml>=6.0",
        "jsonschema>=4.0.0",
        "requests>=2.25.0",
    ]
    
    success = True
    for package in packages:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], 
                         check=True, capture_output=True)
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            success = False
    
    return success

def check_all_tools():
    """Check if all required tools are installed"""
    print("🔍 Checking CI tools installation status...\n")
    
    tools_status = {}
    
    # Check act
    tools_status['act'] = check_command_exists("act")
    print(f"act (GitHub Actions): {'✅ Installed' if tools_status['act'] else '❌ Not found'}")
    
    # Check Docker
    tools_status['docker'] = check_command_exists("docker")
    print(f"Docker: {'✅ Installed' if tools_status['docker'] else '❌ Not found'}")
    
    # Check Git
    tools_status['git'] = check_command_exists("git")
    print(f"Git: {'✅ Installed' if tools_status['git'] else '❌ Not found'}")
    
    # Check Python packages
    python_packages = ["docker", "yaml", "jsonschema", "requests"]
    python_status = []
    
    for package in python_packages:
        try:
            __import__(package)
            python_status.append(True)
            print(f"Python {package}: ✅ Installed")
        except ImportError:
            python_status.append(False)
            print(f"Python {package}: ❌ Not found")
    
    tools_status['python_packages'] = all(python_status)
    
    print(f"\n📊 Overall status: {'✅ All tools ready' if all(tools_status.values()) else '❌ Some tools missing'}")
    return all(tools_status.values())

def main():
    parser = argparse.ArgumentParser(description="Install CI tools for Swing-Bench")
    parser.add_argument("--check", action="store_true", help="Check if tools are installed")
    parser.add_argument("--force", action="store_true", help="Force reinstall tools")
    args = parser.parse_args()
    
    if args.check:
        check_all_tools()
        return
    
    print("🚀 Installing CI tools for Swing-Bench...\n")
    
    success_count = 0
    total_steps = 4
    
    # Install Git (prerequisite)
    if install_git():
        success_count += 1
    
    # Install Docker (prerequisite)
    if install_docker():
        success_count += 1
    
    # Install act
    if install_act() or not args.force:
        success_count += 1
    
    # Install Python packages
    if install_python_packages():
        success_count += 1
    
    print(f"\n📊 Installation Summary: {success_count}/{total_steps} components ready")
    
    if success_count == total_steps:
        print("🎉 All CI tools installed successfully!")
        print("\n💡 You can now run Swing-Bench evaluations with CI integration:")
        print("   export CI_TOOL_NAME=act")
        print("   python swingarena/harness/agent_battle.py --ci_tool_name act ...")
    else:
        print("⚠️  Some tools failed to install. Please install them manually.")
        print("   Check the error messages above for specific instructions.")

if __name__ == "__main__":
    main() 
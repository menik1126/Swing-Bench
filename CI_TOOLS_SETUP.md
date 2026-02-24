# CI Tools Setup Guide for Swing-Bench

This guide explains how to set up CI tools required for Swing-Bench evaluation framework, particularly for running GitHub Actions simulations using `act`.

## 📋 Prerequisites

Before installing CI tools, ensure you have:

- **Python 3.8+** with pip
- **Git** (required for repository operations)
- **Docker** (required for act to run GitHub Actions)
- **sudo/admin privileges** (for system-level tool installation)

## 🚀 Quick Installation

### Method 1: Using setup.py with ci-tools extra

Install Swing-Bench with CI tools in one command:

```bash
pip install -e ".[ci-tools]"
```

This will:
- Install all Python dependencies
- Install `act` binary for your system
- Install Docker SDK for Python
- Set up pre-commit hooks

### Method 2: Using the dedicated installer script

Run the standalone CI tools installer:

```bash
python install_ci_tools.py
```

Or check what's already installed:

```bash
python install_ci_tools.py --check
```

Force reinstall everything:

```bash
python install_ci_tools.py --force
```

## 🔧 Manual Installation

If automatic installation fails, you can install tools manually:

### Installing act (GitHub Actions Local Runner)

**Linux:**
```bash
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

**macOS:**
```bash
# Via Homebrew (recommended)
brew install act

# Or via curl
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

**Windows:**
```bash
# Via Chocolatey
choco install act-cli

# Via winget
winget install nektos.act
```

### Installing Docker

- **Linux**: Follow [Docker Engine installation guide](https://docs.docker.com/engine/install/)
- **macOS**: Install [Docker Desktop for Mac](https://docs.docker.com/desktop/mac/install/)
- **Windows**: Install [Docker Desktop for Windows](https://docs.docker.com/desktop/windows/install/)

### Installing Python packages

```bash
pip install pre-commit docker pyyaml jsonschema requests
```

## ✅ Verification

Check if all tools are properly installed:

```bash
# Check individual tools
act --version
docker --version
git --version

# Check via our script
python install_ci_tools.py --check
```

Expected output:
```
🔍 Checking CI tools installation status...

act (GitHub Actions): ✅ Installed
Docker: ✅ Installed  
Git: ✅ Installed
Python docker: ✅ Installed
Python yaml: ✅ Installed
Python jsonschema: ✅ Installed
Python requests: ✅ Installed

📊 Overall status: ✅ All tools ready
```

## 🎯 Usage in Swing-Bench

Once CI tools are installed, you can use them in Swing-Bench evaluations:

### Basic Usage

```bash
export CI_TOOL_NAME=act
python swingarena/harness/agent_battle.py \
    --ci_tool_name act \
    --dataset_name SwingBench/SwingBench \
    --split Rust \
    --model_lhs "gpt-4" \
    --model_rhs "claude-3"
```

### Advanced Configuration

```bash
# Use custom Docker image for act
export ACT_DOCKER_IMAGE="catthehacker/ubuntu:act-latest"

# Set working directory
export SWING_TESTBED_PATH="/path/to/workdir"
export SWING_REPOS_DIR_PATH="/path/to/repos"

./scripts/examples/battle_template.sh
```

## 🐛 Troubleshooting

### Common Issues

**1. "act: command not found"**
- Ensure `/usr/local/bin` is in your PATH
- Try running `which act` to check installation location
- Reinstall using: `python install_ci_tools.py --force`

**2. "Docker daemon not running"**
- Start Docker service: `sudo systemctl start docker` (Linux)
- Start Docker Desktop (macOS/Windows)
- Check: `docker ps`

**3. "Permission denied" errors**
- Ensure your user is in docker group: `sudo usermod -aG docker $USER`
- Log out and back in, or run: `newgrp docker`

**4. act fails with "Error: unable to find GitHub workflow"**
- This is normal for repositories without `.github/workflows/`
- Swing-Bench handles this gracefully

### System-Specific Notes

**Linux:**
- May require `sudo` for act installation
- Docker group membership needed for non-root Docker access

**macOS:**
- Homebrew is the preferred installation method
- May need to accept Xcode license: `sudo xcodebuild -license`

**Windows:**
- Requires PowerShell or WSL for some operations
- Docker Desktop must be running

## 📚 Additional Resources

- [act GitHub Repository](https://github.com/nektos/act)
- [Docker Installation Guides](https://docs.docker.com/get-docker/)
- [Swing-Bench Documentation](./README.md)

## 🆘 Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Run diagnostics: `python install_ci_tools.py --check`
3. Check Docker status: `docker ps`
4. Verify act installation: `act --version`
5. Open an issue on the Swing-Bench repository

## 🔄 Updates

To update CI tools:

```bash
# Update act
python install_ci_tools.py --force

# Update Python packages
pip install --upgrade pre-commit docker pyyaml jsonschema
``` 
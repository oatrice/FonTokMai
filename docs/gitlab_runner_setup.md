# Setup Local GitLab Runner (Docker Executor)

This guide provides instructions on how to install and register a local GitLab Runner configured to use the Docker executor. This setup ensures your host machine stays clean while jobs run in isolated, ephemeral Docker containers, mirroring the behavior of GitLab Shared Runners.

## 🎯 Objective
Run GitLab CI/CD jobs locally for development or specific tasks without cluttering the host machine with project dependencies.

## 1. Prerequisites
- **Docker** must be installed and the daemon running on your host machine.
- Obtain your **GitLab URL** and **Registration Token** from your project or group under **Settings > CI/CD > Runners**.

## 2. Installation

Follow the installation instructions for your respective operating system.

### macOS (Recommended)
Use Homebrew to install and start the GitLab Runner:
```bash
brew install gitlab-runner
brew services start gitlab-runner
```

### Linux
Download the binary, make it executable, and install it as a service:
```bash
sudo curl -L --output /usr/local/bin/gitlab-runner https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-linux-amd64
sudo chmod +x /usr/local/bin/gitlab-runner
sudo useradd --comment 'GitLab Runner' --create-home gitlab-runner --shell /bin/bash
sudo gitlab-runner install --user=gitlab-runner --working-directory=/home/gitlab-runner
sudo gitlab-runner start
```

### Windows
Use PowerShell (Run as Administrator) to download and start the service:
```powershell
New-Item -Path "C:\GitLab-Runner" -ItemType Directory
Invoke-WebRequest -Uri "https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-windows-amd64.exe" -OutFile "C:\GitLab-Runner\gitlab-runner.exe"
cd C:\GitLab-Runner
.\gitlab-runner.exe install
.\gitlab-runner.exe start
```

## 3. Registration

Register the runner with the Docker executor using the following command. Replace `<YOUR_TOKEN>` with the token obtained from the prerequisites.

```bash
gitlab-runner register \
  --non-interactive \
  --url "https://gitlab.com/" \
  --registration-token "<YOUR_TOKEN>" \
  --executor "docker" \
  --docker-image alpine:latest \
  --description "local-docker-runner" \
  --tag-list "docker,local,mac" \
  --run-untagged="true" \
  --locked="false"
```
*Note: Adjust the tags (`mac`, `linux`, `windows`) appropriately depending on your host OS if you want to target OS-specific pipelines.*

## 4. Advanced Configuration (Optional)

To support Docker-in-Docker (DinD) or caching, update your `config.toml` file to bind the Docker socket.
- **macOS/Linux**: `~/.gitlab-runner/config.toml` or `/etc/gitlab-runner/config.toml`
- **Windows**: `C:\GitLab-Runner\config.toml`

Add the following inside the `[runners.docker]` section:
```toml
[[runners]]
  [runners.docker]
    volumes = ["/var/run/docker.sock:/var/run/docker.sock", "/cache"]
```

## ✅ Verification

1. Run `gitlab-runner verify` to ensure the runner is connected.
2. Check the GitLab UI under **Settings > CI/CD > Runners** to see the runner listed with a green indicator.
3. Trigger a pipeline that targets the `docker` and `local` tags and verify it runs successfully inside a Docker container on the host.

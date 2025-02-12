# Jenkins Docker Permissions Guide
Date: January 5, 2025

## Problem Description
Common Jenkins pipeline errors related to Docker permissions:
```
permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock
```

## Solution Steps

### 1. Add Jenkins User to Docker Group

```bash
# Connect to your EC2 instance
ssh -i your-key.pem ubuntu@54.84.182.6

# Add jenkins user to docker group
sudo usermod -aG docker jenkins

# Verify group membership
groups jenkins
```

Expected output should include 'docker' in the groups list.

### 2. Set Docker Socket Permissions

```bash
# Check current permissions
ls -l /var/run/docker.sock

# Set proper permissions if needed
sudo chmod 666 /var/run/docker.sock

# Make permissions persistent
sudo sh -c 'echo "%docker ALL=(ALL) NOPASSWD: /usr/bin/docker" >> /etc/sudoers'
```

### 3. Fix Workspace Permissions

```bash
# Set Jenkins as owner of workspace
sudo chown -R jenkins:jenkins /var/lib/jenkins/workspace/

# Set proper permissions
sudo chmod -R 755 /var/lib/jenkins/workspace/
```

### 4. Restart Services

```bash
# Restart Docker
sudo systemctl restart docker

# Restart Jenkins
sudo systemctl restart jenkins

# Verify both services are running
sudo systemctl status docker
sudo systemctl status jenkins
```

### 5. Verify Docker Access

```bash
# Switch to jenkins user
sudo su - jenkins

# Test docker access
docker ps

# Test docker-compose
docker compose version
```

### 6. Update Docker Compose Configuration

1. Remove obsolete version field from docker-compose.yaml:

Before:
```yaml
version: '3'
services:
  ...
```

After:
```yaml
services:
  ...
```

2. Verify docker-compose.yaml structure:
```bash
docker compose -f docker/docker-compose.yaml config
```

### 7. Jenkins Pipeline Adjustments

Add these parameters to your Jenkinsfile docker commands if needed:

```groovy
stage('Build and Test Locally') {
    steps {
        script {
            sh """
                # Add -u flag to run as current user
                docker compose -f docker/docker-compose.yaml build --no-cache
                docker compose -f docker/docker-compose.yaml up -d
                
                # Wait for containers
                sleep 30
                
                # Check status
                docker ps -a
            """
        }
    }
}
```

## Troubleshooting

### 1. Permission Issues Persist
If permission issues continue after following the above steps:

```bash
# Check SELinux status (if applicable)
getenforce

# Temporarily disable SELinux
sudo setenforce 0

# Check AppArmor status (Ubuntu)
sudo aa-status

# Add more explicit permissions
sudo setfacl -m user:jenkins:rw /var/run/docker.sock
```

### 2. Docker Service Issues
If Docker service isn't starting properly:

```bash
# Check Docker daemon logs
sudo journalctl -fu docker

# Verify Docker daemon configuration
sudo cat /etc/docker/daemon.json

# Reset Docker daemon
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 3. Workspace Issues
If workspace permission issues occur:

```bash
# Full reset of workspace permissions
sudo find /var/lib/jenkins/workspace/ -type d -exec chmod 755 {} \;
sudo find /var/lib/jenkins/workspace/ -type f -exec chmod 644 {} \;
```

## Security Considerations

1. Regular Maintenance:
   - Regularly audit docker group members
   - Monitor docker.sock permissions
   - Review Jenkins job permissions

2. Best Practices:
   - Use least privilege principle
   - Consider using Docker-in-Docker alternatives
   - Implement proper logging and monitoring

## Verification Steps

After implementing all changes:

1. Check Service Status:
```bash
sudo systemctl status jenkins
sudo systemctl status docker
```

2. Verify Permissions:
```bash
ls -l /var/run/docker.sock
groups jenkins
ls -l /var/lib/jenkins/workspace/
```

3. Test Docker Commands:
```bash
sudo su - jenkins -c "docker ps"
sudo su - jenkins -c "docker compose version"
```

## Important Directories and Files

```
/var/run/docker.sock           # Docker daemon socket
/var/lib/jenkins/workspace/    # Jenkins workspace
/etc/group                     # Group membership
/etc/sudoers                   # Sudo permissions
docker/docker-compose.yaml     # Your docker-compose configuration
```

## Command Quick Reference

```bash
# Add to docker group
sudo usermod -aG docker jenkins

# Restart services
sudo systemctl restart docker jenkins

# Check permissions
ls -l /var/run/docker.sock

# Test docker access
sudo su - jenkins -c "docker ps"

# Full workspace reset
sudo chown -R jenkins:jenkins /var/lib/jenkins/workspace/
```

Remember to always verify permissions and service status after making these changes, and maintain proper security practices while granting access to the Docker daemon.

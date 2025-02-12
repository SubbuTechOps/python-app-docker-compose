# Helm Installation Guide for Jenkins Server
Date: January 5, 2025

## Prerequisites
- Ubuntu/Debian based system
- Root or sudo access
- Running Jenkins server

## Installation Steps

### 1. Add Helm Repository and GPG Key
```bash
# Add Helm's GPG key
curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null

# Install HTTPS transport package
sudo apt-get install apt-transport-https --yes

# Add Helm repository to sources
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
```

### 2. Install Helm
```bash
# Update package list
sudo apt-get update

# Install Helm
sudo apt-get install helm -y
```

### 3. Verify Installation
```bash
# Check Helm version
helm version
```

### 4. Configure Helm for Jenkins User

```bash
# Switch to Jenkins user
sudo su - jenkins

# Add Helm repositories
helm repo add stable https://charts.helm.sh/stable
helm repo update

# Exit jenkins user
exit
```

### 5. Set Required Permissions
```bash
# Set proper ownership for Kubernetes config
sudo chown -R jenkins:jenkins /var/lib/jenkins/.kube

# Set proper ownership for Helm config
sudo chown -R jenkins:jenkins /var/lib/jenkins/.config

# Set proper permissions
sudo chmod 700 /var/lib/jenkins/.kube
sudo chmod 700 /var/lib/jenkins/.config
```

### 6. Verify Installation as Jenkins User
```bash
# Switch to Jenkins user
sudo su - jenkins

# Verify Helm installation
helm version

# List repositories
helm repo list
```

## Troubleshooting

### 1. Permission Issues
If you encounter permission issues:
```bash
sudo chown -R jenkins:jenkins /var/lib/jenkins
sudo chmod -R 755 /var/lib/jenkins
```

### 2. Repository Issues
If Helm can't reach repositories:
```bash
helm repo remove stable
helm repo add stable https://charts.helm.sh/stable
helm repo update
```

### 3. Command Not Found
If 'helm' command is not found after installation:
```bash
# Check if helm binary exists
which helm

# If needed, create symlink
sudo ln -s /usr/local/bin/helm /usr/bin/helm
```

## Verification Steps

After installation, verify these points:
1. Helm version shows correctly
2. Jenkins user can run helm commands
3. Helm repositories are accessible
4. Proper permissions are set

## Common Commands

```bash
# Check version
helm version

# List repositories
helm repo list

# Update repositories
helm repo update

# Search for charts
helm search repo stable

# List installed releases
helm list --all-namespaces
```

## Important Directories

```
/usr/local/bin/helm          # Helm binary location
/var/lib/jenkins/.kube       # Kubernetes config directory
/var/lib/jenkins/.config     # Helm config directory
```

## Regular Maintenance

1. Update Helm regularly:
```bash
sudo apt-get update
sudo apt-get upgrade helm
```

2. Update repositories:
```bash
helm repo update
```

3. Clean up old releases:
```bash
helm list --all-namespaces | grep DELETED
helm delete [release-name] -n [namespace]
```

Remember to always test Helm commands as the Jenkins user after installation to ensure proper functionality in your CI/CD pipeline.

# Complete Guide: Jenkins and GitHub Integration
Date: January 5, 2025

## Table of Contents
1. Prerequisites
2. GitHub Setup
3. Jenkins Configuration
4. Pipeline Setup
5. Testing and Verification
6. Troubleshooting
7. Maintenance

## 1. Prerequisites
- Running Jenkins server (http://54.84.182.6:8080)
- GitHub account with admin access to repository
- AWS EC2 instance running Jenkins (t2.medium)
- Required Jenkins plugins installed:
  - GitHub plugin
  - Git plugin
  - Pipeline plugin

## 2. GitHub Setup

### 2.1 Create Personal Access Token (PAT)
1. Go to GitHub → Settings → Developer Settings
2. Navigate to Personal Access Tokens → Tokens (classic)
3. Click "Generate new token (classic)"
4. Configure token:
   ```
   Token name: Jenkins-Integration
   Permissions required:
   - repo (all)
   - admin:repo_hook
   ```
5. Click Generate and copy the token immediately

### 2.2 Configure Repository Webhook
1. Go to your GitHub repository (e.g., github.com/SubbuTechOps/ecommerce-app)
2. Navigate to Settings → Webhooks
3. Click "Add webhook"
4. Configure webhook:
   ```
   Payload URL: http://54.84.182.6:8080/github-webhook/
   Content Type: application/json
   Events: Just the push event
   ```
5. Click "Add webhook"

## 3. Jenkins Configuration

### 3.1 Configure GitHub Server in Jenkins
1. Go to Jenkins Dashboard → Manage Jenkins → System
2. Scroll to GitHub section
3. Click "Add GitHub Server"
4. Configure:
   ```
   Name: GitHub
   API URL: https://api.github.com
   ```

### 3.2 Add GitHub Credentials
1. In GitHub Server configuration:
2. Credentials → Add → Jenkins
3. Configure credential:
   ```
   Kind: GitHub Personal Access Token
   ID: github-pat
   Description: GitHub PAT for Jenkins
   Token: [Your PAT token]
   ```
4. Click Add
5. Test connection to verify

## 4. Pipeline Setup

### 4.1 Create New Pipeline
1. Jenkins Dashboard → New Item
2. Enter name: "ecommerce-app-pipeline"
3. Select "Pipeline"
4. Click OK

### 4.2 Configure Pipeline General Settings
1. Check "GitHub project"
2. Add Project URL:
   ```
   https://github.com/SubbuTechOps/ecommerce-app
   ```

### 4.3 Configure Pipeline Build Triggers
1. In Build Triggers section
2. Check "GitHub hook trigger for GITScm polling"

### 4.4 Configure Pipeline Definition
1. Select "Pipeline script from SCM"
2. Configure SCM:
   ```
   SCM: Git
   Repository URL: https://github.com/SubbuTechOps/ecommerce-app-three-tier.git
   Credentials: [Select your GitHub credentials]
   Branch Specifier: */main
   Script Path: Jenkinsfile
   ```
3. Click Save

### 4.5 Jenkinsfile Configuration
Create/update Jenkinsfile in your repository:

```groovy
pipeline {
    agent any
    
    environment {
        AWS_ACCOUNT_ID = '017820683847'
        AWS_DEFAULT_REGION = 'us-east-1'
        IMAGE_REPO_NAME = 'ecommerce-app'
        IMAGE_TAG = "${BUILD_NUMBER}"
        REPOSITORY_URI = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/${IMAGE_REPO_NAME}"
        HELM_RELEASE_NAME = 'ecommerce'
        HELM_CHART_PATH = './helm/ecommerce-app'
    }
    
    triggers {
        githubPush()
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build and Test Locally') {
            steps {
                script {
                    sh """
                        docker compose -f docker/docker-compose.yaml build
                        docker compose -f docker/docker-compose.yaml up -d
                        sleep 30
                        docker ps -a | grep 'ecommerce-db'
                        docker ps -a | grep 'docker-backend-1'
                    """
                }
            }
        }
        
        stage('Tag and Push to ECR') {
            steps {
                withCredentials([string(credentialsId: 'aws-access', variable: 'AWS_ACCESS_KEY')]) {
                    script {
                        sh """
                            aws ecr get-login-password --region ${AWS_DEFAULT_REGION} | docker login --username AWS --password-stdin ${REPOSITORY_URI}
                            docker tag docker-backend-1:latest ${REPOSITORY_URI}:backend-${IMAGE_TAG}
                            docker push ${REPOSITORY_URI}:backend-${IMAGE_TAG}
                        """
                    }
                }
            }
        }
        
        stage('Deploy to EKS') {
            steps {
                withCredentials([string(credentialsId: 'aws-access', variable: 'AWS_ACCESS_KEY')]) {
                    script {
                        sh """
                            aws eks update-kubeconfig --name ecommerce-cluster --region ${AWS_DEFAULT_REGION}
                            
                            helm upgrade --install ${HELM_RELEASE_NAME}-db ${HELM_CHART_PATH} \
                                --namespace ecommerce \
                                --create-namespace \
                                --set mysql.name=ecommerce-db \
                                --wait --timeout 5m
                            
                            helm upgrade --install ${HELM_RELEASE_NAME}-backend ${HELM_CHART_PATH} \
                                --namespace ecommerce \
                                --set backend.name=docker-backend \
                                --set backend.image.repository=${REPOSITORY_URI} \
                                --set backend.image.tag=backend-${IMAGE_TAG} \
                                --wait --timeout 5m
                        """
                    }
                }
            }
        }
        
        stage('Verify Deployment') {
            steps {
                withCredentials([string(credentialsId: 'aws-access', variable: 'AWS_ACCESS_KEY')]) {
                    script {
                        sh """
                            kubectl get pods -n ecommerce | grep 'ecommerce-db'
                            kubectl get pods -n ecommerce | grep 'docker-backend'
                            kubectl describe pod -n ecommerce -l app=ecommerce-db
                            kubectl describe pod -n ecommerce -l app=docker-backend
                        """
                    }
                }
            }
        }
    }
    
    post {
        always {
            sh """
                docker compose -f docker/docker-compose.yaml down
                docker rmi ${REPOSITORY_URI}:backend-${IMAGE_TAG} || true
            """
        }
        success {
            echo 'Deployment successful!'
        }
        failure {
            echo 'Deployment failed!'
        }
    }
}
```

## 5. Testing and Verification

### 5.1 Test Webhook
1. Make a small change to your repository
2. Commit and push:
   ```bash
   git add .
   git commit -m "test: testing webhook integration"
   git push origin main
   ```
3. Check Jenkins for automatic build trigger

### 5.2 Verify Webhook Delivery
1. Go to GitHub repository → Settings → Webhooks
2. Click on webhook
3. Check "Recent Deliveries"
4. Look for green checkmark

### 5.3 Check Build Status
1. Go to Jenkins pipeline
2. Check Build History
3. View Console Output for details

## 6. Troubleshooting

### 6.1 Common Issues
1. Webhook not triggering:
   - Verify webhook URL
   - Check EC2 security group (port 8080)
   - Verify GitHub can reach Jenkins

2. Build failures:
   - Check Console Output
   - Verify credentials
   - Check Jenkinsfile syntax

### 6.2 Security Group Settings
Ensure EC2 security group allows:
```
Type: Custom TCP
Port: 8080
Source: 0.0.0.0/0
```

## 7. Maintenance

### 7.1 Regular Tasks
- Monitor webhook deliveries
- Review build logs
- Update plugins
- Rotate credentials

### 7.2 Security Best Practices
- Use specific IP ranges in security groups
- Rotate PAT regularly
- Review webhook settings
- Monitor access logs

### 7.3 Documentation
- Keep setup documents updated
- Document custom configurations
- Maintain troubleshooting guides

## Important URLs
```
Jenkins URL: http://54.84.182.6:8080
Webhook URL: http://54.84.182.6:8080/github-webhook/
Pipeline URL: http://54.84.182.6:8080/job/ecommerce-app-pipeline/
Repository: https://github.com/SubbuTechOps/ecommerce-app
```

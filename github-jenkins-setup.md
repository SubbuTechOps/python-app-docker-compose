# GitHub Integration Setup in Jenkins
Date: January 5, 2025

## Prerequisites
- Jenkins server is running and accessible
- Admin access to both Jenkins and GitHub
- GitHub repository for your project

## Step 1: Create GitHub Personal Access Token (PAT)
1. Navigate to GitHub Settings
   - Click your profile picture → Settings
   - Go to Developer Settings → Personal Access Tokens
   - Select "Tokens (classic)"

2. Generate New Token
   - Click "Generate new token (classic)"
   - Note: Save the token immediately as it won't be shown again

3. Configure Token Settings
   - Token name: `Jenkins-Integration`
   - Expiration: Set as needed (e.g., 90 days)
   - Required Scopes:
     - `repo` (all repo permissions)
     - `admin:repo_hook`
   - Click "Generate token"
   - Copy the generated token immediately

## Step 2: Configure Jenkins GitHub Integration
1. Access Jenkins System Configuration
   - Login to Jenkins
   - Navigate to Dashboard → Manage Jenkins
   - Click "System Configuration" → "Configure System"

2. Add GitHub Server
   - Scroll to GitHub section
   - Click "Add GitHub Server"
   - Configure the following:
     ```
     Name: GitHub
     API URL: https://api.github.com
     ```

3. Add GitHub Credentials
   - Under Credentials:
     - Click "Add" → Jenkins
     - Select "GitHub Personal Access Token"
     - Fill in the details:
       ```
       Scope: Global
       ID: github-pat
       Description: GitHub PAT for Jenkins
       Token: [Paste your GitHub PAT]
       ```
     - Click "Add"
   - Select the added credentials in the dropdown

4. Test Connection
   - Click "Test connection"
   - Should see "Credentials verified for user [your-github-username]"

## Step 3: Configure Webhook (Optional)
1. Jenkins Side
   - In GitHub Server configuration
   - Check "Manage hooks"
   - Save configuration

2. GitHub Side
   - Go to your GitHub repository
   - Click Settings → Webhooks
   - Click "Add webhook"
   - Configure webhook:
     ```
     Payload URL: https://[your-jenkins-url]/github-webhook/
     Content type: application/json
     Secret: [Optional but recommended for security]
     SSL verification: Enable
     ```
   - Choose events:
     - Select "Just the push event" for basic integration
     - Or "Let me select individual events" for:
       - Push
       - Pull requests
       - Issues (if needed)
   - Click "Add webhook"

## Step 4: Pipeline Configuration
Add this to your Jenkinsfile for GitHub integration:

```groovy
pipeline {
    agent any
    
    triggers {
        githubPush() // Triggers pipeline on GitHub push events
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        // Your other stages...
    }
}
```

## Step 5: Verify Setup
1. Test the Integration
   - Make a small change in your GitHub repository
   - Push the change
   - Verify that Jenkins job is automatically triggered

2. Check Webhook Delivery
   - In GitHub repository settings → Webhooks
   - Click on your webhook
   - Check "Recent Deliveries"
   - Should see green checkmarks for successful deliveries

## Troubleshooting
1. Webhook Issues
   - Ensure Jenkins URL is publicly accessible
   - Check webhook payload URL is correct
   - Verify SSL certificates if using HTTPS
   - Check Jenkins logs for webhook reception

2. Authentication Issues
   - Verify PAT hasn't expired
   - Confirm PAT has correct permissions
   - Check if token is properly saved in Jenkins

3. Pipeline Trigger Issues
   - Verify pipeline configuration
   - Check if webhook is properly configured
   - Ensure branch names match between GitHub and Jenkins

## Security Best Practices
1. Token Management
   - Use tokens with minimum required permissions
   - Rotate tokens periodically
   - Use different tokens for different integrations

2. Webhook Security
   - Always use HTTPS
   - Configure webhook secret
   - Limit webhook events to only what's needed

3. Access Control
   - Use Jenkins role-based access control
   - Limit access to credentials
   - Regularly audit access permissions

## Maintenance
1. Regular Tasks
   - Monitor token expiration
   - Review webhook deliveries
   - Update plugins regularly
   - Audit access and permissions

2. Backup Considerations
   - Backup Jenkins credentials
   - Document token configurations
   - Keep setup instructions updated

## Additional Resources
- [Jenkins GitHub Plugin Documentation](https://plugins.jenkins.io/github/)
- [GitHub Webhook Documentation](https://docs.github.com/webhooks)
- [Jenkins Security Best Practices](https://www.jenkins.io/doc/book/security/)

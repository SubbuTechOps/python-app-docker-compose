#!/bin/bash

# Create main helm directory
mkdir -p helm/ecommerce-app

# Move to helm directory
cd helm/ecommerce-app

# Create templates directory and its subdirectories separately
mkdir -p templates/configmaps
mkdir -p templates/secrets
mkdir -p templates/deployments
mkdir -p templates/services
mkdir -p templates/storage

# Create Chart.yaml
cat > Chart.yaml << EOF
apiVersion: v2
name: ecommerce-app
description: E-commerce application with Python backend and MySQL
version: 0.1.0
type: application
EOF

# Create values.yaml
touch values.yaml

# Create template files
touch templates/configmaps/backend-config.yaml
touch templates/secrets/backend-secret.yaml
touch templates/secrets/mysql-secret.yaml
touch templates/deployments/backend-deployment.yaml
touch templates/deployments/mysql-deployment.yaml
touch templates/services/backend-service.yaml
touch templates/services/mysql-service.yaml
touch templates/storage/mysql-pv.yaml
touch templates/storage/mysql-pvc.yaml

echo "Helm chart directory structure created successfully!"
echo "Directory structure:"
tree

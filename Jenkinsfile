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
                        # Create frontend directory in Dockerfile if not exists
                        if ! grep -q "RUN mkdir /frontend" Dockerfile; then
                            sed -i '/RUN apt-get update/a RUN mkdir /frontend' Dockerfile
                        fi
                        
                        docker compose -f docker/docker-compose.yaml build
                        docker compose -f docker/docker-compose.yaml up -d
                        
                        echo "Waiting for containers to be healthy..."
                        sleep 30
                        
                        docker ps -a | grep 'ecommerce-db'
                        docker ps -a | grep 'ecommerce-app-backend'
                    """
                }
            }
        }
        
        stage('Tag and Push to ECR') {
            steps {
                withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                    script {
                        sh """
                            aws ecr get-login-password --region ${AWS_DEFAULT_REGION} | docker login --username AWS --password-stdin ${REPOSITORY_URI}
                            
                            docker tag ecommerce-app-backend:latest ${REPOSITORY_URI}:backend-${IMAGE_TAG}
                            docker push ${REPOSITORY_URI}:backend-${IMAGE_TAG}
                            
                            # Tag as latest for reference
                            docker tag ecommerce-app-backend:latest ${REPOSITORY_URI}:backend-latest
                            docker push ${REPOSITORY_URI}:backend-latest
                        """
                    }
                }
            }
        }
        
        stage('Deploy to EKS') {
            steps {
                withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                    script {
                        sh """
                            aws eks update-kubeconfig --name demo-eks-cluster --region ${AWS_DEFAULT_REGION}
                            
                            # Check cluster and storage status
                            echo "Checking cluster and storage status..."
                            kubectl get nodes
                            kubectl get sc
                            kubectl get pvc -n ecommerce || true
                            
                            # Clean up any failed deployments
                            echo "Cleaning up any failed deployments..."
                            helm uninstall ${HELM_RELEASE_NAME}-db -n ecommerce || true
                            helm uninstall ${HELM_RELEASE_NAME}-backend -n ecommerce || true
                            kubectl delete pvc --all -n ecommerce || true
                            
                            echo "Waiting for cleanup to complete..."
                            sleep 10
                            
                            # Deploy MySQL StatefulSet
                            echo "Deploying MySQL StatefulSet..."
                            helm upgrade --install ${HELM_RELEASE_NAME}-db ${HELM_CHART_PATH} \
                                --namespace ecommerce \
                                --create-namespace \
                                --wait \
                                --timeout 3m
                            
                            # Wait for MySQL to be ready
                            echo "Waiting for MySQL to be ready..."
                            kubectl wait --for=condition=ready pod -l app=ecommerce-db -n ecommerce --timeout=180s
                            
                            # Verify MySQL deployment
                            echo "Verifying MySQL deployment..."
                            kubectl get statefulset,pod,svc,pvc -n ecommerce
                            
                            # Deploy backend with explicit image settings
                            echo "Deploying backend..."
                            helm upgrade --install ${HELM_RELEASE_NAME}-backend ${HELM_CHART_PATH} \
                                --namespace ecommerce \
                                --set backend.image.repository=${REPOSITORY_URI} \
                                --set backend.image.tag=backend-${IMAGE_TAG} \
                                --wait \
                                --timeout 3m
                            
                            # Final verification
                            echo "Final deployment status:"
                            kubectl get all -n ecommerce
                            kubectl get pods -n ecommerce -o wide
                        """
                    }
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                    script {
                        sh """
                            # Check backend logs
                            echo "Checking backend logs..."
                            BACKEND_POD=\$(kubectl get pod -n ecommerce -l app=ecommerce-backend -o jsonpath='{.items[0].metadata.name}')
                            kubectl logs \$BACKEND_POD -n ecommerce
                            
                            # Check MySQL StatefulSet
                            echo "Checking MySQL StatefulSet..."
                            kubectl describe statefulset ${HELM_RELEASE_NAME}-db-mysql -n ecommerce
                            
                            # Check Services
                            echo "Checking Services..."
                            kubectl get svc -n ecommerce
                            
                            # Check ConfigMaps and Secrets
                            echo "Checking ConfigMaps and Secrets..."
                            kubectl get configmap,secret -n ecommerce
                        """
                    }
                }
            }
        }
    }
    
    post {
        always {
            script {
                sh """
                    docker compose -f docker/docker-compose.yaml down
                    docker rmi ${REPOSITORY_URI}:backend-${IMAGE_TAG} || true
                    docker rmi ${REPOSITORY_URI}:backend-latest || true
                """
            }
        }
        success {
            echo 'Deployment successful!'
        }
        failure {
            echo 'Deployment failed!'
            
            script {
                sh """
                    echo "Collecting logs for debugging..."
                    kubectl get pods -n ecommerce
                    kubectl describe pods -n ecommerce
                    kubectl logs -n ecommerce -l app=ecommerce-backend --tail=100
                """
            }
        }
    }
}
pipeline {
    agent any
    
    environment {
        AWS_ACCOUNT_ID = '017820683847'
        AWS_DEFAULT_REGION = 'us-east-1'
        IMAGE_REPO_NAME = 'ecommerce-app'
        GIT_COMMIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
        IMAGE_TAG = "${GIT_COMMIT_SHORT}-${BUILD_NUMBER}"
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
                        echo "Building image with tag: ${IMAGE_TAG}"
                        docker build -t ecommerce-app-backend:${IMAGE_TAG} -f backend/Dockerfile.backend .
                        
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
                            
                            docker tag ecommerce-app-backend:${IMAGE_TAG} ${REPOSITORY_URI}:backend-${IMAGE_TAG}
                            docker push ${REPOSITORY_URI}:backend-${IMAGE_TAG}
                            
                            docker tag ecommerce-app-backend:${IMAGE_TAG} ${REPOSITORY_URI}:backend-latest
                            docker push ${REPOSITORY_URI}:backend-latest
                            
                            echo "Pushed image: ${REPOSITORY_URI}:backend-${IMAGE_TAG}"
                        """
                    }
                }
            }
        }
        
        stage('Deploy Database') {
            steps {
                withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                    script {
                        sh """
                            aws eks update-kubeconfig --name demo-eks-cluster --region ${AWS_DEFAULT_REGION}
                            
                            echo "Cleaning up existing resources..."
                            helm uninstall ${HELM_RELEASE_NAME}-db -n ecommerce || true
                            kubectl delete pvc --all -n ecommerce || true
                            
                            echo "Waiting for cleanup..."
                            sleep 20
                            
                            echo "Deploying MySQL..."
                            helm install ${HELM_RELEASE_NAME}-db ${HELM_CHART_PATH} \
                                --namespace ecommerce \
                                --create-namespace \
                                --set backend.enabled=false \
                                --wait \
                                --timeout 5m
                            
                            echo "Waiting for MySQL to be ready..."
                            kubectl wait --for=condition=ready pod -l app=ecommerce-db -n ecommerce --timeout=300s
                        """
                    }
                }
            }
        }
        
        stage('Deploy Backend') {
            steps {
                withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                    script {
                        sh """
                            echo "Deploying backend with image: ${IMAGE_TAG}"
                            
                            helm upgrade --install ${HELM_RELEASE_NAME}-backend ${HELM_CHART_PATH} \
                                --namespace ecommerce \
                                --set database.enabled=false \
                                --set backend.image.repository=${REPOSITORY_URI} \
                                --set backend.image.tag=backend-${IMAGE_TAG} \
                                --wait \
                                --timeout 5m || {
                                    echo "Backend deployment failed. Checking pods..."
                                    kubectl get pods -n ecommerce
                                    kubectl describe pods -n ecommerce
                                    exit 1
                                }
                            
                            echo "Verifying backend deployment..."
                            kubectl get all -n ecommerce
                            kubectl logs -l app=ecommerce-backend -n ecommerce --tail=100
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
                    docker compose -f docker/docker-compose.yaml down || true
                    docker rmi ${REPOSITORY_URI}:backend-${IMAGE_TAG} || true
                    docker rmi ${REPOSITORY_URI}:backend-latest || true
                    docker rmi ecommerce-app-backend:${IMAGE_TAG} || true
                """
            }
        }
        success {
            echo "Deployment successful! Deployed image: ${REPOSITORY_URI}:backend-${IMAGE_TAG}"
        }
        failure {
            echo 'Deployment failed!'
            script {
                sh """
                    echo "=== Deployment Failure Debug Info ==="
                    echo "Failed image tag: ${IMAGE_TAG}"
                    kubectl get pods -n ecommerce || true
                    kubectl describe pods -n ecommerce || true
                    kubectl logs -l app=ecommerce-backend -n ecommerce --tail=100 || true
                """
            }
        }
    }
}
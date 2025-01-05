pipeline {
    agent any
    
    environment {
        AWS_ACCOUNT_ID = '017820683847'
        AWS_DEFAULT_REGION = 'us-east-1'
        IMAGE_REPO_NAME = 'ecommerce-app'
        GIT_COMMIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
        IMAGE_TAG = "${GIT_COMMIT_SHORT}-${BUILD_NUMBER}"
        REPOSITORY_URI = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/${IMAGE_REPO_NAME}"
    }
    
    stages {
        stage('Build and Test Locally') {
            steps {
                script {
                    sh """
                        echo "Building image with tag: ${IMAGE_TAG}"
                        docker build -t ecommerce-app-backend:${IMAGE_TAG} -f backend/Dockerfile.backend .
                        
                        docker compose -f docker/docker-compose.yaml up -d
                        
                        echo "Waiting for containers to be healthy..."
                        sleep 30
                        
                        docker ps -a
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
                            
                            # Clean up existing resources
                            kubectl delete deployment -n ecommerce --all || true
                            kubectl delete statefulset -n ecommerce --all || true
                            kubectl delete pvc -n ecommerce --all || true
                            helm uninstall ecommerce-db -n ecommerce || true
                            
                            echo "Waiting for cleanup..."
                            sleep 30
                            
                            # Deploy MySQL StatefulSet
                            echo "Deploying MySQL..."
                            helm upgrade --install ecommerce-db ./helm/ecommerce-app \
                                --namespace ecommerce \
                                --create-namespace \
                                --set backend.enabled=false \
                                --set mysql.storageClassName=ebs-sc \
                                --debug \
                                --wait \
                                --timeout 5m
                            
                            # Wait for MySQL to be ready
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
                            # Force pull the new image
                            kubectl delete deployment -n ecommerce -l app=ecommerce-backend || true
                            sleep 10
                            
                            # Deploy backend with new image
                            echo "Deploying backend with image: ${IMAGE_TAG}"
                            helm upgrade --install ecommerce-backend ./helm/ecommerce-app \
                                --namespace ecommerce \
                                --set mysql.enabled=false \
                                --set backend.image.repository=${REPOSITORY_URI} \
                                --set backend.image.tag=backend-${IMAGE_TAG} \
                                --debug \
                                --wait \
                                --timeout 5m
                            
                            # Wait for backend to be ready
                            kubectl rollout status deployment/ecommerce-backend -n ecommerce --timeout=300s
                            
                            echo "Deployment completed. Checking pod status..."
                            kubectl get pods -n ecommerce
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
                    docker rmi ecommerce-app-backend:${IMAGE_TAG} || true
                """
            }
        }
        success {
            echo "Deployment successful!"
        }
        failure {
            echo 'Deployment failed!'
            script {
                withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                    sh """
                        echo "=== Deployment Failure Debug Info ==="
                        aws eks update-kubeconfig --name demo-eks-cluster --region ${AWS_DEFAULT_REGION}
                        kubectl get pods -n ecommerce
                        kubectl describe pods -n ecommerce -l app=ecommerce-backend
                        kubectl logs -l app=ecommerce-backend -n ecommerce --tail=100
                    """
                }
            }
        }
    }
}
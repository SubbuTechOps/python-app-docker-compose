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
        
        stage('Deploy to EKS') {
            steps {
                withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                    script {
                        sh """
                            aws eks update-kubeconfig --name demo-eks-cluster --region ${AWS_DEFAULT_REGION}
                            
                            echo "Checking cluster status..."
                            kubectl get nodes
                            kubectl get sc
                            
                            echo "Cleaning up existing resources..."
                            kubectl delete deployment -n ecommerce --all || true
                            kubectl delete statefulset -n ecommerce --all || true
                            kubectl delete pvc -n ecommerce --all || true
                            helm uninstall ${HELM_RELEASE_NAME}-db -n ecommerce || true
                            helm uninstall ${HELM_RELEASE_NAME}-backend -n ecommerce || true
                            
                            echo "Waiting for cleanup..."
                            sleep 20
                            
                            echo "Deploying MySQL StatefulSet..."
                            helm install ${HELM_RELEASE_NAME}-db ${HELM_CHART_PATH} \
                                --namespace ecommerce \
                                --create-namespace \
                                --set backend.enabled=false \
                                --set mysql.storageClassName=gp2 \
                                --wait \
                                --timeout 5m
                            
                            echo "Waiting for MySQL to be ready..."
                            kubectl wait --for=condition=ready pod -l app=ecommerce-db -n ecommerce --timeout=300s
                            
                            echo "Deploying backend with image tag: ${IMAGE_TAG}"
                            helm install ${HELM_RELEASE_NAME}-backend ${HELM_CHART_PATH} \
                                --namespace ecommerce \
                                --set database.enabled=false \
                                --set backend.image.repository=${REPOSITORY_URI} \
                                --set backend.image.tag=backend-${IMAGE_TAG} \
                                --debug \
                                --wait \
                                --timeout 5m
                            
                            echo "Verifying deployments..."
                            kubectl get all -n ecommerce
                            
                            echo "Checking backend pods..."
                            sleep 30
                            kubectl logs -l app=ecommerce-backend -n ecommerce --tail=100 || true
                            
                            # Verify backend deployment status
                            READY=\$(kubectl get deployment -n ecommerce -l app=ecommerce-backend -o jsonpath='{.items[0].status.readyReplicas}')
                            if [ "\$READY" != "2" ]; then
                                echo "Backend deployment not ready. Checking pod status..."
                                kubectl describe pods -n ecommerce -l app=ecommerce-backend
                                exit 1
                            fi
                        """
                    }
                }
            }
        }
        
        stage('Verify Services') {
            steps {
                withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                    script {
                        sh """
                            echo "Verifying services..."
                            kubectl get svc -n ecommerce
                            
                            echo "Checking backend endpoint..."
                            BACKEND_URL=\$(kubectl get svc -n ecommerce ${HELM_RELEASE_NAME}-backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
                            if [ ! -z "\$BACKEND_URL" ]; then
                                echo "Backend URL: http://\$BACKEND_URL:5000"
                            fi
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
                    aws eks update-kubeconfig --name demo-eks-cluster --region ${AWS_DEFAULT_REGION}
                    echo "Failed image tag: ${IMAGE_TAG}"
                    echo "Pod Status:"
                    kubectl get pods -n ecommerce || true
                    echo "\\nPod Details:"
                    kubectl describe pods -n ecommerce -l app=ecommerce-backend || true
                    echo "\\nPod Logs:"
                    kubectl logs -l app=ecommerce-backend -n ecommerce --tail=100 || true
                    echo "\\nDeployment Status:"
                    kubectl describe deployment -n ecommerce -l app=ecommerce-backend || true
                """
            }
        }
    }
}
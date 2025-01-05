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
                            
                            # Check storage class and PVC status
                            kubectl get sc
                            kubectl get pvc -n ecommerce

                            # Deploy MySQL StatefulSet
                            helm upgrade --install ${HELM_RELEASE_NAME}-db ${HELM_CHART_PATH} \
                                --namespace ecommerce \
                                --create-namespace \
                                --wait --timeout 5m
                            
                            # Check StatefulSet status
                            echo "Checking MySQL StatefulSet status..."
                            kubectl get statefulset -n ecommerce
                            
                            # Wait for StatefulSet to be ready
                            echo "Waiting for MySQL StatefulSet to be ready..."
                            kubectl wait --for=condition=ready pod ${HELM_RELEASE_NAME}-mysql-0 -n ecommerce --timeout=600s
                            
                            # Verify PVC and PV
                            echo "Verifying PVC and PV status..."
                            kubectl get pvc,pv -n ecommerce
                            
                            # Deploy backend with explicit image settings
                            helm upgrade --install ${HELM_RELEASE_NAME}-backend ${HELM_CHART_PATH} \
                                --namespace ecommerce \
                                --set backend.image.repository=${REPOSITORY_URI} \
                                --set backend.image.tag=backend-${IMAGE_TAG} \
                                --wait --timeout 5m
                            
                            # Verify all deployments
                            kubectl get all -n ecommerce
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
                            # Check StatefulSet status
                            kubectl get statefulset -n ecommerce
                            kubectl describe statefulset ${HELM_RELEASE_NAME}-mysql -n ecommerce
                            
                            # Check backend deployment
                            kubectl get pods -n ecommerce | grep 'ecommerce-app-backend'
                            kubectl describe pod -n ecommerce -l app=ecommerce-app-backend
                            
                            # Check PVC and PV status
                            kubectl get pvc,pv -n ecommerce
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
                """
            }
        }
        success {
            echo 'Deployment successful!'
        }
        failure {
            echo 'Deployment failed!'
        }
    }
}
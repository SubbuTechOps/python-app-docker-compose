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
                            aws eks update-kubeconfig --name ecommerce-cluster --region ${AWS_DEFAULT_REGION}
                            
                            helm upgrade --install ${HELM_RELEASE_NAME}-db ${HELM_CHART_PATH} \
                                --namespace ecommerce \
                                --create-namespace \
                                --set mysql.name=ecommerce-db \
                                --wait --timeout 5m
                            
                            helm upgrade --install ${HELM_RELEASE_NAME}-backend ${HELM_CHART_PATH} \
                                --namespace ecommerce \
                                --set backend.name=ecommerce-app-backend \
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
                withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                    script {
                        sh """
                            kubectl get pods -n ecommerce | grep 'ecommerce-db'
                            kubectl get pods -n ecommerce | grep 'ecommerce-app-backend'
                            kubectl describe pod -n ecommerce -l app=ecommerce-db
                            kubectl describe pod -n ecommerce -l app=ecommerce-app-backend
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
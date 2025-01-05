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

                        echo "Starting containers for local testing..."
                        docker compose -f docker/docker-compose.yaml up -d

                        echo "Waiting for containers to be healthy..."
                        for i in {1..10}; do
                            curl -f http://localhost:5000/health && break || sleep 5
                        done

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
                            echo "Logging in to ECR..."
                            aws ecr get-login-password --region ${AWS_DEFAULT_REGION} | docker login --username AWS --password-stdin ${REPOSITORY_URI}

                            echo "Tagging and pushing the image to ECR..."
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
                            echo "Updating kubeconfig for EKS..."
                            aws eks update-kubeconfig --name demo-eks-cluster --region ${AWS_DEFAULT_REGION}

                            echo "Deploying MySQL using Helm..."
                            helm upgrade --install ecommerce-db ./helm/ecommerce-app \
                                --namespace ecommerce \
                                --create-namespace \
                                --set backend.enabled=false \
                                --set mysql.storageClassName=ebs-sc \
                                --debug \
                                --wait \
                                --timeout 5m

                            echo "MySQL Deployment Complete!"
                            kubectl get pods -n ecommerce
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
                        echo "Cleaning up conflicting resources..."
                        kubectl delete deployment ecommerce-backend -n ecommerce || true
                        kubectl delete svc ecommerce-backend -n ecommerce || true

                        echo "Deploying backend using Helm..."
                        helm upgrade --install ecommerce-backend ./helm/ecommerce-app \
                            --namespace ecommerce \
                            --set mysql.enabled=false \
                            --set backend.image.repository=${REPOSITORY_URI} \
                            --set backend.image.tag=backend-${IMAGE_TAG} \
                            --debug --wait --timeout 5m

                        echo "Verifying deployment..."
                        kubectl rollout status deployment/ecommerce-backend -n ecommerce --timeout=300s
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
                    echo "Cleaning up local Docker resources..."
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

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
                       docker build -t ecommerce-app-backend:${IMAGE_TAG} -f backend/Dockerfile.backend .
                       docker compose -f docker/docker-compose.yaml up -d

                       # Health check
                       for i in {1..10}; do
                           curl -f http://localhost:5000/api/health && break || sleep 5
                       done
                       
                       docker ps -a
                   """
               }
           }
       }

       stage('Push to ECR') {
           steps {
               withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                   script {
                       sh """
                           aws ecr get-login-password --region ${AWS_DEFAULT_REGION} | docker login --username AWS --password-stdin ${REPOSITORY_URI}
                           docker tag ecommerce-app-backend:${IMAGE_TAG} ${REPOSITORY_URI}:backend-${IMAGE_TAG}
                           docker push ${REPOSITORY_URI}:backend-${IMAGE_TAG}
                       """
                   }
               }
           }
       }

       stage('Deploy Application') {
           steps {
               withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                   script {
                       sh """
                           aws eks update-kubeconfig --name demo-eks-cluster --region ${AWS_DEFAULT_REGION}

                           # Single Helm deployment for both MySQL and Backend
                           helm upgrade --install ecommerce ./helm/ecommerce-app \
                               --namespace ecommerce \
                               --create-namespace \
                               --set mysql.storageClassName=ebs-sc \
                               --set backend.image.repository=${REPOSITORY_URI} \
                               --set backend.image.tag=backend-${IMAGE_TAG} \
                               --set backend.env.FLASK_APP=wsgi:app \
                               --wait \
                               --timeout 5m
                               --debug

                           # Verify deployments
                           kubectl wait --namespace ecommerce --for=condition=ready pod \
                               -l app=ecommerce-db --timeout=300s
                           kubectl wait --namespace ecommerce --for=condition=ready pod \
                               -l app=ecommerce-backend --timeout=300s

                           echo "Deployment status:"
                           kubectl get pods,svc,deploy,sts -n ecommerce
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
           script {
               withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                   sh """
                       aws eks update-kubeconfig --name demo-eks-cluster --region ${AWS_DEFAULT_REGION}
                       echo "=== Deployment Debug Info ==="
                       kubectl get pods,svc,deploy,sts -n ecommerce
                       kubectl describe pods -n ecommerce -l app=ecommerce-backend
                       kubectl logs -l app=ecommerce-backend -n ecommerce --tail=100
                   """
               }
           }
           echo 'Deployment failed!'
       }
   }
}
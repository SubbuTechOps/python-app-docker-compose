pipeline {
   agent any

   environment {
       AWS_ACCOUNT_ID = '017820683847'
       AWS_DEFAULT_REGION = 'us-east-1'
       IMAGE_REPO_NAME = 'ecommerce-app'
       GIT_COMMIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
       IMAGE_TAG = "${GIT_COMMIT_SHORT}-${BUILD_NUMBER}"
       REPOSITORY_URI = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/${IMAGE_REPO_NAME}"
       NAMESPACE = 'ecommerce'
   }

   stages {
       stage('Build Backend Image') {
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

       stage('Configure Kubernetes') {
           steps {
               withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                   script {
                       sh """
                           aws eks update-kubeconfig --name demo-eks-cluster --region ${AWS_DEFAULT_REGION}
                           
                           # Create namespace if it doesn't exist
                           kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                       """
                   }
               }
           }
       }

       stage('Deploy MySQL') {
           steps {
               withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                   script {
                       // Check if MySQL is already running
                       def mysqlStatus = sh(
                           script: "kubectl get sts -n ${NAMESPACE} ecommerce-mysql -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo '0'",
                           returnStdout: true
                       ).trim()

                       if (mysqlStatus != '1') {
                           echo "MySQL not running or not ready. Deploying MySQL..."
                           sh """
                               helm upgrade --install ecommerce-mysql ./helm/ecommerce-app \
                                   --namespace ${NAMESPACE} \
                                   --set backend.enabled=false \
                                   --set mysql.enabled=true \
                                   --set mysql.storageClassName=ebs-sc \
                                   --wait \
                                   --timeout 5m
                           """
                       } else {
                           echo "MySQL is already running and ready."
                       }

                       // Wait for MySQL to be fully ready
                       sh """
                           kubectl wait --namespace ${NAMESPACE} \
                               --for=condition=ready pod \
                               -l app=ecommerce-db \
                               --timeout=300s
                       """
                   }
               }
           }
       }

       stage('Deploy Backend') {
           steps {
               withAWS(credentials: 'aws-access', region: env.AWS_DEFAULT_REGION) {
                   script {
                       // Clean up old backend deployments
                       sh """
                           kubectl delete deployment -n ${NAMESPACE} -l app=ecommerce-backend --ignore-not-found=true
                           kubectl wait --for=delete deployment -n ${NAMESPACE} -l app=ecommerce-backend --timeout=60s || true
                       """

                       // Deploy new backend
                       sh """
                           helm upgrade --install ecommerce-backend ./helm/ecommerce-app \
                               --namespace ${NAMESPACE} \
                               --set mysql.enabled=false \
                               --set backend.enabled=true \
                               --set backend.image.repository=${REPOSITORY_URI} \
                               --set backend.image.tag=backend-${IMAGE_TAG} \
                               --set backend.env.FLASK_APP=wsgi:app \
                               --set backend.env.FRONTEND_PATH=/app/frontend \
                               --wait \
                               --timeout 5m

                           # Verify backend deployment
                           kubectl wait --namespace ${NAMESPACE} \
                               --for=condition=ready pod \
                               -l app=ecommerce-backend \
                               --timeout=300s
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
                           echo "=== Final Deployment Status ==="
                           kubectl get pods,svc,deploy,sts -n ${NAMESPACE}
                           
                           # Get the LoadBalancer URL
                           echo "Application URL:"
                           kubectl get svc -n ${NAMESPACE} ecommerce-backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
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
                       echo "=== Deployment Debug Info ==="
                       kubectl get pods,svc,deploy,sts -n ${NAMESPACE}
                       echo "=== MySQL Logs ==="
                       kubectl logs -n ${NAMESPACE} -l app=ecommerce-db --tail=100 || true
                       echo "=== Backend Logs ==="
                       kubectl logs -n ${NAMESPACE} -l app=ecommerce-backend --tail=100 || true
                   """
               }
           }
           echo 'Deployment failed!'
       }
   }
}
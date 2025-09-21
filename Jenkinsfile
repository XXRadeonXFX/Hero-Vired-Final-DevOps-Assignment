pipeline {
    agent any
    
    environment {
        AWS_REGION = 'ap-south-1'
        ECR_REPOSITORY = 'flask-app'
        EKS_CLUSTER_NAME = 'flask-app-cluster'
        IMAGE_TAG = "${BUILD_NUMBER}"
        AWS_ACCESS_KEY_ID = credentials('prince-access-key-id')
        AWS_SECRET_ACCESS_KEY = credentials('prince-secret-access-key')
    }
    
    tools {
        terraform 'terraform'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
                    env.GIT_SHORT_COMMIT = env.GIT_COMMIT.take(8)
                }
            }
        }
        
        stage('Get AWS Account Info') {
            steps {
                script {
                    // Get AWS account ID and ECR URL
                    env.AWS_ACCOUNT_ID = sh(returnStdout: true, script: 'aws sts get-caller-identity --query Account --output text').trim()
                    env.ECR_REGISTRY = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                    env.ECR_REPO_URL = "${env.ECR_REGISTRY}/${ECR_REPOSITORY}"
                    echo "AWS Account ID: ${env.AWS_ACCOUNT_ID}"
                    echo "ECR Repository URL: ${env.ECR_REPO_URL}"
                }
            }
        }
        
        stage('Setup Environment') {
            steps {
                script {
                    sh '''
                        # Install kubectl if not present
                        if ! command -v kubectl &> /dev/null; then
                            curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
                            chmod +x kubectl
                            sudo mv kubectl /usr/local/bin/
                        fi
                        
                        # Verify installations
                        terraform version || echo "Terraform not found"
                        kubectl version --client || echo "kubectl not found"
                        aws --version
                        docker --version
                    '''
                }
            }
        }
        
        stage('Infrastructure') {
            steps {
                script {
                    dir('terraform') {
                        sh '''
                            terraform init
                            terraform validate
                            terraform plan -out=tfplan
                            terraform apply -auto-approve tfplan
                            
                            # Get outputs
                            echo "Getting Terraform outputs..."
                            ECR_REPO_URL=$(terraform output -raw ecr_repository_url)
                            echo "ECR_REPO_URL=${ECR_REPO_URL}" >> $WORKSPACE/terraform.env
                            
                            # Update kubeconfig
                            aws eks update-kubeconfig --region ${AWS_REGION} --name ${EKS_CLUSTER_NAME}
                        '''
                    }
                }
            }
        }
        
        stage('Unit Tests') {
            steps {
                script {
                    sh '''
                        # Install Python dependencies
                        python3 -m venv venv
                        source venv/bin/activate
                        pip install -r requirements.txt
                        
                        # Run tests with coverage
                        pytest test_app.py -v --cov=app --cov-report=xml --cov-report=html
                        
                        # Check test results
                        if [ $? -ne 0 ]; then
                            echo "Tests failed!"
                            exit 1
                        fi
                    '''
                }
            }
            post {
                always {
                    // Publish test results if available
                    script {
                        try {
                            publishTestResults testResultsPattern: 'test-results.xml'
                        } catch (Exception e) {
                            echo "No test results to publish"
                        }
                    }
                }
            }
        }
        
        stage('Code Quality') {
            steps {
                script {
                    sh '''
                        source venv/bin/activate
                        
                        # Install quality tools
                        pip install flake8 bandit safety
                        
                        # Run linting
                        flake8 app.py --max-line-length=120 --ignore=E402,W503 || echo "Linting warnings found"
                        
                        # Security scan
                        bandit -r . -f json -o bandit-report.json || echo "Security scan completed with warnings"
                        
                        # Dependency vulnerability check
                        safety check --json --output safety-report.json || echo "Safety check completed"
                    '''
                }
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    // Load terraform outputs if available
                    script {
                        try {
                            def props = readProperties file: 'terraform.env'
                            env.ECR_REPO_URL = props.ECR_REPO_URL
                        } catch (Exception e) {
                            echo "Using environment ECR URL: ${env.ECR_REPO_URL}"
                        }
                    }
                    
                    sh '''
                        # Login to ECR
                        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO_URL}
                        
                        # Build image with multiple tags
                        docker build -t ${ECR_REPO_URL}:${IMAGE_TAG} .
                        docker tag ${ECR_REPO_URL}:${IMAGE_TAG} ${ECR_REPO_URL}:latest
                        docker tag ${ECR_REPO_URL}:${IMAGE_TAG} ${ECR_REPO_URL}:${GIT_SHORT_COMMIT}
                        
                        # Push images
                        docker push ${ECR_REPO_URL}:${IMAGE_TAG}
                        docker push ${ECR_REPO_URL}:latest
                        docker push ${ECR_REPO_URL}:${GIT_SHORT_COMMIT}
                    '''
                }
            }
        }
        
        stage('Deploy to EKS') {
            steps {
                script {
                    sh '''
                        # Update kubeconfig
                        aws eks update-kubeconfig --region ${AWS_REGION} --name ${EKS_CLUSTER_NAME}
                        
                        # Verify cluster connectivity
                        kubectl cluster-info
                        kubectl get nodes
                        
                        # Replace image tag in deployment manifest
                        sed -i "s|IMAGE_TAG|${IMAGE_TAG}|g" k8s/deployment.yaml
                        sed -i "s|ECR_REPO_URL|${ECR_REPO_URL}|g" k8s/deployment.yaml
                        
                        # Apply Kubernetes manifests
                        kubectl apply -f k8s/namespace.yaml
                        kubectl apply -f k8s/deployment.yaml
                        kubectl apply -f k8s/service.yaml
                        kubectl apply -f k8s/hpa.yaml
                        
                        # Wait for deployment to be ready
                        kubectl rollout status deployment/flask-app -n flask-app --timeout=300s
                        
                        # Get service info
                        kubectl get services -n flask-app
                        kubectl get pods -n flask-app
                    '''
                }
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    sh '''
                        # Wait for pods to be ready
                        kubectl wait --for=condition=ready pod -l app=flask-app -n flask-app --timeout=300s
                        
                        # Get service endpoint
                        SERVICE_URL=$(kubectl get service flask-app-service -n flask-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
                        
                        if [ -z "$SERVICE_URL" ]; then
                            # If LoadBalancer not available, use port-forward for testing
                            kubectl port-forward service/flask-app-service 8080:80 -n flask-app &
                            sleep 10
                            SERVICE_URL="localhost:8080"
                        fi
                        
                        # Health check
                        for i in {1..10}; do
                            if curl -f http://${SERVICE_URL}/health; then
                                echo "Health check passed!"
                                break
                            else
                                echo "Health check failed, retrying in 30 seconds..."
                                sleep 30
                            fi
                            
                            if [ $i -eq 10 ]; then
                                echo "Health check failed after 10 attempts"
                                exit 1
                            fi
                        done
                    '''
                }
            }
        }
    }
    
    post {
        always {
            script {
                // Clean up
                sh '''
                    # Clean up Docker images to save space
                    docker image prune -f || echo "Docker cleanup failed"
                    
                    # Deactivate virtual environment
                    deactivate || echo "Virtual environment cleanup"
                '''
            }
            
            // Archive artifacts
            archiveArtifacts artifacts: '**/*.json,**/*.xml,**/*.html', allowEmptyArchive: true
        }
        
        success {
            script {
                echo "Pipeline completed successfully!"
                echo "Application deployed to EKS cluster: ${EKS_CLUSTER_NAME}"
            }
        }
        
        failure {
            script {
                echo "Pipeline failed!"
                
                // Rollback if needed
                sh '''
                    echo "Rolling back deployment..."
                    kubectl rollout undo deployment/flask-app -n flask-app || echo "Rollback failed or not needed"
                '''
            }
        }
    }
}
    
    tools {
        terraform 'terraform'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
                    env.GIT_SHORT_COMMIT = env.GIT_COMMIT.take(8)
                }
            }
        }
        
        stage('Setup Environment') {
            steps {
                script {
                    // Install required tools
                    sh '''
                        # Install kubectl if not present
                        if ! command -v kubectl &> /dev/null; then
                            curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
                            chmod +x kubectl
                            sudo mv kubectl /usr/local/bin/
                        fi
                        
                        # Install AWS CLI if not present
                        if ! command -v aws &> /dev/null; then
                            curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                            unzip awscliv2.zip
                            sudo ./aws/install
                        fi
                        
                        # Verify installations
                        terraform version
                        kubectl version --client
                        aws --version
                        docker --version
                    '''
                }
            }
        }
        
        stage('Infrastructure') {
            steps {
                withCredentials([
                    [$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-credentials']
                ]) {
                    script {
                        dir('terraform') {
                            sh '''
                                terraform init
                                terraform validate
                                terraform plan -out=tfplan
                                terraform apply -auto-approve tfplan
                                
                                # Get outputs
                                echo "Getting Terraform outputs..."
                                ECR_REPO_URL=$(terraform output -raw ecr_repository_url)
                                echo "ECR_REPO_URL=${ECR_REPO_URL}" >> $WORKSPACE/terraform.env
                                
                                # Update kubeconfig
                                aws eks update-kubeconfig --region ${AWS_REGION} --name ${EKS_CLUSTER_NAME}
                            '''
                        }
                    }
                }
            }
        }
        
        stage('Unit Tests') {
            steps {
                script {
                    sh '''
                        # Install Python dependencies
                        python3 -m venv venv
                        source venv/bin/activate
                        pip install -r requirements.txt
                        
                        # Run tests with coverage
                        pytest test_app.py -v --cov=app --cov-report=xml --cov-report=html
                        
                        # Check test results
                        if [ $? -ne 0 ]; then
                            echo "Tests failed!"
                            exit 1
                        fi
                    '''
                }
            }
            post {
                always {
                    // Publish test results
                    publishTestResults testResultsPattern: 'test-results.xml'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'htmlcov',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                }
            }
        }
        
        stage('Code Quality') {
            steps {
                script {
                    sh '''
                        source venv/bin/activate
                        
                        # Install quality tools
                        pip install flake8 bandit safety
                        
                        # Run linting
                        flake8 app.py --max-line-length=120 --ignore=E402,W503
                        
                        # Security scan
                        bandit -r . -f json -o bandit-report.json || true
                        
                        # Dependency vulnerability check
                        safety check --json --output safety-report.json || true
                    '''
                }
            }
        }
        
        stage('Build Docker Image') {
            steps {
                withCredentials([
                    [$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-credentials']
                ]) {
                    script {
                        // Load terraform outputs
                        def props = readProperties file: 'terraform.env'
                        env.ECR_REPO_URL = props.ECR_REPO_URL
                        
                        sh '''
                            # Login to ECR
                            aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO_URL}
                            
                            # Build image with multiple tags
                            docker build -t ${ECR_REPO_URL}:${IMAGE_TAG} .
                            docker tag ${ECR_REPO_URL}:${IMAGE_TAG} ${ECR_REPO_URL}:latest
                            docker tag ${ECR_REPO_URL}:${IMAGE_TAG} ${ECR_REPO_URL}:${GIT_SHORT_COMMIT}
                            
                            # Push images
                            docker push ${ECR_REPO_URL}:${IMAGE_TAG}
                            docker push ${ECR_REPO_URL}:latest
                            docker push ${ECR_REPO_URL}:${GIT_SHORT_COMMIT}
                        '''
                    }
                }
            }
        }
        
        stage('Security Scan') {
            steps {
                script {
                    sh '''
                        # Install Trivy for container scanning
                        if ! command -v trivy &> /dev/null; then
                            sudo apt-get update
                            sudo apt-get install wget apt-transport-https gnupg lsb-release
                            wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
                            echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
                            sudo apt-get update
                            sudo apt-get install trivy
                        fi
                        
                        # Scan the built image
                        trivy image --exit-code 0 --severity HIGH,CRITICAL --format json --output trivy-report.json ${ECR_REPO_URL}:${IMAGE_TAG}
                    '''
                }
            }
        }
        
        stage('Deploy to EKS') {
            steps {
                withCredentials([
                    [$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-credentials']
                ]) {
                    script {
                        sh '''
                            # Update kubeconfig
                            aws eks update-kubeconfig --region ${AWS_REGION} --name ${EKS_CLUSTER_NAME}
                            
                            # Verify cluster connectivity
                            kubectl cluster-info
                            kubectl get nodes
                            
                            # Replace image tag in deployment manifest
                            sed -i "s|IMAGE_TAG|${IMAGE_TAG}|g" k8s/deployment.yaml
                            sed -i "s|ECR_REPO_URL|${ECR_REPO_URL}|g" k8s/deployment.yaml
                            
                            # Apply Kubernetes manifests
                            kubectl apply -f k8s/namespace.yaml
                            kubectl apply -f k8s/deployment.yaml
                            kubectl apply -f k8s/service.yaml
                            kubectl apply -f k8s/hpa.yaml
                            
                            # Wait for deployment to be ready
                            kubectl rollout status deployment/flask-app -n flask-app --timeout=300s
                            
                            # Get service info
                            kubectl get services -n flask-app
                            kubectl get pods -n flask-app
                        '''
                    }
                }
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    sh '''
                        # Wait for pods to be ready
                        kubectl wait --for=condition=ready pod -l app=flask-app -n flask-app --timeout=300s
                        
                        # Get service endpoint
                        SERVICE_URL=$(kubectl get service flask-app-service -n flask-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
                        
                        if [ -z "$SERVICE_URL" ]; then
                            # If LoadBalancer not available, use port-forward for testing
                            kubectl port-forward service/flask-app-service 8080:80 -n flask-app &
                            sleep 10
                            SERVICE_URL="localhost:8080"
                        fi
                        
                        # Health check
                        for i in {1..10}; do
                            if curl -f http://${SERVICE_URL}/health; then
                                echo "Health check passed!"
                                break
                            else
                                echo "Health check failed, retrying in 30 seconds..."
                                sleep 30
                            fi
                            
                            if [ $i -eq 10 ]; then
                                echo "Health check failed after 10 attempts"
                                exit 1
                            fi
                        done
                    '''
                }
            }
        }
        
        stage('Integration Tests') {
            steps {
                script {
                    sh '''
                        # Run integration tests against the deployed service
                        source venv/bin/activate
                        
                        # Get service URL
                        SERVICE_URL=$(kubectl get service flask-app-service -n flask-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
                        
                        if [ -z "$SERVICE_URL" ]; then
                            kubectl port-forward service/flask-app-service 8080:80 -n flask-app &
                            sleep 10
                            SERVICE_URL="localhost:8080"
                        fi
                        
                        # Basic API tests
                        python3 -c "
import requests
import sys

base_url = 'http://${SERVICE_URL}'
try:
    # Test home endpoint
    response = requests.get(f'{base_url}/')
    assert response.status_code == 200
    print('Home endpoint test passed')
    
    # Test health endpoint
    response = requests.get(f'{base_url}/health')
    assert response.status_code == 200
    print('Health endpoint test passed')
    
    # Test tasks endpoint
    response = requests.get(f'{base_url}/tasks')
    assert response.status_code == 200
    print('Tasks endpoint test passed')
    
    print('All integration tests passed!')
    
except Exception as e:
    print(f'Integration test failed: {e}')
    sys.exit(1)
"
                    '''
                }
            }
        }
    }
    
    post {
        always {
            script {
                // Clean up
                sh '''
                    # Clean up Docker images to save space
                    docker image prune -f
                    
                    # Deactivate virtual environment
                    deactivate || true
                '''
            }
            
            // Archive artifacts
            archiveArtifacts artifacts: '**/*.json,**/*.xml,**/*.html', allowEmptyArchive: true
            
            // Clean workspace
            cleanWs()
        }
        
        success {
            script {
                echo "Pipeline completed successfully!"
                // Send success notification (Slack, email, etc.)
            }
        }
        
        failure {
            script {
                echo "Pipeline failed!"
                // Send failure notification
                
                // Rollback if needed
                sh '''
                    echo "Rolling back deployment..."
                    kubectl rollout undo deployment/flask-app -n flask-app || true
                '''
            }
        }
    }
}
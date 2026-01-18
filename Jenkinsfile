pipeline {
    agent any

    environment {
        LOCAL_REPO_PATH = "/var/jenkins_home/warlord/freqtrader"
        IMAGE_NAME      = "my-freqtrade-bot"
        IMAGE_TAG       = "latest"
        ALLOW_LOCAL_CHECKOUT = True
    }

    stages {
        stage('Fix Git Ownership') {
            steps {
                sh "git config --global --add safe.directory ${env.LOCAL_REPO_PATH}"
            }
        }

        stage('Checkout') {
            steps {
                checkout([$class: 'GitSCM', 
                    branches: [[name: '*/develop']], 
                    userRemoteConfigs: [[url: "file://${env.LOCAL_REPO_PATH}"]]
                ])
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    // This builds the image using the Dockerfile in your repo
                    sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                }
            }
        }

        stage('Verify Image') {
            steps {
                // Check if freqtrade is correctly installed in the new image
                sh "docker run --rm ${IMAGE_NAME}:${IMAGE_TAG} freqtrade --version"
            }
        }
    }
    
    post {
        success {
            echo "New Freqtrade image built successfully!"
        }
        failure {
            echo "Build failed. Check the Dockerfile or network logs."
        }
    }
}
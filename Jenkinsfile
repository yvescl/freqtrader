pipeline {
    agent any

    environment {
        LOCAL_REPO_PATH = "/var/jenkins_home/warlord/freqtrader"
        IMAGE_NAME      = "my-freqtrade-bot"
        IMAGE_TAG       = "latest"
        ALLOW_LOCAL_CHECKOUT = "True"
        REGISTRY = "registry.martin.whtn.adminthis.be"
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
            // Correct usage: skip the 'freqtrade' word
            sh "docker run --rm ${IMAGE_NAME}:${TAG} show-config"
             }
        }
        stage('Push to Local Registry') {
            steps {
                // Pushing the tagged image
                sh "docker push ${REGISTRY}/${IMAGE_NAME}:${TAG}"
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
pipeline {
    agent any

    environment {
        LOCAL_REPO_PATH = "/var/jenkins_home/warlord/freqtrader"
        IMAGE_NAME      = "my-freqtrade-bot"
        TAG       = "latest"
        ALLOW_LOCAL_CHECKOUT = "True"
        REGISTRY = "registry.martin.whtn.adminthis.be"
        GIT_CONFIG_PARAMETERS = "'safe.directory=*'"
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

        stage('Build & Tag Image') {
            steps {
                // Use env. prefix for variables defined in the environment block
                sh "docker build -t ${env.IMAGE_NAME}:${env.TAG} ."
                sh "docker tag ${env.IMAGE_NAME}:${env.TAG} ${env.REGISTRY}/${env.IMAGE_NAME}:${env.TAG}"
            }
        }

        stage('Verify Image') {
            steps {
                // Fixed the 'freqtrade' command issue AND the variable issue
                sh "docker run --rm ${env.IMAGE_NAME}:${env.TAG} --version"
            }
        }

        stage('Push to Local Registry') {
            steps {
                sh "docker push ${env.REGISTRY}/${env.IMAGE_NAME}:${env.TAG}"
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
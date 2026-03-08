pipeline {
    agent any

    environment {
        LOCAL_REPO_PATH = "/var/jenkins_home/warlord/freqtrader"
        IMAGE_NAME      = "freqtrader-bot"
        TAG       = "1.0.$BUILD_NUMBER" 
        ALLOW_LOCAL_CHECKOUT = "True"
        REGISTRY = "registry.martin.whtn.adminthis.be"
        //GIT_CONFIG_PARAMETERS = "'safe.directory=*'"
    }

    stages {
    //    stage('Fix Git Ownership') {
    //       steps {
    //           sh "git config --global --add safe.directory ${env.LOCAL_REPO_PATH}"
    //        }
    //    }

        stage('Checkout') {
            steps {
                checkout([$class: 'GitSCM', 
                    branches: [[name: '*/develop']], 
                    userRemoteConfigs: [[url: "https://github.com/yvescl/freqtrader.git"]]
                ])
            }
        }


        stage('Build & Tag Image') {
            steps {
                // Use env. prefix for variables defined in the environment block
                sh "docker buildx build -t ${env.IMAGE_NAME}:${env.TAG} ."
                sh "docker tag ${env.IMAGE_NAME}:${env.TAG} ${env.REGISTRY}/${env.IMAGE_NAME}:${env.TAG}"
                sh "docker buildx build -t ${env.IMAGE_NAME}:latest ."
                sh "docker tag ${env.IMAGE_NAME}:latest ${env.REGISTRY}/${env.IMAGE_NAME}:latest"
            }
        }

        stage('Verify Image') {
            steps {
                // Fixed the 'freqtrade' command issue AND the variable issue
                sh "docker run --rm ${env.IMAGE_NAME}:${env.TAG} --version"
                sh "docker run --rm ${env.IMAGE_NAME}:latest --version"
            }
        }

        stage('Push to Local Registry') {
            steps {
                sh "docker push ${env.REGISTRY}/${env.IMAGE_NAME}:${env.TAG}"
                sh "docker push ${env.REGISTRY}/${env.IMAGE_NAME}:latest"
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
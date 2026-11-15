pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build worker image') {
            steps {
                sh 'docker build -t my-speedtest-worker-image ./app'
            }
        }

        stage('Deploy stack') {
            steps {
                withCredentials([file(credentialsId: 'telemetry-env', variable: 'ENV_FILE')]) {
                    sh 'cp "$ENV_FILE" .env'
                    sh 'docker compose up -d --remove-orphans'
                }
            }
        }
    }

    post {
        always {
            sh 'rm -f .env'
        }
        success {
            echo 'Deployment completed successfully.'
        }
        failure {
            echo 'Pipeline failed during deployment.'
        }
    }
}
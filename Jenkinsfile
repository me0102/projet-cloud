pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Build Docker Image') {
            steps {
                sh 'docker build -t flask-app .'
            }
        }
        stage('Deploy') {
            steps {
                sh 'docker stop flask-app || true'
                sh 'docker rm flask-app || true'
                sh 'docker run -d --name flask-app --restart=always -p 5000:5000 -v /home/vagrant/app/data:/app/data flask-app'
            }
        }
        stage('Verify') {
            steps {
                sh 'sleep 5'
                sh 'curl -f http://192.168.209.128:5000/health'
            }
        }
    }
    post {
        success { echo 'Deploiement reussi !' }
        failure { echo 'Echec du pipeline !' }
    }
}

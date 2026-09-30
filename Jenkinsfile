pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Verify Docker') {
            steps {
                sh 'docker version'
            }
        }

        
        stage('Run Tests') {
            steps {
                sh '''
                    docker build \
                    -t ta-rag-ci \
                    -f jenkins/Dockerfile.ci \
                    .

                    docker run --rm \
                    -v "$WORKSPACE:/workspace" \
                    -w /workspace \
                    ta-rag-ci \
                    pytest -q
                '''
            }
        }
    }
}
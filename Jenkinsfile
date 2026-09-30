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
                    docker build -t ta-rag-backend -f backend/Dockerfile .

                    docker run --rm \
                    --entrypoint /bin/bash \
                    -v "$WORKSPACE:/workspace" \
                    -w /workspace \
                    ta-rag-backend \
                    -c "
                        pip install --no-cache-dir pytest &&
                        pytest -q
                    "
                '''
            }
        }
    }
}
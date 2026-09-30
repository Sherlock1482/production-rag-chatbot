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
                    docker run --rm \
                      -v "$WORKSPACE:/workspace" \
                      -w /workspace \
                      python:3.13-slim \
                      bash -c "
                        python --version &&
                        python -m pip install --upgrade pip &&
                        python -m pip install -r requirements.txt &&
                        python -m pip install pytest &&
                        python -m pytest -q
                      "
                '''
            }
        }
    }
}
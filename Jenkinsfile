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
                sh 'docker network inspect jenkins >/dev/null 2>&1 || docker network create jenkins'
            }
        }

        stage('Build CI Image') {
            steps {
                echo "Building CI test runner image..."
                sh 'docker build -t ta-rag-ci -f jenkins/Dockerfile.ci .'
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    echo "Starting CI Qdrant..."

                    docker rm -f ci-qdrant 2>/dev/null || true

                    docker run -d \
                      --name ci-qdrant \
                      --network jenkins \
                      qdrant/qdrant

                    echo "Waiting for Qdrant..."

                    until docker run --rm \
                        --network jenkins \
                        curlimages/curl:8.11.1 \
                        -fsS --max-time 5 \
                        http://ci-qdrant:6333/readyz; do
                        sleep 2
                    done

                    echo "Qdrant is ready"

                    echo "Seeding Qdrant with test candidate data..."

                    docker run --rm \
                      --network jenkins \
                      -e QDRANT_URL=http://ci-qdrant:6333 \
                      -e PYTHONPATH=/workspace/backend:/workspace \
                      -v "$WORKSPACE:/workspace" \
                      -w /workspace \
                      ta-rag-ci \
                      python -m backend.utils.indexer

                    echo "Running pytest..."

                    docker run --rm \
                      --network jenkins \
                      -e QDRANT_URL=http://ci-qdrant:6333 \
                      -e PYTHONPATH=/workspace/backend:/workspace \
                      -v "$WORKSPACE:/workspace" \
                      -w /workspace \
                      ta-rag-ci \
                      pytest -q
                '''
            }
        }
    }

    post {
        always {
            sh '''
                echo "Cleaning up CI Qdrant..."
                docker rm -f ci-qdrant 2>/dev/null || true
            '''
        }
    }
}
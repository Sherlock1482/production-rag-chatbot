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
                    -v "$WORKSPACE:/workspace" \
                    -w /workspace \
                    ta-rag-ci \
                    python -m backend.utils.indexer

                    echo "Running pytest..."

                    docker run --rm \
                      --network jenkins \
                      -e QDRANT_URL=http://ci-qdrant:6333 \
                      -v "$WORKSPACE:/workspace" \
                      -w /workspace \
                      ta-rag-ci \
                      pytest -q

                    echo "Cleaning up CI Qdrant..."

                    docker rm -f ci-qdrant 2>/dev/null || true
                '''
            }
        }
    }
}
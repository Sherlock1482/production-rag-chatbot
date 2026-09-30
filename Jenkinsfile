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

                    QDRANT_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' ci-qdrant)

                    echo "Qdrant IP: $QDRANT_IP"

                    until curl -fsS "http://$QDRANT_IP:6333/readyz"; do
                        sleep 2
                    done

                    echo "Qdrant is ready"

                    echo "Seeding Qdrant with test candidate data..."

                    docker run --rm \
                      --network jenkins \
                      -e QDRANT_URL=http://ci-qdrant:6333 \
                      -v "$WORKSPACE:/workspace" \
                      -w /workspace/backend \
                      ta-rag-ci \
                      python utils/indexer.py

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
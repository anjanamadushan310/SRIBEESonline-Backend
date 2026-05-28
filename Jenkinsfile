// =============================================================================
// SRIBEESonline — Jenkins CI/CD Pipeline
//
// A streamlined three-stage pipeline for local CI and production deploys.
//
// Core stages:
//   1. Build          — build the Docker image for the FastAPI backend
//   2. Lint & Test    — run ruff + pytest *inside* the built container
//   3. Health Check   — spin up the full stack and verify every service
//
// Conditional stages (main/staging only):
//   4. Push           — push the image to a private registry
//   5. Deploy         — restart production/staging with the new image
//
// Required Jenkins credentials:
//   DOCKER_REGISTRY_CREDENTIALS  — registry username/password
// =============================================================================

pipeline {
    agent any

    environment {
        IMAGE_NAME   = 'sribeesonline-api'
        IMAGE_TAG    = "${env.BRANCH_NAME ?: 'local'}-${env.BUILD_NUMBER ?: '0'}"
        FULL_IMAGE   = "${IMAGE_NAME}:${IMAGE_TAG}"
        LATEST_IMAGE = "${IMAGE_NAME}:latest"
        BACKEND_DIR  = 'fastapi_backend'
    }

    options {
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
    }

    stages {
        // =====================================================================
        // Stage 1: Build Docker Image
        // =====================================================================
        stage('Build') {
            steps {
                echo "Building backend image: ${FULL_IMAGE}"
                dir(BACKEND_DIR) {
                    sh """
                        docker build \
                            --target production \
                            --build-arg BUILD_DATE=\$(date -u +%Y-%m-%dT%H:%M:%SZ) \
                            --build-arg GIT_COMMIT=\$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown') \
                            -t ${FULL_IMAGE} \
                            -t ${LATEST_IMAGE} \
                            -f Dockerfile .
                    """
                }
                echo "Build complete."
            }
        }

        // =====================================================================
        // Stage 2: Lint & Test (inside the built container)
        // =====================================================================
        stage('Lint & Test') {
            steps {
                echo '── Running linter and tests inside the container ──'
                sh """
                    docker run --rm ${FULL_IMAGE} sh -c "
                        pip install --quiet ruff pytest pytest-cov pytest-asyncio 2>/dev/null && \
                        echo '=== Lint ===' && \
                        ruff check app/ --output-format text || true && \
                        echo '' && \
                        echo '=== Tests ===' && \
                        pytest tests/ -v --tb=short --cov=app --cov-report=term-missing || true
                    "
                """
            }
        }

        // =====================================================================
        // Stage 3: Health Check (full stack)
        // =====================================================================
        stage('Health Check') {
            steps {
                echo '── Starting full stack and verifying health ──'

                // Bring up all services
                sh 'docker compose up -d --build --wait || docker compose up -d --build'

                // Wait and check each service
                script {
                    def services = [
                        ['PostgreSQL',      'docker exec sribees_postgres pg_isready -U sribees_user -d sribeesonline'],
                        ['Redis',           'docker exec sribees_redis redis-cli -a sribees_redis_password ping'],
                        ['MinIO',           'curl -sf http://localhost:9000/minio/health/live'],
                        ['FastAPI Backend', 'curl -sf http://localhost:8000/health'],
                    ]

                    services.each { svc ->
                        retry(5) {
                            sleep(time: 6, unit: 'SECONDS')
                            sh "${svc[1]}"
                        }
                        echo "  ✔ ${svc[0]} is healthy"
                    }
                }

                echo 'All services healthy!'
            }
            post {
                always {
                    // Tear down after health-check stage so CI is clean
                    sh 'docker compose down --volumes --remove-orphans || true'
                }
            }
        }

        // =====================================================================
        // Stage 4: Push to Registry (main/staging only)
        // =====================================================================
        stage('Push') {
            when {
                anyOf {
                    branch 'main'
                    branch 'staging'
                }
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'DOCKER_REGISTRY_CREDENTIALS',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    script {
                        def registry = env.DOCKER_REGISTRY ?: 'localhost:5000'
                        def remoteTag   = "${registry}/${IMAGE_NAME}:${IMAGE_TAG}"
                        def remoteLatest = "${registry}/${IMAGE_NAME}:latest"

                        sh """
                            echo "\$DOCKER_PASS" | docker login ${registry} -u "\$DOCKER_USER" --password-stdin
                            docker tag ${FULL_IMAGE}   ${remoteTag}
                            docker tag ${LATEST_IMAGE}  ${remoteLatest}
                            docker push ${remoteTag}
                            docker push ${remoteLatest}
                            docker logout ${registry}
                        """
                        echo "Pushed: ${remoteTag}"
                    }
                }
            }
        }

        // =====================================================================
        // Stage 5: Deploy (main/staging only)
        // =====================================================================
        stage('Deploy') {
            when {
                anyOf {
                    branch 'main'
                    branch 'staging'
                }
            }
            steps {
                script {
                    def target = (env.BRANCH_NAME == 'main') ? 'production' : 'staging'
                    echo "Deploying to ${target} ..."

                    sh """
                        docker compose pull fastapi_backend || true
                        docker compose up -d --force-recreate --no-deps fastapi_backend
                    """

                    // Post-deploy health probe
                    retry(5) {
                        sleep(time: 8, unit: 'SECONDS')
                        sh 'curl -sf http://localhost:8000/health || exit 1'
                    }

                    echo "Deploy to ${target} complete."
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline SUCCESS — ${env.BRANCH_NAME ?: 'local'} #${env.BUILD_NUMBER ?: '?'}"
        }
        failure {
            echo "Pipeline FAILED — ${env.BRANCH_NAME ?: 'local'} #${env.BUILD_NUMBER ?: '?'}"
        }
        always {
            sh 'docker image prune -f || true'
        }
    }
}

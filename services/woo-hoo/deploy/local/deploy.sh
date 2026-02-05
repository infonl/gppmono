#!/usr/bin/env bash
# Deploy woo-hoo to local minikube cluster
#
# Prerequisites:
#   - minikube installed and running
#   - helm installed
#   - kubectl configured for minikube
#   - secrets.env file with your API keys
#
# Usage:
#   ./deploy/local/deploy.sh           # Full deploy (build + deploy)
#   ./deploy/local/deploy.sh --no-build  # Deploy without rebuilding image
#   ./deploy/local/deploy.sh --delete    # Delete deployment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RELEASE_NAME="woo-hoo"
NAMESPACE="default"
SECRETS_FILE="$SCRIPT_DIR/secrets.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v minikube &> /dev/null; then
        log_error "minikube not found. Install from: https://minikube.sigs.k8s.io/"
        exit 1
    fi

    if ! command -v helm &> /dev/null; then
        log_error "helm not found. Install from: https://helm.sh/"
        exit 1
    fi

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Install from: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi

    # Check minikube is running
    if ! minikube status &> /dev/null; then
        log_warn "minikube not running. Starting..."
        minikube start
    fi

    log_info "Prerequisites OK"
}

# Load secrets from env file
load_secrets() {
    if [[ ! -f "$SECRETS_FILE" ]]; then
        log_error "Secrets file not found: $SECRETS_FILE"
        log_info "Create it from the example:"
        log_info "  cp $SCRIPT_DIR/secrets.env.example $SECRETS_FILE"
        log_info "  # Edit secrets.env with your API keys"
        exit 1
    fi

    # Source the secrets file
    set -a
    source "$SECRETS_FILE"
    set +a

    if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
        log_error "OPENROUTER_API_KEY not set in $SECRETS_FILE"
        exit 1
    fi

    log_info "Secrets loaded from $SECRETS_FILE"
}

# Build Docker image in minikube's Docker daemon
build_image() {
    log_info "Building Docker image in minikube..."

    # Use minikube's Docker daemon
    eval $(minikube docker-env)

    docker build -t woo-hoo:latest \
        --build-arg COMMIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "local") \
        --build-arg RELEASE=local \
        "$PROJECT_ROOT"

    log_info "Docker image built: woo-hoo:latest"
}

# Create Kubernetes secret from env vars
create_secrets() {
    log_info "Creating Kubernetes secrets..."

    # Delete existing secret if it exists
    kubectl delete secret woo-hoo-secrets --ignore-not-found -n "$NAMESPACE"

    # Create secret from env vars
    kubectl create secret generic woo-hoo-secrets \
        --from-literal=OPENROUTER_API_KEY="${OPENROUTER_API_KEY}" \
        --from-literal=GPP_API_TOKEN="${GPP_API_TOKEN:-}" \
        -n "$NAMESPACE"

    log_info "Secret created: woo-hoo-secrets"
}

# Deploy with Helm
deploy_helm() {
    log_info "Deploying with Helm..."

    cd "$PROJECT_ROOT"

    # Install or upgrade
    helm upgrade --install "$RELEASE_NAME" ./charts/woo-hoo \
        -f "$SCRIPT_DIR/values-local.yaml" \
        -n "$NAMESPACE" \
        --wait \
        --timeout 2m

    log_info "Helm release deployed: $RELEASE_NAME"
}

# Setup ingress access
setup_ingress() {
    log_info "Setting up ingress..."

    # Enable ingress addon if not already
    minikube addons enable ingress 2>/dev/null || true

    # Get minikube IP
    MINIKUBE_IP=$(minikube ip)

    log_info ""
    log_info "Add this to your /etc/hosts file:"
    log_info "  $MINIKUBE_IP woo-hoo.local"
    log_info ""
    log_info "Then access: http://woo-hoo.local"
    log_info "Or use: minikube service $RELEASE_NAME --url"
}

# Delete deployment
delete_deployment() {
    log_info "Deleting deployment..."

    helm uninstall "$RELEASE_NAME" -n "$NAMESPACE" 2>/dev/null || true
    kubectl delete secret woo-hoo-secrets -n "$NAMESPACE" 2>/dev/null || true

    log_info "Deployment deleted"
}

# Show status
show_status() {
    log_info "Deployment status:"
    kubectl get pods -l app.kubernetes.io/name=woo-hoo -n "$NAMESPACE"
    echo ""
    kubectl get svc -l app.kubernetes.io/name=woo-hoo -n "$NAMESPACE"
    echo ""
    kubectl get ingress -l app.kubernetes.io/name=woo-hoo -n "$NAMESPACE" 2>/dev/null || true
}

# Main
main() {
    local no_build=false
    local delete=false

    # Parse args
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-build)
                no_build=true
                shift
                ;;
            --delete)
                delete=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    check_prerequisites

    if [[ "$delete" == true ]]; then
        delete_deployment
        exit 0
    fi

    load_secrets

    if [[ "$no_build" == false ]]; then
        build_image
    fi

    create_secrets
    deploy_helm
    setup_ingress

    echo ""
    show_status

    log_info ""
    log_info "Deployment complete!"
    log_info "Run 'kubectl logs -f deployment/$RELEASE_NAME' to see logs"
}

main "$@"

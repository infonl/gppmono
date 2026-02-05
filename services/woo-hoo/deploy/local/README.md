# Local Kubernetes Deployment

Deploy woo-hoo to a local minikube cluster for testing.

## Prerequisites

- [minikube](https://minikube.sigs.k8s.io/docs/start/)
- [helm](https://helm.sh/docs/intro/install/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)

## Quick Start

1. **Create secrets file:**
   ```bash
   cp deploy/local/secrets.env.example deploy/local/secrets.env
   # Edit secrets.env with your API keys
   ```

2. **Start minikube:**
   ```bash
   minikube start
   ```

3. **Deploy:**
   ```bash
   make deploy-local
   # Or directly:
   ./deploy/local/deploy.sh
   ```

4. **Add hosts entry:**
   ```bash
   echo "$(minikube ip) woo-hoo.local" | sudo tee -a /etc/hosts
   ```

5. **Access:**
   - http://woo-hoo.local
   - http://woo-hoo.local/docs (Swagger UI)

## Commands

```bash
# Full deploy (build + deploy)
make deploy-local

# Deploy without rebuilding image
./deploy/local/deploy.sh --no-build

# Delete deployment
make deploy-local-delete

# View logs
kubectl logs -f deployment/woo-hoo

# Port forward (alternative to ingress)
kubectl port-forward svc/woo-hoo 8000:80
```

## Configuration

Edit `values-local.yaml` to customize:
- Resource limits
- Log levels
- GPP integration URLs

Secrets are managed separately in `secrets.env` (git-ignored).

## Files

- `secrets.env.example` - Template for secrets (copy to `secrets.env`)
- `secrets.env` - Your secrets (git-ignored)
- `values-local.yaml` - Helm values for local deployment
- `deploy.sh` - Deployment script

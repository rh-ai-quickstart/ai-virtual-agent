# Voice Integration Deployment Guide

This guide covers deploying the AI Virtual Agent with voice-to-text capabilities using the provided `make` commands for both local development and OpenShift cluster deployments.

## Prerequisites

### System Requirements
- **Local Development**: Docker/Podman, Make, Git
- **OpenShift Cluster**: oc CLI, Helm 3, Make, OpenShift cluster access

### Voice Integration Requirements
- **CPU**: 1000m+ (voice processing is CPU intensive)
- **Memory**: 4Gi+ (Whisper model loading requires significant memory)
- **Storage**: 10Gi+ for model cache (optional but recommended)

## 🏠 Local Development Deployment

### Quick Start
```bash
# Clone and navigate to the repository
cd /path/to/ai-virtual-agent/deploy/local

# Start all services with voice integration
make compose-up

# Check service status
make compose-status

# View logs
make compose-logs

# Stop services
make compose-down
```

### Configuration Options

Set environment variables before running `make compose-up`:

```bash
# Voice model configuration (default: base)
export WHISPER_MODEL=small     # Options: tiny, base, small, medium, large, turbo

# Attachment features (required for audio file uploads)
export ENABLE_ATTACHMENTS=true  # Default: true

# Development mode (disables authentication)
export LOCAL_DEV_ENV_MODE=true  # Default: true

# Start with custom configuration
make compose-up
```

### Model Size Guide

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| tiny | 39M | Fastest | Basic | Quick testing |
| base | 74M | Fast | Good | **Recommended for development** |
| small | 244M | Medium | Better | Production with limited resources |
| medium | 769M | Slow | High | Production with more resources |
| large | 1550M | Slowest | Highest | Maximum accuracy needed |
| turbo | 809M | Fast | High | **Recommended for production** |

### Troubleshooting Local Deployment

```bash
# Check container health
make compose-status

# View detailed logs
make compose-logs

# Restart specific service
podman compose -f compose.yaml restart backend

# Clean restart with fresh build
make compose-down
make compose-build
```

### Development Commands

```bash
# Run linters
make lint

# Run tests
make test

# Build images
make compose-build

# Restart with new code changes
make compose-restart
```

## ☸️ OpenShift Cluster Deployment

### Quick Start
```bash
# Navigate to cluster deployment directory
cd /path/to/ai-virtual-agent/deploy/cluster

# Install with default voice configuration
make install NAMESPACE=my-ai-assistant

# Check deployment status
make install-status NAMESPACE=my-ai-assistant

# Uninstall
make uninstall NAMESPACE=my-ai-assistant
```

### Configuration Options

#### Basic Voice Configuration
```bash
# Install with specific Whisper model
WHISPER_MODEL=turbo make install NAMESPACE=my-ai-assistant

# Install with disabled model cache (for resource-constrained environments)
VOICE_CACHE_ENABLED=false make install NAMESPACE=my-ai-assistant
```

#### Advanced Configuration

Create a custom values file:
```yaml
# voice-config.yaml
voice:
  whisperModel: turbo          # Model size
  enableModelCache: true       # Enable persistent cache
  modelCacheSize: 20Gi        # Cache storage size
  storageClass: "gp2"         # Storage class

resources:
  limits:
    cpu: 3000m                 # CPU limit
    memory: 12Gi               # Memory limit
  requests:
    cpu: 1500m                 # CPU request
    memory: 6Gi                # Memory request
```

Deploy with custom configuration:
```bash
helm install ai-virtual-agent helm/ -n my-ai-assistant \
  -f voice-config.yaml \
  --set seed.admin_user.username=admin \
  --set seed.admin_user.email=admin@company.com
```

### Resource Planning

#### Minimum Requirements (Development)
```yaml
resources:
  requests:
    cpu: 500m
    memory: 2Gi
  limits:
    cpu: 1000m
    memory: 4Gi
```

#### Recommended Production
```yaml
resources:
  requests:
    cpu: 1500m
    memory: 6Gi
  limits:
    cpu: 3000m
    memory: 12Gi
```

#### High-Performance Production
```yaml
resources:
  requests:
    cpu: 2000m
    memory: 8Gi
  limits:
    cpu: 4000m
    memory: 16Gi
```

### Storage Configuration

#### Default (Cluster Default Storage Class)
```yaml
voice:
  enableModelCache: true
  modelCacheSize: 10Gi
```

#### Custom Storage Class
```yaml
voice:
  enableModelCache: true
  modelCacheSize: 20Gi
  storageClass: "fast-ssd"
```

#### Disable Persistent Cache (for testing)
```yaml
voice:
  enableModelCache: false
```

### Deployment Commands

```bash
# Show deployment help
make install-help

# Update Helm dependencies
make deps

# List available models
make list-models

# Create namespace and install
make install NAMESPACE=my-ai-assistant

# Check status
make install-status NAMESPACE=my-ai-assistant

# Get application URL
oc get routes ai-virtual-agent-authenticated -n my-ai-assistant

# Uninstall and cleanup
make uninstall NAMESPACE=my-ai-assistant
```

### Environment Variables for Cluster Deployment

Set these before running `make install`:

```bash
# Required
export NAMESPACE=my-ai-assistant

# Optional voice configuration
export WHISPER_MODEL=turbo
export VOICE_CACHE_SIZE=20Gi

# Optional admin user configuration
export ADMIN_USERNAME=admin@company.com
export ADMIN_EMAIL=admin@company.com

# Optional model configuration
export LLM=llama-3-2-1b-instruct
export HF_TOKEN=your_huggingface_token

# Install with configuration
make install
```

## 🔊 Voice Feature Testing

### Local Testing
1. Start the development environment:
   ```bash
   make compose-up
   ```

2. Access the application at `http://localhost:5173`

3. Test voice input:
   - Click the microphone button in the chat interface
   - Grant microphone permissions
   - Speak clearly for 2-5 seconds
   - Verify transcription appears in the input field

### Cluster Testing
1. Deploy to OpenShift:
   ```bash
   make install NAMESPACE=test-voice
   ```

2. Get the application URL:
   ```bash
   make install-status NAMESPACE=test-voice
   ```

3. Access via HTTPS (required for microphone access) and test voice features

### Audio File Upload Testing
1. Prepare test audio files (MP3, WAV, M4A)
2. Use the attachment feature to upload audio files
3. Verify automatic transcription in chat

## 🚀 Production Deployment Best Practices

### 1. Resource Allocation
- **CPU**: Start with 1500m request, 3000m limit
- **Memory**: Start with 6Gi request, 12Gi limit
- **Storage**: 20Gi+ for model cache

### 2. Model Selection
- **Development**: `base` model (good balance)
- **Production**: `turbo` model (optimized performance)
- **High-accuracy**: `large` model (best quality)

### 3. Scaling Considerations
- Whisper models are CPU-intensive
- Model loading happens on first request (can take 30-60 seconds)
- Consider horizontal pod autoscaling for high traffic
- Use persistent volume for model cache to avoid re-downloading

### 4. Monitoring
```bash
# Check pod resource usage
oc top pods -n my-ai-assistant

# View application logs
oc logs deployment/ai-virtual-agent -n my-ai-assistant -f

# Monitor speech processing endpoints
oc logs deployment/ai-virtual-agent -n my-ai-assistant | grep "speech"
```

### 5. Troubleshooting
```bash
# Check voice service health
curl https://your-app-url/api/v1/speech/health

# Check available models
curl https://your-app-url/api/v1/speech/models

# Check pod events
oc describe pod $(oc get pods -l app.kubernetes.io/name=ai-virtual-agent -o name | head -1) -n my-ai-assistant
```

## 📝 Configuration Summary

### Local Development (`deploy/local/`)
- **Command**: `make compose-up`
- **Configuration**: Environment variables
- **Voice Model**: Set via `WHISPER_MODEL` env var
- **Storage**: Docker volumes (persistent across restarts)

### OpenShift Cluster (`deploy/cluster/`)
- **Command**: `make install NAMESPACE=<name>`
- **Configuration**: Helm values + environment variables
- **Voice Model**: Set via Helm values or env vars
- **Storage**: PersistentVolumeClaim (configurable size and storage class)

Both deployment methods support the full voice integration feature set with automatic model downloading, persistent caching, and production-ready configurations.

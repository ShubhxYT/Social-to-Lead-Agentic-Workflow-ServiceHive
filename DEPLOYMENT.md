# Deployment Guide: ServiceHive on Coolify

This guide explains how to deploy the AutoStream AI Assistant on Coolify.

## Prerequisites
- Coolify instance running and accessible
- Docker support enabled on your Coolify instance
- Groq API key (get one from [console.groq.com](https://console.groq.com))

## Quick Start with Docker

### Local Testing (Before Coolify)
```bash
# 1. Build the image
docker build -t servicehive:latest .

# 2. Run with docker-compose (includes volume persistence)
docker-compose up -d

# 3. Access at http://localhost:8501
```

### Deploy to Coolify

1. **Push Repository to Git**
   ```bash
   git add .
   git commit -m "Add Docker configuration for Coolify deployment"
   git push origin main
   ```

2. **In Coolify Dashboard:**
   - Click "Create New Service" → "Docker Compose"
   - Connect your Git repository
   - Select this repository and branch (main/production)
   - Coolify will auto-detect the `docker-compose.yml` file

3. **Configure Environment Variables:**
   - In Coolify service settings, add environment variables:
     - `GROQ_API_KEY`: Your Groq API key
     - Any other custom variables your app needs

4. **Set Ports:**
   - Ensure port 8501 is exposed and publicly accessible
   - Configure domain/subdomain if needed

5. **Deploy:**
   - Click "Deploy" to build and start the container
   - Monitor logs in Coolify dashboard

## Persistent Storage

The `chroma_db` directory is mounted as a Docker volume to persist the vector database across container restarts.

**Volume in Coolify:**
- Coolify automatically creates and manages volumes
- Data persists even if the container is restarted
- Backups are recommended for production use

## Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GROQ_API_KEY` | Yes | Groq API authentication key | `gsk_...` |
| `STREAMLIT_SERVER_PORT` | No | Port for Streamlit (default: 8501) | `8501` |
| `STREAMLIT_SERVER_HEADLESS` | No | Run in headless mode (default: true) | `true` |

## Troubleshooting

### Knowledge Base Not Found
- The container automatically initializes the knowledge base on first run
- This may take a few minutes depending on your documents
- Check logs: `docker logs servicehive-app`

### Port Already in Use
- If port 8501 is already in use locally, map to a different port:
  ```yaml
  ports:
    - "9000:8501"  # Access at http://localhost:9000
  ```

### Memory Issues
- Increase Docker memory limits in Coolify if containers are crashing
- Set resource limits in `docker-compose.yml` if needed:
  ```yaml
  services:
    servicehive:
      deploy:
        resources:
          limits:
            memory: 2G
          reservations:
            memory: 1G
  ```

### API Key Not Working
- Verify `GROQ_API_KEY` is correctly set in Coolify environment
- Ensure the key hasn't expired on Groq's console
- Check container logs for authentication errors

## Monitoring

1. **View Logs:**
   ```bash
   docker logs -f servicehive-app
   ```

2. **Health Check:**
   - Container includes a health check that verifies Streamlit is running
   - Coolify shows health status in the dashboard

3. **Resource Usage:**
   - Monitor CPU and memory in Coolify dashboard
   - Adjust resource limits if needed

## Scaling & Performance

- **Single Instance:** This setup runs one container; Coolify handles automatic restarts if it crashes
- **Multiple Instances:** Coolify can manage load balancing; each instance will maintain its own `chroma_db`
  - For shared databases, consider using external Chroma server (advanced)

## Updates

To deploy a new version:
1. Push your changes to Git
2. In Coolify, click "Redeploy" or enable auto-deploy
3. Coolify rebuilds the image and restarts the container

## Support

For Coolify-specific issues, refer to:
- [Coolify Documentation](https://coolify.io/docs)
- [Streamlit Deployment Guide](https://docs.streamlit.io/deploy)

For project-specific issues:
- Check logs: `docker logs servicehive-app`
- Review `main.py` and `agent/graph.py` for configuration options

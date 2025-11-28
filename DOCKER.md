````{"variant":"document","title":"DOCKER.md","id":"c9301"}
# Docker Setup Guide

This guide explains how to use Docker to run the project in both local and production environments.  

---

## Local Environment

### 1. Start Docker with Local Database

Use the following script to build and launch the Docker Compose setup with a local database:

```bash
./docker-start.local.sh
```

This script will:

- Build the Docker images.
- Start the services defined in `docker-compose.yml` for local development.
- Initialize a local database container.

---

### 2. Destroy Local Docker Setup

To stop and remove all containers, networks, and volumes created by the local Docker Compose setup, run:

```bash
./docker-destroy.sh
```

This ensures that your environment is clean before restarting or changing configurations.

---

## Production Environment

For production or remote database usage, the `docker-compose.yml` file is configured to connect to a remote database.  

### 1. Set Environment Variables

Create a `.env` file in the project root with the following content:

```dotenv
REMOTE_DB_HOST=host
REMOTE_DB_PORT=3306
REMOTE_DB_ROOT_USERNAME=root
REMOTE_DB_ROOT_PASSWORD=password
FRAPPE_SITE_NAME=example.com
```

These variables will be used by the Docker Compose file to connect to the remote database and configure the site.  

### 2. Start Production Docker Compose

Run the following command to start the services:

```bash
docker-compose up -d
```

This will:

- Pull and run the production Docker containers.
- Connect to the remote database using the `.env` configuration.

---

### Notes

- Make sure Docker and Docker Compose are installed and running on your system.
- For local development, the `docker-start.local.sh` script will override `.env` variables if necessary.
- To stop production containers, use:

```bash
docker-compose down
```

This command will stop and remove containers but retain the remote database data.

---

### File Overview

| File | Purpose |
|------|---------|
| `docker-start.local.sh` | Build and start Docker Compose with a local database |
| `docker-destroy.sh` | Stop and remove all local Docker containers and volumes |
| `docker-compose.yml` | Docker Compose configuration for production and remote database |
| `.env` | Environment variables for production Docker setup |

---

Follow this guide to easily switch between local development and production environments using Docker.  
````


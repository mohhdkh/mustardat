#!/bin/bash
# Lost & Found - Docker Run Script for Linux/Mac

set -e

echo "========================================"
echo "Lost & Found - Docker Commands"
echo "========================================"
echo

case "$1" in
  build)
    echo "Building Docker image..."
    docker-compose build
    ;;
  up)
    echo "Starting production server..."
    docker-compose up -d
    echo
    echo "Server running at http://localhost:8000"
    echo "API docs at http://localhost:8000/docs"
    ;;
  dev)
    echo "Starting development server with hot reload..."
    docker-compose --profile dev up api-dev
    ;;
  down)
    echo "Stopping containers..."
    docker-compose down
    ;;
  logs)
    echo "Showing logs..."
    docker-compose logs -f
    ;;
  shell)
    echo "Opening shell in container..."
    docker exec -it lostfound_api /bin/bash
    ;;
  clean)
    echo "Cleaning up Docker resources..."
    docker-compose down -v --rmi local
    docker system prune -f
    ;;
  *)
    echo "Usage: ./docker-run.sh [command]"
    echo
    echo "Commands:"
    echo "  build   - Build Docker image"
    echo "  up      - Start production server (detached)"
    echo "  dev     - Start development server with hot reload"
    echo "  down    - Stop all containers"
    echo "  logs    - View container logs"
    echo "  shell   - Open shell in running container"
    echo "  clean   - Remove containers, volumes, and images"
    echo "  help    - Show this help message"
    echo
    echo "Examples:"
    echo "  ./docker-run.sh build"
    echo "  ./docker-run.sh up"
    echo "  ./docker-run.sh dev"
    ;;
esac

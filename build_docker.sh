#chmod +x build_docker.sh
docker-compose down
docker system prune -f
docker-compose up -d --build
echo "Docker containers rebuilt and started successfully."
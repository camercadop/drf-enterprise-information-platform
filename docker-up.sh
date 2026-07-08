#!/bin/bash
echo "🚀 Starting Enterprise Information Platform..."
docker-compose up -d
echo ""
echo "✅ Services running:"
echo "   PostgreSQL: localhost:5432"
echo "   Redis: localhost:6379"
echo "   Django: localhost:8000"
echo ""
echo "  To stop: docker-compose down"
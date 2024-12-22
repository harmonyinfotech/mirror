#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "🔍 Checking deployment status..."

# Check system services
echo -n "Checking Nginx status: "
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}Running${NC}"
else
    echo -e "${RED}Not running${NC}"
fi

echo -n "Checking Mirror service status: "
if systemctl is-active --quiet mirror; then
    echo -e "${GREEN}Running${NC}"
else
    echo -e "${RED}Not running${NC}"
fi

# Check ports
echo -n "Checking port 80 (HTTP): "
if netstat -tuln | grep -q ":80 "; then
    echo -e "${GREEN}Open${NC}"
else
    echo -e "${RED}Closed${NC}"
fi

echo -n "Checking port 443 (HTTPS): "
if netstat -tuln | grep -q ":443 "; then
    echo -e "${GREEN}Open${NC}"
else
    echo -e "${RED}Closed${NC}"
fi

# Check IP connectivity
echo -n "Checking IPv4 connectivity: "
if ping -c 1 -4 google.com >/dev/null 2>&1; then
    echo -e "${GREEN}Working${NC}"
else
    echo -e "${RED}Not working${NC}"
fi

echo -n "Checking IPv6 connectivity: "
if ping -c 1 -6 google.com >/dev/null 2>&1; then
    echo -e "${GREEN}Working${NC}"
else
    echo -e "${RED}Not working${NC}"
fi

# Check application logs
echo -e "\n📝 Last 5 lines of application logs:"
sudo journalctl -u mirror -n 5

echo -e "\n📝 Last 5 lines of Nginx error log:"
sudo tail -n 5 /var/log/nginx/error.log

echo -e "\n✨ Deployment check complete!"

#!/bin/sh
sudo systemctl start docker || sudo service docker start
docker-compose -p sd1 -f docker/docker-compose-services.yml up -d

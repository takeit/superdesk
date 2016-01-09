#!/bin/sh
docker-compose -p sd1 -f docker/docker-compose-services.yml $@

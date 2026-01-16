#!/bin/bash
###############################################################################
# NSO Curl Wrapper Script
# Simple wrapper that calls curl with proper credentials and returns output
# Supports GET and POST methods
###############################################################################

HOST="$1"
PORT="$2"
USERNAME="$3"
PASSWORD="$4"
ENDPOINT="$5"
METHOD="${6:-GET}"       # Optional 6th arg: GET (default) or POST
DATA="${7:-}"            # Optional 7th arg: POST data

URL="https://${HOST}:${PORT}${ENDPOINT}"

# Build curl command
CURL_CMD=(curl -k -s --noproxy "*" --connect-timeout 5 --max-time 10 -u "${USERNAME}:${PASSWORD}")

# Add method-specific options
if [ "$METHOD" = "POST" ]; then
    CURL_CMD+=(-X POST)
    CURL_CMD+=(-H "Content-Type: application/yang-data+json")
    if [ -n "$DATA" ]; then
        CURL_CMD+=(-d "$DATA")
    fi
fi

# Add URL and execute
CURL_CMD+=("${URL}")
"${CURL_CMD[@]}"

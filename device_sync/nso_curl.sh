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
USE_HTTPS="${8:-true}"   # Optional 8th arg: true (default) or false for HTTP

# Determine protocol
if [ "$USE_HTTPS" = "false" ]; then
    PROTOCOL="http"
    SSL_OPTS=()
else
    PROTOCOL="https"
    SSL_OPTS=(-k --tlsv1.2)
fi

URL="${PROTOCOL}://${HOST}:${PORT}${ENDPOINT}"

# Build curl command
# -4: Force IPv4 (avoid IPv6 issues)
if [ "$USE_HTTPS" = "false" ]; then
    # HTTP mode - no SSL options
    CURL_CMD=(curl -s -4 --noproxy "*" --connect-timeout 5 --max-time 10 -u "${USERNAME}:${PASSWORD}")
else
    # HTTPS mode - add SSL options
    CURL_CMD=(curl -s -4 --noproxy "*" --connect-timeout 5 --max-time 10 -k --tlsv1.2 -u "${USERNAME}:${PASSWORD}")
fi

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

#!/usr/bin/env bash
# Setup Python environment.

set -e

SCRIPT_DIR="$(cd "$(dirname "$([ `readlink "$0"` ] && echo "`readlink "$0"`" || echo "$0")")"; pwd -P)"
cd "$SCRIPT_DIR/.."

LOG_FILE="${1:-./logs/python.log}"
if [ "$LOG_FILE" != "/dev/stdout" -a "$LOG_FILE" != "/dev/stderr" ]
then
  rm -f "$LOG_FILE"
fi

echo "> Installing Python and CLI utilities" | tee -a "$LOG_FILE"
apt-get update >>"$LOG_FILE" 2>&1
apt-get install -y make gcc libdpkg-perl libpq-dev curl git ssh vim python3-dev >>"$LOG_FILE" 2>&1
rm -rf /var/lib/apt/lists/* >>"$LOG_FILE" 2>&1

curl -o /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py >>"$LOG_FILE" 2>&1
python3 /tmp/get-pip.py --force-reinstall >>"$LOG_FILE" 2>&1

#install Python application requirements
echo "> Installing Python project requirements" | tee -a "$LOG_FILE"
 
if [ -f requirements.txt ]
then
  cp requirements.txt "/tmp/requirements.txt" >>"$LOG_FILE" 2>&1
  pip3 install -r "/tmp/requirements.txt" >>"$LOG_FILE" 2>&1
fi
if [ -f requirements-dev.txt ]
then
  cp requirements-dev.txt "/tmp/requirements-dev.txt" >>"$LOG_FILE" 2>&1
  pip3 install -r "/tmp/requirements-dev.txt" >>"$LOG_FILE" 2>&1
fi

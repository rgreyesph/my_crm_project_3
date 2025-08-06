#!/bin/bash
# .platform/hooks/prebuild/01_install_postgres_devel.sh
# Installs postgresql16 only to avoid dependency conflicts

echo "--- Starting prebuild script: 01_install_postgres_devel.sh ---"
echo "Attempting to install postgresql16 using dnf..."

# Install postgresql16 (client tools)
sudo dnf install -y postgresql16
INSTALL_STATUS=$?
if [ $INSTALL_STATUS -eq 0 ]; then
  echo "SUCCESS: 'dnf install -y postgresql16' completed with status 0."
else
  echo "ERROR: 'dnf install -y postgresql16' failed with status $INSTALL_STATUS."
  exit 1
fi

# Verify psql command
echo "Verifying psql command..."
if command -v psql &> /dev/null
then
    echo "psql command FOUND."
    psql --version
else
    echo "WARNING: psql command still NOT found after dnf install attempt."
fi

echo "--- Finished prebuild script: 01_install_postgres_devel.sh ---"
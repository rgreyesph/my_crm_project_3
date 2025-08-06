#!/bin/bash

LOG_FILE="/var/log/migrate.log"
touch $LOG_FILE
chown webapp:webapp $LOG_FILE
chmod 664 $LOG_FILE

echo "==================================================" | tee -a $LOG_FILE
echo "Starting Django migrations at $(date)..." | tee -a $LOG_FILE
echo "==================================================" | tee -a $LOG_FILE

# --- Activate virtual environment (Modern AL2 method) ---
source "$PYTHONPATH/activate"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment." | tee -a $LOG_FILE
    exit 1
fi

cd /var/app/current

# The get-config commands are not needed on AL2 as the variables are already in the environment.
# We will rely on the DATABASE_URL set in the EB console.

# --- Wait for database to be ready ---
echo "Waiting for database connection at $(date)..." >> $LOG_FILE
until psql "$DATABASE_URL" -c "SELECT 1" >> $LOG_FILE 2>&1; do
    echo "Database not ready, waiting 2 seconds..." >> $LOG_FILE
    sleep 2
done
echo "Database connection successful." >> $LOG_FILE

# --- Run Migrations on Leader Instance Only (Modern AL2 method) ---
if [ "$EB_IS_LEADER" = "true" ]; then
  echo "This is the leader instance. Running Django migrations..." | tee -a $LOG_FILE
  python manage.py migrate --noinput --verbosity 2 >> $LOG_FILE 2>&1
  MIGRATE_STATUS=$?
  if [ $MIGRATE_STATUS -eq 0 ]; then
    echo "SUCCESS: Django migrations completed at $(date)." | tee -a $LOG_FILE
  else
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" | tee -a $LOG_FILE
    echo "ERROR: Django migrations failed with status $MIGRATE_STATUS at $(date)." | tee -a $LOG_FILE
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" | tee -a $LOG_FILE
    cat $LOG_FILE
    exit 1
  fi
else
  echo "This is not the leader instance. Skipping migrations." | tee -a $LOG_FILE
fi
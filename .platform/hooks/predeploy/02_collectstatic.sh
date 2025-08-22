#!/bin/bash

# Create log file if missing
sudo touch /var/log/collectstatic.log
sudo chmod 664 /var/log/collectstatic.log
sudo chown webapp:webapp /var/log/collectstatic.log

echo "=== PREDEPLOY: Collecting static files at $(date '+%c %Z') ===" | sudo tee -a /var/log/collectstatic.log

# Activate the virtual environment
source /var/app/venv/*/bin/activate
cd /var/app/current

# Set environment variables
export DATABASE_URL=$(/opt/elasticbeanstalk/bin/get-config environment -k DATABASE_URL)
export SECRET_KEY=$(/opt/elasticbeanstalk/bin/get-config environment -k SECRET_KEY)
export DEBUG="False"
export DATABASE_SSL="True"

echo "Waiting for migrations at $(date)..." | sudo tee -a /var/log/collectstatic.log
until python manage.py migrate --check >> /var/log/collectstatic.log 2>&1; do
    echo "Migrations not complete, waiting..." | sudo tee -a /var/log/collectstatic.log
    sleep 2
done

# Delete manifest to prevent hashed substitution in templates
rm -f /var/app/current/staticfiles/staticfiles.json 2>> /var/log/collectstatic.log || echo "WARN: staticfiles.json not found, skipped deletion" | sudo tee -a /var/log/collectstatic.log

# CRITICAL: Create staticfiles directory with correct permissions BEFORE collectstatic
echo "Creating staticfiles directory..." | sudo tee -a /var/log/collectstatic.log
sudo rm -rf /var/app/current/staticfiles
sudo mkdir -p /var/app/current/staticfiles
sudo chown webapp:webapp /var/app/current/staticfiles
sudo chmod 755 /var/app/current/staticfiles

# Verify directory exists
if [ -d "/var/app/current/staticfiles" ]; then
    echo "✅ staticfiles directory created successfully" | sudo tee -a /var/log/collectstatic.log
    ls -la /var/app/current/ | grep staticfiles | sudo tee -a /var/log/collectstatic.log
else
    echo "❌ ERROR: Failed to create staticfiles directory" | sudo tee -a /var/log/collectstatic.log
    exit 1
fi

# IMPORTANT: Check if django-autocomplete-light is properly installed
echo "DEBUG: Checking installed packages..." | sudo tee -a /var/log/collectstatic.log
pip show django-autocomplete-light | sudo tee -a /var/log/collectstatic.log 2>&1

# Run collectstatic with maximum verbosity for debugging
echo "Running python manage.py collectstatic --noinput --clear --verbosity 2..." | sudo tee -a /var/log/collectstatic.log
python manage.py collectstatic --noinput --clear --verbosity 2 | sudo tee -a /var/log/collectstatic.log 2>&1

COLLECT_STATUS=$?

# CRITICAL: Verify the files actually exist after collection
echo "DEBUG: Verifying critical files exist after collection..." | sudo tee -a /var/log/collectstatic.log

# Check Django admin select2 files
if [ -f "/var/app/current/staticfiles/admin/js/vendor/select2/select2.full.js" ]; then
    echo "✅ SUCCESS: select2.full.js found" | sudo tee -a /var/log/collectstatic.log
else
    echo "❌ ERROR: select2.full.js NOT found!" | sudo tee -a /var/log/collectstatic.log
fi

# Check django-autocomplete-light files
if [ -f "/var/app/current/staticfiles/autocomplete_light/autocomplete_light.min.js" ]; then
    echo "✅ SUCCESS: autocomplete_light.min.js found" | sudo tee -a /var/log/collectstatic.log
else
    echo "❌ ERROR: autocomplete_light.min.js NOT found!" | sudo tee -a /var/log/collectstatic.log
fi

if [ -f "/var/app/current/staticfiles/autocomplete_light/select2.min.js" ]; then
    echo "✅ SUCCESS: autocomplete_light select2.min.js found" | sudo tee -a /var/log/collectstatic.log
else
    echo "❌ ERROR: autocomplete_light select2.min.js NOT found!" | sudo tee -a /var/log/collectstatic.log
fi

if [ -f "/var/app/current/staticfiles/autocomplete_light/i18n/en.js" ]; then
    echo "✅ SUCCESS: autocomplete_light en.js found" | sudo tee -a /var/log/collectstatic.log
else
    echo "❌ ERROR: autocomplete_light en.js NOT found!" | sudo tee -a /var/log/collectstatic.log
fi

# Show total files collected
TOTAL_FILES=$(find /var/app/current/staticfiles/ -type f 2>/dev/null | wc -l)
echo "Total static files collected: $TOTAL_FILES" | sudo tee -a /var/log/collectstatic.log

if [ $COLLECT_STATUS -eq 0 ]; then
    echo "SUCCESS: Static files collected at $(date '+%c %Z')." | sudo tee -a /var/log/collectstatic.log
    
    # CRITICAL: Set proper permissions for web server access
    sudo find /var/app/current/staticfiles -type f -exec chmod 644 {} \;
    sudo find /var/app/current/staticfiles -type d -exec chmod 755 {} \;
    sudo chown -R webapp:webapp /var/app/current/staticfiles
    
    echo "Permissions set for staticfiles directory" | sudo tee -a /var/log/collectstatic.log
    
    # Final verification
    echo "Final directory structure:" | sudo tee -a /var/log/collectstatic.log
    ls -la /var/app/current/staticfiles/ | sudo tee -a /var/log/collectstatic.log
else
    echo "ERROR: Static file collection failed with status $COLLECT_STATUS at $(date '+%c %Z')." | sudo tee -a /var/log/collectstatic.log
    sudo cat /var/log/collectstatic.log
    exit 1
fi

echo "=== PREDEPLOY: Collectstatic completed at $(date '+%c %Z') ===" | sudo tee -a /var/log/collectstatic.log
#!/bin/bash

# Activate the virtual environment
source "$PYTHONPATH/activate"

# This block will only run on the leader instance
if [ "$EB_IS_LEADER" = "true" ]; then
  echo "Leader instance, creating superuser if it does not exist..."
  python manage.py createsuperuser --noinput
  echo "Superuser creation command finished."
else
  echo "Not leader instance, skipping superuser creation."
fi
#!/bin/bash
# Configure PostgreSQL for remote access

echo "=== Configuring PostgreSQL for remote access ==="

# Backup original files
sudo cp /etc/postgresql/14/main/postgresql.conf /etc/postgresql/14/main/postgresql.conf.backup
sudo cp /etc/postgresql/14/main/pg_hba.conf /etc/postgresql/14/main/pg_hba.conf.backup

# Configure postgresql.conf to listen on all addresses
echo "Configuring postgresql.conf..."
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/14/main/postgresql.conf

# Add client authentication rule for remote connections
echo "Configuring pg_hba.conf..."
sudo bash -c 'echo "# Allow remote connections from any IP with password" >> /etc/postgresql/14/main/pg_hba.conf'
sudo bash -c 'echo "host    all             all             0.0.0.0/0               md5" >> /etc/postgresql/14/main/pg_hba.conf'

# Restart PostgreSQL
echo "Restarting PostgreSQL..."
sudo systemctl restart postgresql

# Check status
echo "Checking PostgreSQL status..."
sudo systemctl status postgresql --no-pager

# Show current settings
echo ""
echo "=== Current listen_addresses setting ==="
sudo grep "^listen_addresses" /etc/postgresql/14/main/postgresql.conf || echo "Not set"

echo ""
echo "=== Current pg_hba.conf rules ==="
sudo grep -v "^#" /etc/postgresql/14/main/pg_hba.conf | grep -v "^$"

echo ""
echo "=== PostgreSQL is now configured for remote access ==="
echo "Don't forget to:"
echo "1. Configure firewall to allow port 5432"
echo "2. Test connection from remote machine"

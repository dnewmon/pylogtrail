-- PyLogTrail Database Initialization Script

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS pylogtrail 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Create user if it doesn't exist
CREATE USER IF NOT EXISTS 'pylogtrail'@'%' IDENTIFIED BY 'pylogtrail_password';
CREATE USER IF NOT EXISTS 'pylogtrail'@'localhost' IDENTIFIED BY 'pylogtrail_password';

-- Grant all privileges on pylogtrail database
GRANT ALL PRIVILEGES ON pylogtrail.* TO 'pylogtrail'@'%';
GRANT ALL PRIVILEGES ON pylogtrail.* TO 'pylogtrail'@'localhost';

-- Flush privileges to ensure they take effect
FLUSH PRIVILEGES;

-- Use the pylogtrail database
USE pylogtrail;

-- Create a simple test table (SQLAlchemy will handle the real schema)
-- This is just to verify the database connection works
CREATE TABLE IF NOT EXISTS connection_test (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message VARCHAR(255) DEFAULT 'Database initialized successfully'
);

-- Insert a test record
INSERT INTO connection_test (message) VALUES ('PyLogTrail database ready');

-- Show status
SELECT 'PyLogTrail database initialized successfully' AS status;
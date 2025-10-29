-- Database initialization script for NearbyTix
-- This script ensures PostGIS extension is enabled

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verify PostGIS is installed
SELECT PostGIS_Version();

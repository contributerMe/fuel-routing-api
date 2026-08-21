--sqlite3 db.sqlite3 < test.sql

.mode column
.headers on

-- 1. Check the total number of stations in the database
SELECT COUNT(*) as Total_Stations FROM api_fuelstation;

-- 2. See the 5 absolute cheapest gas stations in the country
SELECT name, city, state, retail_price 
FROM api_fuelstation 
ORDER BY retail_price ASC 
LIMIT 5;

-- 3. See 5 stations located in California
SELECT name, city, retail_price, latitude, longitude 
FROM api_fuelstation 
WHERE state = 'CA' 
LIMIT 5;

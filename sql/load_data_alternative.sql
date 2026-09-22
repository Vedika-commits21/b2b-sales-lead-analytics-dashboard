-- =====================================================================
-- File    : load_data_alternative.sql
-- Purpose : Load the CSV files into MySQL WITHOUT Python (alternative to python/load_to_mysql.py)
-- Run     : AFTER database_schema.sql
--
-- BEFORE YOU RUN (one-time setup):
--   1. Run:  SHOW VARIABLES LIKE 'secure_file_priv';
--      MySQL only reads files from that folder
--      (usually C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/ on Windows).
--   2. Copy sales_reps.csv, cleaned_leads.csv and sales_activities.csv into that folder.
--   3. Replace the folder path below with YOUR secure_file_priv path (use forward slashes /).
-- =====================================================================

USE b2b_sales_analytics;

-- start clean so the script can be re-run (children first)
DELETE FROM sales_activities;
DELETE FROM sales_leads;
DELETE FROM sales_reps;

-- 1. sales_reps
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/sales_reps.csv'
INTO TABLE sales_reps
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(Sales_Rep_ID, Rep_Name, Region, @joining_date)
SET Joining_Date = STR_TO_DATE(TRIM(TRAILING '\r' FROM @joining_date), '%Y-%m-%d');

-- 2. sales_leads (blank cells become NULL, True/False becomes 1/0)
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/cleaned_leads.csv'
INTO TABLE sales_leads
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(Lead_ID, Company_Name, Industry, Company_Size, Size_Order, Location, Lead_Source, Service_Interest, Annual_Revenue_Cr, @revenue_imputed, Lead_Created_Date, Lead_Month, Lead_Stage, Stage_Order, Follow_Up_Status, @next_follow_up, Follow_Up_Flag, Days_Overdue, Sales_Rep_ID, @deal_value, Conversion, Deal_Outcome, Website_Visits, Email_Interactions, Calls_Made, Calls_Connected, Meetings, Total_Activities, @last_contact, @days_since_contact, Score_Size, Score_Revenue, Score_Website, Score_Email, Score_Meetings, Score_Service_Fit, Score_Prior_Engagement, Lead_Score, @lead_category)
SET Revenue_Imputed         = (@revenue_imputed = 'True'),
    Next_Follow_Up_Date     = NULLIF(@next_follow_up, ''),
    Deal_Value              = NULLIF(@deal_value, ''),
    Last_Contact_Date       = NULLIF(@last_contact, ''),
    Days_Since_Last_Contact = NULLIF(@days_since_contact, ''),
    Lead_Category           = TRIM(TRAILING '\r' FROM @lead_category);

-- 3. sales_activities
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/sales_activities.csv'
INTO TABLE sales_activities
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(Activity_ID, Lead_ID, Activity_Type, Activity_Date, @outcome)
SET Outcome = TRIM(TRAILING '\r' FROM @outcome);

-- 4. Verify: expect 10 / 2000 / 9035
SELECT 'sales_reps' AS table_name, COUNT(*) AS row_count FROM sales_reps
UNION ALL SELECT 'sales_leads',      COUNT(*) FROM sales_leads
UNION ALL SELECT 'sales_activities', COUNT(*) FROM sales_activities;

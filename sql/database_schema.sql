-- =====================================================================
-- B2B Sales Lead Generation & Customer Analytics Dashboard
-- File    : database_schema.sql
-- Purpose : Create the MySQL database, 3 linked tables, indexes and a reporting view
-- Needs   : MySQL 8.0+  (window functions / CTEs are used in the analysis queries)
-- Run     : Open in MySQL Workbench -> click the lightning icon (Execute All)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS b2b_sales_analytics
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE b2b_sales_analytics;

-- Drop in child -> parent order so the script can be re-run safely
DROP VIEW  IF EXISTS vw_leads_enriched;
DROP TABLE IF EXISTS sales_activities;
DROP TABLE IF EXISTS sales_leads;
DROP TABLE IF EXISTS sales_reps;

-- ---------------------------------------------------------------------
-- 1. sales_reps : one row per sales representative (parent table)
-- ---------------------------------------------------------------------
CREATE TABLE sales_reps (
    Sales_Rep_ID  VARCHAR(10)  NOT NULL,
    Rep_Name      VARCHAR(100) NOT NULL,
    Region        VARCHAR(20)  NOT NULL,
    Joining_Date  DATE         NOT NULL,
    PRIMARY KEY (Sales_Rep_ID)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. sales_leads : one row per B2B lead (output of the Python pipeline)
-- ---------------------------------------------------------------------
CREATE TABLE sales_leads (
    Lead_ID                 VARCHAR(10)   NOT NULL,
    Company_Name            VARCHAR(150)  NOT NULL,
    Industry                VARCHAR(30)   NOT NULL,
    Company_Size            VARCHAR(15)   NOT NULL,
    Size_Order              TINYINT       NOT NULL,
    Location                VARCHAR(30)   NOT NULL,
    Lead_Source             VARCHAR(30)   NOT NULL,
    Service_Interest        VARCHAR(40)   NOT NULL,
    Annual_Revenue_Cr       DECIMAL(8,1)  NOT NULL,
    Revenue_Imputed         TINYINT(1)    NOT NULL,
    Lead_Created_Date       DATE          NOT NULL,
    Lead_Month              CHAR(7)       NOT NULL,
    Lead_Stage              VARCHAR(15)   NOT NULL,   -- highest funnel stage reached
    Stage_Order             TINYINT       NOT NULL,   -- 1 New ... 6 Won
    Follow_Up_Status        VARCHAR(30)   NOT NULL,
    Next_Follow_Up_Date     DATE          NULL,
    Follow_Up_Flag          VARCHAR(25)   NOT NULL,   -- Overdue / Due Today / Upcoming / No Follow-up Needed
    Days_Overdue            INT           NOT NULL,
    Sales_Rep_ID            VARCHAR(10)   NOT NULL,
    Deal_Value              INT           NULL,       -- INR, only for Proposal / Won leads
    Conversion              VARCHAR(3)    NOT NULL,   -- Yes / No
    Deal_Outcome            VARCHAR(10)   NOT NULL,   -- Won / Lost / Open
    Website_Visits          INT           NOT NULL,
    Email_Interactions      INT           NOT NULL,
    Calls_Made              INT           NOT NULL,
    Calls_Connected         INT           NOT NULL,
    Meetings                INT           NOT NULL,
    Total_Activities        INT           NOT NULL,
    Last_Contact_Date       DATE          NULL,
    Days_Since_Last_Contact INT           NULL,
    Score_Size              TINYINT       NOT NULL,
    Score_Revenue           TINYINT       NOT NULL,
    Score_Website           TINYINT       NOT NULL,
    Score_Email             TINYINT       NOT NULL,
    Score_Meetings          TINYINT       NOT NULL,
    Score_Service_Fit       TINYINT       NOT NULL,
    Score_Prior_Engagement  TINYINT       NOT NULL,
    Lead_Score              TINYINT       NOT NULL,
    Lead_Category           VARCHAR(10)   NOT NULL,   -- Hot / Warm / Cold
    PRIMARY KEY (Lead_ID),
    CONSTRAINT fk_leads_rep FOREIGN KEY (Sales_Rep_ID) REFERENCES sales_reps (Sales_Rep_ID),
    CONSTRAINT chk_lead_score CHECK (Lead_Score BETWEEN 0 AND 100),
    CONSTRAINT chk_conversion CHECK (Conversion IN ('Yes', 'No'))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. sales_activities : calls, emails, meetings and website visits per lead
-- ---------------------------------------------------------------------
CREATE TABLE sales_activities (
    Activity_ID    VARCHAR(10) NOT NULL,
    Lead_ID        VARCHAR(10) NOT NULL,
    Activity_Type  VARCHAR(20) NOT NULL,   -- Call / Email / Meeting / Website Visit
    Activity_Date  DATE        NOT NULL,
    Outcome        VARCHAR(30) NOT NULL,
    PRIMARY KEY (Activity_ID),
    CONSTRAINT fk_activity_lead FOREIGN KEY (Lead_ID) REFERENCES sales_leads (Lead_ID)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Indexes: speed up the GROUP BY / JOIN / filter columns used most in analysis
-- ---------------------------------------------------------------------
CREATE INDEX idx_leads_source     ON sales_leads (Lead_Source);
CREATE INDEX idx_leads_industry   ON sales_leads (Industry);
CREATE INDEX idx_leads_location   ON sales_leads (Location);
CREATE INDEX idx_leads_stage      ON sales_leads (Stage_Order);
CREATE INDEX idx_leads_category   ON sales_leads (Lead_Category);
CREATE INDEX idx_leads_followup   ON sales_leads (Follow_Up_Flag, Next_Follow_Up_Date);
CREATE INDEX idx_leads_rep        ON sales_leads (Sales_Rep_ID);
CREATE INDEX idx_leads_created    ON sales_leads (Lead_Created_Date);
CREATE INDEX idx_activity_lead    ON sales_activities (Lead_ID);
CREATE INDEX idx_activity_type    ON sales_activities (Activity_Type, Activity_Date);

-- ---------------------------------------------------------------------
-- Reporting view: leads + rep details in one place (handy for Power BI)
-- ---------------------------------------------------------------------
CREATE VIEW vw_leads_enriched AS
SELECT  l.*,
        r.Rep_Name,
        r.Region AS Rep_Region
FROM    sales_leads l
JOIN    sales_reps  r ON r.Sales_Rep_ID = l.Sales_Rep_ID;

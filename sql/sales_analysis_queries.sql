-- =====================================================================
-- B2B Sales Lead Generation & Customer Analytics Dashboard
-- File    : sales_analysis_queries.sql
-- Purpose : Business queries that answer the sales team's questions
-- Needs   : MySQL 8.0+ (uses CTEs and window functions)
-- Tip     : In MySQL Workbench put the cursor inside one query and press Ctrl+Enter
--           to run only that query. Run the first two lines (USE / SET) once per session.
-- =====================================================================

USE b2b_sales_analytics;

-- "Today" for this project's dataset (fixed so results match the Python pipeline)
SET @as_of_date = '2026-09-19';


-- #####################################################################
-- SECTION A : EXECUTIVE OVERVIEW
-- #####################################################################

-- Q1. Headline KPIs for the dashboard cards
-- Business question: How is the sales pipeline performing overall?
SELECT
    COUNT(*)                                                                    AS total_leads,
    SUM(Stage_Order >= 3)                                                       AS qualified_leads,
    SUM(Conversion = 'Yes')                                                     AS won_deals,
    ROUND(100.0 * SUM(Conversion = 'Yes') / COUNT(*), 2)                        AS conversion_rate_pct,
    SUM(CASE WHEN Deal_Outcome = 'Open' AND Lead_Stage = 'Proposal'
             THEN Deal_Value ELSE 0 END)                                        AS open_pipeline_value_inr,
    SUM(CASE WHEN Conversion = 'Yes' THEN Deal_Value ELSE 0 END)                AS won_revenue_inr,
    ROUND(AVG(CASE WHEN Conversion = 'Yes' THEN Deal_Value END), 0)             AS avg_won_deal_value_inr
FROM sales_leads;


-- Q2. Sales funnel with drop-off at every stage
-- Business question: Where do we lose most leads?
-- Logic: a lead that reached "Won" also passed every earlier stage, so we add up
--        the leads from the last stage backwards (window SUM ordered DESC).
WITH stage_counts AS (
    SELECT Stage_Order, Lead_Stage, COUNT(*) AS leads_ending_here
    FROM   sales_leads
    GROUP  BY Stage_Order, Lead_Stage
),
funnel AS (
    SELECT Stage_Order, Lead_Stage,
           SUM(leads_ending_here) OVER (ORDER BY Stage_Order DESC) AS leads_reached
    FROM   stage_counts
)
SELECT
    Lead_Stage,
    leads_reached,
    ROUND(100.0 * leads_reached / FIRST_VALUE(leads_reached) OVER (ORDER BY Stage_Order), 2) AS pct_of_all_leads,
    ROUND(100.0 * leads_reached / LAG(leads_reached)         OVER (ORDER BY Stage_Order), 2) AS step_conversion_pct
FROM   funnel
ORDER  BY Stage_Order;


-- Q3. Monthly lead trend with month-over-month growth and cohort conversion
-- Business question: Is lead generation growing? Do newer cohorts convert as well?
-- (Recent cohorts naturally show lower conversion because deals need time to close.)
WITH monthly AS (
    SELECT Lead_Month,
           COUNT(*)                 AS leads,
           SUM(Conversion = 'Yes')  AS won
    FROM   sales_leads
    GROUP  BY Lead_Month
)
SELECT
    Lead_Month,
    leads,
    won,
    ROUND(100.0 * won / leads, 2)                                                    AS cohort_conversion_pct,
    ROUND(100.0 * (leads - LAG(leads) OVER (ORDER BY Lead_Month))
                / LAG(leads) OVER (ORDER BY Lead_Month), 1)                          AS mom_growth_pct,
    SUM(leads) OVER (ORDER BY Lead_Month)                                            AS cumulative_leads
FROM   monthly
ORDER  BY Lead_Month;


-- #####################################################################
-- SECTION B : LEAD SOURCE ANALYSIS
-- #####################################################################

-- Q4. Lead source performance
-- Business question: Which lead generation channels produce better-quality leads?
SELECT
    Lead_Source,
    COUNT(*)                                                             AS total_leads,
    SUM(Stage_Order >= 3)                                                AS qualified,
    SUM(Stage_Order >= 4)                                                AS reached_meeting,
    SUM(Conversion = 'Yes')                                              AS won,
    ROUND(100.0 * SUM(Stage_Order >= 3) / COUNT(*), 2)                   AS qualification_rate_pct,
    ROUND(100.0 * SUM(Conversion = 'Yes') / COUNT(*), 2)                 AS conversion_rate_pct,
    SUM(CASE WHEN Conversion = 'Yes' THEN Deal_Value ELSE 0 END)         AS won_revenue_inr,
    RANK() OVER (ORDER BY 1.0 * SUM(Conversion = 'Yes') / COUNT(*) DESC)       AS conversion_rank
FROM   sales_leads
GROUP  BY Lead_Source
ORDER  BY conversion_rate_pct DESC;


-- Q5. Lead quality by source (based on the lead score)
-- Business question: Do high-volume channels bring high-scoring leads or just noise?
SELECT
    Lead_Source,
    COUNT(*)                                                    AS total_leads,
    ROUND(AVG(Lead_Score), 1)                                   AS avg_lead_score,
    SUM(Lead_Category = 'Hot')                                  AS hot_leads,
    ROUND(100.0 * SUM(Lead_Category = 'Hot') / COUNT(*), 2)     AS hot_lead_pct,
    ROUND(100.0 * SUM(Lead_Category = 'Cold') / COUNT(*), 2)    AS cold_lead_pct
FROM   sales_leads
GROUP  BY Lead_Source
ORDER  BY avg_lead_score DESC;


-- #####################################################################
-- SECTION C : INDUSTRY, COMPANY SIZE, LOCATION
-- #####################################################################

-- Q6. Industry analysis
-- Business question: Which industries should sales focus on?
SELECT
    Industry,
    COUNT(*)                                                             AS total_leads,
    SUM(Stage_Order >= 3)                                                AS qualified,
    SUM(Conversion = 'Yes')                                              AS won,
    ROUND(100.0 * SUM(Conversion = 'Yes') / COUNT(*), 2)                 AS conversion_rate_pct,
    SUM(CASE WHEN Conversion = 'Yes' THEN Deal_Value ELSE 0 END)         AS won_revenue_inr,
    ROUND(AVG(Lead_Score), 1)                                            AS avg_lead_score,
    RANK() OVER (ORDER BY 1.0 * SUM(Conversion = 'Yes') / COUNT(*) DESC)       AS conversion_rank
FROM   sales_leads
GROUP  BY Industry
ORDER  BY conversion_rate_pct DESC;


-- Q7. Company size analysis
-- Business question: Do bigger companies convert more and pay more?
SELECT
    Company_Size,
    COUNT(*)                                                             AS total_leads,
    SUM(Conversion = 'Yes')                                              AS won,
    ROUND(100.0 * SUM(Conversion = 'Yes') / COUNT(*), 2)                 AS conversion_rate_pct,
    ROUND(AVG(Deal_Value), 0)                                            AS avg_deal_value_inr,
    SUM(CASE WHEN Conversion = 'Yes' THEN Deal_Value ELSE 0 END)         AS won_revenue_inr
FROM   sales_leads
GROUP  BY Company_Size, Size_Order
ORDER  BY Size_Order;


-- Q8. Location analysis
-- Business question: Which cities generate the most leads and revenue?
SELECT
    Location,
    COUNT(*)                                                             AS total_leads,
    SUM(Conversion = 'Yes')                                              AS won,
    ROUND(100.0 * SUM(Conversion = 'Yes') / COUNT(*), 2)                 AS conversion_rate_pct,
    SUM(CASE WHEN Conversion = 'Yes' THEN Deal_Value ELSE 0 END)         AS won_revenue_inr,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                   AS share_of_leads_pct
FROM   sales_leads
GROUP  BY Location
ORDER  BY total_leads DESC;


-- Q9. Best industry x lead-source combinations to target
-- Business question: Where is the sweet spot? (only combinations with 20+ leads, to avoid tiny samples)
SELECT
    Industry,
    Lead_Source,
    COUNT(*)                                                             AS total_leads,
    SUM(Conversion = 'Yes')                                              AS won,
    ROUND(100.0 * SUM(Conversion = 'Yes') / COUNT(*), 2)                 AS conversion_rate_pct
FROM   sales_leads
GROUP  BY Industry, Lead_Source
HAVING COUNT(*) >= 20
ORDER  BY conversion_rate_pct DESC, total_leads DESC
LIMIT  10;


-- Q10. Service demand by industry
-- Business question: Which service should we pitch to which industry?
SELECT
    Industry,
    Service_Interest,
    COUNT(*)                                                             AS total_leads,
    SUM(Conversion = 'Yes')                                              AS won,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY Industry), 1) AS pct_of_industry_leads
FROM   sales_leads
GROUP  BY Industry, Service_Interest
ORDER  BY Industry, total_leads DESC;


-- #####################################################################
-- SECTION D : LEAD SCORING
-- #####################################################################

-- Q11. Lead category distribution and conversion (does the score work?)
-- Business question: Do Hot leads really convert better than Cold leads?
SELECT
    Lead_Category,
    COUNT(*)                                                             AS total_leads,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                   AS share_of_leads_pct,
    SUM(Conversion = 'Yes')                                              AS won,
    ROUND(100.0 * SUM(Conversion = 'Yes') / COUNT(*), 2)                 AS conversion_rate_pct,
    ROUND(AVG(Lead_Score), 1)                                            AS avg_lead_score
FROM   sales_leads
GROUP  BY Lead_Category
ORDER  BY avg_lead_score DESC;


-- Q12. Conversion by score band (finer view of the same question)
SELECT
    CASE WHEN Lead_Score >= 80 THEN '80-100'
         WHEN Lead_Score >= 60 THEN '60-79'
         WHEN Lead_Score >= 40 THEN '40-59'
         WHEN Lead_Score >= 20 THEN '20-39'
         ELSE '0-19' END                                                 AS score_band,
    COUNT(*)                                                             AS total_leads,
    SUM(Conversion = 'Yes')                                              AS won,
    ROUND(100.0 * SUM(Conversion = 'Yes') / COUNT(*), 2)                 AS conversion_rate_pct
FROM   sales_leads
GROUP  BY score_band
ORDER  BY score_band DESC;


-- Q13. Priority list: high-potential leads that are still open
-- Business question: Which high-score leads should the sales team work on right now?
SELECT
    l.Lead_ID,
    l.Company_Name,
    l.Industry,
    l.Lead_Source,
    l.Lead_Stage,
    l.Lead_Score,
    l.Lead_Category,
    l.Deal_Value,
    l.Follow_Up_Status,
    l.Next_Follow_Up_Date,
    r.Rep_Name
FROM   sales_leads l
JOIN   sales_reps  r ON r.Sales_Rep_ID = l.Sales_Rep_ID
WHERE  l.Lead_Score >= 80
  AND  l.Deal_Outcome = 'Open'
ORDER  BY l.Lead_Score DESC, l.Deal_Value DESC
LIMIT  25;


-- Q14. Conversion by number of meetings held
-- Business question: How much do meetings matter?
SELECT
    Meetings                                                             AS meetings_held,
    COUNT(*)                                                             AS total_leads,
    SUM(Conversion = 'Yes')                                              AS won,
    ROUND(100.0 * SUM(Conversion = 'Yes') / COUNT(*), 2)                 AS conversion_rate_pct
FROM   sales_leads
GROUP  BY Meetings
ORDER  BY Meetings;


-- #####################################################################
-- SECTION E : FOLLOW-UP MANAGEMENT
-- #####################################################################

-- Q15. Follow-up status summary
-- Business question: What is the current state of our follow-ups?
SELECT
    Follow_Up_Status,
    COUNT(*)                                                             AS total_leads,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                   AS share_pct
FROM   sales_leads
GROUP  BY Follow_Up_Status
ORDER  BY total_leads DESC;


-- Q16. Follow-up workload today: overdue, due today, upcoming
-- Business question: How many leads need follow-up today?
SELECT
    Follow_Up_Flag,
    COUNT(*)                                                             AS total_leads,
    SUM(Lead_Category = 'Hot')                                           AS hot_leads,
    ROUND(AVG(CASE WHEN Follow_Up_Flag = 'Overdue' THEN Days_Overdue END), 1) AS avg_days_overdue
FROM   sales_leads
GROUP  BY Follow_Up_Flag
ORDER  BY FIELD(Follow_Up_Flag, 'Overdue', 'Due Today', 'Upcoming', 'No Follow-up Needed');


-- Q17. Overdue follow-ups, most valuable first
-- Business question: Which overdue leads should be called first?
SELECT
    l.Lead_ID,
    l.Company_Name,
    l.Industry,
    l.Lead_Score,
    l.Lead_Category,
    l.Follow_Up_Status,
    l.Next_Follow_Up_Date,
    l.Days_Overdue,
    r.Rep_Name
FROM   sales_leads l
JOIN   sales_reps  r ON r.Sales_Rep_ID = l.Sales_Rep_ID
WHERE  l.Follow_Up_Flag = 'Overdue'
ORDER  BY l.Lead_Score DESC, l.Days_Overdue DESC
LIMIT  25;


-- Q18. Follow-up workload by sales rep
-- Business question: Which reps have a follow-up backlog?
SELECT
    r.Rep_Name,
    r.Region,
    SUM(l.Follow_Up_Flag = 'Overdue')                                    AS overdue,
    SUM(l.Follow_Up_Flag = 'Due Today')                                  AS due_today,
    SUM(l.Follow_Up_Flag = 'Upcoming')                                   AS upcoming,
    ROUND(AVG(CASE WHEN l.Follow_Up_Flag = 'Overdue' THEN l.Days_Overdue END), 1) AS avg_days_overdue
FROM   sales_reps r
LEFT JOIN sales_leads l ON l.Sales_Rep_ID = r.Sales_Rep_ID
GROUP  BY r.Sales_Rep_ID, r.Rep_Name, r.Region
ORDER  BY overdue DESC;


-- Q19. Today's call list: top 3 open leads per rep
-- Business question: What should each rep work on first today?
WITH ranked AS (
    SELECT
        l.Sales_Rep_ID,
        l.Lead_ID,
        l.Company_Name,
        l.Lead_Score,
        l.Follow_Up_Flag,
        l.Follow_Up_Status,
        ROW_NUMBER() OVER (PARTITION BY l.Sales_Rep_ID
                           ORDER BY l.Lead_Score DESC, l.Days_Overdue DESC) AS rn
    FROM   sales_leads l
    WHERE  l.Deal_Outcome = 'Open'
      AND  l.Follow_Up_Flag IN ('Overdue', 'Due Today')
)
SELECT r.Rep_Name, k.rn AS priority, k.Lead_ID, k.Company_Name, k.Lead_Score, k.Follow_Up_Flag, k.Follow_Up_Status
FROM   ranked k
JOIN   sales_reps r ON r.Sales_Rep_ID = k.Sales_Rep_ID
WHERE  k.rn <= 3
ORDER  BY r.Rep_Name, k.rn;


-- #####################################################################
-- SECTION F : SALES REP PERFORMANCE
-- #####################################################################

-- Q20. Sales rep leaderboard
-- Business question: How is each rep performing?
SELECT
    r.Rep_Name,
    r.Region,
    COUNT(l.Lead_ID)                                                     AS total_leads,
    SUM(l.Conversion = 'Yes')                                            AS won,
    ROUND(100.0 * SUM(l.Conversion = 'Yes') / COUNT(l.Lead_ID), 2)       AS conversion_rate_pct,
    SUM(CASE WHEN l.Conversion = 'Yes' THEN l.Deal_Value ELSE 0 END)     AS won_revenue_inr,
    SUM(CASE WHEN l.Deal_Outcome = 'Open' AND l.Lead_Stage = 'Proposal'
             THEN l.Deal_Value ELSE 0 END)                               AS open_pipeline_inr,
    RANK() OVER (ORDER BY SUM(CASE WHEN l.Conversion = 'Yes' THEN l.Deal_Value ELSE 0 END) DESC) AS revenue_rank
FROM   sales_reps r
LEFT JOIN sales_leads l ON l.Sales_Rep_ID = r.Sales_Rep_ID
GROUP  BY r.Sales_Rep_ID, r.Rep_Name, r.Region
ORDER  BY revenue_rank;


-- #####################################################################
-- SECTION G : ACTIVITY ANALYSIS (uses the sales_activities table)
-- #####################################################################

-- Q21. Activity outcome mix
-- Business question: What happens when we call, email or meet a lead?
SELECT
    Activity_Type,
    Outcome,
    COUNT(*)                                                             AS total_activities,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY Activity_Type), 1) AS pct_within_type
FROM   sales_activities
GROUP  BY Activity_Type, Outcome
ORDER  BY Activity_Type, total_activities DESC;


-- Q22. Effort vs result: average activity per lead by deal outcome
-- Business question: Do won deals get more touches than lost ones?
SELECT
    l.Deal_Outcome,
    COUNT(DISTINCT l.Lead_ID)                                            AS leads,
    ROUND(COUNT(a.Activity_ID) / COUNT(DISTINCT l.Lead_ID), 1)           AS avg_activities_per_lead,
    ROUND(SUM(a.Activity_Type = 'Call')          / COUNT(DISTINCT l.Lead_ID), 1) AS avg_calls,
    ROUND(SUM(a.Activity_Type = 'Email')         / COUNT(DISTINCT l.Lead_ID), 1) AS avg_emails,
    ROUND(SUM(a.Activity_Type = 'Meeting')       / COUNT(DISTINCT l.Lead_ID), 1) AS avg_meetings,
    ROUND(SUM(a.Activity_Type = 'Website Visit') / COUNT(DISTINCT l.Lead_ID), 1) AS avg_web_visits
FROM   sales_leads l
LEFT JOIN sales_activities a ON a.Lead_ID = l.Lead_ID
GROUP  BY l.Deal_Outcome
ORDER  BY avg_activities_per_lead DESC;


-- Q23. Neglected leads: nobody has called, emailed or met them, and they are 30+ days old
-- Business question: Which leads are slipping through the cracks?
-- LEFT JOIN + "IS NULL" (anti-join) finds leads with NO sales touch.
SELECT
    l.Lead_ID,
    l.Company_Name,
    l.Industry,
    l.Lead_Source,
    l.Lead_Score,
    l.Lead_Created_Date,
    DATEDIFF(@as_of_date, l.Lead_Created_Date)                           AS days_since_created,
    r.Rep_Name
FROM   sales_leads l
LEFT JOIN sales_activities a
       ON a.Lead_ID = l.Lead_ID
      AND a.Activity_Type IN ('Call', 'Email', 'Meeting')
JOIN   sales_reps r ON r.Sales_Rep_ID = l.Sales_Rep_ID
WHERE  a.Activity_ID IS NULL
  AND  DATEDIFF(@as_of_date, l.Lead_Created_Date) > 30
ORDER  BY l.Lead_Score DESC, days_since_created DESC
LIMIT  25;


-- #####################################################################
-- SECTION H : DATA QUALITY CHECK
-- #####################################################################

-- Q24. Reconciliation: engagement counts stored on sales_leads must match the raw activity log
-- Business question: Can we trust the numbers? (every mismatch column should be 0)
WITH log_counts AS (
    SELECT
        Lead_ID,
        SUM(Activity_Type = 'Website Visit')                             AS visits,
        SUM(Activity_Type = 'Call')                                      AS calls,
        SUM(Activity_Type = 'Meeting' AND Outcome = 'Completed')         AS meetings,
        COUNT(*)                                                         AS total
    FROM   sales_activities
    GROUP  BY Lead_ID
)
SELECT
    COUNT(*)                                                             AS leads_checked,
    SUM(l.Website_Visits   <> COALESCE(c.visits,   0))                   AS website_mismatch,
    SUM(l.Calls_Made       <> COALESCE(c.calls,    0))                   AS calls_mismatch,
    SUM(l.Meetings         <> COALESCE(c.meetings, 0))                   AS meetings_mismatch,
    SUM(l.Total_Activities <> COALESCE(c.total,    0))                   AS total_mismatch
FROM   sales_leads l
LEFT JOIN log_counts c ON c.Lead_ID = l.Lead_ID;

"""
data_cleaning_lead_scoring.py
-----------------------------
Step 3 of the B2B Sales Lead Analytics project.

Pipeline:
    raw_leads.csv + sales_activities.csv
        -> clean & standardise
        -> engineer engagement / follow-up features
        -> rule-based Lead Score (0-100) + Hot / Warm / Cold category
        -> validate
        -> cleaned_leads.csv  (loaded into MySQL / Power BI later)

Run:  python data_cleaning_lead_scoring.py
"""

import os
import re
import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
TODAY = pd.Timestamp("2026-09-19")  # fixed "as-of" date so results are reproducible

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "..", "dataset")
REPORT_DIR = os.path.join(BASE, "..", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

log_lines = []


def log(msg=""):
    print(msg)
    log_lines.append(msg)


# ----------------------------------------------------------------------------
# 1. Load raw data
# ----------------------------------------------------------------------------
raw = pd.read_csv(os.path.join(DATA_DIR, "raw_leads.csv"), dtype=str)
acts = pd.read_csv(os.path.join(DATA_DIR, "sales_activities.csv"), dtype=str)
reps = pd.read_csv(os.path.join(DATA_DIR, "sales_reps.csv"), dtype=str)

log("=" * 60)
log("DATA CLEANING LOG")
log("=" * 60)
log(f"Raw leads loaded        : {len(raw)} rows, {raw.shape[1]} columns")
log(f"Activities loaded       : {len(acts)} rows")
log(f"Sales reps loaded       : {len(reps)} rows")

# ----------------------------------------------------------------------------
# 2. Cleaning
# ----------------------------------------------------------------------------
df = raw.copy()

# 2.1 Trim whitespace in every text column
for col in df.columns:
    df[col] = df[col].str.strip()

# 2.2 Remove duplicate leads (same Lead_ID). Original row appears first, duplicates are appended.
dup_count = df.duplicated(subset="Lead_ID").sum()
df = df.drop_duplicates(subset="Lead_ID", keep="first").reset_index(drop=True)
log(f"\n[Duplicates] removed    : {dup_count} duplicate Lead_IDs -> {len(df)} unique leads")

# 2.3 Standardise categorical text using case-insensitive lookup maps
INDUSTRIES = ["FinTech", "Healthcare", "E-commerce", "Education", "Manufacturing", "Logistics", "Retail", "SaaS"]
SOURCES = ["LinkedIn", "Website", "Email Campaign", "Cold Calling", "Referral", "Events", "Google Search"]
LOCATION_MAP = {c.lower(): c for c in ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Pune", "Chennai",
                                       "Jaipur", "Gurgaon", "Noida", "Ahmedabad"]}
LOCATION_MAP.update({"bangalore": "Bengaluru", "new delhi": "Delhi", "gurugram": "Gurgaon"})


def standardise(series, mapping, label):
    before = series.copy()
    out = series.str.lower().map(mapping)
    unmapped = series[out.isna() & series.notna()].unique()
    if len(unmapped):
        raise ValueError(f"Unmapped values in {label}: {unmapped}")
    out = out.where(series.notna(), None)
    log(f"[Standardise] {label:<11}: {(before != out).sum()} values fixed "
        f"({before.nunique()} variants -> {out.nunique()} clean values)")
    return out


df["Industry"] = standardise(df["Industry"], {i.lower(): i for i in INDUSTRIES}, "Industry")
df["Lead_Source"] = standardise(df["Lead_Source"], {s.lower(): s for s in SOURCES}, "Lead_Source")

loc_before = df["Location"].copy()
df["Location"] = df["Location"].str.lower().map(LOCATION_MAP)
n_loc_fixed = ((loc_before != df["Location"]) & loc_before.notna()).sum()
n_loc_missing = df["Location"].isna().sum()
df["Location"] = df["Location"].fillna("Unknown")
log(f"[Standardise] Location    : {n_loc_fixed} aliases/spacing fixed (Bangalore, Gurugram, New Delhi ...)")
log(f"[Missing]     Location    : {n_loc_missing} missing -> filled with 'Unknown' (kept honest, not guessed)")

# 2.4 Parse mixed date formats (YYYY-MM-DD and DD/MM/YYYY)
def parse_date(s):
    if pd.isna(s):
        return pd.NaT
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return pd.to_datetime(s, format="%Y-%m-%d")
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", s):
        return pd.to_datetime(s, format="%d/%m/%Y")
    raise ValueError(f"Unrecognised date format: {s}")


for col in ["Lead_Created_Date", "Next_Follow_Up_Date"]:
    bad_fmt = df[col].notna() & df[col].str.contains("/", na=False)
    df[col] = df[col].apply(parse_date)
    log(f"[Dates]       {col:<19}: {bad_fmt.sum()} DD/MM/YYYY values converted to ISO")

# 2.5 Numeric columns
df["Annual_Revenue_Cr"] = pd.to_numeric(df["Annual_Revenue_Cr"])
df["Deal_Value"] = pd.to_numeric(df["Deal_Value"])

# 2.6 Impute missing revenue with the median of the same Company_Size band
df["Revenue_Imputed"] = df["Annual_Revenue_Cr"].isna()
size_median = df.groupby("Company_Size")["Annual_Revenue_Cr"].transform("median")
df["Annual_Revenue_Cr"] = df["Annual_Revenue_Cr"].fillna(size_median).round(1)
log(f"[Missing]     Revenue     : {df['Revenue_Imputed'].sum()} missing -> median of same Company_Size band "
    f"(flagged in Revenue_Imputed)")

# ----------------------------------------------------------------------------
# 3. Feature engineering from sales_activities
# ----------------------------------------------------------------------------
acts["Activity_Date"] = pd.to_datetime(acts["Activity_Date"], format="%Y-%m-%d")

orphans = ~acts["Lead_ID"].isin(df["Lead_ID"])
if orphans.any():
    raise ValueError(f"{orphans.sum()} activities point to unknown Lead_IDs")


def count_where(mask, name):
    return acts[mask].groupby("Lead_ID").size().rename(name)


feat = pd.concat([
    count_where(acts["Activity_Type"] == "Website Visit", "Website_Visits"),
    count_where((acts["Activity_Type"] == "Email") & acts["Outcome"].isin(["Opened", "Replied"]), "Email_Interactions"),
    count_where(acts["Activity_Type"] == "Call", "Calls_Made"),
    count_where((acts["Activity_Type"] == "Call") & (acts["Outcome"] == "Connected"), "Calls_Connected"),
    count_where((acts["Activity_Type"] == "Meeting") & (acts["Outcome"] == "Completed"), "Meetings"),
    acts.groupby("Lead_ID").size().rename("Total_Activities"),
    # last *sales* touch = call / email / meeting (website visits are the lead's action, not ours)
    acts[acts["Activity_Type"].isin(["Call", "Email", "Meeting"])].groupby("Lead_ID")["Activity_Date"].max().rename("Last_Contact_Date"),
], axis=1)

df = df.merge(feat, left_on="Lead_ID", right_index=True, how="left")
count_cols = ["Website_Visits", "Email_Interactions", "Calls_Made", "Calls_Connected", "Meetings", "Total_Activities"]
df[count_cols] = df[count_cols].fillna(0).astype(int)
df["Days_Since_Last_Contact"] = (TODAY - df["Last_Contact_Date"]).dt.days  # NaN = never contacted
log(f"\n[Features]    engagement metrics built from {len(acts)} activities "
    f"({(df['Total_Activities'] == 0).sum()} leads have no activity yet)")

# ----------------------------------------------------------------------------
# 4. Business features: funnel order, month, follow-up flag, outcome
# ----------------------------------------------------------------------------
STAGE_ORDER = {"New": 1, "Contacted": 2, "Qualified": 3, "Meeting": 4, "Proposal": 5, "Won": 6}
SIZE_ORDER = {"1-50": 1, "51-200": 2, "201-500": 3, "501-1000": 4, "1000+": 5}
df["Stage_Order"] = df["Lead_Stage"].map(STAGE_ORDER)
df["Size_Order"] = df["Company_Size"].map(SIZE_ORDER)
df["Lead_Month"] = df["Lead_Created_Date"].dt.strftime("%Y-%m")


def follow_up_flag(d):
    if pd.isna(d):
        return "No Follow-up Needed"
    if d < TODAY:
        return "Overdue"
    if d == TODAY:
        return "Due Today"
    return "Upcoming"


df["Follow_Up_Flag"] = df["Next_Follow_Up_Date"].apply(follow_up_flag)
df["Days_Overdue"] = np.where(df["Follow_Up_Flag"] == "Overdue", (TODAY - df["Next_Follow_Up_Date"]).dt.days, 0)

# Won / Lost / Open
df["Deal_Outcome"] = np.select(
    [df["Conversion"] == "Yes", df["Follow_Up_Status"].isin(["Not Interested", "Closed"])],
    ["Won", "Lost"], default="Open")

# ----------------------------------------------------------------------------
# 5. Lead scoring (0-100), fully rule-based and explainable
#    Size 20 + Revenue 20 + Website 10 + Email 10 + Meetings 20 + Service fit 10 + Prior engagement 10
# ----------------------------------------------------------------------------
SIZE_POINTS = {"1-50": 0, "51-200": 5, "201-500": 10, "501-1000": 15, "1000+": 20}

# Services that are the natural "core need" for each industry -> full relevance points
CORE_SERVICES = {
    "FinTech": {"Cybersecurity", "Cloud Services"},
    "Healthcare": {"Digital Transformation", "Cybersecurity"},
    "E-commerce": {"Software Development", "Cloud Services"},
    "Education": {"Digital Transformation", "Software Development"},
    "Manufacturing": {"Digital Transformation", "Cloud Services"},
    "Logistics": {"Digital Transformation", "Cloud Services"},
    "Retail": {"Cloud Services", "Digital Transformation"},
    "SaaS": {"DevOps", "Cloud Services"},
}


def revenue_points(cr):
    return 0 if cr < 10 else 5 if cr < 50 else 10 if cr < 200 else 15 if cr < 500 else 20


def website_points(n):
    return 0 if n == 0 else 3 if n == 1 else 6 if n <= 3 else 10


def email_points(n):
    return 0 if n == 0 else 5 if n == 1 else 10


def meeting_points(n):
    return 0 if n == 0 else 12 if n == 1 else 20


def prior_engagement_points(n_connected):
    return 0 if n_connected == 0 else 5 if n_connected == 1 else 10


df["Score_Size"] = df["Company_Size"].map(SIZE_POINTS)
df["Score_Revenue"] = df["Annual_Revenue_Cr"].apply(revenue_points)
df["Score_Website"] = df["Website_Visits"].apply(website_points)
df["Score_Email"] = df["Email_Interactions"].apply(email_points)
df["Score_Meetings"] = df["Meetings"].apply(meeting_points)
df["Score_Service_Fit"] = [10 if s in CORE_SERVICES[i] else 4 for i, s in zip(df["Industry"], df["Service_Interest"])]
df["Score_Prior_Engagement"] = df["Calls_Connected"].apply(prior_engagement_points)

score_cols = ["Score_Size", "Score_Revenue", "Score_Website", "Score_Email",
              "Score_Meetings", "Score_Service_Fit", "Score_Prior_Engagement"]
df["Lead_Score"] = df[score_cols].sum(axis=1)
df["Lead_Category"] = pd.cut(df["Lead_Score"], bins=[-1, 59, 79, 100], labels=["Cold", "Warm", "Hot"]).astype(str)

# ----------------------------------------------------------------------------
# 6. Validation checks (fail loudly if the data is inconsistent)
# ----------------------------------------------------------------------------
checks = {
    "Lead_ID is unique": df["Lead_ID"].is_unique,
    "Conversion = Yes only for Won leads": ((df["Conversion"] == "Yes") == (df["Lead_Stage"] == "Won")).all(),
    "Deal_Value exists only for Proposal/Won": (df["Deal_Value"].notna() == df["Lead_Stage"].isin(["Proposal", "Won"])).all(),
    "No nulls in key columns": df[["Lead_ID", "Company_Name", "Industry", "Company_Size", "Location", "Lead_Source",
                                    "Service_Interest", "Annual_Revenue_Cr", "Lead_Created_Date", "Lead_Stage",
                                    "Follow_Up_Status", "Sales_Rep_ID"]].notna().all().all(),
    "Follow-up dates only for pending statuses": (
        df["Next_Follow_Up_Date"].notna() ==
        df["Follow_Up_Status"].isin(["Follow-up Required", "Contacted", "Waiting for Response", "Meeting Scheduled"])).all(),
    "No lead created after today": (df["Lead_Created_Date"] <= TODAY).all(),
    "Lead_Score within 0-100": df["Lead_Score"].between(0, 100).all(),
    "All Sales_Rep_IDs exist": df["Sales_Rep_ID"].isin(reps["Sales_Rep_ID"]).all(),
}
log("\n" + "=" * 60)
log("VALIDATION CHECKS")
log("=" * 60)
for name, ok in checks.items():
    log(f"[{'PASS' if ok else 'FAIL'}] {name}")
if not all(checks.values()):
    raise SystemExit("Validation failed - see log above.")

# ----------------------------------------------------------------------------
# 7. Save
# ----------------------------------------------------------------------------
ORDER = ["Lead_ID", "Company_Name", "Industry", "Company_Size", "Size_Order", "Location", "Lead_Source",
         "Service_Interest", "Annual_Revenue_Cr", "Revenue_Imputed", "Lead_Created_Date", "Lead_Month",
         "Lead_Stage", "Stage_Order", "Follow_Up_Status", "Next_Follow_Up_Date", "Follow_Up_Flag", "Days_Overdue",
         "Sales_Rep_ID", "Deal_Value", "Conversion", "Deal_Outcome",
         "Website_Visits", "Email_Interactions", "Calls_Made", "Calls_Connected", "Meetings", "Total_Activities",
         "Last_Contact_Date", "Days_Since_Last_Contact"] + score_cols + ["Lead_Score", "Lead_Category"]
out = df[ORDER].copy()
for c in ["Lead_Created_Date", "Next_Follow_Up_Date", "Last_Contact_Date"]:
    out[c] = out[c].dt.strftime("%Y-%m-%d")
out["Deal_Value"] = out["Deal_Value"].astype("Int64")
out["Days_Since_Last_Contact"] = out["Days_Since_Last_Contact"].astype("Int64")
out.to_csv(os.path.join(DATA_DIR, "cleaned_leads.csv"), index=False)

# ----------------------------------------------------------------------------
# 8. Quick summary (also proves the score is useful)
# ----------------------------------------------------------------------------
log("\n" + "=" * 60)
log("SUMMARY")
log("=" * 60)
log(f"Clean leads saved       : {len(out)} rows, {out.shape[1]} columns -> dataset/cleaned_leads.csv")
log("\nLead category counts:")
log(df["Lead_Category"].value_counts().reindex(["Hot", "Warm", "Cold"]).to_string())
conv = df.groupby("Lead_Category")["Conversion"].agg(leads="size", won=lambda s: (s == "Yes").sum())
conv["conversion_%"] = (conv["won"] / conv["leads"] * 100).round(2)
log("\nConversion by Lead category (does the score work?):")
log(conv.reindex(["Hot", "Warm", "Cold"]).to_string())
log(f"\nOverall conversion      : {(df['Conversion'] == 'Yes').mean() * 100:.2f}%")
log("\nFollow-up flags:")
log(df["Follow_Up_Flag"].value_counts().to_string())
log(f"\nDeal outcome: {df['Deal_Outcome'].value_counts().to_dict()}")
pipeline = df.loc[(df["Deal_Outcome"] == "Open") & (df["Lead_Stage"] == "Proposal"), "Deal_Value"].sum()
log(f"Open pipeline value (Proposal stage): Rs {pipeline:,.0f}")

with open(os.path.join(REPORT_DIR, "data_cleaning_log.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))

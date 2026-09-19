"""
generate_raw_data.py
--------------------
Generates a synthetic (but business-realistic) B2B lead dataset for an IT services company.

Outputs (in ../dataset/):
    raw_leads.csv         -> ~2,060 rows (2,000 unique leads + ~3% duplicates, with deliberate data-quality issues)
    sales_activities.csv  -> call / email / meeting / website-visit log per lead
    sales_reps.csv        -> 10 sales reps

Business rules baked in:
    * Funnel:  2000 -> 1400 Contacted -> 850 Qualified -> 430 Meeting -> 210 Proposal -> 95 Won
    * Referral converts best, Cold Calling worst, LinkedIn in the middle
    * FinTech / Healthcare convert slightly better
    * Bigger companies -> bigger deal values
    * More engagement (meetings, calls) -> higher conversion (activities are generated from stage reached)
    * Lead_Score is NOT included; it is calculated later in Python (data_cleaning_lead_scoring.py)

Run:  python generate_raw_data.py
"""

import os
import numpy as np
import pandas as pd
from datetime import date, timedelta

SEED = 33
rng = np.random.default_rng(SEED)

TODAY = date(2026, 9, 19)
START = date(2026, 1, 1)
END_CREATED = date(2026, 9, 15)
N_LEADS = 2000

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dataset")
os.makedirs(OUT_DIR, exist_ok=True)

# ----------------------------------------------------------------------------
# Master lists and weights
# ----------------------------------------------------------------------------
INDUSTRIES = {  # name: (share, quality effect)
    "FinTech": (14, 0.35), "Healthcare": (13, 0.25), "E-commerce": (15, 0.00),
    "Education": (9, -0.15), "Manufacturing": (12, -0.05), "Logistics": (9, -0.10),
    "Retail": (11, -0.05), "SaaS": (17, 0.10),
}
SOURCES = {  # name: (share, quality effect)
    "LinkedIn": (20, 0.25), "Website": (15, 0.00), "Email Campaign": (15, -0.10),
    "Cold Calling": (25, -0.35), "Referral": (10, 0.95), "Events": (8, 0.35),
    "Google Search": (7, 0.10),
}
LOCATIONS = {  # city: (share, region)
    "Mumbai": (18, "West"), "Bengaluru": (17, "South"), "Delhi": (15, "North"),
    "Hyderabad": (10, "South"), "Pune": (9, "West"), "Gurgaon": (8, "North"),
    "Chennai": (7, "South"), "Noida": (6, "North"), "Ahmedabad": (5, "West"),
    "Jaipur": (5, "North"),
}
SIZES = ["1-50", "51-200", "201-500", "501-1000", "1000+"]
SIZE_SHARE = [22, 30, 24, 14, 10]
SIZE_REVENUE_CR = {"1-50": (2, 15), "51-200": (10, 60), "201-500": (40, 200),
                   "501-1000": (150, 600), "1000+": (500, 3000)}
SIZE_DEAL_L = {"1-50": (1.5, 4), "51-200": (3, 8), "201-500": (6, 14),
               "501-1000": (10, 20), "1000+": (15, 25)}  # in lakh INR

SERVICES = ["Software Development", "Cloud Services", "Cybersecurity",
            "Digital Transformation", "DevOps"]
INDUSTRY_SERVICE_PREF = {
    "FinTech": [0.15, 0.25, 0.35, 0.15, 0.10],
    "Healthcare": [0.15, 0.20, 0.25, 0.35, 0.05],
    "E-commerce": [0.30, 0.30, 0.10, 0.15, 0.15],
    "Education": [0.25, 0.25, 0.10, 0.35, 0.05],
    "Manufacturing": [0.15, 0.15, 0.10, 0.50, 0.10],
    "Logistics": [0.25, 0.25, 0.10, 0.30, 0.10],
    "Retail": [0.25, 0.30, 0.10, 0.30, 0.05],
    "SaaS": [0.25, 0.25, 0.10, 0.10, 0.30],
}

# Funnel: highest stage reached by each lead
STAGE_COUNTS = [("Won", 95), ("Proposal", 115), ("Meeting", 220),
                ("Qualified", 420), ("Contacted", 550), ("New", 600)]

# Activity counts per stage: (calls, emails, meetings, website visits) as (min, max) inclusive
ACTIVITY_RANGES = {
    "New":       ((0, 0), (0, 0), (0, 0), (0, 2)),
    "Contacted": ((1, 2), (0, 1), (0, 0), (0, 2)),
    "Qualified": ((1, 3), (1, 2), (0, 0), (0, 3)),
    "Meeting":   ((2, 3), (1, 3), (1, 2), (1, 4)),
    "Proposal":  ((2, 4), (2, 4), (2, 3), (2, 5)),
    "Won":       ((3, 5), (3, 5), (2, 3), (3, 6)),
}

# Follow-up status probabilities per stage
FOLLOWUP_PROBS = {
    "New":       {"Follow-up Required": 1.0},
    "Contacted": {"Follow-up Required": .25, "Contacted": .25, "Waiting for Response": .30, "Not Interested": .20},
    "Qualified": {"Follow-up Required": .35, "Contacted": .15, "Waiting for Response": .25,
                  "Meeting Scheduled": .10, "Not Interested": .15},
    "Meeting":   {"Meeting Scheduled": .30, "Follow-up Required": .20, "Waiting for Response": .25,
                  "Contacted": .10, "Not Interested": .15},
    "Proposal":  {"Waiting for Response": .40, "Follow-up Required": .20, "Not Interested": .25, "Closed": .15},
    "Won":       {"Closed": 1.0},
}
PENDING_STATUSES = {"Follow-up Required", "Contacted", "Waiting for Response", "Meeting Scheduled"}

PREFIXES = """Nexora Zenith Aurora Vertex Quantum Apex Bluepeak Orbit Helix Pinnacle Sapphire Cobalt Evergreen Horizon
Lumina Meridian Novus Optima Paragon Radiant Solace Titan Unity Vanguard Wavelet Xenon Zephyr Alpine Banyan Cedar Delta
Ember Falcon Gravity Harbor Indus Jade Kestrel Lotus Mantra Neptune Onyx Prism Quartz Ridge Summit Tundra Umbra Vista
Willow Aryan Bharat Chakra Dhruv Ekam Garuda Himalaya Ishaan Kaveri Lakshya Madhav Narmada Prana Rudra Sagar Trident
Uday Vayu Yash Zeal Astra Bolt Crest Drift Echo Flux Glide Hive Ion Jolt Kinetic Loop Mosaic Nimbus Oasis Pulse Quest
Relay Spark Thrive Urban Vivid Wisp Yonder Zest""".split()
GENERIC_SUFFIX = ["Technologies", "Solutions", "Systems", "Labs", "Networks", "Group", "Softech", "Industries",
                  "Enterprises", "Global", "Pvt Ltd", "Ventures"]
INDUSTRY_SUFFIX = {
    "FinTech": ["Finserv", "Payments", "Capital Tech", "Wealth Tech"],
    "Healthcare": ["Health", "Diagnostics", "Care Systems", "MedTech"],
    "E-commerce": ["Commerce", "Marketplace", "Online", "Retail Tech"],
    "Education": ["Learning", "EdTech", "Academy Systems", "Knowledge"],
    "Manufacturing": ["Manufacturing", "Engineering", "Industrial", "Components"],
    "Logistics": ["Logistics", "Freight", "Supply Chain", "Cargo"],
    "Retail": ["Retail", "Stores", "Mart", "Brands"],
    "SaaS": ["Cloudware", "Software", "Platforms", "Apps"],
}

REPS = [  # id, name, region, joining date
    ("SR01", "Rahul Sharma", "North", "2021-04-12"),
    ("SR02", "Priya Mehta", "West", "2020-07-01"),
    ("SR03", "Amit Verma", "North", "2022-01-17"),
    ("SR04", "Sneha Iyer", "South", "2021-09-06"),
    ("SR05", "Vikram Singh", "North", "2019-11-25"),
    ("SR06", "Neha Kapoor", "West", "2023-02-13"),
    ("SR07", "Arjun Reddy", "South", "2022-06-20"),
    ("SR08", "Pooja Nair", "South", "2023-08-07"),
    ("SR09", "Rohan Gupta", "West", "2024-03-18"),
    ("SR10", "Ananya Das", "North", "2024-10-01"),
]


def weighted_choice(options, n, p=None):
    if p is None:
        p = np.ones(len(options))
    p = np.array(p, dtype=float)
    return rng.choice(options, size=n, p=p / p.sum())


def rand_date(lo: date, hi: date) -> date:
    return lo + timedelta(days=int(rng.integers(0, (hi - lo).days + 1)))


# ----------------------------------------------------------------------------
# 1. Base lead attributes
# ----------------------------------------------------------------------------
n_days = (END_CREATED - START).days + 1
day_weights = np.linspace(1.0, 1.6, n_days)  # pipeline building up through the year
created = [START + timedelta(days=int(d)) for d in weighted_choice(np.arange(n_days), N_LEADS, day_weights)]
created.sort()

industry = weighted_choice(list(INDUSTRIES), N_LEADS, [v[0] for v in INDUSTRIES.values()])
source = weighted_choice(list(SOURCES), N_LEADS, [v[0] for v in SOURCES.values()])
location = weighted_choice(list(LOCATIONS), N_LEADS, [v[0] for v in LOCATIONS.values()])
size = weighted_choice(SIZES, N_LEADS, SIZE_SHARE)
service = np.array([rng.choice(SERVICES, p=INDUSTRY_SERVICE_PREF[i]) for i in industry])

revenue = np.array([round(float(rng.uniform(*SIZE_REVENUE_CR[s])), 1) for s in size])

# unique company names
names, used = [], set()
while len(names) < N_LEADS:
    i = industry[len(names)]
    suffix = rng.choice(INDUSTRY_SUFFIX[i] + GENERIC_SUFFIX)
    nm = f"{rng.choice(PREFIXES)} {suffix}"
    if nm not in used:
        used.add(nm)
        names.append(nm)

# ----------------------------------------------------------------------------
# 2. Funnel stage via latent lead quality (guarantees exact funnel counts)
# ----------------------------------------------------------------------------
size_idx = np.array([SIZES.index(s) for s in size])
age_days = np.array([(TODAY - c).days for c in created])
age_penalty = np.where(age_days < 30, -1.5, np.where(age_days < 60, -0.7, 0.0))
quality = (np.array([SOURCES[s][1] for s in source])
           + np.array([INDUSTRIES[i][1] for i in industry])
           + 0.15 * size_idx + age_penalty
           + rng.normal(0, 1.4, N_LEADS))
order = np.argsort(-quality)
stage = np.empty(N_LEADS, dtype=object)
pos = 0
for st, cnt in STAGE_COUNTS:
    stage[order[pos:pos + cnt]] = st
    pos += cnt

# ----------------------------------------------------------------------------
# 3. Sales rep, follow-up status/date, deal value
# ----------------------------------------------------------------------------
reps_by_region = {}
for rid, _, reg, _ in REPS:
    reps_by_region.setdefault(reg, []).append(rid)
rep_id = np.array([rng.choice(reps_by_region[LOCATIONS[c][1]]) for c in location])

followup = np.array([rng.choice(list(FOLLOWUP_PROBS[s]), p=list(FOLLOWUP_PROBS[s].values())) for s in stage])

next_fu = []
for c, f in zip(created, followup):
    if f not in PENDING_STATUSES:
        next_fu.append(None)
        continue
    r = rng.random()
    if f == "Meeting Scheduled":
        d = TODAY + timedelta(days=int(rng.integers(0, 15)))
    elif r < 0.20:  # overdue
        lo = max(c + timedelta(days=1), TODAY - timedelta(days=20))
        d = lo + timedelta(days=int(rng.integers(0, (TODAY - timedelta(days=1) - lo).days + 1)))
    elif r < 0.30:  # due today
        d = TODAY
    else:  # upcoming
        d = TODAY + timedelta(days=int(rng.integers(1, 22)))
    next_fu.append(d)

deal_value = []
for s_, sz, sv in zip(stage, size, service):
    if s_ in ("Proposal", "Won"):
        lo, hi = SIZE_DEAL_L[sz]
        factor = {"Cybersecurity": 1.05, "Digital Transformation": 1.15, "Cloud Services": 1.0,
                  "Software Development": 1.1, "DevOps": 0.9}[sv]
        v = rng.uniform(lo, hi) * factor * 100000
        v = min(max(v, 150000), 2500000)  # keep within Rs 1.5L - Rs 25L
        deal_value.append(int(round(v / 5000) * 5000))
    else:
        deal_value.append(None)

leads = pd.DataFrame({
    "Lead_ID": [f"L{i + 1:04d}" for i in range(N_LEADS)],
    "Company_Name": names,
    "Industry": industry,
    "Company_Size": size,
    "Location": location,
    "Lead_Source": source,
    "Service_Interest": service,
    "Annual_Revenue_Cr": revenue,
    "Lead_Created_Date": [d.isoformat() for d in created],
    "Lead_Stage": stage,
    "Follow_Up_Status": followup,
    "Next_Follow_Up_Date": [d.isoformat() if d else None for d in next_fu],
    "Sales_Rep_ID": rep_id,
    "Deal_Value": deal_value,
    "Conversion": np.where(stage == "Won", "Yes", "No"),
})

# ----------------------------------------------------------------------------
# 4. Activities (calls, emails, meetings, website visits) generated from stage reached
# ----------------------------------------------------------------------------
OUTCOMES = {
    "Call": (["Connected", "No Answer", "Callback Requested", "Not Interested", "Voicemail"], [.40, .30, .15, .05, .10]),
    "Email": (["Opened", "Replied", "No Response", "Bounced"], [.35, .25, .35, .05]),
    "Meeting": (["Completed", "Rescheduled", "No Show"], [.80, .12, .08]),
    "Website Visit": (["Pricing Page", "Case Study", "Services Page", "Blog", "Contact Page"],
                      [.20, .20, .25, .20, .15]),
}
act_rows = []
for lid, c, st in zip(leads["Lead_ID"], created, stage):
    rngs = ACTIVITY_RANGES[st]
    counts = {t: int(rng.integers(lo, hi + 1)) for t, (lo, hi) in zip(["Call", "Email", "Meeting", "Website Visit"], rngs)}
    span = max(0, min((TODAY - c).days, 90))
    for atype, k in counts.items():
        opts, probs = OUTCOMES[atype]
        for _ in range(k):
            d = c + timedelta(days=int(rng.integers(0, span + 1)))
            act_rows.append((lid, atype, d, rng.choice(opts, p=probs)))

acts = pd.DataFrame(act_rows, columns=["Lead_ID", "Activity_Type", "Activity_Date", "Outcome"])
acts = acts.sort_values(["Activity_Date", "Lead_ID"]).reset_index(drop=True)
acts.insert(0, "Activity_ID", [f"A{i + 1:05d}" for i in range(len(acts))])
acts["Activity_Date"] = acts["Activity_Date"].apply(lambda d: d.isoformat())

reps_df = pd.DataFrame(REPS, columns=["Sales_Rep_ID", "Rep_Name", "Region", "Joining_Date"])

# ----------------------------------------------------------------------------
# 5. Make the RAW file messy on purpose
# ----------------------------------------------------------------------------
raw = leads.copy()


def messy_text(v):
    r = rng.random()
    return v.lower() if r < .35 else v.upper() if r < .65 else v + " " if r < .85 else " " + v


# inconsistent Industry / Lead_Source text (~8% / ~4%)
mask = rng.random(N_LEADS) < 0.08
raw.loc[mask, "Industry"] = raw.loc[mask, "Industry"].apply(messy_text)
mask = rng.random(N_LEADS) < 0.04
raw.loc[mask, "Lead_Source"] = raw.loc[mask, "Lead_Source"].apply(lambda v: v.lower() if rng.random() < .5 else v.upper())

# location aliases and stray spaces (~6%)
alias = {"Bengaluru": "Bangalore", "Gurgaon": "Gurugram", "Delhi": "New Delhi"}
mask = rng.random(N_LEADS) < 0.06
raw.loc[mask, "Location"] = raw.loc[mask, "Location"].apply(lambda v: alias.get(v, v + " "))

# stray spaces in company name (~3%)
mask = rng.random(N_LEADS) < 0.03
raw.loc[mask, "Company_Name"] = raw.loc[mask, "Company_Name"].apply(lambda v: v + " ")

# missing values: Location (~3%), Annual_Revenue_Cr (~4%)
raw.loc[rng.random(N_LEADS) < 0.03, "Location"] = None
raw.loc[rng.random(N_LEADS) < 0.04, "Annual_Revenue_Cr"] = np.nan

# date format errors (~2%): DD/MM/YYYY instead of YYYY-MM-DD
for col in ["Lead_Created_Date", "Next_Follow_Up_Date"]:
    m = (rng.random(N_LEADS) < 0.02) & raw[col].notna()
    raw.loc[m, col] = raw.loc[m, col].apply(lambda s: pd.Timestamp(s).strftime("%d/%m/%Y"))

# ~3% duplicate leads (same Lead_ID re-entered, some with messy formatting)
dups = raw.sample(n=int(N_LEADS * 0.03), random_state=SEED).copy()
half = rng.random(len(dups)) < 0.5
dups.loc[half, "Company_Name"] = dups.loc[half, "Company_Name"].str.upper()
raw = pd.concat([raw, dups], ignore_index=True)

# ----------------------------------------------------------------------------
# 6. Save + quick validation report
# ----------------------------------------------------------------------------
raw.to_csv(os.path.join(OUT_DIR, "raw_leads.csv"), index=False)
acts.to_csv(os.path.join(OUT_DIR, "sales_activities.csv"), index=False)
reps_df.to_csv(os.path.join(OUT_DIR, "sales_reps.csv"), index=False)

if __name__ == "__main__":
    print(f"raw_leads.csv        : {len(raw)} rows ({len(dups)} duplicates)")
    print(f"sales_activities.csv : {len(acts)} rows")
    print(f"sales_reps.csv       : {len(reps_df)} rows")
    order_ = ["New", "Contacted", "Qualified", "Meeting", "Proposal", "Won"]
    reached = [(leads["Lead_Stage"].map(order_.index) >= i).sum() for i in range(len(order_))]
    print("Funnel (reached stage):", dict(zip(order_, reached)))
    print("\nConversion by source (%):")
    print((leads.groupby("Lead_Source")["Conversion"].apply(lambda s: (s == "Yes").mean() * 100)).round(2).sort_values(ascending=False))
    print("\nConversion by industry (%):")
    print((leads.groupby("Industry")["Conversion"].apply(lambda s: (s == "Yes").mean() * 100)).round(2).sort_values(ascending=False))

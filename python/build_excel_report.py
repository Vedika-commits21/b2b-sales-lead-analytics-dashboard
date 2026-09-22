"""
build_excel_report.py
----------------------
Step 5: builds excel/lead_analysis.xlsx from dataset/cleaned_leads.csv and dataset/sales_reps.csv

Sheets created:
    Instructions      - how to use this file + how to add two native PivotTables
    Raw_Data           - full cleaned dataset as an Excel Table (source for PivotTables)
    Rep_Master         - sales rep lookup table
    Lookup_Analysis    - VLOOKUP, INDEX/MATCH and nested IF demo columns
    Source_Summary     - COUNTIFS/SUMIFS pivot-style table + bar chart
    Industry_Summary   - COUNTIFS/SUMIFS pivot-style table
    Location_Summary   - COUNTIFS/SUMIFS pivot-style table
    KPI_Dashboard      - KPI cards (formulas) + 2 charts
    Top_Hot_Leads      - snapshot of the 15 highest-scoring open leads

Run:  python build_excel_report.py
Then: python /mnt/skills/public/xlsx/scripts/recalc.py <output>.xlsx 90
"""

import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.formatting.rule import CellIsRule, FormulaRule, ColorScaleRule
from openpyxl.chart import BarChart, PieChart, Reference

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "..", "dataset")
OUT_DIR = os.path.join(BASE, "..", "excel")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_FILE = os.path.join(OUT_DIR, "lead_analysis.xlsx")

FONT_NAME = "Arial"
NAVY = "1F3864"
BLUE = "2E5395"
LIGHT_BLUE = "DDEBF7"
GREY = "F2F2F2"
GREEN = "C6EFCE"
RED = "FFC7CE"
YELLOW = "FFEB9C"

HEADER_FILL = PatternFill("solid", fgColor=NAVY)
HEADER_FONT = Font(name=FONT_NAME, bold=True, color="FFFFFF", size=10)
TITLE_FONT = Font(name=FONT_NAME, bold=True, size=16, color=NAVY)
SUBTITLE_FONT = Font(name=FONT_NAME, italic=True, size=10, color="555555")
LABEL_FONT = Font(name=FONT_NAME, bold=True, size=10)
BODY_FONT = Font(name=FONT_NAME, size=10)
KPI_FONT = Font(name=FONT_NAME, bold=True, size=20, color=NAVY)
KPI_LABEL_FONT = Font(name=FONT_NAME, size=10, color="555555")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

# ----------------------------------------------------------------------------
# Load data
# ----------------------------------------------------------------------------
leads = pd.read_csv(os.path.join(DATA_DIR, "cleaned_leads.csv"))
reps = pd.read_csv(os.path.join(DATA_DIR, "sales_reps.csv"))
N = len(leads)  # 2000
LAST_ROW = N + 1  # header is row 1

INDUSTRIES = sorted(leads["Industry"].unique())
SOURCES = sorted(leads["Lead_Source"].unique())
LOCATIONS = sorted(leads["Location"].unique())

wb = Workbook()
wb.remove(wb.active)


def style_header(ws, row, n_cols, start_col=1):
    for c in range(start_col, start_col + n_cols):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BOX


def autosize(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def title_block(ws, title, subtitle, span=8):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=span)
    ws["A1"] = title
    ws["A1"].font = TITLE_FONT
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=span)
    ws["A2"] = subtitle
    ws["A2"].font = SUBTITLE_FONT
    ws.row_dimensions[1].height = 26
    ws.row_dimensions[3].height = 6


# ----------------------------------------------------------------------------
# Sheet 1: Instructions
# ----------------------------------------------------------------------------
ws = wb.create_sheet("Instructions")
title_block(ws, "B2B Sales Lead Analytics — Excel Workbook", "How this workbook is organised and how to use it")
rows = [
    ("Raw_Data", "The full cleaned dataset (2,000 leads, one row per lead) as an Excel Table. "
                 "This is the single source of truth every other sheet reads from."),
    ("Rep_Master", "Sales rep lookup table (10 reps) used by VLOOKUP / INDEX-MATCH in Lookup_Analysis."),
    ("Lookup_Analysis", "Demonstrates VLOOKUP, INDEX/MATCH and nested IF: pulls each lead's rep name and "
                        "region, and flags a follow-up priority."),
    ("Source_Summary", "COUNTIFS/SUMIFS pivot-style table: leads, qualified, won and conversion % by Lead_Source, "
                       "plus a bar chart."),
    ("Industry_Summary", "Same breakdown by Industry."),
    ("Location_Summary", "Same breakdown by Location (city)."),
    ("KPI_Dashboard", "Headline KPI cards and two charts (Lead Category split, Leads by Source)."),
    ("Top_Hot_Leads", "The 15 highest-scoring OPEN leads — a ready-made call list for the sales team."),
]
r = 4
ws.cell(row=r, column=1, value="Sheet").font = LABEL_FONT
ws.cell(row=r, column=2, value="What it contains").font = LABEL_FONT
style_header(ws, r, 2)
r += 1
for name, desc in rows:
    ws.cell(row=r, column=1, value=name).font = BODY_FONT
    ws.cell(row=r, column=2, value=desc).font = BODY_FONT
    ws.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[r].height = 30
    r += 1

r += 1
ws.cell(row=r, column=1, value="Add two real native PivotTables (recommended for the resume / interview)").font = LABEL_FONT
r += 1
tips = [
    "1. Click any cell inside the Raw_Data table.",
    "2. Insert tab -> PivotTable -> New Worksheet.",
    "3. Pivot 1 'Funnel by Stage': Rows = Lead_Stage, Values = Count of Lead_ID and Sum of Deal_Value.",
    "4. Pivot 2 'Score vs Conversion': Rows = Lead_Category, Values = Count of Lead_ID and "
    "Average of Lead_Score (right-click a value -> Value Field Settings -> Average).",
    "5. Rename the two new sheets 'Pivot_Funnel' and 'Pivot_ScoreVsConversion'.",
    "This workbook already reproduces both breakdowns with SUMIFS/COUNTIFS formulas in the "
    "Summary sheets, so a native PivotTable here is extra polish, not a requirement.",
]
for t in tips:
    ws.cell(row=r, column=1, value=t).font = BODY_FONT
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    r += 1

autosize(ws, [4, 100])
ws.sheet_view.showGridLines = False

# ----------------------------------------------------------------------------
# Sheet 2: Raw_Data
# ----------------------------------------------------------------------------
ws = wb.create_sheet("Raw_Data")
cols = list(leads.columns)
ws.append(cols)
for row in leads.itertuples(index=False, name=None):
    ws.append([None if pd.isna(v) else v for v in row])
style_header(ws, 1, len(cols))
ws.freeze_panes = "A2"

tbl = Table(displayName="RawLeads", ref=f"A1:{get_column_letter(len(cols))}{LAST_ROW}")
tbl.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
ws.add_table(tbl)

widths = {"Lead_ID": 9, "Company_Name": 24, "Industry": 14, "Company_Size": 12, "Location": 11,
          "Lead_Source": 14, "Service_Interest": 20, "Lead_Created_Date": 12, "Lead_Stage": 11,
          "Follow_Up_Status": 18, "Next_Follow_Up_Date": 12, "Follow_Up_Flag": 16, "Deal_Value": 12,
          "Last_Contact_Date": 12, "Lead_Category": 11}
autosize(ws, [widths.get(c, 12) for c in cols])

col_idx = {name: i + 1 for i, name in enumerate(cols)}


def col(name):
    return get_column_letter(col_idx[name])


rng = lambda name: f"Raw_Data!${col(name)}$2:${col(name)}${LAST_ROW}"

# Conditional formatting on Raw_Data
cat_col = col("Lead_Category")
ws.conditional_formatting.add(
    f"{cat_col}2:{cat_col}{LAST_ROW}",
    CellIsRule(operator="equal", formula=['"Hot"'], fill=PatternFill("solid", fgColor=RED)))
ws.conditional_formatting.add(
    f"{cat_col}2:{cat_col}{LAST_ROW}",
    CellIsRule(operator="equal", formula=['"Warm"'], fill=PatternFill("solid", fgColor=YELLOW)))
ws.conditional_formatting.add(
    f"{cat_col}2:{cat_col}{LAST_ROW}",
    CellIsRule(operator="equal", formula=['"Cold"'], fill=PatternFill("solid", fgColor=LIGHT_BLUE)))

score_col = col("Lead_Score")
ws.conditional_formatting.add(
    f"{score_col}2:{score_col}{LAST_ROW}",
    ColorScaleRule(start_type="min", start_color="FFC7CE", mid_type="percentile", mid_value=50, mid_color="FFEB9C",
                   end_type="max", end_color="C6EFCE"))

flag_col = col("Follow_Up_Flag")
ws.conditional_formatting.add(
    f"{flag_col}2:{flag_col}{LAST_ROW}",
    CellIsRule(operator="equal", formula=['"Overdue"'], fill=PatternFill("solid", fgColor=RED)))

# ----------------------------------------------------------------------------
# Sheet 3: Rep_Master
# ----------------------------------------------------------------------------
ws = wb.create_sheet("Rep_Master")
ws.append(list(reps.columns))
for row in reps.itertuples(index=False, name=None):
    ws.append(list(row))
style_header(ws, 1, len(reps.columns))
rtbl = Table(displayName="RepMaster", ref=f"A1:D{len(reps) + 1}")
rtbl.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
ws.add_table(rtbl)
autosize(ws, [12, 18, 10, 14])

# ----------------------------------------------------------------------------
# Sheet 4: Lookup_Analysis (VLOOKUP, INDEX/MATCH, nested IF)
# ----------------------------------------------------------------------------
ws = wb.create_sheet("Lookup_Analysis")
title_block(ws, "Lookup & Priority Analysis", "VLOOKUP + INDEX/MATCH pull the rep; a nested IF sets follow-up priority", span=9)
headers = ["Lead_ID", "Company_Name", "Industry", "Lead_Score", "Lead_Category",
           "Follow_Up_Flag", "Sales_Rep_ID", "Rep_Name (VLOOKUP)", "Rep_Region (INDEX/MATCH)", "Follow_Up_Priority (IF)"]
hdr_row = 4
for i, h in enumerate(headers, start=1):
    ws.cell(row=hdr_row, column=i, value=h)
style_header(ws, hdr_row, len(headers))
ws.freeze_panes = f"A{hdr_row + 1}"

src = {n: col(n) for n in ["Lead_ID", "Company_Name", "Industry", "Lead_Score", "Lead_Category",
                           "Follow_Up_Flag", "Sales_Rep_ID"]}
for i in range(N):
    r = hdr_row + 1 + i
    src_r = i + 2
    ws.cell(row=r, column=1, value=f"=Raw_Data!{src['Lead_ID']}{src_r}")
    ws.cell(row=r, column=2, value=f"=Raw_Data!{src['Company_Name']}{src_r}")
    ws.cell(row=r, column=3, value=f"=Raw_Data!{src['Industry']}{src_r}")
    ws.cell(row=r, column=4, value=f"=Raw_Data!{src['Lead_Score']}{src_r}")
    ws.cell(row=r, column=5, value=f"=Raw_Data!{src['Lead_Category']}{src_r}")
    ws.cell(row=r, column=6, value=f"=Raw_Data!{src['Follow_Up_Flag']}{src_r}")
    ws.cell(row=r, column=7, value=f"=Raw_Data!{src['Sales_Rep_ID']}{src_r}")
    # VLOOKUP: rep name from Rep_Master using the Sales_Rep_ID in this row
    ws.cell(row=r, column=8, value=f"=VLOOKUP(G{r},Rep_Master!$A$2:$D${len(reps) + 1},2,FALSE)")
    # INDEX/MATCH: region, same lookup done a second way
    ws.cell(row=r, column=9, value=f"=INDEX(Rep_Master!$C$2:$C${len(reps) + 1},MATCH(G{r},Rep_Master!$A$2:$A${len(reps) + 1},0))")
    # Nested IF: Hot+Overdue/Due Today -> urgent; Hot otherwise -> monitor; else based on flag
    ws.cell(row=r, column=10,
            value=(f'=IF(E{r}="Hot",IF(OR(F{r}="Overdue",F{r}="Due Today"),"Urgent - Call Today","Monitor Closely"),'
                   f'IF(F{r}="Overdue","Follow Up Soon","Normal"))'))

autosize(ws, [9, 24, 14, 11, 12, 14, 12, 20, 20, 22])

# Conditional formatting for the priority column
pr_col = "J"
ws.conditional_formatting.add(
    f"{pr_col}{hdr_row + 1}:{pr_col}{hdr_row + N}",
    CellIsRule(operator="equal", formula=['"Urgent - Call Today"'], fill=PatternFill("solid", fgColor=RED)))
ws.conditional_formatting.add(
    f"{pr_col}{hdr_row + 1}:{pr_col}{hdr_row + N}",
    CellIsRule(operator="equal", formula=['"Follow Up Soon"'], fill=PatternFill("solid", fgColor=YELLOW)))

# ----------------------------------------------------------------------------
# Helper to build a COUNTIFS/SUMIFS "pivot-style" summary sheet
# ----------------------------------------------------------------------------
def build_summary_sheet(sheet_name, dim_col_name, dim_values, title, subtitle):
    ws = wb.create_sheet(sheet_name)
    title_block(ws, title, subtitle, span=7)
    headers = [dim_col_name.replace("_", " "), "Total Leads", "Qualified (Stage>=3)", "Won Deals",
               "Conversion %", "Won Revenue (Rs)", "Avg Lead Score"]
    hdr_row = 4
    for i, h in enumerate(headers, start=1):
        ws.cell(row=hdr_row, column=i, value=h)
    style_header(ws, hdr_row, len(headers))

    dim_rng = rng(dim_col_name)
    stage_rng = rng("Stage_Order")
    conv_rng = rng("Conversion")
    deal_rng = rng("Deal_Value")
    score_rng = rng("Lead_Score")

    first_data_row = hdr_row + 1
    for i, val in enumerate(dim_values):
        r = first_data_row + i
        ws.cell(row=r, column=1, value=val)
        ws.cell(row=r, column=2, value=f'=COUNTIFS({dim_rng},$A{r})')
        ws.cell(row=r, column=3, value=f'=COUNTIFS({dim_rng},$A{r},{stage_rng},">=3")')
        ws.cell(row=r, column=4, value=f'=COUNTIFS({dim_rng},$A{r},{conv_rng},"Yes")')
        ws.cell(row=r, column=5, value=f'=IFERROR(D{r}/B{r},0)')
        ws.cell(row=r, column=6, value=f'=SUMIFS({deal_rng},{dim_rng},$A{r},{conv_rng},"Yes")')
        ws.cell(row=r, column=7, value=f'=IFERROR(AVERAGEIFS({score_rng},{dim_rng},$A{r}),0)')
        ws.cell(row=r, column=5).number_format = "0.0%"
        ws.cell(row=r, column=6).number_format = '#,##0'
        ws.cell(row=r, column=7).number_format = "0.0"
        for c in range(1, 8):
            ws.cell(row=r, column=c).border = BOX
            ws.cell(row=r, column=c).font = BODY_FONT

    total_row = first_data_row + len(dim_values)
    ws.cell(row=total_row, column=1, value="TOTAL").font = LABEL_FONT
    ws.cell(row=total_row, column=2, value=f"=SUM(B{first_data_row}:B{total_row - 1})")
    ws.cell(row=total_row, column=3, value=f"=SUM(C{first_data_row}:C{total_row - 1})")
    ws.cell(row=total_row, column=4, value=f"=SUM(D{first_data_row}:D{total_row - 1})")
    ws.cell(row=total_row, column=5, value=f"=IFERROR(D{total_row}/B{total_row},0)")
    ws.cell(row=total_row, column=5).number_format = "0.0%"
    ws.cell(row=total_row, column=6, value=f"=SUM(F{first_data_row}:F{total_row - 1})")
    ws.cell(row=total_row, column=6).number_format = '#,##0'
    ws.cell(row=total_row, column=7, value=f"=IFERROR(AVERAGEIFS({score_rng},{dim_rng},\"<>\"),0)")
    ws.cell(row=total_row, column=7).number_format = "0.0"
    for c in range(1, 8):
        ws.cell(row=total_row, column=c).border = Border(top=Side(style="double"))
        ws.cell(row=total_row, column=c).font = LABEL_FONT

    autosize(ws, [18, 12, 18, 11, 13, 17, 13])
    return ws, first_data_row, total_row - 1, hdr_row


ws_src, src_first, src_last, src_hdr = build_summary_sheet(
    "Source_Summary", "Lead_Source", SOURCES,
    "Lead Source Performance", "Which lead generation channels produce better-quality leads?")

ws_ind, ind_first, ind_last, ind_hdr = build_summary_sheet(
    "Industry_Summary", "Industry", INDUSTRIES,
    "Industry Performance", "Which industries should sales focus on?")

ws_loc, loc_first, loc_last, loc_hdr = build_summary_sheet(
    "Location_Summary", "Location", LOCATIONS,
    "Location Performance", "Which cities generate the most leads and revenue?")

# Bar chart on Source_Summary: Total Leads by source
chart = BarChart()
chart.title = "Total Leads by Source"
chart.y_axis.title = "Leads"
chart.x_axis.title = "Lead Source"
chart.style = 10
data = Reference(ws_src, min_col=2, min_row=src_hdr, max_row=src_last)
cats = Reference(ws_src, min_col=1, min_row=src_first, max_row=src_last)
chart.add_data(data, titles_from_data=True)
chart.set_categories(cats)
chart.width, chart.height = 16, 9
ws_src.add_chart(chart, f"A{src_last + 3}")

# ----------------------------------------------------------------------------
# Sheet: KPI_Dashboard
# ----------------------------------------------------------------------------
ws = wb.create_sheet("KPI_Dashboard")
title_block(ws, "B2B Sales — KPI Dashboard", "All cards are formulas and update automatically if Raw_Data changes", span=8)
ws.sheet_view.showGridLines = False

conv_r = rng("Conversion")
deal_r = rng("Deal_Value")
stage_r = rng("Stage_Order")
outcome_r = rng("Deal_Outcome")
leadstage_r = rng("Lead_Stage")
cat_r = rng("Lead_Category")
flag_r = rng("Follow_Up_Flag")

kpis = [
    ("Total Leads", f'=COUNTA({rng("Lead_ID")})', "0"),
    ("Qualified Leads", f'=COUNTIFS({stage_r},">=3")', "0"),
    ("Won Deals", f'=COUNTIFS({conv_r},"Yes")', "0"),
    ("Conversion Rate", f'=COUNTIFS({conv_r},"Yes")/COUNTA({rng("Lead_ID")})', "0.0%"),
    ("Won Revenue (Rs)", f'=SUMIFS({deal_r},{conv_r},"Yes")', "#,##0"),
    ("Open Pipeline (Rs)", f'=SUMIFS({deal_r},{outcome_r},"Open",{leadstage_r},"Proposal")', "#,##0"),
    ("Hot Leads", f'=COUNTIFS({cat_r},"Hot")', "0"),
    ("Overdue Follow-ups", f'=COUNTIFS({flag_r},"Overdue")', "0"),
]
card_w, gap, start_col, start_row = 11, 1, 1, 4
for i, (label, formula, fmt) in enumerate(kpis):
    row = start_row + (i // 4) * 4
    c = start_col + (i % 4) * (card_w + gap)
    ws.merge_cells(start_row=row, start_column=c, end_row=row, end_column=c + card_w - 1)
    cell = ws.cell(row=row, column=c, value=label)
    cell.font = KPI_LABEL_FONT
    ws.merge_cells(start_row=row + 1, start_column=c, end_row=row + 2, end_column=c + card_w - 1)
    vcell = ws.cell(row=row + 1, column=c, value=formula)
    vcell.font = KPI_FONT
    vcell.number_format = fmt
    for rr in (row, row + 1, row + 2):
        for cc in range(c, c + card_w):
            ws.cell(row=rr, column=cc).fill = PatternFill("solid", fgColor=GREY)
    ws.cell(row=row, column=c).border = Border(top=THIN, left=THIN, right=THIN)
    ws.cell(row=row + 2, column=c).border = Border(bottom=THIN, left=THIN, right=THIN)
    ws.cell(row=row + 1, column=c).border = Border(left=THIN, right=THIN)

autosize(ws, [11] * 40)
for i in range(1, 40):
    ws.column_dimensions[get_column_letter(i)].width = 11

# small helper table for the Lead_Category pie chart
helper_row = 14
ws.cell(row=helper_row, column=1, value="Lead_Category").font = LABEL_FONT
ws.cell(row=helper_row, column=2, value="Leads").font = LABEL_FONT
for i, cat in enumerate(["Hot", "Warm", "Cold"]):
    ws.cell(row=helper_row + 1 + i, column=1, value=cat)
    ws.cell(row=helper_row + 1 + i, column=2, value=f'=COUNTIFS({cat_r},"{cat}")')

pie = PieChart()
pie.title = "Lead Category Split (Hot / Warm / Cold)"
data = Reference(ws, min_col=2, min_row=helper_row, max_row=helper_row + 3)
cats = Reference(ws, min_col=1, min_row=helper_row + 1, max_row=helper_row + 3)
pie.add_data(data, titles_from_data=True)
pie.set_categories(cats)
pie.width, pie.height = 12, 8
ws.add_chart(pie, "A19")

bar2 = BarChart()
bar2.title = "Total Leads by Industry"
bar2.y_axis.title = "Leads"
data = Reference(ws_ind, min_col=2, min_row=ind_hdr, max_row=ind_last)
cats = Reference(ws_ind, min_col=1, min_row=ind_first, max_row=ind_last)
bar2.add_data(data, titles_from_data=True)
bar2.set_categories(cats)
bar2.width, bar2.height = 16, 8
ws.add_chart(bar2, "H19")

# ----------------------------------------------------------------------------
# Sheet: Top_Hot_Leads (snapshot — refresh by re-running the pipeline, or rebuild as a PivotTable)
# ----------------------------------------------------------------------------
ws = wb.create_sheet("Top_Hot_Leads")
title_block(ws, "Top 15 Open Leads to Call This Week", "Snapshot sorted by Lead_Score — refresh after re-running the Python pipeline", span=8)
cols_top = ["Lead_ID", "Company_Name", "Industry", "Lead_Source", "Lead_Stage", "Lead_Score", "Lead_Category",
           "Follow_Up_Status", "Next_Follow_Up_Date", "Sales_Rep_ID"]
top = (leads[leads["Deal_Outcome"] == "Open"]
       .merge(reps[["Sales_Rep_ID", "Rep_Name"]], on="Sales_Rep_ID")
       .sort_values("Lead_Score", ascending=False)
       .head(15))
hdr_row = 4
for i, h in enumerate(cols_top[:-1] + ["Rep_Name"], start=1):
    ws.cell(row=hdr_row, column=i, value=h.replace("_", " "))
style_header(ws, hdr_row, len(cols_top))
for i, row in enumerate(top.itertuples(index=False), start=1):
    d = row._asdict() if hasattr(row, "_asdict") else dict(zip(top.columns, row))
    r = hdr_row + i
    vals = [d["Lead_ID"], d["Company_Name"], d["Industry"], d["Lead_Source"], d["Lead_Stage"], d["Lead_Score"],
            d["Lead_Category"], d["Follow_Up_Status"], d["Next_Follow_Up_Date"], d["Rep_Name"]]
    for c, v in enumerate(vals, start=1):
        cell = ws.cell(row=r, column=c, value=(None if pd.isna(v) else v))
        cell.border = BOX
        cell.font = BODY_FONT
autosize(ws, [9, 24, 14, 14, 11, 11, 12, 18, 15, 18])
ws.conditional_formatting.add(
    f"G{hdr_row + 1}:G{hdr_row + len(top)}",
    CellIsRule(operator="equal", formula=['"Hot"'], fill=PatternFill("solid", fgColor=RED)))

wb.move_sheet("Instructions", offset=-len(wb.sheetnames))
wb.save(OUT_FILE)
print(f"Saved {OUT_FILE}")
print("Sheets:", wb.sheetnames)

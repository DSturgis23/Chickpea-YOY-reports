"""
app.py — Overview / home page
"""
import streamlit as st

st.set_page_config(
    page_title="Chickpea — Overview",
    page_icon="📊",
    layout="wide",
)

from utils import (
    inject_css, render_sidebar, load_data, page_header, sec, note,
    gbp, pct, delta_pct, kpi_html, month_iter, apply_style,
    grouped_bar, line_chart, donut_chart,
    BRAND_GREEN, BRAND_LIGHT, DRINKS_CLR, FOOD_CLR, GOOD, WARN, BAD,
)
import plotly.graph_objects as go

inject_css()
ty_from, ty_to, ly_from, ly_to = render_sidebar()
d = load_data(ty_from, ty_to, ly_from, ly_to)
ty_ev = d["ty_ev"]; ly_ev = d["ly_ev"]
ty_sr = d["ty_sr"]; ly_sr = d["ly_sr"]
ty_wd = d["ty_wd"]; ly_wd = d["ly_wd"]
net = st.session_state.get("show_net", False)

page_header(
    "Annual Performance — Overview",
    f"TY: {ty_from.strftime('%d %b %Y')} – {ty_to.strftime('%d %b %Y')}",
    f"LY: {ly_from.strftime('%d %b %Y')} – {ly_to.strftime('%d %b %Y')}",
)

# ── KPI row 1 ─────────────────────────────────────────────────────────────────
rev_ty = ty_ev["revenue"] or 0;  rev_ly = ly_ev["revenue"] or 0
fb_ty  = ty_wd["total"]  or 0;   fb_ly  = ly_wd["total"]  or 0
cov_ty = ty_sr["covers"] or 0;   cov_ly = ly_sr["covers"] or 0
ug_ty  = ty_sr["unique_guests"] or 0; ug_ly = ly_sr["unique_guests"] or 0

c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_html(f"Room Revenue {'(Net)' if net else '(Gross)'}",
    gbp(rev_ty, net=net), f"LY {gbp(rev_ly, net=net)}", delta_pct(rev_ty, rev_ly)), unsafe_allow_html=True)
c2.markdown(kpi_html(f"F&B Sales {'(Net)' if net else '(Gross)'}",
    gbp(fb_ty, net=net) if fb_ty else "Upload →",
    f"LY {gbp(fb_ly, net=net)}" if fb_ly else "",
    delta_pct(fb_ty, fb_ly) if fb_ty and fb_ly else None), unsafe_allow_html=True)
c3.markdown(kpi_html("F&B Covers (SevenRooms)",
    f"{cov_ty:,}", f"LY {cov_ly:,}", delta_pct(cov_ty, cov_ly)), unsafe_allow_html=True)
c4.markdown(kpi_html("Unique Guests",
    f"{ug_ty:,}", f"LY {ug_ly:,}", delta_pct(ug_ty, ug_ly)), unsafe_allow_html=True)

st.markdown("&nbsp;", unsafe_allow_html=True)

# ── KPI row 2 ─────────────────────────────────────────────────────────────────
occ_ty = ty_ev["occ"]; occ_ly = ly_ev["occ"]
adr_ty = ty_ev["adr"]; adr_ly = ly_ev["adr"]
rp_ty  = ty_ev["revpar"]; rp_ly = ly_ev["revpar"]
stays_ty = ty_ev["stays"] or 0; stays_ly = ly_ev["stays"] or 0

c5, c6, c7, c8 = st.columns(4)
c5.markdown(kpi_html("Occupancy",
    f"{occ_ty*100:.1f}%" if occ_ty else "—",
    f"LY {occ_ly*100:.1f}%" if occ_ly else "—",
    delta_pct(occ_ty or 0, occ_ly or 0) if occ_ty and occ_ly else None), unsafe_allow_html=True)
c6.markdown(kpi_html("ADR",
    gbp(adr_ty, 2, net=net) if adr_ty else "—",
    f"LY {gbp(adr_ly, 2, net=net)}" if adr_ly else "—",
    delta_pct(adr_ty or 0, adr_ly or 0) if adr_ty and adr_ly else None), unsafe_allow_html=True)
c7.markdown(kpi_html("RevPAR",
    gbp(rp_ty, 2, net=net) if rp_ty else "—",
    f"LY {gbp(rp_ly, 2, net=net)}" if rp_ly else "—",
    delta_pct(rp_ty or 0, rp_ly or 0) if rp_ty and rp_ly else None), unsafe_allow_html=True)
c8.markdown(kpi_html("Confirmed Stays",
    f"{stays_ty:,}", f"LY {stays_ly:,}", delta_pct(stays_ty, stays_ly)), unsafe_allow_html=True)

# ── Trend chart + mix donut ───────────────────────────────────────────────────
sec("Monthly Revenue Trend")
months_list  = month_iter(ty_from, ty_to)
month_labels = [m.strftime("%b %y") for m in months_list]

ty_rev_m = [(ty_ev["by_month"].get(m.strftime("%Y-%m"), {}).get("revenue") or 0) for m in months_list]
ly_rev_m = [(ly_ev["by_month"].get(m.replace(year=m.year-1).strftime("%Y-%m"), {}).get("revenue") or 0) for m in months_list]

if d["has_fb"]:
    ty_fb_m = [(ty_wd["by_month"].get(m.strftime("%Y-%m"), {}).get("total") or 0) for m in months_list]
    ly_fb_m = [(ly_wd["by_month"].get(m.replace(year=m.year-1).strftime("%Y-%m"), {}).get("total") or 0) for m in months_list]
    ty_comb_m = [r+f for r, f in zip(ty_rev_m, ty_fb_m)]
    ly_comb_m = [r+f for r, f in zip(ly_rev_m, ly_fb_m)]
else:
    ty_comb_m = ty_rev_m; ly_comb_m = ly_rev_m

col_chart, col_donut = st.columns([3, 1])
with col_chart:
    st.plotly_chart(line_chart(month_labels, ty_comb_m, ly_comb_m, height=320), use_container_width=True)
with col_donut:
    if d["has_fb"] and rev_ty:
        st.plotly_chart(donut_chart(
            ["Rooms", "Drinks", "Food"],
            [rev_ty, ty_wd["wet"] or 0, ty_wd["dry"] or 0],
            colors=[BRAND_GREEN, DRINKS_CLR, FOOD_CLR],
            center_text="Revenue<br>Mix", height=320,
        ), use_container_width=True)
    elif rev_ty:
        st.caption("Upload F&B data for revenue mix chart.")

# ── Summary table ─────────────────────────────────────────────────────────────
sec("Key Metrics at a Glance")
import pandas as pd

def row(label, ty_v, ly_v, fmt):
    chg = delta_pct(ty_v, ly_v) if ty_v is not None and ly_v else None
    return {"Metric": label,
            "Last Year": fmt(ly_v) if ly_v is not None else "—",
            "This Year": fmt(ty_v) if ty_v is not None else "—",
            "YOY": pct(chg) if chg is not None else "—"}

_r = lambda v: gbp(v, net=net) if v else "—"
_a = lambda v: gbp(v, 2, net=net) if v else "—"
_o = lambda v: f"{v*100:.1f}%" if v else "—"
_n = lambda v: f"{v:,.0f}" if v else "—"
_p = lambda v: f"{v*100:.1f}%" if v else "—"

rows = [
    row("Room Revenue", rev_ty, rev_ly, _r),
    row("Confirmed Stays", stays_ty, stays_ly, _n),
    row("Occupancy", occ_ty, occ_ly, _o),
    row("ADR", adr_ty, adr_ly, _a),
    row("RevPAR", rp_ty, rp_ly, _a),
    row("F&B Covers", cov_ty, cov_ly, _n),
    row("Unique Guests", ug_ty, ug_ly, _n),
    row("Repeat Visit Rate", ty_sr.get("repeat_rate"), ly_sr.get("repeat_rate"), _p),
]
if d["has_fb"]:
    rows += [
        row("F&B Total", fb_ty, fb_ly, _r),
        row("Wet (Drinks)", ty_wd["wet"], ly_wd["wet"], _r),
        row("Dry (Food)", ty_wd["dry"], ly_wd["dry"], _r),
    ]

st.dataframe(apply_style(pd.DataFrame(rows), chg=["YOY"]),
             use_container_width=True, hide_index=True)

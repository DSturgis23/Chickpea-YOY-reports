import streamlit as st
st.set_page_config(page_title="Chickpea — Phone", page_icon="📞", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils import (
    inject_css, render_sidebar, page_header, sec,
    kpi_html, gauge_chart,
    BRAND_GREEN, GOOD, WARN, BAD,
)
from config import PHONE_TARGET

inject_css()
render_sidebar()

page_header("Phone Performance", f"Target: below {PHONE_TARGET*100:.0f}% missed calls", "Last 90 days")

PHONE_STATS = [
    {"name": "Fleur de Lys",     "total": 1095, "missed": 272, "avg_wait": "0:14"},
    {"name": "Kings Arms",        "total": 633,  "missed": 249, "avg_wait": "0:17"},
    {"name": "Bell & Crown",      "total": 1149, "missed": 399, "avg_wait": "0:20"},
    {"name": "Bar Bell & Crown",  "total": 8,    "missed": 2,   "avg_wait": "0:14"},
    {"name": "Silver Plough",     "total": 843,  "missed": 325, "avg_wait": "0:15"},
    {"name": "Pembroke",          "total": 2181, "missed": 850, "avg_wait": "0:17"},
    {"name": "Pizza Pembroke",    "total": 607,  "missed": 361, "avg_wait": "0:20"},
    {"name": "George & Dragon",   "total": 64,   "missed": 51,  "avg_wait": "0:07"},
    {"name": "Queens Head",       "total": 514,  "missed": 200, "avg_wait": "0:12"},
    {"name": "Pizza Queens Head", "total": 28,   "missed": 5,   "avg_wait": "0:12"},
    {"name": "Grosvenor",         "total": 1391, "missed": 484, "avg_wait": "0:14"},
    {"name": "Pizza Dog & Gun",   "total": 859,  "missed": 176, "avg_wait": "0:16"},
    {"name": "Bar Manor House",   "total": 1316, "missed": 503, "avg_wait": "0:16"},
    {"name": "Office Accounts",   "total": 227,  "missed": 56,  "avg_wait": "0:09"},
    {"name": "Kirstie Macey",     "total": 299,  "missed": 181, "avg_wait": "0:08"},
]

grp_t = grp_m = 0
prows = []
for row in PHONE_STATS:
    t = row["total"]; m = row["missed"]
    if t == 0: continue
    mp = m / t; vs = mp - PHONE_TARGET
    status = "✅ On target" if mp < PHONE_TARGET else ("🚨 Critical" if mp >= 0.40 else "⚠️ Above target")
    prows.append({
        "Line":      row["name"], "Total": f"{t:,}", "Answered": f"{t-m:,}",
        "Missed": f"{m:,}", "Missed %": f"{mp*100:.0f}%",
        "Target": f"{PHONE_TARGET*100:.0f}%", "vs Target": f"{vs*100:+.0f}%pts",
        "Avg Wait": row.get("avg_wait","—"), "Status": status,
    })
    grp_t += t; grp_m += m

gp      = grp_m / grp_t if grp_t else 0
on_tgt  = sum(1 for r in prows if "On target" in r["Status"])

card_cls = "" if gp < PHONE_TARGET else ("warn" if gp < PHONE_TARGET*2 else "danger")
c1, c2, c3 = st.columns(3)
c1.markdown(kpi_html("Group Missed Call Rate", f"{gp*100:.0f}%", f"Target: {PHONE_TARGET*100:.0f}%",
    (gp - PHONE_TARGET) / PHONE_TARGET, inverse=True, card_class=card_cls), unsafe_allow_html=True)
c2.markdown(kpi_html("Lines On Target", f"{on_tgt} / {len(prows)}", f"Below {PHONE_TARGET*100:.0f}% threshold", None), unsafe_allow_html=True)
c3.markdown(kpi_html("Total Calls", f"{grp_t:,}", f"{grp_m:,} missed", None), unsafe_allow_html=True)

sec("Missed Call Rate by Line")
col_g, col_b = st.columns([1, 2])
with col_g:
    st.plotly_chart(gauge_chart(gp, PHONE_TARGET, title="Group Missed Rate", height=250), use_container_width=True)
with col_b:
    names    = [r["Line"] for r in prows]
    mp_vals  = [int(r["Missed %"].replace("%","")) for r in prows]
    bar_clrs = [GOOD if v < PHONE_TARGET*100 else (WARN if v < 40 else BAD) for v in mp_vals]
    fig_ph   = go.Figure(go.Bar(
        x=mp_vals, y=names, orientation="h", marker_color=bar_clrs,
        text=[f"{v}%" for v in mp_vals], textposition="outside", textfont_size=10,
    ))
    fig_ph.add_vline(x=PHONE_TARGET*100, line_dash="dash", line_color=BRAND_GREEN,
                     annotation_text=f"Target {PHONE_TARGET*100:.0f}%", annotation_font_size=10)
    fig_ph.update_layout(
        height=max(320, len(names)*34+70), showlegend=False,
        xaxis_ticksuffix="%", xaxis_title="Missed %",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="system-ui, sans-serif", size=11),
        margin=dict(t=30, b=28, l=8, r=80),
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(showgrid=False),
    )
    fig_ph.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(fig_ph, use_container_width=True)

prows.append({
    "Line":"GROUP TOTAL","Total":f"{grp_t:,}","Answered":f"{grp_t-grp_m:,}",
    "Missed":f"{grp_m:,}","Missed %":f"{gp*100:.0f}%",
    "Target":f"{PHONE_TARGET*100:.0f}%","vs Target":f"{(gp-PHONE_TARGET)*100:+.0f}%pts",
    "Avg Wait":"—","Status":"✅ On target" if gp < PHONE_TARGET else "⚠️ Above target",
})

sec("Detail")
st.dataframe(pd.DataFrame(prows), use_container_width=True, hide_index=True)
st.caption("✅ On target = below 15%.  ⚠️ Above target = 15–39%.  🚨 Critical = 40%+.  "
           "George & Dragon is low volume and not directly comparable.")

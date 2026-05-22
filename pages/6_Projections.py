import streamlit as st
st.set_page_config(page_title="Chickpea — Projections", page_icon="🔮", layout="wide")

import calendar
import pandas as pd
from datetime import date
from utils import (
    inject_css, render_sidebar, load_data, page_header, sec, note, good,
    gbp, pct, delta_pct, kpi_html, month_iter, grouped_bar,
    BRAND_GREEN, BRAND_LIGHT,
)
from config import EVIIVO_PROPERTIES, ROOM_COUNTS

inject_css()
ty_from, ty_to, ly_from, ly_to = render_sidebar()
d = load_data(ty_from, ty_to, ly_from, ly_to)
ty_ev = d["ty_ev"]
net = st.session_state.get("show_net", False)

page_header("Room Revenue Projections — FY 2026–27",
            f"Based on TY actuals ({ty_from.strftime('%b %Y')} – {ty_to.strftime('%b %Y')})",
            "Occupancy held flat · ADR +5%")

good("<b>Methodology:</b> Occupancy is held at this year's actual rate per property. "
     "ADR is uplifted +5% to reflect expected rate growth. "
     "RevPAR = occupancy × projected ADR. Revenue = RevPAR × rooms × days per month.")

proj_months = month_iter(date(2026, 8, 1), date(2027, 7, 31))
proj_rows, proj_total = [], 0.0
proj_names, proj_vals, ty_vals = [], [], []

for prop in sorted(EVIIVO_PROPERTIES.keys()):
    ty_p   = ty_ev["by_property"].get(prop, {})
    ty_occ = ty_p.get("occ") or 0.0
    ty_adr = ty_p.get("adr") or 0.0
    rooms  = ROOM_COUNTS.get(prop, 0)
    if ty_occ == 0 or ty_adr == 0: continue

    proj_adr    = ty_adr * 1.05
    proj_revpar = ty_occ * proj_adr
    proj_rev    = sum(
        proj_revpar * rooms * calendar.monthrange(m.year, m.month)[1]
        for m in proj_months
    )
    proj_total += proj_rev
    ty_rev_act  = ty_p.get("revenue") or 0

    proj_names.append(prop); proj_vals.append(proj_rev); ty_vals.append(ty_rev_act)
    proj_rows.append({
        "Property":       prop,
        "Rooms":          rooms,
        "TY Occ":         f"{ty_occ*100:.1f}%",
        "TY ADR":         gbp(ty_adr, 2),
        "Proj ADR (+5%)": gbp(proj_adr, 2),
        "Proj RevPAR":    gbp(proj_revpar, 2),
        "Proj Revenue":   gbp(proj_rev, net=net),
        "TY Actual Rev":  gbp(ty_rev_act, net=net) if ty_rev_act else "—",
    })

if not proj_rows:
    st.info("No actuals available yet to build projections — load data first.")
    st.stop()

proj_rows.append({
    "Property":"GROUP TOTAL","Rooms":"—","TY Occ":"—",
    "TY ADR":"—","Proj ADR (+5%)":"—","Proj RevPAR":"—",
    "Proj Revenue": gbp(proj_total, net=net), "TY Actual Rev":"—",
})

rev_ty = ty_ev["revenue"] or 0
c1, c2, c3 = st.columns(3)
c1.markdown(kpi_html(
    f"Projected FY2026-27 Revenue {'(Net)' if net else '(Gross)'}",
    gbp(proj_total, net=net), f"TY Actual {gbp(rev_ty, net=net)}", delta_pct(proj_total, rev_ty),
), unsafe_allow_html=True)
c2.markdown(kpi_html("ADR Uplift Applied", "+5%", "On top of TY actuals", None), unsafe_allow_html=True)
c3.markdown(kpi_html("Occupancy Assumption", "TY actual", "Held flat into FY26-27", None), unsafe_allow_html=True)

sec("TY Actual vs FY2026-27 Projected by Property")
st.plotly_chart(grouped_bar(proj_names, proj_vals, ty_vals, height=400,
                            ty_name="Projected FY26-27", ly_name="TY Actual"),
                use_container_width=True)

sec("Projection Detail")
st.dataframe(pd.DataFrame(proj_rows), use_container_width=True, hide_index=True)

note("Projections are indicative only and subject to trading conditions. Properties that traded "
     "for a partial year may have skewed occupancy rates. The Dog &amp; Gun January occupancy "
     "reflects a partial closure and may be revised upward for FY2026-27.")

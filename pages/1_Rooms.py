import streamlit as st
st.set_page_config(page_title="Chickpea — Rooms", page_icon="🛏", layout="wide")

import pandas as pd
from utils import (
    inject_css, render_sidebar, load_data, page_header, sec, note,
    gbp, pct, delta_pct, kpi_html, month_iter, apply_style,
    grouped_bar, hbar_chart, BRAND_GREEN, BRAND_LIGHT,
)
from config import EVIIVO_PROPERTIES, ROOM_COUNTS

inject_css()
ty_from, ty_to, ly_from, ly_to = render_sidebar()
d = load_data(ty_from, ty_to, ly_from, ly_to)
ty_ev = d["ty_ev"]; ly_ev = d["ly_ev"]
net = st.session_state.get("show_net", False)

page_header("Rooms", f"TY {ty_from.strftime('%b %Y')} – {ty_to.strftime('%b %Y')}",
            f"LY {ly_from.strftime('%b %Y')} – {ly_to.strftime('%b %Y')}")

rev_ty = ty_ev["revenue"] or 0; rev_ly = ly_ev["revenue"] or 0
occ_ty = ty_ev["occ"];           occ_ly = ly_ev["occ"]
adr_ty = ty_ev["adr"];           adr_ly = ly_ev["adr"]
rp_ty  = ty_ev["revpar"];        rp_ly  = ly_ev["revpar"]

c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_html(f"Revenue {'(Net)' if net else '(Gross)'}",
    gbp(rev_ty, net=net), f"LY {gbp(rev_ly, net=net)}", delta_pct(rev_ty, rev_ly)), unsafe_allow_html=True)
c2.markdown(kpi_html("Occupancy",
    f"{occ_ty*100:.1f}%" if occ_ty else "—",
    f"LY {occ_ty*100:.1f}%" if occ_ty else "—",
    delta_pct(occ_ty or 0, occ_ly or 0) if occ_ty and occ_ly else None), unsafe_allow_html=True)
c3.markdown(kpi_html("ADR",
    gbp(adr_ty, 2, net=net) if adr_ty else "—",
    f"LY {gbp(adr_ly, 2, net=net)}" if adr_ly else "—",
    delta_pct(adr_ty or 0, adr_ly or 0) if adr_ty and adr_ly else None), unsafe_allow_html=True)
c4.markdown(kpi_html("RevPAR",
    gbp(rp_ty, 2, net=net) if rp_ty else "—",
    f"LY {gbp(rp_ly, 2, net=net)}" if rp_ly else "—",
    delta_pct(rp_ty or 0, rp_ly or 0) if rp_ty and rp_ly else None), unsafe_allow_html=True)

months_list  = month_iter(ty_from, ty_to)
month_labels = [m.strftime("%b %y") for m in months_list]

def lyk(m): return m.replace(year=m.year-1).strftime("%Y-%m")

ty_rev_m = [(ty_ev["by_month"].get(m.strftime("%Y-%m"), {}).get("revenue") or 0) for m in months_list]
ly_rev_m = [(ly_ev["by_month"].get(lyk(m), {}).get("revenue") or 0) for m in months_list]
ty_occ_m = [(ty_ev["by_month"].get(m.strftime("%Y-%m"), {}).get("occ") or 0)*100 for m in months_list]
ly_occ_m = [(ly_ev["by_month"].get(lyk(m), {}).get("occ") or 0)*100 for m in months_list]

sec("Monthly Revenue — This Year vs Last Year")
t1, t2 = st.tabs(["Revenue", "Occupancy %"])
with t1:
    st.plotly_chart(grouped_bar(month_labels, ty_rev_m, ly_rev_m, height=380), use_container_width=True)
with t2:
    fig = grouped_bar(month_labels, ty_occ_m, ly_occ_m, prefix="", height=380)
    fig.update_layout(yaxis_ticksuffix="%", yaxis_tickprefix="")
    st.plotly_chart(fig, use_container_width=True)

sec("Revenue by Property")
props = sorted(EVIIVO_PROPERTIES.keys())
ty_pr = [ty_ev["by_property"].get(p, {}).get("revenue") or 0 for p in props]
ly_pr = [ly_ev["by_property"].get(p, {}).get("revenue") or 0 for p in props]

cl, cr = st.columns(2)
with cl:
    st.caption("This Year")
    st.plotly_chart(hbar_chart(props, ty_pr, height=320), use_container_width=True)
with cr:
    st.caption("Last Year")
    st.plotly_chart(hbar_chart(props, ly_pr, height=320, colors=[BRAND_LIGHT]*len(props)), use_container_width=True)

sec("Month-by-Month Detail")
rows = []
for m in months_list:
    k_ty = m.strftime("%Y-%m"); k_ly = lyk(m)
    ty_m = ty_ev["by_month"].get(k_ty, {}); ly_m = ly_ev["by_month"].get(k_ly, {})
    g = lambda d, k: d.get(k) or 0
    ty_r = g(ty_m,"revenue"); ly_r = g(ly_m,"revenue")
    rows.append({
        "Month":     m.strftime("%b %Y"),
        "LY Rev":    gbp(ly_r, net=net),
        "TY Rev":    gbp(ty_r, net=net),
        "YOY Rev":   pct(delta_pct(ty_r, ly_r)) if ly_r else "—",
        "LY Stays":  f"{g(ly_m,'stays'):,}",
        "TY Stays":  f"{g(ty_m,'stays'):,}",
        "LY ADR":    gbp(g(ly_m,'adr'), 2, net=net) if g(ly_m,'adr') else "—",
        "TY ADR":    gbp(g(ty_m,'adr'), 2, net=net) if g(ty_m,'adr') else "—",
        "LY Occ":    f"{g(ly_m,'occ')*100:.1f}%" if ly_m.get('occ') else "—",
        "TY Occ":    f"{g(ty_m,'occ')*100:.1f}%" if ty_m.get('occ') else "—",
        "LY RevPAR": gbp(g(ly_m,'revpar'), 2, net=net) if ly_m.get('revpar') else "—",
        "TY RevPAR": gbp(g(ty_m,'revpar'), 2, net=net) if ty_m.get('revpar') else "—",
    })
st.dataframe(apply_style(pd.DataFrame(rows), chg=["YOY Rev"]), use_container_width=True, hide_index=True)

sec("By Property")
prows = []
for p in props:
    ty_p = ty_ev["by_property"].get(p, {}); ly_p = ly_ev["by_property"].get(p, {})
    g = lambda d, k: d.get(k) or 0
    ty_r = g(ty_p,"revenue"); ly_r = g(ly_p,"revenue")
    prows.append({
        "Property":  p,
        "Rooms":     ROOM_COUNTS.get(p, "—"),
        "LY Rev":    gbp(ly_r, net=net),
        "TY Rev":    gbp(ty_r, net=net),
        "YOY":       pct(delta_pct(ty_r, ly_r)) if ly_r else "—",
        "LY Stays":  f"{g(ly_p,'stays'):,}",
        "TY Stays":  f"{g(ty_p,'stays'):,}",
        "LY ADR":    gbp(g(ly_p,'adr'), 2, net=net) if g(ly_p,'adr') else "—",
        "TY ADR":    gbp(g(ty_p,'adr'), 2, net=net) if g(ty_p,'adr') else "—",
        "LY Occ":    f"{g(ly_p,'occ')*100:.1f}%" if ly_p.get('occ') else "—",
        "TY Occ":    f"{g(ty_p,'occ')*100:.1f}%" if ty_p.get('occ') else "—",
        "LY RevPAR": gbp(g(ly_p,'revpar'), 2, net=net) if ly_p.get('revpar') else "—",
        "TY RevPAR": gbp(g(ty_p,'revpar'), 2, net=net) if ty_p.get('revpar') else "—",
    })
st.dataframe(apply_style(pd.DataFrame(prows), chg=["YOY"]), use_container_width=True, hide_index=True)

note("The Fleur de Lys opened late Sep 2025 and Manor House Inn joined Eviivo in Feb 2025 — "
     "their YOY comparisons reflect new trading periods. The Queen's Head expanded from 4 to "
     "9 rooms in March 2026. Year-on-year room revenue is significantly up in part because of "
     "these new/expanded properties.")

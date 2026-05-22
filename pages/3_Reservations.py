import streamlit as st
st.set_page_config(page_title="Chickpea — Reservations", page_icon="🪑", layout="wide")

import pandas as pd
from utils import (
    inject_css, render_sidebar, load_data, page_header, sec, note,
    gbp, pct, delta_pct, kpi_html, month_iter, apply_style,
    grouped_bar, donut_chart, BRAND_GREEN,
)

inject_css()
ty_from, ty_to, ly_from, ly_to = render_sidebar()
d = load_data(ty_from, ty_to, ly_from, ly_to)
ty_sr = d["ty_sr"]; ly_sr = d["ly_sr"]

page_header("Reservations (SevenRooms)", f"TY {ty_from.strftime('%b %Y')} – {ty_to.strftime('%b %Y')}",
            f"LY {ly_from.strftime('%b %Y')} – {ly_to.strftime('%b %Y')}")

def lyk(m): return m.replace(year=m.year-1).strftime("%Y-%m")

res_ty = ty_sr["reservations"] or 0; res_ly = ly_sr["reservations"] or 0
cov_ty = ty_sr["covers"] or 0;       cov_ly = ly_sr["covers"] or 0
ug_ty  = ty_sr["unique_guests"] or 0; ug_ly  = ly_sr["unique_guests"] or 0
rr_ty  = ty_sr["repeat_rate"] or 0;   rr_ly  = ly_sr["repeat_rate"] or 0

c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_html("Reservations", f"{res_ty:,}", f"LY {res_ly:,}", delta_pct(res_ty, res_ly)), unsafe_allow_html=True)
c2.markdown(kpi_html("Covers", f"{cov_ty:,}", f"LY {cov_ly:,}", delta_pct(cov_ty, cov_ly)), unsafe_allow_html=True)
c3.markdown(kpi_html("Unique Guests", f"{ug_ty:,}", f"LY {ug_ly:,}", delta_pct(ug_ty, ug_ly)), unsafe_allow_html=True)
c4.markdown(kpi_html("Repeat Visit Rate", f"{rr_ty*100:.1f}%", f"LY {rr_ly*100:.1f}%", delta_pct(rr_ty, rr_ly)), unsafe_allow_html=True)

note("SevenRooms records reservation covers only — walk-ins not logged in the system are excluded. "
     "Prior-year data includes a ResDiary migration export which may have inflated LY cover counts. "
     "FY2026-27 will be the first clean like-for-like year.")

months_list  = month_iter(ty_from, ty_to)
month_labels = [m.strftime("%b %y") for m in months_list]
ty_cov_m = [(ty_sr["by_month"].get(m.strftime("%Y-%m"), {}).get("covers") or 0) for m in months_list]
ly_cov_m = [(ly_sr["by_month"].get(lyk(m), {}).get("covers") or 0) for m in months_list]

sec("Monthly Covers — This Year vs Last Year")
col_cv, col_fd = st.columns([3, 1])
with col_cv:
    st.plotly_chart(grouped_bar(month_labels, ty_cov_m, ly_cov_m, prefix="", height=360), use_container_width=True)
with col_fd:
    fd = ty_sr.get("freq_dist") or {}
    if any(fd.values()):
        st.plotly_chart(donut_chart(
            list(fd.keys()), list(fd.values()),
            colors=[BRAND_GREEN, "#4a9060", "#90b890", "#c8dfc8"],
            center_text="Guest<br>Frequency", height=360,
        ), use_container_width=True)

sec("By Venue")
all_sv  = sorted(set(list(ty_sr["by_venue"]) + list(ly_sr["by_venue"])))
srows   = []
for v in all_sv:
    ty_v = ty_sr["by_venue"].get(v, {}); ly_v = ly_sr["by_venue"].get(v, {})
    g = lambda d, k: d.get(k) or 0
    ty_c = g(ty_v,"covers"); ly_c = g(ly_v,"covers")
    srows.append({
        "Venue":         v,
        "LY Res":        f"{g(ly_v,'reservations'):,}",
        "TY Res":        f"{g(ty_v,'reservations'):,}",
        "LY Covers":     f"{ly_c:,}",
        "TY Covers":     f"{ty_c:,}",
        "YOY Covers":    pct(delta_pct(ty_c, ly_c)) if ly_c else "—",
        "TY Avg Party":  f"{g(ty_v,'avg_covers'):.1f}",
        "LY Avg Party":  f"{g(ly_v,'avg_covers'):.1f}",
        "TY Repeat %":   f"{g(ty_v,'repeat_rate')*100:.0f}%",
    })
st.dataframe(apply_style(pd.DataFrame(srows), chg=["YOY Covers"]), use_container_width=True, hide_index=True)

sec("Monthly Detail")
mrows = []
for m in months_list:
    k_ty = m.strftime("%Y-%m"); k_ly = lyk(m)
    ty_m = ty_sr["by_month"].get(k_ty, {}); ly_m = ly_sr["by_month"].get(k_ly, {})
    g = lambda d, k: d.get(k) or 0
    ty_c = g(ty_m,"covers"); ly_c = g(ly_m,"covers")
    mrows.append({
        "Month":    m.strftime("%b %Y"),
        "LY Res":   f"{g(ly_m,'reservations'):,}",
        "TY Res":   f"{g(ty_m,'reservations'):,}",
        "LY Covers":f"{ly_c:,}",
        "TY Covers":f"{ty_c:,}",
        "YOY":      pct(delta_pct(ty_c, ly_c)) if ly_c else "—",
        "Avg Party":f"{g(ty_m,'avg_covers'):.1f}",
    })
st.dataframe(apply_style(pd.DataFrame(mrows), chg=["YOY"]), use_container_width=True, hide_index=True)

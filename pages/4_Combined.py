import streamlit as st
st.set_page_config(page_title="Chickpea — Combined", page_icon="🔗", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils import (
    inject_css, render_sidebar, load_data, page_header, sec,
    gbp, pct, delta_pct, kpi_html, apply_style,
    BRAND_GREEN, DRINKS_CLR, FOOD_CLR,
)
from config import ROOMS_AND_FB

inject_css()
ty_from, ty_to, ly_from, ly_to = render_sidebar()
d = load_data(ty_from, ty_to, ly_from, ly_to)
ty_ev = d["ty_ev"]; ly_ev = d["ly_ev"]
ty_wd = d["ty_wd"]; ly_wd = d["ly_wd"]
net = st.session_state.get("show_net", False)

page_header("Combined Revenue — Rooms & F&B", f"TY {ty_from.strftime('%b %Y')} – {ty_to.strftime('%b %Y')}",
            f"LY {ly_from.strftime('%b %Y')} – {ly_to.strftime('%b %Y')}")

if not d["has_fb"]:
    st.info("Upload WEEKLY SALES & MARGINS.xlsx in the sidebar to see combined data.")
    st.stop()

rev_ty = ty_ev["revenue"] or 0; rev_ly = ly_ev["revenue"] or 0
fb_ty  = ty_wd["total"]  or 0;  fb_ly  = ly_wd["total"]  or 0
ty_comb = rev_ty + fb_ty;       ly_comb = rev_ly + fb_ly

c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_html(f"Combined Revenue {'(Net)' if net else '(Gross)'}",
    gbp(ty_comb, net=net), f"LY {gbp(ly_comb, net=net)}", delta_pct(ty_comb, ly_comb)), unsafe_allow_html=True)
c2.markdown(kpi_html("Rooms Share",
    f"{rev_ty/ty_comb*100:.0f}%" if ty_comb else "—", "", None), unsafe_allow_html=True)
c3.markdown(kpi_html("F&B Share",
    f"{fb_ty/ty_comb*100:.0f}%" if ty_comb else "—", "", None), unsafe_allow_html=True)
nights = ty_ev.get("nights") or 1
c4.markdown(kpi_html("Total Rev per Room Night",
    gbp(ty_comb / nights, 2, net=net), "", None), unsafe_allow_html=True)

sec("Revenue Split by Property — Rooms, Drinks & Food")
venue_list = sorted(ROOMS_AND_FB)
stk_rooms = [ty_ev["by_property"].get(v, {}).get("revenue") or 0 for v in venue_list]
stk_wet   = [ty_wd["by_venue"].get(v, {}).get("wet") or 0 for v in venue_list]
stk_dry   = [ty_wd["by_venue"].get(v, {}).get("dry") or 0 for v in venue_list]

fig = go.Figure()
fig.add_bar(name="Rooms",  x=venue_list, y=stk_rooms, marker_color=BRAND_GREEN,
            text=[f"£{v:,.0f}" for v in stk_rooms], textposition="inside", textfont_size=8)
fig.add_bar(name="Drinks", x=venue_list, y=stk_wet,   marker_color=DRINKS_CLR,
            text=[f"£{v:,.0f}" for v in stk_wet],   textposition="inside", textfont_size=8)
fig.add_bar(name="Food",   x=venue_list, y=stk_dry,   marker_color=FOOD_CLR,
            text=[f"£{v:,.0f}" for v in stk_dry],   textposition="inside", textfont_size=8)
fig.update_layout(barmode="stack", height=420, yaxis_tickprefix="£", yaxis_tickformat=",.0f",
                  plot_bgcolor="white", paper_bgcolor="white",
                  font=dict(family="system-ui, sans-serif", size=11),
                  margin=dict(t=44, b=28, l=8, r=8),
                  legend=dict(orientation="h", y=1.1, x=0))
st.plotly_chart(fig, use_container_width=True)

sec("By Property")
prop_rows = []
for v in venue_list:
    ty_r  = ty_ev["by_property"].get(v, {}).get("revenue") or 0
    ly_r  = ly_ev["by_property"].get(v, {}).get("revenue") or 0
    ty_w  = ty_wd["by_venue"].get(v, {}).get("wet") or 0
    ty_dr = ty_wd["by_venue"].get(v, {}).get("dry") or 0
    ly_fb = ly_wd["by_venue"].get(v, {}).get("total") or 0
    ty_t  = ty_r + ty_w + ty_dr; ly_t = ly_r + ly_fb
    prop_rows.append({
        "Property": v,
        "TY Rooms": gbp(ty_r, net=net),
        "TY Drinks":gbp(ty_w, net=net),
        "TY Food":  gbp(ty_dr, net=net),
        "TY Total": gbp(ty_t, net=net),
        "Rooms %":  f"{ty_r/ty_t*100:.0f}%" if ty_t else "—",
        "F&B %":    f"{(ty_w+ty_dr)/ty_t*100:.0f}%" if ty_t else "—",
        "LY Total": gbp(ly_t, net=net),
        "YOY":      pct(delta_pct(ty_t, ly_t)) if ly_t else "—",
    })
st.dataframe(apply_style(pd.DataFrame(prop_rows), chg=["YOY"]), use_container_width=True, hide_index=True)

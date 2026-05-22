import streamlit as st
st.set_page_config(page_title="Chickpea — F&B Sales", page_icon="🍽", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils import (
    inject_css, render_sidebar, load_data, page_header, sec, note,
    gbp, pct, delta_pct, kpi_html, month_iter, apply_style,
    grouped_bar, hbar_chart, stacked_bar,
    BRAND_GREEN, BRAND_LIGHT, DRINKS_CLR, FOOD_CLR,
)

inject_css()
ty_from, ty_to, ly_from, ly_to = render_sidebar()
d = load_data(ty_from, ty_to, ly_from, ly_to)
ty_wd = d["ty_wd"]; ly_wd = d["ly_wd"]
net = st.session_state.get("show_net", False)

page_header("F&B Sales — Wet & Dry", f"TY {ty_from.strftime('%b %Y')} – {ty_to.strftime('%b %Y')}",
            f"LY {ly_from.strftime('%b %Y')} – {ly_to.strftime('%b %Y')}")

if not d["has_fb"]:
    st.info("Upload your WEEKLY SALES & MARGINS.xlsx in the sidebar to see F&B data.")
    st.stop()

fb_ty = ty_wd["total"]; fb_ly = ly_wd["total"] or 0
wet_ty = ty_wd["wet"];  wet_ly = ly_wd["wet"] or 0
dry_ty = ty_wd["dry"];  dry_ly = ly_wd["dry"] or 0

c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_html(f"Total F&B {'(Net)' if net else '(Gross)'}",
    gbp(fb_ty, net=net), f"LY {gbp(fb_ly, net=net)}", delta_pct(fb_ty, fb_ly)), unsafe_allow_html=True)
c2.markdown(kpi_html("Wet (Drinks)", gbp(wet_ty, net=net), f"LY {gbp(wet_ly, net=net)}",
    delta_pct(wet_ty, wet_ly)), unsafe_allow_html=True)
c3.markdown(kpi_html("Dry (Food)", gbp(dry_ty, net=net), f"LY {gbp(dry_ly, net=net)}",
    delta_pct(dry_ty, dry_ly)), unsafe_allow_html=True)
c4.markdown(kpi_html("Wet / Dry Split",
    f"{ty_wd['wet_pct']*100:.0f}% / {ty_wd['dry_pct']*100:.0f}%",
    f"LY {ly_wd['wet_pct']*100:.0f}% / {ly_wd['dry_pct']*100:.0f}%", None), unsafe_allow_html=True)

months_list  = month_iter(ty_from, ty_to)
month_labels = [m.strftime("%b %y") for m in months_list]
def lyk(m): return m.replace(year=m.year-1).strftime("%Y-%m")

ty_wet_m = [(ty_wd["by_month"].get(m.strftime("%Y-%m"), {}).get("wet") or 0) for m in months_list]
ty_dry_m = [(ty_wd["by_month"].get(m.strftime("%Y-%m"), {}).get("dry") or 0) for m in months_list]
ty_tot_m = [(ty_wd["by_month"].get(m.strftime("%Y-%m"), {}).get("total") or 0) for m in months_list]
ly_tot_m = [(ly_wd["by_month"].get(lyk(m), {}).get("total") or 0) for m in months_list]

sec("Monthly F&B Revenue")
t1, t2, t3 = st.tabs(["Wet + Dry Stack (TY)", "TY vs LY Total", "Wet % Trend"])
with t1:
    st.plotly_chart(stacked_bar(month_labels, ty_wet_m, ty_dry_m, height=400), use_container_width=True)
with t2:
    st.plotly_chart(grouped_bar(month_labels, ty_tot_m, ly_tot_m, height=400), use_container_width=True)
with t3:
    ty_wp_m = [(ty_wd["by_month"].get(m.strftime("%Y-%m"), {}).get("wet_pct") or 0)*100 for m in months_list]
    fig = go.Figure()
    fig.add_scatter(x=month_labels, y=ty_wp_m, name="Wet %",
                    fill="tozeroy", line=dict(color=DRINKS_CLR, width=2.5), marker=dict(size=6))
    fig.add_hline(y=ty_wd["wet_pct"]*100, line_dash="dot", line_color=BRAND_GREEN,
                  annotation_text=f"Avg {ty_wd['wet_pct']*100:.0f}%")
    fig.update_layout(height=380, yaxis_ticksuffix="%",
                      plot_bgcolor="white", paper_bgcolor="white",
                      font=dict(family="system-ui, sans-serif"),
                      margin=dict(t=40, b=28, l=8, r=8),
                      xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#f0f0f0"))
    st.plotly_chart(fig, use_container_width=True)

sec("Revenue by Venue")
all_venues = sorted(set(list(ty_wd["by_venue"]) + list(ly_wd["by_venue"])))
v_ty = [ty_wd["by_venue"].get(v, {}).get("total") or 0 for v in all_venues]
v_ly = [ly_wd["by_venue"].get(v, {}).get("total") or 0 for v in all_venues]

cl, cr = st.columns(2)
with cl:
    st.caption("This Year")
    st.plotly_chart(hbar_chart(all_venues, v_ty, height=len(all_venues)*40+80), use_container_width=True)
with cr:
    st.caption("Last Year")
    st.plotly_chart(hbar_chart(all_venues, v_ly, height=len(all_venues)*40+80,
                               colors=[BRAND_LIGHT]*len(all_venues)), use_container_width=True)

sec("Venue Detail")
vrows = []
for v in all_venues:
    ty_v = ty_wd["by_venue"].get(v, {}); ly_v = ly_wd["by_venue"].get(v, {})
    g = lambda d, k: d.get(k) or 0.0
    ty_t = g(ty_v,"total"); ly_t = g(ly_v,"total")
    vrows.append({
        "Venue":    v,
        "LY Wet":   gbp(g(ly_v,"wet"), net=net),
        "LY Dry":   gbp(g(ly_v,"dry"), net=net),
        "LY Total": gbp(ly_t, net=net),
        "TY Wet":   gbp(g(ty_v,"wet"), net=net),
        "TY Dry":   gbp(g(ty_v,"dry"), net=net),
        "TY Total": gbp(ty_t, net=net),
        "Mix":      f"{g(ty_v,'wet_pct')*100:.0f}%W / {(1-g(ty_v,'wet_pct'))*100:.0f}%D" if ty_t else "—",
        "YOY":      pct(delta_pct(ty_t, ly_t)) if ly_t else "—",
    })
st.dataframe(apply_style(pd.DataFrame(vrows), chg=["YOY"]), use_container_width=True, hide_index=True)

sec("Month Detail")
frows = []
for m in months_list:
    k_ty = m.strftime("%Y-%m"); k_ly = lyk(m)
    ty_m = ty_wd["by_month"].get(k_ty, {}); ly_m = ly_wd["by_month"].get(k_ly, {})
    g = lambda d, k: d.get(k) or 0.0
    ty_t = g(ty_m,"total"); ly_t = g(ly_m,"total")
    frows.append({
        "Month":    m.strftime("%b %Y"),
        "LY Total": gbp(ly_t, net=net),
        "TY Total": gbp(ty_t, net=net),
        "YOY":      pct(delta_pct(ty_t, ly_t)) if ly_t else "—",
        "TY Wet":   gbp(g(ty_m,"wet"), net=net),
        "TY Dry":   gbp(g(ty_m,"dry"), net=net),
        "Mix":      f"{g(ty_m,'wet_pct')*100:.0f}%W" if ty_t else "—",
    })
st.dataframe(apply_style(pd.DataFrame(frows), chg=["YOY"]), use_container_width=True, hide_index=True)

note("Fleur de Lys opened late Sep 2025, Manor House Inn Feb 2025, Kings Arms Nov 2024 — "
     "YOY comparisons for these venues reflect new openings. Like-for-like growth "
     "(Bell &amp; Crown, Grosvenor Arms, Pembroke Arms, Silver Plough) is shown on the Analytics page.")

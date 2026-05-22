import streamlit as st
st.set_page_config(page_title="Chickpea — Analytics", page_icon="📈", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils import (
    inject_css, render_sidebar, load_data, page_header, sec, note,
    gbp, pct, delta_pct, kpi_html, month_iter, apply_style,
    BRAND_GREEN, BRAND_LIGHT, GOLD, GOOD, WARN, BAD,
)

inject_css()
ty_from, ty_to, ly_from, ly_to = render_sidebar()
d = load_data(ty_from, ty_to, ly_from, ly_to)
ty_ev = d["ty_ev"]; ly_ev = d["ly_ev"]
ty_wd = d["ty_wd"]; ly_wd = d["ly_wd"]
net = st.session_state.get("show_net", False)

page_header("Analytics", f"TY {ty_from.strftime('%b %Y')} – {ty_to.strftime('%b %Y')}",
            f"LY {ly_from.strftime('%b %Y')} – {ly_to.strftime('%b %Y')}")

rev_ty = ty_ev["revenue"] or 0; rev_ly = ly_ev["revenue"] or 0

# ── Growth decomposition ──────────────────────────────────────────────────────
sec("Revenue Growth Decomposition")
if d["has_fb"]:
    streams = {
        "Rooms":        (rev_ty,          rev_ly),
        "Drinks (Wet)": (ty_wd["wet"],    ly_wd["wet"]),
        "Food (Dry)":   (ty_wd["dry"],    ly_wd["dry"]),
    }
    total_delta = sum(t - l for t, l in streams.values())
    wf_labels, wf_deltas, gd_rows = [], [], []
    for label, (ty_v, ly_v) in streams.items():
        delta_v = ty_v - ly_v
        share = delta_v / total_delta * 100 if total_delta else 0
        gd_rows.append({
            "Stream": label,
            "LY": gbp(ly_v, net=net), "TY": gbp(ty_v, net=net),
            "Change": ("+" if delta_v >= 0 else "") + gbp(abs(delta_v)),
            "YOY": pct(delta_pct(ty_v, ly_v)) if ly_v else "—",
            "Share of Growth": f"{share:+.0f}%",
        })
        wf_labels.append(label); wf_deltas.append(delta_v)

    col_wf, col_tbl = st.columns([2, 3])
    with col_wf:
        fig_wf = go.Figure(go.Waterfall(
            orientation="v", measure=["relative"]*3,
            x=wf_labels, y=wf_deltas,
            connector=dict(line=dict(color="#ccc", width=1)),
            increasing=dict(marker_color=BRAND_GREEN),
            decreasing=dict(marker_color=BAD),
            text=[f"£{abs(v):,.0f}" for v in wf_deltas],
            textposition="outside", textfont_size=10,
        ))
        fig_wf.update_layout(height=320, yaxis_tickprefix="£", yaxis_tickformat=",.0f",
                             plot_bgcolor="white", paper_bgcolor="white",
                             font=dict(family="system-ui, sans-serif", size=11),
                             margin=dict(t=44, b=28, l=8, r=8), showlegend=False)
        st.plotly_chart(fig_wf, use_container_width=True)
    with col_tbl:
        st.dataframe(apply_style(pd.DataFrame(gd_rows), chg=["YOY"]), use_container_width=True, hide_index=True)
else:
    st.info("Upload F&B sales file to see growth decomposition.")

# ── Seasonal index ────────────────────────────────────────────────────────────
sec("Seasonal Trading Index (100 = average month)")
months_list  = month_iter(ty_from, ty_to)
month_labels = [m.strftime("%b %y") for m in months_list]

comb_m = {}
for m in months_list:
    k  = m.strftime("%Y-%m")
    r  = ty_ev["by_month"].get(k, {}).get("revenue") or 0
    fb = ty_wd["by_month"].get(k, {}).get("total") or 0 if d["has_fb"] else 0
    comb_m[k] = r + fb

avg = sum(comb_m.values()) / len(comb_m) if comb_m else 1
idx_vals   = [comb_m[m.strftime("%Y-%m")] / avg * 100 for m in months_list]
idx_colors = [BRAND_GREEN if v >= 100 else BRAND_LIGHT for v in idx_vals]

fig_idx = go.Figure(go.Bar(x=month_labels, y=idx_vals, marker_color=idx_colors,
                            text=[f"{v:.0f}" for v in idx_vals], textposition="outside"))
fig_idx.add_hline(y=100, line_dash="dash", line_color="#999",
                  annotation_text="100 = avg month", annotation_font_size=10)
fig_idx.update_layout(height=340, showlegend=False, yaxis_title="Index",
                      plot_bgcolor="white", paper_bgcolor="white",
                      font=dict(family="system-ui, sans-serif", size=11),
                      margin=dict(t=44, b=28, l=8, r=8),
                      xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#f0f0f0"))
st.plotly_chart(fig_idx, use_container_width=True)

# ── Like-for-like ─────────────────────────────────────────────────────────────
LFL = {"The Bell & Crown", "The Grosvenor Arms", "The Pembroke Arms", "The Silver Plough"}
if d["has_fb"]:
    sec("Like-for-Like F&B Growth (Established Venues)")
    lfl_rows = []
    for v in sorted(LFL):
        ty_v = ty_wd["by_venue"].get(v, {}); ly_v = ly_wd["by_venue"].get(v, {})
        g = lambda dct, k: dct.get(k) or 0.0
        ty_t = g(ty_v,"total"); ly_t = g(ly_v,"total")
        lfl_rows.append({
            "Venue":    v,
            "LY Total": gbp(ly_t, net=net), "TY Total": gbp(ty_t, net=net),
            "LFL YOY":  pct(delta_pct(ty_t, ly_t)) if ly_t else "—",
            "TY Wet":   gbp(g(ty_v,"wet"), net=net),
            "TY Dry":   gbp(g(ty_v,"dry"), net=net),
            "TY Mix":   f"{g(ty_v,'wet_pct')*100:.0f}%W / {(1-g(ty_v,'wet_pct'))*100:.0f}%D" if ty_t else "—",
        })
    lfl_ty = sum(ty_wd["by_venue"].get(v, {}).get("total") or 0 for v in LFL)
    lfl_ly = sum(ly_wd["by_venue"].get(v, {}).get("total") or 0 for v in LFL)
    lfl_rows.append({"Venue": "LFL TOTAL",
                     "LY Total": gbp(lfl_ly, net=net), "TY Total": gbp(lfl_ty, net=net),
                     "LFL YOY": pct(delta_pct(lfl_ty, lfl_ly)) if lfl_ly else "—",
                     "TY Wet": "", "TY Dry": "", "TY Mix": ""})
    st.dataframe(apply_style(pd.DataFrame(lfl_rows), chg=["LFL YOY"]), use_container_width=True, hide_index=True)

    sec("Venue Wet/Dry Benchmarking")
    grp_avg   = ty_wd["wet_pct"]
    bench_rows = []
    for venue, dct in sorted(ty_wd["by_venue"].items(), key=lambda x: -x[1]["wet_pct"]):
        wp = dct["wet_pct"]
        bench_rows.append({
            "Venue":     venue,
            "Wet %":     f"{wp*100:.1f}%",
            "Dry %":     f"{(1-wp)*100:.1f}%",
            "vs Avg":    f"{(wp-grp_avg)*100:+.1f}%pts",
            "TY Revenue":gbp(dct["total"], net=net),
            "Character": (
                "Very drinks-led" if wp > grp_avg+0.10 else
                "Drinks-led"      if wp > grp_avg+0.03 else
                "Balanced"        if abs(wp-grp_avg) <= 0.03 else "Food-led"
            ),
        })
    bench_rows.append({
        "Venue":"GROUP AVERAGE","Wet %":f"{grp_avg*100:.1f}%",
        "Dry %":f"{(1-grp_avg)*100:.1f}%","vs Avg":"—",
        "TY Revenue":gbp(ty_wd["total"], net=net),"Character":"—",
    })
    st.dataframe(pd.DataFrame(bench_rows), use_container_width=True, hide_index=True)

import streamlit as st
st.set_page_config(page_title="Chickpea — Reviews", page_icon="⭐", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils import (
    inject_css, render_sidebar, load_data, load_feedback,
    page_header, sec, note,
    kpi_html, delta_pct, month_iter,
    BRAND_GREEN, BRAND_LIGHT, GOOD, WARN, BAD,
)

inject_css()
ty_from, ty_to, ly_from, ly_to = render_sidebar()
d  = load_data(ty_from, ty_to, ly_from, ly_to)
vm = d.get("vm", {})

page_header("Guest Reviews (SevenRooms Feedback)",
            f"TY {ty_from.strftime('%b %Y')} – {ty_to.strftime('%b %Y')}",
            f"LY {ly_from.strftime('%b %Y')} – {ly_to.strftime('%b %Y')}")

with st.spinner("Loading feedback…"):
    fb_raw   = load_feedback(ty_from, ty_to, ly_from, ly_to, vm)
ty_fb_df = fb_raw.get("ty", pd.DataFrame())
ly_fb_df = fb_raw.get("ly", pd.DataFrame())

if "err" in fb_raw:
    st.warning(f"Feedback load error: {fb_raw['err'][:120]}")

has_reviews = (not ty_fb_df.empty and "rating" in ty_fb_df.columns
               and ty_fb_df["rating"].notna().any())

if not has_reviews:
    st.markdown(
        '<div class="info-box">Guest feedback from SevenRooms will appear here once '
        'reservation feedback is collected. Ensure your SevenRooms venues have the '
        'post-dining survey / feedback feature enabled.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

ty_r = ty_fb_df[ty_fb_df["rating"].notna()].copy()
ly_r = ly_fb_df[ly_fb_df["rating"].notna()].copy() if not ly_fb_df.empty else pd.DataFrame()

ty_avg = float(ty_r["rating"].mean()) if not ty_r.empty else 0.0
ly_avg = float(ly_r["rating"].mean()) if not ly_r.empty else 0.0
ty_cnt = len(ty_r); ly_cnt = len(ly_r)
ty_hi  = len(ty_r[ty_r["rating"] >= 4]); ty_lo = len(ty_r[ty_r["rating"] <= 2])

c1, c2, c3, c4 = st.columns(4)
c1.markdown(kpi_html("Avg Rating", f"{ty_avg:.2f} / 5",
    f"LY {ly_avg:.2f} / 5", delta_pct(ty_avg, ly_avg)), unsafe_allow_html=True)
c2.markdown(kpi_html("Reviews Received", f"{ty_cnt:,}",
    f"LY {ly_cnt:,}", delta_pct(ty_cnt, ly_cnt)), unsafe_allow_html=True)
c3.markdown(kpi_html("4–5 Star Reviews", f"{ty_hi:,}",
    f"{ty_hi/ty_cnt*100:.0f}% of total" if ty_cnt else "", None), unsafe_allow_html=True)
c4.markdown(kpi_html("1–2 Star Reviews", f"{ty_lo:,}",
    f"{ty_lo/ty_cnt*100:.0f}% of total" if ty_cnt else "",
    None, card_class="warn" if ty_lo > 0 else ""), unsafe_allow_html=True)

# By venue
sec("Average Rating by Venue")
venue_ratings = (ty_r.groupby("venue_name")["rating"]
                 .agg(["mean","count"]).reset_index()
                 .sort_values("mean", ascending=True))
v_colors = [GOOD if v >= 4.0 else (WARN if v >= 3.0 else BAD) for v in venue_ratings["mean"]]
fig_vr = go.Figure(go.Bar(
    x=venue_ratings["mean"], y=venue_ratings["venue_name"], orientation="h",
    marker_color=v_colors,
    text=[f"{v:.2f}  ({int(c)} reviews)" for v, c in zip(venue_ratings["mean"], venue_ratings["count"])],
    textposition="outside", textfont_size=10,
))
fig_vr.add_vline(x=ty_avg, line_dash="dot", line_color=BRAND_GREEN,
                 annotation_text=f"Avg {ty_avg:.2f}", annotation_font_size=10)
fig_vr.update_layout(
    height=max(280, len(venue_ratings)*40+80),
    xaxis=dict(range=[0, 5.6], showgrid=True, gridcolor="#f0f0f0"),
    yaxis=dict(showgrid=False), showlegend=False,
    plot_bgcolor="white", paper_bgcolor="white",
    font=dict(family="system-ui, sans-serif", size=11),
    margin=dict(t=20, b=20, l=8, r=100),
)
st.plotly_chart(fig_vr, use_container_width=True)

# Distribution + trend
sec("Rating Distribution & Monthly Trend")
col_dist, col_trend = st.columns(2)

with col_dist:
    buckets = {1:0, 2:0, 3:0, 4:0, 5:0}
    for v in ty_r["rating"].dropna():
        k = min(5, max(1, round(v))); buckets[k] = buckets.get(k, 0) + 1
    fig_d = go.Figure(go.Bar(
        x=[f"{k} ★" for k in sorted(buckets)],
        y=[buckets[k] for k in sorted(buckets)],
        marker_color=[BAD, BAD, WARN, GOOD, GOOD],
        text=[str(buckets[k]) for k in sorted(buckets)], textposition="outside",
    ))
    fig_d.update_layout(height=300, showlegend=False,
                        plot_bgcolor="white", paper_bgcolor="white",
                        font=dict(family="system-ui, sans-serif", size=11),
                        margin=dict(t=20, b=20, l=8, r=8),
                        yaxis=dict(gridcolor="#f0f0f0"), xaxis=dict(showgrid=False))
    st.plotly_chart(fig_d, use_container_width=True)

with col_trend:
    ty_r2 = ty_r.copy()
    ty_r2["month"] = pd.to_datetime(ty_r2["date"], errors="coerce").dt.to_period("M")
    mavg = ty_r2.dropna(subset=["month"]).groupby("month")["rating"].mean().reset_index()
    if not mavg.empty:
        mavg["ms"] = mavg["month"].astype(str)
        fig_t = go.Figure(go.Scatter(
            x=mavg["ms"], y=mavg["rating"], mode="lines+markers",
            line=dict(color=BRAND_GREEN, width=2.5), marker=dict(size=7, color=BRAND_GREEN),
            text=[f"{v:.2f}" for v in mavg["rating"]], textposition="top center", textfont_size=9,
        ))
        fig_t.add_hline(y=ty_avg, line_dash="dot", line_color=BRAND_LIGHT,
                        annotation_text=f"Avg {ty_avg:.2f}", annotation_font_size=9)
        fig_t.update_layout(height=300,
                            yaxis=dict(range=[1, 5.5], gridcolor="#f0f0f0"), showlegend=False,
                            xaxis=dict(showgrid=False), yaxis_title="Avg Rating",
                            plot_bgcolor="white", paper_bgcolor="white",
                            font=dict(family="system-ui, sans-serif", size=11),
                            margin=dict(t=20, b=20, l=8, r=8))
        st.plotly_chart(fig_t, use_container_width=True)

# Sub-ratings
sub_avgs = {}
for col, lbl in [("food_rating","Food"),("service_rating","Service"),("ambiance_rating","Ambiance")]:
    if col in ty_r.columns:
        v = ty_r[col].dropna()
        if len(v) > 0: sub_avgs[lbl] = float(v.mean())

if sub_avgs:
    sec("Category Ratings")
    sc = st.columns(len(sub_avgs))
    for i, (lbl, avg) in enumerate(sub_avgs.items()):
        cls = "" if avg >= 4 else ("warn" if avg >= 3 else "danger")
        sc[i].markdown(kpi_html(f"{lbl} Rating", f"{avg:.2f} / 5", "", None, card_class=cls), unsafe_allow_html=True)

# Recent comments
comments_df = ty_r[ty_r["comments"].str.len() > 5].sort_values("date", ascending=False)
if not comments_df.empty:
    sec("Recent Guest Comments")
    show_n = st.slider("Number of comments to show", 5, min(100, len(comments_df)), 20, step=5)
    for _, row in comments_df.head(show_n).iterrows():
        stars    = int(round(row["rating"])) if pd.notna(row["rating"]) else 0
        star_str = "★" * stars + "☆" * (5 - stars)
        color_s  = GOOD if stars >= 4 else (WARN if stars >= 3 else BAD)
        venue_s  = str(row.get("venue_name", ""))
        date_s   = str(row.get("date", ""))[:10]
        guest_s  = str(row.get("guest_name", "")).strip()
        comment  = str(row.get("comments", "")).strip()
        st.markdown(
            f'<div style="background:white;border-radius:8px;padding:0.7rem 1rem;'
            f'margin-bottom:0.4rem;box-shadow:0 1px 6px rgba(0,0,0,0.06);border-left:4px solid {color_s};">'
            f'<span style="color:{color_s};font-size:1rem;">{star_str}</span>'
            f'&nbsp;&nbsp;<b style="font-size:0.78rem;color:{BRAND_GREEN};">{venue_s}</b>'
            f'<span style="font-size:0.72rem;color:#bbb;margin-left:0.6rem;">{date_s}'
            f'{" · " + guest_s if guest_s else ""}</span>'
            f'<div style="font-size:0.82rem;color:#444;margin-top:0.3rem;line-height:1.45;">{comment}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

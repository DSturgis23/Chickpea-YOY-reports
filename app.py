"""
Chickpea Pub Group — Annual Performance Dashboard
Single-page multi-tab app.
"""
import calendar
import io
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import date, timedelta

st.set_page_config(
    page_title="Chickpea — Annual Performance",
    page_icon="🍺",
    layout="wide",
)

def _check_password():
    """Simple password gate — password stored in st.secrets['app_password']."""
    def _submit():
        pwd = st.secrets.get("app_password", "chickpea2024")
        st.session_state["_auth"] = (st.session_state.get("_pwd_input") == pwd)

    if st.session_state.get("_auth"):
        return True

    st.markdown(
        f"<div style='max-width:380px;margin:6rem auto;background:white;border-radius:16px;"
        f"padding:2.5rem 2rem;box-shadow:0 8px 32px rgba(0,0,0,0.1);text-align:center;'>"
        f"<div style='font-size:2rem;font-weight:900;color:#1C3829;letter-spacing:-0.03em;"
        f"margin-bottom:0.25rem;'>chickpea.</div>"
        f"<div style='font-size:0.8rem;color:#999;margin-bottom:1.8rem;'>Annual Performance Report</div>",
        unsafe_allow_html=True,
    )
    st.text_input("Password", type="password", key="_pwd_input",
                  on_change=_submit, label_visibility="collapsed",
                  placeholder="Enter password…")
    if st.session_state.get("_auth") is False:
        st.error("Incorrect password.", icon="🔒")
    st.markdown("</div>", unsafe_allow_html=True)
    return False

if not _check_password():
    st.stop()

from utils import (
    inject_css, page_header, sec, note, good, date_override,
    gbp, pct, delta_pct, kpi_html, month_iter, apply_style,
    grouped_bar, line_chart, hbar_chart, donut_chart,
    stacked_bar, gauge_chart,
    BRAND_GREEN, BRAND_LIGHT, DRINKS_CLR, FOOD_CLR, GOOD, WARN, BAD,
)
from config import EVIIVO_PROPERTIES, ROOM_COUNTS, ROOMS_AND_FB, PHONE_TARGET
import data as D
import metrics as M

inject_css()

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        f"<div style='color:{BRAND_GREEN};font-size:1rem;font-weight:900;"
        "letter-spacing:-0.02em;margin:0.3rem 0 0.8rem;'>chickpea.</div>",
        unsafe_allow_html=True,
    )

    today   = date.today()
    fy_year = today.year if today.month >= 8 else today.year - 1

    ty_from = st.date_input("Period from", date(fy_year, 8, 1))
    ty_to   = st.date_input("Period to",   today.replace(day=1) - timedelta(days=1))
    ly_from = ty_from.replace(year=ty_from.year - 1)
    ly_to   = ty_to.replace(year=ty_to.year - 1)

    st.divider()
    _EMBEDDED = Path(__file__).parent / "data" / "weekly_sales.xlsx"
    if _EMBEDDED.exists():
        st.markdown("**F&B Sales Data**")
        st.caption("Sales data loaded from embedded file. Upload a newer file below to override.")
        sales_file = st.file_uploader("Override sales file", type=["xlsx"], label_visibility="collapsed")
    else:
        st.markdown("**F&B Sales Data**")
        st.caption("Upload WEEKLY SALES & MARGINS.xlsx to unlock F&B, Combined & Analytics tabs.")
        sales_file = st.file_uploader("", type=["xlsx"], label_visibility="collapsed")

    st.divider()
    show_net = st.toggle("Show net (ex-VAT)", value=False)

    st.divider()
    if st.button("↺ Refresh Data", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        f"<div style='font-size:0.7rem;color:#aaa;margin-top:0.8rem;line-height:1.7;'>"
        f"<b>TY</b> {ty_from.strftime('%d %b %Y')} – {ty_to.strftime('%d %b %Y')}<br>"
        f"<b>LY</b> {ly_from.strftime('%d %b %Y')} – {ly_to.strftime('%d %b %Y')}</div>",
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"<div style='display:flex;align-items:center;justify-content:space-between;"
    f"background:linear-gradient(120deg,{BRAND_GREEN} 0%,#2d5a40 100%);"
    f"color:white;padding:0.85rem 1.4rem;border-radius:10px;margin-bottom:1rem;"
    f"box-shadow:0 4px 18px rgba(28,56,41,0.18);'>"
    f"<div><span style='font-size:1.35rem;font-weight:900;letter-spacing:-0.03em;'>chickpea.</span>"
    f"<span style='font-size:0.95rem;font-weight:600;opacity:0.9;margin-left:0.75rem;'>Annual Performance Report</span></div>"
    f"<div style='text-align:right;font-size:0.74rem;opacity:0.8;'>"
    f"TY: {ty_from.strftime('%d %b %Y')} – {ty_to.strftime('%d %b %Y')}<br>"
    f"LY: {ly_from.strftime('%d %b %Y')} – {ly_to.strftime('%d %b %Y')}</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def load_feedback_cached(tf, tt, lf, lt, vm_items):
    vm = dict(vm_items)
    out = {}
    try:
        tok = D.get_sr_token()
        out["ty"] = D.fetch_sr_feedback(tok, vm, tf, tt)
        out["ly"] = D.fetch_sr_feedback(tok, vm, lf, lt)
    except Exception as e:
        out["ty"] = pd.DataFrame(); out["ly"] = pd.DataFrame(); out["err"] = str(e)
    return out

_EMBEDDED = Path(__file__).parent / "data" / "weekly_sales.xlsx"

# ── Single cached function: fetch APIs + compute metrics, return dicts only ───
# Returning dicts (not DataFrames) means Streamlit's cache never has to copy
# large DataFrames on re-renders — every subsequent call is a fast dict lookup.
@st.cache_data(ttl=3600, show_spinner=False)
def load_all(tf, tt, lf, lt):
    out = {"ev_err": None, "sr_err": None, "vm": {}}
    try:
        tok = D.get_ev_token()
        ty_ev_df = D.fetch_ev_bookings(tok, tf, tt)
        ly_ev_df = D.fetch_ev_bookings(tok, lf, lt)
        out["ty_ev"] = M.ev_metrics(ty_ev_df, tf, tt)
        out["ly_ev"] = M.ev_metrics(ly_ev_df, lf, lt)
    except Exception as e:
        out["ty_ev"] = M.ev_metrics(pd.DataFrame(), tf, tt)
        out["ly_ev"] = M.ev_metrics(pd.DataFrame(), lf, lt)
        out["ev_err"] = str(e)
    try:
        st_tok = D.get_sr_token()
        vm = D.fetch_sr_venues(st_tok)
        ty_sr_df = D.fetch_sr_reservations(st_tok, vm, tf, tt)
        ly_sr_df = D.fetch_sr_reservations(st_tok, vm, lf, lt)
        out["ty_sr"] = M.sr_metrics(ty_sr_df)
        out["ly_sr"] = M.sr_metrics(ly_sr_df)
        out["vm"]    = vm
    except Exception as e:
        out["ty_sr"] = M.sr_metrics(pd.DataFrame())
        out["ly_sr"] = M.sr_metrics(pd.DataFrame())
        out["sr_err"] = str(e)
    return out

@st.cache_data(ttl=None, show_spinner=False)   # historical — never expires
def load_sales(tf, tt, lf, lt):
    p = Path(__file__).parent / "data" / "weekly_sales.xlsx"
    if not p.exists():
        return M.wds_metrics(pd.DataFrame()), M.wds_metrics(pd.DataFrame())
    b = p.read_bytes()
    try:
        return (M.wds_metrics(D.parse_sales_excel(io.BytesIO(b), tf, tt)),
                M.wds_metrics(D.parse_sales_excel(io.BytesIO(b), lf, lt)))
    except Exception:
        return M.wds_metrics(pd.DataFrame()), M.wds_metrics(pd.DataFrame())

@st.cache_data(ttl=3600, show_spinner=False)
def load_tevalis(tf, tt, lf, lt):
    out = {}
    try:
        out["ty"] = D.fetch_tevalis_sales(tf, tt)
        out["ly"] = D.fetch_tevalis_sales(lf, lt)
    except Exception as e:
        out["ty"] = pd.DataFrame(); out["ly"] = pd.DataFrame()
        out["err"] = str(e)
    return out

# ── Load once — all subsequent re-renders are instant dict lookups ─────────────
with st.spinner("Loading data…"):
    _d   = load_all(ty_from, ty_to, ly_from, ly_to)
    ty_wd, ly_wd = load_sales(ty_from, ty_to, ly_from, ly_to)

ty_ev = _d["ty_ev"]; ly_ev = _d["ly_ev"]
ty_sr = _d["ty_sr"]; ly_sr = _d["ly_sr"]
_vm   = _d["vm"]

if _d["ev_err"]: st.sidebar.warning(f"Eviivo: {_d['ev_err'][:80]}")
if _d["sr_err"]: st.sidebar.warning(f"SevenRooms: {_d['sr_err'][:80]}")

has_fb = ty_wd["total"] > 0

months_list  = month_iter(ty_from, ty_to)
month_labels = [m.strftime("%b %y") for m in months_list]
def lyk(m): return m.replace(year=m.year - 1).strftime("%Y-%m")


def metrics_for(tf, tt, lf, lt):
    """Return metrics for a custom date range. All cached — fast on repeat calls."""
    d = load_all(tf, tt, lf, lt)
    twd_m, lwd_m = load_sales(tf, tt, lf, lt)
    ml = month_iter(tf, tt)
    return (d["ty_ev"], d["ly_ev"], d["ty_sr"], d["ly_sr"],
            twd_m, lwd_m, twd_m["total"] > 0, ml, [m.strftime("%b %y") for m in ml])

# Shorthand revenue refs used in multiple tabs
rev_ty = ty_ev["revenue"] or 0;  rev_ly = ly_ev["revenue"] or 0
fb_ty  = ty_wd["total"]   or 0;  fb_ly  = ly_wd["total"]   or 0
occ_ty = ty_ev["occ"];            occ_ly = ly_ev["occ"]
adr_ty = ty_ev["adr"];            adr_ly = ly_ev["adr"]
rp_ty  = ty_ev["revpar"];         rp_ly  = ly_ev["revpar"]
cov_ty = ty_sr["covers"] or 0;   cov_ly = ly_sr["covers"] or 0
ug_ty  = ty_sr["unique_guests"] or 0; ug_ly = ly_sr["unique_guests"] or 0


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "📊 Overview",
    "🛏 Rooms",
    "🍽 F&B Sales",
    "🪑 Reservations",
    "🔗 Combined",
    "📈 Analytics",
    "🔮 Projections",
    "📞 Phone",
    "⭐ Reviews",
    "🍺 EPOS Live",
])
tab_overview, tab_rooms, tab_fb, tab_res, tab_comb, tab_ana, tab_proj, tab_phone, tab_rev, tab_epos = tabs


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    stays_ty = ty_ev["stays"] or 0; stays_ly = ly_ev["stays"] or 0
    c1.markdown(kpi_html(f"Room Revenue {'(Net)' if show_net else '(Gross)'}",
        gbp(rev_ty, net=show_net), f"LY {gbp(rev_ly, net=show_net)}", delta_pct(rev_ty, rev_ly)), unsafe_allow_html=True)
    c2.markdown(kpi_html(f"F&B Sales {'(Net)' if show_net else '(Gross)'}",
        gbp(fb_ty, net=show_net) if fb_ty else "Upload →",
        f"LY {gbp(fb_ly, net=show_net)}" if fb_ly else "",
        delta_pct(fb_ty, fb_ly) if fb_ty and fb_ly else None), unsafe_allow_html=True)
    c3.markdown(kpi_html("F&B Covers", f"{cov_ty:,}", f"LY {cov_ly:,}", delta_pct(cov_ty, cov_ly)), unsafe_allow_html=True)
    c4.markdown(kpi_html("Unique Guests", f"{ug_ty:,}", f"LY {ug_ly:,}", delta_pct(ug_ty, ug_ly)), unsafe_allow_html=True)

    st.markdown("&nbsp;", unsafe_allow_html=True)
    c5, c6, c7, c8 = st.columns(4)
    c5.markdown(kpi_html("Occupancy",
        f"{occ_ty*100:.1f}%" if occ_ty else "—", f"LY {occ_ly*100:.1f}%" if occ_ly else "—",
        delta_pct(occ_ty or 0, occ_ly or 0) if occ_ty and occ_ly else None), unsafe_allow_html=True)
    c6.markdown(kpi_html("ADR",
        gbp(adr_ty, 2, net=show_net) if adr_ty else "—", f"LY {gbp(adr_ly, 2, net=show_net)}" if adr_ly else "—",
        delta_pct(adr_ty or 0, adr_ly or 0) if adr_ty and adr_ly else None), unsafe_allow_html=True)
    c7.markdown(kpi_html("RevPAR",
        gbp(rp_ty, 2, net=show_net) if rp_ty else "—", f"LY {gbp(rp_ly, 2, net=show_net)}" if rp_ly else "—",
        delta_pct(rp_ty or 0, rp_ly or 0) if rp_ty and rp_ly else None), unsafe_allow_html=True)
    c8.markdown(kpi_html("Confirmed Stays", f"{stays_ty:,}", f"LY {stays_ly:,}", delta_pct(stays_ty, stays_ly)), unsafe_allow_html=True)

    sec("Monthly Revenue Trend")
    ty_rev_m = [(ty_ev["by_month"].get(m.strftime("%Y-%m"), {}).get("revenue") or 0) for m in months_list]
    ly_rev_m = [(ly_ev["by_month"].get(lyk(m), {}).get("revenue") or 0) for m in months_list]
    ty_comb_m = [(r + (ty_wd["by_month"].get(m.strftime("%Y-%m"), {}).get("total") or 0)) for r, m in zip(ty_rev_m, months_list)] if has_fb else ty_rev_m
    ly_comb_m = [(r + (ly_wd["by_month"].get(lyk(m), {}).get("total") or 0)) for r, m in zip(ly_rev_m, months_list)] if has_fb else ly_rev_m

    col_c, col_d = st.columns([3, 1])
    with col_c:
        st.plotly_chart(line_chart(month_labels, ty_comb_m, ly_comb_m, height=330), use_container_width=True)
    with col_d:
        if has_fb and rev_ty:
            st.plotly_chart(donut_chart(
                ["Rooms", "Drinks", "Food"], [rev_ty, ty_wd["wet"] or 0, ty_wd["dry"] or 0],
                colors=[BRAND_GREEN, DRINKS_CLR, FOOD_CLR], center_text="Revenue<br>Mix", height=330,
            ), use_container_width=True)

    sec("Key Metrics at a Glance")
    def _r(label, ty_v, ly_v, fmt):
        chg = delta_pct(ty_v, ly_v) if ty_v is not None and ly_v else None
        return {"Metric": label, "Last Year": fmt(ly_v) if ly_v is not None else "—",
                "This Year": fmt(ty_v) if ty_v is not None else "—",
                "YOY": pct(chg) if chg is not None else "—"}

    _rv = lambda v: gbp(v, net=show_net) if v else "—"
    _av = lambda v: gbp(v, 2, net=show_net) if v else "—"
    _ov = lambda v: f"{v*100:.1f}%" if v else "—"
    _nv = lambda v: f"{v:,.0f}" if v else "—"
    _pv = lambda v: f"{v*100:.1f}%" if v else "—"

    summary_rows = [
        _r("Room Revenue", rev_ty, rev_ly, _rv),
        _r("Confirmed Stays", stays_ty, stays_ly, _nv),
        _r("Occupancy", occ_ty, occ_ly, _ov),
        _r("ADR", adr_ty, adr_ly, _av),
        _r("RevPAR", rp_ty, rp_ly, _av),
        _r("F&B Covers", cov_ty, cov_ly, _nv),
        _r("Unique Guests", ug_ty, ug_ly, _nv),
        _r("Repeat Visit Rate", ty_sr.get("repeat_rate"), ly_sr.get("repeat_rate"), _pv),
    ]
    if has_fb:
        summary_rows += [
            _r("F&B Total", fb_ty, fb_ly, _rv),
            _r("Wet (Drinks)", ty_wd["wet"], ly_wd["wet"], _rv),
            _r("Dry (Food)", ty_wd["dry"], ly_wd["dry"], _rv),
        ]
    st.dataframe(apply_style(pd.DataFrame(summary_rows), chg=["YOY"]),
                 use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — ROOMS
# ─────────────────────────────────────────────────────────────────────────────
with tab_rooms:
    _tf, _tt, _lf, _lt, _custom = date_override("rooms", ty_from, ty_to)
    if _custom:
        ty_ev, ly_ev, _, _, _, _, _, months_list, month_labels = metrics_for(_tf, _tt, _lf, _lt)
        rev_ty = ty_ev["revenue"] or 0; rev_ly = ly_ev["revenue"] or 0
        occ_ty = ty_ev["occ"];           occ_ly = ly_ev["occ"]
        adr_ty = ty_ev["adr"];           adr_ly = ly_ev["adr"]
        rp_ty  = ty_ev["revpar"];        rp_ly  = ly_ev["revpar"]
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi_html(f"Revenue {'(Net)' if show_net else '(Gross)'}",
        gbp(rev_ty, net=show_net), f"LY {gbp(rev_ly, net=show_net)}", delta_pct(rev_ty, rev_ly)), unsafe_allow_html=True)
    c2.markdown(kpi_html("Occupancy",
        f"{occ_ty*100:.1f}%" if occ_ty else "—", f"LY {occ_ly*100:.1f}%" if occ_ly else "—",
        delta_pct(occ_ty or 0, occ_ly or 0) if occ_ty and occ_ly else None), unsafe_allow_html=True)
    c3.markdown(kpi_html("ADR",
        gbp(adr_ty, 2, net=show_net) if adr_ty else "—", f"LY {gbp(adr_ly, 2, net=show_net)}" if adr_ly else "—",
        delta_pct(adr_ty or 0, adr_ly or 0) if adr_ty and adr_ly else None), unsafe_allow_html=True)
    c4.markdown(kpi_html("RevPAR",
        gbp(rp_ty, 2, net=show_net) if rp_ty else "—", f"LY {gbp(rp_ly, 2, net=show_net)}" if rp_ly else "—",
        delta_pct(rp_ty or 0, rp_ly or 0) if rp_ty and rp_ly else None), unsafe_allow_html=True)

    sec("Monthly Performance")
    ty_rev_m = [(ty_ev["by_month"].get(m.strftime("%Y-%m"), {}).get("revenue") or 0) for m in months_list]
    ly_rev_m = [(ly_ev["by_month"].get(lyk(m), {}).get("revenue") or 0) for m in months_list]
    ty_occ_m = [(ty_ev["by_month"].get(m.strftime("%Y-%m"), {}).get("occ") or 0)*100 for m in months_list]
    ly_occ_m = [(ly_ev["by_month"].get(lyk(m), {}).get("occ") or 0)*100 for m in months_list]

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

    with st.expander("Month-by-month detail", expanded=True):
        mrows_rev = []; mrows_kpi = []
        for m in months_list:
            ty_m = ty_ev["by_month"].get(m.strftime("%Y-%m"), {}); ly_m = ly_ev["by_month"].get(lyk(m), {})
            g = lambda d, k: d.get(k) or 0
            ty_r2 = g(ty_m,"revenue"); ly_r2 = g(ly_m,"revenue")
            mrows_rev.append({
                "Month":    m.strftime("%b %Y"),
                "LY Revenue": gbp(ly_r2, net=show_net),
                "TY Revenue": gbp(ty_r2, net=show_net),
                "Change %":   pct(delta_pct(ty_r2, ly_r2)) if ly_r2 else "—",
                "LY Stays":   f"{g(ly_m,'stays'):,}",
                "TY Stays":   f"{g(ty_m,'stays'):,}",
            })
            mrows_kpi.append({
                "Month":     m.strftime("%b %Y"),
                "LY ADR":    gbp(g(ly_m,"adr"), 2, net=show_net) if g(ly_m,"adr") else "—",
                "TY ADR":    gbp(g(ty_m,"adr"), 2, net=show_net) if g(ty_m,"adr") else "—",
                "LY Occ":    f"{g(ly_m,'occ')*100:.1f}%" if ly_m.get("occ") else "—",
                "TY Occ":    f"{g(ty_m,'occ')*100:.1f}%" if ty_m.get("occ") else "—",
                "LY RevPAR": gbp(g(ly_m,"revpar"), 2, net=show_net) if ly_m.get("revpar") else "—",
                "TY RevPAR": gbp(g(ty_m,"revpar"), 2, net=show_net) if ty_m.get("revpar") else "—",
            })
        mt1, mt2 = st.tabs(["Revenue & Stays", "ADR / Occupancy / RevPAR"])
        with mt1:
            st.dataframe(apply_style(pd.DataFrame(mrows_rev), chg=["Change %"]),
                         use_container_width=True, hide_index=True)
        with mt2:
            st.dataframe(pd.DataFrame(mrows_kpi), use_container_width=True, hide_index=True)

    with st.expander("By-property detail", expanded=True):
        prows_rev = []; prows_kpi = []
        for p in props:
            ty_p = ty_ev["by_property"].get(p, {}); ly_p = ly_ev["by_property"].get(p, {})
            g = lambda d, k: d.get(k) or 0
            ty_r2 = g(ty_p,"revenue"); ly_r2 = g(ly_p,"revenue")
            prows_rev.append({
                "Property":   p,
                "Rooms":      ROOM_COUNTS.get(p, "—"),
                "LY Revenue": gbp(ly_r2, net=show_net),
                "TY Revenue": gbp(ty_r2, net=show_net),
                "Change %":   pct(delta_pct(ty_r2, ly_r2)) if ly_r2 else "—",
                "LY Stays":   f"{g(ly_p,'stays'):,}",
                "TY Stays":   f"{g(ty_p,'stays'):,}",
            })
            prows_kpi.append({
                "Property":  p,
                "LY ADR":    gbp(g(ly_p,"adr"), 2, net=show_net) if g(ly_p,"adr") else "—",
                "TY ADR":    gbp(g(ty_p,"adr"), 2, net=show_net) if g(ty_p,"adr") else "—",
                "LY Occ":    f"{g(ly_p,'occ')*100:.1f}%" if ly_p.get("occ") else "—",
                "TY Occ":    f"{g(ty_p,'occ')*100:.1f}%" if ty_p.get("occ") else "—",
                "LY RevPAR": gbp(g(ly_p,"revpar"), 2, net=show_net) if ly_p.get("revpar") else "—",
                "TY RevPAR": gbp(g(ty_p,"revpar"), 2, net=show_net) if ty_p.get("revpar") else "—",
            })
        pt1, pt2 = st.tabs(["Revenue & Stays", "ADR / Occupancy / RevPAR"])
        with pt1:
            st.dataframe(apply_style(pd.DataFrame(prows_rev), chg=["Change %"]),
                         use_container_width=True, hide_index=True)
        with pt2:
            st.dataframe(pd.DataFrame(prows_kpi), use_container_width=True, hide_index=True)

    note("The Fleur de Lys opened late Sep 2025 and Manor House Inn joined Eviivo Feb 2025 — "
         "their YOY comparisons reflect new trading periods. The Queen's Head expanded from 4 to "
         "9 rooms in March 2026.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 10 — EPOS LIVE (Tevalis — supplementary / going forward)
# ─────────────────────────────────────────────────────────────────────────────
with tab_epos:
    st.markdown(
        '<div class="info-box"><b>EPOS Live</b> pulls directly from Tevalis in real time. '
        'This tab is supplementary — all F&B figures across the rest of the dashboard '
        'use your uploaded spreadsheet. Going forward, once Tevalis covers the full '
        'financial year, it will replace the spreadsheet upload.</div>',
        unsafe_allow_html=True,
    )
    with st.spinner("Loading Tevalis EPOS data…"):
        tev_raw = load_tevalis(ty_from, ty_to, ly_from, ly_to)
    ty_tev = M.tevalis_metrics(tev_raw.get("ty", pd.DataFrame()))
    ly_tev = M.tevalis_metrics(tev_raw.get("ly", pd.DataFrame()))
    has_tev = ty_tev["total"] > 0
    if not has_tev:
        st.info("No Tevalis EPOS data loaded yet — try refreshing.")
    else:
        wet_ty = ty_tev["wet"]; wet_ly = ly_tev["wet"] or 0
        dry_ty = ty_tev["dry"]; dry_ly = ly_tev["dry"] or 0
        fb_tev_ty = ty_tev["total"]; fb_tev_ly = ly_tev["total"] or 0

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(kpi_html(f"Total F&B {'(Net)' if show_net else '(Gross)'}",
            gbp(fb_tev_ty, net=show_net), f"LY {gbp(fb_tev_ly, net=show_net)}", delta_pct(fb_tev_ty, fb_tev_ly)), unsafe_allow_html=True)
        c2.markdown(kpi_html("Wet (Drinks)", gbp(wet_ty, net=show_net), f"LY {gbp(wet_ly, net=show_net)}", delta_pct(wet_ty, wet_ly)), unsafe_allow_html=True)
        c3.markdown(kpi_html("Dry (Food)", gbp(dry_ty, net=show_net), f"LY {gbp(dry_ly, net=show_net)}", delta_pct(dry_ty, dry_ly)), unsafe_allow_html=True)
        c4.markdown(kpi_html("Covers (EPOS)", f"{ty_tev['covers']:,}", f"LY {ly_tev['covers']:,}", delta_pct(ty_tev["covers"], ly_tev["covers"])), unsafe_allow_html=True)

        sec("Monthly F&B Revenue — EPOS (Tevalis)")
        ty_wet_m_t = [(ty_tev["by_month"].get(m.strftime("%Y-%m"), {}).get("wet") or 0) for m in months_list]
        ty_dry_m_t = [(ty_tev["by_month"].get(m.strftime("%Y-%m"), {}).get("dry") or 0) for m in months_list]
        ty_tot_m_t = [(ty_tev["by_month"].get(m.strftime("%Y-%m"), {}).get("total") or 0) for m in months_list]
        ly_tot_m_t = [(ly_tev["by_month"].get(lyk(m), {}).get("total") or 0) for m in months_list]

        et1, et2 = st.tabs(["Wet + Dry Stack (TY)", "TY vs LY"])
        with et1:
            st.plotly_chart(stacked_bar(month_labels, ty_wet_m_t, ty_dry_m_t, height=400), use_container_width=True)
        with et2:
            st.plotly_chart(grouped_bar(month_labels, ty_tot_m_t, ly_tot_m_t, height=400), use_container_width=True)

        sec("Revenue by Venue")
        all_tev_v = sorted(set(list(ty_tev["by_venue"]) + list(ly_tev["by_venue"])))
        tv_ty = [ty_tev["by_venue"].get(v, {}).get("total") or 0 for v in all_tev_v]
        tv_ly = [ly_tev["by_venue"].get(v, {}).get("total") or 0 for v in all_tev_v]
        cl, cr = st.columns(2)
        with cl:
            st.caption("This Year")
            st.plotly_chart(hbar_chart(all_tev_v, tv_ty, height=len(all_tev_v)*40+80), use_container_width=True)
        with cr:
            st.caption("Last Year")
            st.plotly_chart(hbar_chart(all_tev_v, tv_ly, height=len(all_tev_v)*40+80, colors=[BRAND_LIGHT]*len(all_tev_v)), use_container_width=True)

        with st.expander("Venue detail table"):
            vrows_t = []
            for v in all_tev_v:
                ty_v = ty_tev["by_venue"].get(v, {}); ly_v = ly_tev["by_venue"].get(v, {})
                g = lambda d, k: d.get(k) or 0.0
                ty_t = g(ty_v,"total"); ly_t = g(ly_v,"total")
                vrows_t.append({
                    "Venue": v,
                    "LY Wet": gbp(g(ly_v,"wet"), net=show_net), "LY Dry": gbp(g(ly_v,"dry"), net=show_net), "LY Total": gbp(ly_t, net=show_net),
                    "TY Wet": gbp(g(ty_v,"wet"), net=show_net), "TY Dry": gbp(g(ty_v,"dry"), net=show_net), "TY Total": gbp(ty_t, net=show_net),
                    "TY Mix": f"{g(ty_v,'wet_pct')*100:.0f}%W / {(1-g(ty_v,'wet_pct'))*100:.0f}%D" if ty_t else "—",
                    "TY Covers": f"{g(ty_v,'covers'):,.0f}",
                    "YOY": pct(delta_pct(ty_t, ly_t)) if ly_t else "—",
                })
            st.dataframe(apply_style(pd.DataFrame(vrows_t), chg=["YOY"]), use_container_width=True, hide_index=True)

        note("Data pulled live from Tevalis EPOS. Revenue is gross inc. VAT. "
             "Service charge is excluded from wet/dry totals. "
             "Covers reflect EPOS-recorded transactions, which may differ from SevenRooms reservation covers.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — F&B SALES (from WEEKLY SALES & MARGINS.xlsx)
# ─────────────────────────────────────────────────────────────────────────────
with tab_fb:
    _tf, _tt, _lf, _lt, _custom = date_override("fb", ty_from, ty_to)
    if _custom:
        _, _, _, _, ty_wd, ly_wd, has_fb, months_list, month_labels = metrics_for(_tf, _tt, _lf, _lt)
        fb_ty = ty_wd["total"] or 0; fb_ly = ly_wd["total"] or 0
    if not has_fb:
        st.info("Upload your WEEKLY SALES & MARGINS.xlsx in the sidebar to see F&B data.")
    else:
        st.markdown(
            '<div class="good-box">All figures on this tab — and across Overview, Combined and Analytics — '
            'come from your uploaded <b>WEEKLY SALES & MARGINS.xlsx</b>. '
            'The EPOS Live tab (far right) shows Tevalis data separately for reference.</div>',
            unsafe_allow_html=True,
        )
        wet_ty = ty_wd["wet"]; wet_ly = ly_wd["wet"] or 0
        dry_ty = ty_wd["dry"]; dry_ly = ly_wd["dry"] or 0

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(kpi_html(f"Total F&B {'(Net)' if show_net else '(Gross)'}",
            gbp(fb_ty, net=show_net), f"LY {gbp(fb_ly, net=show_net)}", delta_pct(fb_ty, fb_ly)), unsafe_allow_html=True)
        c2.markdown(kpi_html("Wet (Drinks)", gbp(wet_ty, net=show_net), f"LY {gbp(wet_ly, net=show_net)}", delta_pct(wet_ty, wet_ly)), unsafe_allow_html=True)
        c3.markdown(kpi_html("Dry (Food)", gbp(dry_ty, net=show_net), f"LY {gbp(dry_ly, net=show_net)}", delta_pct(dry_ty, dry_ly)), unsafe_allow_html=True)
        c4.markdown(kpi_html("Wet / Dry Split",
            f"{ty_wd['wet_pct']*100:.0f}% / {ty_wd['dry_pct']*100:.0f}%",
            f"LY {ly_wd['wet_pct']*100:.0f}% / {ly_wd['dry_pct']*100:.0f}%", None), unsafe_allow_html=True)

        sec("Monthly F&B Revenue")
        ty_wet_m = [(ty_wd["by_month"].get(m.strftime("%Y-%m"), {}).get("wet") or 0) for m in months_list]
        ty_dry_m = [(ty_wd["by_month"].get(m.strftime("%Y-%m"), {}).get("dry") or 0) for m in months_list]
        ty_tot_m = [(ty_wd["by_month"].get(m.strftime("%Y-%m"), {}).get("total") or 0) for m in months_list]
        ly_tot_m = [(ly_wd["by_month"].get(lyk(m), {}).get("total") or 0) for m in months_list]

        ft1, ft2, ft3 = st.tabs(["Wet + Dry Stack (TY)", "TY vs LY", "Wet % Trend"])
        with ft1:
            st.plotly_chart(stacked_bar(month_labels, ty_wet_m, ty_dry_m, height=400), use_container_width=True)
        with ft2:
            st.plotly_chart(grouped_bar(month_labels, ty_tot_m, ly_tot_m, height=400), use_container_width=True)
        with ft3:
            ty_wp_m = [(ty_wd["by_month"].get(m.strftime("%Y-%m"), {}).get("wet_pct") or 0)*100 for m in months_list]
            fig = go.Figure()
            fig.add_scatter(x=month_labels, y=ty_wp_m, fill="tozeroy",
                            line=dict(color=DRINKS_CLR, width=2.5), marker=dict(size=6))
            fig.add_hline(y=ty_wd["wet_pct"]*100, line_dash="dot", line_color=BRAND_GREEN,
                          annotation_text=f"Avg {ty_wd['wet_pct']*100:.0f}%")
            fig.update_layout(height=380, yaxis_ticksuffix="%", showlegend=False,
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
            st.plotly_chart(hbar_chart(all_venues, v_ly, height=len(all_venues)*40+80, colors=[BRAND_LIGHT]*len(all_venues)), use_container_width=True)

        with st.expander("Venue detail table", expanded=True):
            vrows_a = []; vrows_b = []
            for v in all_venues:
                ty_v = ty_wd["by_venue"].get(v, {}); ly_v = ly_wd["by_venue"].get(v, {})
                g = lambda d, k: d.get(k) or 0.0
                ty_t = g(ty_v,"total"); ly_t = g(ly_v,"total")
                vrows_a.append({
                    "Venue":    v,
                    "LY Total": gbp(ly_t, net=show_net),
                    "TY Total": gbp(ty_t, net=show_net),
                    "Change %": pct(delta_pct(ty_t, ly_t)) if ly_t else "—",
                })
                vrows_b.append({
                    "Venue":   v,
                    "TY Wet":  gbp(g(ty_v,"wet"), net=show_net),
                    "TY Dry":  gbp(g(ty_v,"dry"), net=show_net),
                    "LY Wet":  gbp(g(ly_v,"wet"), net=show_net),
                    "LY Dry":  gbp(g(ly_v,"dry"), net=show_net),
                    "TY Mix":  f"{g(ty_v,'wet_pct')*100:.0f}% drinks / {(1-g(ty_v,'wet_pct'))*100:.0f}% food" if ty_t else "—",
                })
            vt1, vt2 = st.tabs(["Totals & YOY", "Wet / Dry Split"])
            with vt1:
                st.dataframe(apply_style(pd.DataFrame(vrows_a), chg=["Change %"]),
                             use_container_width=True, hide_index=True)
            with vt2:
                st.dataframe(pd.DataFrame(vrows_b), use_container_width=True, hide_index=True)

        with st.expander("Month detail table"):
            frows = []
            for m in months_list:
                ty_m = ty_wd["by_month"].get(m.strftime("%Y-%m"), {}); ly_m = ly_wd["by_month"].get(lyk(m), {})
                g = lambda d, k: d.get(k) or 0.0
                ty_t = g(ty_m,"total"); ly_t = g(ly_m,"total")
                frows.append({
                    "Month": m.strftime("%b %Y"),
                    "LY Total": gbp(ly_t, net=show_net), "TY Total": gbp(ty_t, net=show_net),
                    "YOY": pct(delta_pct(ty_t, ly_t)) if ly_t else "—",
                    "TY Wet": gbp(g(ty_m,"wet"), net=show_net), "TY Dry": gbp(g(ty_m,"dry"), net=show_net),
                    "Mix": f"{g(ty_m,'wet_pct')*100:.0f}%W" if ty_t else "—",
                })
            st.dataframe(apply_style(pd.DataFrame(frows), chg=["YOY"]), use_container_width=True, hide_index=True)

        note("Fleur de Lys opened late Sep 2025, Manor House Inn Feb 2025, Kings Arms Nov 2024 — "
             "YOY comparisons for these venues reflect new openings. Like-for-like growth "
             "(Bell &amp; Crown, Grosvenor Arms, Pembroke Arms, Silver Plough) is on the Analytics tab.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — RESERVATIONS
# ─────────────────────────────────────────────────────────────────────────────
with tab_res:
    _tf, _tt, _lf, _lt, _custom = date_override("res", ty_from, ty_to)
    if _custom:
        _, _, ty_sr, ly_sr, _, _, _, months_list, month_labels = metrics_for(_tf, _tt, _lf, _lt)
        cov_ty = ty_sr["covers"] or 0; cov_ly = ly_sr["covers"] or 0
        ug_ty = ty_sr["unique_guests"] or 0; ug_ly = ly_sr["unique_guests"] or 0
    res_ty = ty_sr["reservations"] or 0; res_ly = ly_sr["reservations"] or 0
    rr_ty  = ty_sr["repeat_rate"]  or 0; rr_ly  = ly_sr["repeat_rate"]  or 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi_html("Reservations", f"{res_ty:,}", f"LY {res_ly:,}", delta_pct(res_ty, res_ly)), unsafe_allow_html=True)
    c2.markdown(kpi_html("Covers", f"{cov_ty:,}", f"LY {cov_ly:,}", delta_pct(cov_ty, cov_ly)), unsafe_allow_html=True)
    c3.markdown(kpi_html("Unique Guests", f"{ug_ty:,}", f"LY {ug_ly:,}", delta_pct(ug_ty, ug_ly)), unsafe_allow_html=True)
    c4.markdown(kpi_html("Repeat Visit Rate", f"{rr_ty*100:.1f}%", f"LY {rr_ly*100:.1f}%", delta_pct(rr_ty, rr_ly)), unsafe_allow_html=True)

    note("SevenRooms records reservation covers only — walk-ins not logged are excluded. "
         "Prior-year data includes a ResDiary migration export which may have inflated LY counts. "
         "FY2026-27 will be the first clean like-for-like year.")

    sec("Monthly Covers — This Year vs Last Year")
    ty_cov_m = [(ty_sr["by_month"].get(m.strftime("%Y-%m"), {}).get("covers") or 0) for m in months_list]
    ly_cov_m = [(ly_sr["by_month"].get(lyk(m), {}).get("covers") or 0) for m in months_list]

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
    all_sv = sorted(set(list(ty_sr["by_venue"]) + list(ly_sr["by_venue"])))
    srows = []
    for v in all_sv:
        ty_v = ty_sr["by_venue"].get(v, {}); ly_v = ly_sr["by_venue"].get(v, {})
        g = lambda d, k: d.get(k) or 0
        ty_c = g(ty_v,"covers"); ly_c = g(ly_v,"covers")
        srows.append({
            "Venue": v,
            "LY Res": f"{g(ly_v,'reservations'):,}", "TY Res": f"{g(ty_v,'reservations'):,}",
            "LY Covers": f"{ly_c:,}", "TY Covers": f"{ty_c:,}",
            "YOY Covers": pct(delta_pct(ty_c, ly_c)) if ly_c else "—",
            "TY Avg Party": f"{g(ty_v,'avg_covers'):.1f}",
        })
    st.dataframe(apply_style(pd.DataFrame(srows), chg=["YOY Covers"]), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — COMBINED
# ─────────────────────────────────────────────────────────────────────────────
with tab_comb:
    _tf, _tt, _lf, _lt, _custom = date_override("comb", ty_from, ty_to)
    if _custom:
        ty_ev, ly_ev, _, _, ty_wd, ly_wd, has_fb, months_list, month_labels = metrics_for(_tf, _tt, _lf, _lt)
        rev_ty = ty_ev["revenue"] or 0; rev_ly = ly_ev["revenue"] or 0
        fb_ty  = ty_wd["total"]   or 0; fb_ly  = ly_wd["total"]   or 0
    if not has_fb:
        st.info("Upload WEEKLY SALES & MARGINS.xlsx in the sidebar to see combined data.")
    else:
        ty_comb = rev_ty + fb_ty; ly_comb = rev_ly + fb_ly

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(kpi_html(f"Combined Revenue {'(Net)' if show_net else '(Gross)'}",
            gbp(ty_comb, net=show_net), f"LY {gbp(ly_comb, net=show_net)}", delta_pct(ty_comb, ly_comb)), unsafe_allow_html=True)
        ly_rooms_share = f"LY {rev_ly/ly_comb*100:.0f}%" if ly_comb else "—"
        ly_fb_share    = f"LY {fb_ly/ly_comb*100:.0f}%" if ly_comb else "—"
        c2.markdown(kpi_html("Rooms Share",
            f"{rev_ty/ty_comb*100:.0f}%" if ty_comb else "—",
            ly_rooms_share,
            delta_pct(rev_ty/ty_comb if ty_comb else 0, rev_ly/ly_comb if ly_comb else 0) if ty_comb and ly_comb else None,
        ), unsafe_allow_html=True)
        c3.markdown(kpi_html("F&B Share",
            f"{fb_ty/ty_comb*100:.0f}%" if ty_comb else "—",
            ly_fb_share,
            delta_pct(fb_ty/ty_comb if ty_comb else 0, fb_ly/ly_comb if ly_comb else 0) if ty_comb and ly_comb else None,
        ), unsafe_allow_html=True)
        nights    = ty_ev.get("nights") or 1
        ly_nights = ly_ev.get("nights") or 1
        c4.markdown(kpi_html("Total Rev per Room Night",
            gbp(ty_comb / nights, 2, net=show_net),
            f"LY {gbp(ly_comb / ly_nights, 2, net=show_net)}" if ly_comb else "—",
            delta_pct(ty_comb / nights, ly_comb / ly_nights) if ly_comb and ly_nights else None,
        ), unsafe_allow_html=True)

        sec("Revenue Split by Property — Rooms, Drinks & Food")
        venue_list = sorted(ROOMS_AND_FB)
        stk_r = [ty_ev["by_property"].get(v, {}).get("revenue") or 0 for v in venue_list]
        stk_w = [ty_wd["by_venue"].get(v, {}).get("wet") or 0 for v in venue_list]
        stk_d = [ty_wd["by_venue"].get(v, {}).get("dry") or 0 for v in venue_list]

        fig_stk = go.Figure()
        fig_stk.add_bar(name="Rooms",  x=venue_list, y=stk_r, marker_color=BRAND_GREEN,
                        text=[f"£{v:,.0f}" for v in stk_r], textposition="inside", textfont_size=8)
        fig_stk.add_bar(name="Drinks", x=venue_list, y=stk_w, marker_color=DRINKS_CLR,
                        text=[f"£{v:,.0f}" for v in stk_w], textposition="inside", textfont_size=8)
        fig_stk.add_bar(name="Food",   x=venue_list, y=stk_d, marker_color=FOOD_CLR,
                        text=[f"£{v:,.0f}" for v in stk_d], textposition="inside", textfont_size=8)
        fig_stk.update_layout(barmode="stack", height=420, yaxis_tickprefix="£", yaxis_tickformat=",.0f",
                              plot_bgcolor="white", paper_bgcolor="white",
                              font=dict(family="system-ui, sans-serif", size=11),
                              margin=dict(t=44, b=28, l=8, r=8),
                              legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_stk, use_container_width=True)

        sec("By Property")
        prop_rows = []
        for v in venue_list:
            ty_r2 = ty_ev["by_property"].get(v, {}).get("revenue") or 0
            ly_r2 = ly_ev["by_property"].get(v, {}).get("revenue") or 0
            ty_w2 = ty_wd["by_venue"].get(v, {}).get("wet") or 0
            ty_d2 = ty_wd["by_venue"].get(v, {}).get("dry") or 0
            ly_fb2= ly_wd["by_venue"].get(v, {}).get("total") or 0
            ty_t  = ty_r2 + ty_w2 + ty_d2; ly_t = ly_r2 + ly_fb2
            prop_rows.append({
                "Property": v,
                "TY Rooms": gbp(ty_r2, net=show_net), "TY Drinks": gbp(ty_w2, net=show_net),
                "TY Food": gbp(ty_d2, net=show_net), "TY Total": gbp(ty_t, net=show_net),
                "Rooms %": f"{ty_r2/ty_t*100:.0f}%" if ty_t else "—",
                "F&B %": f"{(ty_w2+ty_d2)/ty_t*100:.0f}%" if ty_t else "—",
                "LY Total": gbp(ly_t, net=show_net),
                "YOY": pct(delta_pct(ty_t, ly_t)) if ly_t else "—",
            })
        st.dataframe(apply_style(pd.DataFrame(prop_rows), chg=["YOY"]), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────
with tab_ana:
    _tf, _tt, _lf, _lt, _custom = date_override("ana", ty_from, ty_to)
    if _custom:
        ty_ev, ly_ev, _, _, ty_wd, ly_wd, has_fb, months_list, month_labels = metrics_for(_tf, _tt, _lf, _lt)
        rev_ty = ty_ev["revenue"] or 0; rev_ly = ly_ev["revenue"] or 0
    sec("Revenue Growth Decomposition")
    if has_fb:
        streams = {"Rooms": (rev_ty, rev_ly), "Drinks (Wet)": (ty_wd["wet"], ly_wd["wet"]), "Food (Dry)": (ty_wd["dry"], ly_wd["dry"])}
        total_delta = sum(t-l for t, l in streams.values())
        wf_labels, wf_deltas, gd_rows = [], [], []
        for label, (ty_v, ly_v) in streams.items():
            delta_v = ty_v - ly_v
            share = delta_v / total_delta * 100 if total_delta else 0
            gd_rows.append({"Stream": label, "LY": gbp(ly_v, net=show_net), "TY": gbp(ty_v, net=show_net),
                            "Change": ("+" if delta_v >= 0 else "") + gbp(abs(delta_v)),
                            "YOY": pct(delta_pct(ty_v, ly_v)) if ly_v else "—",
                            "Share of Growth": f"{share:+.0f}%"})
            wf_labels.append(label); wf_deltas.append(delta_v)

        col_wf, col_tbl = st.columns([2, 3])
        with col_wf:
            fig_wf = go.Figure(go.Waterfall(
                orientation="v", measure=["relative"]*3, x=wf_labels, y=wf_deltas,
                connector=dict(line=dict(color="#ccc", width=1)),
                increasing=dict(marker_color=BRAND_GREEN), decreasing=dict(marker_color=BAD),
                text=[f"£{abs(v):,.0f}" for v in wf_deltas], textposition="outside", textfont_size=10,
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

    sec("Seasonal Trading Index (100 = average month)")
    comb_m = {}
    for m in months_list:
        k = m.strftime("%Y-%m")
        r  = ty_ev["by_month"].get(k, {}).get("revenue") or 0
        fb = ty_wd["by_month"].get(k, {}).get("total") or 0 if has_fb else 0
        comb_m[k] = r + fb
    avg = sum(comb_m.values()) / len(comb_m) if comb_m else 1
    idx_vals   = [comb_m[m.strftime("%Y-%m")] / avg * 100 for m in months_list]
    idx_colors = [BRAND_GREEN if v >= 100 else BRAND_LIGHT for v in idx_vals]
    fig_idx = go.Figure(go.Bar(x=month_labels, y=idx_vals, marker_color=idx_colors,
                                text=[f"{v:.0f}" for v in idx_vals], textposition="outside"))
    fig_idx.add_hline(y=100, line_dash="dash", line_color="#999", annotation_text="100 = avg month")
    fig_idx.update_layout(height=340, showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                          font=dict(family="system-ui, sans-serif", size=11),
                          margin=dict(t=44, b=28, l=8, r=8),
                          xaxis=dict(showgrid=False), yaxis=dict(gridcolor="#f0f0f0"))
    st.plotly_chart(fig_idx, use_container_width=True)

    LFL = {"The Bell & Crown", "The Grosvenor Arms", "The Pembroke Arms", "The Silver Plough"}
    if has_fb:
        sec("Like-for-Like F&B Growth (Established Venues)")
        lfl_rows = []
        for v in sorted(LFL):
            ty_v = ty_wd["by_venue"].get(v, {}); ly_v = ly_wd["by_venue"].get(v, {})
            g = lambda d, k: d.get(k) or 0.0
            ty_t = g(ty_v,"total"); ly_t = g(ly_v,"total")
            lfl_rows.append({"Venue": v, "LY Total": gbp(ly_t, net=show_net), "TY Total": gbp(ty_t, net=show_net),
                             "LFL YOY": pct(delta_pct(ty_t, ly_t)) if ly_t else "—",
                             "TY Mix": f"{g(ty_v,'wet_pct')*100:.0f}%W / {(1-g(ty_v,'wet_pct'))*100:.0f}%D" if ty_t else "—"})
        lfl_ty = sum(ty_wd["by_venue"].get(v, {}).get("total") or 0 for v in LFL)
        lfl_ly = sum(ly_wd["by_venue"].get(v, {}).get("total") or 0 for v in LFL)
        lfl_rows.append({"Venue": "LFL TOTAL", "LY Total": gbp(lfl_ly, net=show_net), "TY Total": gbp(lfl_ty, net=show_net),
                         "LFL YOY": pct(delta_pct(lfl_ty, lfl_ly)) if lfl_ly else "—", "TY Mix": ""})
        st.dataframe(apply_style(pd.DataFrame(lfl_rows), chg=["LFL YOY"]), use_container_width=True, hide_index=True)

        sec("Venue Wet/Dry Benchmarking — TY vs LY")
        grp_avg    = ty_wd["wet_pct"]
        ly_grp_avg = ly_wd["wet_pct"] if ly_wd["total"] else None
        bench_rows = []
        for venue, dct in sorted(ty_wd["by_venue"].items(), key=lambda x: -x[1]["wet_pct"]):
            wp    = dct["wet_pct"]
            ly_v  = ly_wd["by_venue"].get(venue, {})
            ly_wp = ly_v.get("wet_pct") if ly_v.get("total") else None
            bench_rows.append({
                "Venue":      venue,
                "TY Wet %":   f"{wp*100:.1f}%",
                "LY Wet %":   f"{ly_wp*100:.1f}%" if ly_wp is not None else "—",
                "Change":     f"{(wp - ly_wp)*100:+.1f}%pts" if ly_wp is not None else "—",
                "TY Total":   gbp(dct["total"], net=show_net),
                "LY Total":   gbp(ly_v.get("total", 0), net=show_net) if ly_v.get("total") else "—",
                "YOY %":      pct(delta_pct(dct["total"], ly_v.get("total", 0))) if ly_v.get("total") else "—",
                "Character":  ("Very drinks-led" if wp>grp_avg+0.10 else "Drinks-led" if wp>grp_avg+0.03 else "Balanced" if abs(wp-grp_avg)<=0.03 else "Food-led"),
            })
        bench_rows.append({
            "Venue":    "GROUP TOTAL",
            "TY Wet %": f"{grp_avg*100:.1f}%",
            "LY Wet %": f"{ly_grp_avg*100:.1f}%" if ly_grp_avg else "—",
            "Change":   f"{(grp_avg - ly_grp_avg)*100:+.1f}%pts" if ly_grp_avg else "—",
            "TY Total": gbp(ty_wd["total"], net=show_net),
            "LY Total": gbp(ly_wd["total"], net=show_net) if ly_wd["total"] else "—",
            "YOY %":    pct(delta_pct(ty_wd["total"], ly_wd["total"])) if ly_wd["total"] else "—",
            "Character": "—",
        })
        st.dataframe(apply_style(pd.DataFrame(bench_rows), chg=["YOY %"]), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 8 — PROJECTIONS
# ─────────────────────────────────────────────────────────────────────────────
with tab_proj:
    good("<b>Methodology:</b> Occupancy held at this year's actual rate per property. "
         "ADR uplifted +5%. RevPAR = occupancy × projected ADR.")

    proj_months = month_iter(date(2026, 8, 1), date(2027, 7, 31))
    proj_rows, proj_total = [], 0.0
    proj_names, proj_vals, ty_r_vals = [], [], []

    for prop in sorted(EVIIVO_PROPERTIES.keys()):
        ty_p   = ty_ev["by_property"].get(prop, {})
        ty_occ = ty_p.get("occ") or 0.0; ty_adr = ty_p.get("adr") or 0.0
        rooms  = ROOM_COUNTS.get(prop, 0)
        if ty_occ == 0 or ty_adr == 0: continue
        proj_adr    = ty_adr * 1.05
        proj_revpar = ty_occ * proj_adr
        proj_rev    = sum(proj_revpar * rooms * calendar.monthrange(m.year, m.month)[1] for m in proj_months)
        proj_total += proj_rev
        ty_rev_act  = ty_p.get("revenue") or 0
        proj_names.append(prop); proj_vals.append(proj_rev); ty_r_vals.append(ty_rev_act)
        proj_rows.append({"Property": prop, "Rooms": rooms,
                          "TY Occ": f"{ty_occ*100:.1f}%", "TY ADR": gbp(ty_adr, 2),
                          "Proj ADR (+5%)": gbp(proj_adr, 2), "Proj RevPAR": gbp(proj_revpar, 2),
                          "Proj Revenue": gbp(proj_rev, net=show_net),
                          "TY Actual Rev": gbp(ty_rev_act, net=show_net) if ty_rev_act else "—"})

    if proj_rows:
        proj_rows.append({"Property": "GROUP TOTAL", "Rooms": "—", "TY Occ": "—",
                          "TY ADR": "—", "Proj ADR (+5%)": "—", "Proj RevPAR": "—",
                          "Proj Revenue": gbp(proj_total, net=show_net), "TY Actual Rev": "—"})
        c1, c2 = st.columns(2)
        c1.markdown(kpi_html(f"Projected FY2026-27 Revenue {'(Net)' if show_net else '(Gross)'}",
            gbp(proj_total, net=show_net), f"TY Actual {gbp(rev_ty, net=show_net)}", delta_pct(proj_total, rev_ty)), unsafe_allow_html=True)
        c2.markdown(kpi_html("ADR Uplift", "+5%", "On top of TY actuals", None), unsafe_allow_html=True)

        sec("TY Actual vs FY2026-27 Projected")
        st.plotly_chart(grouped_bar(proj_names, proj_vals, ty_r_vals, height=400,
                                    ty_name="Projected FY26-27", ly_name="TY Actual"), use_container_width=True)
        sec("Projection Detail")
        st.dataframe(pd.DataFrame(proj_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No actuals available yet — load data first.")

    note("Projections are indicative only. The Dog &amp; Gun January reflects a partial closure "
         "and may be revised upward for FY2026-27.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 9 — PHONE
# ─────────────────────────────────────────────────────────────────────────────
with tab_phone:
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
        prows.append({"Line": row["name"], "Total": f"{t:,}", "Answered": f"{t-m:,}",
                      "Missed": f"{m:,}", "Missed %": f"{mp*100:.0f}%",
                      "Target": f"{PHONE_TARGET*100:.0f}%", "vs Target": f"{vs*100:+.0f}%pts",
                      "Avg Wait": row.get("avg_wait","—"),
                      "Status": "✅ On target" if mp < PHONE_TARGET else ("🚨 Critical" if mp >= 0.40 else "⚠️ Above target")})
        grp_t += t; grp_m += m

    gp = grp_m / grp_t if grp_t else 0
    on_tgt = sum(1 for r in prows if "On target" in r["Status"])
    card_cls = "" if gp < PHONE_TARGET else ("warn" if gp < PHONE_TARGET*2 else "danger")

    c1, c2, c3 = st.columns(3)
    c1.markdown(kpi_html("Group Missed Call Rate", f"{gp*100:.0f}%", f"Target: {PHONE_TARGET*100:.0f}%",
        (gp-PHONE_TARGET)/PHONE_TARGET, inverse=True, card_class=card_cls), unsafe_allow_html=True)
    c2.markdown(kpi_html("Lines On Target", f"{on_tgt} / {len(prows)}", f"{PHONE_TARGET*100:.0f}% threshold", None), unsafe_allow_html=True)
    c3.markdown(kpi_html("Total Calls", f"{grp_t:,}", f"{grp_m:,} missed", None), unsafe_allow_html=True)

    sec("Missed Call Rate by Line")
    col_g, col_b = st.columns([1, 2])
    with col_g:
        st.plotly_chart(gauge_chart(gp, PHONE_TARGET, title="Group Missed Rate", height=260), use_container_width=True)
    with col_b:
        names   = [r["Line"] for r in prows]
        mp_vals = [int(r["Missed %"].replace("%","")) for r in prows]
        bar_clrs= [GOOD if v < PHONE_TARGET*100 else (WARN if v < 40 else BAD) for v in mp_vals]
        fig_ph  = go.Figure(go.Bar(x=mp_vals, y=names, orientation="h", marker_color=bar_clrs,
                                   text=[f"{v}%" for v in mp_vals], textposition="outside", textfont_size=10))
        fig_ph.add_vline(x=PHONE_TARGET*100, line_dash="dash", line_color=BRAND_GREEN,
                         annotation_text=f"Target {PHONE_TARGET*100:.0f}%", annotation_font_size=10)
        fig_ph.update_layout(height=max(340, len(names)*34+70), showlegend=False, xaxis_ticksuffix="%",
                             plot_bgcolor="white", paper_bgcolor="white",
                             font=dict(family="system-ui, sans-serif", size=11),
                             margin=dict(t=30, b=28, l=8, r=80),
                             xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
                             yaxis=dict(showgrid=False))
        fig_ph.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig_ph, use_container_width=True)

    prows.append({"Line":"GROUP TOTAL","Total":f"{grp_t:,}","Answered":f"{grp_t-grp_m:,}",
                  "Missed":f"{grp_m:,}","Missed %":f"{gp*100:.0f}%","Target":f"{PHONE_TARGET*100:.0f}%",
                  "vs Target":f"{(gp-PHONE_TARGET)*100:+.0f}%pts","Avg Wait":"—",
                  "Status":"✅ On target" if gp < PHONE_TARGET else "⚠️ Above target"})
    sec("Detail")
    st.dataframe(pd.DataFrame(prows), use_container_width=True, hide_index=True)
    st.caption("✅ On target = below 15%  ⚠️ Above target = 15–39%  🚨 Critical = 40%+")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 10 — REVIEWS
# ─────────────────────────────────────────────────────────────────────────────
with tab_rev:
    with st.spinner("Loading guest feedback…"):
        fb_raw = load_feedback_cached(ty_from, ty_to, ly_from, ly_to, tuple(sorted(_vm.items())))
    ty_fb_df = fb_raw.get("ty", pd.DataFrame())
    has_reviews = (not ty_fb_df.empty and "rating" in ty_fb_df.columns
                   and ty_fb_df["rating"].notna().any())

    if not has_reviews:
        st.markdown(
            '<div class="info-box">Guest feedback from SevenRooms will appear here once '
            'the post-dining survey feature is enabled on your venues.</div>',
            unsafe_allow_html=True,
        )
    else:
        ty_r = ty_fb_df[ty_fb_df["rating"].notna()].copy()
        ly_fb_df = fb_raw.get("ly", pd.DataFrame())
        ly_r = ly_fb_df[ly_fb_df["rating"].notna()].copy() if not ly_fb_df.empty else pd.DataFrame()

        ty_avg = float(ty_r["rating"].mean()); ly_avg = float(ly_r["rating"].mean()) if not ly_r.empty else 0.0
        ty_cnt = len(ty_r); ly_cnt = len(ly_r)
        ty_hi  = len(ty_r[ty_r["rating"] >= 4]); ty_lo = len(ty_r[ty_r["rating"] <= 2])

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(kpi_html("Avg Rating", f"{ty_avg:.2f} / 5", f"LY {ly_avg:.2f} / 5", delta_pct(ty_avg, ly_avg)), unsafe_allow_html=True)
        c2.markdown(kpi_html("Reviews Received", f"{ty_cnt:,}", f"LY {ly_cnt:,}", delta_pct(ty_cnt, ly_cnt)), unsafe_allow_html=True)
        ly_hi = len(ly_r[ly_r["rating"] >= 4]) if not ly_r.empty else 0
        ly_lo = len(ly_r[ly_r["rating"] <= 2]) if not ly_r.empty else 0
        c3.markdown(kpi_html("4–5 Star Reviews", f"{ty_hi:,}",
            f"LY {ly_hi:,}", delta_pct(ty_hi, ly_hi) if ly_hi else None), unsafe_allow_html=True)
        c4.markdown(kpi_html("1–2 Star Reviews", f"{ty_lo:,}",
            f"LY {ly_lo:,}", delta_pct(ty_lo, ly_lo) if ly_lo else None,
            inverse=True, card_class="warn" if ty_lo else ""), unsafe_allow_html=True)

        sec("Average Rating by Venue")
        vr = ty_r.groupby("venue_name")["rating"].agg(["mean","count"]).reset_index().sort_values("mean", ascending=True)
        v_colors = [GOOD if v >= 4.0 else (WARN if v >= 3.0 else BAD) for v in vr["mean"]]
        fig_vr = go.Figure(go.Bar(x=vr["mean"], y=vr["venue_name"], orientation="h", marker_color=v_colors,
                                   text=[f"{v:.2f}  ({int(c)} reviews)" for v, c in zip(vr["mean"], vr["count"])],
                                   textposition="outside", textfont_size=10))
        fig_vr.add_vline(x=ty_avg, line_dash="dot", line_color=BRAND_GREEN,
                         annotation_text=f"Avg {ty_avg:.2f}", annotation_font_size=10)
        fig_vr.update_layout(height=max(280, len(vr)*40+80),
                             xaxis=dict(range=[0, 5.6], showgrid=True, gridcolor="#f0f0f0"),
                             yaxis=dict(showgrid=False), showlegend=False,
                             plot_bgcolor="white", paper_bgcolor="white",
                             font=dict(family="system-ui, sans-serif", size=11),
                             margin=dict(t=20, b=20, l=8, r=100))
        st.plotly_chart(fig_vr, use_container_width=True)

        comments_df = ty_r[ty_r["comments"].str.len() > 5].sort_values("date", ascending=False)
        if not comments_df.empty:
            sec("Recent Guest Comments")
            show_n = st.slider("Comments to show", 5, min(100, len(comments_df)), 20, step=5)
            for _, row in comments_df.head(show_n).iterrows():
                stars = int(round(row["rating"])) if pd.notna(row["rating"]) else 0
                star_str = "★"*stars + "☆"*(5-stars)
                color_s  = GOOD if stars >= 4 else (WARN if stars >= 3 else BAD)
                st.markdown(
                    f'<div style="background:white;border-radius:8px;padding:0.7rem 1rem;'
                    f'margin-bottom:0.4rem;box-shadow:0 1px 6px rgba(0,0,0,0.06);border-left:4px solid {color_s};">'
                    f'<span style="color:{color_s};font-size:1rem;">{star_str}</span>'
                    f'&nbsp;&nbsp;<b style="font-size:0.78rem;color:{BRAND_GREEN};">{row.get("venue_name","")}</b>'
                    f'<span style="font-size:0.72rem;color:#bbb;margin-left:0.6rem;">{str(row.get("date",""))[:10]}</span>'
                    f'<div style="font-size:0.82rem;color:#444;margin-top:0.3rem;line-height:1.45;">{str(row.get("comments","")).strip()}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

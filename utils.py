# utils.py — Shared helpers, CSS, charts and data loading
import io
import calendar
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import (
    BRAND_GREEN, BRAND_LIGHT,
    EVIIVO_PROPERTIES, ROOM_COUNTS, ROOMS_AND_FB, PHONE_TARGET,
)
import data as D
import metrics as M

# ── Colours ───────────────────────────────────────────────────────────────────
MID_GREEN  = "#2d5a40"
GOLD       = "#c9973a"
DRINKS_CLR = "#3b82f6"
FOOD_CLR   = "#f97316"
GOOD       = "#16a34a"
WARN       = "#d97706"
BAD        = "#dc2626"

CHART_BASE = dict(
    plot_bgcolor="white", paper_bgcolor="white",
    font=dict(family="system-ui, sans-serif", size=11),
    margin=dict(t=44, b=28, l=8, r=8),
    legend=dict(orientation="h", y=1.1, x=0, font_size=11),
    xaxis=dict(showgrid=False),
    yaxis=dict(gridcolor="#f0f0f0", gridwidth=1),
)


# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown(f"""
<style>
.block-container {{ padding-top: 1.4rem !important; padding-bottom: 3rem; }}

.page-hdr {{
    background: linear-gradient(120deg, {BRAND_GREEN} 0%, {MID_GREEN} 100%);
    color: white; padding: 0.85rem 1.4rem; border-radius: 10px;
    margin-bottom: 1.2rem; display: flex; align-items: center;
    justify-content: space-between;
    box-shadow: 0 4px 20px rgba(28,56,41,0.18);
}}
.ph-brand {{ font-size: 1.35rem; font-weight: 900; letter-spacing: -0.03em; }}
.ph-title {{ font-size: 0.95rem; font-weight: 600; opacity: 0.9; margin-left: 0.75rem; }}
.ph-right {{ text-align: right; font-size: 0.74rem; opacity: 0.78; }}

.kpi-card {{
    background: white; border-radius: 12px; padding: 1rem 1.2rem;
    border-left: 5px solid {BRAND_GREEN};
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    margin-bottom: 0.3rem; min-height: 108px;
    display: flex; flex-direction: column; justify-content: space-between;
}}
.kpi-card.warn   {{ border-left-color: {WARN}; }}
.kpi-card.danger {{ border-left-color: {BAD};  }}
.kpi-label {{ font-size: 0.67rem; color: #999; text-transform: uppercase;
              letter-spacing: 0.08em; font-weight: 700; margin-bottom: 2px; }}
.kpi-value {{ font-size: 1.7rem; font-weight: 800; color: {BRAND_GREEN}; line-height: 1.1; }}
.kpi-footer {{ display: flex; justify-content: space-between; align-items: center;
               font-size: 0.72rem; margin-top: 4px; }}
.kpi-ly  {{ color: #bbb; }}
.d-pos   {{ color: {GOOD}; font-weight: 700; }}
.d-neg   {{ color: {BAD};  font-weight: 700; }}
.d-ipos  {{ color: {BAD};  font-weight: 700; }}
.d-ineg  {{ color: {GOOD}; font-weight: 700; }}

.sec-hdr {{
    font-size: 0.8rem; font-weight: 700; color: {BRAND_GREEN};
    text-transform: uppercase; letter-spacing: 0.07em;
    border-bottom: 2px solid {BRAND_LIGHT};
    padding: 0.45rem 0 0.2rem; margin: 1.1rem 0 0.65rem;
}}
.note-box {{
    background: #fffbeb; border-left: 4px solid {GOLD};
    padding: 0.6rem 1rem; border-radius: 6px;
    font-size: 0.79rem; color: #666; margin: 0.6rem 0; line-height: 1.55;
}}
.good-box {{
    background: #f0fdf4; border-left: 4px solid {GOOD};
    padding: 0.6rem 1rem; border-radius: 6px;
    font-size: 0.79rem; color: #166534; margin: 0.6rem 0; line-height: 1.55;
}}
.info-box {{
    background: #eff6ff; border-left: 4px solid {DRINKS_CLR};
    padding: 0.6rem 1rem; border-radius: 6px;
    font-size: 0.79rem; color: #1d4ed8; margin: 0.6rem 0; line-height: 1.55;
}}
[data-testid="stMetric"] {{
    background: white; border-radius: 10px; padding: 0.8rem 1rem;
    border-left: 4px solid {BRAND_GREEN};
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}}
[data-testid="stSidebar"] {{ background: #f5faf5; border-right: 1px solid #dde8dd; }}
[data-testid="stSidebarNav"] a {{ padding: 0.45rem 0.75rem; font-size: 0.85rem; }}
[data-testid="stSidebarNav"] a:hover {{ background: {BRAND_LIGHT}33; border-radius: 6px; }}
</style>
""", unsafe_allow_html=True)


def page_header(title, period_label="", ly_label=""):
    st.markdown(
        f'<div class="page-hdr">'
        f'<div><span class="ph-brand">chickpea.</span>'
        f'<span class="ph-title">{title}</span></div>'
        f'<div class="ph-right">{period_label}<br>{ly_label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def sec(text):
    st.markdown(f'<div class="sec-hdr">{text}</div>', unsafe_allow_html=True)


def note(text):
    st.markdown(f'<div class="note-box">{text}</div>', unsafe_allow_html=True)


def good(text):
    st.markdown(f'<div class="good-box">{text}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — shared across all pages
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown(
            f"<div style='color:{BRAND_GREEN};font-size:1rem;font-weight:900;"
            f"letter-spacing:-0.02em;margin:0.3rem 0 0.8rem;'>chickpea.</div>",
            unsafe_allow_html=True,
        )

        today   = date.today()
        fy_year = today.year if today.month >= 8 else today.year - 1

        if "ty_from" not in st.session_state:
            st.session_state["ty_from"] = date(fy_year, 8, 1)
        if "ty_to" not in st.session_state:
            st.session_state["ty_to"] = today.replace(day=1) - timedelta(days=1)
        if "show_net" not in st.session_state:
            st.session_state["show_net"] = False

        ty_from = st.date_input("Period from", st.session_state["ty_from"], key="ty_from")
        ty_to   = st.date_input("Period to",   st.session_state["ty_to"],   key="ty_to")
        ly_from = ty_from.replace(year=ty_from.year - 1)
        ly_to   = ty_to.replace(year=ty_to.year - 1)

        st.divider()
        st.markdown("**F&B Sales Data**")
        st.caption("Upload WEEKLY SALES & MARGINS.xlsx to unlock F&B, Combined & Analytics pages.")
        sales_file = st.file_uploader("", type=["xlsx"], label_visibility="collapsed")
        if sales_file is not None:
            st.session_state["sales_bytes"] = sales_file.read()

        st.divider()
        st.toggle("Show net (ex-VAT)", key="show_net")

        st.divider()
        if st.button("↺ Refresh Data", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.rerun()

        st.markdown(
            f"<div style='font-size:0.7rem;color:#aaa;margin-top:0.8rem;line-height:1.65;'>"
            f"<b>TY</b> {ty_from.strftime('%d %b %Y')} – {ty_to.strftime('%d %b %Y')}<br>"
            f"<b>LY</b> {ly_from.strftime('%d %b %Y')} – {ly_to.strftime('%d %b %Y')}</div>",
            unsafe_allow_html=True,
        )

    return ty_from, ty_to, ly_from, ly_to


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING (cached — shared across pages via same cache key)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def _load_raw(tf, tt, lf, lt):
    out = {}
    try:
        tok = D.get_ev_token()
        out["ty_ev"] = D.fetch_ev_bookings(tok, tf, tt)
        out["ly_ev"] = D.fetch_ev_bookings(tok, lf, lt)
    except Exception as e:
        out["ty_ev"] = pd.DataFrame(); out["ly_ev"] = pd.DataFrame()
        out["ev_err"] = str(e)
    try:
        st_tok = D.get_sr_token()
        vm = D.fetch_sr_venues(st_tok)
        out["ty_sr"] = D.fetch_sr_reservations(st_tok, vm, tf, tt)
        out["ly_sr"] = D.fetch_sr_reservations(st_tok, vm, lf, lt)
        out["vm"] = vm
    except Exception as e:
        out["ty_sr"] = pd.DataFrame(); out["ly_sr"] = pd.DataFrame()
        out["vm"] = {}; out["sr_err"] = str(e)
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def _load_feedback(tf, tt, lf, lt, vm_tuple):
    vm = dict(vm_tuple)
    out = {}
    try:
        tok = D.get_sr_token()
        out["ty"] = D.fetch_sr_feedback(tok, vm, tf, tt)
        out["ly"] = D.fetch_sr_feedback(tok, vm, lf, lt)
    except Exception as e:
        out["ty"] = pd.DataFrame(); out["ly"] = pd.DataFrame()
        out["err"] = str(e)
    return out


def load_data(ty_from, ty_to, ly_from, ly_to):
    """Load and compute all metrics. Returns a flat dict of all computed data."""
    with st.spinner("Loading data…"):
        raw = _load_raw(ty_from, ty_to, ly_from, ly_to)

    if "ev_err" in raw: st.sidebar.warning(f"Eviivo: {raw['ev_err'][:60]}")
    if "sr_err" in raw: st.sidebar.warning(f"SevenRooms: {raw['sr_err'][:60]}")

    ty_wds = ly_wds = pd.DataFrame()
    sb = st.session_state.get("sales_bytes")
    if sb:
        try:
            ty_wds = D.parse_sales_excel(io.BytesIO(sb), ty_from, ty_to)
            ly_wds = D.parse_sales_excel(io.BytesIO(sb), ly_from, ly_to)
        except Exception as e:
            st.sidebar.error(f"Sales file: {e}")

    return dict(
        ty_ev  = M.ev_metrics(raw.get("ty_ev", pd.DataFrame()), ty_from, ty_to),
        ly_ev  = M.ev_metrics(raw.get("ly_ev", pd.DataFrame()), ly_from, ly_to),
        ty_sr  = M.sr_metrics(raw.get("ty_sr", pd.DataFrame())),
        ly_sr  = M.sr_metrics(raw.get("ly_sr", pd.DataFrame())),
        ty_wd  = M.wds_metrics(ty_wds),
        ly_wd  = M.wds_metrics(ly_wds),
        vm     = raw.get("vm", {}),
        has_fb = M.wds_metrics(ty_wds)["total"] > 0,
    )


def load_feedback(ty_from, ty_to, ly_from, ly_to, vm):
    vm_tuple = tuple(sorted(vm.items()))
    return _load_feedback(ty_from, ty_to, ly_from, ly_to, vm_tuple)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def gbp(v, d=0, net=False):
    if v is None: return "N/A"
    if net: v = v / 1.2
    return f"£{v:,.{d}f}"

def pct(v, d=1):
    if v is None: return "N/A"
    return f"{'+'if v>=0 else ''}{v*100:.{d}f}%"

def delta_pct(ty, ly):
    if ly and ly != 0: return (ty - ly) / ly
    return None

def _delt_html(delta, inverse=False):
    if delta is None: return '<span style="color:#ccc">—</span>'
    p = delta * 100
    sym = "▲" if p >= 0 else "▼"
    cls = ("d-pos" if p >= 0 else "d-neg") if not inverse else ("d-ipos" if p >= 0 else "d-ineg")
    return f'<span class="{cls}">{sym}&nbsp;{abs(p):.1f}%</span>'

def kpi_html(title, ty_val, ly_str, delta, inverse=False, card_class=""):
    return (
        f'<div class="kpi-card {card_class}">'
        f'<div class="kpi-label">{title}</div>'
        f'<div class="kpi-value">{ty_val}</div>'
        f'<div class="kpi-footer">'
        f'<span class="kpi-ly">{ly_str}</span>'
        f'{_delt_html(delta, inverse)}'
        f'</div></div>'
    )

def month_iter(from_d, to_d):
    out, m = [], from_d.replace(day=1)
    while m <= to_d:
        out.append(m)
        nm = m.month % 12 + 1
        ny = m.year + (1 if m.month == 12 else 0)
        m = date(ny, nm, 1)
    return out

def _hchg(val, inverse=False):
    try:
        v = float(str(val).replace('%', '').replace('+', '').strip())
        if inverse: v = -v
        if v >= 10:   return f'background-color:#dcfce7;color:{GOOD};font-weight:600'
        elif v >= 0:  return f'background-color:#f0fdf4;color:{GOOD}'
        elif v >= -5: return f'background-color:#fef3c7;color:{WARN}'
        else:          return f'background-color:#fee2e2;color:{BAD};font-weight:600'
    except Exception: return ''

def apply_style(df, chg=(), inv=()):
    s = df.style.set_properties(**{'font-size': '0.82rem'})
    for c in chg:
        if c in df.columns: s = s.map(_hchg, subset=[c])
    for c in inv:
        if c in df.columns: s = s.map(lambda v: _hchg(v, inverse=True), subset=[c])
    return s

def ly_key(m_date):
    return m_date.replace(year=m_date.year - 1).strftime("%Y-%m")


# ══════════════════════════════════════════════════════════════════════════════
# CHART BUILDERS
# ══════════════════════════════════════════════════════════════════════════════
def _base(**kw):
    d = {**CHART_BASE, **kw}
    return d

def grouped_bar(xlabels, ty_vals, ly_vals, prefix="£", height=360,
                ty_name="This Year", ly_name="Last Year"):
    fig = go.Figure()
    fig.add_bar(name=ly_name, x=xlabels, y=ly_vals, marker_color=BRAND_LIGHT,
                text=[f"{prefix}{v:,.0f}" for v in ly_vals],
                textposition="outside", textfont_size=8)
    fig.add_bar(name=ty_name, x=xlabels, y=ty_vals, marker_color=BRAND_GREEN,
                text=[f"{prefix}{v:,.0f}" for v in ty_vals],
                textposition="outside", textfont_size=8)
    fig.update_layout(barmode="group", height=height,
                      yaxis_tickprefix=prefix, yaxis_tickformat=",.0f",
                      **_base())
    return fig

def line_chart(xlabels, ty_vals, ly_vals, prefix="£", height=320,
               ty_name="This Year", ly_name="Last Year"):
    fig = go.Figure()
    fig.add_scatter(name=ly_name, x=xlabels, y=ly_vals, mode="lines+markers",
                    line=dict(color=BRAND_LIGHT, width=2.5, dash="dash"),
                    marker=dict(size=6, color=BRAND_LIGHT))
    fig.add_scatter(name=ty_name, x=xlabels, y=ty_vals, mode="lines+markers",
                    line=dict(color=BRAND_GREEN, width=3),
                    marker=dict(size=7, color=BRAND_GREEN))
    fig.update_layout(height=height, yaxis_tickprefix=prefix,
                      yaxis_tickformat=",.0f", **_base())
    return fig

def hbar_chart(labels, values, prefix="£", height=None, colors=None, pct_fmt=False):
    if height is None: height = max(220, len(labels) * 38 + 70)
    texts = [f"{v:.1f}%" for v in values] if pct_fmt else [f"{prefix}{v:,.0f}" for v in values]
    c = colors or [BRAND_GREEN] * len(labels)
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color=c,
                           text=texts, textposition="outside", textfont_size=10))
    fig.update_layout(height=height, showlegend=False,
                      **_base(xaxis=dict(showgrid=True, gridcolor="#f0f0f0")))
    fig.update_yaxes(categoryorder="total ascending", showgrid=False)
    return fig

def donut_chart(labels, values, colors=None, height=280, center_text=""):
    if colors is None:
        colors = [BRAND_GREEN, BRAND_LIGHT, "#4a9060", GOLD, DRINKS_CLR]
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.58,
                           marker=dict(colors=colors[:len(labels)]),
                           textinfo="label+percent", textfont_size=11))
    if center_text:
        fig.add_annotation(text=center_text, x=0.5, y=0.5, showarrow=False,
                           font=dict(size=13, color=BRAND_GREEN))
    fig.update_layout(height=height, paper_bgcolor="white", showlegend=False,
                      font=dict(family="system-ui, sans-serif"),
                      margin=dict(t=20, b=10, l=10, r=10))
    return fig

def stacked_bar(xlabels, wet_vals, dry_vals, height=360):
    fig = go.Figure()
    fig.add_bar(name="Dry (Food)", x=xlabels, y=dry_vals, marker_color=FOOD_CLR,
                text=[f"£{v:,.0f}" for v in dry_vals],
                textposition="inside", textfont_size=8)
    fig.add_bar(name="Wet (Drinks)", x=xlabels, y=wet_vals, marker_color=DRINKS_CLR,
                text=[f"£{v:,.0f}" for v in wet_vals],
                textposition="inside", textfont_size=8)
    fig.update_layout(barmode="stack", height=height,
                      yaxis_tickprefix="£", yaxis_tickformat=",.0f", **_base())
    return fig

def gauge_chart(value, target, title="", height=240):
    color = GOOD if value < target else (WARN if value < target * 1.5 else BAD)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value * 100,
        number={"suffix": "%", "font": {"size": 38, "color": color}},
        gauge={
            "axis": {"range": [0, 80], "ticksuffix": "%", "tickfont_size": 9},
            "bar": {"color": color, "thickness": 0.65},
            "steps": [
                {"range": [0, target*100],       "color": "#dcfce7"},
                {"range": [target*100, target*150], "color": "#fef3c7"},
                {"range": [target*150, 80],       "color": "#fee2e2"},
            ],
            "threshold": {"line": {"color": BRAND_GREEN, "width": 3}, "value": target*100},
        },
        title={"text": title, "font": {"size": 13}},
    ))
    fig.update_layout(height=height, paper_bgcolor="white",
                      margin=dict(t=30, b=10, l=20, r=20),
                      font=dict(family="system-ui, sans-serif"))
    return fig

# metrics.py — Metrics computation for Chickpea Annual Performance Report

from datetime import date, timedelta

import pandas as pd

from config import EVIIVO_PROPERTIES, ROOM_COUNTS, ROOM_COUNT_HISTORY


# ══════════════════════════════════════════════════════════════════════════════
# ROOM COUNT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_room_count(property_name, for_date):
    """Return room count for a property on a given date, respecting history."""
    count = ROOM_COUNTS.get(property_name, 0)
    for prop, change_date_str, rooms_before in ROOM_COUNT_HISTORY:
        change_date = (
            date.fromisoformat(change_date_str)
            if isinstance(change_date_str, str)
            else change_date_str
        )
        if prop == property_name and for_date < change_date:
            count = rooms_before
    return count


def available_nights(property_name, from_d, to_d):
    """
    Total available room nights for a property across [from_d, to_d].
    Steps through each calendar month to handle room count changes correctly.
    Returns 0 if the property has no rooms configured.
    """
    has_history = any(p == property_name for p, _, _ in ROOM_COUNT_HISTORY)
    if ROOM_COUNTS.get(property_name, 0) == 0 and not has_history:
        return 0

    total   = 0
    m_start = from_d.replace(day=1)
    while m_start <= to_d:
        if m_start.month == 12:
            m_end  = date(m_start.year + 1, 1, 1) - timedelta(days=1)
            next_m = date(m_start.year + 1, 1, 1)
        else:
            m_end  = date(m_start.year, m_start.month + 1, 1) - timedelta(days=1)
            next_m = date(m_start.year, m_start.month + 1, 1)

        seg_start = max(m_start, from_d)
        seg_end   = min(m_end, to_d)
        seg_days  = (seg_end - seg_start).days + 1

        count  = _get_room_count(property_name, m_start)
        total += count * seg_days
        m_start = next_m
    return total


def _group_available_nights(from_d, to_d):
    return sum(available_nights(p, from_d, to_d) for p in EVIIVO_PROPERTIES)


# ══════════════════════════════════════════════════════════════════════════════
# EVIIVO METRICS
# ══════════════════════════════════════════════════════════════════════════════

def ev_metrics(df, from_d, to_d):
    """
    Compute Eviivo room metrics for a single period.
    Returns dict with keys:
        revenue, stays, nights, adr, alos, occ, revpar,
        by_property, by_month, channel_mix
    """
    if df is None or df.empty:
        return _empty_ev_metrics()

    conf = df[df["status"] == "Confirmed"].copy()
    if conf.empty:
        return _empty_ev_metrics()

    conf["month"] = pd.to_datetime(conf["checkin"]).dt.to_period("M")

    total_rev    = conf["revenue"].sum()
    total_stays  = len(conf)
    total_nights = conf["nights"].sum()
    adr          = total_rev    / total_nights  if total_nights > 0 else 0
    alos         = total_nights / total_stays   if total_stays  > 0 else 0

    avail_overall  = _group_available_nights(from_d, to_d)
    occ_overall    = total_nights / avail_overall if avail_overall > 0 else None
    revpar_overall = total_rev    / avail_overall if avail_overall > 0 else None

    # ── By property ──────────────────────────────────────────────────────────
    by_property = {}
    for prop in EVIIVO_PROPERTIES:
        pdf    = conf[conf["venue_name"] == prop]
        pr     = pdf["revenue"].sum()
        ps     = len(pdf)
        pn     = pdf["nights"].sum()
        pavail = available_nights(prop, from_d, to_d)
        by_property[prop] = {
            "revenue": float(pr),
            "stays":   int(ps),
            "nights":  int(pn),
            "adr":     float(pr / pn)     if pn > 0     else 0.0,
            "alos":    float(pn / ps)     if ps > 0     else 0.0,
            "occ":     float(pn / pavail) if pavail > 0 else None,
            "revpar":  float(pr / pavail) if pavail > 0 else None,
        }

    # ── By month ─────────────────────────────────────────────────────────────
    by_month = {}
    for m, mdf in conf.groupby("month"):
        month_str = str(m)  # e.g. "2025-08"
        m_start   = m.start_time.date()
        m_end     = m.end_time.date()
        m_avail   = _group_available_nights(m_start, m_end)
        mr = mdf["revenue"].sum()
        ms = len(mdf)
        mn = mdf["nights"].sum()
        by_month[month_str] = {
            "revenue": float(mr),
            "stays":   int(ms),
            "nights":  int(mn),
            "adr":     float(mr / mn)      if mn > 0      else 0.0,
            "alos":    float(mn / ms)      if ms > 0      else 0.0,
            "occ":     float(mn / m_avail) if m_avail > 0 else None,
            "revpar":  float(mr / m_avail) if m_avail > 0 else None,
        }

    # ── Channel mix ──────────────────────────────────────────────────────────
    channel_mix = conf.groupby("channel")["booking_ref"].count().to_dict()

    return {
        "revenue":      float(total_rev),
        "stays":        int(total_stays),
        "nights":       int(total_nights),
        "adr":          float(adr),
        "alos":         float(alos),
        "occ":          float(occ_overall)    if occ_overall    is not None else None,
        "revpar":       float(revpar_overall) if revpar_overall is not None else None,
        "by_property":  by_property,
        "by_month":     by_month,
        "channel_mix":  channel_mix,
    }


def _empty_ev_metrics():
    return {
        "revenue": 0.0, "stays": 0, "nights": 0,
        "adr": 0.0, "alos": 0.0, "occ": None, "revpar": None,
        "by_property": {
            p: {"revenue": 0.0, "stays": 0, "nights": 0,
                "adr": 0.0, "alos": 0.0, "occ": None, "revpar": None}
            for p in EVIIVO_PROPERTIES
        },
        "by_month":    {},
        "channel_mix": {},
    }


# ══════════════════════════════════════════════════════════════════════════════
# SEVENROOMS METRICS
# ══════════════════════════════════════════════════════════════════════════════

def sr_metrics(df):
    """
    Compute SevenRooms F&B metrics for a single period.
    Returns dict with keys:
        reservations, covers, avg_covers, unique_guests, repeat_guests,
        repeat_rate, avg_visits, by_venue, by_month, freq_dist
    """
    if df is None or df.empty:
        return _empty_sr_metrics()

    df = df.copy()
    df["month"] = pd.to_datetime(df["date"]).dt.to_period("M")

    total_res    = len(df)
    total_covers = int(df["max_guests"].sum())
    avg_covers   = total_covers / total_res if total_res > 0 else 0.0

    guest_visits  = df.groupby("guest_key").size()
    unique_guests = len(guest_visits)
    repeat_guests = int((guest_visits > 1).sum())
    repeat_rate   = repeat_guests / unique_guests if unique_guests > 0 else 0.0
    avg_visits    = float(guest_visits.mean()) if len(guest_visits) > 0 else 0.0

    freq_dist = {
        "1 visit":    int((guest_visits == 1).sum()),
        "2 visits":   int((guest_visits == 2).sum()),
        "3-5 visits": int(((guest_visits >= 3) & (guest_visits <= 5)).sum()),
        "6+ visits":  int((guest_visits >= 6).sum()),
    }

    # ── By venue ─────────────────────────────────────────────────────────────
    by_venue = {}
    for venue, vdf in df.groupby("venue_name"):
        vg = vdf.groupby("guest_key").size()
        vr = int(vdf["max_guests"].sum())
        vs = len(vdf)
        by_venue[str(venue)] = {
            "reservations":  vs,
            "covers":        vr,
            "avg_covers":    float(vr / vs) if vs > 0 else 0.0,
            "unique_guests": int(len(vg)),
            "repeat_guests": int((vg > 1).sum()),
            "repeat_rate":   float((vg > 1).sum() / len(vg)) if len(vg) > 0 else 0.0,
        }

    # ── By month ─────────────────────────────────────────────────────────────
    by_month = {}
    for m, mdf in df.groupby("month"):
        month_str = str(m)
        mc = int(mdf["max_guests"].sum())
        ms = len(mdf)
        mg = int(mdf["guest_key"].nunique())
        by_month[month_str] = {
            "reservations":  ms,
            "covers":        mc,
            "avg_covers":    float(mc / ms) if ms > 0 else 0.0,
            "unique_guests": mg,
        }

    return {
        "reservations": total_res,
        "covers":       total_covers,
        "avg_covers":   avg_covers,
        "unique_guests": unique_guests,
        "repeat_guests": repeat_guests,
        "repeat_rate":   repeat_rate,
        "avg_visits":    avg_visits,
        "by_venue":      by_venue,
        "by_month":      by_month,
        "freq_dist":     freq_dist,
    }


def _empty_sr_metrics():
    return {
        "reservations": 0, "covers": 0, "avg_covers": 0.0,
        "unique_guests": 0, "repeat_guests": 0,
        "repeat_rate": 0.0, "avg_visits": 0.0,
        "by_venue": {}, "by_month": {},
        "freq_dist": {"1 visit": 0, "2 visits": 0, "3-5 visits": 0, "6+ visits": 0},
    }


# ══════════════════════════════════════════════════════════════════════════════
# WET / DRY SALES METRICS
# ══════════════════════════════════════════════════════════════════════════════

def wds_metrics(df):
    """
    Aggregate wet/dry sales into totals, by-venue, and by-month.
    Returns dict with keys:
        wet, dry, total, wet_pct, dry_pct, by_venue, by_month
    """
    if df is None or df.empty:
        return _empty_wds_metrics()

    df = df.copy()
    df["month"] = pd.to_datetime(df["week_date"]).dt.to_period("M")

    total_wet = float(df["wet"].sum())
    total_dry = float(df["dry"].sum())
    total     = total_wet + total_dry

    # ── By venue ─────────────────────────────────────────────────────────────
    by_venue = {}
    for venue, vdf in df.groupby("venue_name"):
        vw = float(vdf["wet"].sum())
        vd = float(vdf["dry"].sum())
        vt = vw + vd
        by_venue[str(venue)] = {
            "wet":     vw,
            "dry":     vd,
            "total":   vt,
            "wet_pct": vw / vt if vt > 0 else 0.0,
            "dry_pct": vd / vt if vt > 0 else 0.0,
        }

    # ── By month ─────────────────────────────────────────────────────────────
    by_month = {}
    for m, mdf in df.groupby("month"):
        mw = float(mdf["wet"].sum())
        md = float(mdf["dry"].sum())
        mt = mw + md
        by_month[str(m)] = {
            "wet":     mw,
            "dry":     md,
            "total":   mt,
            "wet_pct": mw / mt if mt > 0 else 0.0,
            "dry_pct": md / mt if mt > 0 else 0.0,
        }

    return {
        "wet":     total_wet,
        "dry":     total_dry,
        "total":   total,
        "wet_pct": total_wet / total if total > 0 else 0.0,
        "dry_pct": total_dry / total if total > 0 else 0.0,
        "by_venue":  by_venue,
        "by_month":  by_month,
    }


def _empty_wds_metrics():
    return {
        "wet": 0.0, "dry": 0.0, "total": 0.0,
        "wet_pct": 0.0, "dry_pct": 0.0,
        "by_venue": {}, "by_month": {},
    }

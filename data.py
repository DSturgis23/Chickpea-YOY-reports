# data.py — Data fetching functions for Chickpea Annual Performance Report
# Pulls from Eviivo API (rooms) and SevenRooms API (F&B reservations).
# parse_sales_excel() reads a BytesIO from st.file_uploader.

import re
import io as _io
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import pandas as pd
import requests

from config import (
    get_eviivo_creds, get_sr_creds,
    EVIIVO_PROPERTIES, SALES_VENUE_MAP,
    TEVALIS_API_URL, TEVALIS_DEV_ID, TEVALIS_GUID,
    TEVALIS_GUID2, TEVALIS_COMPANY, TEVALIS_SITES,
)

CHUNK_DAYS = 90  # days per Eviivo request chunk (larger = fewer round trips)


# ══════════════════════════════════════════════════════════════════════════════
# EVIIVO
# ══════════════════════════════════════════════════════════════════════════════

def get_ev_token():
    """Obtain an Eviivo API bearer token."""
    creds = get_eviivo_creds()
    resp = requests.post(
        creds["auth_url"],
        data={
            "grant_type":    "client_credentials",
            "client_id":     creds["client_id"],
            "client_secret": creds["client_secret"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _ev_headers(token):
    creds = get_eviivo_creds()
    return {
        "Authorization":   f"Bearer {token}",
        "X-Auth-ClientId": creds["client_id"],
        "Content-Type":    "application/json",
    }


def _ev_fetch_chunk(token, shortname, chunk_from, chunk_to):
    creds = get_eviivo_creds()
    resp = requests.get(
        f"{creds['api_url']}/property/{shortname}/bookings",
        headers=_ev_headers(token),
        params={
            "request.CheckInFrom": chunk_from.strftime("%Y-%m-%d"),
            "request.CheckInTo":   chunk_to.strftime("%Y-%m-%d"),
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("Bookings", data if isinstance(data, list) else [])


def _normalise_channel(raw):
    cl = str(raw or "").lower()
    if not cl or cl in ("none", "unknown", ""):
        return "Unknown"
    if any(x in cl for x in ("direct", "phone", "walk", "email", "reception", "website", "own")):
        return "Direct"
    if any(x in cl for x in ("booking.com", "expedia", "airbnb", "ota", "tripadvisor",
                              "laterooms", "hotels.com", "agoda", "hostelworld")):
        return "OTA"
    return raw.strip() or "Other"


def _fetch_ev_venue(token, venue_name, shortname, from_date, to_date):
    """Fetch all bookings for a single Eviivo property. Returns list of record dicts."""
    records = []
    seen = {}
    chunk_start = from_date
    while chunk_start <= to_date:
        chunk_end = min(chunk_start + timedelta(days=CHUNK_DAYS - 1), to_date)
        try:
            raw = _ev_fetch_chunk(token, shortname, chunk_start, chunk_end)
        except Exception:
            raw = []
        for rec in raw:
            b   = rec.get("Booking", {})
            ref = b.get("BookingReference", "")
            if not ref or ref in seen:
                continue
            seen[ref] = True
            checkin_str  = b.get("CheckinDate", "")
            checkout_str = b.get("CheckoutDate", "")
            try:
                checkin = date.fromisoformat(checkin_str[:10])
            except Exception:
                checkin = chunk_start
            try:
                checkout = date.fromisoformat(checkout_str[:10])
            except Exception:
                checkout = checkin + timedelta(days=1)
            nights  = max((checkout - checkin).days, 1)
            revenue = float(
                b.get("Total", {}).get("GrossAmount", {}).get("Value", 0) or 0
            )
            channel_raw = (
                b.get("BookingSource") or b.get("Source") or
                b.get("DistributionChannel") or b.get("Channel") or ""
            )
            records.append({
                "venue_name":  venue_name,
                "booking_ref": ref,
                "checkin":     checkin,
                "checkout":    checkout,
                "nights":      nights,
                "revenue":     revenue,
                "status":      "Cancelled" if b.get("Cancelled") else "Confirmed",
                "channel":     _normalise_channel(channel_raw),
            })
        chunk_start = chunk_end + timedelta(days=1)
    return records


def fetch_ev_bookings(token, from_date, to_date):
    """
    Fetch all bookings for all Eviivo properties sequentially.
    Returns DataFrame with columns:
        venue_name, booking_ref, checkin, checkout, nights, revenue, status, channel
    """
    all_records = []
    for vname, sname in EVIIVO_PROPERTIES.items():
        all_records.extend(_fetch_ev_venue(token, vname, sname, from_date, to_date))

    return pd.DataFrame(all_records) if all_records else pd.DataFrame(
        columns=["venue_name", "booking_ref", "checkin", "checkout",
                 "nights", "revenue", "status", "channel"]
    )


# ══════════════════════════════════════════════════════════════════════════════
# SEVENROOMS
# ══════════════════════════════════════════════════════════════════════════════

def get_sr_token():
    """Obtain a SevenRooms API token."""
    creds = get_sr_creds()
    resp = requests.post(
        f"{creds['api_url']}/auth",
        data={
            "client_id":     creds["client_id"],
            "client_secret": creds["client_secret"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    token = (
        data.get("data", {}).get("token") or
        data.get("token") or
        data.get("access_token")
    )
    if not token:
        raise ValueError(f"No token in SevenRooms auth response: {data}")
    return token


def fetch_sr_venues(token):
    """
    Fetch all SevenRooms venues.
    Returns {venue_id: venue_name}.
    """
    creds = get_sr_creds()
    headers = {"Authorization": token, "Content-Type": "application/json"}
    venue_map = {}
    cursor = None
    while True:
        params = {}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(
            f"{creds['api_url']}/venues",
            headers=headers,
            params=params or None,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        for v in data.get("data", {}).get("results", []):
            venue_map[v["id"]] = v.get("name", "").strip()
        cursor = data.get("data", {}).get("cursor")
        if not cursor:
            break
    return venue_map


def fetch_sr_reservations(token, venue_map, from_date, to_date):
    """
    Fetch all SevenRooms reservations with visit date in [from_date, to_date].
    Returns DataFrame with columns:
        venue_name, guest_key, guest_name, email, max_guests, date,
        reservation_type, lifetime_visits
    """
    creds = get_sr_creds()
    headers = {"Authorization": token, "Content-Type": "application/json"}
    records = []
    cursor  = None
    params  = {
        "from_date": from_date.strftime("%Y-%m-%d"),
        "to_date":   to_date.strftime("%Y-%m-%d"),
        "limit":     400,
    }

    while True:
        if cursor:
            params["cursor"] = cursor
        try:
            resp = requests.get(
                f"{creds['api_url']}/reservations",
                headers=headers,
                params=params,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            break

        results = data.get("data", {}).get("results", [])
        for r in results:
            status = str(r.get("status_display") or r.get("status") or "").strip()
            if status.lower() in ("canceled", "cancelled", "no show", "no-show"):
                continue

            email = str(r.get("email", "") or "").lower().strip()
            fname = str(r.get("first_name", "") or "").strip()
            lname = str(r.get("last_name", "") or "").strip()
            guest_name_full = f"{fname} {lname}".strip()

            # Skip Eviivo room placeholder reservations synced into SevenRooms
            if re.match(r'(?i)^room\s*\d+$', guest_name_full):
                continue

            guest_key = email if email else guest_name_full.lower().strip()

            client_obj = r.get("client") or {}
            if not isinstance(client_obj, dict):
                client_obj = {}
            lifetime_visits = (
                r.get("visit_count") or client_obj.get("visit_count") or
                client_obj.get("total_visits") or client_obj.get("num_visits") or 0
            )
            try:
                lifetime_visits = int(lifetime_visits)
            except Exception:
                lifetime_visits = 0

            visit_date_str = str(r.get("date", "") or "")
            try:
                visit_date = date.fromisoformat(visit_date_str[:10])
            except Exception:
                continue  # skip if no parseable date

            venue_id   = r.get("venue_id", "")
            venue_name = venue_map.get(venue_id, r.get("venue_name", "Unknown"))

            arrived = r.get("arrived_guests")
            covers = int(arrived) if arrived else max(int(r.get("max_guests") or 1), 1)

            records.append({
                "venue_name":       venue_name,
                "guest_key":        guest_key if guest_key else "unknown",
                "guest_name":       f"{fname} {lname}".strip() or "Unknown",
                "email":            email,
                "max_guests":       covers,
                "date":             visit_date,
                "reservation_type": str(r.get("reservation_type", "") or ""),
                "lifetime_visits":  lifetime_visits,
            })

        cursor = data.get("data", {}).get("cursor")
        if not cursor:
            break

    return pd.DataFrame(records) if records else pd.DataFrame(
        columns=["venue_name", "guest_key", "guest_name", "email",
                 "max_guests", "date", "reservation_type", "lifetime_visits"]
    )


# ══════════════════════════════════════════════════════════════════════════════
# SEVENROOMS FEEDBACK
# ══════════════════════════════════════════════════════════════════════════════

def fetch_sr_feedback(token, venue_map, from_date, to_date):
    """
    Fetch SevenRooms reservation feedback for all venues.
    Calls /venues/{venue_id}/feedback for each venue in venue_map.
    Returns DataFrame with columns:
        venue_name, date, rating, food_rating, service_rating,
        ambiance_rating, comments, guest_name
    """
    creds   = get_sr_creds()
    headers = {"Authorization": token, "Content-Type": "application/json"}
    records = []

    for venue_id, venue_name in venue_map.items():
        try:
            resp = requests.get(
                f"{creds['api_url']}/venues/{venue_id}/feedback",
                headers=headers,
                params={
                    "start_date": from_date.strftime("%Y-%m-%d"),
                    "end_date":   to_date.strftime("%Y-%m-%d"),
                },
                timeout=30,
            )
            if not resp.ok:
                continue
            data     = resp.json()
            feedbacks = (
                data.get("data", {}).get("reservation_feedback", [])
                if isinstance(data.get("data"), dict)
                else data.get("data", []) if isinstance(data.get("data"), list)
                else []
            )
            for fb in feedbacks:
                if not isinstance(fb, dict):
                    continue
                raw_date = fb.get("date") or fb.get("created_date") or ""
                try:
                    fb_date = date.fromisoformat(str(raw_date)[:10])
                except Exception:
                    fb_date = None

                def _r(key):
                    v = fb.get(key)
                    try:
                        return float(v) if v is not None else None
                    except Exception:
                        return None

                records.append({
                    "venue_name":      venue_name,
                    "date":            fb_date,
                    "rating":          _r("rating") or _r("overall_rating") or _r("total_rating"),
                    "food_rating":     _r("food_rating"),
                    "service_rating":  _r("service_rating"),
                    "ambiance_rating": _r("ambiance_rating") or _r("ambience_rating"),
                    "comments":        str(fb.get("comments") or fb.get("feedback_text") or "").strip(),
                    "guest_name":      str(fb.get("client_name") or fb.get("guest_name") or "").strip(),
                })
        except Exception:
            continue

    return pd.DataFrame(records) if records else pd.DataFrame(
        columns=["venue_name", "date", "rating", "food_rating", "service_rating",
                 "ambiance_rating", "comments", "guest_name"]
    )


# ══════════════════════════════════════════════════════════════════════════════
# WET / DRY SALES  (WEEKLY SALES & MARGINS.xlsx)
# ══════════════════════════════════════════════════════════════════════════════

def parse_sales_excel(uploaded_file, from_date, to_date):
    """
    Parse a WEEKLY SALES & MARGINS.xlsx BytesIO object.
    SALES sheet structure:
      - Row index 3 (row 4) has date headers from column index 3 onwards.
      - Each venue block: row where col[0] = VENUE_NAME, col[2] = 'WET',
        followed immediately by the DRY row.
    Returns DataFrame with columns: venue_name, week_date, wet, dry, total
    """
    import datetime as _dtmod
    import openpyxl

    wb = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
    ws = wb["SALES"]
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    # Row index 3 holds date headers from col index 3 onward
    header    = all_rows[3]
    col_dates = {}
    for i, v in enumerate(header):
        if i < 3 or v is None:
            continue
        if isinstance(v, _dtmod.datetime):
            col_dates[i] = v.date()
        elif isinstance(v, _dtmod.date):
            col_dates[i] = v
        elif isinstance(v, str) and len(v) == 10 and v[2] == "/":
            try:
                col_dates[i] = _dtmod.datetime.strptime(v, "%d/%m/%Y").date()
            except ValueError:
                pass

    records = []
    for idx, row in enumerate(all_rows):
        venue_raw = str(row[0] or "").strip()
        if venue_raw not in SALES_VENUE_MAP or row[2] != "WET":
            continue
        venue_display = SALES_VENUE_MAP[venue_raw]
        dry_row = all_rows[idx + 1] if idx + 1 < len(all_rows) else []

        for col_i, col_date in col_dates.items():
            if col_date < from_date or col_date > to_date:
                continue
            w_raw = row[col_i]     if col_i < len(row)     else None
            d_raw = dry_row[col_i] if col_i < len(dry_row) else None
            wet   = float(w_raw) if isinstance(w_raw, (int, float)) else 0.0
            dry   = float(d_raw) if isinstance(d_raw, (int, float)) else 0.0
            records.append({
                "venue_name": venue_display,
                "week_date":  col_date,
                "wet":        wet,
                "dry":        dry,
                "total":      wet + dry,
            })

    return (
        pd.DataFrame(records) if records
        else pd.DataFrame(columns=["venue_name", "week_date", "wet", "dry", "total"])
    )


# ══════════════════════════════════════════════════════════════════════════════
# TEVALIS EPOS
# ══════════════════════════════════════════════════════════════════════════════

_TEV_HEADERS = {
    "DevID":     TEVALIS_DEV_ID,
    "GUID":      TEVALIS_GUID,
    "GUID2":     TEVALIS_GUID2,
    "CompanyID": TEVALIS_COMPANY,
}


def _tev_summary(site_id, from_date, to_date):
    """
    Call /Reporting/v1/Enterprise/GetTradingSummaryReport for one site + period.
    Returns list of row dicts (Beverage / Food / etc).
    """
    resp = requests.get(
        f"{TEVALIS_API_URL}/Reporting/v1/Enterprise/GetTradingSummaryReport",
        headers=_TEV_HEADERS,
        params={
            "uriCommand.siteIDs":  site_id,
            "uriCommand.dateFrom": from_date.isoformat(),
            "uriCommand.dateTo":   to_date.isoformat(),
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json() if isinstance(resp.json(), list) else []


def fetch_tevalis_sales(from_date, to_date):
    """
    Fetch Tevalis EPOS sales for all configured sites across [from_date, to_date].
    Breaks the range into monthly chunks to avoid timeouts.
    Returns DataFrame with columns:
        venue_name, month, wet, dry, total, covers, transactions
    All revenue values are gross (inc. VAT).
    """
    records = []

    # Build list of month chunks
    chunks = []
    m_start = from_date.replace(day=1)
    while m_start <= to_date:
        if m_start.month == 12:
            m_end  = date(m_start.year + 1, 1, 1) - timedelta(days=1)
            next_m = date(m_start.year + 1, 1, 1)
        else:
            m_end  = date(m_start.year, m_start.month + 1, 1) - timedelta(days=1)
            next_m = date(m_start.year, m_start.month + 1, 1)
        chunks.append((max(m_start, from_date), min(m_end, to_date)))
        m_start = next_m

    def _fetch_site_month(venue_name, site_id, chunk_from, chunk_to):
        try:
            rows = _tev_summary(site_id, chunk_from, chunk_to)
        except Exception:
            return None
        wet = dry = covers = txns = 0.0
        for row in rows:
            if row.get("LineDescription") != "ProductTypes":
                continue
            ptype = str(row.get("ProductTypeName") or "").strip().lower()
            gross = float(row.get("TotalGross") or 0)
            if ptype == "beverage":
                wet    += gross
                covers += float(row.get("TotalCovers") or 0)
                txns   += float(row.get("TotalTransactions") or 0)
            elif ptype == "food":
                dry += gross
        if wet + dry == 0:
            return None
        return {"venue_name": venue_name, "month": chunk_from.strftime("%Y-%m"),
                "wet": wet, "dry": dry, "total": wet + dry,
                "covers": int(covers), "transactions": int(txns)}

    for vname, sid in TEVALIS_SITES.items():
        for cf, ct in chunks:
            result = _fetch_site_month(vname, sid, cf, ct)
            if result:
                records.append(result)

    return (
        pd.DataFrame(records) if records
        else pd.DataFrame(columns=["venue_name", "month", "wet", "dry",
                                   "total", "covers", "transactions"])
    )

# config.py — Credentials and constants for Chickpea Annual Performance Report
# Loaded from st.secrets in cloud; fallback to hardcoded values for local dev.

import streamlit as st


def get_eviivo_creds():
    try:
        return {
            "client_id":     st.secrets["eviivo"]["client_id"],
            "client_secret": st.secrets["eviivo"]["client_secret"],
            "auth_url":      st.secrets["eviivo"].get("auth_url", "https://auth.eviivo.com/api/connect/token"),
            "api_url":       st.secrets["eviivo"].get("api_url",  "https://io.eviivo.com/pms/v2"),
        }
    except Exception:
        return {
            "client_id":     "4a8fc6f8-a0f7-4618-ad28-3c61b00b5d5d",
            "client_secret": "1knWGGXhWQDOv7KTubOJ",
            "auth_url":      "https://auth.eviivo.com/api/connect/token",
            "api_url":       "https://io.eviivo.com/pms/v2",
        }


def get_sr_creds():
    try:
        return {
            "client_id":     st.secrets["sevenrooms"]["client_id"],
            "client_secret": st.secrets["sevenrooms"]["client_secret"],
            "api_url":       st.secrets["sevenrooms"].get("api_url", "https://api.sevenrooms.com/2_4"),
        }
    except Exception:
        return {
            "client_id":     "dcc8dabbbd8de6f13b9831b31535eac35f0792ba6caec7cd2418fb72d1cc90acac580700da9861dfa64f17988b3dcbdd651e3e5fcd626aeb1e70689a37daa962",
            "client_secret": "40590241a64c8988a36341b5245c04eaaac175d3742ab8e09bea7b7fd46cdf56dda467c75934b5a2c557725a4411efad473a0d54747a2aa6291e6a21c7d21d51",
            "api_url":       "https://api.sevenrooms.com/2_4",
        }


EVIIVO_PROPERTIES = {
    "The Bell & Crown":    "TheBellBA121",
    "The Dog & Gun":       "DogandGunSP4",
    "The Fleur de Lys":    "TheFleurdeLysInnBH21",
    "The Grosvenor Arms":  "TheGrosvenorArmsSP3",
    "The Manor House Inn": "TheManorHouseInnBA4",
    "The Pembroke Arms":   "PembrokeSP2",
    "The Queen's Head":    "TheQueensHeadSP5",
}

ROOM_COUNTS = {
    "The Bell & Crown":    6,
    "The Dog & Gun":       6,
    "The Fleur de Lys":    9,
    "The Grosvenor Arms":  9,
    "The Manor House Inn": 9,
    "The Pembroke Arms":   9,
    "The Queen's Head":    9,
}

# Historical room count changes: (property_name, date_of_change_str, rooms_BEFORE_that_date)
# date_of_change_str is ISO format "YYYY-MM-DD"
ROOM_COUNT_HISTORY = [
    ("The Queen's Head", "2026-03-01", 4),
]

SALES_VENUE_MAP = {
    "PEMBROKE ARMS":   "The Pembroke Arms",
    "GROSVENOR ARMS":  "The Grosvenor Arms",
    "BELL & CROWN":    "The Bell & Crown",
    "DOG & GUN":       "The Dog & Gun",
    "QUEENS HEAD":     "The Queen's Head",
    "SILVER PLOUGH":   "The Silver Plough",
    "KINGS ARMS":      "The Kings Arms",
    "MANOR HOUSE INN": "The Manor House Inn",
    "FLEUR DE LYS":    "The Fleur de Lys",
}

ROOMS_AND_FB = {
    "The Bell & Crown", "The Dog & Gun", "The Fleur de Lys",
    "The Grosvenor Arms", "The Manor House Inn",
    "The Pembroke Arms", "The Queen's Head",
}

PHONE_TARGET = 0.15
BRAND_GREEN  = "#1C3829"
BRAND_LIGHT  = "#C8DFC8"
CARD_BG      = "#f8f9fa"

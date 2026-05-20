import html
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

try:
    import feedparser
except Exception:
    feedparser = None


# =============================================================================
# CONFIGURATION
# =============================================================================

APP_NAME = "Alpha Terminal Pro"
CASH_POSITIVE = "Cash Positif"
DATA_NOT_VALIDATED = "Donnée non validée"

FX_FALLBACKS_TO_EUR = {
    "USD": 0.92,
    "GBP": 1.17,
    "CHF": 1.04,
    "CAD": 0.68,
    "JPY": 0.0060,
    "AUD": 0.60,
    "CNY": 0.13,
    "HKD": 0.12,
    "SEK": 0.089,
    "NOK": 0.087,
    "DKK": 0.134,
    "SGD": 0.68,
}

PEA_ISSUERS = (
    "AMUNDI",
    "LYXOR",
    "BNP",
    "BNP PARIBAS",
    "XTRACKERS",
    "HSBC",
    "OSSiam".upper(),
    "FRANKLIN",
)

YAHOO_SYMBOL_ALIASES = {
    "FCHI": "^FCHI",
    "CAC40": "^FCHI",
    "STOXX50E": "^STOXX50E",
    "SX5E": "^STOXX50E",
    "GSPC": "^GSPC",
    "SPX": "^GSPC",
    "DJI": "^DJI",
    "IXIC": "^IXIC",
    "NDX": "^NDX",
}


st.set_page_config(
    page_title=f"{APP_NAME} | Institutionnel",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        :root {
            --bg: #080b10;
            --panel: rgba(18, 25, 34, 0.72);
            --panel-2: rgba(24, 33, 44, 0.84);
            --glass: rgba(255, 255, 255, 0.055);
            --border: rgba(142, 160, 180, 0.18);
            --border-strong: rgba(142, 160, 180, 0.34);
            --muted: #8ea0b4;
            --text: #edf4fb;
            --blue: #68a8ff;
            --green: #34d399;
            --amber: #f0b84b;
            --red: #fb7185;
        }

        .stApp {
            background:
                radial-gradient(circle at 18% 8%, rgba(104,168,255,0.16), transparent 28%),
                radial-gradient(circle at 82% 4%, rgba(52,211,153,0.08), transparent 24%),
                linear-gradient(135deg, #070a0f 0%, #0c1118 42%, #070a0f 100%);
            color: var(--text);
        }

        h1, h2, h3, h4 {
            color: var(--text) !important;
            letter-spacing: 0 !important;
            font-weight: 600 !important;
        }

        [data-testid="stSidebar"] {
            background: rgba(5, 8, 12, 0.92);
            border-right: 1px solid var(--border);
            backdrop-filter: blur(18px);
        }

        .block-container {
            padding-top: 3.25rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }

        .terminal-header {
            position: relative;
            overflow: hidden;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 22px 24px;
            background:
                linear-gradient(135deg, rgba(26, 37, 52, 0.86), rgba(12, 17, 24, 0.78)),
                radial-gradient(circle at 100% 0%, rgba(104,168,255,0.20), transparent 34%);
            margin-bottom: 18px;
            box-shadow: 0 18px 55px rgba(0,0,0,0.28);
            backdrop-filter: blur(18px);
        }

        .terminal-header:after {
            content: "";
            position: absolute;
            inset: 0;
            border-radius: 8px;
            pointer-events: none;
            background: linear-gradient(120deg, rgba(255,255,255,0.10), transparent 28%, transparent 72%, rgba(104,168,255,0.10));
        }

        .terminal-title {
            position: relative;
            z-index: 1;
            font-size: 1.72rem;
            line-height: 1.15;
            font-weight: 780;
            color: var(--text);
            margin-bottom: 4px;
        }

        .terminal-subtitle {
            position: relative;
            z-index: 1;
            color: var(--muted);
            font-size: 0.88rem;
        }

        .bento-section-title {
            margin: 24px 0 12px 0;
            color: var(--text);
            font-size: 0.92rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0;
        }

        .metric-card {
            position: relative;
            overflow: hidden;
            min-height: 114px;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px 17px;
            margin-bottom: 12px;
            background:
                linear-gradient(145deg, rgba(255,255,255,0.088), rgba(255,255,255,0.026)),
                linear-gradient(180deg, rgba(20, 29, 40, 0.86), rgba(10, 14, 20, 0.72));
            box-shadow: 0 16px 42px rgba(0,0,0,0.24);
            backdrop-filter: blur(18px);
            transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease, background 180ms ease;
        }

        .metric-card:before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background: radial-gradient(circle at 92% 10%, rgba(104,168,255,0.16), transparent 28%);
            opacity: 0.72;
        }

        .metric-card:hover {
            transform: translateY(-4px);
            border-color: var(--border-strong);
            box-shadow: 0 20px 48px rgba(0,0,0,0.34), 0 0 32px rgba(104,168,255,0.12);
        }

        .metric-card.compact {
            min-height: 96px;
        }

        .metric-title {
            position: relative;
            z-index: 1;
            color: var(--muted);
            font-size: 0.76rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .metric-value {
            position: relative;
            z-index: 1;
            color: var(--text);
            font-size: 1.35rem;
            font-weight: 750;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }

        .metric-subtitle {
            position: relative;
            z-index: 1;
            color: var(--muted);
            font-size: 0.78rem;
            margin-top: 7px;
        }

        .metric-card.accent {
            border-color: rgba(104,168,255,0.48);
            background:
                linear-gradient(145deg, rgba(104,168,255,0.14), rgba(255,255,255,0.03)),
                linear-gradient(180deg, rgba(20, 30, 43, 0.92), rgba(9, 14, 21, 0.78));
        }

        .metric-card.good {
            border-color: rgba(49,196,141,0.5);
        }

        .metric-card.warn {
            border-color: rgba(214,165,63,0.58);
        }

        .metric-card.bad {
            border-color: rgba(239,100,97,0.56);
        }

        .metric-card.good .metric-value { color: var(--green); }
        .metric-card.warn .metric-value { color: var(--amber); }
        .metric-card.bad .metric-value { color: var(--red); }
        .metric-card.accent .metric-value { color: var(--blue); }

        .value-blue { color: var(--blue); }
        .value-green { color: var(--green); }
        .value-amber { color: var(--amber); }
        .value-red { color: var(--red); }
        .value-na { color: var(--muted); font-weight: 650; }

        .verdict {
            border: 1px solid var(--border);
            border-left: 4px solid var(--blue);
            border-radius: 8px;
            padding: 16px 17px;
            background:
                linear-gradient(145deg, rgba(255,255,255,0.075), rgba(255,255,255,0.025)),
                rgba(14, 20, 28, 0.78);
            margin-bottom: 14px;
            box-shadow: 0 16px 42px rgba(0,0,0,0.22);
            backdrop-filter: blur(18px);
        }

        .verdict.buy { border-left-color: var(--green); }
        .verdict.hold { border-left-color: var(--amber); }
        .verdict.sell { border-left-color: var(--red); }

        .news-card {
            border: 1px solid var(--border);
            border-left: 3px solid var(--amber);
            border-radius: 8px;
            padding: 14px 15px;
            background:
                linear-gradient(145deg, rgba(255,255,255,0.07), rgba(255,255,255,0.025)),
                rgba(14, 20, 28, 0.78);
            margin-bottom: 10px;
            box-shadow: 0 14px 34px rgba(0,0,0,0.20);
            backdrop-filter: blur(18px);
            transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
        }

        .news-card:hover {
            transform: translateY(-3px);
            border-color: rgba(240,184,75,0.52);
            box-shadow: 0 18px 44px rgba(0,0,0,0.30), 0 0 28px rgba(104,168,255,0.10);
        }

        .news-card a {
            color: var(--blue);
            font-weight: 700;
            text-decoration: none;
        }

        .news-meta {
            color: var(--muted);
            font-size: 0.82rem;
            margin-top: 6px;
        }

        .source-badge {
            display: inline-block;
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 4px 9px;
            color: var(--muted);
            font-size: 0.74rem;
            font-weight: 700;
            margin-right: 6px;
            margin-bottom: 6px;
            background: rgba(255,255,255,0.045);
            backdrop-filter: blur(12px);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            width: fit-content;
            max-width: 100%;
            padding: 5px;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: rgba(255,255,255,0.045);
            backdrop-filter: blur(16px);
            margin-bottom: 16px;
        }

        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border: 0;
            border-radius: 999px;
            padding: 8px 15px;
            color: var(--muted);
            transition: background 160ms ease, color 160ms ease, box-shadow 160ms ease;
        }

        .stTabs [aria-selected="true"] {
            color: var(--text);
            background: linear-gradient(135deg, rgba(104,168,255,0.24), rgba(255,255,255,0.07));
            box-shadow: 0 8px 24px rgba(0,0,0,0.22), inset 0 0 0 1px rgba(104,168,255,0.18);
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-baseweb="select"] > div {
            min-height: 44px;
            color: var(--text) !important;
            background: rgba(255,255,255,0.048) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.055), 0 14px 36px rgba(0,0,0,0.18) !important;
            backdrop-filter: blur(16px);
        }

        div[data-testid="stTextInput"] {
            margin-bottom: 16px;
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stNumberInput"] input:focus {
            border-color: rgba(104,168,255,0.58) !important;
            box-shadow: 0 0 0 1px rgba(104,168,255,0.28), 0 16px 38px rgba(0,0,0,0.22) !important;
        }

        div[data-testid="stTextInput"] input::placeholder {
            color: rgba(142,160,180,0.74) !important;
        }

        div[data-testid="stMetricValue"] {
            color: var(--text);
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 16px 42px rgba(0,0,0,0.22);
        }

        .comparison-control {
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px 16px 2px 16px;
            margin-bottom: 18px;
            background:
                linear-gradient(145deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02)),
                rgba(12, 18, 26, 0.72);
            box-shadow: 0 16px 42px rgba(0,0,0,0.22);
            backdrop-filter: blur(18px);
        }

        .matrix-card {
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
            margin: 16px 0 20px 0;
            background:
                linear-gradient(145deg, rgba(255,255,255,0.075), rgba(255,255,255,0.022)),
                rgba(11, 16, 23, 0.84);
            box-shadow: 0 20px 56px rgba(0,0,0,0.28);
            backdrop-filter: blur(18px);
        }

        .matrix-head {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 16px;
            padding: 16px 18px;
            border-bottom: 1px solid var(--border);
            background: linear-gradient(135deg, rgba(104,168,255,0.12), rgba(255,255,255,0.02));
        }

        .matrix-kicker {
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
        }

        .matrix-title {
            color: var(--text);
            font-size: 1.05rem;
            font-weight: 800;
            margin-top: 3px;
        }

        .matrix-count {
            flex: 0 0 auto;
            color: var(--blue);
            border: 1px solid rgba(104,168,255,0.26);
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 0.78rem;
            font-weight: 800;
            background: rgba(104,168,255,0.08);
        }

        .matrix-scroll {
            width: 100%;
            overflow-x: auto;
        }

        .matrix-table {
            width: 100%;
            min-width: 880px;
            border-collapse: collapse;
            table-layout: auto;
        }

        .matrix-table th {
            padding: 12px 12px;
            color: var(--muted);
            font-size: 0.72rem;
            text-transform: uppercase;
            text-align: left;
            border-bottom: 1px solid var(--border);
            background: rgba(255,255,255,0.032);
            white-space: nowrap;
        }

        .matrix-table td {
            padding: 13px 12px;
            color: var(--text);
            font-size: 0.84rem;
            border-bottom: 1px solid rgba(142,160,180,0.11);
            vertical-align: middle;
        }

        .matrix-table tr:last-child td {
            border-bottom: 0;
        }

        .matrix-table tr:hover td {
            background: rgba(104,168,255,0.055);
        }

        .matrix-symbol {
            color: var(--blue);
            font-weight: 850;
            letter-spacing: 0;
            white-space: nowrap;
        }

        .matrix-name {
            min-width: 220px;
            max-width: 320px;
            color: #cbd6e2;
        }

        .matrix-cell-good { color: var(--green) !important; font-weight: 800; }
        .matrix-cell-warn { color: var(--amber) !important; font-weight: 800; }
        .matrix-cell-bad { color: var(--red) !important; font-weight: 800; }
        .matrix-cell-na { color: var(--muted) !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# OUTILS DEFENSIFS
# =============================================================================

def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"", "none", "nan", "null", "na", "n/a", "-"}
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    try:
        result = pd.isna(value)
        if isinstance(result, (bool, np.bool_)):
            return bool(result)
    except Exception:
        return False
    return False


def safe_float(value: Any, multiplier: float = 1.0, precision: int = 2) -> Optional[float]:
    if is_missing(value):
        return None
    try:
        if isinstance(value, str):
            cleaned = (
                value.replace("\u202f", "")
                .replace(" ", "")
                .replace("%", "")
                .replace("€", "")
                .replace("$", "")
                .replace(",", ".")
                .strip()
            )
            if cleaned in {"", "-"}:
                return None
            numeric = float(cleaned)
        else:
            numeric = float(value)
        if not math.isfinite(numeric):
            return None
        return round(numeric * multiplier, precision)
    except Exception:
        return None


def safe_pct(value: Any, precision: int = 2) -> Optional[float]:
    numeric = safe_float(value, precision=6)
    if numeric is None:
        return None
    try:
        if abs(numeric) <= 1.5:
            numeric *= 100
        return round(numeric, precision)
    except Exception:
        return None


def safe_str(value: Any, default: str = "N/A") -> str:
    if is_missing(value):
        return default
    try:
        return str(value).strip()
    except Exception:
        return default


def first_valid(*values: Any) -> Any:
    for value in values:
        if not is_missing(value):
            return value
    return None


def dict_get(data: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        try:
            value = data.get(key)
            if not is_missing(value):
                return value
        except Exception:
            continue
    return None


def fast_get(fast_info: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        try:
            value = fast_info.get(key)
            if not is_missing(value):
                return value
        except Exception:
            continue
    return None


def html_escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def format_number(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "<span class='value-na'>N/A</span>"
    if isinstance(value, str):
        if value == CASH_POSITIVE:
            return "<span class='value-green'>Cash Positif</span>"
        if value == DATA_NOT_VALIDATED:
            return "<span class='value-na'>Donnée non validée</span>"
        return html_escape(value)
    try:
        numeric = float(value)
        if not math.isfinite(numeric):
            return "<span class='value-na'>N/A</span>"
        return f"{numeric:,.{decimals}f}".replace(",", " ")
    except Exception:
        return "<span class='value-na'>N/A</span>"


def format_metric(value: Any, suffix: str = "", decimals: int = 2) -> str:
    if value is None:
        return "<span class='value-na'>N/A</span>"
    if isinstance(value, str):
        return format_number(value, decimals)
    return f"{format_number(value, decimals)} {html_escape(suffix)}".strip()


def format_compact_eur(value_millions: Optional[float]) -> str:
    if value_millions is None:
        return "<span class='value-na'>N/A</span>"
    if abs(value_millions) >= 1000:
        return f"{format_number(value_millions / 1000, 2)} Md€"
    return f"{format_number(value_millions, 2)} M€"


def infer_metric_tone(title: str, value: Any) -> str:
    if value is None or value == DATA_NOT_VALIDATED:
        return ""

    title_l = title.lower()
    if isinstance(value, str):
        if value == CASH_POSITIVE:
            return "good"
        return ""

    numeric = safe_float(value)
    if numeric is None:
        return ""

    if "score" in title_l:
        return "good" if numeric >= 65 else "warn" if numeric >= 40 else "bad"
    if "per" in title_l:
        return "good" if 0 < numeric < 20 else "warn" if 20 <= numeric <= 35 else "bad"
    if "ev / ebitda" in title_l or "ev/ebitda" in title_l:
        return "good" if 0 < numeric < 10 else "warn" if numeric <= 15 else "bad"
    if "price to sales" in title_l:
        return "good" if numeric < 5 else "warn" if numeric <= 10 else "bad"
    if "price to book" in title_l:
        return "good" if numeric < 3 else "warn" if numeric <= 6 else "bad"
    if "marge nette" in title_l:
        return "good" if numeric >= 12 else "warn" if numeric >= 5 else "bad"
    if "marge opérationnelle" in title_l or "marge operationnelle" in title_l:
        return "good" if numeric >= 15 else "warn" if numeric >= 7 else "bad"
    if "marge brute" in title_l:
        return "good" if numeric >= 35 else "warn" if numeric >= 20 else "bad"
    if "roe" in title_l:
        return "good" if numeric >= 15 else "warn" if numeric >= 8 else "bad"
    if "roa" in title_l:
        return "good" if numeric >= 7 else "warn" if numeric >= 3 else "bad"
    if "dette nette / ebitda" in title_l or "levier" in title_l:
        return "good" if numeric < 2 else "warn" if numeric <= 3.5 else "bad"
    if "current ratio" in title_l:
        return "good" if numeric >= 1.2 else "warn" if numeric >= 1 else "bad"
    if "quick ratio" in title_l:
        return "good" if numeric >= 1 else "warn" if numeric >= 0.75 else "bad"
    if "debt to equity" in title_l:
        return "good" if numeric <= 80 else "warn" if numeric <= 150 else "bad"
    if "revenue growth" in title_l or "croissance" in title_l:
        return "good" if numeric >= 5 else "warn" if numeric >= 0 else "bad"
    if "payout" in title_l:
        return "good" if 0 < numeric <= 60 else "warn" if numeric <= 90 else "bad"
    if "frais" in title_l or "ter" in title_l:
        return "good" if numeric <= 0.30 else "warn" if numeric <= 0.60 else "bad"
    if "aum" in title_l or "encours" in title_l or "capitalisation" in title_l:
        return "good" if numeric >= 100 else "bad"
    if "rendement" in title_l:
        return "good" if 0 < numeric <= 8 else "warn" if numeric <= 12 else "bad"

    return ""


def metric_card(
    title: str,
    value_html: str,
    subtitle: str = "",
    tone: str = "",
    raw_value: Any = None,
) -> None:
    inferred = infer_metric_tone(title, raw_value)
    class_names = " ".join(part for part in [tone, inferred] if part).strip()
    subtitle_html = (
        f"<div class='metric-subtitle'>{html_escape(subtitle)}</div>" if subtitle else ""
    )
    st.markdown(
        f"""
        <div class="metric-card {html_escape(class_names)}">
            <div class="metric-title">{html_escape(title)}</div>
            <div class="metric-value">{value_html}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_source_badges(*sources: str) -> None:
    badges = "".join(
        f"<span class='source-badge'>{html_escape(source)}</span>" for source in sources
    )
    st.markdown(badges, unsafe_allow_html=True)


def section_title(title: str) -> None:
    st.markdown(f"<div class='bento-section-title'>{html_escape(title)}</div>", unsafe_allow_html=True)


def normalize_yahoo_symbol(symbol: str) -> str:
    cleaned = safe_str(symbol, "").upper().strip()
    return YAHOO_SYMBOL_ALIASES.get(cleaned, cleaned)


# =============================================================================
# ACQUISITION ROBUSTE DES DONNEES
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_fx_rate_to_eur(currency_code: str) -> float:
    raw_currency = safe_str(currency_code, "EUR")
    pence = raw_currency in {"GBp", "GBX", "GBPp"} or raw_currency.upper() == "GBX"
    currency = "GBP" if pence else raw_currency.upper().replace("=X", "")

    if currency == "EUR":
        return 0.01 if pence else 1.0

    fallback = FX_FALLBACKS_TO_EUR.get(currency, 1.0)

    try:
        pair = f"{currency}EUR=X"
        history = yf.Ticker(pair).history(period="5d", interval="1d")
        if history is not None and not history.empty and "Close" in history:
            last_close = safe_float(history["Close"].dropna().iloc[-1], precision=6)
            if last_close and last_close > 0:
                return round(last_close * (0.01 if pence else 1.0), 6)
    except Exception:
        pass

    try:
        inverse_pair = f"EUR{currency}=X"
        history = yf.Ticker(inverse_pair).history(period="5d", interval="1d")
        if history is not None and not history.empty and "Close" in history:
            last_close = safe_float(history["Close"].dropna().iloc[-1], precision=6)
            if last_close and last_close > 0:
                return round((1 / last_close) * (0.01 if pence else 1.0), 6)
    except Exception:
        pass

    return round(fallback * (0.01 if pence else 1.0), 6)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_yahoo_payload(symbol: str) -> Dict[str, Any]:
    symbol = safe_str(symbol).upper()
    payload: Dict[str, Any] = {"info": {}, "fast_info": {}, "errors": []}

    try:
        ticker = yf.Ticker(symbol)
    except Exception as exc:
        payload["errors"].append(f"Ticker: {exc}")
        return payload

    try:
        info = ticker.info
        if isinstance(info, dict):
            payload["info"] = info
    except Exception as exc:
        payload["errors"].append(f"info: {exc}")

    try:
        fast_obj = ticker.fast_info
        try:
            payload["fast_info"] = dict(fast_obj)
        except Exception:
            fast_keys = [
                "currency",
                "last_price",
                "market_cap",
                "shares",
                "ten_day_average_volume",
                "three_month_average_volume",
                "year_high",
                "year_low",
                "previous_close",
            ]
            extracted = {}
            for key in fast_keys:
                value = None
                try:
                    value = fast_obj[key]
                except Exception:
                    try:
                        value = getattr(fast_obj, key)
                    except Exception:
                        value = None
                if not is_missing(value):
                    extracted[key] = value
            payload["fast_info"] = extracted
    except Exception as exc:
        payload["errors"].append(f"fast_info: {exc}")

    return payload


@st.cache_data(ttl=900, show_spinner=False)
def fetch_history(symbol: str, period: str = "5y") -> pd.DataFrame:
    try:
        history = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=False)
        if history is None or history.empty or "Close" not in history.columns:
            return pd.DataFrame()
        history = history.copy()
        history = history[history["Close"].notna()]
        try:
            if getattr(history.index, "tz", None) is not None:
                history.index = history.index.tz_convert(None)
        except Exception:
            pass
        return history
    except Exception:
        return pd.DataFrame()


def get_latest_price_local(
    info: Dict[str, Any], fast_info: Dict[str, Any], history: Optional[pd.DataFrame] = None
) -> Optional[float]:
    price = first_valid(
        dict_get(info, "currentPrice", "regularMarketPrice", "navPrice", "previousClose"),
        fast_get(fast_info, "last_price", "previous_close"),
    )
    parsed = safe_float(price)
    if parsed is not None:
        return parsed

    try:
        if history is not None and not history.empty and "Close" in history:
            return safe_float(history["Close"].dropna().iloc[-1])
    except Exception:
        return None
    return None


def get_asset_name(info: Dict[str, Any], symbol: str) -> str:
    return safe_str(first_valid(dict_get(info, "longName", "shortName", "displayName"), symbol), symbol)


def get_currency(info: Dict[str, Any], fast_info: Dict[str, Any]) -> str:
    return safe_str(first_valid(dict_get(info, "currency", "financialCurrency"), fast_get(fast_info, "currency")), "USD")


def is_etf_asset(info: Dict[str, Any], symbol: str) -> bool:
    quote_type = safe_str(dict_get(info, "quoteType"), "").upper()
    category = safe_str(dict_get(info, "category"), "").upper()
    name = get_asset_name(info, symbol).upper()
    symbol_upper = symbol.upper()
    if quote_type in {"ETF", "MUTUALFUND", "FUND", "INDEX"}:
        return True
    if "ETF" in quote_type or "ETF" in category or "INDEX" in quote_type:
        return True
    if any(token in name for token in ("ETF", "UCITS", "INDEX FUND", "TRACKER")):
        return True
    if symbol_upper in {"SPY", "QQQ", "DIA", "IWM", "CW8.PA", "ESE.PA", "EWLD.PA"}:
        return True
    return False


# =============================================================================
# ACTIONS: 21 RATIOS, SCORE ET CONSENSUS
# =============================================================================

def extract_stock_data(
    symbol: str,
    info: Dict[str, Any],
    fast_info: Dict[str, Any],
    fx_rate: float,
    history: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    price_local = get_latest_price_local(info, fast_info, history)
    market_cap_local = first_valid(dict_get(info, "marketCap"), fast_get(fast_info, "market_cap"))

    eps_eur = safe_float(dict_get(info, "trailingEps"), fx_rate)
    bvps_eur = safe_float(dict_get(info, "bookValue"), fx_rate)
    graham = None
    if eps_eur is not None and bvps_eur is not None and eps_eur > 0 and bvps_eur > 0:
        graham = round(math.sqrt(22.5 * eps_eur * bvps_eur), 2)

    total_cash_meur = safe_float(dict_get(info, "totalCash"), fx_rate / 1_000_000)
    total_debt_meur = safe_float(dict_get(info, "totalDebt"), fx_rate / 1_000_000)
    ebitda_meur = safe_float(dict_get(info, "ebitda"), fx_rate / 1_000_000)

    net_debt_meur = None
    if total_cash_meur is not None and total_debt_meur is not None:
        net_debt_meur = round(total_debt_meur - total_cash_meur, 2)

    leverage: Any = None
    if net_debt_meur is not None and ebitda_meur is not None and ebitda_meur > 0:
        leverage = CASH_POSITIVE if net_debt_meur < 0 else round(net_debt_meur / ebitda_meur, 2)

    target_eur = safe_float(dict_get(info, "targetMeanPrice", "targetMedianPrice"), fx_rate)
    price_eur = safe_float(price_local, fx_rate)

    recommendation_key = safe_str(dict_get(info, "recommendationKey"), "N/A").lower()
    recommendation_map = {
        "strong_buy": "Achat fort",
        "buy": "Achat",
        "hold": "Conserver",
        "sell": "Vendre",
        "strong_sell": "Vente forte",
        "none": "N/A",
    }
    recommendation = recommendation_map.get(recommendation_key, recommendation_key.replace("_", " ").title())

    data: Dict[str, Any] = {
        "Ticker": symbol.upper(),
        "Nom": get_asset_name(info, symbol),
        "Type": "Action",
        "Devise": get_currency(info, fast_info),
        "Prix": price_eur,
        "Capitalisation_MEUR": safe_float(market_cap_local, fx_rate / 1_000_000),
        "PER_Actuel": safe_float(dict_get(info, "trailingPE")),
        "PER_Futur": safe_float(dict_get(info, "forwardPE")),
        "PS": safe_float(dict_get(info, "priceToSalesTrailing12Months")),
        "PB": safe_float(dict_get(info, "priceToBook")),
        "EV_EBITDA": safe_float(dict_get(info, "enterpriseToEbitda")),
        "BPA": eps_eur,
        "BVPS": bvps_eur,
        "Graham": graham,
        "Marge_Brute": safe_pct(dict_get(info, "grossMargins")),
        "Marge_Op": safe_pct(dict_get(info, "operatingMargins")),
        "Marge_Nette": safe_pct(dict_get(info, "profitMargins")),
        "ROE": safe_pct(dict_get(info, "returnOnEquity")),
        "ROA": safe_pct(dict_get(info, "returnOnAssets")),
        "Dette_Nette": net_debt_meur,
        "EBITDA": ebitda_meur,
        "Levier": leverage,
        "Current_Ratio": safe_float(dict_get(info, "currentRatio")),
        "Quick_Ratio": safe_float(dict_get(info, "quickRatio")),
        "Debt_Equity": safe_pct(dict_get(info, "debtToEquity")),
        "Rev_Growth": safe_pct(dict_get(info, "revenueGrowth")),
        "Payout": safe_pct(dict_get(info, "payoutRatio")),
        "Dividend_Yield": safe_pct(dict_get(info, "dividendYield")),
        "Target": target_eur,
        "Analystes": safe_str(dict_get(info, "numberOfAnalystOpinions"), "N/A"),
        "Reco": recommendation,
        "Sector": safe_str(dict_get(info, "sector"), "N/A"),
        "Industry": safe_str(dict_get(info, "industry"), "N/A"),
    }

    score = 0
    if isinstance(data["Levier"], float) and data["Levier"] < 2:
        score += 15
    elif data["Levier"] == CASH_POSITIVE:
        score += 15
    if data["ROE"] is not None and data["ROE"] > 15:
        score += 15
    if data["Marge_Nette"] is not None and data["Marge_Nette"] > 12:
        score += 15
    if data["Graham"] is not None and data["Prix"] is not None and data["Graham"] > data["Prix"]:
        score += 15
    if data["PER_Actuel"] is not None and 0 < data["PER_Actuel"] < 20:
        score += 10
    if data["Current_Ratio"] is not None and data["Current_Ratio"] > 1.2:
        score += 10
    if data["Rev_Growth"] is not None and data["Rev_Growth"] > 5:
        score += 10
    if data["Payout"] is not None and 0 < data["Payout"] < 60:
        score += 10

    data["Score"] = min(score, 100)
    return data


# =============================================================================
# ETF: FRAIS, AUM, DISTRIBUTION, REPLICATION, FISCALITE
# =============================================================================

def extract_etf_data(
    symbol: str,
    info: Dict[str, Any],
    fast_info: Dict[str, Any],
    fx_rate: float,
    history: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    name = get_asset_name(info, symbol)
    name_upper = name.upper()
    summary = safe_str(dict_get(info, "longBusinessSummary"), "").upper()
    quote_type = safe_str(dict_get(info, "quoteType"), "").upper()
    asset_type = "Indice" if quote_type == "INDEX" else "ETF"
    price_local = get_latest_price_local(info, fast_info, history)

    raw_ter = first_valid(
        dict_get(info, "annualReportExpenseRatio", "netExpenseRatio", "expenseRatio"),
        dict_get(info, "annualReportExpenseRatio"),
    )
    ter = safe_pct(raw_ter)

    aum_meur = safe_float(dict_get(info, "totalAssets"), fx_rate / 1_000_000)

    if any(token in name_upper for token in (" ACC", "ACCUM", "ACCUMULATION", " CAPITALISATION", " C ")):
        distribution = "Capitalisation (Acc)"
    elif any(token in name_upper for token in (" DIST", "DISTR", "DISTRIBUTION", " DIS ")):
        distribution = "Distribution (Dist)"
    else:
        distribution = "Donnée non validée"

    if any(token in name_upper or token in summary for token in ("SWAP", "SYNTH", "SYNTHETIC")):
        replication = "Synthétique (swap)"
    elif any(token in name_upper or token in summary for token in ("PHYSICAL", "PHYSIQUE", "REPLICATION")):
        replication = "Physique"
    else:
        replication = "Donnée non validée"

    pea_probable = symbol.upper().endswith(".PA") and any(issuer in name_upper for issuer in PEA_ISSUERS)
    if pea_probable or "PEA" in name_upper:
        fiscality = "PEA probable"
    elif symbol.upper().endswith(".PA"):
        fiscality = "À valider courtier"
    else:
        fiscality = "Compte-titres ordinaire"

    score = 0
    if aum_meur is not None and aum_meur >= 100:
        score += 30
    if ter is not None and ter <= 0.30:
        score += 25
    elif ter is not None and ter <= 0.60:
        score += 15
    if distribution != DATA_NOT_VALIDATED:
        score += 15
    if replication != DATA_NOT_VALIDATED:
        score += 15
    if "PEA" in fiscality:
        score += 15

    return {
        "Ticker": symbol.upper(),
        "Nom": name,
        "Type": asset_type,
        "Devise": get_currency(info, fast_info),
        "Prix": safe_float(price_local, fx_rate),
        "Capitalisation_MEUR": aum_meur,
        "TER": ter,
        "AUM": aum_meur,
        "Distribution": distribution,
        "Replication": replication,
        "Tracking": "Donnée non validée",
        "Fiscalite": fiscality,
        "Dividend_Yield": safe_pct(dict_get(info, "yield", "dividendYield")),
        "Score": min(score, 100),
    }


# =============================================================================
# NEWS MORNINGSTAR ET CONSENSUS
# =============================================================================

def format_publication_date(value: Any) -> str:
    if is_missing(value):
        return "Récemment"
    try:
        if isinstance(value, (int, float)):
            timestamp = float(value)
            if timestamp > 10_000_000_000:
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        parsed = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(parsed):
            return safe_str(value, "Récemment")
        return parsed.strftime("%d/%m/%Y %H:%M UTC")
    except Exception:
        return safe_str(value, "Récemment")


def normalize_google_news_entry(entry: Any, source_hint: str = "") -> Optional[Dict[str, str]]:
    try:
        raw_title = safe_str(entry.get("title", getattr(entry, "title", "")), "")
        title = raw_title.rsplit(" - ", 1)[0].strip() if " - " in raw_title else raw_title.strip()
        link = safe_str(entry.get("link", getattr(entry, "link", "")), "#")
        if not title or not link or link == "#":
            return None

        source = source_hint or "Presse financière"
        entry_source = entry.get("source", None) if isinstance(entry, dict) else getattr(entry, "source", None)
        if isinstance(entry_source, dict):
            source = safe_str(entry_source.get("title"), source)
        elif entry_source is not None:
            source = safe_str(getattr(entry_source, "title", None), source)

        if "morningstar" in (raw_title + link + source).lower():
            source = "Morningstar"

        published_raw = None
        if isinstance(entry, dict):
            published_raw = first_valid(entry.get("published"), entry.get("updated"))
        else:
            published_raw = first_valid(getattr(entry, "published", None), getattr(entry, "updated", None))

        return {
            "title": title,
            "link": link,
            "publisher": source,
            "published": format_publication_date(published_raw),
        }
    except Exception:
        return None


def google_news_rss_url(query: str, locale: str = "fr") -> str:
    if locale == "fr":
        return (
            "https://news.google.com/rss/search?q="
            + urllib.parse.quote(query)
            + "&hl=fr&gl=FR&ceid=FR:fr"
        )
    return (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(query)
        + "&hl=en-US&gl=US&ceid=US:en"
    )


def parse_rss_url(url: str) -> Any:
    if feedparser is None:
        return None
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 AlphaTerminalPro/1.0",
                "Accept": "application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
            },
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read()
        return feedparser.parse(raw)
    except Exception:
        try:
            return feedparser.parse(url)
        except Exception:
            return None


def collect_google_news(query: str, source_hint: str, limit: int = 8) -> List[Dict[str, str]]:
    if feedparser is None:
        return []

    articles: List[Dict[str, str]] = []
    try:
        for locale in ("fr", "en"):
            feed = parse_rss_url(google_news_rss_url(query, locale))
            if feed is None:
                continue
            for entry in getattr(feed, "entries", [])[:limit]:
                article = normalize_google_news_entry(entry, source_hint)
                if article:
                    articles.append(article)
            if articles:
                break
    except Exception:
        return []

    return articles


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_yahoo_rss_news(symbol: str) -> List[Dict[str, str]]:
    if feedparser is None:
        return []

    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        return []

    rss_urls = [
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={urllib.parse.quote(clean_symbol)}&region=US&lang=en-US",
        f"https://news.search.yahoo.com/rss?p={urllib.parse.quote(clean_symbol + ' stock finance')}",
    ]

    articles: List[Dict[str, str]] = []
    for url in rss_urls:
        feed = parse_rss_url(url)
        if feed is None:
            continue
        for entry in getattr(feed, "entries", [])[:8]:
            article = normalize_google_news_entry(entry, "Yahoo Finance")
            if article:
                articles.append(article)
        if articles:
            break

    return articles


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_yahoo_news(symbol: str) -> List[Dict[str, str]]:
    articles: List[Dict[str, str]] = []
    try:
        raw_news = yf.Ticker(symbol).news or []
    except Exception:
        return []

    for item in raw_news[:10]:
        try:
            content = item.get("content", item) if isinstance(item, dict) else {}
            if not isinstance(content, dict):
                content = {}
            title = first_valid(
                content.get("title"),
                item.get("title") if isinstance(item, dict) else None,
            )
            link = first_valid(
                content.get("canonicalUrl", {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else None,
                content.get("clickThroughUrl", {}).get("url") if isinstance(content.get("clickThroughUrl"), dict) else None,
                item.get("link") if isinstance(item, dict) else None,
                item.get("url") if isinstance(item, dict) else None,
            )
            provider = first_valid(
                content.get("provider", {}).get("displayName") if isinstance(content.get("provider"), dict) else None,
                item.get("publisher") if isinstance(item, dict) else None,
                "Yahoo Finance",
            )
            published = first_valid(
                content.get("pubDate"),
                content.get("displayTime"),
                item.get("providerPublishTime") if isinstance(item, dict) else None,
                item.get("pubDate") if isinstance(item, dict) else None,
            )

            if title and link:
                articles.append(
                    {
                        "title": safe_str(title),
                        "link": safe_str(link),
                        "publisher": safe_str(provider, "Yahoo Finance"),
                        "published": format_publication_date(published),
                    }
                )
        except Exception:
            continue

    return articles


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_press_news(symbol: str, asset_name: str) -> List[Dict[str, str]]:
    clean_symbol = symbol.split(".")[0].strip()
    clean_name = " ".join(asset_name.replace(",", " ").replace("'", " ").split()[:7])
    if not clean_symbol and not clean_name:
        return []

    articles: List[Dict[str, str]] = []
    queries = [
        f'{clean_symbol} {clean_name} Morningstar',
        f'{clean_symbol} Morningstar',
        f'{clean_name} Morningstar finance',
        f'{clean_symbol} {clean_name} stock earnings analyst',
        f'{clean_symbol} {clean_name} finance ETF markets',
    ]

    for idx, query in enumerate(queries):
        source_hint = "Morningstar" if idx < 3 else "Presse financière"
        for article in collect_google_news(query, source_hint):
            articles.append(article)
        if len(articles) >= 6:
            break

    if len(articles) < 3:
        articles.extend(fetch_yahoo_rss_news(symbol))

    if len(articles) < 3:
        articles.extend(fetch_yahoo_news(symbol))

    unique: List[Dict[str, str]] = []
    seen = set()
    for article in articles:
        key = article["title"].strip().lower()
        if key not in seen:
            unique.append(article)
            seen.add(key)
        if len(unique) >= 8:
            break

    return unique[:6]


def build_consensus_summary(data: Dict[str, Any], is_etf: bool, news_count: int) -> str:
    if is_etf:
        aum = data.get("AUM")
        ter = data.get("TER")
        score = data.get("Score", 0)
        liquidity = "robuste" if aum is not None and aum >= 100 else "à surveiller"
        cost = "compétitif" if ter is not None and ter <= 0.30 else "à comparer"
        return (
            f"Score ETF {score}/100. Encours {liquidity}, frais {cost}, "
            f"réplication {data.get('Replication', DATA_NOT_VALIDATED).lower()}. "
            f"Articles presse disponibles: {news_count}. Validation croisée Zonebourse/Investing.com: {DATA_NOT_VALIDATED}."
        )

    price = data.get("Prix")
    target = data.get("Target")
    score = data.get("Score", 0)
    reco = data.get("Reco", "N/A")
    upside_text = "N/A"
    if price is not None and target is not None and price > 0:
        upside = ((target / price) - 1) * 100
        upside_text = f"{upside:.2f}%"

    return (
        f"Score fondamental {score}/100. Recommandation Yahoo Finance: {reco}. "
        f"Potentiel implicite du consensus: {upside_text}. "
        f"Articles presse disponibles: {news_count}. Validation croisée Zonebourse/Investing.com: {DATA_NOT_VALIDATED}."
    )


def build_expert_verdict(data: Dict[str, Any], is_etf: bool) -> str:
    score = int(data.get("Score", 0) or 0)

    if is_etf:
        if score >= 70:
            verdict, tone = "Achat", "buy"
        elif score >= 45:
            verdict, tone = "Conservation", "hold"
        else:
            verdict, tone = "Vente / Évitement", "sell"
        body = (
            f"Le profil ETF obtient {score}/100. L'encours est "
            f"{format_compact_eur(data.get('AUM'))}, les frais sont {format_metric(data.get('TER'), '%')}, "
            f"la réplication est {html_escape(data.get('Replication', DATA_NOT_VALIDATED))} et la fiscalité indiquée est "
            f"{html_escape(data.get('Fiscalite', DATA_NOT_VALIDATED))}. Le risque principal reste la liquidité si l'AUM est inférieur à 100 M€."
        )
    else:
        price = data.get("Prix")
        target = data.get("Target")
        target_support = target is not None and price is not None and price > 0 and target > price
        if score >= 65 and target_support:
            verdict, tone = "Achat", "buy"
        elif score >= 45:
            verdict, tone = "Conservation", "hold"
        else:
            verdict, tone = "Vente / Allègement", "sell"
        body = (
            f"Le profil obtient {score}/100. La rentabilité ressort avec un ROE de "
            f"{format_metric(data.get('ROE'), '%')} et une marge nette de {format_metric(data.get('Marge_Nette'), '%')}. "
            f"Le levier financier est {format_metric(data.get('Levier'), 'x')}, le PER actuel est "
            f"{format_metric(data.get('PER_Actuel'), 'x')} et le prix de Graham ressort à "
            f"{format_metric(data.get('Graham'), '€')}. Le verdict combine valorisation, qualité financière, croissance et consensus."
        )

    return (
        f"<div class='verdict {tone}'>"
        f"<h4 style='margin:0 0 8px 0;'>Verdict de l'Expert : {html_escape(verdict)}</h4>"
        f"<p style='margin:0;color:#c9d1d9;'>{body}</p>"
        f"</div>"
    )


# =============================================================================
# GRAPHIQUES ET DCA
# =============================================================================

def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    try:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=window, min_periods=window).mean()
        avg_loss = loss.rolling(window=window, min_periods=window).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.bfill()
    except Exception:
        return pd.Series(index=close.index, dtype=float)


def render_technical_chart(symbol: str, fx_rate: float) -> None:
    history = fetch_history(symbol, "5y")
    if history.empty or len(history) < 220:
        st.info("Historique insuffisant pour l'analyse technique.")
        return

    close_eur = pd.to_numeric(history["Close"], errors="coerce") * fx_rate
    chart_data = pd.DataFrame(index=history.index)
    chart_data["Close_EUR"] = close_eur
    chart_data["SMA50"] = close_eur.rolling(50).mean()
    chart_data["SMA200"] = close_eur.rolling(200).mean()
    chart_data["RSI"] = compute_rsi(close_eur)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.68, 0.32],
        vertical_spacing=0.055,
    )
    fig.add_trace(
        go.Scatter(x=chart_data.index, y=chart_data["Close_EUR"], name="Prix", line=dict(color="#5aa2ff", width=2)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=chart_data.index, y=chart_data["SMA50"], name="SMA 50", line=dict(color="#d6a53f", width=1.5, dash="dot")),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=chart_data.index, y=chart_data["SMA200"], name="SMA 200", line=dict(color="#ef6461", width=1.5, dash="dot")),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=chart_data.index, y=chart_data["RSI"], name="RSI 14", line=dict(color="#31c48d", width=1.5)),
        row=2,
        col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color="#ef6461", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#31c48d", row=2, col=1)
    fig.update_layout(
        height=640,
        template="plotly_dark",
        paper_bgcolor="#0b0f14",
        plot_bgcolor="#111820",
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="Prix (€)", row=1, col=1, gridcolor="#263241")
    fig.update_yaxes(title_text="RSI", row=2, col=1, gridcolor="#263241", range=[0, 100])
    fig.update_xaxes(gridcolor="#263241")
    st.plotly_chart(fig, use_container_width=True)


def render_dca_simulator(symbol: str, fx_rate: float) -> None:
    controls = st.columns([1, 1, 2])
    monthly_amount = controls[0].number_input(
        "Montant mensuel",
        min_value=10,
        max_value=100_000,
        value=150,
        step=10,
        label_visibility="collapsed",
    )
    period = controls[1].selectbox(
        "Période",
        options=["1y", "3y", "5y", "10y"],
        index=2,
        label_visibility="collapsed",
    )

    history = fetch_history(symbol, period)
    if history.empty or len(history) < 20:
        st.info("Historique insuffisant pour simuler un investissement programmé.")
        return

    prices = (pd.to_numeric(history["Close"], errors="coerce") * fx_rate).dropna()
    monthly_prices = prices.resample("BMS").first().dropna()
    monthly_prices = monthly_prices[monthly_prices > 0]

    if monthly_prices.empty:
        st.info("Aucun prix mensuel exploitable sur la période sélectionnée.")
        return

    total_invested = 0.0
    shares = 0.0
    rows = []

    for date, price in monthly_prices.items():
        shares += float(monthly_amount) / float(price)
        total_invested += float(monthly_amount)
        rows.append(
            {
                "Date": date,
                "Capital investi": total_invested,
                "Valeur portefeuille": shares * float(price),
                "Parts cumulées": shares,
            }
        )

    dca = pd.DataFrame(rows).set_index("Date")
    final_value = float(dca["Valeur portefeuille"].iloc[-1])
    gain = final_value - total_invested
    performance = (gain / total_invested) * 100 if total_invested > 0 else 0.0

    result_label = "Plus-value" if gain >= 0 else "Moins-value"
    st.success(
        f"Capital investi: {total_invested:,.2f} € | "
        f"Valeur finale: {final_value:,.2f} € | "
        f"{result_label}: {gain:,.2f} € | Rendement total: {performance:.2f}%"
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dca.index,
            y=dca["Capital investi"],
            name="Capital Total Investi",
            line=dict(color="#8ea0b4", width=2, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dca.index,
            y=dca["Valeur portefeuille"],
            name="Valeur Réelle du Portefeuille",
            fill="tozeroy",
            line=dict(color="#31c48d", width=2.4),
        )
    )
    fig.update_layout(
        height=460,
        template="plotly_dark",
        paper_bgcolor="#0b0f14",
        plot_bgcolor="#111820",
        margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="#263241")
    fig.update_yaxes(title_text="€", gridcolor="#263241")
    st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# RENDU ACTIONS / ETF / MATRICE
# =============================================================================

def render_header(data: Dict[str, Any], is_etf: bool) -> None:
    st.markdown(
        f"""
        <div class="terminal-header">
            <div class="terminal-title">{html_escape(data.get('Nom', APP_NAME))}</div>
            <div class="terminal-subtitle">{html_escape(data.get('Ticker', ''))} · {html_escape(data.get('Type', ''))} · Devise source {html_escape(data.get('Devise', 'N/A'))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Prix actuel", format_metric(data.get("Prix"), "€"), tone="accent", raw_value=data.get("Prix"))
    with c2:
        cap_title = "AUM" if is_etf else "Capitalisation"
        metric_card(cap_title, format_compact_eur(data.get("Capitalisation_MEUR")), raw_value=data.get("Capitalisation_MEUR"))
    with c3:
        metric_card("Score global", format_metric(data.get("Score"), "/100", decimals=0), raw_value=data.get("Score"))
        st.progress(min(int(data.get("Score", 0) or 0), 100) / 100)
    with c4:
        if is_etf:
            metric_card("Frais courants", format_metric(data.get("TER"), "%"), raw_value=data.get("TER"))
        else:
            metric_card("Consensus", format_metric(data.get("Target"), "€"), subtitle=f"{data.get('Reco', 'N/A')} · {data.get('Analystes', 'N/A')} analystes", tone="accent", raw_value=data.get("Target"))

    render_source_badges("Yahoo Finance", "Morningstar prioritaire", "Google News RSS", f"Validation croisée: {DATA_NOT_VALIDATED}")


def render_stock_fundamentals(data: Dict[str, Any]) -> None:
    section_title("Valorisation & Prix")
    cols = st.columns(4)
    metrics = [
        ("PER Actuel", format_metric(data.get("PER_Actuel"), "x"), data.get("PER_Actuel")),
        ("PER Futur", format_metric(data.get("PER_Futur"), "x"), data.get("PER_Futur")),
        ("Price to Sales", format_metric(data.get("PS"), "x"), data.get("PS")),
        ("Price to Book", format_metric(data.get("PB"), "x"), data.get("PB")),
        ("EV / EBITDA", format_metric(data.get("EV_EBITDA"), "x"), data.get("EV_EBITDA")),
        ("BPA", format_metric(data.get("BPA"), "€"), data.get("BPA")),
        ("Valeur Comptable / Action", format_metric(data.get("BVPS"), "€"), data.get("BVPS")),
        ("Prix Théorique de Graham", format_metric(data.get("Graham"), "€"), data.get("Graham")),
    ]
    for idx, (title, value, raw_value) in enumerate(metrics):
        with cols[idx % 4]:
            metric_card(title, value, tone="compact", raw_value=raw_value)

    section_title("Rentabilité & Performance")
    cols = st.columns(5)
    metrics = [
        ("Marge Brute", format_metric(data.get("Marge_Brute"), "%"), data.get("Marge_Brute")),
        ("Marge Opérationnelle", format_metric(data.get("Marge_Op"), "%"), data.get("Marge_Op")),
        ("Marge Nette", format_metric(data.get("Marge_Nette"), "%"), data.get("Marge_Nette")),
        ("ROE", format_metric(data.get("ROE"), "%"), data.get("ROE")),
        ("ROA", format_metric(data.get("ROA"), "%"), data.get("ROA")),
    ]
    for idx, (title, value, raw_value) in enumerate(metrics):
        with cols[idx]:
            metric_card(title, value, tone="compact", raw_value=raw_value)

    section_title("Santé Financière, Bilan & Risque")
    cols = st.columns(3)
    metrics = [
        ("Dette Nette", format_metric(data.get("Dette_Nette"), "M€"), data.get("Dette_Nette")),
        ("EBITDA", format_metric(data.get("EBITDA"), "M€"), data.get("EBITDA")),
        ("Dette Nette / EBITDA", format_metric(data.get("Levier"), "x"), data.get("Levier")),
        ("Current Ratio", format_metric(data.get("Current_Ratio")), data.get("Current_Ratio")),
        ("Quick Ratio", format_metric(data.get("Quick_Ratio")), data.get("Quick_Ratio")),
        ("Debt to Equity", format_metric(data.get("Debt_Equity"), "%"), data.get("Debt_Equity")),
    ]
    for idx, (title, value, raw_value) in enumerate(metrics):
        with cols[idx % 3]:
            metric_card(title, value, tone="compact", raw_value=raw_value)

    section_title("Croissance & Dividendes")
    cols = st.columns(4)
    with cols[0]:
        metric_card("Revenue Growth", format_metric(data.get("Rev_Growth"), "%"), tone="compact", raw_value=data.get("Rev_Growth"))
    with cols[1]:
        metric_card("Payout Ratio", format_metric(data.get("Payout"), "%"), tone="compact", raw_value=data.get("Payout"))
    with cols[2]:
        metric_card("Rendement Dividende", format_metric(data.get("Dividend_Yield"), "%"), tone="compact", raw_value=data.get("Dividend_Yield"))
    with cols[3]:
        metric_card("Secteur", html_escape(data.get("Sector", "N/A")), subtitle=data.get("Industry", "N/A"), tone="compact")


def render_etf_fundamentals(data: Dict[str, Any]) -> None:
    if data.get("AUM") is not None and data.get("AUM") < 100:
        st.error("Alerte liquidité : encours inférieur à 100 M€.")

    section_title("Profil ETF")
    cols = st.columns(5)
    metrics = [
        ("Frais de gestion", format_metric(data.get("TER"), "%"), data.get("TER")),
        ("Encours", format_compact_eur(data.get("AUM")), data.get("AUM")),
        ("Distribution", html_escape(data.get("Distribution", DATA_NOT_VALIDATED)), data.get("Distribution")),
        ("Réplication", html_escape(data.get("Replication", DATA_NOT_VALIDATED)), data.get("Replication")),
        ("Fiscalité", html_escape(data.get("Fiscalite", DATA_NOT_VALIDATED)), data.get("Fiscalite")),
    ]
    for idx, (title, value, raw_value) in enumerate(metrics):
        with cols[idx]:
            metric_card(title, value, tone="compact", raw_value=raw_value)

    cols = st.columns(2)
    with cols[0]:
        metric_card("Tendance Tracking Difference", html_escape(data.get("Tracking", DATA_NOT_VALIDATED)), tone="compact")
    with cols[1]:
        metric_card("Rendement Distribution", format_metric(data.get("Dividend_Yield"), "%"), tone="compact", raw_value=data.get("Dividend_Yield"))


def render_press_section(data: Dict[str, Any], is_etf: bool) -> None:
    news = fetch_press_news(data.get("Ticker", ""), data.get("Nom", ""))
    section_title("Résumé Exécutif du Consensus")
    st.markdown(
        f"<div class='verdict'><p style='margin:0;color:#c9d1d9;'>{html_escape(build_consensus_summary(data, is_etf, len(news)))}</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown(build_expert_verdict(data, is_etf), unsafe_allow_html=True)

    section_title("Presse Morningstar & Marché")
    if not news:
        st.info("Aucune actualité exploitable pour cet actif.")
        return

    for article in news:
        st.markdown(
            f"""
            <div class="news-card">
                <a href="{html_escape(article['link'])}" target="_blank" rel="noopener noreferrer">{html_escape(article['title'])}</a>
                <div class="news-meta">{html_escape(article['publisher'])} · {html_escape(article['published'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def matrix_display_value(value: Any, suffix: str = "", decimals: int = 2) -> str:
    if is_missing(value):
        return "N/A"
    if isinstance(value, str):
        return value
    numeric = safe_float(value, precision=decimals)
    if numeric is None:
        return "N/A"
    return f"{numeric:,.{decimals}f}".replace(",", " ") + (f" {suffix}" if suffix else "")


def matrix_cell_class(label: str, value: Any) -> str:
    if is_missing(value):
        return "matrix-cell-na"
    if isinstance(value, str):
        lowered = value.lower()
        if value == CASH_POSITIVE or "robuste" in lowered or "pea" in lowered:
            return "matrix-cell-good"
        if "risque" in lowered or "non validée" in lowered:
            return "matrix-cell-bad"
        return ""
    tone = infer_metric_tone(label, value)
    if tone == "good":
        return "matrix-cell-good"
    if tone == "warn":
        return "matrix-cell-warn"
    if tone == "bad":
        return "matrix-cell-bad"
    return ""


def render_matrix_table(
    title: str,
    kicker: str,
    rows: List[Dict[str, Any]],
    columns: List[Dict[str, Any]],
) -> None:
    if not rows:
        return

    header_html = "".join(f"<th>{html_escape(col['label'])}</th>" for col in columns)
    body_rows = []
    for row in rows:
        cells = []
        for col in columns:
            key = col["key"]
            label = col["label"]
            value = row.get(key)
            decimals = int(col.get("decimals", 2))
            suffix = col.get("suffix", "")
            display = matrix_display_value(value, suffix=suffix, decimals=decimals)
            css_class = matrix_cell_class(label, value)
            if key == "Ticker":
                css_class = f"{css_class} matrix-symbol".strip()
            if key == "Nom":
                css_class = f"{css_class} matrix-name".strip()
            cells.append(f"<td class='{html_escape(css_class)}'>{html_escape(display)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    st.markdown(
        f"""
        <div class="matrix-card">
            <div class="matrix-head">
                <div>
                    <div class="matrix-kicker">{html_escape(kicker)}</div>
                    <div class="matrix-title">{html_escape(title)}</div>
                </div>
                <div class="matrix-count">{len(rows)} actif{'s' if len(rows) > 1 else ''}</div>
            </div>
            <div class="matrix-scroll">
                <table class="matrix-table">
                    <thead><tr>{header_html}</tr></thead>
                    <tbody>{"".join(body_rows)}</tbody>
                </table>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def rows_to_export_frame(rows: List[Dict[str, Any]], columns: List[Dict[str, Any]]) -> pd.DataFrame:
    records = []
    for row in rows:
        record = {}
        for col in columns:
            record[col["label"]] = row.get(col["key"], "N/A")
        records.append(record)
    return pd.DataFrame(records)


def load_asset(symbol: str) -> Optional[Dict[str, Any]]:
    if not symbol:
        return None

    yahoo_symbol = normalize_yahoo_symbol(symbol)
    payload = fetch_yahoo_payload(yahoo_symbol)
    info = payload.get("info", {})
    fast_info = payload.get("fast_info", {})
    short_history = fetch_history(yahoo_symbol, "1mo")

    if not info and not fast_info and short_history.empty:
        return None

    currency = get_currency(info, fast_info)
    fx_rate = get_fx_rate_to_eur(currency)
    etf = is_etf_asset(info, yahoo_symbol)

    if etf:
        data = extract_etf_data(yahoo_symbol, info, fast_info, fx_rate, short_history)
    else:
        data = extract_stock_data(yahoo_symbol, info, fast_info, fx_rate, short_history)

    data["_fx_rate"] = fx_rate
    data["_is_etf"] = etf
    data["_requested_symbol"] = safe_str(symbol, yahoo_symbol).upper()
    return data


def render_single_terminal() -> None:
    symbol = st.text_input(
        "Ticker",
        placeholder="AAPL, LVMH.PA, ASML.AS, GSK.L, CW8.PA",
        label_visibility="collapsed",
    ).upper().strip()

    if not symbol:
        st.markdown(
            """
            <div class="terminal-header">
                <div class="terminal-title">Alpha Terminal Pro</div>
                <div class="terminal-subtitle">Terminal financier multi-actifs · Actions · ETF · DCA · Presse Morningstar & marché</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    with st.spinner("Acquisition des données financières..."):
        data = load_asset(symbol)

    if data is None:
        st.error("Donnée non validée. Ticker introuvable ou flux indisponible.")
        return

    is_etf = bool(data.get("_is_etf"))
    fx_rate = float(data.get("_fx_rate", 1.0))
    chart_symbol = safe_str(data.get("Ticker"), symbol)

    render_header(data, is_etf)

    tabs = st.tabs(["Fondamentaux", "Technique", "DCA", "Consensus & Presse"])
    with tabs[0]:
        if is_etf:
            render_etf_fundamentals(data)
        else:
            render_stock_fundamentals(data)
    with tabs[1]:
        render_technical_chart(chart_symbol, fx_rate)
    with tabs[2]:
        render_dca_simulator(chart_symbol, fx_rate)
    with tabs[3]:
        render_press_section(data, is_etf)


def build_comparison_row(symbol: str) -> Optional[Dict[str, Any]]:
    data = load_asset(symbol)
    if data is None:
        return None

    if data.get("Type") == "Action":
        return {
            "Ticker": data.get("Ticker"),
            "Nom": data.get("Nom"),
            "Type": "Action",
            "Score": data.get("Score"),
            "Prix": data.get("Prix"),
            "MarketCap": data.get("Capitalisation_MEUR"),
            "PER": data.get("PER_Actuel"),
            "Marge_Nette": data.get("Marge_Nette"),
            "Levier": data.get("Levier"),
            "Rev_Growth": data.get("Rev_Growth"),
            "Dividend_Yield": data.get("Dividend_Yield"),
            "Reco": data.get("Reco"),
        }

    aum = data.get("AUM")
    if aum is None:
        liquidity = "Donnée non validée"
    elif aum >= 100:
        liquidity = "Robuste"
    else:
        liquidity = "Risque < 100 M€"

    return {
        "Ticker": data.get("Ticker"),
        "Nom": data.get("Nom"),
        "Type": data.get("Type"),
        "Score": data.get("Score"),
        "Prix": data.get("Prix"),
        "AUM": data.get("AUM"),
        "TER": data.get("TER"),
        "Distribution": data.get("Distribution"),
        "Replication": data.get("Replication"),
        "Fiscalite": data.get("Fiscalite"),
        "Dividend_Yield": data.get("Dividend_Yield"),
        "Liquidite": liquidity,
    }


def render_comparator() -> None:
    st.markdown(
        """
        <div class="terminal-header">
            <div class="terminal-title">Comparateur Multi-Actifs</div>
            <div class="terminal-subtitle">Matrices séparées pour actions, ETF et indices · colonnes adaptées à chaque univers</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="comparison-control">
            <div class="matrix-kicker">Univers</div>
            <div class="matrix-title">Tickers à comparer</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    raw = st.text_input(
        "Matrice",
        placeholder="AAPL, MSFT, LVMH.PA, NVDA, CW8.PA, ESE.PA",
        label_visibility="collapsed",
    )

    if not raw:
        return

    symbols = []
    for item in raw.split(","):
        item = item.strip().upper()
        if item and item not in symbols:
            symbols.append(item)

    rows: List[Dict[str, Any]] = []
    with st.spinner("Construction de la matrice multi-actifs..."):
        for symbol in symbols:
            row = build_comparison_row(symbol)
            if row is not None:
                rows.append(row)

    if not rows:
        st.error("Aucune donnée exploitable n'a pu être extraite.")
        return

    etf_rows = [row for row in rows if row.get("Type") != "Action"]
    action_rows = [row for row in rows if row.get("Type") == "Action"]

    etf_rows = sorted(
        etf_rows,
        key=lambda row: (
            safe_float(row.get("Score")) or -1,
            safe_float(row.get("AUM")) or -1,
            -(safe_float(row.get("TER")) if safe_float(row.get("TER")) is not None else 999),
        ),
        reverse=True,
    )
    action_rows = sorted(
        action_rows,
        key=lambda row: (
            safe_float(row.get("Score")) or -1,
            safe_float(row.get("MarketCap")) or -1,
        ),
        reverse=True,
    )

    all_scores = [safe_float(row.get("Score"), precision=0) for row in rows if safe_float(row.get("Score")) is not None]
    best_score = max(all_scores) if all_scores else None
    ter_values = [safe_float(row.get("TER")) for row in etf_rows if safe_float(row.get("TER")) is not None]
    best_ter = min(ter_values) if ter_values else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("ETF & Indices", format_metric(len(etf_rows), decimals=0), raw_value=len(etf_rows))
    with c2:
        metric_card("Actions", format_metric(len(action_rows), decimals=0), raw_value=len(action_rows))
    with c3:
        metric_card("Meilleur Score", format_metric(best_score, "/100", decimals=0), raw_value=best_score)
    with c4:
        metric_card("TER Minimum", format_metric(best_ter, "%"), raw_value=best_ter)

    etf_columns = [
        {"key": "Ticker", "label": "Ticker", "decimals": 0},
        {"key": "Nom", "label": "Nom", "decimals": 0},
        {"key": "Type", "label": "Type", "decimals": 0},
        {"key": "Score", "label": "Score ETF", "decimals": 0, "suffix": "/100"},
        {"key": "Prix", "label": "Prix", "decimals": 2, "suffix": "€"},
        {"key": "AUM", "label": "AUM", "decimals": 2, "suffix": "M€"},
        {"key": "TER", "label": "TER", "decimals": 2, "suffix": "%"},
        {"key": "Distribution", "label": "Distribution", "decimals": 0},
        {"key": "Replication", "label": "Réplication", "decimals": 0},
        {"key": "Fiscalite", "label": "Fiscalité", "decimals": 0},
        {"key": "Liquidite", "label": "Liquidité", "decimals": 0},
        {"key": "Dividend_Yield", "label": "Rendement", "decimals": 2, "suffix": "%"},
    ]
    action_columns = [
        {"key": "Ticker", "label": "Ticker", "decimals": 0},
        {"key": "Nom", "label": "Nom", "decimals": 0},
        {"key": "Score", "label": "Score", "decimals": 0, "suffix": "/100"},
        {"key": "Prix", "label": "Prix", "decimals": 2, "suffix": "€"},
        {"key": "MarketCap", "label": "Capitalisation", "decimals": 2, "suffix": "M€"},
        {"key": "PER", "label": "PER", "decimals": 2, "suffix": "x"},
        {"key": "Marge_Nette", "label": "Marge nette", "decimals": 2, "suffix": "%"},
        {"key": "Levier", "label": "Dette nette / EBITDA", "decimals": 2, "suffix": "x"},
        {"key": "Rev_Growth", "label": "Croissance CA", "decimals": 2, "suffix": "%"},
        {"key": "Dividend_Yield", "label": "Rendement", "decimals": 2, "suffix": "%"},
        {"key": "Reco", "label": "Recommandation", "decimals": 0},
    ]

    export_frames = []
    if etf_rows:
        render_matrix_table("ETF & Indices", "Matrice indicielle", etf_rows, etf_columns)
        export_frames.append(rows_to_export_frame(etf_rows, etf_columns))
    if action_rows:
        render_matrix_table("Actions", "Matrice fondamentale", action_rows, action_columns)
        export_frames.append(rows_to_export_frame(action_rows, action_columns))

    export_df = pd.concat(export_frames, ignore_index=True, sort=False).fillna("N/A")
    csv = export_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Télécharger CSV",
        data=csv,
        file_name="alpha_terminal_pro_matrice.csv",
        mime="text/csv",
        use_container_width=True,
    )


# =============================================================================
# APPLICATION
# =============================================================================

with st.sidebar:
    st.markdown("### Alpha Terminal Pro")
    mode = st.radio(
        "Navigation",
        ["Terminal Quantitatif", "Comparateur Matrice"],
        label_visibility="collapsed",
    )
    st.caption("Sources: Yahoo Finance · Morningstar prioritaire · Google News RSS")

if mode == "Terminal Quantitatif":
    render_single_terminal()
else:
    render_comparator()

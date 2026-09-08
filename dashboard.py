"""
ContractSentinel dashboard - Streamlit frontend for the SLA/Contract
Obligation Monitor. Handles auth, contract upload, AI extraction results,
deadline tracking, and audit trail, all backed by the FastAPI API.
"""
import os
import re
import time
import csv
import io
import base64
from datetime import datetime, timedelta
import requests
import streamlit as st
import extra_streamlit_components as stx

# ── Asset Paths (defined early - page_icon needs this before set_page_config) ──
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
HANDSHAKE_IMG = os.path.join(ASSETS_DIR, "handshake.jpg")
AUDIT_IMG = os.path.join(ASSETS_DIR, "audit.jpg")
CONTRACT_IMG = os.path.join(ASSETS_DIR, "contract_signing.png")
LOGO_IMG = os.path.join(ASSETS_DIR, "logo.png")
FAVICON_IMG = os.path.join(ASSETS_DIR, "favicon.png")

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ContractSentinel — SLA & Obligation Compliance Platform",
    page_icon=FAVICON_IMG if os.path.exists(FAVICON_IMG) else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── API Backend Configuration ──────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_TIMEOUT = 8  # seconds – generous enough to absorb a slow first request after a backend restart

# ── Executive CSS Styling (Dark & Light Mode Compatible) ───────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }

    /* Hide Streamlit Header, Deploy Button, & Developer Toolbar */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stHeader"] {display: none;}
    [data-testid="stToolbar"] {display: none;}

    .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }

    /* ── Top Brand Bar ─────────────────────────────────────────────────── */
    .sentinel-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 28px;
        background-color: #0B1220;
        border-radius: 14px;
        margin-bottom: 28px;
    }
    .sentinel-topbar-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        color: #F8FAFC !important;
        font-weight: 800;
        font-size: 1.15rem;
        letter-spacing: -0.02em;
    }
    .sentinel-topbar-tag {
        color: #94A3B8 !important;
        font-size: 0.8rem;
        font-weight: 500;
    }

    /* ── Dark Gradient Hero (landing page) ─────────────────────────────── */
    .sentinel-dark-hero {
        background: radial-gradient(circle at 30% 20%, #134E4A 0%, #0B1220 55%, #0B1220 100%);
        border-radius: 20px;
        padding: 64px 48px;
        margin-bottom: 24px;
        text-align: center;
    }

    .sentinel-dark-badge {
        display: inline-block;
        border: 1px solid rgba(148, 163, 184, 0.35);
        color: #E2E8F0 !important;
        background-color: rgba(255,255,255,0.04);
        padding: 8px 22px;
        border-radius: 30px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 28px;
    }

    .sentinel-dark-title {
        font-size: 3.2rem;
        font-weight: 800;
        color: #FFFFFF !important;
        letter-spacing: -0.04em;
        line-height: 1.08;
        margin-bottom: 20px;
    }

    .sentinel-dark-subtitle {
        font-size: 1.15rem;
        color: #94A3B8 !important;
        font-weight: 400;
        line-height: 1.6;
        max-width: 640px;
        margin: 0 auto;
    }

    /* ── Light Hero (in-app, on Compliance Overview) ───────────────────── */
    .sentinel-hero-banner {
        background: linear-gradient(135deg, #DBE2FE 0%, #EFF6FF 100%);
        border-radius: 16px;
        padding: 32px 36px;
        margin-bottom: 24px;
        border: 1px solid #BFDBFE;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.08);
    }

    .sentinel-hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #0F172A !important;
        letter-spacing: -0.03em;
        line-height: 1.15;
        margin-bottom: 10px;
    }

    .sentinel-hero-subtitle {
        font-size: 1.02rem;
        color: #334155 !important;
        font-weight: 400;
        line-height: 1.55;
    }

    /* Category Badges */
    .tag-container {
        display: flex;
        gap: 8px;
        margin-bottom: 14px;
        justify-content: center;
    }

    .tag-teal {
        background-color: #064E3B;
        color: #ECFDF5 !important;
        padding: 5px 16px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .tag-primary {
        background-color: #2563EB;
        color: #FFFFFF !important;
        padding: 5px 16px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* ── Pill CTA Buttons (overrides default Streamlit button) ─────────── */
    .stButton > button {
        border-radius: 999px !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.4rem !important;
        transition: all 0.18s ease !important;
        border: 1px solid rgba(148, 163, 184, 0.3) !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.28) !important;
    }

    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.38) !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
    }

    /* Floating KPI Cards */
    .kpi-card {
        border: 1px solid rgba(226, 232, 240, 0.6);
        border-radius: 14px;
        padding: 22px 18px;
        text-align: center;
        background-color: var(--secondary-background-color, #FFFFFF);
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(59, 130, 246, 0.14);
    }

    .kpi-value {
        font-size: 2.2rem;
        font-weight: 800;
        line-height: 1.1;
        color: var(--text-color, #0F172A);
        letter-spacing: -0.02em;
    }

    .kpi-label {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        opacity: 0.7;
        margin-top: 8px;
    }

    /* Status Badges */
    .status-breached {
        color: #991B1B !important;
        background-color: #FEE2E2;
        border: 1px solid #FCA5A5;
        padding: 5px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        display: inline-block;
    }

    .status-upcoming {
        color: #92400E !important;
        background-color: #FEF3C7;
        border: 1px solid #FDE68A;
        padding: 5px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        display: inline-block;
    }

    .status-pending {
        color: #075985 !important;
        background-color: #E0F2FE;
        border: 1px solid #BAE6FD;
        padding: 5px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        display: inline-block;
    }

    .status-completed {
        color: #166534 !important;
        background-color: #DCFCE7;
        border: 1px solid #86EFAC;
        padding: 5px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        display: inline-block;
    }

    /* Disable image zoom/fullscreen - business dashboards shouldn't have
       decorative photos behave like an interactive gallery */
    button[title="View fullscreen"] {
        display: none !important;
    }
    [data-testid="StyledFullScreenButton"] {
        display: none !important;
    }

    /* Round the corners on embedded photos to match the rest of the design */
    [data-testid="stImage"] img {
        border-radius: 16px;
    }

    /* Reference numbers / IDs shown for record-keeping - de-emphasized,
       not styled as prominent as business-relevant fields */
    .reference-tag {
        color: #94A3B8;
        font-size: 0.72rem;
        font-family: monospace;
    }

    .source-tag {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 2px 10px;
        border-radius: 10px;
        background-color: #F1F5F9;
        color: #475569;
        margin-top: 4px;
    }

    /* ── Obligation Cards (colored left border by status) ──────────────── */
    .obligation-card {
        background-color: #F8FAFC;
        border-left: 5px solid #94A3B8;
        border-radius: 10px;
        padding: 14px 20px;
        margin-bottom: 10px;
    }
    .obligation-card.status-border-breached { border-left-color: #DC2626; }
    .obligation-card.status-border-upcoming { border-left-color: #D97706; }
    .obligation-card.status-border-pending { border-left-color: #0EA5E9; }
    .obligation-card.status-border-completed { border-left-color: #16A34A; opacity: 0.72; }

    .obligation-card-title {
        font-size: 1rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 6px;
    }

    .obligation-card-meta {
        display: flex;
        gap: 22px;
        flex-wrap: wrap;
        align-items: center;
        font-size: 0.85rem;
        color: #475569;
    }

    /* ── User Avatar (topbar) ────────────────────────────────────────── */
    .sentinel-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: linear-gradient(135deg, #7C3AED 0%, #4338CA 100%);
        color: #FFFFFF !important;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.82rem;
        flex-shrink: 0;
    }

    .sentinel-topbar-right {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    /* ── Status Ring Chart (pure CSS, no chart library needed) ─────────── */
    .status-ring-wrap {
        display: flex;
        align-items: center;
        gap: 20px;
        height: 100%;
        padding: 12px;
    }

    .status-ring {
        width: 130px;
        height: 130px;
        border-radius: 50%;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
    }

    .status-ring-inner {
        width: 84px;
        height: 84px;
        border-radius: 50%;
        background-color: #FFFFFF;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    .status-ring-inner-value {
        font-size: 1.5rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1;
    }

    .status-ring-inner-label {
        font-size: 0.6rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-top: 2px;
    }

    .status-ring-legend {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .status-ring-legend-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.82rem;
        color: #334155;
    }

    .status-ring-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    /* ── KPI Context Pills (gives raw numbers meaning) ──────────────────── */
    .kpi-context {
        display: inline-block;
        font-size: 0.62rem;
        font-weight: 700;
        padding: 2px 9px;
        border-radius: 8px;
        margin-top: 8px;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }
    .kpi-context-good { background-color: #DCFCE7; color: #166534; }
    .kpi-context-warn { background-color: #FEF3C7; color: #92400E; }
    .kpi-context-bad { background-color: #FEE2E2; color: #991B1B; }
    .kpi-context-neutral { background-color: #F1F5F9; color: #475569; }

    /* ── Footer ──────────────────────────────────────────────────────── */
    .sentinel-footer {
        text-align: center;
        color: #94A3B8;
        font-size: 0.8rem;
        padding: 28px 0 12px 0;
    }
    .sentinel-footer a {
        color: #94A3B8 !important;
        text-decoration: underline;
    }
    .sentinel-logomark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border-radius: 7px;
        background: linear-gradient(135deg, #7C3AED 0%, #4338CA 100%);
        color: #FFFFFF !important;
        font-weight: 800;
        font-size: 0.7rem;
        letter-spacing: -0.02em;
        flex-shrink: 0;
    }

    .sentinel-logomark-img {
        width: 30px;
        height: 30px;
        border-radius: 7px;
        object-fit: cover;
        vertical-align: middle;
        flex-shrink: 0;
    }

    /* Small colored status dot - used instead of emoji circles */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
    }
    /* Labeled Callout Cards - small pill label above a bold value, the way
       Sirion and other enterprise contract tools display extracted fields */
    .callout-group {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 14px;
    }

    .callout-group-index {
        font-size: 0.72rem;
        font-weight: 700;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 10px;
    }

    .callout-row {
        display: flex;
        gap: 14px;
        flex-wrap: wrap;
    }

    .callout-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px 16px;
        flex: 1;
        min-width: 180px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    }

    .callout-card.callout-wide {
        flex-basis: 100%;
    }

    .callout-label {
        display: inline-block;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 3px 10px;
        border-radius: 8px;
        margin-bottom: 8px;
    }

    .callout-label-obligation { background-color: #EDE9FE; color: #5B21B6; }
    .callout-label-date { background-color: #DBEAFE; color: #1E40AF; }
    .callout-label-penalty { background-color: #FEF3C7; color: #92400E; }

    .callout-value {
        font-size: 0.95rem;
        font-weight: 600;
        color: #0F172A;
        line-height: 1.4;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def get_base64_image(path):
    """Reads an image file and returns it as a base64 data URI for embedding in HTML."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(path)[1].lstrip(".") or "png"
    return f"data:image/{ext};base64,{encoded}"


def render_topbar(show_avatar=False):
    """Consistent enterprise brand bar shown on every screen, signed in or not."""
    avatar_html = ""
    if show_avatar and st.session_state.user_email:
        initials = get_initials(st.session_state.user_email)
        avatar_html = f"<div class='sentinel-avatar'>{initials}</div>"

    logo_data_uri = get_base64_image(LOGO_IMG)
    if logo_data_uri:
        brand_mark = f"<img src='{logo_data_uri}' class='sentinel-logomark-img' />"
    else:
        brand_mark = "<span class='sentinel-logomark'>CS</span>"

    topbar_html = (
        "<div class='sentinel-topbar'>"
        f"<div class='sentinel-topbar-brand'>{brand_mark} ContractSentinel</div>"
        "<div class='sentinel-topbar-right'>"
        "<div class='sentinel-topbar-tag'>Enterprise SLA &amp; Obligation Compliance</div>"
        f"{avatar_html}"
        "</div>"
        "</div>"
    )
    st.markdown(topbar_html, unsafe_allow_html=True)


def friendly_error(response, fallback="Something went wrong. Please try again, or contact your administrator if this continues."):
    """Extracts a clean, business-readable message from an API error response."""
    try:
        detail = response.json().get("detail")
        if detail and isinstance(detail, str):
            return detail
    except Exception:
        pass
    return fallback


CONNECTION_ERROR_MSG = "We couldn't reach the system right now. Please try again in a moment, or contact your administrator if this continues."


# --- Extraction time estimate ---
# Mirrors the server's actual chunking (app/services/extraction.py:
# CHUNK_SIZE=12000, CHUNK_OVERLAP=300) so the estimate is grounded in what
# will really happen, not a guess. Per-chunk timing assumes the Gemini
# free-tier limit of 5 requests/minute: the first 5 chunks go through at
# roughly normal API latency, and anything beyond that gets throttled to
# ~1 chunk per 12 seconds. This is an estimate, not a guarantee - actual
# API latency varies - so it's always shown as a range.
_CHUNK_SIZE = 12_000
_CHUNK_OVERLAP = 300
_SECONDS_PER_CHUNK_UNTHROTTLED = 25  # observed: dense legal text with a
                                      # complex structured schema regularly
                                      # takes Gemini 20-40s+ per chunk, not
                                      # the few seconds a simple chat call
                                      # would take - corrected from an
                                      # earlier, too-optimistic assumption
_SECONDS_PER_CHUNK_THROTTLED = 35
_FREE_TIER_BURST = 5


def estimate_chunk_count(content_length: int) -> int:
    if content_length <= _CHUNK_SIZE:
        return 1
    step = _CHUNK_SIZE - _CHUNK_OVERLAP
    return 1 + -(-(content_length - _CHUNK_SIZE) // step)  # ceil division


def estimate_extraction_seconds(content_length: int):
    """Returns (low, high) estimated seconds for extraction to complete."""
    chunks = estimate_chunk_count(content_length)
    if chunks <= _FREE_TIER_BURST:
        best = chunks * _SECONDS_PER_CHUNK_UNTHROTTLED
    else:
        best = (_FREE_TIER_BURST * _SECONDS_PER_CHUNK_UNTHROTTLED) + (
            (chunks - _FREE_TIER_BURST) * _SECONDS_PER_CHUNK_THROTTLED
        )
    low = max(5, int(best * 0.7))
    high = int(best * 1.6) + 10
    return low, high


def format_seconds(s: int) -> str:
    return f"{s}s" if s < 60 else f"{s // 60}m {s % 60}s"


def format_seconds_range(low: int, high: int) -> str:
    return f"{format_seconds(low)} - {format_seconds(high)}"
TIMEOUT_ERROR_MSG = "This is taking longer than expected. Please try again in a moment."


def get_initials(email):
    """Turns an email like 'jane.doe@company.com' into 'JD' for the avatar badge."""
    if not email:
        return "?"
    local = email.split("@")[0]
    parts = [p for p in re.split(r"[._\-+]", local) if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return local[:2].upper()


def render_status_ring(breached, upcoming, pending, completed):
    """A dependency-free donut chart built with a CSS conic-gradient, so we
    don't need to add plotly/altair just to show a proportion breakdown."""
    total = breached + upcoming + pending + completed
    colors = {
        "breached": "#DC2626",
        "upcoming": "#D97706",
        "pending": "#0EA5E9",
        "completed": "#16A34A",
    }

    if total == 0:
        gradient = "#E2E8F0"
    else:
        segments = [
            ("breached", breached), ("upcoming", upcoming),
            ("pending", pending), ("completed", completed),
        ]
        stops = []
        cursor = 0.0
        for name, count in segments:
            if count <= 0:
                continue
            start_pct = (cursor / total) * 100
            cursor += count
            end_pct = (cursor / total) * 100
            stops.append(f"{colors[name]} {start_pct:.1f}% {end_pct:.1f}%")
        gradient = ", ".join(stops) if stops else "#E2E8F0"

    legend_items = [
        ("Missed Deadline", colors["breached"], breached),
        ("Due Soon", colors["upcoming"], upcoming),
        ("Not Yet Due", colors["pending"], pending),
        ("Completed", colors["completed"], completed),
    ]
    legend_html = "".join(
        f"<div class='status-ring-legend-item'><span class='status-ring-dot' style='background-color:{color};'></span>{label}: <strong>{count}</strong></div>"
        for label, color, count in legend_items
    )

    return f"""
    <div class='status-ring-wrap'>
        <div class='status-ring' style='background: conic-gradient({gradient});'>
            <div class='status-ring-inner'>
                <div class='status-ring-inner-value'>{total}</div>
                <div class='status-ring-inner-label'>Total</div>
            </div>
        </div>
        <div class='status-ring-legend'>{legend_html}</div>
    </div>
    """


def kpi_context_pill(text, tone="neutral"):
    """Small colored pill under a KPI value, e.g. 'Needs attention' - gives
    a raw number meaning at a glance instead of leaving it ambiguous."""
    return f"<div class='kpi-context kpi-context-{tone}'>{text}</div>"

# ── Session State Management ───────────────────────────────────────────────────
# key= keeps this stable across reruns - must not be @st.cache_resource, since
# the constructor itself makes a component call, which caching disallows.
cookie_manager = stx.CookieManager(key="sla_cookie_manager")


def safe_delete_cookie(name, key):
    """CookieManager.delete() raises KeyError internally if the cookie isn't
    already in its own cache dict - guard against that library quirk."""
    try:
        cookie_manager.delete(name, key=key)
    except KeyError:
        pass

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Restores a previous session from a cookie so a refresh doesn't log you out.
if not st.session_state.access_token:
    cookies = cookie_manager.cookies
    stored_token = cookies.get("sla_access_token") if cookies else None
    stored_email = cookies.get("sla_user_email") if cookies else None

    if stored_token and stored_email:
        with st.spinner("Restoring your session..."):
            try:
                verify_res = requests.get(
                    f"{API_BASE_URL}/contracts/",
                    headers={"Authorization": f"Bearer {stored_token}"},
                    timeout=API_TIMEOUT,
                )
                if verify_res.status_code == 200:
                    st.session_state.access_token = stored_token
                    st.session_state.user_email = stored_email
                else:
                    safe_delete_cookie("sla_access_token", key="del_expired_token")
                    safe_delete_cookie("sla_user_email", key="del_expired_email")
            except Exception:
                pass  # Backend unreachable - show the login screen normally
    elif not cookies and "cookie_retry_done" not in st.session_state:
        # Cookie may not have arrived from the browser yet - retry once.
        st.session_state.cookie_retry_done = True
        st.markdown(
            "<div style='text-align:center; padding-top:120px;'>"
            "<p style='color:#94A3B8;'>Loading ContractSentinel...</p></div>",
            unsafe_allow_html=True,
        )
        time.sleep(0.6)
        st.rerun()


def get_headers():
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}


def execute_login(email, password):
    try:
        with st.spinner("Authenticating..."):
            res = requests.post(
                f"{API_BASE_URL}/auth/login",
                data={"username": email, "password": password},
                timeout=API_TIMEOUT,
            )
        if res.status_code == 200:
            token = res.json()["access_token"]
            st.session_state.access_token = token
            st.session_state.user_email = email
            cookie_expiry = datetime.now() + timedelta(days=1)
            cookie_manager.set("sla_access_token", token, expires_at=cookie_expiry, key="set_token")
            cookie_manager.set("sla_user_email", email, expires_at=cookie_expiry, key="set_email")
            st.toast("Signed in successfully.")
            # Brief pause so the browser finishes writing the cookie before reload.
            time.sleep(0.5)
            st.rerun()
        else:
            st.error(friendly_error(res, "We couldn't sign you in. Please check your email and password and try again."))
    except requests.exceptions.ConnectionError:
        st.error(CONNECTION_ERROR_MSG)
    except requests.exceptions.Timeout:
        st.error(TIMEOUT_ERROR_MSG)
    except Exception:
        st.error(CONNECTION_ERROR_MSG)


def execute_register(email, password):
    try:
        with st.spinner("Creating account..."):
            res = requests.post(
                f"{API_BASE_URL}/auth/signup",
                json={"email": email, "password": password},
                timeout=API_TIMEOUT,
            )
        if res.status_code == 201:
            st.success("Your account has been created. You can now sign in with your credentials.")
        else:
            st.error(friendly_error(res, "We couldn't create your account. Please check your details and try again."))
    except requests.exceptions.ConnectionError:
        st.error(CONNECTION_ERROR_MSG)
    except requests.exceptions.Timeout:
        st.error(TIMEOUT_ERROR_MSG)
    except Exception:
        st.error(CONNECTION_ERROR_MSG)


# ── LANDING HOMEPAGE & AUTHENTICATION PORTAL ──────────────────────────────────
if not st.session_state.access_token:
    render_topbar()

    st.markdown(
        """
        <div class='sentinel-dark-hero'>
            <div class='sentinel-dark-badge'>Enterprise SLA & Contract Compliance</div>
            <div class='sentinel-dark-title'>Never Miss a Contract<br>Deadline Again</div>
            <div class='sentinel-dark-subtitle'>ContractSentinel reads your contracts, finds every obligation and deadline automatically, and alerts your team before a breach happens.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    landing_col1, landing_col2, landing_col3 = st.columns([0.15, 0.7, 0.15])
    with landing_col2:
        if os.path.exists(CONTRACT_IMG):
            st.image(CONTRACT_IMG, use_column_width=True)

        st.write("")
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        st.subheader("Sign In to Your Account")
        st.markdown("</div>", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        with tab_login:
            st.caption("Enter your credentials to access your compliance dashboard.")
            login_email = st.text_input("Email Address", placeholder="name@company.com", key="auth_email")
            login_password = st.text_input("Password", placeholder="••••••••", type="password", key="auth_pass")

            if st.button("Sign In", type="primary", use_container_width=True):
                execute_login(login_email, login_password)

        with tab_register:
            st.caption("Set up a new account for your company.")
            reg_email = st.text_input("Email Address", placeholder="name@company.com", key="new_email")
            reg_password = st.text_input("Password", placeholder="••••••••", type="password", key="new_pass")
            if st.button("Create Account", use_container_width=True):
                execute_register(reg_email, reg_password)

    st.stop()


# ── AUTHENTICATED DASHBOARD VIEW ───────────────────────────────────────────────
render_topbar(show_avatar=True)

# Sidebar Controls
with st.sidebar:
    st.markdown("### ContractSentinel")
    safe_email = st.session_state.user_email.replace("@", "&#64;")
    st.markdown(
        f"<p style='color: rgba(49, 51, 63, 0.6); font-size: 0.875rem;'>Signed in as <strong>{safe_email}</strong></p>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("#### Actions")
    if st.button("Check for Upcoming Deadlines", type="primary", use_container_width=True):
        try:
            with st.spinner("Checking obligations against current deadlines..."):
                res = requests.post(f"{API_BASE_URL}/monitoring/run-check", headers=get_headers(), timeout=API_TIMEOUT)
            if res.status_code == 200:
                data = res.json()["details"]
                st.toast(
                    f"Check complete — {data['checked']} obligations reviewed, {data['flagged_breached']} newly flagged as breached."
                )
                st.rerun()
            else:
                st.error(friendly_error(res, "The deadline check couldn't be completed right now."))
        except requests.exceptions.ConnectionError:
            st.error(CONNECTION_ERROR_MSG)
        except requests.exceptions.Timeout:
            st.error(TIMEOUT_ERROR_MSG)
        except Exception:
            st.error(CONNECTION_ERROR_MSG)

    st.divider()
    if st.button("Sign Out", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.user_email = None
        st.session_state.pop("cookie_retry_done", None)
        safe_delete_cookie("sla_access_token", key="del_token")
        safe_delete_cookie("sla_user_email", key="del_email")
        time.sleep(0.5)  # Let the browser commit the cookie deletion before reload.
        st.rerun()


# ── Data Loading ────────────────────────────────────────────────────────────────
# Shows a spinner, retries once on failure, and only shows an error if it persists.

def fetch_dashboard_data():
    contracts, obligations, alerts = [], [], []

    c_res = requests.get(f"{API_BASE_URL}/contracts/", headers=get_headers(), timeout=API_TIMEOUT)
    if c_res.status_code == 200:
        contracts = c_res.json()

    o_res = requests.get(f"{API_BASE_URL}/obligations/", headers=get_headers(), timeout=API_TIMEOUT)
    if o_res.status_code == 200:
        obligations = o_res.json()

    a_res = requests.get(f"{API_BASE_URL}/monitoring/alerts", headers=get_headers(), timeout=API_TIMEOUT)
    if a_res.status_code == 200:
        alerts = a_res.json()

    return contracts, obligations, alerts


contracts_list, obligations_list, alerts_list = [], [], []
data_load_failed = False

with st.spinner("Loading your dashboard..."):
    try:
        contracts_list, obligations_list, alerts_list = fetch_dashboard_data()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # First attempt failed - could just be a cold start. Wait a moment
        # and try once more before treating this as a real problem.
        time.sleep(2)
        try:
            contracts_list, obligations_list, alerts_list = fetch_dashboard_data()
        except Exception:
            data_load_failed = True
    except Exception:
        data_load_failed = True

if data_load_failed:
    st.markdown(
        """
        <div style='text-align:center; padding: 48px 24px;'>
            <div style='font-size: 1.05rem; color: #334155; margin-bottom: 18px;'>
                We're having trouble loading your dashboard right now.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    retry_col1, retry_col2, retry_col3 = st.columns([1, 0.6, 1])
    with retry_col2:
        if st.button("Retry", type="primary", use_container_width=True):
            st.rerun()
    st.stop()


# Metric Computations
total_contracts = len(contracts_list)
total_obligations = len(obligations_list)
breached_count = sum(1 for o in obligations_list if o.get("status") == "breached")
upcoming_count = sum(1 for o in obligations_list if o.get("status") == "upcoming")
pending_count = sum(1 for o in obligations_list if o.get("status") == "pending")
completed_count = sum(1 for o in obligations_list if o.get("status") == "completed")

total_penalty_risk = sum(
    float(o.get("penalty_amount") or 0)
    for o in obligations_list
    if o.get("status") in ("breached", "upcoming", "pending")
)

st.session_state.last_refreshed = datetime.now().strftime("%I:%M %p")

# Richer sidebar - appended after data loads since sidebar renders in write order.
with st.sidebar:
    st.divider()
    st.markdown("#### Quick Stats")
    st.markdown(f"<span class='status-dot' style='background-color:#DC2626;'></span>**{breached_count}** Missed Deadline{'s' if breached_count != 1 else ''}", unsafe_allow_html=True)
    st.markdown(f"<span class='status-dot' style='background-color:#D97706;'></span>**{upcoming_count}** Due Soon", unsafe_allow_html=True)
    st.markdown(f"<span class='status-dot' style='background-color:#0EA5E9;'></span>**{pending_count}** Not Yet Due", unsafe_allow_html=True)

    st.divider()
    with st.expander("Need help?"):
        st.caption("Questions about a contract or deadline? Reach out to your workspace administrator, or email:")
        st.markdown("[support@contractsentinel.example](mailto:support@contractsentinel.example)")


# ── TABBED NAVIGATION ──────────────────────────────────────────────────────────
tab_compliance, tab_upload, tab_audit, tab_contracts = st.tabs(
    ["Compliance Overview", "Add New Contract", "Notifications & Audit Trail", "Contract Repository"]
)

# ── TAB 1: OBLIGATION COMPLIANCE TABLE ─────────────────────────────────────────
with tab_compliance:
    # HERO BANNER WITH CORPORATE IMAGE (only on main dashboard tab)
    hero_col1, hero_col2 = st.columns([2.2, 1])

    with hero_col1:
        st.markdown(
            """
            <div class='sentinel-hero-banner'>
                <div class='sentinel-hero-title'>Your Compliance Snapshot</div>
                <div class='sentinel-hero-subtitle'>Track every contract obligation, deadline, and penalty risk in one place.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with hero_col2:
        st.markdown(
            render_status_ring(breached_count, upcoming_count, pending_count, completed_count),
            unsafe_allow_html=True,
        )

    st.caption(f"Last refreshed: {st.session_state.last_refreshed}")

    # ── FLOATING KPI METRICS CARDS ──────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        contracts_context = kpi_context_pill(f"{total_obligations} obligations found", "neutral")
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-value'>{total_contracts}</div><div class='kpi-label'>Total Contracts</div>{contracts_context}</div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-value' style='color:#7C3AED;'>{total_obligations}</div><div class='kpi-label'>Total Obligations</div>{kpi_context_pill('Across all contracts', 'neutral')}</div>",
            unsafe_allow_html=True,
        )
    with c3:
        due_tone = "warn" if upcoming_count > 0 else "good"
        due_text = "Review soon" if upcoming_count > 0 else "Nothing urgent"
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-value' style='color:#D97706;'>{upcoming_count}</div><div class='kpi-label'>Due Within 7 Days</div>{kpi_context_pill(due_text, due_tone)}</div>",
            unsafe_allow_html=True,
        )
    with c4:
        breach_tone = "bad" if breached_count > 0 else "good"
        breach_text = "Needs attention" if breached_count > 0 else "All clear"
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-value' style='color:#DC2626;'>{breached_count}</div><div class='kpi-label'>Missed Deadlines</div>{kpi_context_pill(breach_text, breach_tone)}</div>",
            unsafe_allow_html=True,
        )
    with c5:
        risk_tone = "bad" if total_penalty_risk > 0 else "good"
        risk_text = "At risk" if total_penalty_risk > 0 else "No exposure"
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-value' style='color:#059669;'>${total_penalty_risk:,.2f}</div><div class='kpi-label'>Potential Penalty Exposure</div>{kpi_context_pill(risk_text, risk_tone)}</div>",
            unsafe_allow_html=True,
        )

    st.write("")
    st.divider()

    st.subheader("Obligation Tracker")

    search_col, filter_col, export_col = st.columns([3, 1, 1])
    with search_col:
        search_query = st.text_input(
            "Filter obligations", placeholder="Search by description or contract title...", label_visibility="collapsed"
        )
    with filter_col:
        STATUS_DISPLAY_MAP = {
            "All Statuses": "All Statuses",
            "Missed Deadline": "breached",
            "Due Soon": "upcoming",
            "Not Yet Due": "pending",
            "Completed": "completed",
        }
        status_display_choice = st.selectbox(
            "Status Filter", list(STATUS_DISPLAY_MAP.keys()), label_visibility="collapsed"
        )
        status_filter = STATUS_DISPLAY_MAP[status_display_choice]

    filtered_obs = obligations_list
    if status_filter != "All Statuses":
        filtered_obs = [o for o in filtered_obs if o.get("status") == status_filter]
    if search_query:
        filtered_obs = [
            o for o in filtered_obs
            if search_query.lower() in o.get("description", "").lower()
        ]

    with export_col:
        if filtered_obs:
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["Description", "Deadline", "Status", "Penalty Amount", "Penalty Currency", "Source"])
            for o in filtered_obs:
                writer.writerow([
                    o.get("description", ""),
                    o.get("deadline", "").split("T")[0],
                    o.get("status", ""),
                    o.get("penalty_amount", ""),
                    o.get("penalty_currency", ""),
                    "AI-Extracted" if o.get("is_ai_extracted") else "Manually Added",
                ])
            st.download_button(
                "Export CSV",
                data=csv_buffer.getvalue(),
                file_name="obligations.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.button("Export CSV", disabled=True, use_container_width=True)

    # Reset pagination whenever the search/filter changes, so a new query
    # always starts from the top instead of showing an oddly cut-off list.
    filter_signature = f"{search_query}|{status_filter}"
    if st.session_state.get("ob_filter_sig") != filter_signature:
        st.session_state.ob_filter_sig = filter_signature
        st.session_state.ob_display_count = 10
    display_count = st.session_state.get("ob_display_count", 10)

    if not filtered_obs:
        if not obligations_list:
            st.info("No obligations yet. Add a contract under **Add New Contract** to get started.")
        else:
            st.info("No obligations match your search or filter. Try adjusting them.")
    else:
        visible_obs = filtered_obs[:display_count]

        for ob in visible_obs:
            status = ob.get("status", "pending")
            if status == "breached":
                badge_html = "<span class='status-breached'>MISSED DEADLINE</span>"
                border_class = "status-border-breached"
            elif status == "upcoming":
                badge_html = "<span class='status-upcoming'>DUE SOON</span>"
                border_class = "status-border-upcoming"
            elif status == "completed":
                badge_html = "<span class='status-completed'>COMPLETED</span>"
                border_class = "status-border-completed"
            else:
                badge_html = "<span class='status-pending'>NOT YET DUE</span>"
                border_class = "status-border-pending"

            penalty_text = (
                f"${float(ob['penalty_amount']):,.2f} {ob.get('penalty_currency', 'USD')}"
                if ob.get("penalty_amount")
                else "No penalty on file"
            )
            deadline_str = ob.get("deadline", "").split("T")[0]
            source_label = "AI-Extracted" if ob.get("is_ai_extracted") else "Manually Added"

            card_col, action_col = st.columns([5, 1])

            with card_col:
                st.markdown(
                    f"""
                    <div class='obligation-card {border_class}'>
                        <div class='obligation-card-title'>{ob.get('description')} <span class='source-tag'>{source_label}</span></div>
                        <div class='obligation-card-meta'>
                            <span>Due: <strong>{deadline_str}</strong></span>
                            <span>Penalty: <strong>{penalty_text}</strong></span>
                            <span>{badge_html}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with action_col:
                if status != "completed":
                    if st.button("Mark as Done", key=f"complete_{ob['id']}", use_container_width=True):
                        try:
                            up_res = requests.patch(
                                f"{API_BASE_URL}/obligations/{ob['id']}/status",
                                json={"status": "completed"},
                                headers=get_headers(),
                                timeout=API_TIMEOUT,
                            )
                            if up_res.status_code == 200:
                                st.toast("Marked as completed.")
                                st.rerun()
                            else:
                                st.error(friendly_error(up_res, "Couldn't update this obligation right now."))
                        except requests.exceptions.ConnectionError:
                            st.error(CONNECTION_ERROR_MSG)
                        except requests.exceptions.Timeout:
                            st.error(TIMEOUT_ERROR_MSG)
                else:
                    st.caption("Resolved")

        if len(filtered_obs) > display_count:
            remaining = len(filtered_obs) - display_count
            st.write("")
            load_col1, load_col2, load_col3 = st.columns([1, 1, 1])
            with load_col2:
                if st.button(f"Load More ({remaining} remaining)", use_container_width=True):
                    st.session_state.ob_display_count += 10
                    st.rerun()


# ── TAB 2: ADD NEW CONTRACT ─────────────────────────────────────────────────────
with tab_upload:
    st.subheader("Add a New Contract")
    st.caption("Upload a contract document and we'll automatically identify its deadlines and obligations.")

    # Shows the last extraction result, stored in session_state so it survives
    # the st.rerun() below (which refreshes every tab's data).
    if st.session_state.get("last_extraction_result"):
        result = st.session_state.pop("last_extraction_result")
        if result["items"]:
            st.success(f"Done! We found {len(result['items'])} obligation(s) in this contract. Check **Compliance Overview** to see them.")
            st.markdown("#### What we found")
            for idx, item in enumerate(result["items"], 1):
                dl_str = item.get("deadline", "").split("T")[0]
                pen_str = f"${float(item['penalty_amount']):,.2f} {item.get('penalty_currency', 'USD')}" if item.get("penalty_amount") else "No penalty on file"
                st.markdown(
                    f"""
                    <div class='callout-group'>
                        <div class='callout-group-index'>Obligation {idx}</div>
                        <div class='callout-row'>
                            <div class='callout-card callout-wide'>
                                <span class='callout-label callout-label-obligation'>Description</span>
                                <div class='callout-value'>{item.get('description')}</div>
                            </div>
                        </div>
                        <div class='callout-row' style='margin-top: 10px;'>
                            <div class='callout-card'>
                                <span class='callout-label callout-label-date'>Due Date</span>
                                <div class='callout-value'>{dl_str}</div>
                            </div>
                            <div class='callout-card'>
                                <span class='callout-label callout-label-penalty'>Penalty if Missed</span>
                                <div class='callout-value'>{pen_str}</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.success("Contract uploaded. We didn't find any obligations with specific deadlines in this document — you can add them manually if needed.")
        st.divider()

    col_form, col_img = st.columns([1.2, 0.8])

    with col_form:
        contract_title = st.text_input("Contract Name", placeholder="e.g. Master Services Agreement 2025")
        uploaded_file = st.file_uploader("Contract Document", type=["pdf", "txt"])

        if st.button("Upload & Identify Obligations", type="primary", use_container_width=True):
            if not contract_title or not uploaded_file:
                st.error("Please enter a contract name and choose a file to upload.")
            else:
                try:
                    with st.spinner("Reading your document..."):
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        data = {"title": contract_title}
                        upload_res = requests.post(
                            f"{API_BASE_URL}/contracts/upload",
                            data=data,
                            files=files,
                            headers=get_headers(),
                            timeout=30,
                        )

                    if upload_res.status_code == 201:
                        contract_id = upload_res.json()["id"]
                        content_length = upload_res.json().get("content_length", 0)
                        low, high = estimate_extraction_seconds(content_length)

                        with st.spinner("Starting AI extraction..."):
                            extract_res = requests.post(
                                f"{API_BASE_URL}/contracts/{contract_id}/extract",
                                headers=get_headers(),
                                timeout=30,
                            )

                        if extract_res.status_code == 202:
                            # Extraction now runs in the background on the server -
                            # this call returns almost instantly. We do a short,
                            # bounded check here so a fast/small document can show
                            # its result immediately, but we never block longer
                            # than a few seconds: if it's not done by then, the
                            # user is freed to keep using the app while it
                            # finishes on its own. The Contract Repository tab
                            # will reflect the final status whenever they check it.
                            final_status = "processing"
                            status_placeholder = st.empty()
                            start_time = time.time()
                            for _ in range(4):
                                elapsed = int(time.time() - start_time)
                                status_placeholder.info(
                                    f"Reading the document and identifying obligations... "
                                    f"elapsed {elapsed}s (estimated {format_seconds_range(low, high)})"
                                )
                                time.sleep(2)
                                check_res = requests.get(
                                    f"{API_BASE_URL}/contracts/{contract_id}",
                                    headers=get_headers(),
                                    timeout=API_TIMEOUT,
                                )
                                if check_res.status_code == 200:
                                    final_status = check_res.json().get("status", "processing")
                                if final_status in ("processed", "failed"):
                                    break
                            status_placeholder.empty()

                            if final_status == "processed":
                                st.success("Done! Obligations have been identified.")
                            elif final_status == "failed":
                                st.error("Extraction failed on this document. You can retry it from the Contract Repository tab.")
                            else:
                                st.info(
                                    f"This document is larger than usual (estimated "
                                    f"{format_seconds_range(low, high)} total), so extraction is still running "
                                    f"in the background. Feel free to keep using the app - check the Contract "
                                    f"Repository tab in a bit and it'll be ready."
                                )
                            st.session_state.last_extraction_result = {"contract_id": contract_id}
                            st.rerun()
                        else:
                            st.error(friendly_error(extract_res, "We couldn't start processing this document. Please try again."))
                    else:
                        st.error(friendly_error(upload_res, "We couldn't upload this file. Please check the format and try again."))
                except requests.exceptions.ConnectionError:
                    st.error(CONNECTION_ERROR_MSG)
                except requests.exceptions.Timeout:
                    st.error("This is taking a moment - check the Contract Repository tab shortly, it may still finish in the background.")
                except Exception:
                    st.error(CONNECTION_ERROR_MSG)

    with col_img:
        if os.path.exists(HANDSHAKE_IMG):
            st.image(HANDSHAKE_IMG, caption="Contract Execution & Verification", use_column_width=True)


# ── TAB 3: NOTIFICATIONS & AUDIT TRAIL ──────────────────────────────────────────
with tab_audit:
    st.subheader("Notifications & Audit Trail")

    audit_col1, audit_col2 = st.columns([2, 1])

    with audit_col1:
        st.caption("A complete record of deadline reminders and breach notices, kept for compliance purposes.")

        if not alerts_list:
            st.info("No notifications yet. You'll see deadline reminders and missed-deadline notices here as they happen.")
        else:
            for alert in alerts_list:
                alert_type = alert.get("alert_type")
                sent_time = alert.get("sent_at", "").replace("T", " ")[:19]
                msg = alert.get("message")

                if alert_type == "breach_notice":
                    st.error(f"**Missed Deadline** · {sent_time}\n\n{msg}")
                else:
                    st.warning(f"**Upcoming Deadline** · {sent_time}\n\n{msg}")

    with audit_col2:
        if os.path.exists(AUDIT_IMG):
            st.image(AUDIT_IMG, caption="Regulatory Compliance & Audit Traceability", use_column_width=True)


# ── TAB 4: CONTRACT REPOSITORY ──────────────────────────────────────────────────
with tab_contracts:
    st.subheader("Contract Repository")
    st.caption("Every contract you've uploaded, along with its processing status.")

    if not contracts_list:
        st.info("No contracts uploaded yet. Use **Add New Contract** to upload your first one.")
    else:
        STATUS_LABELS = {
            "uploaded": "Uploaded",
            "processing": "Processing",
            "processed": "Ready",
            "failed": "Needs Attention",
        }
        STATUS_BADGE_CLASS = {
            "uploaded": "status-pending",
            "processing": "status-upcoming",
            "processed": "status-completed",
            "failed": "status-breached",
        }
        for c in contracts_list:
            contract_status = c.get("status", "uploaded")
            status_label = STATUS_LABELS.get(contract_status, contract_status.title())
            badge_class = STATUS_BADGE_CLASS.get(contract_status, "status-pending")
            contract_obligations = [o for o in obligations_list if o.get("contract_id") == c.get("id")]

            with st.expander(f"{c.get('title')} — {status_label} · {len(contract_obligations)} obligation(s)"):
                top_col, badge_col = st.columns([3, 1])
                with top_col:
                    st.write(f"**File name:** {c.get('original_filename') or 'N/A'}")
                    st.write(f"**Uploaded on:** {c.get('created_at', '').split('T')[0]}")
                    st.markdown(f"<span class='reference-tag'>Reference: {c.get('id')[:8]}</span>", unsafe_allow_html=True)
                with badge_col:
                    st.markdown(f"<span class='{badge_class}'>{status_label.upper()}</span>", unsafe_allow_html=True)

                # Still running in the background (extraction is now async) -
                # give the user an easy way to check without re-uploading.
                # Also offer delete here: if the server process restarted or
                # redeployed mid-extraction, this row can be stuck at
                # "processing" forever with no automatic recovery, since
                # nothing ever runs to flip its status to "failed" in that
                # case. Deleting a contract that's genuinely still running is
                # safe - the background task will simply fail to save its
                # results afterward (the row it's looking for is gone) rather
                # than creating orphaned data.
                if contract_status == "processing":
                    # updated_at reflects when this contract last changed
                    # status - i.e. when the *current* extraction attempt
                    # actually started. Using created_at here was a bug: for
                    # a contract that had been retried, it showed time since
                    # the ORIGINAL upload, not since this attempt began,
                    # making things look far more stuck than they were.
                    started_at_str = c.get("updated_at") or c.get("created_at", "")
                    try:
                        started_dt = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
                        elapsed_s = int((datetime.now(started_dt.tzinfo) - started_dt).total_seconds())
                    except (ValueError, TypeError):
                        elapsed_s = None
                    low, high = estimate_extraction_seconds(c.get("content_length", 0))
                    if elapsed_s is not None:
                        st.caption(f"⏱ Processing for {format_seconds(elapsed_s)} · estimated {format_seconds_range(low, high)} total")
                    else:
                        st.caption(f"⏱ Estimated {format_seconds_range(low, high)} total")

                    check_col, stuck_delete_col = st.columns(2)
                    with check_col:
                        if st.button("Check status", key=f"refresh_{c['id']}", use_container_width=True):
                            st.rerun()
                    with stuck_delete_col:
                        if st.button("Delete (if stuck)", key=f"delete_stuck_{c['id']}", use_container_width=True):
                            try:
                                del_res = requests.delete(
                                    f"{API_BASE_URL}/contracts/{c['id']}",
                                    headers=get_headers(),
                                    timeout=API_TIMEOUT,
                                )
                                if del_res.status_code == 204:
                                    st.toast("Contract deleted.")
                                    st.rerun()
                                else:
                                    st.error(friendly_error(del_res, "Couldn't delete this contract right now."))
                            except requests.exceptions.ConnectionError:
                                st.error(CONNECTION_ERROR_MSG)

                # Failed or never-extracted contracts: offer retry (reuses this
                # same contract_id, so it never creates a duplicate row) and
                # delete (cleans up the row entirely) instead of forcing a
                # re-upload, which is what caused the duplicate-contract issue.
                if contract_status in ("failed", "uploaded"):
                    retry_col, delete_col = st.columns(2)
                    with retry_col:
                        if st.button("Retry Extraction", key=f"retry_{c['id']}", use_container_width=True):
                            try:
                                with st.spinner("Starting extraction again..."):
                                    retry_res = requests.post(
                                        f"{API_BASE_URL}/contracts/{c['id']}/extract",
                                        headers=get_headers(),
                                        timeout=30,
                                    )
                                if retry_res.status_code == 202:
                                    st.toast("Extraction restarted - running in the background.")
                                    st.rerun()
                                else:
                                    st.error(friendly_error(retry_res, "Extraction failed again. Please try again shortly."))
                            except requests.exceptions.Timeout:
                                st.error("Still taking longer than expected. Please try again in a moment.")
                            except requests.exceptions.ConnectionError:
                                st.error(CONNECTION_ERROR_MSG)
                    with delete_col:
                        if st.button("Delete Contract", key=f"delete_{c['id']}", use_container_width=True):
                            try:
                                del_res = requests.delete(
                                    f"{API_BASE_URL}/contracts/{c['id']}",
                                    headers=get_headers(),
                                    timeout=API_TIMEOUT,
                                )
                                if del_res.status_code == 204:
                                    st.toast("Contract deleted.")
                                    st.rerun()
                                else:
                                    st.error(friendly_error(del_res, "Couldn't delete this contract right now."))
                            except requests.exceptions.ConnectionError:
                                st.error(CONNECTION_ERROR_MSG)

                if contract_obligations:
                    show_key = f"show_obs_{c['id']}"
                    if show_key not in st.session_state:
                        st.session_state[show_key] = False

                    if st.button(
                        "Hide Obligations" if st.session_state[show_key] else "View Obligations",
                        key=f"toggle_{c['id']}",
                    ):
                        st.session_state[show_key] = not st.session_state[show_key]
                        st.rerun()

                    if st.session_state[show_key]:
                        st.write("")
                        for ob in contract_obligations:
                            ob_status = ob.get("status", "pending")
                            status_word = {
                                "breached": "Missed Deadline", "upcoming": "Due Soon",
                                "completed": "Completed", "pending": "Not Yet Due",
                            }.get(ob_status, ob_status.title())
                            deadline_str = ob.get("deadline", "").split("T")[0]
                            st.markdown(f"- {ob.get('description')} — *{status_word}, due {deadline_str}*")


# ── FOOTER ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class='sentinel-footer'>
        ContractSentinel v1.0 · Built for enterprise legal & procurement teams ·
        <a href='mailto:support@contractsentinel.example'>Contact Support</a>
    </div>
    """,
    unsafe_allow_html=True,
)

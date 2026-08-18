import streamlit as st 
import yfinance as yf

# ── PRESETS ────────────────────────────────────────────────────────────────────

PRESETS = {
    "AAOIFI Standard (Default)": {
        "debt_mc": 0.33, "interest_rev": 0.05, "receivables_mc": 0.45,
        "info": "Most widely used Islamic investment standard globally."
    },
    "MSCI Islamic Index": {
        "debt_mc": 0.3333, "interest_rev": 0.05, "receivables_mc": 0.3333,
        "info": "Used by MSCI for their global Islamic index products."
    },
    "S&P Dow Jones Islamic": {
        "debt_mc": 0.33, "interest_rev": 0.05, "receivables_mc": 0.49,
        "info": "Standard behind S&P Dow Jones Islamic Market indices."
    },
    "Conservative": {
        "debt_mc": 0.10, "interest_rev": 0.02, "receivables_mc": 0.25,
        "info": "Stricter thresholds for more conservative interpretations."
    },
    "Zero Interest (Strict)": {
        "debt_mc": 0.00, "interest_rev": 0.00, "receivables_mc": 0.20,
        "info": "Requires zero interest-bearing debt or income. Very strict."
    },
    "Custom": {
        "debt_mc": 0.33, "interest_rev": 0.05, "receivables_mc": 0.45,
        "info": "Set your own thresholds using the sliders below."
    },
}

# ── BUSINESS ACTIVITY DATA ─────────────────────────────────────────────────────

ALWAYS_EXCLUDED = {
    "Beverages—Wineries & Distilleries": "Alcohol production",
    "Beverages—Breweries": "Alcohol production",
    "Tobacco": "Tobacco products",
    "Gambling": "Gambling and betting",
}

OPTIONAL_SECTORS = {
    "conventional_finance": {
        "label": "Conventional Banking & Insurance",
        "default": True,
        "industries": [
            "Banks—Regional", "Banks—Diversified",
            "Insurance—Life", "Insurance—Property & Casualty",
            "Insurance—Diversified", "Credit Services", "Mortgage Finance",
        ],
        "reason": "Conventional interest-based financial services (riba)",
    },
    "defense": {
        "label": "Weapons & Defence",
        "default": True,
        "industries": ["Aerospace & Defense"],
        "reason": "Primary weapons manufacturing",
    },
    "entertainment": {
        "label": "Entertainment & Media",
        "default": False,
        "industries": ["Entertainment", "Broadcasting"],
        "reason": "Entertainment and media sector",
    },
    "hotels": {
        "label": "Hotels & Hospitality",
        "default": False,
        "industries": ["Lodging", "Resorts & Casinos"],
        "reason": "Hotels and hospitality sector",
    },
    "social_media": {
        "label": "Social Media Platforms",
        "default": False,
        "industries": ["Internet Content & Information"],
        "reason": "Social media platforms",
    },
}

PROHIBITED_KEYWORDS = [
    "alcohol", "beer", "wine", "spirits", "distill", "brewery", "whiskey",
    "casino", "gambling", "betting", "lottery", "wagering",
    "tobacco", "cigarette", "nicotine",
    "pork", "pig farming",
    "pornograph", "adult entertainment",
]

# BDS — based on BDS movement's own published lists (public information)
BDS_COMPANIES = {
    "HPQ": "HP Inc — technology contracted to Israeli military checkpoints and prisons",
    "HPE": "Hewlett Packard Enterprise — similar concerns to HP Inc",
    "CAT": "Caterpillar — bulldozers used in demolition of Palestinian homes",
    "BKNG": "Booking Holdings — lists accommodation in illegal Israeli settlements",
    "EXPE": "Expedia Group — lists properties in occupied Palestinian territories",
    "TRIP": "TripAdvisor — lists businesses in occupied territories",
    "SBUX": "Starbucks — commonly cited in BDS campaign materials",
    "MCD": "McDonald's — commonly cited in BDS campaign materials",
    "INTC": "Intel — major Israeli operations cited by BDS movement",
    "AXP": "American Express — financial services cited in BDS materials",
}
# ── HELPERS ──────────────────────────────────────────────────────────────────── 

def fmt(n):
    if not n: return "N/A"
    if abs(n) >= 1e12: return f"${n/1e12:.1f}T"
    if abs(n) >= 1e9: return f"${n/1e9:.1f}B"
    return f"${n/1e6:.0f}M"

# ── SCREENING LOGIC ────────────────────────────────────────────────────────────

def check_business(info, active_sectors, bds_on, ticker):
    industry = info.get("industry", "")
    summary = (info.get("longBusinessSummary", "") or "").lower()
    fails = []

    # Always excluded industries
    if industry in ALWAYS_EXCLUDED:
        fails.append(f"{ALWAYS_EXCLUDED[industry]}")

    # Optional sector exclusions
    for key, cfg in OPTIONAL_SECTORS.items():
        if active_sectors.get(key, cfg["default"]):
            if industry in cfg["industries"]:
                fails.append(cfg["reason"])
                break

    # Keyword scan
    for kw in PROHIBITED_KEYWORDS:
        if kw in summary:
            fails.append(f"Business involves: {kw}")
            break

    # BDS check
    bds_flag = None
    if bds_on:
        bds_flag = BDS_COMPANIES.get(ticker.upper())

    return fails, bds_flag


def check_ratios(info, thresholds):
    mc = info.get("marketCap") or 0
    debt = info.get("totalDebt") or 0
    rev = info.get("totalRevenue") or 0
    iinc = info.get("interestIncome") or 0
    recv = info.get("netReceivables") or 0

    if mc == 0:
        return "UNKNOWN", [], {}

    issues, data = [], {}

    # 1 — Debt / Market Cap
    dr = debt / mc
    data["Debt / Market Cap"] = {
        "value": dr, "limit": thresholds["debt_mc"], "pass": dr <= thresholds["debt_mc"]
    }
    if dr > thresholds["debt_mc"]:
        issues.append(f"Debt/Market Cap {dr:.1%} exceeds your {thresholds['debt_mc']:.0%} limit")

    # 2 — Interest Income / Revenue
    if rev > 0 and iinc:
        ir = abs(iinc) / rev
        data["Interest Income / Revenue"] = {
            "value": ir, "limit": thresholds["interest_rev"], "pass": ir <= thresholds["interest_rev"]
        }
        if ir > thresholds["interest_rev"]:
            issues.append(f"Interest Income/Revenue {ir:.1%} exceeds your {thresholds['interest_rev']:.0%} limit")

    # 3 — Receivables / Market Cap
    if recv > 0:
        rr = recv / mc
        data["Receivables / Market Cap"] = {
            "value": rr, "limit": thresholds["receivables_mc"], "pass": rr <= thresholds["receivables_mc"]
        }
        if rr > thresholds["receivables_mc"]:
            issues.append(f"Receivables/Market Cap {rr:.1%} exceeds your {thresholds['receivables_mc']:.0%} limit")

    return ("FAIL" if issues else "PASS"), issues, data


def build_summary(biz_fails, bds_flag, fin_result, fin_issues, preset_name):
    if biz_fails:
        return (
            f"This stock does not pass your business activity screen. "
            f"The company is involved in: **{biz_fails[0]}**. "
            f"This applies regardless of its financial ratios. "
            f"Consider looking for alternatives in other sectors."
        )
    if bds_flag:
        return (
            f"This stock passes the financial and business screens under **{preset_name}**, "
            f"but is flagged by your BDS filter. {bds_flag}. "
            f"Whether to invest is a personal decision — the BDS filter only flags, it does not automatically disqualify."
        )
    if fin_result == "FAIL":
        first = fin_issues[0] if fin_issues else ""
        return (
            f"The company's business activities are acceptable, "
            f"but it fails the financial screen under **{preset_name}**. "
            f"{first}. "
            f"Try a different preset or adjust your custom thresholds to compare."
        )
    if fin_result == "UNKNOWN":
        return (
            "Business activities appear acceptable, but there was insufficient financial data "
            "to complete the ratio screen. Verify the ratios manually before investing."
        )
    return (
        f"This stock passes all your criteria under **{preset_name}** — "
        f"business activities, financial ratios, and any additional filters you have set. "
        f"It appears suitable based on your personalised settings."
    )

# ── APP ────────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="Shariah Screener", page_icon="☪️", layout="wide")
# ── SIDEBAR ─────────────────────────────────────────────────────────────── 
    with st.sidebar:
        st.markdown("# ⚙️ Your Screening Settings")
        st.markdown("Customise the criteria below. Changes apply instantly.")
        st.markdown("---")

        # 1. Standard / Preset
        st.markdown("### 📐 Financial Standard")
        preset_name = st.selectbox(
            "Choose a standard",
            list(PRESETS.keys()),
            index=0,
            label_visibility="collapsed"
        )
        preset = PRESETS[preset_name]
        st.caption(preset["info"])
        st.markdown(" ")

        # 2. Thresholds
        st.markdown("### 📊 Financial Ratio Limits")
        if preset_name == "Custom":
            st.caption("Drag the sliders to set your own limits.")
            debt_limit = st.slider(
                "Max Debt / Market Cap", 0, 60, 33, 1, format="%d%%"
            ) / 100
            int_limit = st.slider(
                "Max Interest Income / Revenue", 0, 20, 5, 1, format="%d%%"
            ) / 100
            recv_limit = st.slider(
                "Max Receivables / Market Cap", 0, 70, 45, 1, format="%d%%"
            ) / 100
        else:
            debt_limit = preset["debt_mc"]
            int_limit = preset["interest_rev"]
            recv_limit = preset["receivables_mc"]
            c1, c2, c3 = st.columns(3)
            c1.metric("Debt/MC", f"{debt_limit:.0%}")
            c2.metric("Interest/Rev", f"{int_limit:.0%}")
            c3.metric("Recv/MC", f"{recv_limit:.0%}")

        thresholds = {
            "debt_mc": debt_limit,
            "interest_rev": int_limit,
            "receivables_mc": recv_limit,
        }

        # 3. Business Activity Exclusions
        st.markdown("---")
        st.markdown("### 🏭 Business Exclusions")
        st.caption("Always excluded: Alcohol · Tobacco · Gambling · Adult content")
        st.markdown(" ")

        active_sectors = {}
        for key, cfg in OPTIONAL_SECTORS.items():
            active_sectors[key] = st.toggle(
                cfg["label"],
                value=cfg["default"],
                key=f"s_{key}"
            )

        # 4. Additional Filters
        st.markdown("---")
        st.markdown("### 🌍 Additional Filters")
        bds_on = st.toggle(
            "🇵🇸 BDS Compliance Filter",
            value=False,
            help=(
                "Flags companies cited in the BDS (Boycott, Divestment, Sanctions) "
                "movement's published materials. Based on publicly available BDS lists. "
                "May be incomplete — verify independently."
            )
        )
        if bds_on:
            st.caption(
                "⚠️ BDS lists are maintained by the BDS movement and may change. "
                "This filter flags known companies only. "
                "Flagging does not automatically mean non-compliant — "
                "the decision to divest is yours."
            )

        st.markdown("---")
        st.caption("📊 Data: Yahoo Finance\n☪️ Standards: AAOIFI · MSCI · S&P Dow Jones")

    # ── MAIN AREA ─────────────────────────────────────────────────────────────
    st.title("☪️ Shariah Stock Screener")
    st.markdown(f"Screening with: **{preset_name}** &nbsp;|&nbsp; Debt limit: **{debt_limit:.0%}** &nbsp;|&nbsp; Interest limit: **{int_limit:.0%}**")
    st.markdown("---")

    c_in, c_btn = st.columns([4, 1])
    with c_in:
        raw = st.text_input(
            "ticker",
            placeholder="Enter ticker symbol — e.g. AAPL TSLA 2222.SR EMAAR.AE",
            label_visibility="collapsed"
        )
    with c_btn:
        go = st.button("Screen →", type="primary", use_container_width=True)

    ticker = (raw or "").upper().strip()

    if not go:
        st.markdown("---")
        st.markdown("#### Current Settings Summary")
        c1, c2, c3 = st.columns(3)
        c1.info(f"**Debt limit:** {debt_limit:.0%}")
        c2.info(f"**Interest limit:** {int_limit:.0%}")
        c3.info(f"**Receivables limit:** {recv_limit:.0%}")

        on_sectors = [cfg["label"] for k, cfg in OPTIONAL_SECTORS.items() if active_sectors.get(k)]
        if bds_on:
            on_sectors.append("🇵🇸 BDS Filter")
        if on_sectors:
            st.info("**Active filters:** " + " &nbsp;·&nbsp; ".join(on_sectors))
        return

    if not ticker:
        st.warning("Please enter a stock ticker first.")
        return
# ── FETCH ───────────────────────────────────────────────────────────────── 
    with st.spinner(f"Fetching data for **{ticker}**..."):
        try:
            info = yf.Ticker(ticker).info
        except Exception:
            st.error("Could not connect to Yahoo Finance. Check your connection and try again.")
            return

    company = info.get("longName") or info.get("shortName") or ticker

    if not info.get("sector") and not info.get("industry") and not info.get("marketCap"):
        st.error(
            f"**'{ticker}'** not found. Check the symbol. "
            "For GCC stocks add the exchange suffix, e.g. **2222.SR** for Aramco."
        )
        return

    # ── SCREEN ────────────────────────────────────────────────────────────────
    biz_fails, bds_flag = check_business(info, active_sectors, bds_on, ticker)
    fin_result, fin_issues, ratios = check_ratios(info, thresholds)

    if biz_fails or fin_result == "FAIL":
        overall = "FAIL"
    elif bds_flag:
        overall = "BDS"
    elif fin_result == "UNKNOWN":
        overall = "UNKNOWN"
    else:
        overall = "PASS"

    # ── COMPANY HEADER ────────────────────────────────────────────────────────
    price = info.get("regularMarketPrice") or info.get("currentPrice")
    st.markdown(f"## {company} &nbsp; `{ticker}`")
    c1, c2, c3, c4 = st.columns(4)
    c1.caption(f"**Sector:** {info.get('sector','N/A')}")
    c2.caption(f"**Industry:** {info.get('industry','N/A')}")
    c3.caption(f"**Market Cap:** {fmt(info.get('marketCap'))}")
    if price:
        c4.caption(f"**Price:** ${price:,.2f}")
    st.markdown("---")

    # ── VERDICT ───────────────────────────────────────────────────────────────
    if overall == "PASS":
        st.success(f"## ✅ Passes Your Screening — *{preset_name}*")
    elif overall == "BDS":
        st.warning(f"## 🇵🇸 Flagged by BDS Filter — Financial screens: Passed")
    elif overall == "FAIL":
        st.error(f"## ❌ Fails Your Screening — *{preset_name}*")
    else:
        st.warning("## ⚠️ Inconclusive — Insufficient Financial Data")

    st.markdown("---")

    # ── CHECK COLUMNS ─────────────────────────────────────────────────────────
    num_cols = 3 if bds_on else 2
    cols = st.columns(num_cols)

    with cols[0]:
        st.markdown("**🏢 Business Activity**")
        if not biz_fails:
            st.success("✅ Passed")
            st.caption("No prohibited activities found")
        else:
            st.error("❌ Failed")
            for f in biz_fails:
                st.caption(f"• {f}")

    with cols[1]:
        st.markdown("**📊 Financial Ratios**")
        if fin_result == "PASS":
            st.success("✅ Passed")
            st.caption("All ratios within your thresholds")
        elif fin_result == "UNKNOWN":
            st.warning("⚠️ Insufficient data")
            st.caption("Could not retrieve full financial data")
        else:
            st.error("❌ Failed")
            for iss in fin_issues:
                st.caption(f"• {iss}")

    if bds_on:
        with cols[2]:
            st.markdown("**🇵🇸 BDS Filter**")
            if bds_flag:
                st.warning("⚠️ Flagged")
                st.caption(bds_flag)
            else:
                st.success("✅ Not flagged")
                st.caption("Not in BDS lists we track")

    # ── RATIO BREAKDOWN ───────────────────────────────────────────────────────
    if ratios:
        with st.expander("📈 Full Ratio Breakdown"):
            mc = info.get("marketCap") or 0
            debt = info.get("totalDebt") or 0
            c1, c2 = st.columns(2)
            c1.metric("Market Cap", fmt(mc))
            c2.metric("Total Debt", fmt(debt))
            st.markdown("---")
            for name, r in ratios.items():
                icon = "✅" if r["pass"] else "❌"
                color = "green" if r["pass"] else "red"
                word = "within" if r["pass"] else "exceeds"
                st.markdown(
                    f"{icon} **{name}:** "
                    f"<span style='color:{color}'>{r['value']:.1%}</span> — "
                    f"{word} your **{r['limit']:.0%}** limit",
                    unsafe_allow_html=True
                )
# ── FETCH ───────────────────────────────────────────────────────────────── 
    with st.spinner(f"Fetching data for **{ticker}**..."):
        try:
            info = yf.Ticker(ticker).info
        except Exception:
            st.error("Could not connect to Yahoo Finance. Check your connection and try again.")
            return

    company = info.get("longName") or info.get("shortName") or ticker

    if not info.get("sector") and not info.get("industry") and not info.get("marketCap"):
        st.error(
            f"**'{ticker}'** not found. Check the symbol. "
            "For GCC stocks add the exchange suffix, e.g. **2222.SR** for Aramco."
        )
        return

    # ── SCREEN ────────────────────────────────────────────────────────────────
    biz_fails, bds_flag = check_business(info, active_sectors, bds_on, ticker)
    fin_result, fin_issues, ratios = check_ratios(info, thresholds)

    if biz_fails or fin_result == "FAIL":
        overall = "FAIL"
    elif bds_flag:
        overall = "BDS"
    elif fin_result == "UNKNOWN":
        overall = "UNKNOWN"
    else:
        overall = "PASS"

    # ── COMPANY HEADER ────────────────────────────────────────────────────────
    price = info.get("regularMarketPrice") or info.get("currentPrice")
    st.markdown(f"## {company} &nbsp; `{ticker}`")
    c1, c2, c3, c4 = st.columns(4)
    c1.caption(f"**Sector:** {info.get('sector','N/A')}")
    c2.caption(f"**Industry:** {info.get('industry','N/A')}")
    c3.caption(f"**Market Cap:** {fmt(info.get('marketCap'))}")
    if price:
        c4.caption(f"**Price:** ${price:,.2f}")
    st.markdown("---")

    # ── VERDICT ───────────────────────────────────────────────────────────────
    if overall == "PASS":
        st.success(f"## ✅ Passes Your Screening — *{preset_name}*")
    elif overall == "BDS":
        st.warning(f"## 🇵🇸 Flagged by BDS Filter — Financial screens: Passed")
    elif overall == "FAIL":
        st.error(f"## ❌ Fails Your Screening — *{preset_name}*")
    else:
        st.warning("## ⚠️ Inconclusive — Insufficient Financial Data")

    st.markdown("---")

    # ── CHECK COLUMNS ─────────────────────────────────────────────────────────
    num_cols = 3 if bds_on else 2
    cols = st.columns(num_cols)

    with cols[0]:
        st.markdown("**🏢 Business Activity**")
        if not biz_fails:
            st.success("✅ Passed")
            st.caption("No prohibited activities found")
        else:
            st.error("❌ Failed")
            for f in biz_fails:
                st.caption(f"• {f}")

    with cols[1]:
        st.markdown("**📊 Financial Ratios**")
        if fin_result == "PASS":
            st.success("✅ Passed")
            st.caption("All ratios within your thresholds")
        elif fin_result == "UNKNOWN":
            st.warning("⚠️ Insufficient data")
            st.caption("Could not retrieve full financial data")
        else:
            st.error("❌ Failed")
            for iss in fin_issues:
                st.caption(f"• {iss}")

    if bds_on:
        with cols[2]:
            st.markdown("**🇵🇸 BDS Filter**")
            if bds_flag:
                st.warning("⚠️ Flagged")
                st.caption(bds_flag)
            else:
                st.success("✅ Not flagged")
                st.caption("Not in BDS lists we track")

    # ── RATIO BREAKDOWN ───────────────────────────────────────────────────────
    if ratios:
        with st.expander("📈 Full Ratio Breakdown"):
            mc = info.get("marketCap") or 0
            debt = info.get("totalDebt") or 0
            c1, c2 = st.columns(2)
            c1.metric("Market Cap", fmt(mc))
            c2.metric("Total Debt", fmt(debt))
            st.markdown("---")
            for name, r in ratios.items():
                icon = "✅" if r["pass"] else "❌"
                color = "green" if r["pass"] else "red"
                word = "within" if r["pass"] else "exceeds"
                st.markdown(
                    f"{icon} **{name}:** "
                    f"<span style='color:{color}'>{r['value']:.1%}</span> — "
                    f"{word} your **{r['limit']:.0%}** limit",
                    unsafe_allow_html=True
                )
 # ── SETTINGS USED ───────────────────────────────────────────────────────── 
    with st.expander("⚙️ Settings Used For This Screen"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Debt / Market Cap limit", f"{debt_limit:.0%}")
        c2.metric("Interest Income / Rev limit", f"{int_limit:.0%}")
        c3.metric("Receivables / Market Cap limit", f"{recv_limit:.0%}")

        always = ["Alcohol", "Tobacco", "Gambling", "Adult content"]
        optional_on = [cfg["label"] for k, cfg in OPTIONAL_SECTORS.items() if active_sectors.get(k)]
        all_excl = always + optional_on
        st.markdown("**Excluded sectors:** " + " · ".join(all_excl))
        if bds_on:
            st.markdown("**BDS filter:** Active")

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**💬 Summary**")
    st.info(build_summary(biz_fails, bds_flag, fin_result, fin_issues, preset_name))

    # ── DISCLAIMER ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.caption(
        "⚠️ **Disclaimer:** This tool is for informational purposes only and does not "
        "constitute a formal Shariah ruling (fatwa). BDS flags are based on the BDS movement's "
        "publicly available materials and may be incomplete or change over time. "
        "Financial data sourced from Yahoo Finance may have delays or inaccuracies. "
        "Consult a qualified Islamic scholar for formal investment guidance."
    )

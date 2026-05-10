"""
CryptoBot ML — Streamlit dashboard.

All data is fetched from the FastAPI backend (no direct DB access).
Set API_BASE_URL env var to point at the API (default: http://localhost:8001).
"""
import os
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001").rstrip("/")
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
SIGNAL_COLOR: Dict[str, str] = {
    "BUY":  "#00C853",
    "SELL": "#D50000",
    "HOLD": "#FF8F00",
}
SIGNAL_EMOJI: Dict[str, str] = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️"}
SIGNAL_ACTION: Dict[str, str] = {"BUY": "ACHETER", "SELL": "VENDRE", "HOLD": "ATTENDRE"}
SYMBOL_NAME: Dict[str, str] = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "SOLUSDT": "Solana",
}


def _signal_phrase(label: str, symbol: str) -> str:
    name = SYMBOL_NAME.get(symbol, symbol)
    if label == "BUY":
        return f"🟢 Le bot pense que **{name}** va **monter** — il recommande d'**acheter**."
    if label == "SELL":
        return f"🔴 Le bot pense que **{name}** va **baisser** — il recommande de **vendre**."
    return f"🟡 Le bot pense que **{name}** va rester **stable** — il recommande d'**attendre**."


def _confidence_phrase(conf: float) -> str:
    if conf >= 0.70:
        return f"Le bot est **très confiant** dans cette prédiction ({conf:.0%})."
    if conf >= 0.50:
        return f"Le bot est **assez confiant** ({conf:.0%})."
    return f"Le bot est **peu confiant** ({conf:.0%}) — prédiction à prendre avec prudence."


_PARIS_TZ = "Europe/Paris"


def _to_paris(ts) -> pd.Timestamp:
    """Convert any timestamp (UTC string, int, or naive) to Europe/Paris local time."""
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return t.tz_convert(_PARIS_TZ)


def _fmt_paris(ts, fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Return a timestamp formatted in Europe/Paris timezone. Returns '–' on error."""
    try:
        return _to_paris(ts).strftime(fmt)
    except Exception:
        return str(ts)[:16]


st.set_page_config(
    page_title="CryptoBot ML",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def api_get(endpoint: str, params: Optional[Dict] = None) -> Any:
    """Cached GET (TTL 60 s) — use for read-only endpoints."""
    try:
        r = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.warning(f"API `{endpoint}` → HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        st.error(f"API inaccessible ({API_BASE_URL}) : {e}")
        return None


def api_get_live(endpoint: str, params: Optional[Dict] = None) -> Any:
    """Non-cached GET — for /predict and real-time status calls."""
    try:
        r = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.warning(f"API `{endpoint}` → HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        st.error(f"API inaccessible ({API_BASE_URL}) : {e}")
        return None


# ---------------------------------------------------------------------------
# Sidebar — navigation + global tech toggle
# ---------------------------------------------------------------------------
if "goto" in st.session_state:
    st.session_state["nav"] = st.session_state.pop("goto")

st.sidebar.title("📊 CryptoBot ML")
st.sidebar.caption(f"API : `{API_BASE_URL}`")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["🎯 Démo", "🔴 Live", "📈 Marché", "📅 Vision Long Terme", "📊 Indicateurs", "⚙️ Modèle", "🔍 Monitoring"],
    key="nav",
)

st.sidebar.markdown("---")
show_tech: bool = st.sidebar.toggle(
    "🔧 Afficher les détails techniques",
    value=False,
    key="show_tech",
    help="Active les métriques avancées sur toutes les pages.",
)


# ---------------------------------------------------------------------------
# Page : 🎯 Démo
# ---------------------------------------------------------------------------
if page == "🎯 Démo":
    st.title("🎯 CryptoBot ML")

    if not show_tech:
        st.caption(
            "Un bot d'intelligence artificielle qui surveille les marchés crypto et vous dit "
            "quand acheter, vendre ou attendre."
        )
    else:
        st.caption("Vue d'ensemble pour la soutenance — tous les services en un clin d'œil.")

    # Accès rapide
    b1, b2, b3, b4 = st.columns(4)
    b1.link_button("🌊 Airflow",     "http://localhost:8080",      use_container_width=True)
    b2.link_button("📊 Grafana",     "http://localhost:3000",      use_container_width=True)
    b3.link_button("📖 API Swagger", "http://localhost:8001/docs", use_container_width=True)
    b4.link_button("🔬 Prometheus",  "http://localhost:9090",      use_container_width=True)

    st.markdown("---")

    # ── Signaux ML ────────────────────────────────────────────────────────
    hdr, refresh_btn = st.columns([5, 1])
    hdr.markdown("### Que dit le bot en ce moment ?")
    with refresh_btn:
        st.write("")
        if st.button("🔄", help="Actualiser", key="demo_refresh"):
            st.rerun()

    col_btc, col_eth, col_sol = st.columns(3)

    def _demo_card(col, sym: str) -> None:
        with col:
            pred = api_get_live("/predict", {"symbol": sym})
            name = SYMBOL_NAME.get(sym, sym)
            if pred:
                label = pred.get("signal_label", "–")
                conf  = pred.get("confidence", 0.0)
                price = pred.get("price", 0.0)
                color = SIGNAL_COLOR.get(label, "#444")
                model = pred.get("model_version", "")
                algo  = "XGB" if "xgboost" in model else ("LGB" if "lgb" in model else "ML")
                emoji = SIGNAL_EMOJI.get(label, "❓")
                phrase = {"BUY": "Va monter", "SELL": "Va baisser", "HOLD": "Stable"}.get(label, label)

                tech_row = (
                    f'<div style="color:rgba(255,255,255,0.55);font-size:0.72rem;'
                    f'margin-top:8px;border-top:1px solid rgba(255,255,255,0.15);padding-top:6px;">'
                    f'Conf. {conf:.1%} · {algo} · signal: {label}</div>'
                    if show_tech else ""
                )
                st.markdown(
                    f'<div style="background:{color};border-radius:14px;padding:22px 16px;'
                    f'text-align:center;">'
                    f'<div style="color:rgba(255,255,255,0.85);font-size:1rem;font-weight:700;">'
                    f'{name}</div>'
                    f'<div style="font-size:2.6rem;line-height:1.1;margin:8px 0 4px;">{emoji}</div>'
                    f'<div style="color:white;font-size:1.25rem;font-weight:800;">{phrase}</div>'
                    f'<div style="color:rgba(255,255,255,0.85);font-size:1rem;margin-top:6px;">'
                    f'<strong>${price:,.2f}</strong></div>'
                    + tech_row
                    + f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="background:#2a2a2e;border:1px solid #444;border-radius:14px;'
                    f'padding:22px 16px;text-align:center;">'
                    f'<div style="color:#888;font-size:1rem;font-weight:700;">{name}</div>'
                    f'<div style="color:#555;font-size:2.2rem;margin:8px 0;">–</div>'
                    f'<div style="color:#666;font-size:0.85rem;">indisponible</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    for col, sym in [(col_btc, "BTCUSDT"), (col_eth, "ETHUSDT"), (col_sol, "SOLUSDT")]:
        _demo_card(col, sym)

    st.markdown("---")

    # ── Performances du bot ───────────────────────────────────────────────
    st.markdown("### Comment se comporte le bot ?")
    metrics = api_get("/model/metrics")
    if metrics:
        m_cols = st.columns(len(metrics))
        for col, m in zip(m_cols, metrics):
            name    = SYMBOL_NAME.get(m["symbol"], m["symbol"])
            acc_pct = int(m["accuracy"] * 100)
            sharpe  = m["sharpe_ratio"]
            with col:
                if not show_tech:
                    gain_tag = (
                        f"🟢 {sharpe:.1f}× gains/risques" if sharpe > 1
                        else f"🔴 {sharpe:.2f}" if sharpe < 0
                        else f"🟡 {sharpe:.2f}"
                    )
                    st.markdown(
                        f'<div style="background:#1e1e2e;border:1px solid #333;border-radius:12px;'
                        f'padding:18px;text-align:center;">'
                        f'<div style="color:#bbb;font-size:0.85rem;font-weight:700;">{name}</div>'
                        f'<div style="color:white;font-size:2rem;font-weight:800;margin:8px 0;">'
                        f'{acc_pct}%</div>'
                        f'<div style="color:#ccc;font-size:0.82rem;">de bonnes prédictions</div>'
                        f'<div style="color:#aaa;font-size:0.75rem;margin-top:8px;">{gain_tag}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div style="background:#1e1e2e;border:1px solid #333;border-radius:10px;'
                        f'padding:14px;text-align:center;">'
                        f'<div style="color:#aaa;font-size:0.78rem;font-weight:700;letter-spacing:1px;">'
                        f'{m["symbol"]}</div>'
                        f'<div style="color:white;font-size:0.8rem;margin:4px 0 10px;">'
                        f'{m["model_name"].upper()}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    ma, mb, mc = st.columns(3)
                    ma.metric("Sharpe", f"{sharpe:.2f}")
                    mb.metric("F1",     f"{m['f1_macro']:.3f}")
                    mc.metric("Acc.",   f"{m['accuracy']:.1%}")
                st.caption(f"Entraîné le {m['date_train'][:10]}")
    else:
        st.info("Métriques indisponibles — vérifiez que l'API est démarrée.")



# ---------------------------------------------------------------------------
# Page : 🔴 Live
# ---------------------------------------------------------------------------
elif page == "🔴 Live":
    st.title("🔴 Live — Prédictions en temps réel")

    col_sym, col_ctrl, col_ref = st.columns([2, 1, 1])
    symbol   = col_sym.selectbox("Symbole", SYMBOLS, key="live_sym")
    sym_name = SYMBOL_NAME.get(symbol, symbol)

    status  = api_get_live("/live/status", {"symbol": symbol}) or {}
    running = status.get("running", False)

    with col_ctrl:
        st.write("")
        if not running:
            if st.button("▶ Démarrer", key="live_start"):
                try:
                    r = requests.post(
                        f"{API_BASE_URL}/live/start",
                        params={"symbol": symbol},
                        timeout=30,
                    )
                    r.raise_for_status()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur démarrage : {e}")
        else:
            if st.button("⏹ Arrêter", key="live_stop"):
                try:
                    requests.post(
                        f"{API_BASE_URL}/live/stop",
                        params={"symbol": symbol},
                        timeout=10,
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur arrêt : {e}")

    with col_ref:
        st.write("")
        auto_refresh = st.toggle("Auto-refresh 5s", value=True, key="live_auto")

    st.markdown("---")

    if not running:
        if not show_tech:
            st.info(
                f"Le bot ne surveille pas encore **{sym_name}**. "
                "Cliquez sur **▶ Démarrer** pour lancer l'analyse en direct."
            )
        else:
            st.info(
                "Le prédicteur live n'est pas démarré. "
                "Cliquez **▶ Démarrer** pour lancer le flux WebSocket Binance 1m."
            )
    else:
        live_price = status.get("live_price", 0.0)
        live_time  = status.get("live_time", "")
        sig        = status.get("signal") or {}
        score_str  = status.get("score_str", "0/0")
        score_pct  = status.get("score_pct")
        total      = status.get("total_predictions", 0)

        # ── KPIs ──────────────────────────────────────────────────────────
        if not show_tech:
            parts = score_str.split("/") if "/" in score_str else ["0", "0"]
            good, n_eval = parts[0].strip(), parts[1].strip() if len(parts) > 1 else "?"
            k1, k2 = st.columns(2)
            k1.metric(f"Prix {sym_name}", f"${live_price:,.2f}" if live_price else "–")
            k2.metric(
                "Score du bot",
                f"{good} bonnes sur {n_eval}",
                delta=f"{score_pct}% de précision" if score_pct is not None else None,
            )
        else:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Prix live",            f"${live_price:,.2f}" if live_price else "–")
            k2.metric("Timestamp",            live_time[11:19] if live_time else "–")
            k3.metric("Score",                score_str,
                      delta=f"{score_pct}%" if score_pct is not None else None)
            k4.metric("Prédictions évaluées", str(total))

            spread_val    = sig.get("spread") if sig else None
            threshold_val = sig.get("profitability_threshold") if sig else None
            if spread_val is not None or threshold_val is not None:
                p1, p2 = st.columns(2)
                p1.metric("Spread (bid/ask)", f"${spread_val:,.6f}" if spread_val is not None else "–",
                          help="Différence ask − bid récupérée en temps réel sur Binance")
                p2.metric("Seuil de rentabilité", f"${threshold_val:,.4f}" if threshold_val is not None else "–",
                          help="(spread + frais 0.1%) × 10 — signal forcé à HOLD si mouvement espéré < seuil")

        # ── Signal courant ────────────────────────────────────────────────
        st.markdown("### Ce que dit le bot")
        if sig:
            label      = sig.get("signal_label", "–")
            confidence = sig.get("confidence", 0.0)
            sig_price  = sig.get("price", 0.0)
            _ts_raw    = sig.get("timestamp", "")
            sig_time   = _fmt_paris(_ts_raw, "%d/%m/%Y %H:%M:%S") if _ts_raw else "–"
            color      = SIGNAL_COLOR.get(label, "#555555")

            if not show_tech:
                action_label = f"{SIGNAL_EMOJI.get(label, '')} {SIGNAL_ACTION.get(label, label)}"
                st.markdown(
                    f'<div style="background:{color};padding:26px;border-radius:14px;'
                    f'text-align:center;margin-bottom:16px;">'
                    f'<h1 style="color:white;margin:0;font-size:2.8rem;">{action_label}</h1>'
                    f'<p style="color:rgba(255,255,255,0.9);margin:12px 0 0;font-size:1.1rem;">'
                    f'Prix actuel : <strong>${sig_price:,.2f}</strong></p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(_signal_phrase(label, symbol))
                st.markdown(_confidence_phrase(confidence))
            else:
                st.markdown(
                    f'<div style="background:{color};padding:18px 24px;border-radius:12px;'
                    f'text-align:center;margin-bottom:12px;">'
                    f'<h1 style="color:white;margin:0;font-size:2.6rem;">{label}</h1>'
                    f'<p style="color:white;margin:6px 0 0;font-size:1.1rem;">'
                    f'Confiance : <strong>{confidence:.1%}</strong>'
                    f' &nbsp;|&nbsp; Prix : <strong>${sig_price:,.2f}</strong>'
                    f' &nbsp;|&nbsp; à <strong>{sig_time}</strong>'
                    f'</p></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.warning("En attente du premier signal (la première bougie de 1m doit se fermer…)")

        # ── Historique ────────────────────────────────────────────────────
        st.markdown("### Dernières prédictions")
        history = status.get("history", [])
        if history:
            rows = []
            for h in reversed(history):
                evaluated = h.get("evaluated", False)
                correct   = h.get("correct")
                ret_pct   = h.get("actual_ret_pct")
                lbl       = h.get("signal_label", "")
                _h_ts = h.get("timestamp")
                if not show_tech:
                    rows.append({
                        "Heure":    _fmt_paris(_h_ts, "%H:%M") if _h_ts else "–",
                        "Conseil":  f"{SIGNAL_EMOJI.get(lbl, '')} {SIGNAL_ACTION.get(lbl, lbl)}",
                        "Prix":     f"${h.get('price', 0):,.2f}",
                        "Résultat": ("✅ Correct" if correct else "❌ Incorrect") if evaluated else "⏳ En cours",
                    })
                else:
                    rows.append({
                        "Heure":      _fmt_paris(_h_ts, "%d/%m/%Y %H:%M:%S") if _h_ts else "–",
                        "Signal":     lbl,
                        "Conf.":      f"{h.get('confidence', 0):.1%}",
                        "Prix":       f"${h.get('price', 0):,.2f}",
                        "Évalué":     "✓" if evaluated else "…",
                        "Correct":    ("✅" if correct else "❌") if evaluated else "–",
                        "Δ prix (%)": f"{ret_pct:+.3f}" if ret_pct is not None else "–",
                    })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            if show_tech:
                fig_hist = go.Figure(go.Bar(
                    x=list(range(len(history))),
                    y=[h.get("confidence", 0) for h in history],
                    marker_color=[SIGNAL_COLOR.get(h.get("signal_label", ""), "#888") for h in history],
                    text=[h.get("signal_label", "") for h in history],
                    textposition="outside",
                ))
                fig_hist.update_layout(
                    title="Confiance des dernières prédictions",
                    yaxis_range=[0, 1.2], yaxis_title="Confidence",
                    height=240, template="plotly_dark",
                    margin=dict(l=0, r=0, t=40, b=0),
                    showlegend=False,
                )
                st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("En attente des premières prédictions…")

    if running and auto_refresh:
        time.sleep(5)
        st.rerun()


# ---------------------------------------------------------------------------
# Page : 📈 Marché
# ---------------------------------------------------------------------------
elif page == "📈 Marché":
    st.title("📈 Marché")

    if show_tech:
        c1, c2, c3 = st.columns(3)
        symbol   = c1.selectbox("Symbole",    SYMBOLS,            key="mkt_sym")
        interval = c2.selectbox("Intervalle", ["1h", "4h", "1d"], key="mkt_int")
        limit    = c3.slider("Bougies",       50, 500, 200,        key="mkt_lim")
    else:
        c1, c2 = st.columns(2)
        symbol = c1.selectbox("Symbole", SYMBOLS, key="mkt_sym")
        period_label = c2.selectbox(
            "Période",
            ["Dernière semaine", "Dernier mois", "6 derniers mois", "2 ans"],
            index=1,
            key="mkt_period",
        )
        _period_map = {
            "Dernière semaine": ("1h",  168),
            "Dernier mois":     ("1d",   30),
            "6 derniers mois":  ("1d",  180),
            "2 ans":            ("1d",  730),
        }
        interval, limit = _period_map[period_label]

    raw = api_get(f"/api/historical/{symbol}", {"interval": interval, "limit": limit})

    if raw:
        df = pd.DataFrame(raw)

        if show_tech:
            with st.expander("🔍 Diagnostic colonnes", expanded=False):
                st.write("**Colonnes reçues :**", df.columns.tolist())
                st.dataframe(df.dtypes.rename("dtype").to_frame(), use_container_width=False)
                st.dataframe(df.head(2), use_container_width=True)

        df["open_time"] = (
            pd.to_datetime(df["open_time"], utc=True, errors="coerce")
            .dt.tz_convert(_PARIS_TZ)
            .dt.tz_localize(None)   # strip tz for Plotly compatibility
        )
        for _col in ("open", "high", "low", "close", "volume"):
            df[_col] = pd.to_numeric(df[_col], errors="coerce")
        df = (
            df.dropna(subset=["open_time", "open", "high", "low", "close"])
            .drop_duplicates("open_time")
            .sort_values("open_time")
            .reset_index(drop=True)
        )

        if df.empty:
            st.warning("Données vides après nettoyage — vérifiez MongoDB.")
        else:
            last, prev = df.iloc[-1], df.iloc[-2]
            pct = (last["close"] - prev["close"]) / prev["close"] * 100

            # KPIs
            if not show_tech:
                m1, m2, m3 = st.columns(3)
                m1.metric(f"Prix {SYMBOL_NAME.get(symbol, symbol)}", f"${last['close']:,.2f}", f"{pct:+.2f}%")
                m2.metric("Plus haut", f"${last['high']:,.2f}")
                m3.metric("Plus bas",  f"${last['low']:,.2f}")
            else:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Prix",   f"${last['close']:,.2f}", f"{pct:+.2f}%")
                m2.metric("Haut",   f"${last['high']:,.2f}")
                m3.metric("Bas",    f"${last['low']:,.2f}")
                m4.metric("Volume", f"{last['volume']:,.0f}")

            # Chart
            if show_tech:
                fig = make_subplots(
                    rows=2, cols=1, shared_xaxes=True,
                    row_heights=[0.75, 0.25], vertical_spacing=0.02,
                )
                fig.add_trace(go.Candlestick(
                    x=df["open_time"], open=df["open"], high=df["high"],
                    low=df["low"], close=df["close"], name="OHLC",
                ), row=1, col=1)
                fig.add_trace(go.Bar(
                    x=df["open_time"], y=df["volume"], name="Volume",
                    marker_color="rgba(100,149,237,0.5)",
                ), row=2, col=1)
                fig.update_layout(
                    title=f"{symbol} — {interval}",
                    xaxis_rangeslider_visible=False,
                    height=540, template="plotly_dark",
                    margin=dict(l=0, r=0, t=40, b=0),
                )
            else:
                fig = go.Figure(go.Candlestick(
                    x=df["open_time"], open=df["open"], high=df["high"],
                    low=df["low"], close=df["close"], name="OHLC",
                ))
                arrow = "▲" if pct >= 0 else "▼"
                fig.update_layout(
                    title=f"{SYMBOL_NAME.get(symbol, symbol)} — {arrow} {abs(pct):.2f}% aujourd'hui",
                    xaxis_rangeslider_visible=False,
                    height=480, template="plotly_dark",
                    margin=dict(l=0, r=0, t=40, b=0),
                )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Données indisponibles — vérifiez que l'API et MongoDB sont démarrés.")


# ---------------------------------------------------------------------------
# Page : 📅 Vision Long Terme
# ---------------------------------------------------------------------------
elif page == "📅 Vision Long Terme":
    st.title("📅 Vision Long Terme")

    st.warning(
        "⚠️ **Ces signaux sont basés sur des données JOURNALIÈRES (1 jour).**\n\n"
        "Ils peuvent être différents des signaux de la page 🔴 Live qui analysent des données à la MINUTE. "
        "C'est normal — un bot peut recommander d'acheter sur le long terme (journalier) et d'attendre sur le court terme (minute). "
        "C'est comme comparer la météo de la semaine vs la météo de l'heure."
    )

    if not show_tech:
        st.info(
            "📋 Cette page affiche l'**historique** des recommandations du bot et si elles étaient correctes — "
            "contrairement à la page 🔴 Live qui montre uniquement ce qui se passe *maintenant*. "
            "Utile pour évaluer la fiabilité du bot sur le passé."
        )
    else:
        st.caption("Prédictions à la demande via /predict + historique depuis PostgreSQL.")

    c1, c2 = st.columns([3, 1])
    symbol   = c1.selectbox("Symbole", SYMBOLS, key="sig_sym")
    sym_name = SYMBOL_NAME.get(symbol, symbol)

    if "predictions" not in st.session_state:
        st.session_state.predictions = {}

    c2.write("")
    c2.write("")
    if c2.button("🔄 Voir la recommandation du jour"):
        with st.spinner("Prédiction en cours…"):
            pred = api_get_live("/predict", {"symbol": symbol})
            if pred:
                st.session_state.predictions[symbol] = pred

    pred = st.session_state.predictions.get(symbol)
    if pred:
        label      = pred["signal_label"]
        confidence = pred["confidence"]
        price      = pred["price"]
        color      = SIGNAL_COLOR.get(label, "#888888")

        if not show_tech:
            action_label = f"{SIGNAL_EMOJI.get(label, '')} {SIGNAL_ACTION.get(label, label)}"
            st.markdown(
                f'<div style="background:{color};padding:24px;border-radius:14px;'
                f'text-align:center;margin-bottom:16px;">'
                f'<h1 style="color:white;margin:0;font-size:2.6rem;">{action_label}</h1>'
                f'<p style="color:rgba(255,255,255,0.9);margin:10px 0 0;font-size:1.1rem;">'
                f'Prix actuel : <strong>${price:,.2f}</strong></p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown(_signal_phrase(label, symbol))
            st.markdown(_confidence_phrase(confidence))
        else:
            st.markdown(
                f'<div style="background:{color};padding:20px 24px;border-radius:12px;'
                f'text-align:center;margin-bottom:12px;">'
                f'<h1 style="color:white;margin:0;font-size:2.8rem;">{label}</h1>'
                f'<p style="color:white;margin:6px 0 0;font-size:1.1rem;">'
                f'Confiance : <strong>{confidence:.1%}</strong></p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            a, b, c = st.columns(3)
            a.metric("Prix",      f"${price:,.2f}")
            b.metric("Timestamp", _fmt_paris(pred["timestamp"]))
            c.metric("Modèle",    pred["model_version"].split("_")[1])
    else:
        st.info("Cliquez sur **Voir la recommandation du jour** pour lancer une prédiction.")

    st.markdown("---")
    st.subheader(f"Historique des prédictions — {sym_name if not show_tech else symbol}")

    hist = api_get("/signal/history", {"symbol": symbol, "limit": 50})
    if hist:
        df_h = pd.DataFrame(hist)

        # Detect the date column — API may use different names
        _TIME_CANDIDATES = ["timestamp", "open_time", "time", "date", "created_at", "signal_time"]
        _ts_col = next((c for c in _TIME_CANDIDATES if c in df_h.columns), None)

        if show_tech:
            st.caption(
                f"Colonnes API : `{df_h.columns.tolist()}` — "
                f"colonne date détectée : `{_ts_col}`"
            )

        if _ts_col is None:
            st.warning(
                f"Impossible de trouver une colonne date dans la réponse API. "
                f"Colonnes disponibles : `{df_h.columns.tolist()}`"
            )
        else:
            # Normalize to a single internal column _ts_paris (tz-aware, Paris)
            df_h["_ts_paris"] = (
                pd.to_datetime(df_h[_ts_col], utc=True, errors="coerce")
                .dt.tz_convert(_PARIS_TZ)
            )

            fig = go.Figure(go.Bar(
                x=df_h["_ts_paris"],
                y=df_h["confidence"],
                marker_color=[SIGNAL_COLOR.get(l, "#888") for l in df_h["signal_label"]],
                text=(
                    df_h["signal_label"] if show_tech
                    else df_h["signal_label"].map(SIGNAL_EMOJI)
                ),
                textposition="outside",
            ))
            fig.update_layout(
                title=f"Historique — {sym_name if not show_tech else symbol}",
                yaxis_title="Confiance" if not show_tech else "Confidence",
                yaxis_range=[0, 1.15],
                height=320, template="plotly_dark",
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

            if not show_tech:
                df_disp = df_h.copy()
                _all_midnight = (
                    (df_disp["_ts_paris"].dt.hour == 0) &
                    (df_disp["_ts_paris"].dt.minute == 0)
                ).all()
                if _all_midnight:
                    st.caption(
                        "ℹ️ Les signaux historiques sont calculés sur des données journalières "
                        "— l'heure exacte n'est pas disponible."
                    )
                    _date_col = "Date"
                    df_disp[_date_col] = df_disp["_ts_paris"].dt.strftime("%d/%m/%Y")
                else:
                    _date_col = "Heure"
                    df_disp[_date_col] = df_disp["_ts_paris"].dt.strftime("%d/%m/%Y %H:%M")
                df_disp["Conseil"]   = df_disp["signal_label"].map(
                    {"BUY": "📈 Acheter", "SELL": "📉 Vendre", "HOLD": "⏸️ Attendre"}
                )
                df_disp["Confiance"] = df_disp["confidence"].apply(lambda x: f"{x:.0%}")
                st.dataframe(
                    df_disp.sort_values("_ts_paris", ascending=False)
                    [[_date_col, "Conseil", "Confiance"]]
                    .reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.dataframe(
                    df_h.sort_values("_ts_paris", ascending=False)
                    [["_ts_paris", "signal_label", "confidence", "model_version"]]
                    .rename(columns={"_ts_paris": "timestamp (Paris)"})
                    .reset_index(drop=True),
                    use_container_width=True,
                )
    else:
        st.info("Aucun historique — lancez au moins une prédiction via le bouton ci-dessus.")


# ---------------------------------------------------------------------------
# Page : 📊 Indicateurs
# ---------------------------------------------------------------------------
elif page == "📊 Indicateurs":
    st.title("📊 Indicateurs de marché")

    c1, c2 = st.columns(2)
    symbol   = c1.selectbox("Symbole", SYMBOLS, key="ind_sym")
    sym_name = SYMBOL_NAME.get(symbol, symbol)

    if show_tech:
        limit = c2.slider("Bougies", 50, 300, 120, key="ind_lim")
    else:
        limit = 90
        c2.caption("90 dernières périodes")

    if not show_tech:
        with st.expander("📖 Que signifient ces termes ?", expanded=True):
            st.markdown(
                "**RSI** — *Indice de Force Relative* : mesure si un actif est **trop acheté** "
                "(valeur >70, risque de baisse) ou **trop vendu** (<30, rebond possible). "
                "C'est comme un thermomètre de l'appétit des investisseurs."
            )
            st.markdown(
                "**MACD** — *Convergence/Divergence de Moyennes Mobiles* : détecte les **changements "
                "de tendance** en comparant deux moyennes de prix sur des périodes différentes. "
                "Quand les deux lignes se croisent, la tendance bascule."
            )
            st.markdown(
                "**Momentum** : la **vitesse à laquelle le prix change** — un momentum élevé "
                "signale une tendance forte (haussière ou baissière). C'est l'élan du marché."
            )
            st.markdown(
                "**Bandes de Bollinger** : bandes de **volatilité** tracées autour du prix moyen. "
                "Quand le prix sort des bandes, il est dans une zone inhabituelle — souvent signe "
                "d'un mouvement fort ou d'un retour vers la moyenne."
            )

    raw = api_get("/features", {"symbol": symbol, "limit": limit})

    if raw:
        df = pd.DataFrame(raw)
        df["timestamp"] = (
            pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            .dt.tz_convert(_PARIS_TZ)
            .dt.tz_localize(None)   # strip tz for Plotly compatibility
        )
        df = df.sort_values("timestamp").reset_index(drop=True)

        last_rsi    = df["rsi_14"].iloc[-1]    if not df["rsi_14"].isna().all()    else None
        last_macd   = df["macd"].iloc[-1]      if not df["macd"].isna().all()      else None
        last_sig    = df["macd_signal"].iloc[-1] if not df["macd_signal"].isna().all() else None

        # ── RSI ───────────────────────────────────────────────────────────
        if not show_tech and last_rsi is not None:
            if last_rsi >= 70:
                rsi_label   = "🔴 Suracheté"
                rsi_explain = (
                    f"Le marché a **beaucoup monté** ces derniers jours "
                    f"(RSI {last_rsi:.0f}/100). Une correction est possible."
                )
            elif last_rsi <= 30:
                rsi_label   = "🟢 Survendu"
                rsi_explain = (
                    f"Le marché a **beaucoup baissé** ces derniers jours "
                    f"(RSI {last_rsi:.0f}/100). Un rebond est possible."
                )
            else:
                rsi_label   = "🟡 Neutre"
                rsi_explain = (
                    f"Le marché est dans une zone **normale** "
                    f"(RSI {last_rsi:.0f}/100). Pas de signal fort."
                )
            st.markdown(f"### Force du marché : {rsi_label}")
            st.markdown(rsi_explain)
        else:
            st.subheader("RSI (14)")

        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(
            x=df["timestamp"], y=df["rsi_14"], name="RSI 14",
            line=dict(color="#FFD700"),
        ))
        fig_rsi.add_hline(y=70, line_dash="dot", line_color="red",   annotation_text="Surachat 70")
        fig_rsi.add_hline(y=30, line_dash="dot", line_color="green", annotation_text="Survente 30")
        fig_rsi.update_layout(
            height=230, yaxis_range=[0, 100], template="plotly_dark",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_rsi, use_container_width=True)

        # ── MACD ──────────────────────────────────────────────────────────
        if not show_tech and last_macd is not None and last_sig is not None:
            if last_macd > last_sig:
                macd_label   = "📈 Tendance haussière"
                macd_explain = "Le momentum est **positif** : la dynamique du marché est à la hausse."
            else:
                macd_label   = "📉 Tendance baissière"
                macd_explain = "Le momentum est **négatif** : la dynamique du marché est à la baisse."
            st.markdown(f"### Tendance : {macd_label}")
            st.markdown(macd_explain)
        else:
            st.subheader("MACD")

        fig_macd = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.55, 0.45], vertical_spacing=0.04,
        )
        fig_macd.add_trace(go.Scatter(
            x=df["timestamp"], y=df["macd"], name="MACD",
            line=dict(color="#00BFFF"),
        ), row=1, col=1)
        fig_macd.add_trace(go.Scatter(
            x=df["timestamp"], y=df["macd_signal"], name="Signal",
            line=dict(color="#FF6347"),
        ), row=1, col=1)
        hist_colors = ["#00C853" if v >= 0 else "#D50000" for v in df["macd_hist"].fillna(0)]
        fig_macd.add_trace(go.Bar(
            x=df["timestamp"], y=df["macd_hist"],
            name="Histogramme", marker_color=hist_colors,
        ), row=2, col=1)
        fig_macd.update_layout(
            height=350, template="plotly_dark",
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_macd, use_container_width=True)

        # Bollinger Bands + valeurs exactes : mode technique uniquement
        if show_tech:
            st.subheader("Prix & Bandes de Bollinger")
            fig_bb = go.Figure()
            fig_bb.add_trace(go.Scatter(
                x=df["timestamp"], y=df["bb_upper"], name="BB Upper",
                line=dict(color="rgba(100,200,255,0.5)", dash="dot"),
            ))
            fig_bb.add_trace(go.Scatter(
                x=df["timestamp"], y=df["bb_lower"], name="BB Lower",
                line=dict(color="rgba(100,200,255,0.5)", dash="dot"),
                fill="tonexty", fillcolor="rgba(100,200,255,0.06)",
            ))
            fig_bb.add_trace(go.Scatter(
                x=df["timestamp"], y=df["bb_mid"], name="BB Mid",
                line=dict(color="rgba(100,200,255,0.35)", dash="dash"),
            ))
            fig_bb.add_trace(go.Scatter(
                x=df["timestamp"], y=df["close"], name="Close",
                line=dict(color="white", width=1.5),
            ))
            fig_bb.update_layout(
                height=350, template="plotly_dark",
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig_bb, use_container_width=True)

            st.markdown("**Valeurs actuelles**")
            row = df.iloc[-1]
            v1, v2, v3, v4, v5 = st.columns(5)
            v1.metric("RSI",      f"{row.get('rsi_14', 0):.1f}")
            v2.metric("MACD",     f"{row.get('macd', 0):.4f}")
            v3.metric("BB Upper", f"{row.get('bb_upper', 0):,.2f}")
            v4.metric("BB Lower", f"{row.get('bb_lower', 0):,.2f}")
            v5.metric("ATR 14",   f"{row.get('atr_14', 0):.4f}")
    else:
        st.info("Données de features indisponibles — vérifiez que l'API et PostgreSQL sont démarrés.")


# ---------------------------------------------------------------------------
# Page : ⚙️ Modèle
# ---------------------------------------------------------------------------
elif page == "⚙️ Modèle":
    st.title("⚙️ Le modèle ML")

    metrics = api_get("/model/metrics")
    if metrics:
        for m in metrics:
            name    = SYMBOL_NAME.get(m["symbol"], m["symbol"])
            n_total = m["n_train"] + m["n_val"] + m["n_test"]
            acc_pct = int(m["accuracy"] * 100)
            sharpe  = m["sharpe_ratio"]

            expander_title = (
                f"**{name}** ({m['symbol']})" if not show_tech
                else f"**{m['symbol']}** — {m['model_name'].upper()}"
            )
            with st.expander(expander_title, expanded=True):
                if not show_tech:
                    if sharpe > 2:
                        perf = f"🟢 **Très performant** — génère **{sharpe:.1f}× plus de gains que de risques**"
                    elif sharpe > 1:
                        perf = f"🟡 **Correct** — génère **{sharpe:.1f}× plus de gains que de risques**"
                    elif sharpe > 0:
                        perf = f"🟠 **Limité** — légèrement positif ({sharpe:.2f})"
                    else:
                        perf = f"🔴 **En difficulté** sur cette période ({sharpe:.2f})"

                    sol_note = ""
                    if m["symbol"] == "SOLUSDT" and sharpe < 0.5:
                        sol_note = (
                            "\n> ⚠️ **Pourquoi Solana est plus difficile ?** "
                            "Solana est une crypto **plus volatile et imprévisible** que Bitcoin ou Ethereum. "
                            "Ses mouvements de prix sont plus brusques, ce qui rend la prédiction plus difficile pour le bot.\n"
                        )
                    st.markdown(f"""
Le bot a été entraîné sur **{n_total:,} données historiques** de {name}.

- Il prédit correctement **{acc_pct}% du temps**
- {perf}
{sol_note}
*Dernier entraînement : {m['date_train'][:10]} · algorithme : {m['model_name'].upper()}*
                    """)
                else:
                    a, b, c = st.columns(3)
                    a.metric("Accuracy",     f"{m['accuracy']:.1%}")
                    b.metric("F1 macro",     f"{m['f1_macro']:.3f}")
                    c.metric("Sharpe Ratio", f"{m['sharpe_ratio']:.3f}")

                    d, e, f_ = st.columns(3)
                    d.metric("Train", f"{m['n_train']} lignes")
                    e.metric("Val",   f"{m['n_val']} lignes")
                    f_.metric("Test", f"{m['n_test']} lignes")

                    st.caption(
                        f"Version : `{m['model_version']}` · "
                        f"Entraîné le {m['date_train'][:10]}"
                    )
    else:
        st.info("Métriques indisponibles — vérifiez que l'API est démarrée.")


# ---------------------------------------------------------------------------
# Page : 🔍 Monitoring
# ---------------------------------------------------------------------------
elif page == "🔍 Monitoring":
    st.title("🔍 Monitoring")

    health   = api_get_live("/health")
    streams  = api_get_live("/api/stream/active")
    sym_data = api_get("/api/symbols")

    api_ok      = health is not None and health.get("status") == "healthy"
    model_ok    = health.get("model_loaded", False) if health else False
    stream_list = streams.get("active_streams", []) if streams else []
    syms_in_db  = sym_data.get("symbols", []) if sym_data else []

    # LivePredictor status per symbol (source of truth for running predictors)
    _live_statuses = {
        sym: (api_get_live("/live/status", {"symbol": sym}) or {})
        for sym in SYMBOLS
    }
    live_running = [sym for sym, s in _live_statuses.items() if s.get("running", False)]

    if not show_tech:
        # Global status banner
        st.markdown("### État général du système")
        if api_ok and model_ok:
            st.success("✅ Tout fonctionne correctement")
        elif api_ok:
            st.warning("⚠️ L'API fonctionne mais le modèle ML n'est pas chargé")
        else:
            st.error("🔴 L'API est inaccessible — vérifiez que les services sont démarrés")

        st.markdown("### Services")
        services = [
            ("Serveur principal (API)", api_ok,
             "Le serveur qui fait tourner le bot est opérationnel." if api_ok
             else "Le serveur ne répond pas."),
            ("Modèle d'intelligence artificielle", model_ok,
             "Le modèle de prédiction est chargé et prêt." if model_ok
             else "Le modèle n'est pas encore chargé."),
            (f"Prédicteurs live ({len(live_running)} actif(s))", len(live_running) > 0,
             f"Le bot analyse en ce moment : {', '.join(SYMBOL_NAME.get(s, s) for s in live_running)}." if live_running
             else "Aucun prédicteur live actif pour l'instant."),
            ("Base de données", len(syms_in_db) > 0,
             f"Données disponibles pour : {', '.join(SYMBOL_NAME.get(s, s) for s in syms_in_db)}." if syms_in_db
             else "Aucune donnée trouvée en base."),
        ]
        for svc_name, ok, desc in services:
            light = "🟢" if ok else "🔴"
            st.markdown(f"{light} **{svc_name}**")
            st.caption(f"  {desc}")

        st.markdown("### Interfaces disponibles")
        _links = st.columns(4)
        _link_data = [
            ("📖 API", "http://localhost:8001/docs"),
            ("📊 Grafana", "http://localhost:3000"),
            ("🔬 Prometheus", "http://localhost:9090"),
            ("🌊 Airflow", "http://localhost:8080"),
        ]
        for col, (label, url) in zip(_links, _link_data):
            col.link_button(label, url, use_container_width=True)

    else:
        c_left, c_right = st.columns(2)

        with c_left:
            st.subheader("Statut des services")
            if health:
                ok = health.get("status") == "healthy"
                ml = health.get("model_loaded", False)
                st.markdown(f"{'🟢' if ok else '🔴'} **API FastAPI** : `{health.get('status', '?')}`")
                st.markdown(f"{'🟢' if ml else '🔴'} **Modèle ML chargé** : `{ml}`")
            else:
                st.markdown("🔴 **API FastAPI** : inaccessible")

            st.markdown("")
            if streams:
                active = streams.get("active_streams", [])
                st.markdown(
                    f"{'🟢' if active else '⚪'} **WebSocket streams actifs** : {len(active)}"
                )
                for s in active:
                    st.markdown(f"  - `{s['symbol']}` — {s['connected_clients']} client(s)")

            st.markdown("")
            st.markdown(
                f"{'🟢' if live_running else '⚪'} **Prédicteurs live actifs** : "
                f"{len(live_running)}/{len(SYMBOLS)}"
            )
            for sym in SYMBOLS:
                s_data = _live_statuses[sym]
                run    = s_data.get("running", False)
                score  = s_data.get("score_str", "–") if run else "–"
                st.markdown(
                    f"  - {'🟢' if run else '🔴'} `{sym}` — "
                    + (f"actif · score : {score}" if run else "arrêté")
                )

        with c_right:
            st.subheader("Liens & interfaces")
            st.markdown("""
| Service | Lien |
|---|---|
| API Swagger | [localhost:8001/docs](http://localhost:8001/docs) |
| Grafana | [localhost:3000](http://localhost:3000) |
| Prometheus | [localhost:9090](http://localhost:9090) |
| Airflow | [localhost:8080](http://localhost:8080) |
            """)

        st.markdown("---")
        st.subheader("Symboles disponibles en base")
        if syms_in_db:
            st.write(", ".join(syms_in_db))
        else:
            st.info("MongoDB indisponible.")

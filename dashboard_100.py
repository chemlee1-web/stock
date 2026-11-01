import io
import re
import urllib.error
import urllib.request
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# 페이지 설정
st.set_page_config(page_title="100개 기술지표 분석 대시보드", layout="wide")
st.markdown(
    """
    <style>
    :root {
        color-scheme: dark;
        --page: #0b1120;
        --panel: #111a2b;
        --panel-soft: #151f32;
        --border: #263248;
        --text: #e6edf7;
        --muted: #91a0b7;
        --accent: #55d6be;
    }

    .stApp {
        background:
            radial-gradient(ellipse at 78% -10%, rgba(52, 94, 144, 0.19), transparent 42%),
            var(--page);
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: rgba(11, 17, 32, 0.72);
    }

    [data-testid="stSidebar"] {
        background: #0e1727;
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 2rem;
    }

    .block-container {
        max-width: 1540px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        color: var(--text) !important;
        letter-spacing: -0.035em;
    }

    h1 {
        font-size: clamp(1.8rem, 3vw, 2.45rem) !important;
        font-weight: 720 !important;
        margin-bottom: 0.3rem !important;
    }

    h2 {
        font-size: 1.25rem !important;
        font-weight: 650 !important;
    }

    h3 {
        font-size: 1.15rem !important;
        font-weight: 620 !important;
    }

    [data-testid="stCaptionContainer"], [data-testid="stMarkdownContainer"] p {
        color: var(--muted);
    }

    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #141f32, #101827);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        min-height: 116px;
    }

    [data-testid="stMetricLabel"] p {
        color: var(--muted) !important;
        font-size: 0.84rem;
        font-weight: 550;
    }

    [data-testid="stMetricValue"] {
        color: var(--text);
        font-size: clamp(1rem, 1.25vw, 1.25rem);
        font-weight: 680;
    }

    [data-testid="stMetricDelta"] {
        font-size: 0.82rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(17, 26, 43, 0.72);
        border-color: var(--border) !important;
        border-radius: 16px;
    }

    [data-testid="stAlert"] {
        border-radius: 12px;
        border: 1px solid var(--border);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
    }

    [data-testid="stExpander"] {
        background: rgba(17, 26, 43, 0.72);
        border: 1px solid var(--border);
        border-radius: 14px;
    }

    [data-testid="stTextInput"] input {
        background: var(--panel-soft) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }

    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: var(--panel-soft);
        border-color: var(--border);
        border-radius: 10px;
        color: var(--text);
    }

    input[type="checkbox"] {
        accent-color: var(--accent);
    }

    [data-testid="stCheckbox"] label {
        color: var(--text);
    }

    hr {
        border-color: var(--border);
        margin: 1.6rem 0;
    }

    @media (max-width: 700px) {
        .block-container {
            padding: 1.2rem 1rem 3rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("시장 지표 대시보드")
st.caption(
    "기술지표 100개 + FRED 미국 거시지표 | 통합 점수: 기술 70% · 거시 30% | "
    "분석 점수는 참고용이며 실시간 시세나 투자 수익을 보장하지 않습니다."
)
st.session_state.setdefault("ticker_input", "FFIV")
ticker = st.text_input(
    "종목 코드 입력 (예: FFIV, TQQQ, AAPL)", key="ticker_input"
).upper().strip()


MAX_ANALYSIS_HISTORY = 20
SUPPORTED_PERIODS = ["6m", "1y", "2y", "5y"]


def record_analysis_history(history, ticker_value, period_value):
  """현재 방문자 세션의 최근 분석 20개를 유지한다."""
  updated_history = [
      item
      for item in history
      if (item["ticker"], item["period"]) != (ticker_value, period_value)
  ]
  updated_history.insert(
      0,
      {
          "ticker": ticker_value,
          "period": period_value,
          "analyzed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
      },
  )
  return updated_history[:MAX_ANALYSIS_HISTORY]


def select_analysis_from_history(ticker_value, period_value):
  st.session_state["ticker_input"] = ticker_value
  st.session_state["period_input"] = period_value
  st.session_state["force_history_record"] = True


def render_analysis_history(container, history):
  with container.container():
    st.markdown("---")
    st.subheader("최근 분석 기록")
    st.caption("이 방문자 세션의 기록입니다. 버튼을 누르면 다시 분석합니다.")
    if history:
      for index, entry in enumerate(history):
        analyzed_at = datetime.fromisoformat(entry["analyzed_at"])
        button_label = (
            f"{entry['ticker']} · {entry['period']} · "
            f"{analyzed_at.astimezone().strftime('%m/%d %H:%M')}"
        )
        st.button(
            button_label,
            key=f"analysis_history_{index}",
            on_click=select_analysis_from_history,
            args=(entry["ticker"], entry["period"]),
            use_container_width=True,
        )
    else:
      st.caption("성공한 분석이 여기에 저장됩니다.")

st.session_state.setdefault("analysis_history", [])
st.session_state.setdefault("last_successful_analysis", None)

# 사이드바 설정
st.sidebar.header("⚙️ 분석 설정")
st.session_state.setdefault("period_input", "1y")
period = st.sidebar.selectbox(
    "조회 기간", options=SUPPORTED_PERIODS, key="period_input"
)
use_trend_guard = st.sidebar.checkbox(
    "🛡️ Trend Guard (20MA ≥ 60MA 정배열 필터)", value=True
)
history_panel = st.sidebar.empty()

@st.cache_data(ttl=300)
def load_real_stock_data(symbol, period_val):
  """Yahoo Finance 일봉 데이터에서 100개 기술지표와 그룹별 신호를 계산한다."""
  yahoo_period = {"6m": "6mo"}.get(period_val, period_val)
  df = yf.Ticker(symbol).history(period=yahoo_period, interval="1d")
  if df.empty:
    return None
  if len(df) < 60:
    return None

  if df.index.tz is not None:
    df.index = df.index.tz_localize(None)
  close = df["Close"].astype(float)
  high = df["High"].astype(float)
  low = df["Low"].astype(float)
  open_price = df["Open"].astype(float)
  volume = df["Volume"].astype(float)
  typical = (high + low + close) / 3
  indicators = {}

  def add(name, values):
    indicators[name] = values

  def wma(values, window):
    weights = np.arange(1, window + 1, dtype=float)
    return values.rolling(window).apply(
        lambda sample: np.dot(sample, weights) / weights.sum(), raw=True
    )

  def rsi(values, window):
    delta = values.diff()
    gain = delta.clip(lower=0).ewm(
        alpha=1 / window, min_periods=window, adjust=False
    ).mean()
    loss = (-delta.clip(upper=0)).ewm(
        alpha=1 / window, min_periods=window, adjust=False
    ).mean()
    return 100 - 100 / (1 + gain / loss.replace(0, np.nan))

  previous_close = close.shift(1)
  true_range = pd.concat(
      [
          high - low,
          (high - previous_close).abs(),
          (low - previous_close).abs(),
      ],
      axis=1,
  ).max(axis=1)
  atr14 = true_range.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()

  # 25 trend indicators
  for window in [5, 10, 20, 30, 50, 60]:
    add(f"SMA_{window}", close.rolling(window).mean())
  for window in [8, 12, 20, 26, 50]:
    add(f"EMA_{window}", close.ewm(span=window, adjust=False).mean())
  for window in [10, 20, 30]:
    add(f"WMA_{window}", wma(close, window))
  ema20 = close.ewm(span=20, adjust=False).mean()
  ema20_twice = ema20.ewm(span=20, adjust=False).mean()
  ema20_thrice = ema20_twice.ewm(span=20, adjust=False).mean()
  add("DEMA_20", 2 * ema20 - ema20_twice)
  add("TEMA_20", 3 * ema20 - 3 * ema20_twice + ema20_thrice)
  add("HMA_20", wma(2 * wma(close, 10) - wma(close, 20), 4))
  add(
      "VWMA_20",
      (close * volume).rolling(20).sum()
      / volume.rolling(20).sum().replace(0, np.nan),
  )
  add(
      "VWAP_20",
      (typical * volume).rolling(20).sum()
      / volume.rolling(20).sum().replace(0, np.nan),
  )
  add("ZLEMA_20", (close + close - close.shift(9)).ewm(span=20, adjust=False).mean())
  efficiency = close.diff(10).abs() / close.diff().abs().rolling(10).sum()
  smoothing = (efficiency * (2 / 3 - 2 / 31) + 2 / 31) ** 2
  smoothing = smoothing.fillna(0)
  kama = pd.Series(np.nan, index=df.index, dtype=float)
  if len(df) >= 10:
    kama.iloc[9] = close.iloc[:10].mean()
    for i in range(10, len(df)):
      kama.iloc[i] = kama.iloc[i - 1] + smoothing.iloc[i] * (
          close.iloc[i] - kama.iloc[i - 1]
      )
  add("KAMA_10", kama)
  add(
      "LSMA_20",
      close.rolling(20).apply(
          lambda sample: np.polyval(np.polyfit(np.arange(20), sample, 1), 19),
          raw=True,
      ),
  )
  alma_weights = np.exp(-((np.arange(20) - 12) ** 2) / (2 * 4.5**2))
  add(
      "ALMA_20",
      close.rolling(20).apply(
          lambda sample: np.dot(sample, alma_weights) / alma_weights.sum(),
          raw=True,
      ),
  )
  basic_upper = (high + low) / 2 + 3 * atr14
  basic_lower = (high + low) / 2 - 3 * atr14
  final_upper = pd.Series(np.nan, index=df.index, dtype=float)
  final_lower = pd.Series(np.nan, index=df.index, dtype=float)
  supertrend = pd.Series(np.nan, index=df.index, dtype=float)
  for i in range(len(df)):
    if pd.isna(atr14.iloc[i]):
      continue
    if i == 0 or pd.isna(final_upper.iloc[i - 1]):
      final_upper.iloc[i] = basic_upper.iloc[i]
      final_lower.iloc[i] = basic_lower.iloc[i]
      supertrend.iloc[i] = basic_upper.iloc[i]
      continue
    final_upper.iloc[i] = (
        basic_upper.iloc[i]
        if basic_upper.iloc[i] < final_upper.iloc[i - 1]
        or close.iloc[i - 1] > final_upper.iloc[i - 1]
        else final_upper.iloc[i - 1]
    )
    final_lower.iloc[i] = (
        basic_lower.iloc[i]
        if basic_lower.iloc[i] > final_lower.iloc[i - 1]
        or close.iloc[i - 1] < final_lower.iloc[i - 1]
        else final_lower.iloc[i - 1]
    )
    if supertrend.iloc[i - 1] == final_upper.iloc[i - 1]:
      supertrend.iloc[i] = (
          final_upper.iloc[i]
          if close.iloc[i] <= final_upper.iloc[i]
          else final_lower.iloc[i]
      )
    else:
      supertrend.iloc[i] = (
          final_lower.iloc[i]
          if close.iloc[i] >= final_lower.iloc[i]
          else final_upper.iloc[i]
      )
  add("Supertrend_10_3", supertrend)
  psar = pd.Series(np.nan, index=df.index, dtype=float)
  if len(df) > 1:
    rising = close.iloc[1] >= close.iloc[0]
    psar.iloc[0] = low.iloc[0] if rising else high.iloc[0]
    extreme = high.iloc[0] if rising else low.iloc[0]
    acceleration = 0.02
    for i in range(1, len(df)):
      sar = psar.iloc[i - 1] + acceleration * (extreme - psar.iloc[i - 1])
      if rising:
        sar = min(sar, low.iloc[i - 1], low.iloc[i])
        if low.iloc[i] < sar:
          rising = False
          sar = extreme
          extreme = low.iloc[i]
          acceleration = 0.02
        elif high.iloc[i] > extreme:
          extreme = high.iloc[i]
          acceleration = min(acceleration + 0.02, 0.2)
      else:
        sar = max(sar, high.iloc[i - 1], high.iloc[i])
        if high.iloc[i] > sar:
          rising = True
          sar = extreme
          extreme = high.iloc[i]
          acceleration = 0.02
        elif low.iloc[i] < extreme:
          extreme = low.iloc[i]
          acceleration = min(acceleration + 0.02, 0.2)
      psar.iloc[i] = sar
  add("Parabolic_SAR", psar)

  # 30 momentum indicators
  for window in [6, 14, 21]:
    add(f"RSI_{window}", rsi(close, window))
  ema12 = close.ewm(span=12, adjust=False).mean()
  ema26 = close.ewm(span=26, adjust=False).mean()
  macd = ema12 - ema26
  macd_signal = macd.ewm(span=9, adjust=False).mean()
  add("MACD", macd)
  add("MACD_Signal", macd_signal)
  add("MACD_Hist", macd - macd_signal)
  ppo = 100 * macd / ema26.replace(0, np.nan)
  ppo_signal = ppo.ewm(span=9, adjust=False).mean()
  add("PPO", ppo)
  add("PPO_Signal", ppo_signal)
  add("PPO_Hist", ppo - ppo_signal)
  lowest14 = low.rolling(14).min()
  highest14 = high.rolling(14).max()
  stoch_k = 100 * (close - lowest14) / (highest14 - lowest14).replace(0, np.nan)
  add("Stoch_K", stoch_k)
  add("Stoch_D", stoch_k.rolling(3).mean())
  rsi14 = indicators["RSI_14"]
  rsi_min = rsi14.rolling(14).min()
  rsi_max = rsi14.rolling(14).max()
  stoch_rsi = 100 * (rsi14 - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)
  add("StochRSI_K", stoch_rsi)
  add("StochRSI_D", stoch_rsi.rolling(3).mean())
  add("Williams_R", -100 * (highest14 - close) / (highest14 - lowest14).replace(0, np.nan))
  mean_typical = typical.rolling(20).mean()
  mean_deviation = typical.rolling(20).apply(
      lambda sample: np.mean(np.abs(sample - sample.mean())), raw=True
  )
  add("CCI_20", (typical - mean_typical) / (0.015 * mean_deviation))
  add("ROC_12", close.pct_change(12) * 100)
  add("Momentum_10", close - close.shift(10))
  momentum = close.diff()
  tsi = (
      momentum.ewm(span=25, adjust=False).mean().ewm(span=13, adjust=False).mean()
      / momentum.abs().ewm(span=25, adjust=False).mean().ewm(
          span=13, adjust=False
      ).mean()
      * 100
  )
  add("TSI", tsi)
  add("TSI_Signal", tsi.ewm(span=7, adjust=False).mean())
  up_sum = momentum.clip(lower=0).rolling(14).sum()
  down_sum = (-momentum.clip(upper=0)).rolling(14).sum()
  add("CMO_14", 100 * (up_sum - down_sum) / (up_sum + down_sum))
  buying_pressure = close - pd.concat([low, previous_close], axis=1).min(axis=1)
  bp7 = buying_pressure.rolling(7).sum() / true_range.rolling(7).sum()
  bp14 = buying_pressure.rolling(14).sum() / true_range.rolling(14).sum()
  bp28 = buying_pressure.rolling(28).sum() / true_range.rolling(28).sum()
  add("Ultimate_Oscillator", 100 * (4 * bp7 + 2 * bp14 + bp28) / 7)
  aroon_high = high.rolling(26).apply(
      lambda sample: 100 * np.argmax(sample) / 25, raw=True
  )
  aroon_low = low.rolling(26).apply(
      lambda sample: 100 * np.argmin(sample) / 25, raw=True
  )
  add("Aroon_Up", aroon_high)
  add("Aroon_Down", aroon_low)
  add("Aroon_Osc", aroon_high - aroon_low)
  upward = high.diff()
  downward = -low.diff()
  plus_dm = upward.where((upward > downward) & (upward > 0), 0)
  minus_dm = downward.where((downward > upward) & (downward > 0), 0)
  plus_di = 100 * plus_dm.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean() / atr14
  minus_di = 100 * minus_dm.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean() / atr14
  dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
  add("ADX_14", dx.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean())
  add("Plus_DI_14", plus_di)
  add("Minus_DI_14", minus_di)
  add("Vortex_Plus", (high - low.shift(1)).abs().rolling(14).sum() / true_range.rolling(14).sum())
  add("Vortex_Minus", (low - high.shift(1)).abs().rolling(14).sum() / true_range.rolling(14).sum())
  price_position = (close - lowest14) / (highest14 - lowest14).replace(0, np.nan)
  fisher_input = (2 * price_position - 1).clip(-0.999, 0.999)
  fisher = 0.5 * np.log((1 + fisher_input) / (1 - fisher_input))
  add("Fisher_Transform", fisher.ewm(span=3, adjust=False).mean())

  # 20 volatility indicators
  bb_middle = close.rolling(20).mean()
  bb_std = close.rolling(20).std()
  bb_upper = bb_middle + 2 * bb_std
  bb_lower = bb_middle - 2 * bb_std
  add("BB_Upper", bb_upper)
  add("BB_Middle", bb_middle)
  add("BB_Lower", bb_lower)
  add("BB_Percent_B", (close - bb_lower) / (bb_upper - bb_lower))
  add("BB_Width", (bb_upper - bb_lower) / bb_middle * 100)
  keltner_mid = close.ewm(span=20, adjust=False).mean()
  add("Keltner_Upper", keltner_mid + 2 * atr14)
  add("Keltner_Lower", keltner_mid - 2 * atr14)
  donchian_upper = high.rolling(20).max()
  donchian_lower = low.rolling(20).min()
  add("Donchian_Upper", donchian_upper)
  add("Donchian_Middle", (donchian_upper + donchian_lower) / 2)
  add("Donchian_Lower", donchian_lower)
  add("ATR_14", atr14)
  add("NATR_14", atr14 / close * 100)
  add("True_Range", true_range)
  log_return = np.log(close / previous_close)
  add("Historical_Volatility_20", log_return.rolling(20).std() * np.sqrt(252) * 100)
  drawdown = (close / close.rolling(14).max() - 1) * 100
  add("Ulcer_Index_14", np.sqrt((drawdown**2).rolling(14).mean()))
  add(
      "Choppiness_14",
      100
      * np.log10(true_range.rolling(14).sum() / (high.rolling(14).max() - low.rolling(14).min()))
      / np.log10(14),
  )
  smoothed_range = (high - low).ewm(span=9, adjust=False).mean()
  add(
      "Mass_Index",
      (smoothed_range / smoothed_range.ewm(span=9, adjust=False).mean())
      .rolling(25)
      .sum(),
  )
  add(
      "Parkinson_Volatility_20",
      np.sqrt((np.log(high / low) ** 2).rolling(20).mean() / (4 * np.log(2)) * 252)
      * 100,
  )
  gk_variance = 0.5 * np.log(high / low) ** 2 - (
      2 * np.log(2) - 1
  ) * np.log(close / open_price) ** 2
  add(
      "Garman_Klass_Volatility_20",
      np.sqrt(gk_variance.rolling(20).mean().clip(lower=0) * 252) * 100,
  )
  add("Chaikin_Volatility", smoothed_range.pct_change(10) * 100)

  # 25 volume and price-volume indicators
  direction = np.sign(close.diff()).fillna(0)
  obv = (direction * volume).cumsum()
  add("OBV", obv)
  money_multiplier = (
      ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
  ).fillna(0)
  money_volume = money_multiplier * volume
  adl = money_volume.cumsum()
  add("ADL", adl)
  chaikin = adl.ewm(span=3, adjust=False).mean() - adl.ewm(span=10, adjust=False).mean()
  add("Chaikin_Oscillator", chaikin)
  add("CMF_20", money_volume.rolling(20).sum() / volume.rolling(20).sum())
  raw_money_flow = typical * volume
  positive_flow = raw_money_flow.where(typical.diff() > 0, 0).rolling(14).sum()
  negative_flow = raw_money_flow.where(typical.diff() < 0, 0).rolling(14).sum()
  add("MFI_14", 100 - 100 / (1 + positive_flow / negative_flow))
  add("Force_Index_13", (close.diff() * volume).ewm(span=13, adjust=False).mean())
  add(
      "Ease_of_Movement_14",
      (((high + low) / 2).diff() * (high - low) / (volume / 100_000_000))
      .rolling(14)
      .mean(),
  )
  add("VPT", (volume * close.pct_change()).fillna(0).cumsum())
  volume_change = volume.diff()
  daily_return = close.pct_change().fillna(0)
  add("NVI", 1000 * (1 + daily_return.where(volume_change < 0, 0)).cumprod())
  add("PVI", 1000 * (1 + daily_return.where(volume_change > 0, 0)).cumprod())
  volume_sma5 = volume.rolling(5).mean()
  volume_sma20 = volume.rolling(20).mean()
  add("Volume_SMA_5", volume_sma5)
  add("Volume_SMA_20", volume_sma20)
  add("Volume_EMA_20", volume.ewm(span=20, adjust=False).mean())
  add("Volume_SMA_Ratio_20", volume / volume_sma20)
  add("Volume_ROC_5", volume.pct_change(5) * 100)
  add("Volume_ROC_20", volume.pct_change(20) * 100)
  add("OBV_SMA_20", obv.rolling(20).mean())
  add("ADL_EMA_20", adl.ewm(span=20, adjust=False).mean())
  add("CMF_10", money_volume.rolling(10).sum() / volume.rolling(10).sum())
  positive_volume = volume.where(close.diff() > 0, 0).rolling(20).sum()
  negative_volume = volume.where(close.diff() < 0, 0).rolling(20).sum()
  add("Up_Down_Volume_Ratio_20", positive_volume / negative_volume)
  add("Price_Volume_Correlation_20", close.pct_change().rolling(20).corr(volume.pct_change()))
  add("Volume_ZScore_20", (volume - volume_sma20) / volume.rolling(20).std())
  trend_direction = np.sign(typical.diff()).replace(0, np.nan).ffill().fillna(1)
  add("Klinger_Oscillator", (volume * trend_direction).ewm(span=34, adjust=False).mean() - (volume * trend_direction).ewm(span=55, adjust=False).mean())
  add("Klinger_Signal", indicators["Klinger_Oscillator"].ewm(span=13, adjust=False).mean())
  add("Volume_Weighted_Return_20", (daily_return * volume).rolling(20).sum() / volume.rolling(20).sum())

  if len(indicators) != 100:
    raise RuntimeError(f"100개 지표 계산 오류: 현재 {len(indicators)}개입니다.")
  df = pd.concat([df, pd.DataFrame(indicators, index=df.index)], axis=1)

  trend_names = [
      name for name in indicators
      if name.startswith(("SMA_", "EMA_", "WMA_"))
      or name in [
          "DEMA_20", "TEMA_20", "HMA_20", "VWMA_20", "VWAP_20",
          "ZLEMA_20", "KAMA_10", "LSMA_20", "ALMA_20",
          "Supertrend_10_3", "Parabolic_SAR",
      ]
  ]
  momentum_names = [
      name for name in indicators
      if name.startswith(("RSI_", "MACD", "PPO", "Stoch", "Aroon_", "Vortex_"))
      or name in [
          "Williams_R", "CCI_20", "ROC_12", "Momentum_10", "TSI",
          "TSI_Signal", "CMO_14", "Ultimate_Oscillator", "ADX_14",
          "Plus_DI_14", "Minus_DI_14", "Fisher_Transform",
      ]
  ]
  volatility_names = [
      name for name in indicators
      if name.startswith(("BB_", "Keltner_", "Donchian_"))
      or name in [
          "ATR_14", "NATR_14", "True_Range", "Historical_Volatility_20",
          "Ulcer_Index_14", "Choppiness_14", "Mass_Index",
          "Parkinson_Volatility_20", "Garman_Klass_Volatility_20",
          "Chaikin_Volatility",
      ]
  ]
  volume_names = [
      name for name in indicators
      if name not in trend_names + momentum_names + volatility_names
  ]

  scores = pd.DataFrame(50.0, index=df.index, columns=indicators)

  def continuous_score(signal, scale):
    return (50 + 50 * np.tanh(signal / scale)).clip(0, 100)

  for name in trend_names:
    relative_distance = close / indicators[name].replace(0, np.nan) - 1
    scores[name] = continuous_score(relative_distance, 0.05)
  for name in momentum_names:
    values = indicators[name]
    if name.startswith(("RSI_", "Stoch")):
      scores[name] = (100 - values).clip(0, 100)
    elif name == "Williams_R":
      scores[name] = (-values).clip(0, 100)
    elif name == "CCI_20":
      scores[name] = (50 - values * 0.5).clip(0, 100)
    elif name == "Ultimate_Oscillator":
      scores[name] = (100 - values).clip(0, 100)
    elif name == "ADX_14":
      direction = np.sign(
          indicators["Plus_DI_14"] - indicators["Minus_DI_14"]
      )
      scores[name] = continuous_score(
          direction * (values - 15).clip(lower=0), 40
      )
    elif name in ["Aroon_Up", "Plus_DI_14", "Vortex_Plus"]:
      pair = {
          "Aroon_Up": "Aroon_Down",
          "Plus_DI_14": "Minus_DI_14",
          "Vortex_Plus": "Vortex_Minus",
      }[name]
      difference = values - indicators[pair]
      scale = 50 if name == "Aroon_Up" else (15 if name == "Plus_DI_14" else 0.2)
      scores[name] = continuous_score(difference, scale)
    elif name in ["Aroon_Down", "Minus_DI_14", "Vortex_Minus"]:
      pair = {
          "Aroon_Down": "Aroon_Up",
          "Minus_DI_14": "Plus_DI_14",
          "Vortex_Minus": "Vortex_Plus",
      }[name]
      difference = indicators[pair] - values
      scale = 50 if name == "Aroon_Down" else (15 if name == "Minus_DI_14" else 0.2)
      scores[name] = continuous_score(difference, scale)
    elif name == "Aroon_Osc":
      scores[name] = (50 + values * 0.5).clip(0, 100)
    elif name == "Fisher_Transform":
      scores[name] = continuous_score(values, 1)
    elif name.startswith(("MACD",)):
      scores[name] = continuous_score(values / close * 100, 2)
    elif name.startswith(("PPO",)):
      scores[name] = continuous_score(values, 3)
    elif name in ["TSI", "TSI_Signal", "CMO_14"]:
      scores[name] = continuous_score(values, 25)
    elif name == "ROC_12":
      scores[name] = continuous_score(values, 5)
    elif name == "Momentum_10":
      scores[name] = continuous_score(values / close * 100, 5)
    else:
      scores[name] = continuous_score(values, 25)

  channel_groups = {
      "BB": ("BB_Lower", "BB_Upper"),
      "Donchian": ("Donchian_Lower", "Donchian_Upper"),
      "Keltner": ("Keltner_Lower", "Keltner_Upper"),
  }
  for lower_name, upper_name in channel_groups.values():
    lower = indicators[lower_name]
    upper = indicators[upper_name]
    position = (close - lower) / (upper - lower).replace(0, np.nan)
    channel_score = (100 - 100 * position).clip(0, 100)
    scores[lower_name] = channel_score
    scores[upper_name] = channel_score
    middle_name = next(
        (
            candidate
            for candidate in [
                f"{lower_name.removesuffix('_Lower')}_Middle",
            ]
            if candidate in indicators
        ),
        None,
    )
    if middle_name:
      scores[middle_name] = channel_score

  for name in volatility_names:
    values = indicators[name]
    if name == "BB_Percent_B":
      scores[name] = (100 - 100 * values).clip(0, 100)

  five_day_return = close.pct_change(5)
  for name in volume_names:
    values = indicators[name]
    if name in ["CMF_20", "CMF_10"]:
      scores[name] = continuous_score(values, 0.2)
    elif name == "MFI_14":
      scores[name] = (100 - values).clip(0, 100)
    elif name == "Up_Down_Volume_Ratio_20":
      scores[name] = 50 + 50 * np.tanh(np.log(values.replace(0, np.nan)))
    elif name == "Volume_SMA_Ratio_20":
      scores[name] = continuous_score(
          np.sign(five_day_return) * np.log(values.replace(0, np.nan)), 0.25
      )
    elif name in ["Volume_SMA_5", "Volume_SMA_20", "Volume_EMA_20"]:
      baseline = volume.rolling(60, min_periods=20).mean()
      ratio = values / baseline.replace(0, np.nan)
      scores[name] = continuous_score(
          np.sign(five_day_return) * np.log(ratio.replace(0, np.nan)), 0.25
      )
    elif name in ["Volume_ROC_5", "Volume_ROC_20", "Volume_ZScore_20"]:
      scale = 50 if name.startswith("Volume_ROC") else 2
      scores[name] = continuous_score(
          np.sign(five_day_return) * values, scale
      )
    elif name == "Price_Volume_Correlation_20":
      scores[name] = continuous_score(values * np.sign(five_day_return), 0.5)
    elif name == "Volume_Weighted_Return_20":
      scores[name] = continuous_score(values, 0.02)
    elif name == "Volume_Price_Trend_20":
      volume_baseline = volume.rolling(20).sum().replace(0, np.nan)
      scores[name] = continuous_score(values / volume_baseline, 0.02)
    elif name in ["OBV", "ADL", "VPT", "NVI", "PVI", "OBV_SMA_20", "ADL_EMA_20"]:
      slope = values.diff(5)
      scale = slope.rolling(20).std().replace(0, np.nan)
      scores[name] = continuous_score(slope / scale, 1)
    elif name in ["Klinger_Oscillator", "Klinger_Signal", "Chaikin_Oscillator", "Force_Index_13", "Ease_of_Movement_14"]:
      scale = values.rolling(20).std().replace(0, np.nan)
      scores[name] = continuous_score(values / scale, 1)

  group_names = {
      "추세": trend_names,
      "모멘텀": momentum_names,
      "변동성": volatility_names,
      "거래량": volume_names,
  }
  group_weights = {"추세": 0.35, "모멘텀": 0.25, "변동성": 0.25, "거래량": 0.15}
  group_scores = {
      group: scores[names].mean(axis=1) for group, names in group_names.items()
  }
  df["Indicator_Score"] = sum(
      group_scores[group] * group_weights[group] for group in group_names
  )
  return df, list(indicators), group_scores, scores


FRED_SERIES = {
    "DFF": "연방기금금리",
    "DGS2": "미국 2년물 금리",
    "DGS10": "미국 10년물 금리",
    "DCOILWTICO": "WTI 원유 가격",
    "CPIAUCSL": "소비자물가지수 (CPI)",
    "UNRATE": "실업률",
    "ICSA": "신규 실업수당 청구",
    "PAYEMS": "비농업 고용자 수",
    "GDPC1": "실질 GDP",
    "DTWEXBGS": "미국 달러 지수",
}


@st.cache_data(ttl=3600)
def load_fred_series(series_id):
  """FRED public CSV endpoint에서 경제 시계열 하나를 내려받는다."""
  if series_id not in FRED_SERIES:
    raise ValueError(f"지원하지 않는 FRED 지표입니다: {series_id}")
  url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
  request = urllib.request.Request(
      url, headers={"User-Agent": "Mozilla/5.0 market-indicator-dashboard"}
  )
  with urllib.request.urlopen(request, timeout=15) as response:
    csv_content = response.read()
  frame = pd.read_csv(io.BytesIO(csv_content), na_values=["."])
  if "observation_date" not in frame or series_id not in frame:
    raise ValueError(f"FRED 응답 형식이 올바르지 않습니다: {series_id}")
  frame["observation_date"] = pd.to_datetime(
      frame["observation_date"], errors="coerce"
  )
  frame[series_id] = pd.to_numeric(frame[series_id], errors="coerce")
  series = frame.dropna(subset=["observation_date", series_id]).set_index(
      "observation_date"
  )[series_id]
  if series.empty:
    raise ValueError(f"FRED에서 유효한 관측값이 없습니다: {series_id}")
  return series.sort_index()


def load_macro_data():
  """거시 시계열을 읽고 실패한 출처를 호출자에게 돌려준다."""
  series_data = {}
  errors = []
  for series_id in FRED_SERIES:
    try:
      series_data[series_id] = load_fred_series(series_id)
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
        pd.errors.ParserError,
    ) as error:
      errors.append(f"{FRED_SERIES[series_id]} ({series_id}): {error}")
  return series_data, errors


def calculate_macro_score(series_data):
  """투명한 변화 기준으로 거시 점수와 상세 표 데이터를 계산한다."""

  def value_three_months_ago(series):
    cutoff = series.index[-1] - pd.DateOffset(months=3)
    previous_values = series.loc[:cutoff]
    if previous_values.empty:
      raise ValueError("거시 데이터의 과거 관측값이 부족합니다.")
    return float(previous_values.iloc[-1])

  def direction_score(change, scale, lower_is_better=True):
    signed_change = -change if lower_is_better else change
    return float(50 + 50 * np.tanh(signed_change / scale))

  details = []
  indicator_scores = {}

  def add_detail(name, value, unit, comparison, observed_at, score):
    indicator_scores[name] = score
    details.append(
        {
            "지표": name,
            "최근 관측값": f"{value:,.2f} {unit}".strip(),
            "최근 변화": comparison,
            "관측일": observed_at.strftime("%Y-%m-%d"),
            "거시 신호 점수": round(score, 1),
        }
    )

  rate_scores = []
  for series_id in ["DFF", "DGS2", "DGS10"]:
    series = series_data[series_id]
    current = float(series.iloc[-1])
    change = current - value_three_months_ago(series)
    score = direction_score(change, 0.25)
    rate_scores.append(score)
    add_detail(
        FRED_SERIES[series_id],
        current,
        "%",
        f"3개월 {change:+.2f}%p",
        series.index[-1],
        score,
    )

  two_year = series_data["DGS2"]
  ten_year = series_data["DGS10"]
  spread = float(ten_year.iloc[-1] - two_year.iloc[-1])
  spread_score = direction_score(spread, 0.5, lower_is_better=False)
  rate_scores.append(spread_score)
  add_detail(
      "미국 10년물-2년물 금리차",
      spread,
      "%p",
      "수익률곡선 역전" if spread < 0 else "수익률곡선 정상",
      min(ten_year.index[-1], two_year.index[-1]),
      spread_score,
  )

  oil = series_data["DCOILWTICO"]
  oil_previous = value_three_months_ago(oil)
  oil_change_pct = (float(oil.iloc[-1]) / oil_previous - 1) * 100
  oil_score = direction_score(oil_change_pct, 10.0)
  add_detail(
      FRED_SERIES["DCOILWTICO"],
      float(oil.iloc[-1]),
      "USD/배럴",
      f"3개월 {oil_change_pct:+.1f}%",
      oil.index[-1],
      oil_score,
  )

  cpi = series_data["CPIAUCSL"]
  inflation = cpi.pct_change(12) * 100
  inflation = inflation.dropna()
  inflation_previous = value_three_months_ago(inflation)
  inflation_change = float(inflation.iloc[-1]) - inflation_previous
  inflation_score = direction_score(inflation_change, 0.3)
  add_detail(
      "CPI 전년 대비 상승률",
      float(inflation.iloc[-1]),
      "%",
      f"3개월 {inflation_change:+.2f}%p",
      inflation.index[-1],
      inflation_score,
  )

  unemployment = series_data["UNRATE"]
  unemployment_change = float(unemployment.iloc[-1]) - value_three_months_ago(
      unemployment
  )
  unemployment_score = direction_score(unemployment_change, 0.2)
  add_detail(
      FRED_SERIES["UNRATE"],
      float(unemployment.iloc[-1]),
      "%",
      f"3개월 {unemployment_change:+.2f}%p",
      unemployment.index[-1],
      unemployment_score,
  )

  claims = series_data["ICSA"].rolling(4).mean().dropna()
  if len(claims) < 14:
    raise ValueError("신규 실업수당 청구 데이터의 과거 관측값이 부족합니다.")
  claims_change_pct = (float(claims.iloc[-1]) / float(claims.iloc[-14]) - 1) * 100
  claims_score = direction_score(claims_change_pct, 10.0)
  add_detail(
      "신규 실업수당 청구 (4주 평균)",
      float(claims.iloc[-1]),
      "건",
      f"약 3개월 {claims_change_pct:+.1f}%",
      claims.index[-1],
      claims_score,
  )

  payrolls = series_data["PAYEMS"]
  if len(payrolls) < 4:
    raise ValueError("비농업 고용 데이터의 과거 관측값이 부족합니다.")
  payroll_change = float(payrolls.iloc[-1]) - float(payrolls.iloc[-4])
  payroll_score = float(50 + 50 * np.tanh((payroll_change - 300) / 300))
  add_detail(
      FRED_SERIES["PAYEMS"],
      float(payrolls.iloc[-1]),
      "천 명",
      f"3개월 순증 {payroll_change:+,.0f}천 명",
      payrolls.index[-1],
      payroll_score,
  )

  gdp_growth = series_data["GDPC1"].pct_change(4).dropna() * 100
  if len(gdp_growth) < 2:
    raise ValueError("실질 GDP 성장률의 과거 관측값이 부족합니다.")
  gdp_growth_change = float(gdp_growth.iloc[-1]) - float(gdp_growth.iloc[-2])
  gdp_score = direction_score(gdp_growth_change, 0.5, lower_is_better=False)
  add_detail(
      "실질 GDP 전년 대비 성장률",
      float(gdp_growth.iloc[-1]),
      "%",
      f"직전 분기 대비 {gdp_growth_change:+.2f}%p",
      gdp_growth.index[-1],
      gdp_score,
  )

  dollar = series_data["DTWEXBGS"]
  dollar_change_pct = (
      float(dollar.iloc[-1]) / value_three_months_ago(dollar) - 1
  ) * 100
  dollar_score = direction_score(dollar_change_pct, 3.0)
  add_detail(
      FRED_SERIES["DTWEXBGS"],
      float(dollar.iloc[-1]),
      "지수",
      f"3개월 {dollar_change_pct:+.1f}%",
      dollar.index[-1],
      dollar_score,
  )

  groups = {
      "금리": rate_scores,
      "물가·유가": [inflation_score, oil_score],
      "고용": [unemployment_score, claims_score, payroll_score],
      "성장": [gdp_score],
      "달러": [dollar_score],
  }
  group_scores = {
      name: float(np.mean(scores)) for name, scores in groups.items()
  }
  macro_score = float(np.mean(list(group_scores.values())))
  return macro_score, group_scores, pd.DataFrame(details)


def styled_data_table(frame):
  return frame.style.set_properties(
      **{
          "background-color": "#111a2b",
          "color": "#e6edf7",
          "border-color": "#263248",
      }
  ).set_table_styles(
      [
          {
              "selector": "th",
              "props": [
                  ("background-color", "#182439"),
                  ("color", "#e6edf7"),
                  ("border-color", "#263248"),
              ],
          }
      ]
  )


# 데이터 실행
res = None
ticker_is_valid = bool(re.fullmatch(r"[A-Z0-9^.=+-]+", ticker))
if not ticker:
  st.error("종목 코드를 입력해 주세요. 예: AAPL, TQQQ, BRK-B")
elif not ticker_is_valid:
  st.error(
      "종목 코드에 사용할 수 없는 문자가 있습니다. 영문·숫자와 ., -, ^, =만 "
      "입력해 주세요. 입력값 뒤에 설명 문구가 붙지 않았는지 확인해 주세요."
  )
else:
  with st.spinner(f"'{ticker}' 실제 시장 데이터를 불러오는 중..."):
    res = load_real_stock_data(ticker, period)

if res is None:
  render_analysis_history(
      history_panel, st.session_state["analysis_history"]
  )
  if ticker and ticker_is_valid:
    st.error(
        f"'{ticker}'의 Yahoo Finance 일봉 데이터가 비어 있거나 분석에 필요한 "
        "60거래일보다 적습니다. 티커와 조회 기간을 확인해 주세요. "
        "일부 거래소 티커는 접미사(예: .KS)가 필요할 수 있습니다."
    )
else:
  df, indicator_names, group_scores, indicator_scores = res
  current_analysis = (ticker, period)
  force_history_record = st.session_state.pop("force_history_record", False)
  if (
      current_analysis
      != st.session_state.get("last_successful_analysis")
      or force_history_record
  ):
    updated_history = record_analysis_history(
        st.session_state["analysis_history"], ticker, period
    )
    st.session_state["analysis_history"] = updated_history
    st.session_state["last_successful_analysis"] = current_analysis
  render_analysis_history(
      history_panel, st.session_state["analysis_history"]
  )

  with st.spinner("FRED에서 미국 금리·유가·경제지표를 불러오는 중..."):
    macro_series, macro_errors = load_macro_data()
  macro_result = None
  if macro_errors:
    st.error(
        "FRED 거시 데이터 일부를 불러오지 못해 기술·거시 통합 점수는 계산할 수 "
        "없습니다. 잠시 후 다시 시도해 주세요."
    )
    with st.expander("데이터 오류 상세"):
      for error in macro_errors:
        st.write(error)
  else:
    try:
      macro_result = calculate_macro_score(macro_series)
    except ValueError as error:
      st.error(f"거시 지표 점수를 계산할 수 없습니다: {error}")

  latest = df.iloc[-1]
  prev = df.iloc[-2]

  ma20 = latest["SMA_20"]
  ma60 = latest["SMA_60"]
  is_bullish = ma20 >= ma60
  trend_guard_block = use_trend_guard and not is_bullish
  trend_score = group_scores["추세"].iloc[-1]
  mom_score = group_scores["모멘텀"].iloc[-1]
  vol_score = group_scores["변동성"].iloc[-1]
  volume_score = group_scores["거래량"].iloc[-1]
  technical_score = float(latest["Indicator_Score"])
  macro_score = macro_result[0] if macro_result else None
  macro_group_scores = macro_result[1] if macro_result else None
  macro_details = macro_result[2] if macro_result else None
  if trend_guard_block:
    technical_score = 0
  final_score = (
      0.0
      if trend_guard_block
      else (
          technical_score * 0.70 + macro_score * 0.30
          if macro_score is not None
          else None
      )
  )

  # --- 핵심 지표 요약 ---
  col1, col2, col3, col4, col5 = st.columns(5)
  chg_pct = ((latest["Close"] - prev["Close"]) / prev["Close"]) * 100

  col1.metric(
      "현재 종가", value=f"${latest['Close']:.2f}", delta=f"{chg_pct:+.2f}%"
  )
  col2.metric(
      "이동평균 추세", value="정배열" if is_bullish else "역배열"
  )
  col3.metric("기술 점수 · 70%", value=f"{technical_score:.1f} / 100")
  col4.metric(
      "거시 점수 · 30%",
      f"{macro_score:.1f} / 100" if macro_score is not None else "데이터 없음",
  )
  col5.metric(
      "통합 참고 점수",
      f"{final_score:.1f} / 100" if final_score is not None else "계산 대기",
  )

  if trend_guard_block:
    status_text = "안전 필터 작동"
    status_detail = "20일 이동평균이 60일 이동평균보다 낮아 점수를 0점 처리했습니다."
  elif final_score is None:
    status_text = "통합 점수 대기"
    status_detail = "거시 경제 데이터를 불러오지 못해 기술·거시 통합 점수를 표시하지 않습니다."
  elif final_score >= 70:
    status_text = "긍정 신호"
    status_detail = "기술지표 70%와 미국 거시지표 30%를 합산한 참고 점수입니다."
  else:
    status_text = "관망 구간"
    status_detail = "기술·거시 지표를 합산한 기준에서 강한 긍정 신호가 확인되지 않습니다."

  with st.container(border=True):
    status_col, detail_col = st.columns([1, 4])
    status_col.markdown("**현재 신호**")
    status_col.markdown(f"### {status_text}")
    detail_col.markdown("**분석 요약**")
    detail_col.write(status_detail)
    detail_col.caption(
        "통합 점수 = 기술 점수 70% + 거시 점수 30%. "
        "점수는 매수 확률이나 투자 권유가 아닙니다."
    )

  st.subheader("미국 거시경제 환경")
  st.caption(
      "금리·물가·유가·고용·성장·달러의 최근 변화로 만든 규칙 기반 점수입니다. "
      "각 지표의 관측일과 원값을 함께 표시합니다."
  )
  if macro_details is not None:
    macro_cols = st.columns(5)
    for column, (name, value) in zip(
        macro_cols, macro_group_scores.items(), strict=True
    ):
      column.metric(name, f"{value:.1f} / 100")
    st.dataframe(
        styled_data_table(macro_details),
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("거시 점수 산정 방식"):
      st.markdown(
          """
          - 금리(연방기금금리·미국 2년물·10년물)는 최근 3개월 하락 시 우호, 상승 시 부담으로 봅니다. 금리차가 역전되면 금리 그룹에 낮은 점수를 줍니다.
          - CPI 상승률이 둔화하고 WTI 유가가 하락하면 물가·유가 그룹에 우호적으로 반영합니다.
          - 실업률과 신규 실업수당 청구가 증가하면 고용 그룹에 부담, 비농업 고용자 수가 3개월간 30만 명 이상 증가하면 우호적으로 반영합니다.
          - 실질 GDP 성장률 개선과 달러 약세는 각각 성장·달러 그룹에 우호적으로 반영합니다.
                  - 기술지표와 거시 점수는 기준과의 거리·변화 크기에 따라 연속형 0~100점으로 계산합니다. 금리·물가/유가·고용·성장·달러의 5개 거시 그룹은 동일 비중으로 평균하고, 통합 점수에서는 거시 점수가 30%를 차지합니다.
                  - 50점은 대체로 중립, 50점보다 높으면 설정한 규칙에서 상대적으로 우호적, 낮으면 부담으로 해석합니다. 소수점은 계산 정밀도이며 확률이나 예측 정확도를 의미하지 않습니다.
          """
      )
    st.caption(
        "출처: "
        "[FRED 공개 데이터](https://fred.stlouisfed.org/) · "
        "경제지표는 발표 주기와 수정 시점이 서로 다르며, 규칙 기반 점수는 "
        "경기·주가 방향을 확정적으로 예측하지 않습니다."
    )

  st.markdown("---")

  # --- 일별 캔들스틱 및 지표 차트 ---
  st.subheader("가격")
  st.caption("일봉 캔들 · 20/60일 이동평균 · 볼린저 밴드 · 거래량")

  fig = make_subplots(
      rows=2,
      cols=1,
      shared_xaxes=True,
      vertical_spacing=0.03,
      row_heights=[0.75, 0.25],
  )

  # 캔들스틱 차트 추가 (실제 일별 데이터)
  fig.add_trace(
      go.Candlestick(
          x=df.index,
          open=df["Open"],
          high=df["High"],
          low=df["Low"],
          close=df["Close"],
          name="가격",
          increasing_line_color="#35c79a",
          decreasing_line_color="#ef6675",
      ),
      row=1,
      col=1,
  )

  # 이동평균선 추가
  fig.add_trace(
      go.Scatter(
          x=df.index,
          y=df["SMA_20"],
          name="20일선",
          line=dict(color="#f3bd55", width=1.5),
      ),
      row=1,
      col=1,
  )
  fig.add_trace(
      go.Scatter(
          x=df.index,
          y=df["SMA_60"],
          name="60일선",
          line=dict(color="#55c8d8", width=1.7),
      ),
      row=1,
      col=1,
  )

  # 볼린저 밴드
  fig.add_trace(
      go.Scatter(
          x=df.index,
          y=df["BB_Upper"],
          name="볼린저 상단",
          line=dict(color="rgba(143,160,183,0.52)", dash="dot", width=1),
      ),
      row=1,
      col=1,
  )
  fig.add_trace(
      go.Scatter(
          x=df.index,
          y=df["BB_Lower"],
          name="볼린저 하단",
          line=dict(color="rgba(143,160,183,0.52)", dash="dot", width=1),
          fill="tonexty",
          fillcolor="rgba(143,160,183,0.06)",
      ),
      row=1,
      col=1,
  )

  # 거래량 바 차트
  bar_colors = [
      "#35c79a" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#ef6675"
      for i in range(len(df))
  ]
  fig.add_trace(
      go.Bar(
          x=df.index,
          y=df["Volume"],
          name="거래량",
          marker_color=bar_colors,
          showlegend=False,
      ),
      row=2,
      col=1,
  )

  fig.update_layout(
      template="plotly_dark",
      height=660,
      paper_bgcolor="rgba(0,0,0,0)",
      plot_bgcolor="rgba(0,0,0,0)",
      font=dict(color="#c5d0df", family="sans-serif", size=12),
      margin=dict(l=20, r=20, t=42, b=18),
      xaxis_rangeslider_visible=False,
      hovermode="x unified",
      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
  )
  fig.update_xaxes(
      showgrid=False,
      linecolor="#263248",
      zerolinecolor="#263248",
      rangeslider_visible=False,
  )
  fig.update_yaxes(
      showgrid=True,
      gridcolor="rgba(145,160,183,0.12)",
      linecolor="#263248",
      zerolinecolor="#263248",
  )
  with st.container(border=True):
    st.plotly_chart(fig, use_container_width=True)

  # --- 하단 카테고리별 점수 ---
  st.subheader("지표 그룹별 요약")
  st.caption(
      "점수는 0~100 연속형 규칙 기반 참고값입니다. 50은 대체로 중립이며, "
      "소수점은 매수 확률이나 예측 정밀도를 뜻하지 않습니다. "
      "지표별 원래 계산값은 아래 상세표에서 확인할 수 있습니다."
  )
  c1, c2, c3, c4 = st.columns(4)
  c1.metric("추세", f"{trend_score:.1f} / 100")
  c2.metric("모멘텀", f"{mom_score:.1f} / 100")
  c3.metric("변동성", f"{vol_score:.1f} / 100")
  c4.metric("거래량", f"{volume_score:.1f} / 100")

  with st.expander("100개 원 지표값과 환산 신호 점수"):
    st.dataframe(
        styled_data_table(
            pd.DataFrame(
                {
                    "지표": indicator_names,
                    "원 지표값": [latest[name] for name in indicator_names],
                    "환산 신호 점수 (0~100)": [
                        indicator_scores[name].iloc[-1]
                        for name in indicator_names
                    ],
                }
            )
        ),
        use_container_width=True,
        hide_index=True,
    )
"""
US Stock Trading Decision System
Technical Analysis based trading signals
Version 2.0 - Added ATR, Position Sizing, Risk Management
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def get_stock_data(symbol, period="1y"):
    """获取股票数据"""
    stock = yf.Ticker(symbol)
    df = stock.history(period=period)
    if df.empty:
        return None
    df['Symbol'] = symbol
    return df


def calculate_rsi(prices, period=14):
    """计算RSI指标"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """计算MACD指标"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_ma(prices, periods=[5, 20, 60]):
    """计算移动平均线"""
    ma_dict = {}
    for period in periods:
        ma_dict[f'MA{period}'] = prices.rolling(window=period).mean()
    return ma_dict


def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """计算布林带"""
    ma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = ma + (std * std_dev)
    lower_band = ma - (std * std_dev)
    return upper_band, ma, lower_band


def calculate_atr(df, period=14):
    """计算ATR (Average True Range) 波动率指标"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr


def calculate_volume_ma(volume, period=20):
    """计算成交量均线"""
    return volume.rolling(window=period).mean()


def analyze_trend(prices, ma5, ma20, ma60):
    """分析趋势"""
    if ma5 > ma20 > ma60:
        return "强势上涨"
    elif ma5 > ma20:
        return "上涨趋势"
    elif ma5 < ma20 < ma60:
        return "强势下跌"
    elif ma5 < ma20:
        return "下跌趋势"
    else:
        return "横盘整理"


def calculate_position_size(atr, price, account_size=100000, risk_percent=2):
    """计算仓位大小"""
    risk_amount = account_size * (risk_percent / 100)
    position_size = risk_amount / atr
    return int(position_size)


def generate_signal(df, symbol):
    """生成交易信号"""
    close = df['Close']
    volume = df['Volume']
    high = df['High']
    low = df['Low']
    
    # 计算各项指标
    rsi = calculate_rsi(close)
    macd_line, signal_line, histogram = calculate_macd(close)
    ma_dict = calculate_ma(close)
    ma5, ma20, ma60 = ma_dict['MA5'], ma_dict['MA20'], ma_dict['MA60']
    upper_band, middle_band, lower_band = calculate_bollinger_bands(close)
    vol_ma = calculate_volume_ma(volume)
    atr = calculate_atr(df)
    
    # 最新数据
    latest = df.iloc[-1]
    latest_rsi = rsi.iloc[-1]
    latest_macd = macd_line.iloc[-1]
    latest_signal = signal_line.iloc[-1]
    latest_hist = histogram.iloc[-1]
    latest_ma5 = ma5.iloc[-1]
    latest_ma20 = ma20.iloc[-1]
    latest_ma60 = ma60.iloc[-1]
    latest_vol = latest['Volume']
    latest_close = latest['Close']
    latest_atr = atr.iloc[-1]
    
    # 成交量判断
    vol_ratio = latest_vol / vol_ma.iloc[-1] if vol_ma.iloc[-1] > 0 else 1
    
    # 趋势判断
    trend = analyze_trend(close, latest_ma5, latest_ma20, latest_ma60)
    
    # 买卖信号评分 (0-100)
    buy_score = 0
    sell_score = 0
    
    # RSI评分
    if latest_rsi < 30:
        buy_score += 25
    elif latest_rsi < 40:
        buy_score += 15
    elif latest_rsi > 70:
        sell_score += 25
    elif latest_rsi > 60:
        sell_score += 15
    
    # MACD评分
    if latest_hist > 0:  # 金叉
        buy_score += 20
    else:  # 死叉
        sell_score += 20
    
    # 均线评分
    if latest_ma5 > latest_ma20:
        buy_score += 15
    else:
        sell_score += 15
    
    # 成交量评分
    if vol_ratio > 1.5:
        if latest_close > close.iloc[-2]:  # 上涨放量
            buy_score += 15
        else:  # 下跌放量
            sell_score += 15
    elif vol_ratio < 0.5:
        buy_score -= 5
        sell_score -= 5
    
    # 趋势评分
    if trend == "强势上涨":
        buy_score += 15
    elif trend == "强势下跌":
        sell_score += 15
    elif trend == "上涨趋势":
        buy_score += 10
    elif trend == "下跌趋势":
        sell_score += 10
    
    # 布林带评分
    if latest_close < lower_band.iloc[-1]:
        buy_score += 10
    elif latest_close > upper_band.iloc[-1]:
        sell_score += 10
    
    # 计算仓位
    position_size = calculate_position_size(latest_atr, latest_close)
    
    # 生成决策
    if buy_score >= 60:
        decision = "强烈买入"
    elif buy_score >= 40:
        decision = "建议买入"
    elif sell_score >= 60:
        decision = "强烈卖出"
    elif sell_score >= 40:
        decision = "建议卖出"
    else:
        decision = "观望"
    
    # 风险评估
    risk_level = "低"
    risk_warning = ""
    if latest_rsi > 70 or latest_rsi < 30:
        risk_level = "高"
        risk_warning = "RSI超买/超卖区域，注意风险"
    elif atr.iloc[-1] / latest_close > 0.05:  # ATR波动>5%
        risk_level = "中"
        risk_warning = "波动较大，建议轻仓"
    
    return {
        "symbol": symbol,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "latest_price": round(latest_close, 2),
        "latest_volume": int(latest_vol),
        "atr": round(latest_atr, 2),
        "atr_percent": round(latest_atr / latest_close * 100, 2),
        "rsi": round(latest_rsi, 2),
        "macd": round(latest_macd, 2),
        "macd_signal": round(latest_signal, 2),
        "ma5": round(latest_ma5, 2),
        "ma20": round(latest_ma20, 2),
        "ma60": round(latest_ma60, 2),
        "trend": trend,
        "volume_ratio": round(vol_ratio, 2),
        "buy_score": buy_score,
        "sell_score": sell_score,
        "decision": decision,
        "position_size": position_size,
        "risk_level": risk_level,
        "risk_warning": risk_warning
    }


def print_report(data):
    """打印分析报告"""
    print(f"\n{'='*60}")
    print(f"📊 股票分析报告: {data['symbol']} ({data['date']})")
    print(f"{'='*60}")
    print(f"💰 当前价格: ${data['latest_price']}")
    print(f"📈 成交量: {data['latest_volume']:,} (量比: {data['volume_ratio']})")
    print(f"📊 ATR波动: {data['atr']} ({data['atr_percent']}%)")
    print(f"\n📊 技术指标:")
    print(f"  RSI(14): {data['rsi']}")
    print(f"  MACD: {data['macd']} (信号线: {data['macd_signal']})")
    print(f"  MA5: {data['ma5']}, MA20: {data['ma20']}, MA60: {data['ma60']}")
    print(f"  趋势: {data['trend']}")
    print(f"\n🎯 决策评分:")
    print(f"  买入评分: {data['buy_score']}/100")
    print(f"  卖出评分: {data['sell_score']}/100")
    print(f"\n💡 最终决策: {data['decision']}")
    print(f"\n📊 仓位建议:")
    print(f"  建议仓位: {data['position_size']} 股 (风险偏好2%)")
    print(f"  风险等级: {data['risk_level']}")
    if data['risk_warning']:
        print(f"  ⚠️ 风险提示: {data['risk_warning']}")
    print(f"{'='*60}\n")


def analyze_multiple(symbols):
    """批量分析多只股票"""
    results = []
    for symbol in symbols:
        print(f"📥 正在分析 {symbol}...")
        df = get_stock_data(symbol)
        if df is not None:
            result = generate_signal(df, symbol)
            results.append(result)
            print_report(result)
        else:
            print(f"❌ 无法获取 {symbol} 的数据")
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python trading_system.py <stock_symbol> [symbol2] ...")
        print("Example: python trading_system.py AAPL TSLA MSFT")
        print("\n分析默认股票列表: AAPL, TSLA, MSFT, GOOGL, NVDA, META")
        symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "NVDA", "META"]
        analyze_multiple(symbols)
    else:
        symbols = sys.argv[1:]
        analyze_multiple(symbols)

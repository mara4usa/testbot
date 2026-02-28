"""
美股交易决策系统 v1.2
输入：股票代码（如 AAPL, TSLA, NVDA）
输出：日K级别的买卖决策
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sys
import time


def get_stock_data(symbol, period="1y", max_retries=5, retry_delay=10):
    """获取股票历史数据 - 使用yfinance，带重试机制"""
    for attempt in range(max_retries):
        try:
            print(f"  尝试 {attempt + 1}/{max_retries}...")
            stock = yf.Ticker(symbol)
            df = stock.history(period=period)
            if df is not None and not df.empty:
                return df
            print(f"  返回数据为空，{retry_delay}秒后重试...")
        except Exception as e:
            print(f"  错误: {e}，{retry_delay}秒后重试...")
        
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    
    return None


def calculate_indicators(df):
    """计算技术指标"""
    # RSI (14)
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp12 = df['Close'].ewm(span=12, adjust=False).mean()
    exp26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal']
    
    # MA
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # Bollinger Bands
    df['BB_middle'] = df['Close'].rolling(window=20).mean()
    df['BB_std'] = df['Close'].rolling(window=20).std()
    df['BB_upper'] = df['BB_middle'] + 2 * df['BB_std']
    df['BB_lower'] = df['BB_middle'] - 2 * df['BB_std']
    
    # Volume MA
    df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
    
    return df


def analyze_signals(df):
    """分析买卖信号"""
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # MACD交叉判断
    macd_cross = "NONE"
    if prev['MACD'] <= prev['Signal'] and latest['MACD'] > latest['Signal']:
        macd_cross = "GOLDEN"
    elif prev['MACD'] >= prev['Signal'] and latest['MACD'] < latest['Signal']:
        macd_cross = "DEAD"
    
    # 均线排列
    ma_arrange = "NEUTRAL"
    if latest['MA5'] > latest['MA20'] > latest['MA60']:
        ma_arrange = "BULL"
    elif latest['MA5'] < latest['MA20'] < latest['MA60']:
        ma_arrange = "BEAR"
    
    signals = {
        "RSI": latest['RSI'],
        "MACD": latest['MACD'],
        "MACD_Signal": latest['Signal'],
        "MACD_Hist": latest['MACD_Hist'],
        "MACD_Cross": macd_cross,
        "MA5": latest['MA5'],
        "MA20": latest['MA20'],
        "MA60": latest['MA60'],
        "MA_Arrange": ma_arrange,
        "BB_position": (latest['Close'] - latest['BB_lower']) / (latest['BB_upper'] - latest['BB_lower']) if latest['BB_upper'] != latest['BB_lower'] else 0.5,
        "Volume": latest['Volume'],
        "Volume_Ratio": latest['Volume'] / latest['Volume_MA20'] if latest['Volume_MA20'] > 0 else 1,
        "Price_Change": (latest['Close'] - latest['Open']) / latest['Open'] * 100
    }
    
    return signals


def make_decision(signals):
    """生成交易决策"""
    score = 0
    reasons = []
    
    # RSI (权重: 2)
    if pd.isna(signals['RSI']):
        pass
    elif signals['RSI'] < 30:
        score += 2
        reasons.append(f"RSI超卖({signals['RSI']:.1f})")
    elif signals['RSI'] > 70:
        score -= 2
        reasons.append(f"RSI超买({signals['RSI']:.1f})")
    
    # MACD (权重: 2)
    if signals['MACD_Cross'] == "GOLDEN":
        score += 2
        reasons.append("MACD金叉")
    elif signals['MACD_Cross'] == "DEAD":
        score -= 2
        reasons.append("MACD死叉")
    
    if signals['MACD'] > 0:
        score += 1
        reasons.append("MACD零轴上方")
    
    # MA (权重: 2)
    if signals['MA_Arrange'] == "BULL":
        score += 2
        reasons.append("均线多头排列")
    elif signals['MA_Arrange'] == "BEAR":
        score -= 2
        reasons.append("均线空头排列")
    
    # Volume (权重: 1)
    if signals['Volume_Ratio'] > 1.5 and signals['Price_Change'] > 2:
        score += 1
        reasons.append("放量上涨")
    elif signals['Volume_Ratio'] > 1.5 and signals['Price_Change'] < -2:
        score -= 1
        reasons.append("放量下跌")
    
    # Bollinger Bands (权重: 1)
    if signals['BB_position'] < 0.2:
        score += 1
        reasons.append("布林带下轨")
    elif signals['BB_position'] > 0.8:
        score -= 1
        reasons.append("布林带上轨")
    
    # 决策
    if score >= 3:
        decision = "🟢 强烈买入"
    elif score >= 1:
        decision = "🟡 建议买入"
    elif score <= -3:
        decision = "🔴 强烈卖出"
    elif score <= -1:
        decision = "🟠 建议卖出"
    else:
        decision = "⚪ 观望"
    
    return decision, score, reasons


def trade_signal(symbol):
    """主函数：输入股票代码，返回交易决策"""
    print(f"📊 正在获取 {symbol} 数据（请耐心等待，可能需要多次重试）...")
    
    # 获取数据
    df = get_stock_data(symbol, max_retries=5, retry_delay=10)
    
    if df is None or df.empty:
        return {"error": f"无法获取 {symbol} 的数据，请稍后再试"}
    
    print(f"✅ 成功获取 {len(df)} 条数据")
    
    # 计算指标
    df = calculate_indicators(df)
    
    # 分析信号
    signals = analyze_signals(df)
    
    # 决策
    decision, score, reasons = make_decision(signals)
    
    # 整理输出
    result = {
        "symbol": symbol,
        "latest_price": df.iloc[-1]['Close'],
        "decision": decision,
        "score": score,
        "reasons": reasons,
        "indicators": {
            "RSI": signals['RSI'],
            "MACD": signals['MACD'],
            "MACD_Cross": signals['MACD_Cross'],
            "MA_Arrange": signals['MA_Arrange'],
            "Volume_Ratio": signals['Volume_Ratio'],
            "Price_Change": signals['Price_Change']
        }
    }
    
    return result


def print_result(result):
    """打印结果"""
    if "error" in result:
        print(f"❌ {result['error']}")
        return
    
    print(f"\n{'='*55}")
    print(f"📈 股票: {result['symbol']}")
    print(f"💰 最新价格: ${result['latest_price']:.2f}")
    print(f"{'='*55}")
    print(f"🎯 决策: {result['decision']}")
    print(f"📊 综合评分: {result['score']}")
    print(f"📝 决策理由: {', '.join(result['reasons']) if result['reasons'] else '无明显信号'}")
    print(f"{'='*55}")
    print(f"📊 技术指标详情:")
    print(f"   RSI(14):     {result['indicators']['RSI']:.1f} (超买>70, 超卖<30)")
    print(f"   MACD:        {result['indicators']['MACD']:.4f}")
    print(f"   MACD交叉:    {result['indicators']['MACD_Cross']}")
    print(f"   均线排列:    {result['indicators']['MA_Arrange']}")
    print(f"   成交量比:    {result['indicators']['Volume_Ratio']:.2f}x")
    print(f"   当日涨跌幅:  {result['indicators']['Price_Change']:+.2f}%")
    print(f"{'='*55}\n")
    print("💡 提示: 此系统仅供娱乐，不构成投资建议！")
    print("📌 买卖信号权重: RSI(±2), MACD(±2), MA(±2), Volume(±1), BB(±1)\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()
    else:
        symbol = "AAPL"
    
    result = trade_signal(symbol)
    print_result(result)

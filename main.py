import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import argrelextrema
import matplotlib.cm as cm  # Для роботи з кольоровими картами

from ccxt_utils import get_ohlcv_sync
from config import WINDOW_EXTREMUM, STEP_FOR_HEAD_AND_SHOULDERS, TIMEFRAME, LIMIT_CANDLES, HEAD_AND_SHOULDERS_THRESHOLD
from utils import PatternChecker, MarketAnalyzer

# 1. Завантаження даних
ohlcv = get_ohlcv_sync('BTC-USDT', TIMEFRAME, LIMIT_CANDLES)
data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'Close', 'volume'])
pattern_checker = PatternChecker(WINDOW_EXTREMUM, STEP_FOR_HEAD_AND_SHOULDERS)


# Обчислення RSI
def calculate_rsi(data, window=14):
    """Функція для обчислення RSI."""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


data['RSI'] = calculate_rsi(data)
print(data)


# Визначення рівнів підтримки та опору в межах локального інтервалу
def calculate_support_resistance(data, window=5):
    """
    Визначає рівні підтримки та опору, обмежуючи їх в межах вказаного інтервалу.
    """
    support_levels = []
    resistance_levels = []

    # Локальні мінімуми (підтримка)
    min_indices = argrelextrema(data['Close'].values, np.less, order=window)[0]
    for idx in min_indices:
        start = max(idx - window, 0)
        end = min(idx + window, len(data))
        support_levels.append((idx, data['Close'][start:end].min()))

    # Локальні максимуми (опір)
    max_indices = argrelextrema(data['Close'].values, np.greater, order=window)[0]
    for idx in max_indices:
        start = max(idx - window, 0)
        end = min(idx + window, len(data))
        resistance_levels.append((idx, data['Close'][start:end].max()))

    return support_levels, resistance_levels


support_levels, resistance_levels = calculate_support_resistance(data, window=WINDOW_EXTREMUM)


# Функція для виявлення всіх патернів "Голова та плечі" та їх інверсії
def detect_all_head_and_shoulders(prices, threshold=HEAD_AND_SHOULDERS_THRESHOLD):
    patterns = []
    inverted_patterns = []
    for i in range(len(prices) - 5):
        left_shoulder = prices[i]
        head = prices[i + STEP_FOR_HEAD_AND_SHOULDERS]
        right_shoulder = prices[i + STEP_FOR_HEAD_AND_SHOULDERS * 2]

        # Звичайний патерн: "Голова та плечі"
        if (
            left_shoulder < head
            and right_shoulder < head
            and abs(left_shoulder - right_shoulder) < threshold * head
        ):
            patterns.append((i, i + STEP_FOR_HEAD_AND_SHOULDERS,
                             i + STEP_FOR_HEAD_AND_SHOULDERS * 2))  # Додаємо індекси плечей і голови

        # Інверсія: "Зворотна голова та плечі"
        if (
            left_shoulder > head
            and right_shoulder > head
            and abs(left_shoulder - right_shoulder) < threshold * head
        ):
            inverted_patterns.append((i, i + STEP_FOR_HEAD_AND_SHOULDERS,
                                      i + STEP_FOR_HEAD_AND_SHOULDERS * 2))  # Додаємо індекси плечей і голови

    return patterns, inverted_patterns


# Знаходимо всі патерни
patterns, inverted_patterns = detect_all_head_and_shoulders(data['Close'].values)

# 5. Візуалізація
plt.figure(figsize=(12, 6))
plt.plot(data['Close'], label='Ціна закриття', color='blue')

# Кольорова карта
colormap = cm.get_cmap('tab10')
num_patterns = len(patterns) + len(inverted_patterns)


# Фільтрація сигналів на основі RSI
rsi_threshold_lower = 30  # Перепроданість
rsi_threshold_upper = 70  # Перекупленість

# Відфільтровуємо патерни на основі значень RSI
# patterns = [pattern for pattern in patterns if data['RSI'].iloc[pattern[1]] < rsi_threshold_lower]
# inverted_patterns = [pattern for pattern in inverted_patterns if
#                               data['RSI'].iloc[pattern[1]] > rsi_threshold_upper]

# Позначення звичайних патернів
for idx, pattern in enumerate(patterns):
    color = colormap(idx / num_patterns)
    plt.scatter(list(pattern), data['Close'].iloc[list(pattern)], color=color)

# Позначення інверсії
for idx, pattern in enumerate(inverted_patterns):
    color = colormap((idx + len(patterns)) / num_patterns)
    plt.scatter(list(pattern), data['Close'].iloc[list(pattern)], color=color, marker='x')

# Рівні підтримки
for idx, level in support_levels:
    plt.hlines(level, xmin=max(idx - WINDOW_EXTREMUM, 0), xmax=min(idx + WINDOW_EXTREMUM, len(data)),
               colors='green', linestyles='solid', label='Локальна підтримка' if idx == support_levels[0][0] else "")
    bet_made = pattern_checker.is_pattern_found(idx, inverted_patterns)
    vline_style = 'solid' if bet_made else 'dashed'
    if vline_style == 'solid':
        plt.vlines(
            x=min(idx + WINDOW_EXTREMUM, len(data)),
            colors='green',
            ymin=data['Close'].min(),
            ymax=data['Close'].max(),
            linestyles=vline_style
        )

# Рівні опору
for idx, level in resistance_levels:
    plt.hlines(level, xmin=max(idx - WINDOW_EXTREMUM, 0), xmax=min(idx + WINDOW_EXTREMUM, len(data)),
               colors='red', linestyles='solid', label='Локальний опір' if idx == resistance_levels[0][0] else "")

    bet_made = pattern_checker.is_pattern_found(idx, patterns)
    vline_style = 'solid' if bet_made else 'dashed'
    if vline_style == 'solid':
        plt.vlines(
            min(idx + WINDOW_EXTREMUM, len(data)),
            colors='red',
            ymin=data['Close'].min(),
            ymax=data['Close'].max(),
            linestyles=vline_style
        )

plt.legend()
plt.title('Визначення патернів: Голова і плечі та зворотна голова і плечі з фільтрацією за RSI')
plt.xlabel('Час')
plt.ylabel('Ціна')
plt.show()

market_analyzer = MarketAnalyzer(support_levels, resistance_levels, patterns, inverted_patterns,
                                 WINDOW_EXTREMUM, STEP_FOR_HEAD_AND_SHOULDERS, data)
market_analyzer.analyze()

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import argrelextrema
import matplotlib.cm as cm  # Для роботи з кольоровими картами

from ccxt_utils import get_ohlcv_sync
from utils import calculate_head_and_shoulders_plus_resistance_and_support

# 1. Завантаження даних
ohlcv = get_ohlcv_sync('BTC-USDT', '3d', 200)
data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'Close', 'volume'])
print(data)
# data['Close'] = data['Close'].rolling(window=3).mean()  # Ковзаюче середнє для згладжування
window_extremum = 20
step_for_head_and_shoulders = 1


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


# Обчислення рівнів
support_levels, resistance_levels = calculate_support_resistance(data, window=window_extremum)


# Функція для виявлення всіх патернів "Голова та плечі" та їх інверсії
def detect_all_head_and_shoulders(prices, threshold=0.3):
    patterns = []
    inverted_patterns = []
    for i in range(len(prices) - 5):
        left_shoulder = prices[i]
        head = prices[i + step_for_head_and_shoulders]
        right_shoulder = prices[i + step_for_head_and_shoulders * 2]

        # Звичайний патерн: "Голова та плечі"
        if (
            left_shoulder < head
            and right_shoulder < head
            and abs(left_shoulder - right_shoulder) < threshold * head
        ):
            patterns.append((i, i + step_for_head_and_shoulders,
                             i + step_for_head_and_shoulders * 2))  # Додаємо індекси плечей і голови

        # Інверсія: "Зворотна голова та плечі"
        if (
            left_shoulder > head
            and right_shoulder > head
            and abs(left_shoulder - right_shoulder) < threshold * head
        ):
            inverted_patterns.append((i, i + step_for_head_and_shoulders,
                                      i + step_for_head_and_shoulders * 2))  # Додаємо індекси плечей і голови

    return patterns, inverted_patterns


# Знаходимо всі патерни
patterns, inverted_patterns = detect_all_head_and_shoulders(data['Close'].values)

# 5. Візуалізація
plt.figure(figsize=(12, 6))
plt.plot(data['Close'], label='Ціна закриття', color='blue')

# Кольорова карта
colormap = cm.get_cmap('tab10')
num_patterns = len(patterns) + len(inverted_patterns)

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
    plt.hlines(level, xmin=max(idx - window_extremum, 0), xmax=min(idx + window_extremum, len(data)),
               colors='green', linestyles='solid', label='Локальна підтримка' if idx == support_levels[0][0] else "")
    plt.vlines(min(idx + window_extremum, len(data)), colors='green', ymin=data['Close'].min(),
               ymax=data['Close'].max())

# Рівні опору
for idx, level in resistance_levels:
    plt.hlines(level, xmin=max(idx - window_extremum, 0), xmax=min(idx + window_extremum, len(data)),
               colors='red', linestyles='solid', label='Локальний опір' if idx == resistance_levels[0][0] else "")
    plt.vlines(min(idx + window_extremum, len(data)), colors='red', ymin=data['Close'].min(), ymax=data['Close'].max())

plt.legend()
plt.title('Визначення патернів: Голова і плечі та зворотна голова і плечі')
plt.xlabel('Час')
plt.ylabel('Ціна')
plt.show()
calculate_head_and_shoulders_plus_resistance_and_support(support_levels, resistance_levels, patterns, inverted_patterns,
                                                         window_extremum, step_for_head_and_shoulders, data)

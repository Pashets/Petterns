import matplotlib.pyplot as plt
import matplotlib.cm as cm  # Для роботи з кольоровими картами


def plot_visualization(data, support_levels, resistance_levels, patterns, inverted_patterns, transactions,
                       window_extremum, step_for_head_and_shoulders):
    """
    Функція для візуалізації даних з рівнями підтримки, опору, RSI, та патернами "Голова і плечі".

    Параметри:
        - data: pd.DataFrame - датафрейм із фінансовими даними.
        - support_levels: list - рівні підтримки.
        - resistance_levels: list - рівні опору.
        - patterns: list - знайдені патерни "Голова і плечі".
        - inverted_patterns: list - інверсні патерни "Голова і плечі".
        - transactions: list - транзакції на основі аналізу.
        - window_extremum: int - розмір вікна для екстремумів.
        - step_for_head_and_shoulders: int - крок для патернів "Голова і плечі".
    """
    plt.figure(figsize=(12, 6))
    plt.plot(data['Close'], label='Ціна закриття', color='blue')

    # Кольорова карта
    colormap = cm.get_cmap('tab10')
    num_patterns = len(patterns) + len(inverted_patterns)

    # Фільтрація сигналів на основі RSI
    rsi_threshold_lower = 30  # Перепроданість
    rsi_threshold_upper = 70  # Перекупленість

    # Відфільтровуємо патерни на основі значень RSI
    patterns = [pattern for pattern in patterns if data['RSI'].iloc[pattern[1]] < rsi_threshold_lower]
    inverted_patterns = [pattern for pattern in inverted_patterns if data['RSI'].iloc[pattern[1]] > rsi_threshold_upper]

    # Позначення звичайних патернів
    # for idx, pattern in enumerate(patterns):
    #     color = colormap(idx / num_patterns)
    #     plt.scatter(list(pattern), data['Close'].iloc[list(pattern)], color=color)
    #
    # Позначення інверсії
    # for idx, pattern in enumerate(inverted_patterns):
    #     color = colormap((idx + len(patterns)) / num_patterns)
    #     plt.scatter(list(pattern), data['Close'].iloc[list(pattern)], color=color, marker='x')

    # Рівні підтримки
    for idx, level in support_levels:
        plt.hlines(level, xmin=max(idx - window_extremum, 0), xmax=min(idx + window_extremum, len(data)),
                   colors='green', linestyles='solid', label='Локальна підтримка' if idx == support_levels[0][0] else "")

    # Рівні опору
    for idx, level in resistance_levels:
        plt.hlines(level, xmin=max(idx - window_extremum, 0), xmax=min(idx + window_extremum, len(data)),
                   colors='red', linestyles='solid', label='Локальний опір' if idx == resistance_levels[0][0] else "")

    # Транзакції
    num_transactions = len(transactions)
    for i, transaction in enumerate(transactions):
        color = colormap(i / num_transactions)
        # Додаємо число біля лінії для початку транзакції
        plt.text(
            transaction[0][0],  # X-координата (час)
            data['Close'].max(),  # Y-координата (на верхній межі графіка)
            str(i),  # Текст (номер транзакції)
            color=color,
            fontsize=7,
            horizontalalignment='center',
        )

        # Додаємо вертикальну лінію для кінця транзакції
        plt.vlines(
            transaction[1][0],
            ymin=data['Close'].min(),
            ymax=data['Close'].max(),
            colors=color,
            linestyles='dashed'
        )
        # Додаємо число біля лінії для кінця транзакції
        plt.text(
            transaction[1][0],  # X-координата (час)
            data['Close'].max(),  # Y-координата (на верхній межі графіка)
            str(i),  # Текст (номер транзакції)
            color=color,
            fontsize=7,
            horizontalalignment='center'
        )

    # Лінія RSI
    min_close = data['Close'].min()
    max_close = data['Close'].max()
    diff = max_close - min_close
    level_rsi_70 = min_close + diff * 70 / 100
    level_rsi_30 = min_close + diff * 30 / 100
    data['RSI'] = min_close + diff * data['RSI'] / 100
    plt.plot(data['RSI'], label='RSI', color='orange', linestyle='solid')

    # Рівні перекупленості та перепроданості
    plt.axhline(level_rsi_70, color='red', linestyle='dotted', label='Перекупленість (70)')
    plt.axhline(level_rsi_30, color='green', linestyle='dotted', label='Перепроданість (30)')

    # Заголовок і легенда
    plt.title('Ціна закриття з рівнями підтримки, опору та RSI')
    plt.xlabel('Час')
    plt.ylabel('Ціна / RSI')
    plt.legend()

    plt.show()
    print(data['Close'])

# INCORRECT
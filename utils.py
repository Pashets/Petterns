import numpy as np
import pandas as pd

# support_levels = [(np.int64(3), np.float64(90247.42)), (np.int64(6), np.float64(89125.25)),
#                   (np.int64(10), np.float64(91294.13)), (np.int64(15), np.float64(92036.14)),
#                   (np.int64(33), np.float64(95915.8)), (np.int64(42), np.float64(91690.6)),
#                   (np.int64(48), np.float64(94956.22)), (np.int64(55), np.float64(96642.04)),
#                   (np.int64(59), np.float64(96327.9)), (np.int64(68), np.float64(95278.23)),
#                   (np.int64(73), np.float64(95738.65)), (np.int64(79), np.float64(97730.97)),
#                   (np.int64(83), np.float64(99294.81)), (np.int64(88), np.float64(98887.69)),
#                   (np.int64(94), np.float64(96899.18)), (np.int64(97), np.float64(95637.6))]
# resistance_levels = [(np.int64(4), np.float64(91296.09)), (np.int64(9), np.float64(92329.01)),
#                      (np.int64(13), np.float64(92385.41)), (np.int64(23), np.float64(98832.01)),
#                      (np.int64(26), np.float64(99270.52)), (np.int64(36), np.float64(98488.86)),
#                      (np.int64(46), np.float64(96229.29)), (np.int64(53), np.float64(98012.85)),
#                      (np.int64(62), np.float64(97766.15)), (np.int64(65), np.float64(97120.71)),
#                      (np.int64(75), np.float64(102941.05)), (np.int64(82), np.float64(100369.27)),
#                      (np.int64(87), np.float64(99931.22)), (np.int64(90), np.float64(100024.32)),
#                      (np.int64(96), np.float64(97483.0))]
# patters = [(2, 4, 6), (6, 8, 10), (7, 9, 11), (11, 13, 15), (21, 23, 25), (24, 26, 28), (33, 35, 37), (44, 46, 48),
#            (51, 53, 55), (52, 54, 56), (55, 57, 59), (59, 61, 63), (60, 62, 64), (63, 65, 67), (69, 71, 73),
#            (74, 76, 78), (79, 81, 83), (80, 82, 84), (84, 86, 88), (85, 87, 89), (88, 90, 92), (94, 96, 98)]
# inverted_patterns = [(0, 2, 4), (1, 3, 5), (4, 6, 8), (8, 10, 12), (9, 11, 13), (13, 15, 17), (31, 33, 35),
#                      (32, 34, 36), (40, 42, 44), (41, 43, 45), (46, 48, 50), (47, 49, 51), (53, 55, 57), (54, 56, 58),
#                      (57, 59, 61), (61, 63, 65), (66, 68, 70), (67, 69, 71), (77, 79, 81), (78, 80, 82), (81, 83, 85),
#                      (82, 84, 86), (86, 88, 90), (92, 94, 96)]
# window_extremum = 2


# Типи даних для рівнів та патернів
Level = tuple[int, float, str]
Pattern = tuple[int, int, int]


def calculate_head_and_shoulders_plus_resistance_and_support(
    support_levels: list[tuple[int, float]],
    resistance_levels: list[tuple[int, float]],
    patterns: list[Pattern],
    inverted_patterns: list[Pattern],
    window_extremum: int,
    step_for_head_and_shoulders:int,
    data: pd.DataFrame
) -> None:
    """
    Функція для аналізу патернів "Голова та плечі" із урахуванням рівнів підтримки та опору.

    Parameters:
        support_levels: Список рівнів підтримки (індекс, ціна).
        resistance_levels: Список рівнів опору (індекс, ціна).
        patterns: Список звичайних патернів (індекси плечей і голови).
        inverted_patterns: Список інверсних патернів (індекси плечей і голови).
        window_extremum: Вікно для екстремумів.
        step_for_head_and_shoulders: Крок для голови і плечей.
        data: DataFrame із ціновими даними (обов'язково містить колонку 'Close').
    """
    balance = 100.0
    last_cost = 0.0
    last_level = None

    # Підготовка рівнів із позначенням типу
    support_levels = [(*s, 'sup') for s in support_levels]
    resistance_levels = [(*s, 'res') for s in resistance_levels]
    levels: list[Level] = sorted(support_levels + resistance_levels)

    def process_level(level: Level, pattern_list: list[Pattern], direction: str) -> None:
        nonlocal balance, last_cost, last_level
        index, _, level_type = level

        print(f"\nОбробка рівня: Індекс = {index}, Тип = {level_type}, Напрямок = {direction}")

        # Перевірка патернів у межах вікна екстремуму
        for offset in range(window_extremum + 1):
            extremum_index = index + offset
            pattern_to_check = (extremum_index - step_for_head_and_shoulders, extremum_index, extremum_index + step_for_head_and_shoulders)
            end_level_index = index + window_extremum

            # Перевіряємо, чи є патерн у списку
            if pattern_to_check in pattern_list:
                action = "Закриваємо шорт, відкриваємо лонг" if direction == 'sup' else "Закриваємо лонг, відкриваємо шорт"
                print(f"Патерн знайдено: {pattern_to_check}. Дія: {action}")

                # Перевірка коректності індексу перед доступом до даних
                if 0 <= end_level_index < len(data):
                    cost = data['Close'].iloc[end_level_index]
                    print(f"Ціна на екстремумі (індекс {end_level_index}): {cost:.2f}")

                    if last_level is None:
                        last_cost = cost
                        print("Це перший рівень, встановлюємо початкову ціну.")
                    else:
                        if last_level != level[2]:
                            diff_cost = (cost - last_cost) / last_cost if direction == 'res' else (last_cost - cost) / cost
                            # transaction_fee = balance / 20 / 100
                            transaction_fee = 0  # В майбутньому можна врахувати комісію
                            profit_or_loss = diff_cost * balance / 20 - transaction_fee
                            balance += profit_or_loss
                            print(
                                f"Результат угоди: {'Прибуток' if profit_or_loss > 0 else 'Збиток'} {profit_or_loss:.2f}")
                            last_cost = cost
                        else:
                            print("Рівень не змінився. Оновлюємо середню ціну.")
                            last_cost = (last_cost + cost) / 2

                        print(f"Оновлений баланс: {balance:.2f}")
                    last_level = level[2]
                else:
                    print(f"Некоректний індекс екстремуму: {end_level_index}, пропускаємо.")
                break

    # Обробка рівнів
    for level in levels:
        if level[2] == 'sup':
            process_level(level, inverted_patterns, 'sup')
        elif level[2] == 'res':
            process_level(level, patterns, 'res')
    print(f'Баланс = {balance:.2f}')


if __name__ == '__main__':
    calculate_head_and_shoulders_plus_resistance_and_support(support_levels, resistance_levels, patters,
                                                             inverted_patterns, window_extremum)

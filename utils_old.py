from typing import List, Tuple
import pandas as pd

from config import INITIAL_BALANCE, STAKE_MULTIPLIER_START, PERCENT_OF_BALANCE_FOR_BET

Level = Tuple[int, float, str]
Pattern = Tuple[int, int, int]


class PatternChecker:
    def __init__(self, window_extremum: int, step_for_head_and_shoulders: int):
        self.window_extremum = window_extremum
        self.step_for_head_and_shoulders = step_for_head_and_shoulders

    def is_pattern_found(self, index: int, pattern_list: List[Pattern]) -> bool:
        """Перевіряє, чи є патерн у списку в межах вікна екстремуму."""
        for offset in range(self.window_extremum + 1):
            extremum_index = index + offset
            pattern_to_check = (
                extremum_index - self.step_for_head_and_shoulders,
                extremum_index,
                extremum_index + self.step_for_head_and_shoulders
            )
            if pattern_to_check in pattern_list:
                return True
        return False


class MarketAnalyzer:
    def __init__(
        self,
        support_levels: List[Tuple[int, float]],
        resistance_levels: List[Tuple[int, float]],
        patterns: List[Pattern],
        inverted_patterns: List[Pattern],
        window_extremum: int,
        step_for_head_and_shoulders: int,
        data: pd.DataFrame
    ):
        self.balance = INITIAL_BALANCE
        self.last_cost = 0.0
        self.last_level = None
        self.stake_multiplier = STAKE_MULTIPLIER_START
        self.percent_of_balance_for_bet = PERCENT_OF_BALANCE_FOR_BET
        self.data = data

        self.patterns = patterns
        self.inverted_patterns = inverted_patterns
        self.pattern_checker = PatternChecker(window_extremum, step_for_head_and_shoulders)

        # Підготовка рівнів із позначенням типу
        self.levels: List[Level] = sorted(
            [(*s, 'sup') for s in support_levels] + [(*r, 'res') for r in resistance_levels]
        )

    def analyze(self):
        for level in self.levels:
            if level[2] == 'sup':
                self._process_level(level, self.inverted_patterns, 'sup')
            elif level[2] == 'res':
                self._process_level(level, self.patterns, 'res')
        print(f'Баланс = {self.balance:.2f}')

    def _process_level(self, level: Level, pattern_list: List[Pattern], direction: str):
        index, _, level_type = level

        print(f"\nОбробка рівня: Індекс = {index}, Тип = {level_type}, Напрямок = {direction}")

        if self.pattern_checker.is_pattern_found(index, pattern_list):
            end_level_index = index + self.pattern_checker.window_extremum
            self._execute_trade(level, direction, end_level_index)

    def _execute_trade(self, level: Level, direction: str, end_level_index: int):
        if not (0 <= end_level_index < len(self.data)):
            print(f"Некоректний індекс екстремуму: {end_level_index}, пропускаємо.")
            return

        cost = self.data['Close'].iloc[end_level_index]
        print(f"Ціна на кінці рівня (індекс {end_level_index}): {cost:.2f}")

        if self.last_level is None:
            self.last_cost = cost
            self.stake_multiplier = 1.0
            print("Це перший рівень, встановлюємо початкову ціну.")
        else:
            if self.last_level != level[2]:
                diff_cost = (cost - self.last_cost) / self.last_cost if direction == 'res' \
                    else (self.last_cost - cost) / cost
                transaction_fee = self.balance * self.percent_of_balance_for_bet /100 / 100
                # transaction_fee = 0  # В майбутньому можна врахувати комісію
                profit_or_loss = diff_cost * self.balance * self.percent_of_balance_for_bet / 100 * self.stake_multiplier - transaction_fee
                roi = diff_cost * 100  # ROI у відсотках
                self.balance += profit_or_loss
                print(
                    f"Угода: \n"
                    f"  Куплено за: {self.last_cost:.2f}\n"
                    f"  Продано за: {cost:.2f}\n"
                    f"  Результат: {'Прибуток' if profit_or_loss > 0 else 'Збиток'} {profit_or_loss:.2f}\n"
                    f"  ROI: {roi:.2f}%"
                )
                self.last_cost = cost
                self.stake_multiplier = 1.0  # Скидаємо множник
            else:
                print("Рівень не змінився. Оновлюємо середню ціну.")
                self.last_cost = (self.last_cost + cost) / 2
                self.stake_multiplier *= 2  # Збільшуємо ставку вдвічі
                print(f"Новий множник ставки: {self.stake_multiplier}, "
                      f"в гривнях = {self.balance * self.percent_of_balance_for_bet /100 * self.stake_multiplier}")

            print(f"Оновлений баланс: {self.balance:.2f}")
        self.last_level = level[2]

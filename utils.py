from typing import List, Tuple
import pandas as pd

from config import INITIAL_BALANCE, STAKE_MULTIPLIER_START, PERCENT_OF_BALANCE_FOR_BET, PERCENT_TAKE_PROFIT, \
    PERCENT_STOP_LOSS, TRAILING_STOP_LOSS_PERCENT

Level = Tuple[int, float, str]
Pattern = Tuple[int, int, int]


class PatternChecker:
    def __init__(self, window_extremum: int, step_for_head_and_shoulders: int):
        self.window_extremum = window_extremum
        self.step_for_head_and_shoulders = step_for_head_and_shoulders

    def is_pattern_found(self, index: int, pattern_list: List[Pattern]) -> bool:
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


class TradeExecutor:
    def __init__(self, stake_amount, cost, direction):
        self.stake_amount = stake_amount
        self.entry_price = cost
        self.direction = direction
        self.trailing_stop_loss = None
        self.max_roi = 0
        self.trailing_stop_loss_percent = TRAILING_STOP_LOSS_PERCENT

    def calculate_roi(self, current_price):
        """Розрахунок ROI залежно від напряму угоди."""
        if self.direction == 'long':
            return (current_price - self.entry_price) / self.entry_price * 100
        elif self.direction == 'short':
            return (self.entry_price - current_price) / self.entry_price * 100

    def update_trailing_stop_loss(self, roi):
        """Оновлення трейлінг стоп-лосса."""
        self.max_roi = max(self.max_roi, roi)
        trailing_stop_loss_percent = max(self.max_roi - self.trailing_stop_loss_percent, 7)  # Мінімальний ROI +7%
        if self.direction == 'long':
            self.trailing_stop_loss = self.entry_price * (1 + trailing_stop_loss_percent / 100)
        elif self.direction == 'short':
            self.trailing_stop_loss = self.entry_price * (1 - trailing_stop_loss_percent / 100)

    def is_stop_loss_hit(self, current_price):
        """Перевірка, чи досягнуто стоп-лос."""
        if self.direction == 'long':
            return current_price <= self.trailing_stop_loss
        elif self.direction == 'short':
            return current_price >= self.trailing_stop_loss

    def is_take_profit_hit(self, current_price, take_profit):
        """Перевірка, чи досягнуто тейк-профіт."""
        if self.direction == 'long':
            return current_price >= take_profit
        elif self.direction == 'short':
            return current_price <= take_profit


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

        self.levels: List[Level] = sorted(
            [(*s, 'sup') for s in support_levels] + [(*r, 'res') for r in resistance_levels]
        )

    def analyze(self):
        for level in self.levels:
            if level[2] == 'sup':
                self._process_level(level, self.inverted_patterns)
            elif level[2] == 'res':
                self._process_level(level, self.patterns)
        print(f'Баланс = {self.balance:.2f}')

    def _process_level(self, level: Level, pattern_list: List[Pattern]):
        index, _, level_type = level

        print(f"\nОбробка рівня: Індекс = {index}, Тип = {level_type}")

        if self.pattern_checker.is_pattern_found(index, pattern_list):
            end_level_index = index + self.pattern_checker.window_extremum
            self._execute_trade(level, end_level_index)

    def _execute_trade(self, level: Level, end_level_index: int):
        if not (0 <= end_level_index < len(self.data)):
            print(f"Некоректний індекс екстремуму: {end_level_index}, пропускаємо.")
            return

        cost = self.data['Close'].iloc[end_level_index]
        future_price = self.data['Close'].iloc[end_level_index]
        print(f"Ціна на кінці рівня (індекс {end_level_index}): {cost:.2f}")

        stake_amount = self.balance * self.percent_of_balance_for_bet / 100 * self.stake_multiplier
        direction = 'long' if level[2] == 'sup' else 'short'

        stop_loss = cost * (1 - PERCENT_STOP_LOSS / 100) if direction == 'long' else cost * (
                1 + PERCENT_STOP_LOSS / 100)
        take_profit = cost * (1 + PERCENT_TAKE_PROFIT / 100) if direction == 'long' else cost * (
                1 - PERCENT_TAKE_PROFIT / 100)

        print(f"Стоп-лос: {stop_loss:.2f}, Тейк-профіт: {take_profit:.2f}")

        executor = TradeExecutor(stake_amount, cost, direction)

        for future_index in range(end_level_index + 1, len(self.data)):
            future_price = self.data['Close'].iloc[future_index]
            roi = executor.calculate_roi(future_price)

            if executor.trailing_stop_loss is not None:
                if executor.is_stop_loss_hit(future_price):
                    profit_or_loss = stake_amount * roi/100
                    print(
                        f"Трейлінг стоп-лос досягнуто на індексі {future_index}. Ціна: {future_price:.2f}, ROI: {roi:.2f}%")
                    break
            else:
                if future_price <= stop_loss if direction == 'long' else future_price >= stop_loss:
                    profit_or_loss = -stake_amount * PERCENT_STOP_LOSS / 100
                    print(f"Стоп-лос досягнуто на індексі {future_index}. Ціна: {future_price:.2f}")
                    break
                elif executor.is_take_profit_hit(future_price, take_profit):
                    print(
                        f"Тейк-профіт досягнуто на індексі {future_index}. Ціна: {future_price:.2f}, ROI: {roi:.2f}%")
                    executor.update_trailing_stop_loss(roi)

            if executor.trailing_stop_loss is not None:
                executor.update_trailing_stop_loss(roi)

        else:
            roi = executor.calculate_roi(future_price)
            print(f"Стоп-лос і тейк-профіт не досягнуті. Трейд закрито за останньою ціною. ROI: {roi:.2f}%")
            profit_or_loss = stake_amount * (
                    future_price - cost) / cost if direction == 'long' else stake_amount * (
                    cost - future_price) / cost

        self.balance += profit_or_loss
        print(stake_amount, future_price, cost)
        print(f"Результат трейду: {'Прибуток' if profit_or_loss > 0 else 'Збиток'} {profit_or_loss:.2f}")
        print(f"Оновлений баланс: {self.balance:.2f}")

        self.last_cost = cost
        self.last_level = level[2]
        self.stake_multiplier = 1.0

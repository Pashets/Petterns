from enum import Enum
from typing import List, Tuple
import pandas as pd

from config import INITIAL_BALANCE, STAKE_MULTIPLIER_START, PERCENT_OF_BALANCE_FOR_BET, PERCENT_TAKE_PROFIT, \
    PERCENT_STOP_LOSS, TRAILING_STOP_LOSS_PERCENT, TRAILING_STOP_LOSS_PERCENT_FOR_POSITIVE_FILTER, \
    TRAILING_STOP_LOSS_PERCENT_FOR_NEGATIVE_FILTER, RSI_FOR_INCREASE_TRAILING_PERCENT_ON_LONG, \
    RSI_FOR_CLOSING_LONG, RSI_FOR_CLOSING_SHORT, RSI_FOR_DECREASE_TRAILING_PERCENT_ON_LONG, \
    RSI_FOR_DECREASE_TRAILING_PERCENT_ON_SHORT, RSI_FOR_INCREASE_TRAILING_PERCENT_ON_SHORT

Level = Tuple[int, float, str]
Pattern = Tuple[int, int, int]

MINIMUM_TRAILING_STOP_LOSS_PERCENT = PERCENT_TAKE_PROFIT * (100 - TRAILING_STOP_LOSS_PERCENT) / 100


class StateTrailingStopLoss(Enum):
    normal = 'normal'
    increased = 'increased'
    decreased = 'decreased'


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
        self.state_trailing_stop_loss = StateTrailingStopLoss.normal

    def calculate_roi(self, current_price):
        """Розрахунок ROI залежно від напряму угоди."""
        if self.direction == 'long':
            return (current_price - self.entry_price) / self.entry_price * 100
        elif self.direction == 'short':
            return (self.entry_price - current_price) / self.entry_price * 100

    def update_trailing_stop_loss(self, roi, price, rsi, long_ema, short_ema):
        """Оновлення трейлінг стоп-лосса."""
        self.update_state_trailing_stop_loss(price, rsi, long_ema, short_ema)
        self.max_roi = max(self.max_roi, roi)

        # diff_trailing_stop_loss_percent = self.trailing_stop_loss_percent
        # if self.state_trailing_stop_loss == StateTrailingStopLoss.increased:
        #     diff_trailing_stop_loss_percent *= 1 + TRAILING_STOP_LOSS_PERCENT_FOR_POSITIVE_FILTER / 100
        # if self.state_trailing_stop_loss == StateTrailingStopLoss.decreased:
        #     diff_trailing_stop_loss_percent *= 1 - TRAILING_STOP_LOSS_PERCENT_FOR_NEGATIVE_FILTER / 100
        #
        trailing_stop_loss_percent = max(
            self.max_roi * (100 - TRAILING_STOP_LOSS_PERCENT) / 100,
            # self.max_roi * (100 - diff_trailing_stop_loss_percent) / 100,
            MINIMUM_TRAILING_STOP_LOSS_PERCENT
        )
        if self.direction == 'long':
            self.trailing_stop_loss = self.entry_price * (1 + trailing_stop_loss_percent / 100)
        elif self.direction == 'short':
            self.trailing_stop_loss = self.entry_price * (1 - trailing_stop_loss_percent / 100)
        # print(self.max_roi, self.trailing_stop_loss_percent, diff_trailing_stop_loss_percent,
        print(self.max_roi, self.trailing_stop_loss_percent, TRAILING_STOP_LOSS_PERCENT,
              trailing_stop_loss_percent, self.trailing_stop_loss)

    def update_state_trailing_stop_loss(self, price, rsi, long_ema, short_ema):
        if self.direction == 'long':
            if (
                rsi > RSI_FOR_DECREASE_TRAILING_PERCENT_ON_LONG
                and price < short_ema
            ):
                if self.state_trailing_stop_loss != StateTrailingStopLoss.decreased:
                    print(f'trailing_stop_loss_percent знизився на {TRAILING_STOP_LOSS_PERCENT_FOR_NEGATIVE_FILTER}%!')
                    self.state_trailing_stop_loss = StateTrailingStopLoss.decreased
            elif (
                RSI_FOR_DECREASE_TRAILING_PERCENT_ON_LONG > rsi > RSI_FOR_INCREASE_TRAILING_PERCENT_ON_LONG
                and price > short_ema
                and price > long_ema
            ):
                if self.state_trailing_stop_loss != StateTrailingStopLoss.increased:
                    print(
                        f'trailing_stop_loss_percent збільшився на {TRAILING_STOP_LOSS_PERCENT_FOR_POSITIVE_FILTER}%!')
                    self.state_trailing_stop_loss = StateTrailingStopLoss.increased
            elif self.state_trailing_stop_loss != StateTrailingStopLoss.normal:
                print(f'trailing_stop_loss_percent звичайний!')
                self.state_trailing_stop_loss = StateTrailingStopLoss.normal
        if self.direction == 'short':
            if (
                rsi < RSI_FOR_DECREASE_TRAILING_PERCENT_ON_SHORT
                and price > short_ema
            ):
                if self.state_trailing_stop_loss != StateTrailingStopLoss.decreased:
                    print(f'trailing_stop_loss_percent знизився на {TRAILING_STOP_LOSS_PERCENT_FOR_NEGATIVE_FILTER}%!')
                    self.state_trailing_stop_loss = StateTrailingStopLoss.decreased
            elif (
                RSI_FOR_DECREASE_TRAILING_PERCENT_ON_SHORT < rsi < RSI_FOR_INCREASE_TRAILING_PERCENT_ON_SHORT
                and price < short_ema
                and price < long_ema
            ):
                if self.state_trailing_stop_loss != StateTrailingStopLoss.increased:
                    print(
                        f'trailing_stop_loss_percent збільшився на {TRAILING_STOP_LOSS_PERCENT_FOR_POSITIVE_FILTER}%!')
                    self.state_trailing_stop_loss = StateTrailingStopLoss.increased
            elif self.state_trailing_stop_loss != StateTrailingStopLoss.normal:
                print(f'trailing_stop_loss_percent звичайний!')
                self.state_trailing_stop_loss = StateTrailingStopLoss.normal

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

    def is_close_position(self, rsi):
        if self.direction == 'short':
            return rsi > RSI_FOR_CLOSING_LONG
        if self.direction == 'long':
            return rsi < RSI_FOR_CLOSING_SHORT


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
        self.transactions = []

    def analyze(self):
        for level in self.levels:
            if level[2] == 'sup':
                self._process_level(level, self.inverted_patterns)
            elif level[2] == 'res':
                self._process_level(level, self.patterns)
        print(f'Баланс = {self.balance:.2f}')
        return self.transactions

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
            rsi = self.data['RSI'].iloc[future_index]
            long_ema = self.data['LONG_EMA'].iloc[future_index]
            short_ema = self.data['SHORT_EMA'].iloc[future_index]

            if executor.trailing_stop_loss is not None:
                # if executor.is_close_position(rsi):
                #     profit_or_loss = stake_amount * roi / 100
                #     print(
                #         f"Закриваємо через {rsi=} на індексі {future_index}. Ціна: {future_price:.2f}, ROI: {roi:.2f}%")
                #     break

                if executor.is_stop_loss_hit(future_price):
                    profit_or_loss = stake_amount * roi / 100
                    print(
                        f"Трейлінг стоп-лос досягнуто на індексі {future_index}. Ціна: {future_price:.2f}, ROI: {roi:.2f}%")
                    break
            else:
                if future_price <= stop_loss if direction == 'long' else future_price >= stop_loss:
                    profit_or_loss = -stake_amount * PERCENT_STOP_LOSS / 100
                    print(f"Стоп-лос досягнуто на індексі {future_index}. Ціна: {future_price:.2f}. ROI: {roi:.2f}%")
                    break
                elif executor.is_take_profit_hit(future_price, take_profit):
                    print(
                        f"Тейк-профіт досягнуто на індексі {future_index}. Ціна: {future_price:.2f}, ROI: {roi:.2f}%")
                    executor.update_trailing_stop_loss(roi, future_price, rsi, long_ema, short_ema)

            if executor.trailing_stop_loss is not None:
                executor.update_trailing_stop_loss(roi, future_price, rsi, long_ema, short_ema)

        else:
            roi = executor.calculate_roi(future_price)
            print(f"Стоп-лос і тейк-профіт не досягнуті. Трейд закрито за останньою ціною. ROI: {roi:.2f}%")
            profit_or_loss = stake_amount * (
                future_price - cost) / cost if direction == 'long' else stake_amount * (
                cost - future_price) / cost

        transaction_fee = stake_amount / 100
        # transaction_fee = 0
        profit_or_loss -= transaction_fee
        self.balance += profit_or_loss
        print(f"Результат трейду: {'Прибуток' if profit_or_loss > 0 else 'Збиток'} {profit_or_loss:.2f}")
        print(f"Оновлений баланс: {self.balance:.2f}")

        self.last_cost = cost
        self.last_level = level[2]
        self.stake_multiplier = 1.0
        self.transactions.append([(end_level_index, cost), (future_index, future_price, profit_or_loss, roi)])

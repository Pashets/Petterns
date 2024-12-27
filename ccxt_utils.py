import random

import ccxt.async_support as ccxt
from ccxt import RequestTimeout, ExchangeError


def get_random_exchange():
    return random.choice([
        ccxt.binance(),
        ccxt.bingx(),
    ])


async def get_ohlcv(symbol, timeframe, limit):
    exchange = get_random_exchange()
    try:
        data = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    except (RequestTimeout, ExchangeError):
        return await get_ohlcv(symbol, timeframe, limit)
    else:
        await exchange.close()
        return data


def get_ohlcv_sync(symbol, timeframe, limit):
    import ccxt
    exchange = random.choice([
        # ccxt.binance(),
        ccxt.bingx(),
    ])
    data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    print(symbol, timeframe)
    return data
import threading
from shared_memory import symbol_obj_map, data
from strategies.trading_strategy import TradingStrategy
#from strategies.delta_neutral_strategy import Delta_Neutral_Base
from strategies.ratio_strategy import Ratio
from strategies.straddle_strangle_strategy import Straddle_Strangle
from strategies.straddle_strategy import Straddle
from strategies.ema_strategy import Ema
import time


strategy_class_map = {
    TradingStrategy.RATIO: Ratio,
    TradingStrategy.STRADDLE_STRANGLE_COMBO: Straddle_Strangle,
    TradingStrategy.STRADDLE: Straddle,
    TradingStrategy.EMA: Ema,
    #TradingStrategy.DELTA_NEUTRAL: Delta_Neutral_Base
}


def thread_monitor():
    time.sleep(50) 

    while True:
        for symbol in symbol_obj_map.dictionary:
            if symbol_obj_map.dictionary[symbol] != None:
                if not symbol_obj_map.dictionary[symbol].is_alive():

                    print(f"Thread: {symbol} is inactive, restarting...")
                    thread = strategy_class_map[data.strategy]( symbol = symbol,
                                                                quantity = symbol_obj_map.dictionary[symbol].quantity,
                                                                is_hedge = symbol_obj_map.dictionary[symbol].is_hedge
                                                                )
                    thread.start()
                    symbol_obj_map.dictionary[symbol] = thread

        time.sleep(5)  
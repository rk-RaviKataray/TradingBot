from pya3 import *
from shared_memory import data,shared_memory
import time
import math


class order_type:
    SELL = 'sell'
    BUY = 'buy'


def place_order(symbol,quantity,exchange,transaction_type):

    #print(f'placing order for {symbol} - {quantity}')
    order_type_ = TransactionType.Sell if transaction_type == order_type.SELL else TransactionType.Buy
    token = shared_memory.dictionary[symbol]['TOKEN']
    
    '''
    for index in data.todays_trading_instrument:
        if symbol.startswith(index):
            freeze_limit = data.quantity_freeze_dict[index]
            lot_size = data.lot_size_dict[index]
      

    if not quantity % lot_size == 0:
        raise Exception(f'{symbol} Quantity not a multiple of lot size, expected a multiple of {lot_size} got {quantity}.')

    no_of_orders = math.ceil(quantity / freeze_limit)
    last_order_quantity = quantity % freeze_limit


    for order in range(no_of_orders):
        
        qunatity_ = last_order_quantity if order == no_of_orders - 1 else freeze_limit
    '''


'''
        while True:
            response = data.alice.place_order(transaction_type = order_type_,
                                instrument = data.alice.get_instrument_by_token(exchange, token),
                                quantity = quantity,
                                order_type = OrderType.Market,
                                product_type = ProductType.Intraday,
                                price = 0.0,
                                trigger_price = None,
                                stop_loss = None,
                                square_off = None,
                                trailing_sl = None,
                                is_amo = False,
                                order_tag='order1')
        
            if response['stat'] == 'Ok':
                break
            time.sleep(0.5)

'''
from flask import Flask, jsonify, render_template, request, send_file
import shared_memory
from shared_memory import shared_memory, symbol_obj_map, data
import Socket
from pya3 import *
import pandas as pd
import datetime
import pytz
import json
import os
from multiprocessing import Process, Manager
from UltraDict import UltraDict
import multiprocessing
import helper_functions
import frontend
from strategy_initializer.strategy_initializer import strategy_Initializer
import time
from thread_monitor import thread_monitor
import schedule
from functools import partial



app = Flask(__name__, static_url_path='/static')
manager = Manager()
shared_dict = manager.dict()

@app.route('/get_frontend_data', methods=['GET', 'POST'])
def get_frontend_data():
    return dict(shared_dict)


@app.route('/api/candle_data/<filename>', methods=['GET', 'POST'])
def serve_file(filename):
    try:
        data_directory = os.path.join('instrument_data',data.strategy, filename, 'candle_data.jsonl')

        # Send the file's content as the API response
        return send_file(data_directory, mimetype='application/json')
    except Exception as e:
        print('Error serving file:', e)
        return '', 500


@app.route('/api/position_data/<filename>', methods=['GET', 'POST'])
def serve_position_file(filename):
    try:
        data_directory = os.path.join('instrument_data',data.strategy, filename, f'{filename}.log')

        # Send the file's content as the API response
        return send_file(data_directory, mimetype='text/html')
    except Exception as e:
        print('Error serving file:', e)
        return '', 500

@app.route('/sell', methods=['GET', 'POST'])
def sell():

    instrument = request.args.get('instrument')
    index = ''

    for indice in data.indices:
        if instrument.startswith(indice):
            index = indice

    shared_memory.dictionary[index]['SELL_INSTRUMENT_LIST'] = instrument
   
    return '', 204
    

@app.route('/buy', methods=['GET', 'POST'])
def buy():
    
    instrument = request.args.get('instrument')
    index = ''

    for indice in data.indices:
        if instrument.startswith(indice):
            index = indice
    shared_memory.dictionary[index]['BUY_INSTRUMENT_LIST'] = instrument
 
    return '', 204 

 

@app.route('/square_off_all_positions', methods=['GET', 'POST'])
def square_off_all_positions():

    index = request.args.get('index')
    helper_functions.square_off_all_positions(index)

    return '', 204

    


@app.route('/hold_atm', methods=['GET', 'POST']) 
def hold_atm():
    index = request.args.get('index')

    if shared_memory.dictionary[index]['HOLD_ATM']:  
        shared_memory.dictionary[index]['HOLD_ATM'] = False     

    elif not shared_memory.dictionary[index]['HOLD_ATM']:  
        shared_memory.dictionary[index]['HOLD_ATM'] = True

    return '', 204

@app.route('/increment_atm', methods=['GET', 'POST'])
def increment_atm():

    index = request.args.get('index')
    shared_memory.dictionary[index]['INCREMENT_ATM'] = True
    return '', 204

@app.route('/decrement_atm', methods=['GET', 'POST']) 
def decrement_atm():

    index = request.args.get('index')
    shared_memory.dictionary[index]['DECREMENT_ATM'] = True
    
    return '', 204

@app.route('/refresh_feed', methods=['GET', 'POST']) 
def refresh_feed():

    data.alice.subscribe(data.subscribe_list)
    return '', 204

@app.route('/')
def index():
    # return render_template('dy1.html') 
    return render_template('index.html',strategy_name= data.strategy)


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(message)s")
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    print(
        '********************************************** UPCOMING EXPIRIES *************************************************************')
   
    for index in data.indices:
        print(f"{index}: {data.expiries_dict[index]}") 

    print(f'Todays Colliding expiry:{data.colliding_expiries_instrument_list}') if len(data.colliding_expiries_instrument_list) > 1 else ''
    print(f'Todays expiry / Trading instrment :{data.todays_trading_instrument}')


    Socket.socket()
    time.sleep(2)

    for index in data.todays_trading_instrument:
        quantity = data.get_freeze_quantity(shared_memory.dictionary[index]['LP'])
        data.quantity_freeze_dict[index] = quantity
    

    print(
        "waiting for ATM at 9:30, current time- {}:{}".format(datetime.datetime.now(pytz.timezone('Asia/Kolkata')).hour,
                                                              datetime.datetime.now(
                                                                  pytz.timezone('Asia/Kolkata')).minute))

    
    ATM_dict = {}
    
    

    while True:
        current_time = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).time()
        
        if current_time.hour >= 9 and current_time.minute >= 27 and current_time.second >= 0:
           
            for index in data.todays_trading_instrument:

                atm = int(round(float(shared_memory.dictionary[index]["LP"]) / data.config[index]['Strike_difference']) * data.config[index]['Strike_difference'])
                ATM_dict[index] = atm

                quantity = data.get_freeze_quantity(shared_memory.dictionary[index]['LP'])
                data.quantity_freeze_dict[index] = quantity if data.config[index]['Exchange'] == 'NSE' else 1000

                
            print(f'ATM:{ATM_dict}')  
            print(f'QUANTITY FREEZE DICT:{data.quantity_freeze_dict}')
            break

    print("trying to resubcribe")
    
    subscribe_list_ = helper_functions.get_subscribe_list(ATM_dict)
    data.alice.subscribe(subscribe_list_)
    data.subscribe_list.extend(subscribe_list_)
    sleep(6)


    strategy_Initializer(strategy_name=data.strategy, atm_dict= ATM_dict )

    #thread_monitor_process = Process(target=thread_monitor)
    #thread_monitor_process.start()
   

    def run_app():
        
        app.run(host='0.0.0.0', port=5001, debug=False)

    #html['html'] = frontend.get_frontend_data_()
    frontend_process = Process(target=run_app)
    frontend_process.start()




    partial_square_off_all_positions = partial(helper_functions.square_off_all_positions, 'MARKET_CLOSING')
    schedule.every().day.at('15:28').do(partial_square_off_all_positions)
    while True:
            
        shared_dict['html'] = frontend.get_frontend_data_()
        #schedule.run_pending()
        time.sleep(0.5)
        


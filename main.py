from indodax import indodax as idx
from datetime import datetime
import json, time, requests, pprint
import telegram_send as ts


CONFIGURATION_DATA  = []
ASSET               = []
TOTAL_PERSEN        = []
BALANCE             = []


def conf():
    '''
    Mengambil konfigurasi API dari text file
    untuk digunakan pada fungsi-fungsi lain 
    yang ada dalam program
    '''
    # membuka file konfigurasi yang berisikan data konfigurasi API
    try:
        with open('conf.txt') as conf_file:
            conf_data   = conf_file.read()
        get_data    = json.loads(conf_data)
        key         = get_data['api_key']
        secret      = str.encode(get_data['secret_key'])
        stoploss    = get_data['sl']
        takeprofit  = get_data['tp']
        # tambahkan data dari file ke dalam list configuration data
        CONFIGURATION_DATA.append(key)
        CONFIGURATION_DATA.append(secret)
        CONFIGURATION_DATA.append(stoploss)
        CONFIGURATION_DATA.append(takeprofit)
    except Exception as error:
        print(error)
        return 0        


def check_balance():
    '''
    Mengambil active saldo yang ada pada akun Indodax
    Data ditampilkan dalam bentuk dictionary
    '''
    active  = {}
    conf_data   = CONFIGURATION_DATA
    key, secret = conf_data[0],conf_data[1]
    # otentikasi ke akun Indodax
    account     = idx(key, secret)
    time.sleep(2)

    try:
        account_info= json.loads(account.get_info())
        if account_info['success'] == 0:
            print(account_info['error'])
        else:
            # mengambil data active balance
            balance_active = account_info['return']['balance']
            for i in balance_active:
                if float(balance_active[i]) > 0:
                    if i != 'idr':
                        active[i] = balance_active[i]                        
    except Exception as error:
        print(error)

    return active


def check_price(n):
    '''
    Menggunakan publik API dari Indodax
    untuk mendapatkan data harga terbaru
    Output berupa dictionary    
    '''
    api_url     = 'https://indodax.com/api/summaries'
    get_data    = requests.get(api_url).json()
    tickers     = get_data['tickers'][n+'_idr']
    
    return tickers


def stoploss(asset, price, balance):
    '''
    Fungsi untuk melakukan stoploss pada active asset
    parameter yang dimasukan harus berupa data string
    '''
    key, secret = CONFIGURATION_DATA[0], CONFIGURATION_DATA[1]
    account     = idx(key, secret)
    try:
        sell_asset  = account.trade_sell(asset, price, balance)
    except Exception as error:
        print(error)


def run_bot():
    '''
    BOT akan dijalankan setelah user memilih
    active asset yang valid. 
    Output berupa nama asset dalam bentuk list
    '''
    active_asset        = check_balance()
    print('Informasi Pengaturan BOT\nNilai Stoploss =',CONFIGURATION_DATA[2]+'%\nNilai Takeprofit =',CONFIGURATION_DATA[3]+'%')
    print('-'*75)
    if bool(active_asset) == False:
        print('INFO! Tidak ada asset yang aktif')
        print('Untuk mulai menggunakan BOT, harus ada active asset dan pastikan aset tidak ada dalam orderbook')
        time.sleep(5)
        quit()
    else:
        for i in active_asset:
            print('Asset:',str.upper(i),'  / Saldo:',round(float(active_asset[i]),2),'  / Harga sekarang:',check_price(i)['last'],'  / Nilai IDR:',(round(float(active_asset[i]))*int(check_price(i)['last'])))
  

    # menampilkan inputan ke user untuk memasukan pilihan active asset
    while True:
        print('-'*75)
        user_input  = str.lower(input('\nMasukan nama aset: '))
        print('-'*75)
        if user_input not in active_asset:
            print('Asset yang dimasukan tidak ada dalam active asset!')
        else:             
            ASSET.append(user_input)
            balance = round(float(active_asset[user_input]),2)
            BALANCE.append(balance)
            break

    # menampilkan inputan ke user untuk memilih besaran balance yang ingin di stoploss
    while True:
        user_input  = input('\nTotal asset yang ingin dijaga oleh BOT (masukan angka tanpa tanda "%"): ')
        print('-'*75)
        try:
            data    = int(user_input)
            if data < 25 or data > 100:
                print('Angka yang dimasukan tidak boleh lebih kecil dari 25% atau lebih besar dari 100%')
            else:
                TOTAL_PERSEN.append(data)
                print('Please wait...')
                break
        except:
            print('Data harus berupa angka dan tanpa tanda "%"')


def buy_history():
    '''
    Fungsi mengembalikan data harga beli awal
    Dari asset yang dipilih oleh use
    output yang dihasilkan harga beli
    '''
    price_history   = [] # data yang masuk disini, bisa lebih dari satu
    key, secret     = CONFIGURATION_DATA[0], CONFIGURATION_DATA[1]
    account         = idx(key, secret)
    asset           = ASSET
    time.sleep(1)
    buy_price_history   = json.loads(account.order_history(asset[0]))['return']['orders']
    for i in buy_price_history:
        if i['type'] == 'buy':
            price_history.append(i['price'])
            break

    return price_history
    

def compare_price():
    asset       = ASSET[0]
    order_price = buy_history() # data order beli
    time.sleep(0.5) 
    sl          = int(CONFIGURATION_DATA[2])
    tp          = int(CONFIGURATION_DATA[3])

    a           = 100 # nilai acuan untuk masuk kondisi a != b

    while True:
        get_price       = check_price(asset)
        last_price      = int(get_price['last'])
        bid_price       = int(get_price['buy'])
        p_change        = 0
        now = datetime.now()
        log_time_full   = now.strftime("%d/%m/%Y %H:%M:%S")
        log_time        = now.strftime("%H:%M:%S")
        # masuk ke kondisi jika ada pembelian dengan harga berbeda dengan harga beli terakhir
        if len(order_price) > 1: 
            order_price_all = []
            for i in order_price:
                order_price_all.append(int(i))
            x   = len(order_price) 
            y   = sum(order_price_all)
            average_order_price = y/x
            p_change = (last_price - average_order_price) / last_price * 100
        else:
            p_change = (last_price - int(order_price[0])) / last_price * 100

        # semua format pesan dibawah ini
        when_price_change   = '# '+str(log_time)+' > '+str.upper(asset)+' | Harga awal/checkpoint: '+order_price[0]+' | Harga sekarang: '+str(last_price)+' | Perubahan: '+str(round(p_change,1))+'%'
        when_price_up       = 'Harga naik menyentuh nilai TP, naik '+str(round(p_change,1))+'% dari harga beli/checkpoint'
        when_price_down     = 'Harga turun menyentuh nilai SL, turun '+str(round(p_change,1))+'% dari harga beli/checkpoint'


        if p_change <= sl:
            print(when_price_down)
            
            # force sell
            market_sell     = bid_price - (5*bid_price/100)
            market_sell     = str(round(market_sell))

            # total balance yang akan dijual
            bl      = float(BALANCE[0])
            tpj     = int(TOTAL_PERSEN[0])
            total   = (tpj * bl) / 100
            balance = round(total,2)

            #laksanakan perintah stoploss
            # stoploss(asset, market_sell, balance)
            print('Berhasil terjual')
            break
        if p_change >= tp:
            order_price = [str(last_price)]
            print(when_price_up)
        else:
            b = round(p_change,1)
            if b != a:
                a = b
                print(when_price_change)
            time.sleep(5) # jeda sebelum balik ke looping dan melakukan request baru

       
def menu():
    print('='*48)
    print('\tNaraBOT Indodax Stoploss v 0.1')
    print('='*48+'\n')
    print('Checking configuration file...')
    if conf() == 0:
        print('Mohon periksa file konfigurasi di conf.txt')
        time.sleep(5)
    else:  
        run_bot()
        compare_price()

menu()












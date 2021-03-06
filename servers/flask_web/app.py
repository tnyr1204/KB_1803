#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from influxdb import InfluxDBClient
from pytz import timezone
from datetime import datetime

from flask import Flask, jsonify, request, render_template, make_response
import json
import calc
app = Flask(__name__)

# "/api"で起動するアプリ:書き込み
@app.route("/api", methods=['GET'])
def sensor_request_api():
    # リクエストの引数から，各センサ値を抽出
    params = request.args
    wetness = params.get('wetness', default='0', type = str)
    dryness = (float(wetness) / 4095.0) * 100.0
    temperature = params.get('temperature', default='0', type = str)
    humidity = params.get('humidity', default='0', type = str)
    co2 = params.get('co2', default='0', type = str)
    tvoc = params.get('tvoc', default='0', type = str)

    # 乾くまでの残り時間を計算
    rest_of_time = calc.calc(dryness, temperature, humidity)

    # センサ値と計算値をinfluxDBに書き込む
    write(dryness, temperature, humidity, co2, tvoc, rest_of_time)

    # 完了したで
    return 'success'###"wetness" + wetness + " temperature:" + temperature + " humidity" + humidity + " co2" + co2 + " tvoc:" + tvoc

# "/"で起動するアプリ:読み出し
@app.route("/", methods=['GET'])
def index():
    client = InfluxDBClient(host='influxdb', port=8086, database='superdry')
    sensordata = client.query("select * from sensordata where time >= now() - 30m")

    sensordata_json2list = list(sensordata.get_points(measurement=None))

    # 要素の有無
    if len(sensordata_json2list) == 0:
        #return str("過去%s分間のデータがありません" % str(minutes))
        datalist = [0.0,0.0,0.0,0.0,0.0,0.0]
        return "error"
    else:
        # リストから最新の要素を取り出す
        sensordata_dict = sensordata_json2list[-1]
        # キー
        keys = list(sensordata_dict.keys())
        # 値
        values = list(sensordata_dict.values())

        # 取ってきた値を変数に代入()
        dryness = (int(sensordata_dict['dryness']))
        temperature = int(float(sensordata_dict['temperature']) / 100.0)
        co2 = int(sensordata_dict['co2'])
        humidity = int(sensordata_dict['humidity'])
        tvoc = int(sensordata_dict['tvoc'])
        rest_of_time = int(sensordata_dict['rest_of_time'])
        time = sensordata_dict['time']

        return render_template('index.html', dryness=dryness, temperature=temperature, humidity=humidity, rest_of_time=rest_of_time)

# influxDBにデータを書き込む関数
def write(dryness, temperature, humidity, co2, tvoc, rest_of_time):

    utc_now = datetime.now(timezone('UTC'))
    jst_now = utc_now.astimezone(timezone('Asia/Tokyo'))
    host='influxdb'
    port=8086
    user = 'root'
    password = 'root'
    dbname = 'superdry'
    json_body = [
        {
            "measurement": "sensordata",
            "tags": {
                "user": "umetsu",
                "id": "0"},
            "time": str(jst_now),
            "fields": {
                "dryness": dryness,
                "temperature": temperature,
                "humidity": humidity,
                "co2": co2,
                "tvoc": tvoc,
                "rest_of_time": rest_of_time
            }
        }
    ]

    print("client: ",host, port, user, password, dbname)
    client = InfluxDBClient(host, port, user, password, dbname)
    client.create_database(dbname)
    client.write_points(json_body)

    return "write"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6500, debug=True)

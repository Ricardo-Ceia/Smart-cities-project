from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash, Response
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from flask_cors import CORS
from typing import List, Dict
from werkzeug.security import generate_password_hash, check_password_hash
import io
import csv


app = Flask(__name__)
CORS(app)
app.secret_key = 'test'

users = {
    'admin': generate_password_hash('admin123')
}

# InfluxDB configuration
INFLUXDB_URL = "https://eu-central-1-1.aws.cloud2.influxdata.com"
INFLUXDB_TOKEN = "pnHl2KOX92zF2cLyVNhoI6EW9dRlBb1FJhIyVK2XdwUDvXTjmv6ool8SObJbcOlo-2uA3bYUT-Wu27faFOG2kg=="
INFLUXDB_ORG = "Isel"
INFLUXDB_BUCKET = "bucket1"

def to_flux_time(dt_str):
    dt = datetime.fromisoformat(dt_str)
    dt -= timedelta(hours=1)  # Subtrai 1 hora
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + "Z"

def query_influxdb(variable, start_timestamp, end_timestamp):
    """Query InfluxDB for sound level data."""
    # Convert timestamps to RFC3339 format
    start = datetime.fromtimestamp(start_timestamp / 1000).isoformat() + "Z"
    end = datetime.fromtimestamp(end_timestamp / 1000).isoformat() + "Z"
    
    # Map frontend variable names to database field names
    
    field = variable

    query = f'''from(bucket: "bucket1")
            |> range(start: {start}, stop: {end})
            |> filter(fn: (r) => r._measurement == "sound_level" and r._field == "{field}")
    '''

    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()
    result = query_api.query(org=INFLUXDB_ORG, query=query)

    data = []
    for table in result:
        for record in table.records:
            data.append({
                "time": record.get_time(),
                "value": record.get_value()
            })

    return data

@app.route('/api/get_data_for_calculation', methods=['POST'])
def get_data_for_calculation():
    data = request.get_json()
    start_ts = int(data['start_timestamp'])
    end_ts = int(data['end_timestamp'])
    sensor_id = str(data['sensors'])  
    start_time = datetime.utcfromtimestamp(start_ts / 1000).isoformat() + "Z"
    end_time = datetime.utcfromtimestamp(end_ts / 1000).isoformat() + "Z"

    variables = ["LAeq", "LAFmin", "LAFmax", "LCpeak","LAEA"]
    response_data = {var: [] for var in variables}

    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        for var in variables:
            query = f'''
                from(bucket: "{INFLUXDB_BUCKET}")
                |> range(start: time(v: "{start_time}"), stop: time(v: "{end_time}"))
                |> filter(fn: (r) => r._measurement == "sound_level")
                |> filter(fn: (r) => r._field == "sensor_id" or r._field == "{var}")
                |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> filter(fn: (r) => r.sensor_id == "{sensor_id}")
                |> keep(columns: ["_time", "{var}"])
                |> rename(columns: {{"{var}": "_value"}})
            '''

            tables = query_api.query(org=INFLUXDB_ORG, query=query)

            for table in tables:
                for record in table.records:
                    response_data[var].append({
                        'time': record.get_time().isoformat(),
                        'value': record.get_value()
                    })
        return jsonify(response_data)

    except Exception as e:
        print("Error on get_data_calculation:",str(e))
        return jsonify({'error': str(e)}), 500

@app.route("/api/lden_data", methods=["POST"])
def get_lden_data():
    data = request.get_json()
    sensor_id = str(data.get("sensor"))  # como field, pode ser número
    start_timestamp = int(data.get("start_timestamp"))  # em ms


    print(f"sensor_id:{sensor_id}")
    print(f"start_timestamp:{start_timestamp}")
    start_dt = datetime.utcfromtimestamp(start_timestamp / 1000)
    next_day = start_dt + timedelta(days=1)

    # Períodos de Lden
    periods = {
        "Lday": (start_dt.replace(hour=7, minute=0, second=0), start_dt.replace(hour=19, minute=0, second=0)),
        "Levening": (start_dt.replace(hour=19, minute=0, second=0), start_dt.replace(hour=23, minute=0, second=0)),
        "Lnight": (start_dt.replace(hour=23, minute=0, second=0), next_day.replace(hour=7, minute=0, second=0))
    }

    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()
    results = {}

    for label, (start, end) in periods.items():
        start_str = start.isoformat() + "Z"
        end_str = end.isoformat() + "Z"
        print(start_str)
        print(end_str)
        # Usa pivot para permitir filtrar por sensor_id que é um campo (_field)
        query = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: {start_str}, stop: {end_str})
            |> filter(fn: (r) => r._measurement == "sound_level")
            |> filter(fn: (r) => r._field == "sensor_id" or r._field == "LAEA")
            |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> filter(fn: (r) => r.sensor_id == "{sensor_id}")
            |> keep(columns: ["_time", "LAEA"])
            |> rename(columns: {{"LAEA": "_value"}})
        '''

        try:
            tables = query_api.query(org=INFLUXDB_ORG, query=query)
            values = []

            for table in tables:
                for record in table.records: 
                    values.append(record.get_value())

            results[label] = values

        except Exception as e:
            print(f"Erro ao consultar {label}: {e}")
            results[label] = []
    print(f"Lday:{results['Lday'][0:10]}")
    print(f"Levening:{results['Levening'][0:10]}")
    print(f"Lnight:{results['Lnight'][0:10]}")

    return jsonify(results)

@app.route('/events',methods=['GET'])
def events():
    return render_template("events.html")


@app.route('/api/sensor-events', methods=['POST'])
def api_sensor_events():
    data = request.json
    start = int(data["start_date"])
    end = int(data["end_date"])
    start = datetime.utcfromtimestamp(start / 1000).isoformat()+'Z'
    end = datetime.utcfromtimestamp(end / 1000).isoformat()+'Z'
    print(f"start{start},stopt:{end}")
    client = InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG,
        timeout=60000
    )

    query_api = client.query_api()

    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
    |> range(start: {start}, stop: {end})
    |> filter(fn: (r) =>
        r._measurement == "sound_level" and
        (r._field == "EventDetect" or r._field == "LCpeak" or
        r._field == "EventType1" or r._field == "EventType2" or r._field == "EventType3" or
        r._field == "EventType4" or r._field == "EventType5" or r._field == "EventType6" or
        r._field == "EventType7" or r._field == "EventType8" or r._field == "EventType9" or
        r._field == "EventType10")
    )
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> keep(columns: ["_time", "EventDetect", "LCpeak", "EventType1", "EventType2", "EventType3", "EventType4", "EventType5", "EventType6", "EventType7", "EventType8", "EventType9", "EventType10"])
    |> sort(columns: ["_time"])
    '''


    tables = query_api.query(query)
    print(f"tables:{tables}")
    rows = []

    for table in tables:
        for record in table.records:
            r = record.values
            rows.append({
                "timestamp": r["_time"],
                "EventDetect": int(r.get("EventDetect", 0)),
                "LCpeak": float(r.get("LCpeak", 0)),
                **{f"EventType{i}": float(r.get(f"EventType{i}", 0)) for i in range(1, 11)}
            })


    # Agrupamento por eventos contínuos com EventDetect == 10
    eventos = []
    evento_atual = []

    for row in rows:
        if row["EventDetect"] == 10:
            evento_atual.append(row)
        elif evento_atual:
            eventos.append(evento_atual)
            evento_atual = []
    if evento_atual:
        eventos.append(evento_atual)

    resultado = []

    for evento in eventos:
        start_time = evento[0]["timestamp"]
        end_time = evento[-1]["timestamp"]
        duration = (end_time - start_time).total_seconds()
        max_lcpeak = max(evento, key=lambda x: x["LCpeak"])["LCpeak"]

        # Calcular a média de cada EventType
        event_type_means = {}
        for i in range(1, 11):
            key = f"EventType{i}"
            values = [row.get(key, 0.0) for row in evento]
            avg_value = sum(values) / len(values) if values else 0.0
            event_type_means[key] = avg_value

        # Determinar o EventType com maior média
        event_type_max, event_type_max_value = max(event_type_means.items(), key=lambda x: x[1])

        resultado.append({
            "inicio": start_time.isoformat(),
            "fim": end_time.isoformat(),
            "duracao_segundos": duration,
            "max_lcpeak": max_lcpeak,
            "event_type_max": event_type_max,
            "event_type_max_value": event_type_max_value
        })


    print(f"resultado: {resultado}")
    return jsonify(resultado)

@app.route('/')
def home():
    """Render the home page."""
    return render_template('homepage.html')

@app.route('/api/get_data', methods=['POST'])
def api_get_data():
    """API endpoint to get sound level data."""
    data = request.json
    variable = data['variable']
    start_timestamp = data['start_timestamp']
    end_timestamp = data['end_timestamp']

    influx_data = query_influxdb(variable, start_timestamp, end_timestamp)
    return jsonify(influx_data)



@app.route('/live_monitor')
def live_monitor():
    return render_template('live_monitor.html')

@app.route('/interval_monitor')
def interval_monitor():
    return render_template('interval_monitor.html')

@app.route('/display-mode', methods=['GET', 'POST'])
def display_mode():
    if request.method == 'POST':
        # Se for JSON (primeira opção)
        if request.is_json:
            data = request.get_json()
            sensor = data.get('sensor')
            parameter = data.get('parameter', 'LAEA')
            interval = data.get('interval', '5m')
        else:
            # Se for form data (segunda opção)
            sensor = request.form.get('sensor')
            parameter = request.form.get('parameter', 'LAEA')
            interval = request.form.get('interval', '5m')
    else:
        # GET request
        sensor = request.args.get('sensor')
        parameter = request.args.get('parameter', 'LAEA')
        interval = request.args.get('interval', '5m')
    
    # Validação
    if not sensor:
        return "Sensor não especificado", 400
    
    return render_template('display-mode.html', 
                         sensor=sensor, 
                         parameter=parameter, 
                         interval=interval)

def validate_date(date_str):
    """Validate the provided date string."""
    if not date_str:
        return False, "Date is required"
    
    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        current_time = datetime.now()
        
        if date > current_time:
            return False, "Date cannot be in the future"
        
        if current_time - date > timedelta(days=30):
            return False, "Date must be within the last 30 days"
            
        return True, None
    except ValueError:
        return False, "Invalid date format"

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and check_password_hash(users[username], password):
            session['user'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Credenciais inválidas', 'danger')
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('admin_login'))
    return render_template("admin_dashboard.html")


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('admin_login'))

def freq_key(col):
    try:
        # extrai o número da frequência
        return int(col.replace('_HZ', '').replace('_', '').replace('.', ''))
    except Exception:
        return 10**9  # colunas que não são frequência ficam no fim

@app.route('/download_csv')
def download_csv():
    start_raw = request.args.get('start')  
    end_raw = request.args.get('end')      
    print("1",start_raw)
    print("2",end_raw)
    if not start_raw or not end_raw:
        return "Falta o intervalo de tempo.", 400

    start = to_flux_time(start_raw)
    end = to_flux_time(end_raw)

    flux_query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: {start}, stop: {end})
      |> filter(fn: (r) => r._measurement == "sound_level")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    print("query_test",flux_query)
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()
    tables = query_api.query(flux_query)

    output = io.StringIO()
    writer = csv.writer(output)

    # Colunas fixas que sempre queremos no começo
    fixed_columns = ['_time', 'sensor_id']
    # Métricas que devem vir logo após fixed_columns (coloque aqui todas as métricas que quiser)
    metric_columns = [
        'LAEA', 'LAEA_SLOW_EVENT', 'LAFmax', 'LAFmaxT', 'LAFmin', 'LAFminT', 'LAeq',
        'LCpeak', 'LCpeakT'
    ]

    # Armazenar linhas para processar depois
    rows = []
    all_columns = set()

    for table in tables:
        for record in table.records:
            values = record.values.copy()
            # Remover colunas indesejadas
            if 'result' in values:
                values.pop('result')
            if 'measurement' in values:
                values.pop('measurement')
            # Armazenar colunas e linhas
            all_columns.update(values.keys())
            rows.append(values)

    # Remove duplicados e mantém ordem de fixed + métricas + frequências ordenadas + outras colunas restantes
    all_columns = list(all_columns)
    # Separar colunas de frequência
    freq_columns = [c for c in all_columns if c.endswith('_HZ')]
    other_columns = [c for c in all_columns if c not in freq_columns]

    # Ordenar frequências numericamente
    freq_columns.sort(key=freq_key)

    # Garantir que fixed e metric colunas venham primeiro (se estiverem presentes)
    ordered_columns = []
    for col in fixed_columns:
        if col in other_columns:
            ordered_columns.append(col)
    for col in metric_columns:
        if col in other_columns and col not in ordered_columns:
            ordered_columns.append(col)
    # Adicionar demais colunas que não sejam fixed/metrics/frequencies
    for col in other_columns:
        if col not in ordered_columns:
            ordered_columns.append(col)
    # Finalmente as frequências ordenadas
    ordered_columns.extend(freq_columns)

    # Escrever header
    writer.writerow(ordered_columns)

    # Escrever linhas ordenando as colunas conforme o header
    for row in rows:
        writer.writerow([row.get(col, '') for col in ordered_columns])

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=sound_data.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True)
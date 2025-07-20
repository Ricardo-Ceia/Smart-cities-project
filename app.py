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
def get_sensor_events():
    """
    Rota para obter eventos de sensores num período específico.
    
    Payload esperado:
    {
        "sensor_id": "string",
        "start_date": "2025-07-17T00:00:00Z",
        "end_date": "2025-07-18T23:59:59Z"
    }
    """
    try:
        data = request.get_json()
        sensor_id = data.get('sensor_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        print(f"data:{data}")
        if not all([sensor_id, start_date, end_date]):
            return jsonify({"error": "sensor_id, start_date e end_date são obrigatórios"}), 400
        
        # Buscar dados da base de dados
        events_data = fetch_sensor_events(sensor_id, start_date, end_date)
        #print(f"events_data:{events_data}")
        # Agrupar eventos contínuos
        grouped_events = group_continuous_events(events_data)
        
        return jsonify(grouped_events)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def fetch_sensor_events(sensor_id: str, start_date: str, end_date: str) -> List[Dict]:
    """
    Busca eventos da base de dados onde EventDetect = 1 usando Flux.
    """
    # Query Flux para buscar eventos
    flux_query = f'''
                    from(bucket: "{INFLUXDB_BUCKET}")
                    |> range(start: {start_date}, stop: {end_date})
                    |> filter(fn: (r) => r["_measurement"] == "sound_level")
                    |> filter(fn: (r) => r["_field"] == "sensor_id" or
                                        r["_field"] == "EventDetect" or 
                                        r["_field"] == "EventType1" or 
                                        r["_field"] == "EventType2" or 
                                        r["_field"] == "EventType3" or 
                                        r["_field"] == "EventType4" or 
                                        r["_field"] == "EventType5" or 
                                        r["_field"] == "EventType6" or 
                                        r["_field"] == "EventType7" or 
                                        r["_field"] == "EventType8" or 
                                        r["_field"] == "EventType9" or 
                                        r["_field"] == "EventType10" or 
                                        r["_field"] == "LCpeak")
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                    |> filter(fn: (r) => r["EventDetect"] == 1.0)
                    |> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")
                    |> sort(columns: ["_time"])
                '''
    
    # Conectar ao InfluxDB
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()
    
    try:
        # Executar query
        result = query_api.query(flux_query)
        # Processar resultados
        events_by_time = {}
        
        for table in result:
            for record in table.records:
                values = record.values
                time_key = values.get('_time').isoformat()

                events_by_time[time_key] = {
                    'time': time_key,
                    'EventDetect': values.get('EventDetect', 0),
                    'EventType1': values.get('EventType1', 0),
                    'EventType2': values.get('EventType2', 0),
                    'EventType3': values.get('EventType3', 0),
                    'EventType4': values.get('EventType4', 0),
                    'EventType5': values.get('EventType5', 0),
                    'EventType6': values.get('EventType6', 0),
                    'EventType7': values.get('EventType7', 0),
                    'EventType8': values.get('EventType8', 0),
                    'EventType9': values.get('EventType9', 0),
                    'EventType10': values.get('EventType10', 0),
                    'LCpeak': values.get('LCpeak', 0)
                }
        # Converter para lista ordenada por tempo
        events = list(events_by_time.values())
        #print(f"events{events}")
        events.sort(key=lambda x: x['time'])
        
        return events
        
    finally:
        client.close()

def group_continuous_events(events_data: List[Dict]) -> List[Dict]:
    """
    Agrupa eventos contínuos em períodos.
    """
    if not events_data:
        return []
    
    grouped_events = []
    current_event = None
    
    for event in events_data:
        event_time = datetime.fromisoformat(event['time'].replace('Z', '+00:00'))
        
        # Coletar valores dos EventTypes
        event_types = {}
        for i in range(1, 11):  # EventType1 a EventType10
            event_types[f'EventType{i}'] = event.get(f'EventType{i}', 0)
        
        if current_event is None:
            # Início de um novo evento
            current_event = {
                "start_time": event['time'],
                "end_time": event['time'],
                "event_types": [event_types],
                "lcpeak_values": [event.get('LCpeak', 0)]
            }
        else:
            # Verificar se é continuação do evento atual
            prev_time = datetime.fromisoformat(current_event['end_time'].replace('Z', '+00:00'))
            time_diff = (event_time - prev_time).total_seconds() * 1000
            
            if time_diff <= 200:  # Gap máximo de 200ms para considerar o mesmo evento
                # Continuar evento atual
                current_event['end_time'] = event['time']
                current_event['event_types'].append(event_types)
                current_event['lcpeak_values'].append(event.get('LCpeak', 0))
            else:
                # Finalizar evento atual e começar novo
                grouped_events.append(current_event)
                
                # Começar novo evento
                current_event = {
                    "start_time": event['time'],
                    "end_time": event['time'],
                    "event_types": [event_types],
                    "lcpeak_values": [event.get('LCpeak', 0)]
                }
    
    # Adicionar último evento se existir
    if current_event:
        grouped_events.append(current_event)
    
    return grouped_events



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
from flask import Flask, render_template, request
from datetime import datetime,timedelta

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('homepage.html')

@app.route('/select-variables', methods=['GET'])
def select_variables_get():
    return render_template("select-variables.html")

@app.route('/select-variables', methods=['POST'])
def select_variables_post():
    variable = request.form.get('variable')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    
    date_is_valid,invalid_date_message = validate_date(start_date_str)

    if date_is_valid:

        if start_date_str:
            if '.' not in start_date_str:
                start_date_str += ":00.000"  
            start_date = datetime.strptime(start_date_str, "%Y-%m-%dT%H:%M:%S.%f")

        if end_date_str:
            if '.' not in end_date_str:
                end_date_str += ":00.000"  
            end_date = datetime.strptime(end_date_str, "%Y-%m-%dT%H:%M:%S.%f")

        if start_date:
            start_timestamp = int(start_date.timestamp() * 1000) 
        if end_date:
            end_timestamp = int(end_date.timestamp() * 1000)  

        return render_template('select-variables.html', variable=variable, start_timestamp=start_timestamp, end_timestamp=end_timestamp)

    return render_template('select-variables.html', variable=variable,invalid_date_message=invalid_date_message)
    
    

def validate_date(start_date):
    start_date = datetime.fromisoformat(start_date)
    current_time = datetime.now()
    time_difference = current_time - start_date
    print(time_difference)
    if time_difference >= timedelta(days=30):
        return False,"Start date be within the last 30 days"
    if start_date > current_time:
        return False,"Start date cannot be in the future"
    return True,None


if __name__ == '__main__':
    app.run(debug=True)  
from flask import Flask, render_template, request, send_file, redirect, url_for, flash , Response
from flask_bootstrap import Bootstrap
import pandas as pd
from unidecode import unidecode
import re
from io import BytesIO
from datetime import datetime
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)


Bootstrap(app)

def count_words(dialogos):
    words = []
    for dialogo in dialogos:
        words += dialogo.split()
    return len(words)


@app.route('/')

def index():
    fecha_actual = datetime.now().strftime('%d/%m/%Y')
    try:
        return render_template('index.html', fecha_actual=fecha_actual)
    except Exception as e:
        return "Ha ocurrido un error: {}".format(str(e))

@app.route('/', methods=['POST'])

def upload_file():
    fecha_actual = datetime.now().strftime('%d/%m/%Y')
    try:
        file = request.files['file']
        if not file:
            return render_template('index.html', error='No se seleccionó archivo')

        #df = pd.read_excel(file)
        df = pd.read_excel(file, sheet_name='SCRIPT', )

        # Verificar si la columna 'T.C' existe
        if 'T.C' not in df.columns:
            flash('Formato Incorrecto: El archivo debe contener una columna llamada: T.C', 'error')
            return redirect(url_for('index'))

        # Verificar si la columna 'PERSONAJE' existe
        if 'PERSONAJE' not in df.columns:
            flash('Formato Incorrecto: El archivo debe contener una columna llamada: PERSONAJE', 'error')
            return redirect(url_for('index'))

        # Verificar si la columna 'DIÁLOGO' existe
        if 'DIÁLOGO' not in df.columns:
            # Verificar si la columna 'DIALOGO' existe
            if 'DIALOGO' in df.columns:
                # Renombrar 'DIALOGO' a 'DIÁLOGO'
                df = df.rename(columns={'DIALOGO': 'DIÁLOGO'})
            else:
                flash('Formato Incorrecto: El archivo debe contener una columna llamada DIÁLOGO o DIALOGO', 'error')
                return redirect(url_for('index'))

        # Verificar celdas vacías en la columna T.C
        if df['T.C'].isnull().values.any():
            flash('El archivo no puede tener celdas vacías en la columna T.C', 'error')
            return redirect(url_for('index'))

        # Verificar celdas vacías en la columna PERSONAJE
        if df['PERSONAJE'].isnull().values.any():
            flash('El archivo no puede tener celdas vacías en la columna PERSONAJE', 'error')
            return redirect(url_for('index'))

        # Verificar celdas vacías en la columna DIÁLOGO
        #if df['DIÁLOGO'].isnull().values.any():
            #flash('El archivo no puede tener celdas vacías en la columna DIÁLOGO', 'error')

        # Verificar celdas vacías en la columna DIÁLOGO
        if df['DIÁLOGO'].isnull().values.any():
            flash('El archivo no puede tener celdas vacías en la columna DIÁLOGO', 'error')
            return redirect(url_for('index'))

        df = df.applymap(lambda x: unidecode(str(x)))

        # Eliminar espacios en blanco en la columna "PERSONAJE"
        df['PERSONAJE'] = df['PERSONAJE'].str.strip()

        # Eliminar caracteres especiales, palabras '(REAC)' y '(REACS)', signos de admiración e interrogación
        #df = df.applymap(lambda x: x.replace('(REAC)', '').replace('(REACS)', '').strip())
        df = df.applymap(lambda x: re.sub(r'[^\w\s]', '', x))
        df = df.applymap(lambda x: x.replace('!', '').replace('?', ''))

        # Agrupar diálogos por personaje y eliminar personajes duplicados
        df = df.groupby('PERSONAJE')['DIÁLOGO'].apply(list).reset_index()
        df = df.rename(columns={'DIÁLOGO': 'DIALOGOS'})

        # Contar palabras en los diálogos y agregar columna al DataFrame
        df['CANTIDAD_PALABRAS'] = df['DIALOGOS'].apply(count_words)
        df = df.sort_values(by='CANTIDAD_PALABRAS', ascending=False).reset_index(drop=True)

        # Eliminar espacios en blanco en la columna 'PERSONAJE'
        df['PERSONAJE'] = df['PERSONAJE'].str.strip()

        # Cambiar las tildes en el JSON generado
        json = df.to_json(orient='records', force_ascii=False)

        # Crear una tabla HTML de pandas para mostrar los resultados
        #tabla_html = df[['PERSONAJE', 'CANTIDAD_PALABRAS']].to_html(index=False)
        tabla_html = df[['PERSONAJE', 'CANTIDAD_PALABRAS']].to_html(index=False,classes='table table-striped table-bordered')

        # Agregar el HTML generado al contexto para que se pueda mostrar en la plantilla
        return render_template('index.html', tabla_html=tabla_html, table_classes="table table-striped table-bordered", json=json, fecha_actual=datetime.now().strftime('%d/%m/%Y'))

    except Exception as e:
        return render_template('index.html', error='Error: {}'.format(str(e)))

@app.route('/download')
def download():
    try:
        tabla_html = request.args.get('tabla_html', None)
        df = pd.read_html(tabla_html)[0]
        csv_buffer = df.to_csv(index=False).encode('utf-8')
        return send_file(
            BytesIO(csv_buffer),
            mimetype='text/csv',
            as_attachment=True,
            download_name='tabla.csv'
        )
    except Exception as e:
        return "Error al descargar el archivo: {}".format(str(e))

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error=error)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

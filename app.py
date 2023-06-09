from flask import Flask, render_template, request, send_file, redirect, url_for, flash, Response, make_response
from flask_bootstrap import Bootstrap
import pandas as pd
from unidecode import unidecode
import re
from io import BytesIO
from datetime import datetime
import secrets
import string

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
        if df['DIÁLOGO'].isnull().values.any():
            flash('El archivo no puede tener celdas vacías en la columna DIÁLOGO', 'error')
            return redirect(url_for('index'))

        df = df.applymap(lambda x: unidecode(str(x)))

        # Eliminar espacios en blanco en la columna "PERSONAJE"
        df['PERSONAJE'] = df['PERSONAJE'].str.strip()

        # Eliminar caracteres especiales, palabras '(REAC)' y '(REACS)', signos de admiración e interrogación
        # df = df.applymap(lambda x: x.replace('(REAC)', '').replace('(REACS)', '').strip())
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
        # tabla_html = df[['PERSONAJE', 'CANTIDAD_PALABRAS']].to_html(index=False)
        tabla_html = df[['PERSONAJE', 'CANTIDAD_PALABRAS']].to_html(index=False,
                                                                    classes='table table-striped table-bordered')

        # Agregar el HTML generado al contexto para que se pueda mostrar en la plantilla
        return render_template('index.html', tabla_html=tabla_html, table_classes="table table-striped table-bordered",
                               json=json, fecha_actual=datetime.now().strftime('%d/%m/%Y'))

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


def get_column_label(index):
    alphabet = string.ascii_uppercase
    label = ""
    while index >= 0:
        label = alphabet[index % 26] + label
        index = index // 26 - 1
    return label


@app.route('/validar', methods=['GET', 'POST'])
def validar():
    fecha_actual = datetime.now().strftime('%d/%m/%Y')
    if request.method == 'POST':
        # Verificar si se ha enviado un archivo
        if 'file' not in request.files:
            raise Exception('No se ha enviado ningún archivo.')

        file = request.files['file']

        # Verificar si el archivo tiene un nombre y es un archivo Excel
        if file.filename == '':
            raise Exception('No se ha seleccionado ningún archivo.')

        if not file.filename.endswith('.xlsx'):
            raise Exception('El archivo debe tener formato .xlsx.')

        # Leer el archivo Excel usando pandas
        try:
            df = pd.read_excel(file)
        except Exception as e:
            raise Exception(f'Error al leer el archivo: {str(e)}')

        # Obtener las celdas vacías y generar una lista con su ubicación en formato "columna-fila"
        empty_cells = []
        count_empty_cells = 0  # Contador de celdas vacías

        for index, row in df.iterrows():
            for col in df.columns:
                value = row[col]
                if pd.isnull(value):
                    if isinstance(col, int):
                        label = get_column_label(col)
                    else:
                        label = col
                    empty_cells.append(f'{label}-{index + 2}')
                    count_empty_cells += 1

                    # Verificar si se han encontrado más de 1000 celdas vacías
                    if count_empty_cells > 1000:
                        raise Exception(
                            'El archivo contiene más de 1000 celdas vacías. Se recomienda copiar el contenido del archivo a uno nuevo.')

        if count_empty_cells == 0:
            success_message = 'Validación exitosa: el archivo no contiene celdas vacías.'
            empty_cells = None
        else:
            success_message = None

        return render_template('resultado.html', empty_cells=empty_cells, success_message=success_message,
                               fecha_actual=datetime.now().strftime('%d/%m/%Y'))

    return render_template('validar.html', fecha_actual=datetime.now().strftime('%d/%m/%Y'))


@app.errorhandler(Exception)
def handle_error(error):
    # Obtener el mensaje de error
    error_message = str(error)

    # Renderizar la plantilla de error
    return render_template('error.html', error_message=error_message), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

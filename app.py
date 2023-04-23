from flask import Flask, render_template, request, send_file, redirect, url_for, Response
from flask_bootstrap import Bootstrap
import pandas as pd
from unidecode import unidecode
import re
from io import BytesIO



def count_words(dialogos):
    words = []
    for dialogo in dialogos:
        words += dialogo.split()
    return len(words)

app = Flask(__name__)
Bootstrap(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def upload_file():
    file = request.files['file']
    if not file:
        return render_template('index.html', error='No se seleccionó archivo')

    df = pd.read_excel(file)

    # Eliminar caracteres especiales, palabras '(REAC)' y '(REACS)', signos de admiración e interrogación
    df = df.applymap(lambda x: unidecode(str(x)))
    df = df.applymap(lambda x: x.replace('(REAC)', '').replace('(REACS)', '').strip())
    df = df.applymap(lambda x: re.sub(r'[^\w\s]', '', x))
    df = df.applymap(lambda x: x.replace('!', '').replace('?', ''))

    # Agrupar diálogos por personaje y eliminar personajes duplicados
    df = df.groupby('PERSONAJE')['DIALOGO'].apply(list).reset_index()
    df = df.rename(columns={'DIALOGO': 'DIALOGOS'})

    # Contar palabras en los diálogos y agregar columna al DataFrame
    df['CANTIDAD_PALABRAS'] = df['DIALOGOS'].apply(count_words)

    # Cambiar las tildes en el JSON generado
    json = df.to_json(orient='records', force_ascii=False)

    # Crear una tabla HTML de pandas para mostrar los resultados
    tabla_html = df[['PERSONAJE', 'CANTIDAD_PALABRAS']].to_html(index=False)

    # Agregar el HTML generado al contexto para que se pueda mostrar en la plantilla
    return render_template('index.html', tabla_html=tabla_html, table_classes="table table-striped", json=json)

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

if __name__ == '__main__':
    app.run()

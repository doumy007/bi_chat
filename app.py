import os, re
from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter
from db_config import DB_CONFIG, OPENAI_API_KEY

app = Flask(__name__)

# 1. Conexión a Base de Datos
db_uri = f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
try:
    engine = create_engine(db_uri, connect_args={'connect_timeout': 30}, pool_pre_ping=True)
    # Filtramos solo las tablas necesarias para mantener el consumo de tokens bajo
    db = SQLDatabase(engine, schema=DB_CONFIG['database'], include_tables=['Campaigns', 'Dashboard'])
    print(f"✅ Tablas listas: {db.get_usable_table_names()}")
except Exception as e:
    print(f"❌ Error DB: {e}")
    db = None

# 2. Lógica de Limpieza de SQL (Evita el error de las comillas ```sql)
def clean_sql_query(query):
    # Elimina bloques de código Markdown y espacios extra
    query = query.replace("```sql", "").replace("```", "").strip()
    return query

# 3. Configuración de IA
if db:
    llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=OPENAI_API_KEY, temperature=0)

    # Generador de SQL Estricto
    sql_prompt = PromptTemplate.from_template(
        """Eres un generador de SQL para MySQL.
        Tablas: {schema}
        Pregunta: {question}
        IMPORTANTE: Devuelve SOLO la consulta SQL. No uses bloques de código, ni comillas triples, ni explicaciones.
        SQL:"""
    )

    def get_schema(_): return db.get_table_info()

    # Cadena de procesamiento
    write_query = (
        RunnablePassthrough.assign(schema=get_schema)
        | sql_prompt
        | llm
        | StrOutputParser()
        | clean_sql_query # Limpiamos el resultado aquí
    )

    execute_query = QuerySQLDataBaseTool(db=db)

    answer_prompt = PromptTemplate.from_template(
        """Dada la pregunta, la consulta y el resultado, da una respuesta amigable.
        Pregunta: {question}
        SQL: {query}
        Resultado: {result}
        Respuesta:"""
    )

    chain = (
        RunnablePassthrough.assign(query=write_query)
        | RunnablePassthrough.assign(result=itemgetter("query") | execute_query)
        | answer_prompt
        | llm
        | StrOutputParser()
    )

@app.route('/')
def index(): return render_template('index.html')

@app.route('/preguntar', methods=['POST'])
def preguntar():
    data = request.json
    try:
        res = chain.invoke({"question": data.get('pregunta')})
        return jsonify({"respuesta": res})
    except Exception as e:
        return jsonify({"respuesta": f"Error: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
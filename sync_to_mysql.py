import os
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from models import db, User, LessonProgress, ExerciseAttempt, Achievement, DailyStreak, QuizResult, PracticeSubmission

# Configuraciones de conexión
# Supabase PostgreSQL (Producción)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "postgresql://postgres.inedpsykfbriqmkuhcws:4j7L9DExpgdtegDV@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require")

# MySQL Local (phpMyAdmin)
# Cambia esto por tus credenciales de phpMyAdmin locales
MYSQL_USER = "root"
MYSQL_PASSWORD = ""
MYSQL_HOST = "localhost"
MYSQL_DB = "py2java_edu"
MYSQL_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"

def sync_databases():
    print("Iniciando sincronización de Supabase a MySQL local...")
    
    try:
        import pymysql
    except ImportError:
        print("Por favor instala pymysql para conectarte a MySQL: pip install pymysql")
        return

    # Conectar a Supabase
    print("Conectando a Supabase...")
    supabase_engine = sqlalchemy.create_engine(SUPABASE_URL)
    SupabaseSession = sessionmaker(bind=supabase_engine)
    supa_session = SupabaseSession()

    # Conectar a MySQL Local
    print("Conectando a MySQL local...")
    mysql_engine = sqlalchemy.create_engine(MYSQL_URL)
    
    # Crear tablas en MySQL si no existen (usa los modelos definidos en models.py)
    db.metadata.create_all(mysql_engine)
    
    MysqlSession = sessionmaker(bind=mysql_engine)
    mysql_session = MysqlSession()

    # Tablas a sincronizar (ordenadas para respetar foreign keys)
    tables = [
        User,
        LessonProgress,
        ExerciseAttempt,
        Achievement,
        DailyStreak,
        QuizResult,
        PracticeSubmission
    ]

    for model in tables:
        print(f"Sincronizando {model.__tablename__}...")
        
        # Obtener todos los registros de Supabase
        records = supa_session.query(model).all()
        
        # Opcional: limpiar tabla en MySQL antes de insertar (o hacer un merge)
        # mysql_session.query(model).delete()
        
        for record in records:
            # Desvincular el objeto de la sesión de SQLAlchemy (Supabase)
            # para poder agregarlo a la sesión de MySQL
            supa_session.expunge(record)
            sqlalchemy.orm.make_transient(record)
            
            # Merge o agregar
            mysql_session.merge(record)
            
        mysql_session.commit()
        print(f"✓ {len(records)} registros guardados en MySQL.")

    supa_session.close()
    mysql_session.close()
    print("Sincronización completada exitosamente.")

if __name__ == "__main__":
    sync_databases()

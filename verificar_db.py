import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

# --- Configuración de la Base de Datos ---

DB_FILE = 'socios_bot.db'
engine = create_engine(f'sqlite:///{DB_FILE}')
Base = declarative_base()
Session = sessionmaker(bind=engine) 

# --- Modelos de Datos ---

class Usuario(Base):
    __tablename__ = 'usuarios'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=True) 
    
    username = Column(String(50), unique=True, nullable=False)
    login_key = Column(String(100), nullable=False) 
    
    saldo = Column(Float, default=0.00)
    es_admin = Column(Boolean, default=False)
    fecha_registro = Column(DateTime, default=datetime.now)

class Producto(Base):
    __tablename__ = 'productos'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    categoria = Column(String(50), nullable=False)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    descripcion = Column(String(255)) 
    fecha_creacion = Column(DateTime, default=datetime.now)

# --- Función de Utilidad ---

def get_session():
    """Retorna una nueva sesión de SQLAlchemy."""
    return Session()

# --- Función de Inicialización (Asegura que el Admin exista) ---

def inicializar_db():
    """Crea las tablas y el usuario administrador si no existen."""
    Base.metadata.create_all(engine)
    
    with get_session() as session:
        if session.query(Usuario).count() == 0:
            logging.info("Insertando SOLAMENTE el usuario administrador: admin/adminpass")
            admin_user = Usuario(username='admin', login_key='adminpass', saldo=1000.00, es_admin=True)
            session.add(admin_user)
            session.commit()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("Inicializando la base de datos y creando tablas...")
    inicializar_db()
    print(f"Tablas creadas en {DB_FILE}.")
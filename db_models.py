import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
from dotenv import load_dotenv # Necesario para el if __name__

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO)

# --- Definición de la Base ---
Base = declarative_base()

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
    descripcion = Column(String(255)) 
    fecha_creacion = Column(DateTime, default=datetime.now)
    
    keys = relationship("Key", back_populates="producto")


class Key(Base):
    __tablename__ = 'keys'
    
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    licencia = Column(String(255), unique=True, nullable=False)
    estado = Column(String(20), default='available') # 'available' o 'used'
    
    producto = relationship("Producto", back_populates="keys")


# --- Función de Inicialización ---

def inicializar_db(engine): 
    """Crea las tablas, y el usuario administrador si no existen."""
    
    # 1. Crea las tablas
    Base.metadata.create_all(bind=engine) 

    # 2. Crea el usuario administrador
    Session = sessionmaker(bind=engine)
    with Session() as session:
        if session.query(Usuario).count() == 0:
            logging.info("Insertando SOLAMENTE el usuario administrador: admin/adminpass")
            admin_user = Usuario(username='admin', login_key='adminpass', saldo=1000.00, es_admin=True)
            session.add(admin_user)
            session.commit()
            print("Base de datos inicializada con usuario administrador.")
        else:
             print("Base de datos verificada. Usuario administrador existente.")


if __name__ == '__main__':
    # --- CONEXIÓN DIRECTA Y TEMPORAL A POSTGRESQL (USANDO TU URL REAL) ---
    # Esto asegura que el script ya no busque SQLite, sino que intente conectarse a Render.
    
    DATABASE_URL = 'postgresql://torresdb_prod_user:7lS9o4crKgVc7DDXjFnnqy2W7z2Z0VaX@dpg-d4lq0vk9c44c73flnkl0-a/torresdb_prod'
    
    print(f"Conectando a PostgreSQL Remoto: {DATABASE_URL}")

    try:
        # Crea el motor de conexión
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        print("Inicializando la base de datos y creando/verificando tablas...")
        
        # Ejecuta la función de creación de tablas
        inicializar_db(engine) 
        print("¡Proceso de creación de tablas finalizado con éxito en el servidor de Render!")
        
    except Exception as e:
        print(f"\n--- ERROR CRÍTICO DE CONEXIÓN ---\nNo se pudo conectar a la base de datos en {DATABASE_URL}")
        print("Asegúrate de que el servidor de Render esté activo.")
        print(f"Detalle del error: {e}\n")
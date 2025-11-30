from flask import Flask, render_template, request, redirect, url_for, session as flask_session, flash
from sqlalchemy.exc import IntegrityError
from db_models import Usuario, Producto, Key, get_session, inicializar_db 
from functools import wraps
import logging

logging.basicConfig(level=logging.INFO)
inicializar_db()

app = Flask(__name__)
app.secret_key = '9876543210qwertyuiopasdfghjklzxcvbnm' 

# =================================================================
# 1. Decorador de Autenticación
# =================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not flask_session.get('logged_in'):
            flash('Debes iniciar sesión para acceder a esta página.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# =================================================================
# 2. Rutas de Autenticación
# =================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        login_key_input = request.form.get('login_key') or request.form.get('password')

        db_session = get_session()
        try:
            usuario = db_session.query(Usuario).filter_by(
                username=username, 
                login_key=login_key_input, 
                es_admin=True
            ).first()

            if usuario:
                flask_session['logged_in'] = True
                flask_session['username'] = usuario.username
                flask_session['user_id'] = usuario.id
                flash('Inicio de sesión exitoso.', 'success')
                return redirect(url_for('manage_users')) 
            else:
                flash('Credenciales incorrectas o no eres administrador.', 'danger')
        except Exception as e:
            logging.error(f'Error al procesar login: {e}')
            flash('Ocurrió un error inesperado al iniciar sesión.', 'danger')
        finally:
            db_session.close()

    return render_template('login.html') 

@app.route('/logout')
def logout():
    flask_session.clear()
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('login'))


# =================================================================
# 3. Gestión de Usuarios (Socios)
# =================================================================

@app.route('/')
@app.route('/users')
@login_required
def manage_users():
    db_session = get_session()
    try:
        usuarios = db_session.query(Usuario).all()
    finally:
        db_session.close()
    
    return render_template('admin_users.html', usuarios=usuarios) 

@app.route('/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        login_key = request.form.get('login_key')
        saldo = request.form.get('saldo', 0.0)
        es_admin = request.form.get('es_admin') == 'on'
        
        db_session = get_session()
        try:
            nuevo_usuario = Usuario(
                username=username,
                login_key=login_key,
                saldo=float(saldo),
                es_admin=es_admin
            )
            db_session.add(nuevo_usuario)
            db_session.commit()
            flash(f'Socio "{username}" registrado exitosamente.', 'success')
            return redirect(url_for('manage_users'))
        except IntegrityError:
            db_session.rollback()
            flash('Error: El nombre de usuario ya existe.', 'danger')
        finally:
            db_session.close()

    return render_template('create_user.html')

@app.route('/adjust_saldo/<int:user_id>', methods=['GET', 'POST'])
@login_required
def adjust_saldo(user_id):
    db_session = get_session()
    try:
        usuario = db_session.query(Usuario).filter_by(id=user_id).first()
        if not usuario:
            flash('Usuario no encontrado.', 'danger')
            return redirect(url_for('manage_users'))

        if request.method == 'POST':
            try:
                monto = float(request.form.get('monto'))
                usuario.saldo += monto
                db_session.commit()
                flash(f'Saldo de {usuario.username} actualizado a ${usuario.saldo:.2f}', 'success')
                return redirect(url_for('manage_users'))
            except ValueError:
                flash('Monto no válido.', 'danger')
            except Exception as e:
                db_session.rollback()
                flash(f'Error al ajustar saldo: {e}', 'danger')
        
        return render_template('adjust_saldo.html', usuario=usuario)
    finally:
        db_session.close()


# =================================================================
# 4. Gestión de Productos e Inventario (Keys)
# =================================================================

@app.route('/products')
@login_required
def manage_products():
    """Calcula el stock y muestra la lista de productos."""
    db_session = get_session()
    try:
        productos = db_session.query(Producto).all()
        for p in productos:
            p.stock_available = db_session.query(Key).filter(Key.producto_id == p.id, Key.estado == 'available').count()
    finally:
        db_session.close()
    return render_template('manage_products.html', productos=productos)


@app.route('/product/<int:product_id>/keys', methods=['GET', 'POST'])
@login_required
def manage_keys(product_id):
    """Muestra las keys de un producto y permite agregar nuevas."""
    db_session = get_session()
    try:
        producto = db_session.query(Producto).filter_by(id=product_id).first()
        if not producto:
            flash('Producto no encontrado.', 'danger')
            return redirect(url_for('manage_products'))
        
        available_keys = db_session.query(Key).filter_by(producto_id=product_id, estado='available').all()
        used_keys = db_session.query(Key).filter_by(producto_id=product_id, estado='used').all()

        if request.method == 'POST':
            licencias_raw = request.form.get('licencias') 
            if licencias_raw:
                nuevas_keys = 0
                for lic in licencias_raw.splitlines():
                    lic = lic.strip()
                    if lic:
                        nueva_key = Key(producto_id=product_id, licencia=lic, estado='available')
                        db_session.add(nueva_key)
                        nuevas_keys += 1
                db_session.commit()
                flash(f'{nuevas_keys} nuevas licencias agregadas a {producto.nombre}.', 'success')
                return redirect(url_for('manage_keys', product_id=product_id))

    finally:
        db_session.close()

    return render_template('manage_keys.html', producto=producto, available_keys=available_keys, used_keys=used_keys)


@app.route('/create_product', methods=['GET', 'POST'])
@login_required
def create_product():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        categoria = request.form.get('categoria')
        precio = request.form.get('precio', 0.0)
        descripcion = request.form.get('descripcion')
        
        db_session = get_session()
        try:
            nuevo_producto = Producto(
                nombre=nombre,
                categoria=categoria,
                precio=float(precio),
                descripcion=descripcion
            )
            db_session.add(nuevo_producto)
            db_session.commit()
            flash(f'Producto "{nombre}" creado exitosamente.', 'success')
            return redirect(url_for('manage_products'))
        except Exception as e:
            db_session.rollback()
            flash(f'Error al crear producto: {e}', 'danger')
        finally:
            db_session.close()
            
    return render_template('create_product.html')

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    db_session = get_session()
    try:
        producto = db_session.query(Producto).filter_by(id=product_id).first()
        if not producto:
            flash('Producto no encontrado.', 'danger')
            return redirect(url_for('manage_products'))

        if request.method == 'POST':
            producto.nombre = request.form.get('nombre')
            producto.categoria = request.form.get('categoria')
            producto.precio = float(request.form.get('precio'))
            producto.descripcion = request.form.get('descripcion')
            
            db_session.commit()
            flash(f'Producto "{producto.nombre}" actualizado exitosamente.', 'success')
            return redirect(url_for('manage_products'))

        return render_template('edit_product.html', producto=producto)
    except Exception as e:
        db_session.rollback()
        flash(f'Error al editar producto: {e}', 'danger')
        return redirect(url_for('manage_products'))
    finally:
        db_session.close()

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    db_session = get_session()
    try:
        producto = db_session.query(Producto).filter_by(id=product_id).first()
        if producto:
            db_session.query(Key).filter_by(producto_id=product_id).delete()
            db_session.delete(producto)
            db_session.commit()
            flash(f'Producto "{producto.nombre}" y sus Keys eliminados exitosamente.', 'success')
        else:
            flash('Producto no encontrado.', 'danger')
    finally:
        db_session.close()
    return redirect(url_for('manage_products'))


# =================================================================
# 5. Ejecución
# =================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
import os
import json
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuración de seguridad y Base de Datos
app.config['SECRET_KEY'] = 'minimarket_adriano_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///minimarket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------------------------------------------------------------
# MODELOS DE LA BASE DE DATOS
# -------------------------------------------------------------------------
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<Usuario {self.username}>'

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    imagen = db.Column(db.String(200), nullable=True, default='default.png')

    def __repr__(self):
        return f'<Producto {self.nombre}>'

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Cambiado a timezone-aware para evitar desajustes en el cierre de caja diario
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    productos_vendidos = db.Column(db.Text, nullable=False)  # Detalle en texto
    total = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Venta Boleta #{self.id}>'

# -------------------------------------------------------------------------
# RUTAS DE CONTROL DE ACCESO (LOGIN Y SESIONES)
# -------------------------------------------------------------------------
@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        usuario_ingresado = request.form.get('username')
        password_ingresado = request.form.get('password')
        
        # Primero buscamos si el usuario existe en la base de datos relacional
        usuario = Usuario.query.filter_by(username=usuario_ingresado).first()
        
        if usuario and usuario.password == password_ingresado:
            session['usuario'] = usuario.username
            flash('¡Inicio de sesión exitoso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
            
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor, completa todos los campos.', 'error')
            return redirect(url_for('registro'))
            
        usuario_existente = Usuario.query.filter_by(username=username).first()
        if usuario_existente:
            flash('El nombre de usuario ya está registrado.', 'error')
            return redirect(url_for('registro'))
            
        nuevo_usuario = Usuario(username=username, password=password)
        
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash('Cuenta creada con éxito. Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Ocurrió un error al crear la cuenta.', 'error')
            return redirect(url_for('registro'))
            
    return render_template('registro.html')

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        flash('Debes iniciar sesión primero.', 'error')
        return redirect(url_for('login'))
    
    total_productos = Producto.query.count()
    stock_bajo = Producto.query.filter(Producto.stock <= 5).count()
    
    # Cálculo preciso de ingresos diarios usando UTC coordinado
    hoy = datetime.now(timezone.utc).date()
    ventas_hoy = Venta.query.all()
    
    total_ventas_hoy = 0.0
    for venta in ventas_hoy:
        if venta.fecha.date() == hoy:
            total_ventas_hoy += venta.total

    return render_template(
        'dashboard.html', 
        total_productos=total_productos, 
        stock_bajo=stock_bajo, 
        total_ventas_hoy=total_ventas_hoy
    )

@app.route('/nosotros')
def nosotros():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('nosotros.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('login'))

@app.route('/resetear-bd')
def resetear_bd():
    db.drop_all()
    db.create_all()
    
    # Pre-creamos el usuario administrador por defecto para que no te quedes fuera
    admin_defecto = Usuario(username='ADMIN', password='1234')
    db.session.add(admin_defecto)
    db.session.commit()
    
    return "Base de datos reseteada con éxito. Inicia con ADMIN / 1234 o registra una cuenta nueva."

# -------------------------------------------------------------------------
# MÓDULO DE INVENTARIO (PRODUCTOS)
# -------------------------------------------------------------------------
@app.route('/productos')
def productos():
    if 'usuario' not in session:
        flash('Debes iniciar sesión primero.', 'error')
        return redirect(url_for('login'))
    
    todos_los_productos = Producto.query.all()
    return render_template('productos.html', productos=todos_los_productos)

@app.route('/productos/nuevo', methods=['GET', 'POST'])
def nuevo_producto():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio = float(request.form.get('precio'))
        stock = int(request.form.get('stock'))
        
        nuevo = Producto(nombre=nombre, precio=precio, stock=stock)
        db.session.add(nuevo)
        db.session.commit()
        
        flash(f'¡Producto "{nombre}" agregado exitosamente!', 'success')
        return redirect(url_for('productos'))
        
    return render_template('producto_form.html', producto=None)

@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    producto_a_editar = Producto.query.get_or_404(id)
    
    if request.method == 'POST':
        producto_a_editar.nombre = request.form.get('nombre')
        producto_a_editar.precio = float(request.form.get('precio'))
        producto_a_editar.stock = int(request.form.get('stock'))
        
        db.session.commit()
        flash('Producto actualizado correctamente.', 'success')
        return redirect(url_for('productos'))
        
    return render_template('producto_form.html', producto=producto_a_editar)

@app.route('/productos/eliminar/<int:id>')
def eliminar_producto(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    producto_a_eliminar = Producto.query.get_or_404(id)
    db.session.delete(producto_a_eliminar)
    db.session.commit()
    
    flash('El producto fue eliminado del inventario.', 'success')
    return redirect(url_for('productos'))

# -------------------------------------------------------------------------
# MÓDULO DE CAJA Y PROCESAMIENTO DE VENTAS
# -------------------------------------------------------------------------
@app.route('/caja')
def caja():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    productos_disponibles = Producto.query.order_by(Producto.nombre).all()
    return render_template('caja.html', productos=productos_disponibles)

@app.route('/procesar_venta', methods=['POST'])
def procesar_venta():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    items_raw = request.form.get('items_json')
    if not items_raw:
        return redirect(url_for('caja'))
        
    try:
        items = json.loads(items_raw)
        detalle_boleta = []
        total_venta = 0
        
        for item in items:
            producto = Producto.query.get(int(item['id']))
            if producto:
                producto.stock -= int(item['cantidad'])
                if producto.stock < 0:
                    producto.stock = 0
                
                subtotal = producto.precio * int(item['cantidad'])
                total_venta += subtotal
                detalle_boleta.append(f"{item['cantidad']}x {producto.nombre}")
        
        texto_productos = ", ".join(detalle_boleta)
        nueva_venta = Venta(productos_vendidos=texto_productos, total=total_venta)
        db.session.add(nueva_venta)
        
        db.session.commit()
        flash('¡Venta procesada y registrada con éxito!', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al procesar la venta: {e}")
        flash('Hubo un error al procesar la venta.', 'error')
        
    return redirect(url_for('ventas_historial'))

# -------------------------------------------------------------------------
# MÓDULO DE HISTORIAL DE VENTAS
# -------------------------------------------------------------------------
@app.route('/ventas')
def ventas_historial():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    todas_las_ventas = Venta.query.order_by(Venta.fecha.desc()).all()
    return render_template('ventas.html', ventas=todas_las_ventas)

# -------------------------------------------------------------------------
# INICIALIZACIÓN DE LA APLICACIÓN
# -------------------------------------------------------------------------
if __name__ == '__main__':

    with app.app_context():

        db.create_all()

        

        # SCRIPT DE PRECARGA: Si el inventario está en cero, inserta datos iniciales

        if Producto.query.count() == 0:

            productos_iniciales = [

                Producto(nombre="Inca Kola 1.5L", precio=4.50, stock=20),

                Producto(nombre="Coca Cola 500ml", precio=2.80, stock=15),

                Producto(nombre="Arroz Costeño 1kg", precio=4.20, stock=30),

                Producto(nombre="Aceite Primor 1L", precio=8.90, stock=12),

                Producto(nombre="Leche Gloria Azul Caneca", precio=4.00, stock=25),

                Producto(nombre="Galletas Casino Chocolate", precio=1.00, stock=50),

                Producto(nombre="Fideos Don Vittorio Spagetti 1kg", precio=3.70, stock=18),

                Producto(nombre="Detergente Opal 1kg", precio=7.50, stock=8)

            ]

            

            db.session.bulk_save_objects(productos_iniciales)

            db.session.commit()

            print("¡Productos del minimarket cargados con éxito!")

    

    # Ejecutamos el servidor local

    app.run(debug=False, port=5010) 



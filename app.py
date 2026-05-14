from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# =========================
# CONFIG
# =========================
app.secret_key = os.getenv("SECRET_KEY", "autopartes_secret")

DATABASE_URL = os.getenv("MYSQL_URL")

if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/autopartes'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# ESTA LÍNEA DEBE IR AQUÍ
db = SQLAlchemy(app)

# =========================
# ADMIN
# =========================
USUARIO_ADMIN = "admin"
PASSWORD_ADMIN = "123456"


# =========================
# MODELO
# =========================
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    marca = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    anio = db.Column(db.Integer)
    precio = db.Column(db.Float)
    stock = db.Column(db.Integer, default=1)
    imagen = db.Column(db.String(200))


# =========================
# CATÁLOGO
# =========================
@app.route('/')
def home():
    productos = Producto.query.all()
    return render_template('catalogo.html', productos=productos)


# =========================
# LOGIN
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if (
            request.form['usuario'] == USUARIO_ADMIN and
            request.form['password'] == PASSWORD_ADMIN
        ):
            session['admin'] = True
            return redirect('/admin')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')


# =========================
# PANEL ADMIN
# =========================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin'):
        return redirect('/login')

    if request.method == 'POST':
        archivo = request.files['imagen']
        nombre_archivo = archivo.filename

        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        ruta = os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo)
        archivo.save(ruta)

        nuevo = Producto(
            nombre=request.form['nombre'],
            marca=request.form['marca'],
            modelo=request.form['modelo'],
            anio=int(request.form['anio']),
            precio=float(request.form['precio']),
            stock=int(request.form['stock']),
            imagen=nombre_archivo
        )

        db.session.add(nuevo)
        db.session.commit()

        return redirect('/admin')

    productos = Producto.query.all()

    total = Producto.query.count()
    disponibles = Producto.query.filter(Producto.stock > 0).count()
    agotados = Producto.query.filter(Producto.stock == 0).count()

    return render_template(
        'admin.html',
        productos=productos,
        total=total,
        disponibles=disponibles,
        agotados=agotados
    )


# =========================
# EDITAR
# =========================
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if not session.get('admin'):
        return redirect('/login')

    producto = Producto.query.get_or_404(id)

    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.marca = request.form['marca']
        producto.modelo = request.form['modelo']
        producto.anio = int(request.form['anio'])
        producto.precio = float(request.form['precio'])

        db.session.commit()
        return redirect('/admin')

    return render_template('editar.html', producto=producto)


# =========================
# STOCK +1
# =========================
@app.route('/sumar/<int:id>')
def sumar_stock(id):
    producto = Producto.query.get_or_404(id)
    producto.stock += 1
    db.session.commit()
    return redirect('/admin')


# =========================
# STOCK -1
# =========================
@app.route('/restar/<int:id>')
def restar_stock(id):
    producto = Producto.query.get_or_404(id)

    if producto.stock > 0:
        producto.stock -= 1

    db.session.commit()
    return redirect('/admin')


# =========================
# AGOTAR
# =========================
@app.route('/agotado/<int:id>')
def marcar_agotado(id):
    producto = Producto.query.get_or_404(id)
    producto.stock = 0
    db.session.commit()
    return redirect('/admin')


# =========================
# ACTIVAR
# =========================
@app.route('/disponible/<int:id>')
def marcar_disponible(id):
    producto = Producto.query.get_or_404(id)
    producto.stock = 1
    db.session.commit()
    return redirect('/admin')


# =========================
# ELIMINAR
# =========================
@app.route('/eliminar/<int:id>')
def eliminar(id):
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    return redirect('/admin')


# =========================
# INIT DB
# =========================
with app.app_context():
    db.create_all()


# =========================
# RUN
# =========================
if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
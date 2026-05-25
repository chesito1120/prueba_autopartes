from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from openpyxl import load_workbook
from urllib.parse import quote_plus
import os

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "autopartes_secret")

# =========================
# BASE DE DATOS
# =========================

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")

DB_USER = os.getenv("MYSQLUSER")
DB_PASSWORD = os.getenv("MYSQLPASSWORD")
DB_HOST = os.getenv("MYSQLHOST")
DB_PORT = os.getenv("MYSQLPORT")
DB_NAME = os.getenv("MYSQLDATABASE")

if all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    DB_PASSWORD_SAFE = quote_plus(DB_PASSWORD)

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD_SAFE}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
else:
    raise RuntimeError("Faltan variables de base de datos en Railway")

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD_SAFE}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

else:
    raise RuntimeError("Faltan variables de base de datos en Railway")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "static/uploads"

db = SQLAlchemy(app)

# =========================
# USUARIOS TEMPORALES
# =========================

USUARIOS = {
    "admin": {
        "password": "123456",
        "rol": "admin"
    },
    "vendedor": {
        "password": "123456",
        "rol": "vendedor"
    },
    "cliente": {
        "password": "123456",
        "rol": "cliente"
    }
}

# =========================
# MODELO
# =========================

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    marca = db.Column(db.String(100))
    modelo = db.Column(db.String(100))
    anio = db.Column(db.Integer)
    autoparte = db.Column(db.String(150))
    observaciones = db.Column(db.Text)
    transmision = db.Column(db.String(100))
    motor = db.Column(db.String(100))
    propiedad = db.Column(db.String(100))
    tipo = db.Column(db.String(100))
    lado = db.Column(db.String(50))
    origen = db.Column(db.String(100))
    costo_venta = db.Column(db.Float)
    stock = db.Column(db.Integer, default=1)
    foto = db.Column(db.String(300))
    link_ml = db.Column(db.String(500))
    estado = db.Column(db.String(50), default="disponible")

    vendido_a = db.Column(db.String(150))
    metodo_pago = db.Column(db.String(100))
    factura = db.Column(db.String(100))
    comentarios_venta = db.Column(db.Text)
    fecha_salida = db.Column(db.String(100))
    fecha_prestamo = db.Column(db.String(100))


# =========================
# CATÁLOGO
# =========================

@app.route("/")
def home():
    pagina = request.args.get("page", 1, type=int)
    por_pagina = 21

    productos_paginados = Producto.query.paginate(
        page=pagina,
        per_page=por_pagina,
        error_out=False
    )

    return render_template(
        "catalogo.html",
        productos=productos_paginados.items,
        paginacion=productos_paginados
    )


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        password = request.form.get("password")

        if usuario in USUARIOS and USUARIOS[usuario]["password"] == password:
            session["usuario"] = usuario
            session["rol"] = USUARIOS[usuario]["rol"]

            if session["rol"] in ["admin", "vendedor"]:
                return redirect("/inventario")

            if session["rol"] == "cliente":
                return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================
# ADMIN / AGREGAR PRODUCTO
# =========================

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("rol") in ["admin", "vendedor"]:
        return redirect("/login")

    if request.method == "POST":
        archivo = request.files.get("imagen") or request.files.get("foto")
        nombre_archivo = ""

        if archivo and archivo.filename:
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            nombre_archivo = archivo.filename
            ruta = os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo)
            archivo.save(ruta)

        nuevo = Producto(
            marca=request.form.get("marca"),
            modelo=request.form.get("modelo"),
            anio=int(request.form.get("anio") or 0),
            autoparte=request.form.get("autoparte") or request.form.get("nombre"),
            observaciones=request.form.get("observaciones"),
            transmision=request.form.get("transmision"),
            motor=request.form.get("motor"),
            propiedad=request.form.get("propiedad"),
            tipo=request.form.get("tipo"),
            lado=request.form.get("lado"),
            origen=request.form.get("origen"),
            costo_venta=float(request.form.get("costo_venta") or request.form.get("precio") or 0),
            stock=int(request.form.get("stock") or 1),
            foto=nombre_archivo,
            link_ml=request.form.get("link_ml"),
            estado="disponible"
        )

        db.session.add(nuevo)
        db.session.commit()

        return redirect("/inventario")

    productos = Producto.query.all()
    total = Producto.query.count()
    disponibles = Producto.query.filter(Producto.stock > 0).count()
    agotados = Producto.query.filter(Producto.stock == 0).count()

    return render_template(
        "admin.html",
        productos=productos,
        total=total,
        disponibles=disponibles,
        agotados=agotados
    )


# =========================
# INVENTARIO
# =========================

@app.route("/inventario")
def inventario():
    if not session.get("rol") in ["admin", "vendedor"]:
        return redirect("/login")

    productos = Producto.query.all()

    return render_template(
        "inventario.html",
        productos=productos
    )


# =========================
# EDITAR
# =========================

@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    if not session.get("rol") in ["admin", "vendedor"]:
        return redirect("/login")

    producto = Producto.query.get_or_404(id)

    if request.method == "POST":
        producto.marca = request.form.get("marca")
        producto.modelo = request.form.get("modelo")
        producto.anio = int(request.form.get("anio") or 0)
        producto.autoparte = request.form.get("autoparte") or request.form.get("nombre")
        producto.observaciones = request.form.get("observaciones")
        producto.transmision = request.form.get("transmision")
        producto.motor = request.form.get("motor")
        producto.propiedad = request.form.get("propiedad")
        producto.tipo = request.form.get("tipo")
        producto.lado = request.form.get("lado")
        producto.origen = request.form.get("origen")
        producto.costo_venta = float(
            request.form.get("costo_venta")
            or request.form.get("precio")
            or 0
        )
        producto.link_ml = request.form.get("link_ml")

        db.session.commit()

        return redirect("/inventario")

    return render_template(
        "editar.html",
        producto=producto
    )


# =========================
# STOCK
# =========================

@app.route("/stock/<int:id>", methods=["GET", "POST"])
def ajustar_stock(id):
    if not session.get("rol") in ["admin", "vendedor"]:
        return redirect("/login")

    producto = Producto.query.get_or_404(id)

    if request.method == "POST":
        nuevo_stock = int(request.form.get("stock") or 0)

        producto.stock = nuevo_stock

        if producto.stock > 0:
            producto.estado = "disponible"
        else:
            producto.estado = "agotado"

        db.session.commit()

        return redirect("/inventario")

    return render_template(
        "stock.html",
        producto=producto
    )


@app.route("/sumar/<int:id>")
def sumar_stock(id):
    producto = Producto.query.get_or_404(id)
    producto.stock += 1
    producto.estado = "disponible"
    db.session.commit()
    return redirect("/inventario")


@app.route("/restar/<int:id>")
def restar_stock(id):
    producto = Producto.query.get_or_404(id)

    if producto.stock > 0:
        producto.stock -= 1

    if producto.stock == 0:
        producto.estado = "agotado"

    db.session.commit()
    return redirect("/inventario")


@app.route("/agotado/<int:id>")
def marcar_agotado(id):
    producto = Producto.query.get_or_404(id)
    producto.stock = 0
    producto.estado = "agotado"
    db.session.commit()
    return redirect("/inventario")


@app.route("/disponible/<int:id>")
def marcar_disponible(id):
    producto = Producto.query.get_or_404(id)
    producto.stock = 1
    producto.estado = "disponible"
    db.session.commit()
    return redirect("/inventario")


@app.route("/eliminar/<int:id>")
def eliminar(id):
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    return redirect("/inventario")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():
    if not session.get("rol") in ["admin", "vendedor"]:
        return redirect("/login")

    productos = Producto.query.all()

    total = Producto.query.count()
    disponibles = Producto.query.filter(Producto.stock > 0).count()
    agotados = Producto.query.filter(Producto.stock == 0).count()

    vendidas = Producto.query.filter(Producto.estado == "vendido").count()
    prestadas = Producto.query.filter(Producto.estado == "prestado").count()
    credito = Producto.query.filter(Producto.estado == "credito").count()

    facturadas = Producto.query.filter(
        Producto.factura.isnot(None),
        Producto.factura != "",
        Producto.factura != "no"
    ).count()

    valor_total = 0

    for producto in productos:
        precio = producto.costo_venta or 0
        stock = producto.stock or 0
        valor_total += precio * stock

    return render_template(
        "dashboard.html",
        total=total,
        disponibles=disponibles,
        agotados=agotados,
        valor_total=round(valor_total, 2),
        vendidas=vendidas,
        prestadas=prestadas,
        credito=credito,
        facturadas=facturadas
    )


# =========================
# VENTAS / CRÉDITOS / PRÉSTAMOS
# =========================

@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    if not session.get("rol") in ["admin", "vendedor"]:
        return redirect("/login")

    mensaje = None
    error = None

    if request.method == "POST":
        producto_id = request.form.get("producto_id")
        tipo_movimiento = request.form.get("tipo_movimiento")
        cantidad = int(request.form.get("cantidad") or 1)

        producto = Producto.query.get_or_404(producto_id)

        if cantidad <= 0:
            error = "La cantidad debe ser mayor a 0."

        elif cantidad > producto.stock:
            error = f"No hay suficiente stock. Stock actual: {producto.stock}"

        else:
            producto.stock -= cantidad

            if tipo_movimiento == "vendido":
                producto.estado = "vendido"

            elif tipo_movimiento == "credito":
                producto.estado = "credito"

            elif tipo_movimiento == "prestado":
                producto.estado = "prestado"

            producto.vendido_a = request.form.get("vendido_a")
            producto.metodo_pago = request.form.get("metodo_pago")
            producto.factura = request.form.get("factura")
            producto.fecha_salida = request.form.get("fecha_salida")
            producto.fecha_prestamo = request.form.get("fecha_prestamo")

            producto.comentarios_venta = (
                f"Cantidad: {cantidad}. "
                f"{request.form.get('comentarios_venta') or ''}"
            )

            db.session.commit()

            mensaje = f"Movimiento registrado correctamente. Cantidad: {cantidad}"

    productos = Producto.query.filter(Producto.stock > 0).all()

    movimientos = Producto.query.filter(
        Producto.estado.in_(["vendido", "credito", "prestado"])
    ).all()

    return render_template(
        "ventas.html",
        productos=productos,
        movimientos=movimientos,
        mensaje=mensaje,
        error=error
    )


# =========================
# PRÉSTAMOS
# =========================

@app.route("/prestamos")
def prestamos():
    if not session.get("rol") in ["admin", "vendedor"]:
        return redirect("/login")

    prestamos = Producto.query.filter(
        Producto.estado == "prestado"
    ).all()

    return render_template(
        "prestamos.html",
        prestamos=prestamos
    )


@app.route("/devolver/<int:id>")
def devolver_prestamo(id):
    if not session.get("rol") in ["admin", "vendedor"]:
        return redirect("/login")

    producto = Producto.query.get_or_404(id)

    producto.estado = "disponible"
    producto.stock += 1
    producto.vendido_a = ""
    producto.fecha_salida = ""
    producto.fecha_prestamo = ""
    producto.comentarios_venta = ""
    producto.metodo_pago = ""
    producto.factura = ""

    db.session.commit()

    return redirect("/prestamos")


# =========================
# EXCEL
# =========================

@app.route("/excel", methods=["GET", "POST"])
def excel():
    if not session.get("rol") in ["admin", "vendedor"]:
        return redirect("/login")

    mensaje = None

    if request.method == "POST":
        archivo = (
            request.files.get("archivo_excel")
            or request.files.get("excel")
        )

        if archivo and archivo.filename:
            workbook = load_workbook(archivo)
            hoja = workbook.active

            encabezados = []

            for celda in hoja[1]:
                encabezados.append(str(celda.value).strip().lower())

            total_cargados = 0

            for fila in hoja.iter_rows(min_row=2, values_only=True):
                datos = dict(zip(encabezados, fila))

                if not datos.get("autoparte") and not datos.get("marca"):
                    continue

                nuevo = Producto(
                    marca=datos.get("marca"),
                    modelo=datos.get("modelo"),
                    anio=int(datos.get("año") or 0),
                    observaciones=datos.get("observaciones"),
                    transmision=datos.get("transmision"),
                    motor=datos.get("motor"),
                    autoparte=datos.get("autoparte"),
                    propiedad=datos.get("propiedad"),
                    tipo=datos.get("tipo"),
                    lado=datos.get("lado"),
                    origen=datos.get("origen"),
                    costo_venta=float(datos.get("costo de venta") or 0),
                    foto=datos.get("foto") or "",
                    link_ml=datos.get("link mercado libre"),
                    stock=int(datos.get("stock") or 1),
                    estado="disponible",
                    comentarios_venta=datos.get("seccion de las ventas y comentarios"),
                    metodo_pago=datos.get("metodo de pago"),
                    factura=datos.get("factura"),
                    fecha_salida=str(datos.get("fecha de la salida") or ""),
                    fecha_prestamo=str(datos.get("fecha de prestamos") or "")
                )

                db.session.add(nuevo)
                total_cargados += 1

            db.session.commit()

            mensaje = f"Se cargaron {total_cargados} productos correctamente."

    return render_template("excel.html", mensaje=mensaje)


# =========================
# CREAR TABLAS
# =========================

with app.app_context():
    db.create_all()


# =========================
# RUN
# =========================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
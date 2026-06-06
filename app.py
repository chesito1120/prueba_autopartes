from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from openpyxl import load_workbook
from urllib.parse import quote_plus
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
import zipfile

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "autopartes_secret")

# =========================
# BASE DE DATOS
# =========================

MYSQL_URL = os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL")

DB_USER = os.getenv("MYSQLUSER")
DB_PASSWORD = os.getenv("MYSQLPASSWORD")
DB_HOST = os.getenv("MYSQLHOST")
DB_PORT = os.getenv("MYSQLPORT")
DB_NAME = os.getenv("MYSQLDATABASE")

print("========== DB DEBUG ==========")
print("MYSQL_URL existe:", bool(MYSQL_URL))
print("MYSQLUSER existe:", bool(DB_USER))
print("MYSQLPASSWORD existe:", bool(DB_PASSWORD))
print("MYSQLHOST existe:", bool(DB_HOST))
print("MYSQLPORT existe:", bool(DB_PORT))
print("MYSQLDATABASE existe:", bool(DB_NAME))
print("==============================")

if MYSQL_URL:
    app.config["SQLALCHEMY_DATABASE_URI"] = MYSQL_URL

elif all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    DB_PASSWORD_SAFE = quote_plus(DB_PASSWORD)

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD_SAFE}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

else:
    print("ADVERTENCIA: No se encontraron variables MySQL completas. Usando SQLite temporal.")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///autopartes_local.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "static/uploads"

db = SQLAlchemy(app)

print("BASE DE DATOS ACTIVA:")
print(app.config["SQLALCHEMY_DATABASE_URI"])


# =========================
# FUNCIONES DE IMAGEN
# =========================

def guardar_imagen(archivo):
    if not archivo or not archivo.filename:
        return ""

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    nombre_original = secure_filename(archivo.filename)
    extension = nombre_original.rsplit(".", 1)[-1].lower()

    if extension not in ["jpg", "jpeg", "png", "webp"]:
        return ""

    nombre_archivo = f"{uuid.uuid4().hex}.{extension}"
    ruta = os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo)

    archivo.save(ruta)

    return nombre_archivo


def guardar_varias_imagenes(archivos):
    fotos = []

    for archivo in archivos:
        if archivo and archivo.filename:
            nombre = guardar_imagen(archivo)

            if nombre:
                fotos.append(nombre)

        if len(fotos) == 5:
            break

    return "|".join(fotos)


def extraer_zip_imagenes(archivo_zip):
    imagenes_extraidas = set()

    if not archivo_zip or not archivo_zip.filename:
        return imagenes_extraidas

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    nombre_zip = secure_filename(archivo_zip.filename)
    ruta_zip = os.path.join(app.config["UPLOAD_FOLDER"], nombre_zip)

    archivo_zip.save(ruta_zip)

    try:
        with zipfile.ZipFile(ruta_zip, "r") as zip_ref:
            for archivo in zip_ref.namelist():
                nombre_archivo = os.path.basename(archivo)

                if not nombre_archivo:
                    continue

                nombre_seguro = secure_filename(nombre_archivo)

                if "." not in nombre_seguro:
                    continue

                extension = nombre_seguro.rsplit(".", 1)[-1].lower()

                if extension not in ["jpg", "jpeg", "png", "webp"]:
                    continue

                ruta_destino = os.path.join(app.config["UPLOAD_FOLDER"], nombre_seguro)

                with zip_ref.open(archivo) as origen, open(ruta_destino, "wb") as destino:
                    destino.write(origen.read())

                imagenes_extraidas.add(nombre_seguro)

    except zipfile.BadZipFile:
        print("ERROR: El archivo subido no es un ZIP válido.")

    if os.path.exists(ruta_zip):
        os.remove(ruta_zip)

    return imagenes_extraidas


# =========================
# MODELOS
# =========================

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(150), nullable=False)
    correo = db.Column(db.String(180), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)
    rol = db.Column(db.String(50), default="vendedor")
    activo = db.Column(db.Boolean, default=True)


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
    error = None

    if request.method == "POST":
        correo = (request.form.get("correo") or "").strip().lower()
        password = request.form.get("password") or ""

        usuario = Usuario.query.filter_by(correo=correo).first()

        if usuario and usuario.activo and check_password_hash(usuario.password_hash, password):
            session["usuario"] = usuario.nombre
            session["correo"] = usuario.correo
            session["rol"] = usuario.rol

            if usuario.rol in ["admin", "vendedor"]:
                return redirect("/inventario")

            return redirect("/")

        error = "Correo o contraseña incorrectos."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================
# USUARIOS
# =========================

@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    if not session.get("rol"):
        return redirect("/login")

    if session.get("rol") != "admin":
        return redirect("/inventario")

    mensaje = None
    error = None

    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        correo = (request.form.get("correo") or "").strip().lower()
        password = request.form.get("password") or ""
        rol = request.form.get("rol") or "vendedor"

        if rol not in ["admin", "vendedor"]:
            rol = "vendedor"

        if not nombre or not correo or not password:
            error = "Todos los campos son obligatorios."

        elif Usuario.query.filter_by(correo=correo).first():
            error = "Ese correo ya está registrado."

        else:
            nuevo_usuario = Usuario(
                nombre=nombre,
                correo=correo,
                password_hash=generate_password_hash(password),
                rol=rol,
                activo=True
            )

            db.session.add(nuevo_usuario)
            db.session.commit()

            mensaje = "Usuario creado correctamente."

    usuarios_lista = Usuario.query.order_by(Usuario.id.desc()).all()

    return render_template(
        "usuarios.html",
        usuarios=usuarios_lista,
        mensaje=mensaje,
        error=error
    )


@app.route("/usuarios/desactivar/<int:id>")
def desactivar_usuario(id):
    if not session.get("rol"):
        return redirect("/login")

    if session.get("rol") != "admin":
        return redirect("/inventario")

    usuario = Usuario.query.get_or_404(id)

    if usuario.correo != session.get("correo"):
        usuario.activo = False
        db.session.commit()

    return redirect("/usuarios")


@app.route("/usuarios/activar/<int:id>")
def activar_usuario(id):
    if not session.get("rol"):
        return redirect("/login")

    if session.get("rol") != "admin":
        return redirect("/inventario")

    usuario = Usuario.query.get_or_404(id)
    usuario.activo = True
    db.session.commit()

    return redirect("/usuarios")


@app.route("/usuarios/eliminar/<int:id>")
def eliminar_usuario(id):
    if not session.get("rol"):
        return redirect("/login")

    if session.get("rol") != "admin":
        return redirect("/inventario")

    usuario = Usuario.query.get_or_404(id)

    if usuario.correo != session.get("correo"):
        db.session.delete(usuario)
        db.session.commit()

    return redirect("/usuarios")


# =========================
# ADMIN / AGREGAR PRODUCTO
# =========================

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("rol") in ["admin", "vendedor"]:
        return redirect("/login")

    if request.method == "POST":
        archivos = request.files.getlist("fotos")
        nombre_archivo = guardar_varias_imagenes(archivos)

        if not nombre_archivo:
            archivo = request.files.get("imagen") or request.files.get("foto")
            nombre_archivo = guardar_imagen(archivo)

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

        archivos = request.files.getlist("fotos")
        nuevas_fotos = guardar_varias_imagenes(archivos)

        if nuevas_fotos:
            producto.foto = nuevas_fotos
        else:
            archivo = request.files.get("foto")

            if archivo and archivo.filename:
                nombre_archivo = guardar_imagen(archivo)
                producto.foto = nombre_archivo

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
    if not session.get("rol") in ["admin", "vendedor"]:
        return redirect("/login")

    producto = Producto.query.get_or_404(id)

    db.session.delete(producto)
    db.session.commit()

    return redirect("/inventario")


@app.route("/eliminar_masivo", methods=["POST"])
def eliminar_masivo():
    if not session.get("rol") in ["admin", "vendedor"]:
        return redirect("/login")

    ids = request.form.getlist("productos")

    if ids:
        Producto.query.filter(
            Producto.id.in_(ids)
        ).delete(
            synchronize_session=False
        )

        db.session.commit()

    return redirect("/inventario")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():
    if session.get("rol") != "admin":
        return redirect("/inventario")

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

        archivo_zip = (
            request.files.get("imagenes_zip")
            or request.files.get("zip")
            or request.files.get("imagenes")
        )

        imagenes_disponibles = extraer_zip_imagenes(archivo_zip)

        if archivo and archivo.filename:
            workbook = load_workbook(archivo)
            hoja = workbook.active

            encabezados = []

            for celda in hoja[1]:
                encabezado = str(celda.value or "").strip().lower()
                encabezados.append(encabezado)

            total_cargados = 0

            for fila in hoja.iter_rows(min_row=2, values_only=True):
                datos = dict(zip(encabezados, fila))

                if not datos.get("autoparte") and not datos.get("marca"):
                    continue

                fotos_excel = []

                for campo in ["foto", "foto1", "foto2", "foto3", "foto4", "foto5"]:
                    nombre_foto = datos.get(campo)

                    if nombre_foto:
                        nombre_foto = secure_filename(str(nombre_foto).strip())

                        if nombre_foto:
                            if not imagenes_disponibles or nombre_foto in imagenes_disponibles:
                                fotos_excel.append(nombre_foto)

                    if len(fotos_excel) == 5:
                        break

                nuevo = Producto(
                    marca=datos.get("marca"),
                    modelo=datos.get("modelo"),
                    anio=int(datos.get("año") or datos.get("anio") or 0),
                    observaciones=datos.get("observaciones"),
                    transmision=datos.get("transmision"),
                    motor=datos.get("motor"),
                    autoparte=datos.get("autoparte"),
                    propiedad=datos.get("propiedad"),
                    tipo=datos.get("tipo"),
                    lado=datos.get("lado"),
                    origen=datos.get("origen"),
                    costo_venta=float(datos.get("costo de venta") or datos.get("costo_venta") or 0),
                    foto="|".join(fotos_excel),
                    link_ml=datos.get("link mercado libre") or datos.get("link_ml"),
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
# CREAR TABLAS Y ADMIN INICIAL
# =========================

with app.app_context():
    db.create_all()

    if Usuario.query.count() == 0:
        admin_inicial = Usuario(
            nombre="Administrador",
            correo=os.getenv("ADMIN_CORREO", "admin@autopartesch.com"),
            password_hash=generate_password_hash(os.getenv("ADMIN_PASSWORD", "Admin12345")),
            rol="admin",
            activo=True
        )

        db.session.add(admin_inicial)
        db.session.commit()

        print("====================================")
        print("ADMIN INICIAL CREADO")
        print("Correo:", os.getenv("ADMIN_CORREO", "admin@autopartesch.com"))
        print("Contraseña temporal:", os.getenv("ADMIN_PASSWORD", "Admin12345"))
        print("CAMBIA ESTOS DATOS EN PRODUCCIÓN")
        print("====================================")


# =========================
# RUN
# =========================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from config import Config
import MySQLdb

app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)
app.secret_key = 'your_secret_key'

@app.route('/')
def index():
    if 'user_email' in session:
        return render_template('index.html', logged_in=True)
    return render_template('index.html', logged_in=False)

@app.route('/nosotros')
def nosotros():
    return render_template('nosotros.html')

@app.route('/recursos')
def recursos():
    return render_template('recursos.html')

@app.route('/consejos')
def consejos():
    return render_template('consejos.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_email', None)
    session.pop('specialist_email', None)
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        contraseña = request.form['contraseña']
        
        cur = mysql.connection.cursor()
        try:
            cur.callproc('CrearUsuario', [nombre, email, telefono, direccion, contraseña])
            mysql.connection.commit()
            return redirect(url_for('index'))
        except MySQLdb.OperationalError as e:
            mysql.connection.rollback()
            if e.args[0] == 1062:  # Duplicate entry error
                flash('Este correo ya está siendo utilizado.', 'danger')
            else:
                flash('Ocurrió un error al registrar el usuario. Por favor, inténtalo de nuevo.', 'danger')
        finally:
            cur.close()
    
    return render_template('registro_cliente.html')

@app.route('/register_specialist', methods=['GET', 'POST'])
def register_specialist():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        telefono = request.form['telefono']
        especialidad = request.form['especialidad']
        direccion = request.form['direccion']
        sobre_mi = request.form['sobre_mi']
        contraseña = request.form['contraseña']
        
        cur = mysql.connection.cursor()
        try:
            cur.callproc('CrearEspecialista', [nombre, email, telefono, especialidad, direccion, sobre_mi, contraseña])
            mysql.connection.commit()
            return redirect(url_for('index'))
        except MySQLdb.OperationalError as e:
            mysql.connection.rollback()
            if e.args[0] == 1062:  # Duplicate entry error
                flash('Este correo ya está siendo utilizado.', 'danger')
            else:
                flash('Ocurrió un error al registrar el especialista. Por favor, inténtalo de nuevo.', 'danger')
        finally:
            cur.close()
    
    return render_template('registro_especialista.html')

@app.route('/login_usuario', methods=['GET', 'POST'])
def login_usuario():
    if request.method == 'POST':
        email = request.form['email']
        contraseña = request.form['contraseña']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, contraseña FROM usuarios WHERE email = %s", (email,))
        user = cur.fetchone()

        if user:
            user_id, hashed_password = user
            if contraseña == hashed_password:
                session['logged_in'] = True
                session['user_email'] = email
                session['user_id'] = user_id  
                return redirect(url_for('index'))
            else:
                flash('Contraseña incorrecta', 'danger')
        else:
            flash('Email no registrado', 'danger')

        cur.close()
    
    return render_template('login_usuario.html')

@app.route('/login_especialista', methods=['GET', 'POST'])
def login_especialista():
    if request.method == 'POST':
        email = request.form['email']
        contraseña = request.form['contraseña']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, contraseña FROM especialistas WHERE email = %s", (email,))
        specialist = cur.fetchone()

        if specialist:
            specialist_id, hashed_password = specialist
            if contraseña == hashed_password:
                session['logged_in'] = True
                session['specialist_email'] = email
                session['specialist_id'] = specialist_id  
                return redirect(url_for('index'))
            else:
                flash('Contraseña incorrecta', 'danger')
        else:
            flash('Email no registrado', 'danger')

        cur.close()
    
    return render_template('login_especialista.html')

@app.route('/crear_cita', methods=['GET', 'POST'])
def crear_cita():
    if 'user_email' not in session:
        flash('Debes iniciar sesión para crear una cita.', 'warning')
        return redirect(url_for('login_usuario'))

    especialista_id = request.args.get('especialista_id')
    
    if request.method == 'POST':
        fecha_cita = request.form['fecha_cita']
        hora_cita = request.form['hora_cita']
        motivo = request.form['motivo']
        usuario_id = session.get('user_id')

        cur = mysql.connection.cursor()
        try:
            cur.callproc('CrearCita', [usuario_id, especialista_id, fecha_cita, hora_cita, motivo])
            mysql.connection.commit()
            return redirect(url_for('index'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cur.close()

    return render_template('crear_cita.html', especialista_id=especialista_id)

@app.route('/mis_citas')
def mis_citas():
    if 'specialist_email' not in session:
        flash('Debes iniciar sesión como especialista para ver tus citas.', 'warning')
        return redirect(url_for('login_especialista'))

    specialist_email = session['specialist_email']

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT citas.id, usuarios.nombre AS usuario_nombre, fecha_cita, hora_cita, motivo, citas.estado
        FROM citas
        JOIN usuarios ON citas.usuario_id = usuarios.id
        WHERE citas.especialista_id = (
            SELECT id FROM especialistas WHERE email = %s
        )
        """, (specialist_email,))
    
    citas = cur.fetchall()
    cur.close()

    return render_template('mis_citas.html', citas=citas)

@app.route('/actualizar_estado/<int:cita_id>', methods=['POST'])
def actualizar_estado(cita_id):
    nuevo_estado = request.form['estado']
    
    cur = mysql.connection.cursor()
    try:
        cur.callproc('ActualizarEstadoCita', [cita_id, nuevo_estado])
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()

    return redirect(url_for('mis_citas'))

@app.route('/mis_citas_paciente')
def mis_citas_paciente():
    if 'user_email' not in session:
        flash('Debes iniciar sesión para ver tus citas.', 'warning')
        return redirect(url_for('login_usuario'))

    user_id = session.get('user_id')

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT citas.id, especialistas.nombre AS especialista_nombre, fecha_cita, hora_cita, motivo, citas.estado
        FROM citas
        JOIN especialistas ON citas.especialista_id = especialistas.id
        WHERE citas.usuario_id = %s
        """, (user_id,))
    
    citas = cur.fetchall()
    cur.close()

    return render_template('mis_citas_paciente.html', citas=citas)

@app.route('/cancelar_cita/<int:cita_id>', methods=['POST'])
def cancelar_cita(cita_id):
    if 'user_email' not in session:
        flash('Debes iniciar sesión para cancelar una cita.', 'warning')
        return redirect(url_for('login_usuario'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("UPDATE citas SET estado = 'cancelada' WHERE id = %s AND usuario_id = %s", (cita_id, session.get('user_id')))
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error: {e}', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('mis_citas_paciente'))

@app.route('/especialistas')
def especialistas():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nombre, email, especialidad, telefono, direccion, sobre_mi FROM especialistas")
    especialistas = cur.fetchall()
    cur.close()
    return render_template('especialistas.html', especialistas=especialistas)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contraseña = request.form['contraseña']

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM administradores WHERE usuario = %s AND contraseña = %s", (usuario, contraseña))
        admin = cur.fetchone()

        if admin:
            session['admin_logged_in'] = True
            session['admin_id'] = admin[0]
            return redirect(url_for('administracion'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')

        cur.close()
    
    return render_template('admin_login.html')

@app.route('/logout_admin')
def logout_admin():
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    return redirect(url_for('index'))

# Protege las rutas administrativas de forma sencilla
@app.route('/administracion')
def administracion():
    if 'admin_logged_in' not in session:
        flash('Debes iniciar sesión como administrador para acceder a esta página.', 'warning')
        return redirect(url_for('admin_login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM bitacora")
    bitacora = cur.fetchall()
    cur.close()
    return render_template('admin_dashboard.html', bitacora=bitacora)

@app.route('/admin_usuarios', methods=['GET', 'POST'])
def admin_usuarios():
    if 'admin_logged_in' not in session:
        flash('Debes iniciar sesión como administrador para acceder a esta página.', 'warning')
        return redirect(url_for('admin_login'))

    cur = mysql.connection.cursor()
    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')
        contraseña = request.form.get('contraseña')
        
        if action == 'add':
            cur.callproc('CrearUsuario', [nombre, email, telefono, direccion, contraseña])
        elif action == 'update':
            cur.execute("UPDATE usuarios SET nombre=%s, email=%s, telefono=%s, direccion=%s, contraseña=%s WHERE id=%s",
                        (nombre, email, telefono, direccion, contraseña, user_id))
        elif action == 'delete':
            cur.execute("DELETE FROM citas WHERE usuario_id=%s", (user_id,))
            cur.execute("DELETE FROM usuarios WHERE id=%s", (user_id,))
        
        mysql.connection.commit()
    
    cur.execute("SELECT * FROM usuarios")
    usuarios = cur.fetchall()
    cur.close()
    return render_template('admin_usuarios.html', usuarios=usuarios)

@app.route('/admin_especialistas', methods=['GET', 'POST'])
def admin_especialistas():
    if 'admin_logged_in' not in session:
        flash('Debes iniciar sesión como administrador para acceder a esta página.', 'warning')
        return redirect(url_for('admin_login'))

    cur = mysql.connection.cursor()
    if request.method == 'POST':
        action = request.form.get('action')
        specialist_id = request.form.get('specialist_id')
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        especialidad = request.form.get('especialidad')
        direccion = request.form.get('direccion')
        sobre_mi = request.form.get('sobre_mi')
        contraseña = request.form.get('contraseña')
        
        if action == 'add':
            cur.callproc('CrearEspecialista', [nombre, email, telefono, especialidad, direccion, sobre_mi, contraseña])
        elif action == 'update':
            cur.execute("UPDATE especialistas SET nombre=%s, email=%s, telefono=%s, especialidad=%s, direccion=%s, sobre_mi=%s, contraseña=%s WHERE id=%s",
                        (nombre, email, telefono, especialidad, direccion, sobre_mi, contraseña, specialist_id))
        elif action == 'delete':
            cur.execute("DELETE FROM citas WHERE especialista_id=%s", (specialist_id,))
            cur.execute("DELETE FROM especialistas WHERE id=%s", (specialist_id,))
        
        mysql.connection.commit()
    
    cur.execute("SELECT * FROM especialistas")
    especialistas = cur.fetchall()
    cur.close()
    return render_template('admin_especialistas.html', especialistas=especialistas)


@app.route('/admin_citas', methods=['GET', 'POST'])
def admin_citas():
    if 'admin_logged_in' not in session:
        flash('Debes iniciar sesión como administrador para acceder a esta página.', 'warning')
        return redirect(url_for('admin_login'))

    cur = mysql.connection.cursor()
    if request.method == 'POST':
        action = request.form.get('action')
        cita_id = request.form.get('cita_id')
        usuario_id = request.form.get('usuario_id')
        especialista_id = request.form.get('especialista_id')
        fecha_cita = request.form.get('fecha_cita')
        hora_cita = request.form.get('hora_cita')
        motivo = request.form.get('motivo')
        estado = request.form.get('estado')

        # Verificar si el usuario y el especialista existen
        cur.execute("SELECT id FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cur.fetchone()
        cur.execute("SELECT id FROM especialistas WHERE id = %s", (especialista_id,))
        especialista = cur.fetchone()

        if not usuario:
            flash('El ID de usuario no existe.', 'danger')
        elif not especialista:
            flash('El ID de especialista no existe.', 'danger')
        else:
            try:
                if action == 'add':
                    cur.callproc('CrearCita', [usuario_id, especialista_id, fecha_cita, hora_cita, motivo])
                elif action == 'update':
                    cur.execute("UPDATE citas SET usuario_id=%s, especialista_id=%s, fecha_cita=%s, hora_cita=%s, motivo=%s, estado=%s WHERE id=%s",
                                (usuario_id, especialista_id, fecha_cita, hora_cita, motivo, estado, cita_id))
                elif action == 'delete':
                    cur.execute("DELETE FROM citas WHERE id=%s", (cita_id,))
                
                mysql.connection.commit()
                flash('Operación realizada con éxito.', 'success')
            except Exception as e:
                mysql.connection.rollback()
                flash(f'Error: {e}', 'danger')

    cur.execute("SELECT * FROM citas")
    citas = cur.fetchall()
    cur.close()
    return render_template('admin_citas.html', citas=citas)


if __name__ == '__main__':
    app.run(debug=True)


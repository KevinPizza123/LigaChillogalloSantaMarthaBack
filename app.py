import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from models import db, Usuario, Equipo, Jugador, Arbitro, Partido, Gol, TablaPosiciones

app = Flask(__name__)
app.secret_key = 'liga_chillogallo_secret_key'

# Configuración de base de datos SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'liga.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración para subida de fotos de jugadores
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)

def archivo_permitido(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==========================================
# RUTAS PÚBLICAS Y VISTAS DE NAVEGACIÓN
# ==========================================

@app.route('/')
def index():
    return redirect(url_for('ver_tablas'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        pwd = request.form.get('password')
        usuario = Usuario.query.filter_by(username=user, password=pwd).first()
        if usuario:
            session['usuario_id'] = usuario.id
            session['username'] = usuario.username
            session['rol'] = usuario.rol
            flash('¡Bienvenido al sistema!', 'success')
            return redirect(url_for('ver_tablas'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('login'))

@app.route('/tablas')
def ver_tablas():
    tabla_masc = TablaPosiciones.query.filter_by(genero='Masculino').order_by(TablaPosiciones.pts.desc(), TablaPosiciones.dg.desc()).all()
    tabla_fem = TablaPosiciones.query.filter_by(genero='Femenino').order_by(TablaPosiciones.pts.desc(), TablaPosiciones.dg.desc()).all()
    return render_template('tablas.html', tabla_masc=tabla_masc, tabla_fem=tabla_fem)

@app.route('/goleadores')
def ver_goleadores():
    jugadores = Jugador.query.all()
    goleadores_masc = []
    goleadores_fem = []
    
    for j in jugadores:
        tot_goles = len(j.goles_lista)
        if tot_goles > 0:
            item = {'nombre': j.nombre, 'equipo': j.equipo.nombre, 'goles': tot_goles}
            if j.equipo.genero == 'Masculino':
                goleadores_masc.append(item)
            else:
                goleadores_fem.append(item)
                
    goleadores_masc = sorted(goleadores_masc, key=lambda x: x['goles'], reverse=True)
    goleadores_fem = sorted(goleadores_fem, key=lambda x: x['goles'], reverse=True)
    
    return render_template('goleadores.html', masculinos=goleadores_masc, femeninos=goleadores_fem)

# ==========================================
# PANEL MESA DE VOCALÍA Y REGISTRO DE ACTAS
# ==========================================

@app.route('/vocalia')
def panel_vocalia():
    if 'username' not in session:
        return redirect(url_for('login'))
    partidos_pendientes = Partido.query.filter_by(estado='Pendiente').order_by(Partido.fecha_numero).all()
    return render_template('vocalia.html', partidos=partidos_pendientes)

@app.route('/vocalia/acta/<int:partido_id>')
def llenar_acta(partido_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    partido = db.session.get(Partido, partido_id)
    if not partido:
        flash('Partido no encontrado', 'error')
        return redirect(url_for('panel_vocalia'))
        
    jug_local = Jugador.query.filter_by(equipo_id=partido.equipo_local_id).all()
    jug_vis = Jugador.query.filter_by(equipo_id=partido.equipo_visitante_id).all()
    return render_template('acta_partido.html', partido=partido, jug_local=jug_local, jug_vis=jug_vis)

@app.route('/vocalia/guardar-acta/<int:partido_id>', methods=['POST'])
def guardar_acta(partido_id):
    if 'username' not in session:
        return redirect(url_for('login'))
        
    partido = db.session.get(Partido, partido_id)
    if not partido:
        return redirect(url_for('panel_vocalia'))
    
    partido.dia_juego = request.form.get('dia_juego')
    partido.hora_inicio = request.form.get('hora_inicio')
    partido.hora_fin = request.form.get('hora_fin')
    
    partido.goles_local = int(request.form.get('goles_local', 0))
    partido.goles_visitante = int(request.form.get('goles_visitante', 0))
    
    partido.amarillas_local = int(request.form.get('amarillas_local', 0))
    partido.rojas_local = int(request.form.get('rojas_local', 0))
    partido.amarillas_visitante = int(request.form.get('amarillas_visitante', 0))
    partido.rojas_visitante = int(request.form.get('rojas_visitante', 0))
    
    partido.observaciones = request.form.get('observaciones', '')
    partido.firma_local = request.form.get('firma_local')
    partido.firma_visitante = request.form.get('firma_visitante')
    partido.estado = 'Jugado'
    
    # Limpiar goles guardados previamente si reeditan el acta
    Gol.query.filter_by(partido_id=partido.id).delete()
    
    # Goles individuales (Local)
    jug_local = Jugador.query.filter_by(equipo_id=partido.equipo_local_id).all()
    for j in jug_local:
        cant_goles = int(request.form.get(f'goles_jugador_{j.id}', 0))
        for _ in range(cant_goles):
            nuevo_gol = Gol(partido_id=partido.id, jugador_id=j.id, equipo_id=j.equipo_id)
            db.session.add(nuevo_gol)

    # Goles individuales (Visitante)
    jug_vis = Jugador.query.filter_by(equipo_id=partido.equipo_visitante_id).all()
    for j in jug_vis:
        cant_goles = int(request.form.get(f'goles_jugador_{j.id}', 0))
        for _ in range(cant_goles):
            nuevo_gol = Gol(partido_id=partido.id, jugador_id=j.id, equipo_id=j.equipo_id)
            db.session.add(nuevo_gol)

    db.session.commit()
    recalcular_tabla(partido.genero)
    
    flash('¡Acta guardada exitosamente!', 'success')
    return redirect(url_for('vocalias_realizadas'))

@app.route('/vocalias/realizadas')
def vocalias_realizadas():
    partidos_jugados = Partido.query.filter_by(estado='Jugado').order_by(Partido.fecha_numero.desc()).all()
    return render_template('vocalias_realizadas.html', partidos=partidos_jugados)

@app.route('/vocalia/pdf/<int:partido_id>')
def ver_acta_pdf(partido_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    partido = db.session.get(Partido, partido_id)
    if not partido:
        return redirect(url_for('vocalias_realizadas'))
        
    jug_local = Jugador.query.filter_by(equipo_id=partido.equipo_local_id).all()
    jug_vis = Jugador.query.filter_by(equipo_id=partido.equipo_visitante_id).all()
    return render_template('acta_pdf.html', partido=partido, jug_local=jug_local, jug_vis=jug_vis)

# ==========================================
# PANEL ADMINISTRATIVO Y CALENDARIOS
# ==========================================

@app.route('/admin')
def panel_admin():
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
    equipos = Equipo.query.order_by(Equipo.nombre).all()
    arbitros = Arbitro.query.order_by(Arbitro.nombre).all()
    return render_template('admin.html', equipos=equipos, arbitros=arbitros)

@app.route('/admin/registrar-equipo', methods=['POST'])
def registrar_equipo():
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
    nombre = request.form.get('nombre')
    genero = request.form.get('genero')
    if nombre and genero:
        nuevo_e = Equipo(nombre=nombre, genero=genero)
        db.session.add(nuevo_e)
        db.session.commit()
        # Inicializar en tabla de posiciones
        nueva_pos = TablaPosiciones(equipo_id=nuevo_e.id, genero=genero)
        db.session.add(nueva_pos)
        db.session.commit()
        flash('Equipo registrado con éxito', 'success')
    return redirect(url_for('panel_admin'))

@app.route('/admin/editar-equipo/<int:equipo_id>', methods=['POST'])
def editar_equipo(equipo_id):
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    equipo = db.session.get(Equipo, equipo_id)
    if equipo:
        equipo.nombre = request.form.get('nombre')
        equipo.genero = request.form.get('genero')
        db.session.commit()
        flash('Equipo actualizado correctamente', 'success')
        
    return redirect(url_for('panel_admin'))

@app.route('/admin/eliminar-equipo/<int:equipo_id>', methods=['POST'])
def eliminar_equipo(equipo_id):
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    equipo = db.session.get(Equipo, equipo_id)
    if equipo:
        TablaPosiciones.query.filter_by(equipo_id=equipo.id).delete()
        Jugador.query.filter_by(equipo_id=equipo.id).delete()
        db.session.delete(equipo)
        db.session.commit()
        flash('Equipo y sus registros fueron eliminados', 'success')
        
    return redirect(url_for('panel_admin'))

@app.route('/admin/registrar-jugador', methods=['POST'])
def registrar_jugador():
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    nombre = request.form.get('nombre')
    cedula = request.form.get('cedula')
    dorsal = request.form.get('dorsal')
    equipo_id = request.form.get('equipo_id')
    
    nombre_foto = 'default_player.png'
    file = request.files.get('foto')
    if file and archivo_permitido(file.filename):
        filename = secure_filename(f"{cedula}_{file.filename}")
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        nombre_foto = filename

    if nombre and equipo_id:
        nuevo_j = Jugador(nombre=nombre, cedula=cedula, dorsal=dorsal, foto=nombre_foto, equipo_id=int(equipo_id))
        db.session.add(nuevo_j)
        db.session.commit()
        flash('Jugador inscrito correctamente', 'success')
        
    return redirect(url_for('panel_admin'))

@app.route('/admin/editar-jugador/<int:jugador_id>', methods=['POST'])
def editar_jugador(jugador_id):
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    jugador = db.session.get(Jugador, jugador_id)
    if jugador:
        jugador.nombre = request.form.get('nombre')
        jugador.cedula = request.form.get('cedula')
        jugador.dorsal = request.form.get('dorsal')
        jugador.equipo_id = int(request.form.get('equipo_id'))
        
        file = request.files.get('foto')
        if file and archivo_permitido(file.filename):
            filename = secure_filename(f"{jugador.cedula}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            jugador.foto = filename

        db.session.commit()
        flash('Datos del jugador actualizados', 'success')
        
    return redirect(url_for('panel_admin'))

@app.route('/admin/eliminar-jugador/<int:jugador_id>', methods=['POST'])
def eliminar_jugador(jugador_id):
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    jugador = db.session.get(Jugador, jugador_id)
    if jugador:
        db.session.delete(jugador)
        db.session.commit()
        flash('Jugador eliminado del registro', 'success')
        
    return redirect(url_for('panel_admin'))

@app.route('/admin/calendario')
def ver_calendario():
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    p_masc = Partido.query.filter_by(genero='Masculino').order_by(Partido.fecha_numero, Partido.id).all()
    p_fem = Partido.query.filter_by(genero='Femenino').order_by(Partido.fecha_numero, Partido.id).all()
    
    f_masc = sorted(list(set([p.fecha_numero for p in p_masc])))
    f_fem = sorted(list(set([p.fecha_numero for p in p_fem])))
    
    eq_masc = Equipo.query.filter_by(genero='Masculino').order_by(Equipo.nombre).all()
    eq_fem = Equipo.query.filter_by(genero='Femenino').order_by(Equipo.nombre).all()
    arbitros_lista = Arbitro.query.order_by(Arbitro.nombre).all()
    
    json_masc = [{"id": e.id, "nombre": e.nombre} for e in eq_masc]
    json_fem = [{"id": e.id, "nombre": e.nombre} for e in eq_fem]
    
    return render_template('calendario.html', 
                           partidos_masc=p_masc, 
                           partidos_fem=p_fem, 
                           fechas_masc=f_masc, 
                           fechas_fem=f_fem,
                           equipos_masc=eq_masc,
                           equipos_fem=eq_fem,
                           json_masc=json_masc,
                           json_fem=json_fem,
                           arbitros=arbitros_lista)

@app.route('/admin/crear-partido-manual', methods=['POST'])
def crear_partido_manual():
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    fecha_num = int(request.form.get('fecha_numero', 1))
    genero = request.form.get('genero')
    local_id = int(request.form.get('equipo_local_id'))
    visitante_id = int(request.form.get('equipo_visitante_id'))
    vocal_id = int(request.form.get('equipo_vocal_id'))
    
    dia_juego = request.form.get('dia_juego', 'Por definir')
    hora_inicio = request.form.get('hora_inicio', '')
    hora_fin = request.form.get('hora_fin', '')
    
    arbitro_id_val = request.form.get('arbitro_id')
    arb_id = int(arbitro_id_val) if arbitro_id_val else None
    
    if local_id == visitante_id:
        flash('El equipo local y el visitante no pueden ser el mismo.', 'error')
        return redirect(url_for('ver_calendario'))
        
    try:
        nuevo_partido = Partido(
            fecha_numero=fecha_num,
            genero=genero,
            equipo_local_id=local_id,
            equipo_visitante_id=visitante_id,
            equipo_vocal_id=vocal_id,
            arbitro_id=arb_id,
            dia_juego=dia_juego,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            estado='Pendiente'
        )
        db.session.add(nuevo_partido)
        db.session.commit()
        flash('¡Partido registrado con éxito!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al registrar el partido.', 'error')
        
    return redirect(url_for('ver_calendario'))

@app.route('/admin/eliminar-partido/<int:partido_id>', methods=['POST'])
def eliminar_partido(partido_id):
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    partido = db.session.get(Partido, partido_id)
    if partido:
        db.session.delete(partido)
        db.session.commit()
        flash('Partido eliminado.', 'success')
    return redirect(url_for('ver_calendario'))

@app.route('/admin/arbitros', methods=['GET', 'POST'])
def gestionar_arbitros():
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        if nombre:
            nuevo_arb = Arbitro(nombre=nombre, telefono=telefono)
            db.session.add(nuevo_arb)
            db.session.commit()
            flash('Árbitro registrado exitosamente', 'success')
            
    arbitros = Arbitro.query.order_by(Arbitro.nombre).all()
    return render_template('arbitros.html', arbitros=arbitros)

@app.route('/admin/editar-arbitro/<int:arbitro_id>', methods=['POST'])
def editar_arbitro(arbitro_id):
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    arbitro = db.session.get(Arbitro, arbitro_id)
    if arbitro:
        arbitro.nombre = request.form.get('nombre')
        arbitro.telefono = request.form.get('telefono')
        db.session.commit()
        flash('Árbitro actualizado', 'success')
        
    return redirect(url_for('gestionar_arbitros'))

@app.route('/admin/eliminar-arbitro/<int:arbitro_id>', methods=['POST'])
def eliminar_arbitro(arbitro_id):
    if 'username' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    arbitro = db.session.get(Arbitro, arbitro_id)
    if arbitro:
        db.session.delete(arbitro)
        db.session.commit()
        flash('Árbitro eliminado', 'success')
        
    return redirect(url_for('gestionar_arbitros'))

# ==========================================
# RUTAS API REST PARA LA APP EN REACT NATIVE
# ==========================================

@app.route('/api/partidos', methods=['GET'])
def api_partidos():
    partidos = Partido.query.order_by(Partido.fecha_numero, Partido.id).all()
    data = []
    for p in partidos:
        data.append({
            "id": p.id,
            "fecha_numero": p.fecha_numero,
            "genero": p.genero,
            "dia_juego": p.dia_juego,
            "hora_inicio": p.hora_inicio or "--:--",
            "hora_fin": p.hora_fin or "--:--",
            "local": p.equipo_local.nombre,
            "visitante": p.equipo_visitante.nombre,
            "vocalia": p.equipo_vocal.nombre if p.equipo_vocal else "Por definir",
            "arbitro": p.arbitro.nombre if p.arbitro else "Por asignar",
            "goles_local": p.goles_local,
            "goles_visitante": p.goles_visitante,
            "estado": p.estado
        })
    return jsonify(data)

@app.route('/api/tablas', methods=['GET'])
def api_tablas():
    tabla_masc = TablaPosiciones.query.filter_by(genero='Masculino').order_by(TablaPosiciones.pts.desc(), TablaPosiciones.dg.desc()).all()
    tabla_fem = TablaPosiciones.query.filter_by(genero='Femenino').order_by(TablaPosiciones.pts.desc(), TablaPosiciones.dg.desc()).all()
    
    def serializar(filas):
        return [{
            "equipo": f.equipo.nombre,
            "pj": f.pj, "pg": f.pg, "pe": f.pe, "pp": f.pp,
            "gf": f.gf, "gc": f.gc, "dg": f.dg, "pts": f.pts
        } for f in filas]

    return jsonify({
        "masculino": serializar(tabla_masc),
        "femenino": serializar(tabla_fem)
    })

@app.route('/api/goleadores', methods=['GET'])
def api_goleadores():
    jugadores = Jugador.query.all()
    masc = []
    fem = []
    
    for j in jugadores:
        tot_goles = len(j.goles_lista)
        if tot_goles > 0:
            item = {"nombre": j.nombre, "equipo": j.equipo.nombre, "goles": tot_goles}
            if j.equipo.genero == 'Masculino':
                masc.append(item)
            else:
                fem.append(item)
                
    masc = sorted(masc, key=lambda x: x['goles'], reverse=True)
    fem = sorted(fem, key=lambda x: x['goles'], reverse=True)
    
    return jsonify({"masculino": masc, "femenino": fem})

# ==========================================
# FUNCIÓN AUXILIAR RECALCULAR TABLA DE POSICIONES
# ==========================================

def recalcular_tabla(genero):
    partidos = Partido.query.filter_by(genero=genero, estado='Jugado').all()
    posiciones = TablaPosiciones.query.filter_by(genero=genero).all()
    
    stats = {}
    for pos in posiciones:
        stats[pos.equipo_id] = {'pj': 0, 'pg': 0, 'pe': 0, 'pp': 0, 'gf': 0, 'gc': 0, 'pts': 0}
        
    for p in partidos:
        e1 = p.equipo_local_id
        e2 = p.equipo_visitante_id
        g1 = p.goles_local
        g2 = p.goles_visitante
        
        if e1 in stats and e2 in stats:
            stats[e1]['pj'] += 1
            stats[e2]['pj'] += 1
            stats[e1]['gf'] += g1
            stats[e1]['gc'] += g2
            stats[e2]['gf'] += g2
            stats[e2]['gc'] += g1
            
            if g1 > g2:
                stats[e1]['pg'] += 1
                stats[e1]['pts'] += 3
                stats[e2]['pp'] += 1
            elif g2 > g1:
                stats[e2]['pg'] += 1
                stats[e2]['pts'] += 3
                stats[e1]['pp'] += 1
            else:
                stats[e1]['pe'] += 1
                stats[e2]['pe'] += 1
                stats[e1]['pts'] += 1
                stats[e2]['pts'] += 1

    for pos in posiciones:
        st = stats.get(pos.equipo_id, {'pj': 0, 'pg': 0, 'pe': 0, 'pp': 0, 'gf': 0, 'gc': 0, 'pts': 0})
        pos.pj = st['pj']
        pos.pg = st['pg']
        pos.pe = st['pe']
        pos.pp = st['pp']
        pos.gf = st['gf']
        pos.gc = st['gc']
        pos.dg = st['gf'] - st['gc']
        pos.pts = st['pts']
        
    db.session.commit()

# ==========================================
# ARRANQUE DE SERVIDOR CON SOPORTE RED LOCAL
# ==========================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
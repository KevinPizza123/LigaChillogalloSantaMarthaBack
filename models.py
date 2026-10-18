from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), default='vocal')

class Equipo(db.Model):
    __tablename__ = 'equipos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    genero = db.Column(db.String(10), nullable=False)
    escudo = db.Column(db.String(255), default='default.png')
    
    jugadores = db.relationship('Jugador', backref='equipo', lazy=True)

class Jugador(db.Model):
    __tablename__ = 'jugadores'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    cedula = db.Column(db.String(20), nullable=True)
    dorsal = db.Column(db.Integer, nullable=True)
    foto = db.Column(db.String(255), default='default_player.png')  # Nueva foto
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=False)

class Arbitro(db.Model):
    __tablename__ = 'arbitros'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)

class Partido(db.Model):
    __tablename__ = 'partidos'
    id = db.Column(db.Integer, primary_key=True)
    fecha_numero = db.Column(db.Integer, nullable=False)
    genero = db.Column(db.String(10), nullable=False)
    
    equipo_local_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=False)
    equipo_visitante_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=False)
    equipo_vocal_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=False)
    arbitro_id = db.Column(db.Integer, db.ForeignKey('arbitros.id'), nullable=True)
    
    dia_juego = db.Column(db.String(50), default="Por definir")
    hora_inicio = db.Column(db.String(20), nullable=True)
    hora_fin = db.Column(db.String(20), nullable=True)
    
    goles_local = db.Column(db.Integer, default=0)
    goles_visitante = db.Column(db.Integer, default=0)
    
    amarillas_local = db.Column(db.Integer, default=0)
    rojas_local = db.Column(db.Integer, default=0)
    amarillas_visitante = db.Column(db.Integer, default=0)
    rojas_visitante = db.Column(db.Integer, default=0)
    
    observaciones = db.Column(db.Text, nullable=True)
    firma_local = db.Column(db.String(100), nullable=True)
    firma_visitante = db.Column(db.String(100), nullable=True)
    
    estado = db.Column(db.String(20), default='Pendiente')

    equipo_local = db.relationship('Equipo', foreign_keys=[equipo_local_id])
    equipo_visitante = db.relationship('Equipo', foreign_keys=[equipo_visitante_id])
    equipo_vocal = db.relationship('Equipo', foreign_keys=[equipo_vocal_id])
    arbitro = db.relationship('Arbitro', foreign_keys=[arbitro_id])
    goles_lista = db.relationship('Gol', backref='partido', lazy=True, cascade="all, delete-orphan")

    @property
    def multa_local(self):
        return (self.amarillas_local * 0.50) + (self.rojas_local * 1.00)

    @property
    def multa_visitante(self):
        return (self.amarillas_visitante * 0.50) + (self.rojas_visitante * 1.00)

class Gol(db.Model):
    __tablename__ = 'goles'
    id = db.Column(db.Integer, primary_key=True)
    partido_id = db.Column(db.Integer, db.ForeignKey('partidos.id'), nullable=False)
    jugador_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'), nullable=False)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=False)
    
    jugador = db.relationship('Jugador', backref='goles_lista')

class TablaPosiciones(db.Model):
    __tablename__ = 'tabla_posiciones'
    id = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=False)
    genero = db.Column(db.String(10), nullable=False)
    pj = db.Column(db.Integer, default=0)
    pg = db.Column(db.Integer, default=0)
    pe = db.Column(db.Integer, default=0)
    pp = db.Column(db.Integer, default=0)
    gf = db.Column(db.Integer, default=0)
    gc = db.Column(db.Integer, default=0)
    dg = db.Column(db.Integer, default=0)
    pts = db.Column(db.Integer, default=0)

    equipo = db.relationship('Equipo', backref='posicion')
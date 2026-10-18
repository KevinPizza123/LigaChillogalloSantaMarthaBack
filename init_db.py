from app import app
from models import db, Usuario

with app.app_context():
    # Elimina las tablas existentes y crea las nuevas estructuras
    db.drop_all()
    db.create_all()

    # Crear usuario administrador por defecto
    admin = Usuario(username='admin', password='123', rol='admin')
    # Crear usuario vocal por defecto
    vocal = Usuario(username='vocal', password='123', rol='vocal')

    db.session.add(admin)
    db.session.add(vocal)
    db.session.commit()

    print("¡Base de datos reiniciada con éxito y usuarios por defecto creados!")
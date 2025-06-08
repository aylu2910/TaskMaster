import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import re  # Para validar el correo electrónico
from datetime import datetime, date
from flask_wtf.csrf import CSRFProtect # Import CSRFProtect
from flask_migrate import Migrate # Import Migrate

from models import db, User, Task # Import Task model
from forms import TaskForm, RegistrationForm # Import TaskForm and RegistrationForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'  # ¡Cambia esto por una clave segura!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Usaremos una base de datos SQLite local
db.init_app(app) # Initialize db with app
csrf = CSRFProtect(app) # Initialize CSRF protection
migrate = Migrate(app, db) # Initialize Flask-Migrate

# Función para validar la fortaleza de la contraseña
def is_password_strong(password):
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    if not re.search(r"[A-Z]", password):
        return False, "La contraseña debe contener al menos una letra mayúscula."
    if not re.search(r"[a-z]", password):
        return False, "La contraseña debe contener al menos una letra minúscula."
    if not re.search(r"[0-9]", password):
        return False, "La contraseña debe contener al menos un número."
    if not re.search(r"[!@#$%^&*]", password):
        return False, "La contraseña debe contener al menos un carácter especial."
    return True, None

# Ruta raíz para redirigir al login o a las tareas si ya está logueado
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('tasks'))
    else:
        return redirect(url_for('login'))

# Ruta para la página de registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        confirm_password = form.confirm_password.data

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return render_template('register.html', form=form, error='Correo electrónico no válido.')

        password_strength, error_message = is_password_strong(password)
        if not password_strength:
            return render_template('register.html', form=form, error=error_message)

        if password != confirm_password:
            return render_template('register.html', form=form, error='Las contraseñas no coinciden.')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template('register.html', form=form, error='El correo electrónico ya está registrado.')

        hashed_password = generate_password_hash(password)
        new_user = User(email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

# Ruta para la página de inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('tasks'))  # Redirigir a la página de tareas
        else:
            return render_template('login.html', error='Credenciales inválidas.')

    return render_template('login.html')

# Ruta para la página de tareas (requiere inicio de sesión)
@app.route('/tasks')
def tasks():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    
    # Get filter values from query parameters
    status_filter = request.args.get('status_filter', 'Todos') # Default to 'Todos'
    priority_filter = request.args.get('priority_filter', 'Todas') # Default to 'Todas'

    # Base query
    query = Task.query.filter_by(author=user)

    # Apply status filter
    if status_filter == 'Pendientes':
        query = query.filter_by(is_completed=False)
    elif status_filter == 'Completadas':
        query = query.filter_by(is_completed=True)
    # 'Todos' doesn't require filtering by status

    # Apply priority filter
    if priority_filter in ['Alta', 'Media', 'Baja']:
        query = query.filter_by(priority=priority_filter)
    # 'Todas' doesn't require filtering by priority

    # Order and execute query
    user_tasks = query.order_by(Task.created_at.desc()).all()

    # Pass tasks and current filter values to the template
    return render_template(
        'tasks.html', 
        tasks=user_tasks, 
        current_status=status_filter,
        current_priority=priority_filter,
        today=date.today()
    ) 

# Ruta para crear una nueva tarea
@app.route('/create_task', methods=['GET', 'POST'])
def create_task():
    if 'user_id' not in session:
        return redirect(url_for('login')) # Redirigir si no está logueado

    form = TaskForm()
    if form.validate_on_submit():
        title = form.title.data
        description = form.description.data
        due_date = form.due_date.data
        priority = form.priority.data
        user_id = session['user_id']

        new_task = Task(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            user_id=user_id
        )
        db.session.add(new_task)
        db.session.commit()
        flash('¡Tarea creada exitosamente!', 'success')
        return redirect(url_for('tasks'))

    return render_template('create_task.html', form=form)

# Ruta API para obtener detalles de una tarea
@app.route('/task_details/<int:task_id>')
def task_details(task_id):
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 401

    user_id = session['user_id']
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()

    if not task:
        return jsonify({"error": "Tarea no encontrada o no pertenece al usuario"}), 404

    return jsonify({
        'id': task.id,
        'title': task.title,
        'description': task.description or '-',
        'due_date': task.due_date.strftime('%d/%m/%Y') if task.due_date else '-',
        'priority': task.priority,
        'is_completed': task.is_completed # Return the actual status
    })

# Ruta para cambiar el estado de una tarea (PUT)
@csrf.exempt # Exempt this route from CSRF protection for simplicity with fetch API
@app.route('/toggle_task_status/<int:task_id>', methods=['PUT'])
def toggle_task_status(task_id):
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 401

    user_id = session['user_id']
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()

    if not task:
        return jsonify({"error": "Tarea no encontrada o no pertenece al usuario"}), 404

    try:
        # Toggle the status
        task.is_completed = not task.is_completed
        db.session.commit()
        # Return the new status
        return jsonify({
            "success": True, 
            "new_status": task.is_completed, 
            "message": "Estado de la tarea actualizado"
        }), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error toggling status for task {task_id}: {e}")
        return jsonify({"error": "Error al actualizar el estado de la tarea"}), 500

# Ruta para editar una tarea existente
@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    if 'user_id' not in session:
        flash('Debes iniciar sesión para editar tareas.', 'warning')
        return redirect(url_for('login'))

    task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()
    form = TaskForm(obj=task) # Pre-populate form with task data on GET

    if form.validate_on_submit(): # This runs on POST request if valid
        try:
            task.title = form.title.data
            task.description = form.description.data
            task.due_date = form.due_date.data
            task.priority = form.priority.data
            db.session.commit()
            flash('¡Tarea actualizada exitosamente!', 'success')
            return redirect(url_for('tasks'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating task {task_id}: {e}")
            flash('Error al actualizar la tarea.', 'danger')

    # For GET request, or if POST validation fails, render the edit form
    # If it's a GET, the form is pre-populated by TaskForm(obj=task)
    # If POST fails, WTForms keeps the submitted data in the form fields
    return render_template('edit_task.html', form=form, task_id=task_id)

# Ruta para eliminar una tarea (DELETE)
@csrf.exempt # Exempt this route from CSRF protection
@app.route('/delete_task/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'user_id' not in session:
        return jsonify({"error": "No autorizado"}), 401

    user_id = session['user_id']
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()

    if not task:
        return jsonify({"error": "Tarea no encontrada o no pertenece al usuario"}), 404

    try:
        db.session.delete(task)
        db.session.commit()
        return jsonify({"success": True, "message": "Tarea eliminada exitosamente"}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting task: {e}") # Log the error for debugging
        return jsonify({"error": "Error al eliminar la tarea"}), 500

# Ruta para el cierre de sesión
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Has cerrado sesión.', 'info') # Mensaje opcional de cierre de sesión
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Crea la base de datos si no existe
    app.run(debug=True)
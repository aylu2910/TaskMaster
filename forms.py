from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SelectField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from datetime import date, timedelta

class TaskForm(FlaskForm):
    title = StringField('Título', validators=[
        DataRequired(message="El título es requerido."), 
        Length(max=100, message="El título no puede exceder los 100 caracteres.")
    ])
    description = TextAreaField('Descripción', validators=[
        Length(max=500, message="La descripción no puede exceder los 500 caracteres."),
        Optional()
    ])
    due_date = DateField('Fecha de Vencimiento', format='%Y-%m-%d', validators=[Optional()])
    priority = SelectField('Prioridad', choices=[('Alta', 'Alta'), ('Media', 'Media'), ('Baja', 'Baja')], default='Media', validators=[DataRequired()])
    submit = SubmitField('Guardar Tarea')

    def validate_due_date(self, field):
        if field.data:
            today = date.today()
            if field.data < today:
                raise ValidationError('La fecha de vencimiento no puede ser en el pasado.')
            
            one_year_from_today = today + timedelta(days=365)
            if field.data > one_year_from_today:
                raise ValidationError('La fecha de vencimiento no puede ser más de un año en el futuro.')

class RegistrationForm(FlaskForm):
    email = StringField('Correo Electrónico', validators=[
        DataRequired(message="El correo electrónico es requerido."),
        Length(max=120, message="El correo electrónico no puede exceder los 120 caracteres.")
    ])
    password = PasswordField('Contraseña', validators=[
        DataRequired(message="La contraseña es requerida."),
        Length(min=8, message="La contraseña debe tener al menos 8 caracteres.")
    ])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[
        DataRequired(message="La confirmación de la contraseña es requerida."),
        Length(min=8, message="La confirmación de la contraseña debe tener al menos 8 caracteres.")
    ])
    submit = SubmitField('Registrarse')
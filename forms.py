from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, IntegerField, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    qualification = StringField('Qualification')
    dob = DateField('Date of Birth', format='%Y-%m-%d')
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists.')

class SubjectForm(FlaskForm):
    name = StringField('Subject Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Save Subject')

class ChapterForm(FlaskForm):
    name = StringField('Chapter Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    subject = SelectField('Subject', coerce=int)
    submit = SubmitField('Save Chapter')

class QuizForm(FlaskForm):
    title = StringField('Quiz Title', validators=[DataRequired()])
    chapter = SelectField('Chapter', coerce=int)
    duration = IntegerField('Duration (minutes)', validators=[DataRequired()])
    submit = SubmitField('Save Quiz')

class QuestionForm(FlaskForm):
    text = TextAreaField('Question Text', validators=[DataRequired()])
    option1 = StringField('Option 1', validators=[DataRequired()])
    option2 = StringField('Option 2', validators=[DataRequired()])
    option3 = StringField('Option 3')
    option4 = StringField('Option 4')
    correct_option = SelectField('Correct Option', choices=[
        (1, 'Option 1'), 
        (2, 'Option 2'), 
        (3, 'Option 3'), 
        (4, 'Option 4')
    ], coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save Question')
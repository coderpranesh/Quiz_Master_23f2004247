from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Subject, Chapter, Quiz, Question, Score
from forms import LoginForm, RegistrationForm, SubjectForm, ChapterForm, QuizForm, QuestionForm
from datetime import datetime, timedelta
import math


app = Flask(__name__)
# app.jinja_env.filters['datetimeformat'] = datetimeformat
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

csrf = CSRFProtect(app)
db.init_app(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.template_filter('datetimeformat')
def datetimeformat(value, fmt='%Y-%m-%d %H:%M'):
    """Custom datetime formatter filter"""
    if not value:
        return ""
    try:
        return value.strftime(fmt)
    except AttributeError:
        return ""

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_admin():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(is_admin=True).first():
            admin = User(
                username='admin@quizmaster.com',
                full_name='Admin User',
                is_admin=True
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            db.session.commit()

create_admin()

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return "success"
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('auth/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            full_name=form.full_name.data,
            qualification=form.qualification.data,
            dob=form.dob.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(debug=True, port=5003)
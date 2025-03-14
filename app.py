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

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_dashboard'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    search_query = request.args.get('search', '')
    
    # Query users with their scores
    users_query = User.query.filter(or_(
        User.username.ilike(f'%{search_query}%'),
        User.full_name.ilike(f'%{search_query}%')
    ))
    
    user_scores = []
    for user in users_query.all():
        # Get scores ordered by latest first
        scores = Score.query.filter_by(user_id=user.id)\
            .order_by(Score.timestamp.desc())\
            .all()
        
        # Calculate scores
        latest_score = None
        average_score = None
        
        if scores:
            # Calculate latest score percentage
            latest = scores[0]
            latest_score = (latest.score / latest.total_questions) * 100
            
            # Calculate average score
            total_percentage = sum(
                (s.score / s.total_questions) * 100 
                for s in scores
                if s.total_questions > 0  # Prevent division by zero
            )
            average_score = total_percentage / len(scores)
        
        user_scores.append({
            'user': user,
            'scores': scores,
            'latest_score': latest_score,
            'average_score': average_score
        })
    
    # Statistics
    stats = {
        'users': User.query.count(),
        'subjects': Subject.query.count(),
        'quizzes': Quiz.query.count(),
        'questions': Question.query.count()
    }
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         user_scores=user_scores,
                         search_query=search_query)





if __name__ == '__main__':
    app.run(debug=True, port=5003)
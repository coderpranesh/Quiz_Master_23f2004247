from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Subject, Chapter, Quiz, Question, Score
from forms import LoginForm, RegistrationForm, SubjectForm, ChapterForm, QuizForm, QuestionForm
from datetime import datetime, timedelta
import math
from sqlalchemy import or_


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
        return redirect(url_for('dashboard'))
    
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


@app.route('/admin/delete-score/<int:score_id>', methods=['POST'])
@login_required
def admin_delete_score(score_id):
    if not current_user.is_admin:
        abort(403)
    
    score = Score.query.get_or_404(score_id)
    
    try:
        db.session.delete(score)
        db.session.commit()
        flash('Quiz attempt deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting quiz attempt: {str(e)}', 'danger')
    
    return redirect(url_for('admin_dashboard'))


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


@app.route('/admin/users/<int:user_id>')
@login_required
def view_user(user_id):
    if not current_user.is_admin:
        abort(403)
    
    user = User.query.get_or_404(user_id)  # Get user from database
    return render_template('admin/user_detail.html', user=user)  # Pass to template


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        abort(403)
    
    user = User.query.get_or_404(user_id)
    
    try:
        # Delete user and all related scores
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('admin_dashboard'))


# Admin Routes
# @app.route('/admin/dashboard')
# @login_required
# def admin_dashboard():
#     if not current_user.is_admin:
#         return redirect(url_for('user_dashboard'))
    
#     stats = {
#         'users': User.query.count(),
#         'subjects': Subject.query.count(),
#         'quizzes': Quiz.query.count(),
#         'questions': Question.query.count()
#     }
#     return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/subjects', methods=['GET', 'POST'])
@login_required
def manage_subjects():
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    form = SubjectForm()
    if form.validate_on_submit():
        subject = Subject(name=form.name.data, description=form.description.data)
        db.session.add(subject)
        db.session.commit()
        flash('Subject created successfully!', 'success')
        return redirect(url_for('manage_subjects'))
    
    subjects = Subject.query.all()
    return render_template('admin/manage_subjects.html', form=form, subjects=subjects)

@app.route('/admin/chapters', methods=['GET', 'POST'])
@login_required
def manage_chapters():
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    form = ChapterForm()
    form.subject.choices = [(s.id, s.name) for s in Subject.query.all()]
    
    if form.validate_on_submit():
        chapter = Chapter(
            name=form.name.data,
            description=form.description.data,
            subject_id=form.subject.data
        )
        db.session.add(chapter)
        db.session.commit()
        flash('Chapter created successfully!', 'success')
        return redirect(url_for('manage_chapters'))
    
    chapters = Chapter.query.all()
    return render_template('admin/manage_chapters.html', form=form, chapters=chapters)

@app.route('/admin/quizzes', methods=['GET', 'POST'])
@login_required
def manage_quizzes():
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    form = QuizForm()
    form.chapter.choices = [(c.id, f"{c.subject.name} - {c.name}") for c in Chapter.query.join(Subject).all()]
    
    if form.validate_on_submit():
        quiz = Quiz(
            title=form.title.data,
            chapter_id=form.chapter.data,
            duration=form.duration.data
        )
        db.session.add(quiz)
        db.session.commit()
        flash('Quiz created successfully!', 'success')
        return redirect(url_for('manage_quizzes'))
    
    quizzes = Quiz.query.all()
    return render_template('admin/manage_quizzes.html', form=form, quizzes=quizzes)

@app.route('/admin/questions/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def manage_questions(quiz_id):
    if not current_user.is_admin:
        return redirect(url_for('user_dashboard'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    form = QuestionForm()
    
    if form.validate_on_submit():
        question = Question(
            text=form.text.data,
            option1=form.option1.data,
            option2=form.option2.data,
            option3=form.option3.data,
            option4=form.option4.data,
            correct_option=form.correct_option.data,
            quiz_id=quiz_id
        )
        db.session.add(question)
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('manage_questions', quiz_id=quiz_id))
    
    questions = quiz.questions
    return render_template('admin/manage_questions.html', form=form, quiz=quiz, questions=questions)


@app.route('/admin/quizzes/delete/<int:quiz_id>')
@login_required
def delete_quiz(quiz_id):
    if not current_user.is_admin:
        abort(403)
    quiz = Quiz.query.get_or_404(quiz_id)
    db.session.delete(quiz)
    db.session.commit()
    flash('Quiz deleted successfully', 'success')
    return redirect(url_for('manage_quizzes'))



@app.route('/admin/chapters/delete/<int:chapter_id>')
@login_required
def delete_chapter(chapter_id):
    if not current_user.is_admin:
        abort(403)
    chapter = Chapter.query.get_or_404(chapter_id)
    db.session.delete(chapter)
    db.session.commit()
    flash('Chapter deleted successfully', 'success')
    return redirect(url_for('manage_chapters'))


@app.route('/admin/subjects/delete/<int:subject_id>')
@login_required
def delete_subject(subject_id):
    if not current_user.is_admin:
        abort(403)
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted successfully', 'success')
    return redirect(url_for('manage_subjects'))

# @app.route('/admin/subjects/edit/<int:quiz_id>', methods=['POST'])
# @login_required
# def edit_subject(quiz_id):
#     if not current_user.is_admin:
#         abort(403)
#     quiz = Subject.query.get_or_404(quiz_id)
#     quiz.name =request.form['name']
#     quiz.description = request.form['description']
#     db.session.commit()
#     flash('Subject updated successfully', 'success')
#     return redirect(url_for('manage_quizzes')) 

# @app.route('/admin/subjects/edit/<int:subject_id>', methods=['POST'])
# @login_required
# def edit_subject(subject_id):
#     if not current_user.is_admin:
#         abort(403)
#     subject = Subject.query.get_or_404(subject_id)
#     subject.name = request.form['name']
#     subject.description = request.form['description']
#     db.session.commit()
#     flash('Subject updated successfully', 'success')
#     return redirect(url_for('manage_subjects'))


@app.route('/admin/subjects/edit/<int:subject_id>', methods=['POST'])
@login_required
def edit_subject(subject_id):
    if not current_user.is_admin:
        abort(403)
    
    subject = Subject.query.get_or_404(subject_id)
    
    try:
        subject.name = request.form['name']
        subject.description = request.form['description']
        db.session.commit()
        flash('Subject updated successfully', 'success')
    except KeyError:
        flash('Invalid form submission', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating subject: {str(e)}', 'danger')
    
    return redirect(url_for('manage_subjects'))




if __name__ == '__main__':
    app.run(debug=True, port=5003)
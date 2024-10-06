# app.py

from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_socketio import SocketIO, emit
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, BooleanField
from wtforms.validators import (
    DataRequired,
    Length,
    Email,
    EqualTo,
    ValidationError,
    NumberRange,
    Optional,
    URL,
)
from dotenv import load_dotenv
import os
from sqlalchemy import event
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or "your_default_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI", "sqlite:///Database.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False



# Initialize Extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "login"  # Redirect to 'login' for @login_required
login_manager.login_message_category = "info"
socketio = SocketIO(app, cors_allowed_origins="*")  # Adjust CORS as needed

# ==========================
# Models
# ==========================

print("Database URI:", app.config["SQLALCHEMY_DATABASE_URI"])

# ==========================
# Model User
# ==========================

class User(UserMixin, db.Model):
    __tablename__ = 'user'  # Changed table name from 'user_table' to 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password = db.Column(db.String(60), nullable=False)
    mailing_list = db.Column(db.Boolean, default=False)  # Add the mailing list column
    is_mod = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)  # Add this field for banning/unbanning users
    is_deleted = db.Column(db.Boolean, default=False)  # Add this field for deleting/restoring users
    last_login = db.Column(db.DateTime)  # To track the last login time
    stock_level = db.Column(db.Integer, default=0)  # Default value could be 0 or any other preferred value
    show_url = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<User('{self.username}', '{self.email}', Moderator: {self.is_mod})>"
    


# ==========================
# Model Message
# ==========================

class Message(db.Model):
    __tablename__ = 'message'  # Table name remains 'message'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Updated ForeignKey to 'user.id'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    visible = db.Column(db.Boolean, default=True)  # New field for visibility

    user = db.relationship('User', backref=db.backref('messages', lazy=True))  # Relationship remains unchanged

    def __repr__(self):
        return f"<Message('{self.content}', '{self.timestamp}')>"

# ==========================
# Forms
# ==========================



# ==========================
# User Registration
# ==========================


class RegistrationForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[DataRequired(), Length(min=2, max=150)],
        filters=[lambda x: x.strip() if x else x]
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(), Length(min=6, max=150)],
        filters=[lambda x: x.strip() if x else x]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password')]
    )
    show_url = StringField('Programmed Show URL', validators=[Optional(), URL(message="Invalid URL format")])  # New field
    mailing_list = BooleanField('Subscribe to Mailing List')  # Add this field to handle the mailing list
    submit = SubmitField('Register')

    # Custom validators to ensure unique username and email
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please choose a different one.')
        

# ==========================
# User Login
# ==========================

class LoginForm(FlaskForm):
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(), Length(min=6, max=150)],
        filters=[lambda x: x.strip() if x else x]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired()]
    )
    submit = SubmitField('Login')


# ==========================
# User Profile
# ==========================

class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[Optional(), Length(min=2, max=20)])
    email = StringField('Email', validators=[Optional(), Email()])
    stock_level = IntegerField('Stock Level', validators=[Optional(), NumberRange(min=0, max=4, message="Stock level must be a positive number")])
    show_url = StringField('Programmed Show URL', validators=[Optional(), URL(message="Invalid URL format")])  # New field
    submit = SubmitField('Update Profile')

# ==========================
# User Loader for Flask-Login
# ==========================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==========================
# Event Listeners
# ==========================

def setup_listeners():
    @event.listens_for(db.engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable foreign key support for SQLite."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

with app.app_context():
    setup_listeners()

# ==========================
# User Ban announcment 
# ==========================

def add_system_message(content):
    system_message = Message(
        content=content,
        timestamp=datetime.utcnow()
    )
    db.session.add(system_message)
    db.session.commit()


# ==========================
# Routes
# ==========================

# ==========================
# Stock Levels
# ==========================
STOCK_LEVEL_LABELS = {
    0: "No Candy",
    1: "Low on Candy",
    2: "Half Left",
    3: "A Lot",
    4: "I could feed a village with all this candy"
}

# ==========================
# Programmed Show
# ==========================


@app.route('/show')
@login_required
def show():
    if current_user.show_url:
        return render_template('show.html', show_url=current_user.show_url)
    else:
        return redirect(url_for('profile'))  # Redirect to profile if no URL is set


# ==========================
# Edit user ADMIN
# ==========================

@app.route("/admin/user/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    if not current_user.is_mod:
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("home"))

    user = User.query.get_or_404(user_id)
    form = RegistrationForm(obj=user)

    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        db.session.commit()
        flash("User details updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_user.html", title="Edit User", form=form, user=user)


# ==========================
# ADMIN FUNCTION USER ACTIVITY
# ==========================

@app.route("/admin/user/activity")
@login_required
def user_activity():
    if not current_user.is_mod:
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("home"))

    users = User.query.order_by(User.last_login.desc()).all()
    return render_template("user_activity.html", users=users)


# ==========================
# ADMIN FUNCTION DELETE USER
# ==========================

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_mod:
        flash('You do not have permission to delete users.', 'danger')
        return redirect(url_for('admin_dashboard'))

    user = User.query.get_or_404(user_id)

    # Add system message before deleting the user
    add_system_message(f"SYSTEM: User {user.username} has been deleted and all their messages have been purged.")

    # Delete all user messages
    Message.query.filter_by(user_id=user_id).delete()

    # Delete the user
    db.session.delete(user)
    db.session.commit()

    flash(f'User {user.username} has been deleted and their messages have been purged.', 'success')
    return redirect(url_for('admin_dashboard'))

# ==========================
# ADMIN FUNCTION RESTORE USER
# ==========================

@app.route("/admin/user/restore/<int:user_id>")
@login_required
def restore_user(user_id):
    if not current_user.is_mod:
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("home"))

    user = User.query.get_or_404(user_id)
    user.is_deleted = False
    db.session.commit()
    flash(f"User {user.username} has been restored.", "success")
    return redirect(url_for("admin_dashboard"))

# ==========================
# TIME AND DATE
# ==========================
@app.route("/")
def home():
    current_year = datetime.now().year
    return render_template("index.html", current_year=current_year)

# ==========================
# Register Account
# ==========================

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        return redirect(url_for("home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        # Create new user without password hashing
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,  # No password hashing here
            mailing_list=form.mailing_list.data
        )
        # Add to database
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template("register.html", title="Register", form=form)

# ==========================
# Log in
# ==========================

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        return redirect(url_for("home"))
    form = LoginForm()
    if form.validate_on_submit():
        # Query user by email
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.password == form.password.data:  # No password hash check
            # Log the user in
            login_user(user)
            flash("Logged in successfully!", "success")
            # Redirect to next page if exists
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("home"))
        else:
            flash("Login Unsuccessful. Please check email and password.", "danger")
    return render_template("login.html", title="Login", form=form)

# ==========================
# Profile
# ==========================
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user, STOCK_LEVEL_LABELS=STOCK_LEVEL_LABELS)


# ==========================
# Map Link
# ==========================
@app.route('/map')
def map():
    return render_template('map.html')

# ==========================
# Edit Profile
# ==========================
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()

    if form.validate_on_submit():
        # Check which fields have data and update only those fields
        if form.username.data:
            current_user.username = form.username.data
        if form.email.data:
            current_user.email = form.email.data
        if form.stock_level.data is not None:  # Note: IntegerField's default value is `None`
            current_user.stock_level = form.stock_level.data
        if form.show_url.data:  # Update show_url if provided, or set to None if empty
            current_user.show_url = form.show_url.data
        else:
            current_user.show_url = None

        # Commit the changes to the database
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile'))

    # Prepopulate form with existing data
    form.username.data = form.username.data or current_user.username
    form.email.data = form.email.data or current_user.email
    form.stock_level.data = form.stock_level.data or current_user.stock_level
    form.show_url.data = form.show_url.data or current_user.show_url

    return render_template('edit_profile.html', form=form)

# ==========================
# Login manager
# ==========================


@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user and not user.is_banned:
        return user
    return None

# ==========================
# Delete Message ADMIN
# ==========================

@app.route("/admin/messages/delete", methods=["POST"])
@login_required
def delete_selected_messages():
    if not current_user.is_mod:
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("home"))

    # Get the list of selected message IDs
    selected_ids = request.form.getlist("message_ids")

    if not selected_ids:
        flash("No messages were selected for deletion.", "warning")
        return redirect(url_for("admin_dashboard"))

    # Convert selected_ids to integers
    selected_ids = [int(id) for id in selected_ids]

    # Delete the selected messages
    Message.query.filter(Message.id.in_(selected_ids)).delete(synchronize_session=False)
    db.session.commit()

    flash(f"{len(selected_ids)} messages have been deleted.", "success")
    return redirect(url_for("admin_dashboard"))

# ==========================
# Logout
# ==========================

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

# ==========================
# ADMIN FUNCTION PROMOTE USER
# ==========================

@app.route("/admin/user/promote/<int:user_id>")
@login_required
def promote_user(user_id):
    if not current_user.is_mod:
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("home"))

    user = User.query.get_or_404(user_id)
    user.is_mod = True
    db.session.commit()
    flash(f"{user.username} has been promoted to Moderator.", "success")
    return redirect(url_for("admin_dashboard"))

# ==========================
# ADMIN FUNCTION DEMOTE USER
# ==========================

@app.route("/admin/user/demote/<int:user_id>")
@login_required
def demote_user(user_id):
    if not current_user.is_mod:
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("home"))

    user = User.query.get_or_404(user_id)
    user.is_mod = False
    db.session.commit()
    flash(f"{user.username} has been demoted to User.", "success")
    return redirect(url_for("admin_dashboard"))

# ==========================
# ADMIN FUNCTION BAN USER
# ==========================

@app.route("/admin/user/ban/<int:user_id>")
@login_required
def ban_user(user_id):
    if not current_user.is_mod:
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("home"))

    user = User.query.get_or_404(user_id)
    user.is_banned = True
    db.session.commit()
    flash(f"{user.username} has been banned.", "success")
    return redirect(url_for("admin_dashboard"))

# ==========================
# ADMIN FUNCTION UNBAN USER
# ==========================

@app.route("/admin/user/unban/<int:user_id>")
@login_required
def unban_user(user_id):
    if not current_user.is_mod:
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("home"))

    user = User.query.get_or_404(user_id)
    user.is_banned = False
    db.session.commit()
    flash(f"{user.username} has been unbanned.", "success")
    return redirect(url_for("admin_dashboard"))



# ==========================
# Chat Funcution
# ==========================

@app.route("/chat")
@login_required
def chat():
    # All users see all messages without visibility filtering
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    return render_template("chat.html", title="Chat", messages=messages)

# ==========================
# ADMIN Interface
# ==========================
@app.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_mod:
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("home"))
    users = User.query.all()
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    return render_template("admin_dashboard.html", title="Admin Dashboard", users=users, messages=messages)

# Route to mark a message as hidden

# ==========================
# ADMIN HIDE MESSAGE
# ==========================

@app.route("/admin/hide_message/<int:message_id>", methods=["POST"])
@login_required
def hide_message(message_id):
    if not current_user.is_mod:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for("admin_dashboard"))

    message = Message.query.get_or_404(message_id)
    message.visible = False
    db.session.commit()

    flash("Message has been hidden.", "success")
    return redirect(url_for("admin_dashboard"))


# ==========================
# ADMIN UNHIDE MESSAGE
# ==========================


@app.route("/admin/unhide_message/<int:message_id>", methods=["POST"])
@login_required
def unhide_message(message_id):
    if not current_user.is_mod:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for("admin_dashboard"))

    message = Message.query.get_or_404(message_id)
    message.visible = True
    db.session.commit()

    flash("Message has been made visible again.", "success")
    return redirect(url_for("admin_dashboard"))

# ==========================
# SocketIO Events
# ==========================

@socketio.on('send_message')
def handle_send_message_event(data):
    # Ensure that the current user is authenticated
    if not current_user.is_authenticated:
        # Emit an error message back to the sender only, not to all clients
        emit('error', {'message': 'Unauthorized'}, broadcast=False)
        return

    # Additional check: If the user is banned, prevent them from sending messages
    if current_user.is_banned:
        emit('error', {'message': 'You are banned from sending messages.'}, broadcast=False)
        return

    # Create a new message object and save it to the database
    message = Message(content=data['message'], user_id=current_user.id)

    # Add message to the database session and commit it
    db.session.add(message)
    db.session.commit()

    # Broadcast the message to all connected clients, including the timestamp and username
    emit('receive_message', {
        'message': message.content,
        'username': current_user.username,
        'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    }, broadcast=True)

    # Optional: Log the event for debugging
    print(f"Message sent by {current_user.username}: {message.content}")

# ==========================
# Run the Application
# ==========================

if __name__ == "__main__":
    # Run the app with SocketIO
    socketio.run(app, debug=True)

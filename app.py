from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin
from flask import request, redirect
from flask_login import current_user

app = Flask(__name__)
app.secret_key = 'lumina-grand-secret-key'

# KONFIGURASI DATABASE
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# INISIALISASI DATABASE
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# MODEL USER
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255))
    status = db.Column(db.String(20), default='available')

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    guest_name = db.Column(db.String(100))
    room_name = db.Column(db.String(100))

    check_in = db.Column(db.String(50))
    check_out = db.Column(db.String(50))

    total_payment = db.Column(db.Integer)

    status = db.Column(db.String(50))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ROUTE HOME
@app.route('/')
def home():
    return render_template('/user/Index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        new_user = User(
            username=username,
            email=email,
            password=password
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect('/')

    return render_template('/user/Register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            login_user(user)
            return redirect('/')

    return render_template('/user/Login.html')

@app.route('/dashboard')
@login_required
def dashboard():

    if current_user.role not in ['admin', 'super_admin']:
        return "Access Denied"

    rooms = Room.query.all()

    return render_template(
        'Dashboard.html',
        rooms=rooms
    )

@app.route('/add_room', methods=['GET', 'POST'])
@login_required
def add_room():

    if current_user.role not in ['admin', 'super_admin']:
        return "Access Denied"

    if request.method == 'POST':

        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        image = request.form['image']
        status = request.form['status']

        new_room = Room(
            name=name,
            price=price,
            description=description,
            image=image,
            status=status
        )

        db.session.add(new_room)
        db.session.commit()

        return redirect('/dashboard')

    return render_template('add_room.html')

@app.route('/bookings')
@login_required
def bookings():

    if current_user.role not in ['admin', 'super_admin']:
        return "Access Denied"

    bookings = Booking.query.all()

    return render_template(
        'booking.html',
        bookings=bookings
    )

@app.route('/staff')
@login_required
def staff():

    if current_user.role != 'super_admin':
        return "Access Denied"

    staff_members = User.query.filter(User.role.in_(['admin', 'staff'])).all()

    return render_template(
        'staff.html',
        staff_members=staff_members
    )

# MEMBUAT DATABASE
with app.app_context():

    db.create_all()

    existing_booking = Booking.query.first()

    if not existing_booking:

        sample = Booking(
            guest_name='Fajri',
            room_name='Deluxe Room',
            check_in='2026-05-20',
            check_out='2026-05-25',
            total_payment=500,
            status='Confirmed'
        )

        db.session.add(sample)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
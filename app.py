from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin
from flask import request, redirect

app = Flask(__name__)

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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ROUTE HOME
@app.route('/')
def home():
    return render_template('Index.html')

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

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            login_user(user)
            return redirect('/')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    rooms = Room.query.all()
    return render_template('Dashboard.html', rooms=rooms)

@app.route('/add_room', methods=['GET', 'POST'])
def add_room():

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

# MEMBUAT DATABASE
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
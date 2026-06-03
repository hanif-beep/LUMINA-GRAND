from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, UserMixin, current_user
)

app = Flask(__name__)
app.secret_key = 'lumina-grand-secret-key'

# ── DATABASE CONFIG ────────────────────────────────────────────
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db           = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ── MODELS ─────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    id       = db.Column(db.Integer,     primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email    = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    role     = db.Column(db.String(20),  default='user')


class Room(db.Model):
    id          = db.Column(db.Integer,     primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    price       = db.Column(db.Integer,     nullable=False)
    description = db.Column(db.Text,        nullable=False)
    image       = db.Column(db.String(255))
    status      = db.Column(db.String(20),  default='available')
    # Tambahan field untuk halaman kamar
    guests      = db.Column(db.Integer,     default=2)
    bed_type    = db.Column(db.String(50),  default='King')
    category    = db.Column(db.String(50),  default='Superior')   # Superior / Deluxe / Suite


class Booking(db.Model):
    id            = db.Column(db.Integer,     primary_key=True)
    guest_name    = db.Column(db.String(100))
    room_name     = db.Column(db.String(100))
    check_in      = db.Column(db.String(50))
    check_out     = db.Column(db.String(50))
    total_payment = db.Column(db.Integer)
    status        = db.Column(db.String(50))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── PUBLIC ROUTES ──────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('/user/Index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Cek apakah email sudah digunakan
        if User.query.filter_by(email=email).first():
            # Kembalikan 409 agar JS tahu email sudah ada
            return 'Email already exists', 409

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('/user/Register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            login_user(user)
            # ✅ Redirect ke halaman kamar setelah login
            return redirect(url_for('rooms'))

        # Login gagal → kembalikan halaman login dengan status 401
        return render_template('/user/Login.html'), 401

    return render_template('/user/Login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ── ROOMS ROUTE (Halaman Kamar — butuh login) ──────────────────

@app.route('/rooms')
@login_required
def rooms():
    """
    Halaman utama daftar kamar.
    Mendukung filter via query string:
        ?category=Deluxe
        ?status=available
        ?q=ocean   (search nama kamar)
    """
    category = request.args.get('category', '')
    status   = request.args.get('status', '')
    q        = request.args.get('q', '').strip()

    query = Room.query

    if category:
        query = query.filter_by(category=category)
    if status:
        query = query.filter_by(status=status)
    if q:
        query = query.filter(Room.name.ilike(f'%{q}%'))

    all_rooms = query.all()

    return render_template(
        '/user/Kamar.html',
        rooms=all_rooms,
        user=current_user,
        active_category=category,
        active_status=status,
        search_query=q,
    )


@app.route('/rooms/<int:room_id>')
@login_required
def room_detail(room_id):
    """Detail satu kamar (bisa dipakai modal/AJAX atau halaman terpisah)."""
    room = Room.query.get_or_404(room_id)
    return jsonify({
        'id'         : room.id,
        'name'       : room.name,
        'price'      : room.price,
        'description': room.description,
        'image'      : room.image,
        'status'     : room.status,
        'guests'     : room.guests,
        'bed_type'   : room.bed_type,
        'category'   : room.category,
    })


@app.route('/book/<int:room_id>', methods=['POST'])
@login_required
def book_room(room_id):
    """Proses reservasi kamar oleh user yang sudah login."""
    room = Room.query.get_or_404(room_id)

    if room.status != 'available':
        return jsonify({'error': 'Room is not available'}), 400

    check_in  = request.form.get('check_in')
    check_out = request.form.get('check_out')

    if not check_in or not check_out:
        return jsonify({'error': 'Check-in and check-out dates are required'}), 400

    booking = Booking(
        guest_name    = current_user.username,
        room_name     = room.name,
        check_in      = check_in,
        check_out     = check_out,
        total_payment = room.price,
        status        = 'Pending',
    )

    room.status = 'booked'
    db.session.add(booking)
    db.session.commit()

    return jsonify({'message': 'Booking successful', 'booking_id': booking.id})


# ── ADMIN ROUTES ───────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role not in ['admin', 'super_admin']:
        return 'Access Denied', 403
    rooms = Room.query.all()
    return render_template('Dashboard.html', rooms=rooms)


@app.route('/add_room', methods=['GET', 'POST'])
@login_required
def add_room():
    if current_user.role not in ['admin', 'super_admin']:
        return 'Access Denied', 403

    if request.method == 'POST':
        new_room = Room(
            name        = request.form['name'],
            price       = request.form['price'],
            description = request.form['description'],
            image       = request.form['image'],
            status      = request.form['status'],
            guests      = request.form.get('guests', 2),
            bed_type    = request.form.get('bed_type', 'King'),
            category    = request.form.get('category', 'Superior'),
        )
        db.session.add(new_room)
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('add_room.html')


@app.route('/bookings')
@login_required
def bookings():
    if current_user.role not in ['admin', 'super_admin']:
        return 'Access Denied', 403
    all_bookings = Booking.query.all()
    return render_template('booking.html', bookings=all_bookings)


@app.route('/staff')
@login_required
def staff():
    if current_user.role != 'super_admin':
        return 'Access Denied', 403
    staff_members = User.query.filter(User.role.in_(['admin', 'staff'])).all()
    return render_template('staff.html', staff_members=staff_members)


# ── SEED DATABASE ──────────────────────────────────────────────
with app.app_context():
    db.create_all()

    # ── Auto-migrate: tambah kolom baru jika belum ada ─────────
    # Diperlukan jika hotel.db sudah ada sebelum kolom baru ditambahkan
    from sqlalchemy import text, inspect as sa_inspect
    with db.engine.connect() as conn:
        inspector   = sa_inspect(db.engine)
        existing    = [c['name'] for c in inspector.get_columns('room')]

        if 'guests' not in existing:
            conn.execute(text('ALTER TABLE room ADD COLUMN guests INTEGER DEFAULT 2'))
            conn.commit()
        if 'bed_type' not in existing:
            conn.execute(text("ALTER TABLE room ADD COLUMN bed_type VARCHAR(50) DEFAULT 'King'"))
            conn.commit()
        if 'category' not in existing:
            conn.execute(text("ALTER TABLE room ADD COLUMN category VARCHAR(50) DEFAULT 'Superior'"))
            conn.commit()

    # Seed sample booking jika belum ada
    if not Booking.query.first():
        db.session.add(Booking(
            guest_name='Fajri', room_name='Deluxe Room',
            check_in='2026-05-20', check_out='2026-05-25',
            total_payment=500, status='Confirmed'
        ))
        db.session.commit()

    # Seed sample rooms jika belum ada
    if not Room.query.first():
        sample_rooms = [
            Room(
                name='Superior Room', price=450,
                description='A comfortable room with modern amenities and city view.',
                image='https://lh3.googleusercontent.com/aida-public/AB6AXuDXciBEBnOsvNcjv9R8BlOMS1djvsmVc8ouAaj6o4rIpidMKn1E535kgLfs7B6k_HcvNXRLHx9q6P9qKZTlSFMio_suaCscsZDVgFICbn-Ma8GNMqyTIjFoJYqN7JcqQtSTQgt7znVhNaW9SsT1yHRrxAkM-u2LYUwmxaJJKr4mgZRIVMumWf3J1WPfQroILEnXwiiQQMTNWhYIYjy-0jZt7CJ58O9wK0vpkfd61Z1hs4Hln9vPGuYXAhM4ilcZguHLlTnuDFkrEIY',
                status='available', guests=2, bed_type='Queen', category='Superior',
            ),
            Room(
                name='Deluxe Ocean View', price=680,
                description='Stunning ocean panorama with private balcony and king-size bed.',
                image='https://lh3.googleusercontent.com/aida/ADBb0uhivCtf76RBYYmZAf_CEtOnhIMj-K-3J_pU4ke9nyvFVw-oX4MhG6aOxAAHfxyBIFxA1uJRZQ2i8E1C9NoLnSbFO-63g-Q9vk18Bh_w1Pn68u7Tl94XPx6WUXjuBQweykPRNvTw08xqYwp5kr9FCNL6lfNZvqMQcQ5ZiwAMnKlWZuE-YlxQSbjDDtFEqeTBdgr9m8lCfRl37oHkOxX7zGdWUuHzeOijt7DGSpzp1IRJ3osTKiSZzuRoqXo',
                status='available', guests=2, bed_type='King', category='Deluxe',
            ),
            Room(
                name='Junior Suite', price=920,
                description='Spacious suite with living area, soaking tub, and espresso machine.',
                image='https://lh3.googleusercontent.com/aida-public/AB6AXuASgiCQLN7_7ofWgO0-HwsQ78vS90EDKMyT5aQ_iNk5bz_mLVDMjPhTvPKGRyp8esuSZxgMbkDrz4cdozngH-uIpbQnv5NYzBxixxE4AFVNwfSSQRiSSH2Y4UEYyQYNAmSSw2hX1nVEpbWPkaR-AHuxme7LwWlgpg6IkrY3fLq5X00tAFLcBoqaTXcAkjCDwzQLGlW53aeYlNzftIvvqOElZV09vdwvZYTkSCF3sXQD4GJjZ3AALRHgcZWg9MNHCieRScq-ffd1MFg',
                status='available', guests=3, bed_type='King', category='Suite',
            ),
        ]
        db.session.add_all(sample_rooms)
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True)


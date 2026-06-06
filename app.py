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
    total_rooms = db.Column(db.Integer,     default=5)   # jumlah unit kamar yang tersedia


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

            # Admin & Super Admin -> Dashboard
            if user.role in ['admin', 'super_admin']:
                return redirect(url_for('dashboard'))

            # User biasa -> Rooms
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

    # Ambil booking milik user yang sedang login
    my_bookings = Booking.query.filter_by(guest_name=current_user.username).order_by(Booking.id.desc()).all()

    # Hitung sisa kamar per room (tanpa filter tanggal — total unit - active bookings)
    room_remaining = {}
    for r in all_rooms:
        active = Booking.query.filter(
            Booking.room_name == r.name,
            Booking.status.in_(['Pending', 'Confirmed'])
        ).count()
        room_remaining[r.id] = max(0, (r.total_rooms or 1) - active)

    return render_template(
        '/user/Kamar.html',
        rooms=all_rooms,
        user=current_user,
        active_category=category,
        active_status=status,
        search_query=q,
        my_bookings=my_bookings,
        room_remaining=room_remaining,
    )

@app.route('/admin/rooms')
@login_required
def admin_rooms():
    if current_user.role not in ['admin', 'super_admin']:
        return 'Access Denied', 403

    rooms = Room.query.all()
    return render_template('admin/rooms.html', rooms=rooms)


@app.route('/rooms/detail/<int:room_id>')
@login_required
def room_detail_page(room_id):
    """Halaman detail kamar — render template sesuai kategori."""
    room = Room.query.get_or_404(room_id)
    template_map = {
        'Deluxe' : '/user/detail_deluxe.html',
        'Suite'  : '/user/detail_suite.html',
        'Superior': '/user/detail_superior.html',
    }
    template = template_map.get(room.category, '/user/detail_deluxe.html')
    return render_template(template, room=room, user=current_user)


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


@app.route('/rooms/<int:room_id>/availability')
@login_required
def room_availability(room_id):
    """Return remaining units for a room on given dates."""
    room      = Room.query.get_or_404(room_id)
    check_in  = request.args.get('check_in', '')
    check_out = request.args.get('check_out', '')

    if not check_in or not check_out:
        return jsonify({'total': room.total_rooms, 'booked': 0, 'remaining': room.total_rooms})

    active = Booking.query.filter(
        Booking.room_name == room.name,
        Booking.status.in_(['Pending', 'Confirmed']),
        Booking.check_in  < check_out,
        Booking.check_out > check_in,
    ).count()

    total     = room.total_rooms or 1
    remaining = max(0, total - active)
    return jsonify({'total': total, 'booked': active, 'remaining': remaining})


@app.route('/book/<int:room_id>', methods=['POST'])
@login_required
def book_room(room_id):
    """Proses reservasi kamar oleh user yang sudah login."""
    room = Room.query.get_or_404(room_id)

    check_in  = request.form.get('check_in')
    check_out = request.form.get('check_out')

    if not check_in or not check_out:
        return jsonify({'error': 'Check-in and check-out dates are required'}), 400

    # Hitung booking aktif (Pending/Confirmed) yang overlap dengan tanggal yang dipilih
    active_bookings = Booking.query.filter(
        Booking.room_name == room.name,
        Booking.status.in_(['Pending', 'Confirmed']),
        Booking.check_in  < check_out,
        Booking.check_out > check_in,
    ).count()

    total_units = room.total_rooms or 1
    remaining   = total_units - active_bookings

    if remaining <= 0:
        return jsonify({'error': 'No rooms available for the selected dates'}), 400

    booking = Booking(
        guest_name    = current_user.username,
        room_name     = room.name,
        check_in      = check_in,
        check_out     = check_out,
        total_payment = room.price,
        status        = 'Pending',
    )

    db.session.add(booking)
    db.session.commit()

    # Update status room berdasarkan sisa unit
    new_active = active_bookings + 1
    room.status = 'available' if new_active < total_units else 'booked'
    db.session.commit()

    return jsonify({'message': 'Booking successful', 'booking_id': booking.id, 'remaining': total_units - new_active})


# ── ADMIN ROUTES ───────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role not in ['admin', 'super_admin']:
        return 'Access Denied', 403
    rooms = Room.query.all()
    return render_template('admin/Dashboard.html', rooms=rooms)


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
    return render_template('admin/booking.html', bookings=all_bookings)


@app.route('/staff')
@login_required
def staff():
    if current_user.role != 'super_admin':
        return 'Access Denied', 403
    staff_members = User.query.filter(User.role.in_(['admin', 'staff'])).all()
    return render_template('admin/staff.html', staff_members=staff_members)


# ── SEED DATABASE ──────────────────────────────────────────────
with app.app_context():
    db.create_all()

    admin = User.query.filter_by(email='superadmin@gmail.com').first()

    if not admin:
        admin = User(
            username='Super Admin',
            email='superadmin@gmail.com',
            password='superadmin123',
            role='super_admin'
        )
        db.session.add(admin)
        db.session.commit()

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
        if 'total_rooms' not in existing:
            conn.execute(text('ALTER TABLE room ADD COLUMN total_rooms INTEGER DEFAULT 5'))
            conn.commit()

    # Update harga lama (USD) ke IDR jika masih kecil (<= 2000)
    old_price_rooms = Room.query.filter(Room.price <= 2000).all()
    price_map = {
        'Superior Room'    : 1150000,
        'Deluxe Room': 1850000,
        'Junior Suite'     : 2750000,
    }
    for r in old_price_rooms:
        if r.name in price_map:
            r.price = price_map[r.name]
    if old_price_rooms:
        db.session.commit()

    # Rename 'Deluxe Ocean View' -> 'Deluxe Room' jika masih ada di DB
    deluxe_old = Room.query.filter_by(name='Deluxe Ocean View').first()
    if deluxe_old:
        deluxe_old.name        = 'Deluxe Room'
        deluxe_old.description = 'Kamar deluxe luas dengan interior premium, ranjang king-size, dan fasilitas lengkap untuk kenyamanan menginap terbaik.'
        db.session.commit()

    # Update gambar lama (googleusercontent) ke Unsplash yang stabil
    image_map = {
        'Superior Room'    : 'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80',
        'Deluxe Room': 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80',
        'Junior Suite'     : 'https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&q=80',
    }
    changed = False
    for r in Room.query.all():
        if r.name in image_map and (not r.image or 'googleusercontent' in r.image or 'lh3.google' in r.image):
            r.image = image_map[r.name]
            changed = True
    if changed:
        db.session.commit()

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
                name='Superior Room',
                price=1150000,
                description='Kamar nyaman dengan sentuhan modern, pemandangan kota, dan fasilitas lengkap untuk istirahat berkualitas.',
                image='https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80',
                status='available', guests=2, bed_type='Queen', category='Superior',
            ),
            Room(
                name='Deluxe Room',
                price=1900000,
                description='Kamar deluxe luas dengan interior premium, ranjang king-size, dan fasilitas lengkap untuk kenyamanan menginap terbaik.',
                image='https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80',
                status='available', guests=2, bed_type='King', category='Deluxe',
            ),
            Room(
                name='Junior Suite',
                price=2800000,
                description='Suite luas dengan ruang tamu terpisah, bathtub rendam mewah, dan mesin espresso premium untuk kenyamanan maksimal.',
                image='https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&q=80',
                status='available', guests=3, bed_type='King', category='Suite',
            ),
        ]
        db.session.add_all(sample_rooms)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
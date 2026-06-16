from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, UserMixin, current_user
)
from datetime import date, datetime
from collections import Counter

app = Flask(__name__)
app.secret_key = 'lumina-grand-secret-key'

# ── DATABASE CONFIG ────────────────────────────────────────────
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db            = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# ── MODELS ────────────────────────────────────────────────────
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
    guests      = db.Column(db.Integer,     default=2)
    bed_type    = db.Column(db.String(50),  default='King')
    category    = db.Column(db.String(50),  default='Superior')
    total_rooms = db.Column(db.Integer,     default=5)


class Booking(db.Model):
    id            = db.Column(db.Integer,   primary_key=True)
    guest_name    = db.Column(db.String(100))
    room_name     = db.Column(db.String(100))
    check_in      = db.Column(db.String(50))
    check_out     = db.Column(db.String(50))
    total_payment = db.Column(db.Integer)
    status        = db.Column(db.String(50))
    created_at    = db.Column(db.DateTime,  default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── AUTO-UPDATE BOOKING STATUS ────────────────────────────────
@app.before_request
def auto_update_booking_status():
    """
    Tiap request: booking yang check_out-nya sudah lewat otomatis diupdate.
    Confirmed  -> Completed
    Pending    -> Cancelled
    """
    today_str = date.today().isoformat()
    expired = Booking.query.filter(
        Booking.status.in_(['Pending', 'Confirmed']),
        Booking.check_out <= today_str
    ).all()
    if expired:
        for b in expired:
            b.status = 'Completed' if b.status == 'Confirmed' else 'Cancelled'
        db.session.commit()


# ── HELPER FUNCTIONS ──────────────────────────────────────────
def format_date(date_str):
    """'2026-06-05' -> '05 Jun 2026'"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d %b %Y')
    except (ValueError, TypeError):
        return date_str or '-'


def time_ago(dt):
    """datetime -> human-readable relative time"""
    if not dt:
        return '-'
    seconds = (datetime.utcnow() - dt).total_seconds()
    if seconds < 60:
        return 'Just now'
    minutes = int(seconds // 60)
    if minutes < 60:
        return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
    hours = int(minutes // 60)
    if hours < 24:
        return f'{hours} hour{"s" if hours != 1 else ""} ago'
    days = int(hours // 24)
    return f'{days} day{"s" if days != 1 else ""} ago'


def nights_between(check_in, check_out):
    try:
        ci = datetime.strptime(check_in, '%Y-%m-%d')
        co = datetime.strptime(check_out, '%Y-%m-%d')
        return max(0, (co - ci).days)
    except (ValueError, TypeError):
        return 0


# ── PUBLIC ROUTES ─────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('/user/Index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if User.query.filter_by(email=email).first():
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
        user     = User.query.filter_by(email=email).first()

        if user and user.password == password:
            login_user(user)
            if user.role in ['admin', 'super_admin', 'staff']:
                return redirect(url_for('dashboard'))
            return redirect(url_for('rooms'))

        return render_template('/user/Login.html'), 401

    return render_template('/user/Login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ── ROOMS (USER) ──────────────────────────────────────────────
@app.route('/rooms')
@login_required
def rooms():
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

    all_rooms   = query.all()
    my_bookings = Booking.query.filter_by(
        guest_name=current_user.username
    ).order_by(Booking.id.desc()).all()

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


@app.route('/rooms/detail/<int:room_id>')
@login_required
def room_detail_page(room_id):
    room = Room.query.get_or_404(room_id)
    template_map = {
        'Deluxe':   '/user/detail_deluxe.html',
        'Suite':    '/user/detail_suite.html',
        'Superior': '/user/detail_superior.html',
    }
    template = template_map.get(room.category, '/user/detail_deluxe.html')
    return render_template(template, room=room, user=current_user)


@app.route('/rooms/<int:room_id>')
@login_required
def room_detail(room_id):
    room = Room.query.get_or_404(room_id)
    return jsonify({
        'id':          room.id,
        'name':        room.name,
        'price':       room.price,
        'description': room.description,
        'image':       room.image,
        'status':      room.status,
        'guests':      room.guests,
        'bed_type':    room.bed_type,
        'category':    room.category,
    })


@app.route('/rooms/<int:room_id>/availability')
@login_required
def room_availability(room_id):
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
    room      = Room.query.get_or_404(room_id)
    check_in  = request.form.get('check_in')
    check_out = request.form.get('check_out')

    if not check_in or not check_out:
        return jsonify({'error': 'Check-in and check-out dates are required'}), 400
    
    nights = nights_between(check_in, check_out)
    if nights <= 0:
        return jsonify({'error': 'Invalid dates'}), 400

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
        total_payment = room.price * nights,
        status        = 'Pending',
    )
    db.session.add(booking)
    db.session.commit()

    new_active  = active_bookings + 1
    room.status = 'available' if new_active < total_units else 'booked'
    db.session.commit()

    return jsonify({
        'message':    'Booking successful',
        'booking_id': booking.id,
        'remaining':  total_units - new_active,
    })


# ── ADMIN ROUTES ──────────────────────────────────────────────
@app.route('/admin/rooms')
@login_required
def admin_rooms():
    if current_user.role not in ['admin', 'super_admin', 'staff']:
        return 'Access Denied', 403
    all_rooms = Room.query.all()
    return render_template('admin/rooms.html', rooms=all_rooms)


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role not in ['admin', 'super_admin', 'staff']:
        return 'Access Denied', 403

    all_rooms    = Room.query.all()
    all_bookings = Booking.query.all()

    today         = date.today()
    today_str     = today.isoformat()
    current_month = today.strftime('%Y-%m')

    # Stat cards
    total_room_units = sum((r.total_rooms or 1) for r in all_rooms)

    active_bookings       = [b for b in all_bookings if b.status in ('Pending', 'Confirmed')]
    active_bookings_count = len(active_bookings)

    occupied_count = sum(
        1 for b in active_bookings
        if b.check_in and b.check_out and b.check_in <= today_str <= b.check_out
    )
    reserved_count = sum(
        1 for b in active_bookings
        if b.check_in and b.check_in > today_str
    )
    maintenance_count = sum(1 for r in all_rooms if r.status == 'maintenance')
    available_count   = max(0, total_room_units - occupied_count - reserved_count - maintenance_count)
    occupancy_rate    = round((occupied_count / total_room_units) * 100, 1) if total_room_units else 0

    monthly_revenue = sum(
        b.total_payment or 0 for b in all_bookings
        if b.status in ('Confirmed', 'Completed')
        and (b.check_in or '').startswith(current_month)
    )

    # Recent bookings (5 terbaru)
    recent_bookings = []
    for b in Booking.query.order_by(Booking.id.desc()).limit(5).all():
        recent_bookings.append({
            'id':         b.id,
            'guest_name': b.guest_name,
            'room_name':  b.room_name,
            'check_in':   format_date(b.check_in),
            'check_out':  format_date(b.check_out),
            'status':     b.status,
        })

    # Activity feed (4 terbaru)
    activity_feed = []
    for b in Booking.query.order_by(Booking.id.desc()).limit(4).all():
        activity_feed.append({
            'status':     b.status,
            'guest_name': b.guest_name,
            'room_name':  b.room_name,
            'booking_id': b.id,
            'time_ago':   time_ago(b.created_at),
        })

    # Insights
    room_counter      = Counter(b.room_name for b in all_bookings)
    most_booked       = room_counter.most_common(1)
    most_booked_name  = most_booked[0][0] if most_booked else '-'
    most_booked_count = most_booked[0][1] if most_booked else 0

    room_occupied_today = Counter()
    for b in active_bookings:
        if b.check_in and b.check_out and b.check_in <= today_str <= b.check_out:
            room_occupied_today[b.room_name] += 1

    highest_room_name, highest_rate = '-', 0
    for r in all_rooms:
        total = r.total_rooms or 1
        rate  = (room_occupied_today.get(r.name, 0) / total) * 100
        if rate > highest_rate:
            highest_rate      = rate
            highest_room_name = r.name

    stay_lengths = [
        n for n in (nights_between(b.check_in, b.check_out) for b in all_bookings)
        if n > 0
    ]
    avg_stay           = round(sum(stay_lengths) / len(stay_lengths), 1) if stay_lengths else 0
    total_reservations = len(all_bookings)

    return render_template(
        'admin/Dashboard.html',
        rooms=all_rooms,
        total_room_units=total_room_units,
        active_bookings_count=active_bookings_count,
        occupancy_rate=occupancy_rate,
        monthly_revenue=monthly_revenue,
        available_count=available_count,
        occupied_count=occupied_count,
        reserved_count=reserved_count,
        maintenance_count=maintenance_count,
        recent_bookings=recent_bookings,
        activity_feed=activity_feed,
        most_booked_name=most_booked_name,
        most_booked_count=most_booked_count,
        highest_room_name=highest_room_name,
        highest_rate=round(highest_rate, 1),
        avg_stay=avg_stay,
        total_reservations=total_reservations,
    )


@app.route('/add_room', methods=['GET', 'POST'])
@login_required
def add_room():
    if current_user.role not in ['admin', 'super_admin', 'staff']:
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

@app.route('/edit_room/<int:room_id>', methods=['POST'])
@login_required
def edit_room(room_id):
    room = Room.query.get_or_404(room_id)

    room.name = request.form['name']
    room.price = request.form['price']
    room.status = request.form['status']
    room.guests = request.form['guests']
    room.bed_type = request.form['bed_type']
    room.total_rooms = request.form['total_rooms']
    room.image = request.form['image']
    room.description = request.form['description']

    db.session.commit()

    return redirect(url_for('admin_rooms'))  # balik ke halaman rooms


@app.route('/bookings')
@login_required
def bookings():
    if current_user.role not in ['admin', 'super_admin', 'staff']:
        return 'Access Denied', 403
    all_bookings = Booking.query.all()
    return render_template('admin/booking.html', bookings=all_bookings)

@app.route('/bookings/<int:booking_id>/edit', methods=['POST'])
@login_required
def edit_booking(booking_id):
    b = Booking.query.get_or_404(booking_id)
    b.guest_name    = request.form['guest_name']
    b.room_name     = request.form['room_name']
    b.check_in      = request.form['check_in']
    b.check_out     = request.form['check_out']
    b.total_payment = request.form['total_payment']
    b.status        = request.form['status']
    db.session.commit()
    return redirect(url_for('bookings'))

@app.route('/bookings/<int:booking_id>/delete', methods=['POST'])
@login_required
def delete_booking(booking_id):
    b = Booking.query.get_or_404(booking_id)
    db.session.delete(b)
    db.session.commit()
    return redirect(url_for('bookings'))

@app.route('/bookings/create', methods=['POST'])
@login_required
def create_booking():
    b = Booking(
        guest_name    = request.form['guest_name'],
        room_name     = request.form['room_name'],
        check_in      = request.form['check_in'],
        check_out     = request.form['check_out'],
        total_payment = request.form['total_payment'],
        status        = request.form['status'],
    )
    db.session.add(b)
    db.session.commit()
    return redirect(url_for('bookings'))


@app.route('/staff')
@login_required
def staff():
    if current_user.role != 'super_admin':
        return 'Access Denied', 403
    staff_members = User.query.filter(User.role.in_(['admin', 'staff'])).all()
    return render_template('admin/staff.html', staff_members=staff_members)

@app.route('/add_staff', methods=['POST'])
@login_required
def add_staff():
    if current_user.role != 'super_admin':
        return 'Access Denied', 403

    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')

    # cek email sudah ada atau belum
    if User.query.filter_by(email=email).first():
        return 'Email already exists', 409

    new_staff = User(
        username=username,
        email=email,
        password=password,
        role=role
    )

    db.session.add(new_staff)
    db.session.commit()

    return redirect(url_for('staff'))

@app.route('/staff/<int:id>/edit', methods=['POST'])
@login_required
def edit_staff(id):
    if current_user.role != 'super_admin':
        return 'Access Denied', 403

    staff = User.query.get_or_404(id)

    staff.username = request.form.get('username')
    staff.role = request.form.get('role')

    db.session.commit()

    return redirect(url_for('staff'))

@app.route('/staff/<int:id>/delete', methods=['POST'])
@login_required
def delete_staff(id):
    if current_user.role != 'super_admin':
        return 'Access Denied', 403

    staff = User.query.get_or_404(id)

    # biar ga bisa hapus akun sendiri
    if staff.id == current_user.id:
        return 'You cannot delete yourself', 400

    db.session.delete(staff)
    db.session.commit()

    return redirect(url_for('staff'))


# ── SEED & AUTO-MIGRATE ───────────────────────────────────────
with app.app_context():
    db.create_all()

    # Superadmin default
    if not User.query.filter_by(email='superadmin@gmail.com').first():
        db.session.add(User(
            username='Super Admin',
            email='superadmin@gmail.com',
            password='superadmin123',
            role='super_admin'
        ))
        db.session.commit()

    # Auto-migrate kolom baru
    from sqlalchemy import text, inspect as sa_inspect
    with db.engine.connect() as conn:
        inspector = sa_inspect(db.engine)

        # Kolom Room
        existing_room = [c['name'] for c in inspector.get_columns('room')]
        if 'guests' not in existing_room:
            conn.execute(text('ALTER TABLE room ADD COLUMN guests INTEGER DEFAULT 2'))
            conn.commit()
        if 'bed_type' not in existing_room:
            conn.execute(text("ALTER TABLE room ADD COLUMN bed_type VARCHAR(50) DEFAULT 'King'"))
            conn.commit()
        if 'category' not in existing_room:
            conn.execute(text("ALTER TABLE room ADD COLUMN category VARCHAR(50) DEFAULT 'Superior'"))
            conn.commit()
        if 'total_rooms' not in existing_room:
            conn.execute(text('ALTER TABLE room ADD COLUMN total_rooms INTEGER DEFAULT 5'))
            conn.commit()

        # Kolom Booking
        existing_booking = [c['name'] for c in inspector.get_columns('booking')]
        if 'created_at' not in existing_booking:
            conn.execute(text('ALTER TABLE booking ADD COLUMN created_at DATETIME'))
            conn.commit()

    # Update harga lama ke IDR
    price_map = {
        'Superior Room': 1150000,
        'Deluxe Room':   1850000,
        'Junior Suite':  2750000,
    }
    changed = False
    for r in Room.query.filter(Room.price <= 2000).all():
        if r.name in price_map:
            r.price = price_map[r.name]
            changed = True
    if changed:
        db.session.commit()

    # Rename Deluxe Ocean View -> Deluxe Room
    deluxe_old = Room.query.filter_by(name='Deluxe Ocean View').first()
    if deluxe_old:
        deluxe_old.name        = 'Deluxe Room'
        deluxe_old.description = 'Kamar deluxe luas dengan interior premium, ranjang king-size, dan fasilitas lengkap untuk kenyamanan menginap terbaik.'
        db.session.commit()

    # Update gambar lama ke Unsplash
    image_map = {
        'Superior Room': 'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80',
        'Deluxe Room':   'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80',
        'Junior Suite':  'https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&q=80',
    }
    changed = False
    for r in Room.query.all():
        if r.name in image_map and (
            not r.image
            or 'googleusercontent' in r.image
            or 'lh3.google' in r.image
        ):
            r.image  = image_map[r.name]
            changed  = True
    if changed:
        db.session.commit()

    # Seed booking contoh
    if not Booking.query.first():
        db.session.add(Booking(
            guest_name='Fajri', room_name='Deluxe Room',
            check_in='2026-05-20', check_out='2026-05-25',
            total_payment=1900000, status='Completed',
        ))
        db.session.commit()

    # Seed rooms contoh
    if not Room.query.first():
        db.session.add_all([
            Room(
                name='Superior Room', price=1150000,
                description='Kamar nyaman dengan sentuhan modern, pemandangan kota, dan fasilitas lengkap untuk istirahat berkualitas.',
                image='https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80',
                status='available', guests=2, bed_type='Queen', category='Superior', total_rooms=5,
            ),
            Room(
                name='Deluxe Room', price=1900000,
                description='Kamar deluxe luas dengan interior premium, ranjang king-size, dan fasilitas lengkap untuk kenyamanan menginap terbaik.',
                image='https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80',
                status='available', guests=2, bed_type='King', category='Deluxe', total_rooms=5,
            ),
            Room(
                name='Junior Suite', price=2800000,
                description='Suite luas dengan ruang tamu terpisah, bathtub rendam mewah, dan mesin espresso premium untuk kenyamanan maksimal.',
                image='https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&q=80',
                status='available', guests=3, bed_type='King', category='Suite', total_rooms=3,
            ),
        ])
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True)
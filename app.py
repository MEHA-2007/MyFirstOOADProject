import os
from datetime import date, datetime
from flask import Flask, flash, redirect, render_template, request, session, url_for
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL
from dotenv import load_dotenv

from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / '.env', override=True)

app = Flask(__name__)
import os

print("APP ROOT:", app.root_path)
print("TEMPLATE FOLDER:", app.template_folder)

print(
    "FILE EXISTS:",
    os.path.isfile(
        os.path.join(
            app.root_path,
            "templates",
            "forgot_password.html"
        )
    )
)
app.config.update(SECRET_KEY=os.getenv('SECRET_KEY', 'dev-only-change-this-key'), MYSQL_HOST=os.getenv('MYSQL_HOST', 'localhost'), MYSQL_USER=os.getenv('MYSQL_USER', 'root'), MYSQL_PASSWORD=os.getenv('MYSQL_PASSWORD', ''), MYSQL_DB=os.getenv('MYSQL_DB', 'homeease'), MYSQL_CURSORCLASS='DictCursor')
mysql, bcrypt = MySQL(app), Bcrypt(app)
SERVICES = {'Plumbing': ('🚿',450,['leak','tap','pipe','drain','plumb','water','toilet']), 'Electrical': ('⚡',500,['electric','wire','light','switch','power','fan','socket']), 'Cleaning': ('🧹',350,['clean','dust','deep clean','kitchen','bathroom']), 'Carpentry': ('🪚',550,['wood','door','cabinet','furniture','carpenter','shelf']), 'Appliance Repair': ('🧰',600,['fridge','washer','washing machine','ac','appliance','oven','machine'])}
STATUSES = ('Requested','Confirmed','Provider on the Way','In Progress','Completed','Cancelled')

def db():
 return mysql.connection.cursor()
def current_user():
    if not session.get('user_id'): return None
    c=db(); c.execute('SELECT id,name,email,role,phone,address FROM users WHERE id=%s',(session['user_id'],)); u=c.fetchone(); c.close(); return u
def require_user(admin=False):
    u=current_user()
    if not u: flash('Please sign in to continue.','warning'); return None
    if admin and u['role']!='admin': flash('Administrator access is required.','danger'); return None
    return u
# ---------------- CUSTOMER NOTIFICATIONS ----------------
def notify_all_customers(message):
    """Create one notification for every registered customer."""
    c = db()
    try:
        c.execute(
            """
            INSERT INTO notifications (user_id, message)
            SELECT id, %s
            FROM users
            WHERE role = 'customer'
            """,
            (message,)
        )
        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('Could not create customer notifications')
        raise
    finally:
        c.close()


def notify_new_provider(provider_name):
    """Call this immediately after a provider is successfully added."""
    notify_all_customers(
        f"New service provider {provider_name} is now available on HomeEase."
    )


def notify_new_service(service_name):
    """Call this immediately after a new service is successfully added."""
    notify_all_customers(
        f"A new service, {service_name}, is now available on HomeEase."
    )
def recommend(text):
    text=(text or '').lower(); scores=[(sum(w in text for w in vals[2]),name) for name,vals in SERVICES.items()]; score,name=max(scores)
    return name if score else 'Cleaning'
def estimate(category,text): return SERVICES[category][1]+min(1000,max(0,len(text.split())-8)*25)
@app.context_processor
def context(): return {'user':current_user(),'service_icons':{k:v[0] for k,v in SERVICES.items()}}
@app.route('/')
def index(): return render_template('index.html',services=SERVICES)
@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form.get('name','').strip(); email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
        if not name or len(name)>100 or '@' not in email or len(password)<8: flash('Enter a valid name and email. Password must be at least 8 characters.','danger')
        else:
            c=db()
            try:
                c.execute('INSERT INTO users(name,email,password_hash,phone) VALUES(%s,%s,%s,%s)',(name,email,bcrypt.generate_password_hash(password).decode(),request.form.get('phone','').strip())); mysql.connection.commit(); session['user_id']=c.lastrowid; c.close(); return redirect(url_for('dashboard'))
            except Exception:
                mysql.connection.rollback(); c.close(); flash('That email is already registered or registration failed.','danger')
    return render_template('auth.html',mode='register')
@app.route("/provider-login", methods=["GET", "POST"])
def provider_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        cur = mysql.connection.cursor()

        cur.execute(
            """
            SELECT id, password_hash, role
            FROM users
            WHERE email = %s
            """,
            (email,)
        )
        user = cur.fetchone()
        cur.close()

        if (
            user
            and user["role"] == "provider"
            and bcrypt.check_password_hash(
                user["password_hash"], password
            )
        ):
            session["user_id"] = user["id"]
            return redirect(url_for("provider_dashboard"))

        flash("Invalid provider email or password.", "error")

    return render_template("provider_login.html")
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        c=db(); c.execute('SELECT id,password_hash FROM users WHERE email=%s',(request.form.get('email','').strip().lower(),)); row=c.fetchone(); c.close()
        if row and bcrypt.check_password_hash(row['password_hash'],request.form.get('password','')):
            session.clear(); session['user_id']=row['id']; return redirect(url_for('admin') if current_user()['role']=='admin' else url_for('dashboard'))
        flash('Email or password was not recognised.','danger')
    return render_template('auth.html',mode='login')
@app.route('/role-login', methods=['GET', 'POST'])
def role_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')  
        selected_role = request.form.get('role', 'customer')

        # Allow only these three roles
        if selected_role not in ['customer', 'provider', 'admin']:
            flash('Invalid account type.', 'warning')
            return redirect(url_for('role_login'))

        c = db()
        c.execute(
            'SELECT id, password_hash, role FROM users WHERE email = %s',
            (email,)
        )
        account = c.fetchone()
        c.close()

        # Verify account role and password
        if (
            not account
            or account['role'] != selected_role
            or not bcrypt.check_password_hash(
                account['password_hash'], password
            )
        ):
            flash(
                'Invalid email, password, or account type.',
                'warning'
            )
            return redirect(url_for('role_login'))

        session.clear()
        session['user_id'] = account['id']

        # Redirect according to role
        if selected_role == 'admin':
            return redirect(url_for('admin'))

        elif selected_role == 'provider':
            return redirect(url_for('provider_dashboard'))

        else:
            return redirect(url_for('dashboard'))

    return render_template('role_login.html')
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()

        if not email or not phone:
            flash('Please enter your registered email and phone number.', 'warning')
            return render_template('forgot_password.html')

        c = db()
        c.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s AND phone = %s
            """,
            (email, phone)
        )
        account = c.fetchone()
        c.close()

        if account:
            session['password_reset_user_id'] = account['id']
            return redirect(url_for('reset_password'))

        flash('Email or phone number does not match our records.', 'danger')

    return render_template('forgot_password.html')


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    user_id = session.get('password_reset_user_id')

    if not user_id:
        flash('Please verify your account first.', 'warning')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if len(password) < 8:
            flash('Password must contain at least 8 characters.', 'danger')

        elif password != confirm_password:
            flash('Passwords do not match.', 'danger')

        else:
            c = db()

            # Confirm the account still exists.
            c.execute(
                'SELECT id FROM users WHERE id = %s',
                (user_id,)
            )
            account = c.fetchone()

            if not account:
                c.close()
                session.pop('password_reset_user_id', None)
                flash('Account not found. Please try again.', 'danger')
                return redirect(url_for('forgot_password'))

            password_hash = bcrypt.generate_password_hash(
                password
            ).decode('utf-8')

            c.execute(
                'UPDATE users SET password_hash = %s WHERE id = %s',
                (password_hash, user_id)
            )

            mysql.connection.commit()
            c.close()

            session.pop('password_reset_user_id', None)

            flash('Password changed successfully. Please log in.', 'success')
            return redirect(url_for('role_login'))

    return render_template('reset_password.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('index'))
@app.route('/dashboard')
def dashboard():
    u = require_user()

    if not u:
        return redirect(url_for('login'))
    if u['role'] != 'customer':
        flash('This dashboard is for customer accounts.', 'warning')
        return redirect(url_for('provider_dashboard') if u['role'] == 'provider' else url_for('admin'))

    c = db()

    # Customer bookings
    c.execute("""
        SELECT b.*, s.name service_name, p.name provider_name
        FROM bookings b
        JOIN services s ON s.id = b.service_id
        LEFT JOIN providers p ON p.id = b.provider_id
        WHERE b.user_id = %s
        ORDER BY b.created_at DESC
        LIMIT 8
    """, (u['id'],))

    bookings = c.fetchall()

    # Total bookings
    c.execute(
        'SELECT COUNT(*) n FROM bookings WHERE user_id=%s',
        (u['id'],)
    )

    total = c.fetchone()['n']

    # Customer notifications
    c.execute("""
        SELECT id, message, created_at, is_read
        FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (u['id'],))

    notifications = c.fetchall()

    c.close()

    return render_template(
        'dashboard.html',
        bookings=bookings,
        total=total,
        notifications=notifications
    )
@app.route('/book', methods=['GET', 'POST'])
def book():
    u = require_user()

    if not u:
        return redirect(url_for('login'))

    c = db()  

    c.execute(
        'SELECT * FROM services WHERE active=1 ORDER BY name'
    )
    services = c.fetchall()

    if request.method == 'POST':
        desc = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        day = request.form.get('service_date', '')
        provider_id = request.form.get('provider_id', '').strip()

        if (
            category not in SERVICES
            or len(desc) < 8
            or not day
            or day < date.today().isoformat()
            or not provider_id
        ):
            flash(
                'Please select a service, describe your issue, '
                'choose a provider and select a valid date.',
                'danger'
            )
            c.close()
            return render_template(
                'booking.html',
                services=services,
                categories=list(SERVICES),
                today=date.today().isoformat()
            )

        try:
            provider_id = int(provider_id)
        except (ValueError, TypeError):
            flash('Invalid provider selection.', 'danger')
            c.close()
            return render_template(
                'booking.html',
                services=services,
                categories=list(SERVICES),
                today=date.today().isoformat()
            )

        c.execute(
            'SELECT id FROM services WHERE name=%s',
            (category,)
        )
        service = c.fetchone()

        c.execute("""
            SELECT id
            FROM providers
            WHERE id = %s
              AND active = 1
              AND FIND_IN_SET(
                  %s,
                  REPLACE(skills, ', ', ',')
              ) > 0
        """, (provider_id, category))

        provider = c.fetchone()

        if not service or not provider:
            flash(
                'Selected provider is not available for this service. '
                'Please choose another provider.',
                'danger'
            )
            c.close()
            return render_template(
                'booking.html',
                services=services,
                categories=list(SERVICES),
                today=date.today().isoformat()
            )

        cost = estimate(category, desc)

        c.execute("""
            INSERT INTO bookings (
                user_id,
                service_id,
                provider_id,
                description,
                service_date,
                time_slot,
                urgent,
                estimated_cost,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Requested')
        """, (
            u['id'],
            service['id'],
            provider['id'],
            desc,
            day,
            request.form.get('time_slot', 'Morning'),
            bool(request.form.get('urgent')),
            cost
        ))

        mysql.connection.commit()

        booking_id = c.lastrowid
        c.close()

        return redirect(
            url_for('tracking', booking_id=booking_id)
        )

    c.close()

    return render_template(
        'booking.html',
        services=services,
        categories=list(SERVICES),
        today=date.today().isoformat()
    )
@app.route('/api/recommend-provider', methods=['POST'])
def recommend_provider():
    user = current_user()

    if not user:
        return {'error': 'Please log in first.'}, 401

    data = request.get_json(silent=True) or {}
    description = data.get('description', '').strip()
    category = data.get('category', '').strip()

    if category not in SERVICES:
        return {'error': 'Invalid service category.'}, 400

    if len(description) < 8:
        return {'error': 'Please describe your problem.'}, 400

    c = db()

    try:
        c.execute("""
            SELECT id, name, rating, experience_years
            FROM providers
            WHERE active = 1
              AND FIND_IN_SET(
                  %s,
                  REPLACE(skills, ', ', ',')
              ) > 0
            ORDER BY
                COALESCE(rating, 0) DESC,
                COALESCE(experience_years, 0) DESC
        """, (category,))

        rows = c.fetchall()

        providers_list = []

        for provider in rows:
            providers_list.append({
                'id': provider['id'],
                'name': provider['name'],
                'rating': (
                    float(provider['rating'])
                    if provider['rating'] is not None
                    else None
                ),
                'experience_years': provider['experience_years']
            })

        return {'providers': providers_list}, 200

    except Exception:
        app.logger.exception('Provider recommendation failed')
        return {'error': 'Could not find providers.'}, 500

    finally:
        c.close()
@app.route('/providers')
def providers():
    c = db()
    c.execute('SELECT * FROM providers WHERE active=1 ORDER BY rating DESC')
    rows = c.fetchall()
    c.close()
    return render_template('providers.html', providers=rows)

@app.route('/provider-location')
def provider_location():
    user = current_user()

    if not user or user['role'] != 'provider':
        flash('Please log in with a provider account.', 'warning')
        return redirect(url_for('provider_login'))

    booking_id = request.args.get('booking_id', type=int)

    if not booking_id:
        flash('Please select a valid booking.', 'warning')
        return redirect(url_for('provider_dashboard'))

    c = db()
    c.execute("""
        SELECT b.id
        FROM bookings b
        JOIN providers p ON p.id = b.provider_id
        WHERE b.id = %s
          AND p.user_id = %s
          AND b.status IN (
              'Confirmed',
              'Provider on the Way',
              'In Progress'
          )
    """, (booking_id, user['id']))

    booking = c.fetchone()
    c.close()

    if not booking:
        flash('Booking not found or not available for tracking.', 'warning')
        return redirect(url_for('provider_dashboard'))

    return render_template(
        'provider_location.html',
        booking_id=booking_id
    )

@app.route('/update-provider-location', methods=['POST'])
def update_provider_location():
    user = current_user()

    if not user or user['role'] != 'provider':
        return {'error': 'Provider login required.'}, 401

    data = request.get_json(silent=True) or {}

    try:
        booking_id = int(data.get('booking_id'))
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
    except (TypeError, ValueError):
        return {'error': 'Invalid location data.'}, 400

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return {'error': 'Invalid GPS coordinates.'}, 400

    c = db()

    c.execute("""
        SELECT b.id, b.provider_id
        FROM bookings b
        JOIN providers p ON p.id = b.provider_id
        WHERE b.id = %s
          AND p.user_id = %s
          AND b.status IN (
              'Confirmed',
              'Provider on the Way',
              'In Progress'
          )
    """, (booking_id, user['id']))

    booking = c.fetchone()

    if not booking:
        c.close()
        return {
            'error': 'Booking not found, not assigned to you, or not accepted.'
        }, 403

    try:
        c.execute("""
            INSERT INTO provider_locations
                (booking_id, provider_id, latitude, longitude)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                provider_id = VALUES(provider_id),
                latitude = VALUES(latitude),
                longitude = VALUES(longitude),
                updated_at = CURRENT_TIMESTAMP
        """, (
            booking_id,
            booking['provider_id'],
            latitude,
            longitude
        ))

        mysql.connection.commit()
        c.close()

        return {'success': True}, 200

    except Exception:
        mysql.connection.rollback()
        c.close()
        app.logger.exception('Failed to save provider GPS location')
        return {'error': 'Could not save GPS location.'}, 500
@app.route('/provider-dashboard')
def provider_dashboard():
    user = current_user()

    if not user or user['role'] != 'provider':
        flash('Please log in with a provider account.', 'warning')
        return redirect(url_for('provider_login'))

    c = db()

    c.execute("""
        SELECT
            b.id,
            b.description,
            b.service_date,
            b.time_slot,
            b.status,
            b.estimated_cost,
            u.name AS customer_name,
            u.phone AS customer_phone,
            s.name AS service_name
        FROM bookings b
        JOIN providers p ON p.id = b.provider_id
        JOIN services s ON s.id = b.service_id
        JOIN users u ON u.id = b.user_id
        WHERE p.user_id = %s
        ORDER BY b.created_at DESC
    """, (user['id'],))

    bookings = c.fetchall()
    c.close()

    return render_template(
        'provider_dashboard.html',
        bookings=bookings
    )
@app.route('/provider-booking/<int:booking_id>/<action>', methods=['POST'])
def provider_booking_action(booking_id, action):
    user = current_user()

    if not user or user['role'] != 'provider':
        flash('Please log in as a provider.', 'warning')
        return redirect(url_for('provider_login'))

    if action not in ['accept', 'reject']:
        return "Invalid action", 400

    c = db()

    c.execute("""
        SELECT b.id
        FROM bookings b
        JOIN providers p ON p.id = b.provider_id
        WHERE b.id = %s
          AND p.user_id = %s
          AND b.status = 'Requested'
    """, (booking_id, user['id']))

    booking = c.fetchone()

    if not booking:
        c.close()
        return "Booking not found or already processed", 404

    new_status = 'Confirmed' if action == 'accept' else 'Cancelled'

    c.execute("""
        UPDATE bookings
        SET status = %s
        WHERE id = %s AND status = 'Requested'
    """, (new_status, booking_id))

    mysql.connection.commit()
    c.close()

    flash(f'Booking {new_status.lower()} successfully!', 'success')

    return redirect(url_for('provider_dashboard'))
@app.route('/get-provider-location/<int:booking_id>')
def get_provider_location(booking_id):
    user = current_user()

    if not user or user['role'] != 'customer':
        return {'error': 'Please log in as a customer.'}, 401

    c = db()

    c.execute("""
        SELECT
            pl.latitude,
            pl.longitude,
            pl.updated_at
        FROM bookings b
        LEFT JOIN provider_locations pl
            ON pl.booking_id = b.id
        WHERE b.id = %s
          AND b.user_id = %s
          AND b.status IN (
              'Confirmed',
              'Provider on the Way',
              'In Progress'
          )
    """, (booking_id, user['id']))

    location = c.fetchone()
    c.close()

    if not location:
        return {'error': 'Location is not available yet.'}, 404

    if location['latitude'] is None or location['longitude'] is None:
        return {'error': 'Waiting for provider GPS location.'}, 404

    return {
        'latitude': float(location['latitude']),
        'longitude': float(location['longitude']),
        'updated_at': str(location['updated_at'])
    }
@app.route('/tracking/<int:booking_id>')
def tracking(booking_id):
    u = require_user()

    if not u:
        return redirect(url_for('login'))

    c = db()

    c.execute("""
        SELECT
            b.*,
            s.name AS service_name,
            p.name AS provider_name,
            p.phone AS provider_phone,
            p.rating
        FROM bookings b
        JOIN services s ON s.id = b.service_id
        LEFT JOIN providers p ON p.id = b.provider_id
        WHERE b.id = %s AND b.user_id = %s
    """, (booking_id, u['id']))

    booking = c.fetchone()
    c.close()

    if not booking:
        flash('Booking not found.', 'warning')
        return redirect(url_for('dashboard'))

    # Tracking is enabled only after the provider accepts.
    if booking['status'] == 'Requested':
        flash(
            'Tracking will be available after the provider accepts your request.',
            'info'
        )
        return redirect(url_for('dashboard'))

    if booking['status'] == 'Cancelled':
        flash('This booking has been cancelled.', 'warning')
        return redirect(url_for('dashboard'))

    return render_template(
        'tracking.html',
        booking=booking,
        statuses=STATUSES
    )
@app.route('/review/<int:booking_id>', methods=['GET', 'POST'])
def review_booking(booking_id):
    u = require_user()

    if not u:
        return redirect(url_for('login'))

    c = db()

    # Get booking details
    c.execute("""
        SELECT id, user_id, provider_id, status
        FROM bookings
        WHERE id = %s AND user_id = %s
    """, (booking_id, u['id']))

    booking = c.fetchone()

    if not booking:
        c.close()
        flash('Booking not found.', 'warning')
        return redirect(url_for('dashboard'))

    # Review only completed bookings
    if booking['status'] != 'Completed' or not booking['provider_id']:
        c.close()
        flash('You can review only completed services.', 'warning')
        return redirect(
            url_for('tracking', booking_id=booking_id)
        )

    # Check existing review
    c.execute("""
        SELECT id
        FROM reviews
        WHERE booking_id = %s
    """, (booking_id,))

    existing_review = c.fetchone()

    if existing_review:
        c.close()
        flash('You have already reviewed this service.', 'info')
        return redirect(
            url_for('tracking', booking_id=booking_id)
        )

    # Submit review
    if request.method == 'POST':

        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '').strip()

        if rating not in (1, 2, 3, 4, 5):
            c.close()
            flash('Please select a rating from 1 to 5.', 'warning')
            return redirect(
                url_for('review_booking', booking_id=booking_id)
            )

        c.execute("""
            INSERT INTO reviews
                (booking_id, customer_id, provider_id, rating, comment)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            booking_id,
            u['id'],
            booking['provider_id'],
            rating,
            comment
        ))

        # Update provider rating
        c.execute("""
            UPDATE providers
            SET rating = (
                SELECT AVG(rating)
                FROM reviews
                WHERE provider_id = %s
            )
            WHERE id = %s
        """, (
            booking['provider_id'],
            booking['provider_id']
        ))

        mysql.connection.commit()
        c.close()

        flash('Thank you for your review!', 'success')

        return redirect(
            url_for('tracking', booking_id=booking_id)
        )

    c.close()

    return render_template(
        'review.html',
        booking=booking
    ) 
@app.route('/history')
def history():
    u=require_user()
    if not u:return redirect(url_for('login'))
    c=db(); c.execute('SELECT b.*,s.name service_name,p.name provider_name,r.id report_id FROM bookings b JOIN services s ON s.id=b.service_id LEFT JOIN providers p ON p.id=b.provider_id LEFT JOIN service_reports r ON r.booking_id=b.id WHERE b.user_id=%s ORDER BY b.created_at DESC',(u['id'],)); rows=c.fetchall(); c.close(); return render_template('history.html',bookings=rows)
@app.route('/payment/<int:booking_id>',methods=['GET','POST'])
def payment(booking_id):
    u=require_user()
    if not u:return redirect(url_for('login'))
    c=db(); c.execute('SELECT b.*,s.name service_name FROM bookings b JOIN services s ON s.id=b.service_id WHERE b.id=%s AND b.user_id=%s',(booking_id,u['id'])); b=c.fetchone()
    if not b:c.close(); return redirect(url_for('dashboard'))
    if request.method=='POST':
        c.execute("INSERT INTO payments(booking_id,amount,method,status,transaction_ref) VALUES(%s,%s,%s,'Paid',%s) ON DUPLICATE KEY UPDATE status='Paid',method=VALUES(method)",(booking_id,b['estimated_cost'],request.form.get('method','Demo card'),'DEMO-'+datetime.now().strftime('%Y%m%d%H%M%S'))); mysql.connection.commit(); c.close(); flash('Demo payment recorded. No real money was charged.','success'); return redirect(url_for('history'))
    c.close(); return render_template('payment.html',booking=b)
@app.route('/report/<int:booking_id>')
def report(booking_id):
    u=require_user()
    if not u:return redirect(url_for('login'))
    c=db(); c.execute('SELECT r.*,b.service_date,s.name service_name,p.name provider_name,w.duration_months,w.expiry_date FROM service_reports r JOIN bookings b ON b.id=r.booking_id JOIN services s ON s.id=b.service_id LEFT JOIN providers p ON p.id=b.provider_id LEFT JOIN warranties w ON w.report_id=r.id WHERE r.booking_id=%s AND b.user_id=%s',(booking_id,u['id'])); r=c.fetchone(); c.close(); return render_template('report.html',report=r)
@app.route('/profile',methods=['GET','POST'])
def profile():
    u=require_user()
    if not u:return redirect(url_for('login'))
    if request.method=='POST':
        c=db(); c.execute('UPDATE users SET name=%s,phone=%s,address=%s WHERE id=%s',(request.form.get('name','').strip(),request.form.get('phone','').strip(),request.form.get('address','').strip(),u['id'])); mysql.connection.commit(); c.close(); flash('Profile saved.','success'); return redirect(url_for('profile'))
    return render_template('profile.html')
@app.route('/admin')
def admin():
    u=require_user(True)
    if not u:return redirect(url_for('login'))
    c=db(); c.execute('SELECT b.*,u.name customer_name,s.name service_name FROM bookings b JOIN users u ON u.id=b.user_id JOIN services s ON s.id=b.service_id ORDER BY b.urgent DESC,b.created_at DESC'); rows=c.fetchall(); c.execute("SELECT COUNT(*) n FROM users WHERE role='customer'"); customers=c.fetchone()['n']; c.execute('SELECT COUNT(*) n FROM providers'); providers_count=c.fetchone()['n']; c.close(); return render_template('admin.html',bookings=rows,customers=customers,provider_count=providers_count,statuses=STATUSES)
@app.route('/admin/booking/<int:booking_id>',methods=['POST'])
def update_booking(booking_id):
    if not require_user(True):return redirect(url_for('login'))
    status=request.form.get('status')
    if status not in STATUSES:return redirect(url_for('admin'))
    c=db(); c.execute('UPDATE bookings SET status=%s WHERE id=%s',(status,booking_id))
    if status=='Completed': c.execute("INSERT IGNORE INTO service_reports(booking_id,work_details,materials_used,final_cost) SELECT id,'Service completed. Please update notes.','To be updated',estimated_cost FROM bookings WHERE id=%s",(booking_id,))
    mysql.connection.commit(); c.close(); return redirect(url_for('admin'))
if __name__=='__main__': app.run(debug=os.getenv('FLASK_DEBUG','0')=='1')

import os
from datetime import date, datetime
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config.update(SECRET_KEY=os.getenv('SECRET_KEY', 'dev-only-change-this-key'), MYSQL_HOST=os.getenv('MYSQL_HOST', 'localhost'), MYSQL_USER=os.getenv('MYSQL_USER', 'root'), MYSQL_PASSWORD=os.getenv('MYSQL_PASSWORD', ''), MYSQL_DB=os.getenv('MYSQL_DB', 'homeease'), MYSQL_CURSORCLASS='DictCursor')
mysql, bcrypt = MySQL(app), Bcrypt(app)
SERVICES = {'Plumbing': ('🚿',450,['leak','tap','pipe','drain','plumb','water','toilet']), 'Electrical': ('⚡',500,['electric','wire','light','switch','power','fan','socket']), 'Cleaning': ('🧹',350,['clean','dust','deep clean','kitchen','bathroom']), 'Carpentry': ('🪚',550,['wood','door','cabinet','furniture','carpenter','shelf']), 'Appliance Repair': ('🧰',600,['fridge','washer','washing machine','ac','appliance','oven','machine'])}
STATUSES = ('Requested','Confirmed','Provider on the Way','In Progress','Completed','Cancelled')

def db(): return mysql.connection.cursor()
def current_user():
    if not session.get('user_id'): return None
    c=db(); c.execute('SELECT id,name,email,role,phone,address FROM users WHERE id=%s',(session['user_id'],)); u=c.fetchone(); c.close(); return u
def require_user(admin=False):
    u=current_user()
    if not u: flash('Please sign in to continue.','warning'); return None
    if admin and u['role']!='admin': flash('Administrator access is required.','danger'); return None
    return u
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
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        c=db(); c.execute('SELECT id,password_hash FROM users WHERE email=%s',(request.form.get('email','').strip().lower(),)); row=c.fetchone(); c.close()
        if row and bcrypt.check_password_hash(row['password_hash'],request.form.get('password','')):
            session.clear(); session['user_id']=row['id']; return redirect(url_for('admin') if current_user()['role']=='admin' else url_for('dashboard'))
        flash('Email or password was not recognised.','danger')
    return render_template('auth.html',mode='login')
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('index'))
@app.route('/dashboard')
def dashboard():
    u=require_user()
    if not u:return redirect(url_for('login'))
    c=db(); c.execute('SELECT b.*,s.name service_name,p.name provider_name FROM bookings b JOIN services s ON s.id=b.service_id LEFT JOIN providers p ON p.id=b.provider_id WHERE b.user_id=%s ORDER BY b.created_at DESC LIMIT 8',(u['id'],)); bookings=c.fetchall(); c.execute('SELECT COUNT(*) n FROM bookings WHERE user_id=%s',(u['id'],)); total=c.fetchone()['n']; c.close(); return render_template('dashboard.html',bookings=bookings,total=total)
@app.route('/book',methods=['GET','POST'])
def book():
    u=require_user()
    if not u:return redirect(url_for('login'))
    c=db(); c.execute('SELECT * FROM services WHERE active=1 ORDER BY name'); services=c.fetchall()
    if request.method=='POST':
        desc=request.form.get('description','').strip(); category=request.form.get('category') or recommend(desc); day=request.form.get('service_date')
        if category not in SERVICES or len(desc)<8 or not day or day<date.today().isoformat(): flash('Choose a service and future date; describe the issue in at least 8 characters.','danger')
        else:
            c.execute('SELECT id FROM services WHERE name=%s',(category,)); service=c.fetchone(); c.execute("SELECT id FROM providers WHERE active=1 AND FIND_IN_SET(%s,REPLACE(skills,', ',','))>0 ORDER BY rating DESC,experience_years DESC LIMIT 1",(category,)); p=c.fetchone(); cost=estimate(category,desc)
            c.execute("INSERT INTO bookings(user_id,service_id,provider_id,description,service_date,time_slot,urgent,estimated_cost,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'Requested')",(u['id'],service['id'],p['id'] if p else None,desc,day,request.form.get('time_slot','Morning'),bool(request.form.get('urgent')),cost)); mysql.connection.commit(); bid=c.lastrowid; c.close(); return redirect(url_for('tracking',booking_id=bid))
    c.close(); return render_template('booking.html',services=services,categories=list(SERVICES),today=date.today().isoformat())
@app.route('/providers')
def providers():
    c=db(); c.execute('SELECT * FROM providers WHERE active=1 ORDER BY rating DESC'); rows=c.fetchall(); c.close(); return render_template('providers.html',providers=rows)
@app.route('/tracking/<int:booking_id>')
def tracking(booking_id):
    u=require_user()
    if not u:return redirect(url_for('login'))
    c=db(); c.execute('SELECT b.*,s.name service_name,p.name provider_name,p.phone provider_phone,p.rating FROM bookings b JOIN services s ON s.id=b.service_id LEFT JOIN providers p ON p.id=b.provider_id WHERE b.id=%s AND b.user_id=%s',(booking_id,u['id'])); b=c.fetchone(); c.close()
    if not b: return redirect(url_for('dashboard'))
    return render_template('tracking.html',booking=b,statuses=STATUSES)
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

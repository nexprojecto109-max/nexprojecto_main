# ╔══════════════════════════════════════════════════════╗
# ║         NEXPROJECTO - Complete Backend              ║
# ╚══════════════════════════════════════════════════════╝

from flask import Flask, request, jsonify, session, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, random, string

app = Flask(__name__, template_folder='templates')

# ── CONFIG ──────────────────────────────────────────────
app.config['SECRET_KEY'] = 'nexprojecto_ultra_secret_2024_xK9mP'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nexprojecto.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, supports_credentials=True, origins=['http://localhost:5000', 'http://127.0.0.1:5000', '*'])

db = SQLAlchemy(app)


# ============ MODELS (Same as before) ============
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    avatar_color = db.Column(db.String(20), default='#6366f1')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    long_desc = db.Column(db.Text)
    category = db.Column(db.String(100), nullable=False)
    tech_stack = db.Column(db.String(300))
    price = db.Column(db.Float, nullable=False)
    original_price = db.Column(db.Float)
    features = db.Column(db.Text)
    icon = db.Column(db.String(10), default='🚀')
    gradient = db.Column(db.String(100), default='135deg, #6366f1, #8b5cf6')
    is_featured = db.Column(db.Boolean, default=False)
    downloads = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=4.5)
    download_url = db.Column(db.String(500), default='https://github.com/example/project-source/archive/refs/heads/main.zip')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_ref = db.Column(db.String(20), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    amount = db.Column(db.Float)
    payment_method = db.Column(db.String(50))
    payment_detail = db.Column(db.String(200))
    status = db.Column(db.String(30), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='orders')
    project = db.relationship('Project', backref='orders')


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    rating = db.Column(db.Integer, default=5)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='reviews')


class CustomizationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    project_title = db.Column(db.String(200), nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    budget = db.Column(db.Float)
    target_date = db.Column(db.String(50))
    status = db.Column(db.String(30), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='customization_requests')


# ── FRONTEND ROUTE ───────────────────────────────────────
@app.route('/')
def serve_frontend():
    import os
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    if os.path.exists(template_path):
        return render_template('index.html')
    else:
        return f"Template not found at {template_path}. Please create templates folder and add index.html"


# ── HELPERS ─────────────────────────────────────────────
def gen_order_ref():
    return 'NXP-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def current_user():
    uid = session.get('user_id')
    return User.query.get(uid) if uid else None


def project_dict(p, full=False, include_download=False):
    d = {
        'id': p.id, 'title': p.title, 'description': p.description,
        'category': p.category, 'tech_stack': p.tech_stack, 'price': p.price,
        'original_price': p.original_price, 'icon': p.icon, 'gradient': p.gradient,
        'is_featured': p.is_featured, 'downloads': p.downloads, 'rating': p.rating,
        'created_at': p.created_at.strftime('%b %d, %Y'),
        'discount': int((1 - p.price / p.original_price) * 100) if p.original_price else 0,
        'features': p.features or ''
    }
    if full:
        d['long_desc'] = p.long_desc or p.description
    if include_download:
        d['download_url'] = p.download_url
    return d


# ── AUTH ROUTES ─────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    d = request.json
    if not d.get('name') or not d.get('email') or not d.get('password'):
        return jsonify({'error': 'All fields required'}), 400
    if len(d['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if User.query.filter_by(email=d['email'].lower()).first():
        return jsonify({'error': 'Email already registered'}), 409
    colors = ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899']
    user = User(
        name=d['name'].strip(),
        email=d['email'].lower().strip(),
        password=generate_password_hash(d['password']),
        avatar_color=random.choice(colors)
    )
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    return jsonify({'success': True,
                    'user': {'id': user.id, 'name': user.name, 'email': user.email, 'is_admin': user.is_admin,
                             'avatar_color': user.avatar_color}})


@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    user = User.query.filter_by(email=d.get('email', '').lower()).first()
    if not user or not check_password_hash(user.password, d.get('password', '')):
        return jsonify({'error': 'Invalid email or password'}), 401
    session['user_id'] = user.id
    return jsonify({'success': True,
                    'user': {'id': user.id, 'name': user.name, 'email': user.email, 'is_admin': user.is_admin,
                             'avatar_color': user.avatar_color}})


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/me')
def me():
    u = current_user()
    if not u: return jsonify({'user': None})
    return jsonify({'user': {'id': u.id, 'name': u.name, 'email': u.email, 'is_admin': u.is_admin,
                             'avatar_color': u.avatar_color}})


# ── PROJECT ROUTES ───────────────────────────────────────
@app.route('/api/projects')
def get_projects():
    q = request.args.get('q', '').lower()
    cat = request.args.get('category', '')
    sort = request.args.get('sort', 'featured')
    query = Project.query
    if cat and cat != 'all':
        query = query.filter_by(category=cat)
    if q:
        query = query.filter(
            (Project.title.ilike(f'%{q}%')) |
            (Project.description.ilike(f'%{q}%')) |
            (Project.tech_stack.ilike(f'%{q}%'))
        )
    if sort == 'price_low':
        query = query.order_by(Project.price.asc())
    elif sort == 'price_high':
        query = query.order_by(Project.price.desc())
    elif sort == 'newest':
        query = query.order_by(Project.created_at.desc())
    elif sort == 'popular':
        query = query.order_by(Project.downloads.desc())
    else:
        query = query.order_by(Project.is_featured.desc(), Project.created_at.desc())
    return jsonify({'projects': [project_dict(p) for p in query.all()]})


@app.route('/api/projects/<int:pid>')
def get_project(pid):
    p = Project.query.get_or_404(pid)
    u = current_user()
    purchased = False
    if u:
        purchased = Order.query.filter_by(user_id=u.id, project_id=pid, status='completed').first() is not None
        if u.is_admin:
            purchased = True
    
    res_dict = project_dict(p, full=True)
    if purchased:
        res_dict['download_url'] = p.download_url
    else:
        res_dict['download_url'] = None
    res_dict['purchased'] = purchased
    return jsonify({'project': res_dict})


@app.route('/api/projects/<int:pid>/download')
def download_project(pid):
    u = current_user()
    if not u:
        return jsonify({'error': 'Login required'}), 401
    
    purchased = Order.query.filter_by(user_id=u.id, project_id=pid, status='completed').first() is not None
    if u.is_admin:
        purchased = True
        
    if not purchased:
        return jsonify({'error': 'You must purchase this project to download it'}), 403
        
    p = Project.query.get_or_404(pid)
    return jsonify({'success': True, 'download_url': p.download_url})


@app.route('/api/categories')
def get_categories():
    cats = db.session.query(Project.category, db.func.count(Project.id)).group_by(Project.category).all()
    return jsonify({'categories': [{'name': c[0], 'count': c[1]} for c in cats]})


# ── CART ROUTES ──────────────────────────────────────────
@app.route('/api/cart')
def get_cart():
    u = current_user()
    if not u: return jsonify({'items': [], 'total': 0})
    items = CartItem.query.filter_by(user_id=u.id).all()
    projects = [Project.query.get(i.project_id) for i in items]
    projects = [p for p in projects if p]
    total = sum(p.price for p in projects)
    return jsonify({'items': [
        {'project_id': p.id, 'title': p.title, 'price': p.price, 'icon': p.icon, 'gradient': p.gradient,
         'category': p.category} for p in projects], 'total': round(total, 2), 'count': len(projects)})


@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    u = current_user()
    if not u: return jsonify({'error': 'Login required'}), 401
    pid = request.json.get('project_id')
    if not Project.query.get(pid): return jsonify({'error': 'Project not found'}), 404
    if not CartItem.query.filter_by(user_id=u.id, project_id=pid).first():
        db.session.add(CartItem(user_id=u.id, project_id=pid))
        db.session.commit()
    return jsonify({'success': True})


@app.route('/api/cart/remove', methods=['POST'])
def remove_from_cart():
    u = current_user()
    if not u: return jsonify({'error': 'Login required'}), 401
    CartItem.query.filter_by(user_id=u.id, project_id=request.json.get('project_id')).delete()
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/cart/clear', methods=['POST'])
def clear_cart():
    u = current_user()
    if not u: return jsonify({'error': 'Login required'}), 401
    CartItem.query.filter_by(user_id=u.id).delete()
    db.session.commit()
    return jsonify({'success': True})


# ── ORDER ROUTES ─────────────────────────────────────────
@app.route('/api/order', methods=['POST'])
def create_order():
    u = current_user()
    if not u: return jsonify({'error': 'Login required'}), 401
    d = request.json
    created = []
    for pid in d.get('project_ids', []):
        p = Project.query.get(pid)
        if not p: continue
        existing = Order.query.filter_by(user_id=u.id, project_id=pid, status='completed').first()
        if existing:
            created.append({'ref': existing.order_ref, 'title': p.title})
            continue
        ref = gen_order_ref()
        o = Order(
            order_ref=ref, user_id=u.id, project_id=pid,
            amount=round(p.price * 1.18, 2),
            payment_method=d.get('payment_method', 'demo'),
            payment_detail=d.get('payment_detail', ''),
            status='completed'
        )
        p.downloads += 1
        db.session.add(o)
        created.append({'ref': ref, 'title': p.title})
    db.session.commit()
    return jsonify({'success': True, 'orders': created})


@app.route('/api/my-orders')
def my_orders():
    u = current_user()
    if not u: return jsonify({'orders': []})
    orders = Order.query.filter_by(user_id=u.id).order_by(Order.created_at.desc()).all()
    return jsonify({'orders': [{
        'id': o.id, 'order_ref': o.order_ref,
        'project_id': o.project_id,
        'project_title': o.project.title,
        'project_icon': o.project.icon,
        'project_gradient': o.project.gradient,
        'amount': o.amount, 'payment_method': o.payment_method,
        'status': o.status, 'date': o.created_at.strftime('%b %d, %Y'),
        'download_url': o.project.download_url if o.status == 'completed' else None
    } for o in orders]})


@app.route('/logo.jfif')
def serve_logo():
    import os
    return send_from_directory(os.path.dirname(__file__), 'logo.jfif')


# ── CUSTOMIZATION REQUEST ROUTES ─────────────────────────────
@app.route('/api/customization/submit', methods=['POST'])
def submit_customization():
    d = request.json
    if not d.get('name') or not d.get('email') or not d.get('project_title') or not d.get('requirements'):
        return jsonify({'error': 'Name, Email, Project Title, and Requirements are required'}), 400
    
    u = current_user()
    req = CustomizationRequest(
        user_id=u.id if u else None,
        name=d['name'].strip(),
        email=d['email'].strip().lower(),
        project_title=d['project_title'].strip(),
        requirements=d['requirements'].strip(),
        budget=float(d.get('budget')) if d.get('budget') else None,
        target_date=d.get('target_date', '')
    )
    db.session.add(req)
    db.session.commit()
    return jsonify({'success': True, 'id': req.id})


@app.route('/api/customization/my-requests')
def my_customizations():
    u = current_user()
    if not u: return jsonify({'requests': []})
    reqs = CustomizationRequest.query.filter_by(user_id=u.id).order_by(CustomizationRequest.created_at.desc()).all()
    return jsonify({'requests': [{
        'id': r.id, 'project_title': r.project_title, 'requirements': r.requirements,
        'budget': r.budget, 'target_date': r.target_date, 'status': r.status,
        'date': r.created_at.strftime('%b %d, %Y')
    } for r in reqs]})


@app.route('/api/admin/customizations')
def admin_customizations():
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'Admin access required'}), 403
    reqs = CustomizationRequest.query.order_by(CustomizationRequest.created_at.desc()).all()
    return jsonify({'requests': [{
        'id': r.id, 'user_name': r.name, 'user_email': r.email,
        'project_title': r.project_title, 'requirements': r.requirements,
        'budget': r.budget, 'target_date': r.target_date, 'status': r.status,
        'date': r.created_at.strftime('%b %d, %Y')
    } for r in reqs]})


@app.route('/api/admin/customization/<int:rid>/status', methods=['POST'])
def admin_update_customization_status(rid):
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'Admin access required'}), 403
    d = request.json
    status = d.get('status')
    if not status: return jsonify({'error': 'Status is required'}), 400
    
    req = CustomizationRequest.query.get_or_404(rid)
    req.status = status
    db.session.commit()
    return jsonify({'success': True})


# ── ADMIN ROUTES ─────────────────────────────────────────
@app.route('/api/admin/stats')
def admin_stats():
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'Admin access required'}), 403
    revenue = db.session.query(db.func.sum(Order.amount)).filter_by(status='completed').scalar() or 0
    return jsonify({
        'projects': Project.query.count(),
        'users': User.query.filter_by(is_admin=False).count(),
        'orders': Order.query.count(),
        'revenue': round(revenue, 2),
        'today_orders': Order.query.filter(db.func.date(Order.created_at) == datetime.utcnow().date()).count()
    })


@app.route('/api/admin/projects')
def admin_get_projects():
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'Admin access required'}), 403
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return jsonify({'projects': [project_dict(p, include_download=True) for p in projects]})


@app.route('/api/admin/project', methods=['POST'])
def admin_add_project():
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'Admin access required'}), 403
    d = request.json
    p = Project(
        title=d['title'], description=d['description'],
        category=d['category'], price=float(d['price']),
        icon=d.get('icon', '🚀'), gradient=d.get('gradient', '135deg, #6366f1, #8b5cf6'),
        download_url=d.get('download_url', 'https://github.com/example/project-source/archive/refs/heads/main.zip')
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'success': True, 'id': p.id})


@app.route('/api/admin/project/<int:pid>', methods=['DELETE'])
def admin_delete_project(pid):
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'Admin access required'}), 403
    p = Project.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/admin/transactions')
def admin_transactions():
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'Admin access required'}), 403
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify({'orders': [{
        'order_ref': o.order_ref, 'user_name': o.user.name,
        'project_title': o.project.title, 'amount': o.amount,
        'status': o.status, 'date': o.created_at.strftime('%b %d, %Y')
    } for o in orders]})


@app.route('/api/admin/users')
def admin_users():
    u = current_user()
    if not u or not u.is_admin: return jsonify({'error': 'Admin access required'}), 403
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({'users': [{'id': u.id, 'name': u.name, 'email': u.email, 'is_admin': u.is_admin} for u in users]})


# ── SEED DATA ───────────────────────────────────────────────
def seed_data():
    if User.query.first():
        return

    # Create admin
    admin = User(
        name='Admin',
        email='admin@nexprojecto.com',
        password=generate_password_hash('admin@123'),
        is_admin=True,
        avatar_color='#6366f1'
    )
    db.session.add(admin)

    # Sample projects
    sample_projects = [
        {'title': 'E-Commerce Platform', 'description': 'Full-stack e-commerce with cart and payments',
         'category': 'Web Development', 'price': 799, 'icon': '🛒', 'download_url': 'https://github.com/vks21/ecommerce-platform/archive/refs/heads/main.zip'},
        {'title': 'Face Recognition System', 'description': 'AI-powered attendance system',
         'category': 'Machine Learning', 'price': 999, 'icon': '👁️', 'download_url': 'https://github.com/vks21/face-recognition/archive/refs/heads/main.zip'},
        {'title': 'Hospital Management', 'description': 'Complete hospital ERP system', 'category': 'Web Development',
         'price': 1299, 'icon': '🏥', 'download_url': 'https://github.com/vks21/hospital-management/archive/refs/heads/main.zip'},
        {'title': 'Chat Application', 'description': 'Real-time messaging app', 'category': 'Web Development',
         'price': 499, 'icon': '💬', 'download_url': 'https://github.com/vks21/chat-app/archive/refs/heads/main.zip'},
        {'title': 'URL Shortener', 'description': 'Bit.ly clone with analytics', 'category': 'API/Backend',
         'price': 299, 'icon': '🔗', 'download_url': 'https://github.com/vks21/url-shortener/archive/refs/heads/main.zip'},
    ]

    for p in sample_projects:
        project = Project(**p)
        db.session.add(project)

    db.session.commit()
    print("[+] Database seeded with admin and sample projects!")

@app.route('/test')
def test():
    return "Hello! Flask is working!"

# ── MAIN ────────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            # Test queries to check schema validity
            Project.query.filter_by(download_url='test_probe').first()
            CustomizationRequest.query.first()
        except Exception as e:
            print("[!] Database schema mismatch detected. Recreating database...")
            try:
                db.drop_all()
            except Exception as drop_err:
                print(f"Error dropping tables: {drop_err}")
                db_path = os.path.join(app.instance_path, 'nexprojecto.db')
                if os.path.exists(db_path):
                    try:
                        os.remove(db_path)
                    except Exception as rm_err:
                        print(f"Could not remove db file: {rm_err}")
            db.create_all()
        seed_data()

    print("\n" + "=" * 55)
    print("  [>] NEXPROJECTO Running!")
    print("  URL: http://localhost:5000")
    print("  Admin: admin@nexprojecto.com / admin@123")
    print("=" * 55 + "\n")
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, port=port, host='0.0.0.0')

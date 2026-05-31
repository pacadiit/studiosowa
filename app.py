import os
import uuid
import json
from datetime import datetime
from functools import wraps

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import cloudinary
import cloudinary.uploader

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, abort, jsonify, send_from_directory)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from slugify import slugify
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'studiosowa-dev-key-change-in-prod')

# Database — PostgreSQL en production (Railway), SQLite en local
DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or f"sqlite:///{os.path.join(BASE_DIR, 'studiosowa.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 80 * 1024 * 1024  # 80 MB

def get_admin_password():
    return os.environ.get('ADMIN_PASSWORD', 'sowa2024!')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}

# Cloudinary — stockage cloud des images (production)
# En local : les images restent sur le disque
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
CLOUDINARY_API_KEY    = os.environ.get('CLOUDINARY_API_KEY', '')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '')
CLOUDINARY_CONFIGURED = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)

if CLOUDINARY_CONFIGURED:
    cloudinary.config(
        cloud_name = CLOUDINARY_CLOUD_NAME,
        api_key    = CLOUDINARY_API_KEY,
        api_secret = CLOUDINARY_API_SECRET,
        secure     = True,
    )

# Mail config (optional — only used if MAIL_USERNAME is set in .env)
MAIL_SERVER    = os.environ.get('MAIL_SERVER',    'smtp.gmail.com')
MAIL_PORT      = int(os.environ.get('MAIL_PORT',  '587'))
MAIL_USE_TLS   = os.environ.get('MAIL_USE_TLS',   'true').lower() == 'true'
MAIL_USERNAME  = os.environ.get('MAIL_USERNAME',  '')
MAIL_PASSWORD  = os.environ.get('MAIL_PASSWORD',  '')
MAIL_RECIPIENT = os.environ.get('MAIL_RECIPIENT', MAIL_USERNAME)

db = SQLAlchemy(app)

# Redirection www → non-www
@app.before_request
def redirect_www():
    host = request.host
    if host and host.startswith('www.'):
        return redirect('https://studiosowa.com' + request.full_path.rstrip('?'), 301)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Project(db.Model):
    __tablename__ = 'projects'

    id            = db.Column(db.Integer, primary_key=True)
    slug          = db.Column(db.String(300), unique=True, nullable=False)

    title_fr      = db.Column(db.String(400), nullable=False, default='')
    title_en      = db.Column(db.String(400), nullable=False, default='')
    description_fr = db.Column(db.Text, default='')
    description_en = db.Column(db.Text, default='')

    location      = db.Column(db.String(300), default='')
    year          = db.Column(db.String(10),  default='')
    architect     = db.Column(db.String(300), default='')
    client        = db.Column(db.String(300), default='')
    phase         = db.Column(db.String(200), default='')
    category      = db.Column(db.String(150), default='')
    surface       = db.Column(db.String(100), default='')
    programme     = db.Column(db.String(300), default='')

    featured_image = db.Column(db.String(600), default='')
    image_size     = db.Column(db.String(20),  default='large')   # 'large' | 'medium'

    sort_order    = db.Column(db.Integer, default=0)
    published     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = db.relationship(
        'ProjectImage', backref='project', lazy=True,
        order_by='ProjectImage.sort_order',
        cascade='all, delete-orphan'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'slug': self.slug,
            'title_fr': self.title_fr,
            'title_en': self.title_en,
            'location': self.location,
            'year': self.year,
            'image_size': self.image_size,
            'featured_image': self.featured_image,
            'published': self.published,
        }


class ProjectImage(db.Model):
    __tablename__ = 'project_images'

    id         = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    filename   = db.Column(db.String(600), nullable=False)
    caption_fr = db.Column(db.String(400), default='')
    caption_en = db.Column(db.String(400), default='')
    sort_order = db.Column(db.Integer, default=0)
    is_cover   = db.Column(db.Boolean, default=False)

    @property
    def url(self):
        return image_url(self.filename)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def cloudinary_public_id(url):
    """Extraire le public_id Cloudinary depuis une URL sécurisée."""
    if not url or 'cloudinary.com' not in url:
        return None
    try:
        parts = url.split('/upload/')
        path = parts[1]
        if path.startswith('v') and '/' in path:
            path = path.split('/', 1)[1]
        return path.rsplit('.', 1)[0]
    except Exception:
        return None


def is_cloudinary_url(value):
    return value and isinstance(value, str) and 'cloudinary.com' in value


def image_url(filename):
    """Retourner l'URL d'une image (Cloudinary ou locale)."""
    if not filename:
        return ''
    if is_cloudinary_url(filename):
        return filename
    return url_for('static', filename=f'uploads/{filename}')


# Rendre image_url accessible dans tous les templates
app.jinja_env.globals['image_url'] = image_url


def save_image(file):
    """
    Sauvegarder une image uploadée.
    - En production (Cloudinary configuré) : upload vers Cloudinary, retourne l'URL sécurisée.
    - En local : sauvegarde sur disque, retourne le nom de fichier.
    """
    if CLOUDINARY_CONFIGURED:
        # Optimiser l'image avant upload
        img = Image.open(file)
        img = img.convert('RGB')
        max_dim = 2400
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)

        import io
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=88, optimize=True)
        buffer.seek(0)

        result = cloudinary.uploader.upload(
            buffer,
            folder='studiosowa',
            resource_type='image',
            quality='auto',
            fetch_format='auto',
        )
        return result['secure_url']
    else:
        # Stockage local (développement)
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{'jpg' if ext == 'jpeg' else ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        img = Image.open(file)
        img = img.convert('RGB')
        max_dim = 2400
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        img.save(filepath, quality=88, optimize=True)
        return filename


def delete_image_file(filename):
    """Supprimer une image (Cloudinary ou disque local)."""
    if not filename:
        return
    if is_cloudinary_url(filename):
        public_id = cloudinary_public_id(filename)
        if public_id:
            try:
                cloudinary.uploader.destroy(public_id)
            except Exception:
                pass
    else:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        except FileNotFoundError:
            pass


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def send_contact_email(name, email, subject, message):
    """Send a contact form email. Returns (success: bool, error: str)."""
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        return False, 'SMTP non configuré (voir .env)'

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'[StudioSowa] {subject or "Message de contact"}'
    msg['From']    = MAIL_USERNAME
    msg['To']      = MAIL_RECIPIENT
    msg['Reply-To'] = f'{name} <{email}>'

    body_text = f"De : {name} <{email}>\n\n{message}"
    body_html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#222;max-width:600px;margin:auto">
      <p style="font-size:13px;color:#999;letter-spacing:.1em;text-transform:uppercase">
        Message via studiosowa.com</p>
      <h2 style="font-weight:300;font-size:22px">{subject or 'Message de contact'}</h2>
      <p><strong>De :</strong> {name} &lt;{email}&gt;</p>
      <hr style="border:none;border-top:1px solid #eee;margin:16px 0">
      <p style="line-height:1.7">{message.replace(chr(10), '<br>')}</p>
    </body></html>
    """

    msg.attach(MIMEText(body_text, 'plain'))
    msg.attach(MIMEText(body_html, 'html'))

    try:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10) as smtp:
            if MAIL_USE_TLS:
                smtp.starttls()
            smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
            smtp.sendmail(MAIL_USERNAME, MAIL_RECIPIENT, msg.as_string())
        return True, ''
    except Exception as e:
        return False, str(e)


def unique_slug(base, project_id=None):
    slug = slugify(base)
    candidate = slug
    counter = 1
    while True:
        existing = Project.query.filter_by(slug=candidate).first()
        if not existing or (project_id and existing.id == project_id):
            return candidate
        candidate = f"{slug}-{counter}"
        counter += 1


# ---------------------------------------------------------------------------
# Context processor – inject language into all templates
# ---------------------------------------------------------------------------

@app.context_processor
def inject_lang():
    lang = request.args.get('lang', request.cookies.get('lang', 'fr'))
    if lang not in ('fr', 'en'):
        lang = 'fr'
    return dict(lang=lang)


# ---------------------------------------------------------------------------
# PUBLIC ROUTES
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    projects = (Project.query
                .filter_by(published=True)
                .order_by(Project.sort_order, Project.created_at.desc())
                .all())
    return render_template('index.html', projects=projects)


@app.route('/projet/<slug>')
@app.route('/project/<slug>')
def project_detail(slug):
    project = Project.query.filter_by(slug=slug, published=True).first_or_404()
    # Next & previous
    all_projects = (Project.query
                    .filter_by(published=True)
                    .order_by(Project.sort_order, Project.created_at.desc())
                    .all())
    ids = [p.id for p in all_projects]
    idx = ids.index(project.id)
    prev_project = all_projects[idx - 1] if idx > 0 else None
    next_project = all_projects[idx + 1] if idx < len(all_projects) - 1 else None
    return render_template('project.html', project=project,
                           prev_project=prev_project, next_project=next_project)


@app.route('/studio')
def studio():
    return render_template('studio.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    sent = False
    mail_error = ''
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if name and email and message:
            ok, err = send_contact_email(name, email, subject, message)
            if ok:
                sent = True
            else:
                mail_error = err
        else:
            mail_error = 'Tous les champs obligatoires doivent être remplis.'

    return render_template('contact.html', sent=sent, mail_error=mail_error)


@app.route('/projet/<slug>/fiche')
@app.route('/project/<slug>/sheet')
def project_sheet(slug):
    """Print-optimised PDF sheet for a project."""
    project = Project.query.filter_by(slug=slug, published=True).first_or_404()
    return render_template('project_sheet.html', project=project)


@app.route('/set-lang/<lang>')
def set_lang(lang):
    if lang not in ('fr', 'en'):
        lang = 'fr'
    redirect_url = request.referrer or url_for('index')
    response = redirect(redirect_url)
    response.set_cookie('lang', lang, max_age=60 * 60 * 24 * 365, samesite='Lax')
    return response


# ---------------------------------------------------------------------------
# ADMIN ROUTES
# ---------------------------------------------------------------------------

@app.route('/admin')
@admin_required
def admin_index():
    return redirect(url_for('admin_projects'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_projects'))
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == get_admin_password():
            session['admin_logged_in'] = True
            session.permanent = True
            return redirect(url_for('admin_projects'))
        error = 'Mot de passe incorrect.'
    return render_template('admin/login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/admin/projets')
@admin_required
def admin_projects():
    projects = Project.query.order_by(Project.sort_order, Project.created_at.desc()).all()
    return render_template('admin/dashboard.html', projects=projects)


@app.route('/admin/projets/nouveau', methods=['GET', 'POST'])
@admin_required
def admin_new_project():
    if request.method == 'POST':
        title_fr = request.form.get('title_fr', '').strip()
        title_en = request.form.get('title_en', '').strip()
        if not title_fr:
            flash('Le titre en français est obligatoire.', 'error')
            return render_template('admin/project_form.html', project=None)

        slug_base = title_fr
        slug = unique_slug(slug_base)

        project = Project(
            slug=slug,
            title_fr=title_fr,
            title_en=title_en or title_fr,
            description_fr=request.form.get('description_fr', ''),
            description_en=request.form.get('description_en', ''),
            location=request.form.get('location', ''),
            year=request.form.get('year', ''),
            architect=request.form.get('architect', ''),
            client=request.form.get('client', ''),
            phase=request.form.get('phase', ''),
            category=request.form.get('category', ''),
            surface=request.form.get('surface', ''),
            programme=request.form.get('programme', ''),
            image_size=request.form.get('image_size', 'large'),
            sort_order=int(request.form.get('sort_order', 0)),
            published='published' in request.form,
        )
        db.session.add(project)
        db.session.flush()  # get project.id

        # Handle image uploads
        files = request.files.getlist('images')
        for i, file in enumerate(files):
            if file and file.filename and allowed_file(file.filename):
                filename = save_image(file)
                img = ProjectImage(
                    project_id=project.id,
                    filename=filename,
                    caption_fr=request.form.get(f'caption_fr_{i}', ''),
                    caption_en=request.form.get(f'caption_en_{i}', ''),
                    sort_order=i,
                    is_cover=(i == 0),
                )
                db.session.add(img)
                if i == 0:
                    project.featured_image = filename

        db.session.commit()
        flash('Projet créé avec succès !', 'success')
        return redirect(url_for('admin_projects'))

    return render_template('admin/project_form.html', project=None)


@app.route('/admin/projets/<int:project_id>/modifier', methods=['GET', 'POST'])
@admin_required
def admin_edit_project(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        title_fr = request.form.get('title_fr', '').strip()
        title_en = request.form.get('title_en', '').strip()
        if not title_fr:
            flash('Le titre en français est obligatoire.', 'error')
            return render_template('admin/project_form.html', project=project)

        project.title_fr = title_fr
        project.title_en = title_en or title_fr
        project.description_fr = request.form.get('description_fr', '')
        project.description_en = request.form.get('description_en', '')
        project.location = request.form.get('location', '')
        project.year = request.form.get('year', '')
        project.architect = request.form.get('architect', '')
        project.client = request.form.get('client', '')
        project.phase = request.form.get('phase', '')
        project.category = request.form.get('category', '')
        project.surface = request.form.get('surface', '')
        project.programme = request.form.get('programme', '')
        project.image_size = request.form.get('image_size', 'large')
        project.sort_order = int(request.form.get('sort_order', 0))
        project.published = 'published' in request.form
        project.updated_at = datetime.utcnow()

        # Handle new image uploads
        files = request.files.getlist('images')
        current_count = len(project.images)
        for i, file in enumerate(files):
            if file and file.filename and allowed_file(file.filename):
                filename = save_image(file)
                img = ProjectImage(
                    project_id=project.id,
                    filename=filename,
                    sort_order=current_count + i,
                    is_cover=False,
                )
                db.session.add(img)

        # Set featured image to first image if not set
        if not project.featured_image and project.images:
            project.featured_image = project.images[0].filename

        db.session.commit()
        flash('Projet mis à jour !', 'success')
        return redirect(url_for('admin_edit_project', project_id=project.id))

    return render_template('admin/project_form.html', project=project)


@app.route('/admin/projets/<int:project_id>/supprimer', methods=['POST'])
@admin_required
def admin_delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    # Delete image files (Cloudinary ou local)
    for img in project.images:
        delete_image_file(img.filename)
    db.session.delete(project)
    db.session.commit()
    flash('Projet supprimé.', 'success')
    return redirect(url_for('admin_projects'))


# --- Image management via AJAX ---

@app.route('/admin/images/<int:image_id>/supprimer', methods=['POST'])
@admin_required
def admin_delete_image(image_id):
    img = ProjectImage.query.get_or_404(image_id)
    project_id = img.project_id
    delete_image_file(img.filename)
    # If this was the featured image, reset it
    project = Project.query.get(project_id)
    if project and project.featured_image == img.filename:
        project.featured_image = ''
    db.session.delete(img)
    db.session.commit()
    # Set new featured image
    if project:
        remaining = ProjectImage.query.filter_by(project_id=project_id).order_by(ProjectImage.sort_order).first()
        if remaining:
            project.featured_image = remaining.filename
            db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/images/reorder', methods=['POST'])
@admin_required
def admin_reorder_images():
    data = request.get_json()
    order = data.get('order', [])  # list of image ids in new order
    for i, img_id in enumerate(order):
        img = ProjectImage.query.get(img_id)
        if img:
            img.sort_order = i
            if i == 0:
                project = Project.query.get(img.project_id)
                if project:
                    project.featured_image = img.filename
    db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/images/<int:image_id>/cover', methods=['POST'])
@admin_required
def admin_set_cover(image_id):
    img = ProjectImage.query.get_or_404(image_id)
    project = Project.query.get(img.project_id)
    if project:
        project.featured_image = img.filename
        db.session.commit()
    return jsonify({'success': True})


# --- Project reorder ---

@app.route('/admin/projets/reorder', methods=['POST'])
@admin_required
def admin_reorder_projects():
    data = request.get_json()
    order = data.get('order', [])   # list of project ids in new order
    for i, project_id in enumerate(order):
        p = Project.query.get(project_id)
        if p:
            p.sort_order = i
    db.session.commit()
    return jsonify({'success': True})


# Upload individual image via AJAX (used in edit form)
@app.route('/admin/projets/<int:project_id>/upload', methods=['POST'])
@admin_required
def admin_upload_image(project_id):
    project = Project.query.get_or_404(project_id)
    file = request.files.get('image')
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Fichier non valide'}), 400
    filename = save_image(file)
    count = ProjectImage.query.filter_by(project_id=project_id).count()
    img = ProjectImage(
        project_id=project_id,
        filename=filename,
        sort_order=count,
        is_cover=(count == 0),
    )
    db.session.add(img)
    if count == 0 or not project.featured_image:
        project.featured_image = filename
    db.session.commit()
    return jsonify({
        'success': True,
        'image_id': img.id,
        'filename': filename,
        'url': image_url(filename),
    })


# ---------------------------------------------------------------------------
# Init DB & seed
# ---------------------------------------------------------------------------

def seed_demo_projects():
    """Add some demo projects if the DB is empty."""
    if Project.query.count() > 0:
        return
    demos = [
        dict(
            title_fr="Résidence Sow — Dakar Almadies",
            title_en="Sow Residence — Dakar Almadies",
            description_fr="Une villa contemporaine implantée sur un terrain en pente face à l'Atlantique. Le projet joue sur la superposition de volumes minéraux et la transparence des façades pour créer un dialogue permanent entre intérieur et horizon.",
            description_en="A contemporary villa set on a sloping plot overlooking the Atlantic. The project plays on layered mineral volumes and transparent facades to create a permanent dialogue between interior and horizon.",
            location="Dakar, Almadies, Sénégal",
            year="2024",
            architect="StudioSowa",
            client="Famille Sow",
            phase="Livré",
            category="Résidentiel",
            surface="480 m²",
            image_size="large",
            sort_order=1,
        ),
        dict(
            title_fr="Centre Culturel de Thiès",
            title_en="Thiès Cultural Centre",
            description_fr="Un équipement culturel ambitieux pour la ville de Thiès. La conception s'inspire des techniques constructives vernaculaires sénégalaises — la brique de latérite et les claustras — réinterprétées avec une modernité sobre.",
            description_en="An ambitious cultural facility for the city of Thiès. The design draws on Senegalese vernacular construction techniques — laterite brick and mashrabiyas — reinterpreted with restrained modernity.",
            location="Thiès, Sénégal",
            year="2023",
            architect="StudioSowa",
            client="Ville de Thiès",
            phase="Chantier",
            category="Culturel",
            surface="1 200 m²",
            image_size="large",
            sort_order=2,
        ),
        dict(
            title_fr="École Primaire de Ziguinchor",
            title_en="Ziguinchor Primary School",
            description_fr="Ce projet de 12 classes propose une architecture bioclimatique adaptée au climat casamançais. Les toitures ventilées, les cours ombragées et les matériaux locaux constituent l'ossature d'un bâtiment résilient et joyeux.",
            description_en="This 12-classroom project proposes bioclimatic architecture adapted to the Casamance climate. Ventilated roofs, shaded courtyards and local materials form the backbone of a resilient and joyful building.",
            location="Ziguinchor, Sénégal",
            year="2023",
            architect="StudioSowa",
            client="Ministère de l'Éducation",
            phase="Esquisse",
            category="Éducation",
            surface="960 m²",
            image_size="medium",
            sort_order=3,
        ),
        dict(
            title_fr="Hôtel Boutique — Saint-Louis",
            title_en="Boutique Hotel — Saint-Louis",
            description_fr="Réhabilitation d'un bâtiment colonial classé dans l'île de Saint-Louis du Sénégal. La restauration préserve l'enveloppe historique tout en introduisant un programme hôtelier contemporain de 18 suites.",
            description_en="Rehabilitation of a listed colonial building on the island of Saint-Louis, Senegal. The restoration preserves the historic envelope while introducing a contemporary 18-suite hotel programme.",
            location="Saint-Louis, Sénégal",
            year="2022",
            architect="StudioSowa",
            client="Investisseur privé",
            phase="Livré",
            category="Hôtellerie",
            surface="1 800 m²",
            image_size="medium",
            sort_order=4,
        ),
        dict(
            title_fr="Maison de la Presse — Dakar Plateau",
            title_en="Press House — Dakar Plateau",
            description_fr="Restructuration complète d'un immeuble des années 70 pour accueillir les locaux de la presse nationale. Le projet transforme une façade banale en une peau perforée qui régule lumière et chaleur.",
            description_en="Full restructuring of a 1970s building to house national press offices. The project transforms an unremarkable facade into a perforated skin that regulates light and heat.",
            location="Dakar, Plateau, Sénégal",
            year="2024",
            architect="StudioSowa",
            client="Groupement de presse",
            phase="Permis de construire",
            category="Tertiaire",
            surface="2 400 m²",
            image_size="large",
            sort_order=5,
        ),
    ]
    for d in demos:
        d['slug'] = unique_slug(d['title_fr'])
        p = Project(**d)
        db.session.add(p)
        db.session.flush()  # assign id before next slug check
    db.session.commit()


# ---------------------------------------------------------------------------
# Initialisation base de données
# ---------------------------------------------------------------------------

_db_ready = False

@app.before_request
def ensure_db():
    """
    Crée les tables à la première requête reçue.
    Fonctionne avec gunicorn (plusieurs workers) et SQLite/PostgreSQL.
    """
    global _db_ready
    if not _db_ready:
        try:
            db.create_all()
            seed_demo_projects()
            _db_ready = True
            print("[StudioSowa] Base de données initialisée.")
        except Exception as e:
            print(f"[StudioSowa] Erreur init DB : {e}")


# ---------------------------------------------------------------------------
# Entry point (développement local uniquement)
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

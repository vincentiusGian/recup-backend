# konfigurasi port: 5000 for db, 5001 for backend server

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
import os
from flask_cors import CORS
import cloudinary
import cloudinary.uploader
from datetime import datetime
import midtransclient
import random
import json

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

snap = midtransclient.Snap(
    is_production=False,
    server_key=os.getenv("MIDTRANS_SERVER_KEY"),
    client_key=os.getenv("MIDTRANS_CLIENT_KEY")
)

# ambil variabel env
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

app = Flask(__name__)

CORS(app)

DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "poolclass": NullPool,
    "pool_pre_ping": True
}

db = SQLAlchemy(app)

try:
    with app.app_context():
        db.create_all()
    print("Database connected and tables created successfully.")
except Exception as e:
    print("Database connection failed:", e)


# ⚡ NEW: Table untuk menyimpan detail anggota tim
class TeamMember(db.Model):
    __tablename__ = 'team_member'
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registration.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    photo_url = db.Column(db.String(300))
    surat_keterangan_url = db.Column(db.String(300))
    pakta_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=db.func.now())

# ⚡ NEW: Table untuk official/coach/guru pendamping
class Official(db.Model):
    __tablename__ = 'official'
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registration.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'coach', 'guru_pendamping', 'official'
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    photo_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=db.func.now())

class Registration(db.Model):
    __tablename__ = 'registration'
    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competition.id'), nullable=False)
    name = db.Column(db.String(100))  # Nama Tim
    team_leader = db.Column(db.String(100))  # Nama Ketua Tim
    school = db.Column(db.String(100))
    email = db.Column(db.String(100))
    whatsapp = db.Column(db.String(20))
    
    # ⚡ Hapus field ini karena sekarang per-member
    # surat_keterangan_url = db.Column(db.String(300))
    # pakta_url = db.Column(db.String(300))
    
    created_at = db.Column(db.DateTime, default=db.func.now())
    order_id = db.Column(db.String(100), unique=True)
    payment_status = db.Column(db.String(50), default="pending")
    snap_token = db.Column(db.String(200))
    total_fee = db.Column(db.Integer)
    total_members = db.Column(db.Integer)
    
    # ⚡ Relationships
    team_members = db.relationship('TeamMember', backref='registration', cascade='all, delete-orphan')
    officials = db.relationship('Official', backref='registration', cascade='all, delete-orphan')

class Competition(db.Model):
    __tablename__ = 'competition'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(100), nullable=False)
    img = db.Column(db.String(300), nullable=False)
    recent_quota = db.Column(db.Integer, primary_key=False)
    fee = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"Competition: {self.title}"

    def __init__(self, title, description=None, img=None, recent_quota=None, fee=None):
        self.title = title
        self.description = description
        self.img = img
        self.recent_quota = recent_quota
        self.fee = fee

with app.app_context():
    db.create_all()

def format_competition(competition):
    return {
        "title": competition.title,
        "id": competition.id,
        "description": competition.description,
        "img": competition.img,
        "recent_quota": competition.recent_quota,
        "fee": competition.fee
    }

def format_registration(registrationdata):
    return {
        "competition_id": registrationdata.competition_id,
        "id": registrationdata.id,
        "name": registrationdata.name,
        "team_leader": registrationdata.team_leader,
        "school": registrationdata.school,
        "email": registrationdata.email,
        "whatsapp": registrationdata.whatsapp,
        "order_id": registrationdata.order_id,
        "payment_status": registrationdata.payment_status,
        "snap_token": registrationdata.snap_token,
        "total_fee": registrationdata.total_fee,
        "total_members": registrationdata.total_members,
        "team_members": [
            {
                "name": member.name,
                "phone": member.phone,
                "photo_url": member.photo_url,
                "surat_keterangan_url": member.surat_keterangan_url,
                "pakta_url": member.pakta_url
            } for member in registrationdata.team_members
        ],
        "officials": [
            {
                "role": official.role,
                "name": official.name,
                "phone": official.phone,
                "photo_url": official.photo_url
            } for official in registrationdata.officials
        ]
    }


@app.route("/")
def debug():
    return "Hi, this is a debugging text. If you're seeing this, it means that you've connected with the server."

# create competition
@app.route("/competitions", methods=['POST'])
def create_competition():
    data = request.get_json()
    title = data.get('title')
    description = data.get('description', '')
    img = data.get('img', '')
    recent_quota = data.get('recent_quota')
    fee = data.get('fee')

    competition = Competition(title, description, img, recent_quota, fee)
    db.session.add(competition)
    db.session.commit()

    return format_competition(competition)

# ⚡ OPTIMIZED: get competitions dengan caching header
@app.route("/competitions", methods=['GET'])
def get_competitions():
    competitions = Competition.query.order_by(Competition.id.asc()).all()
    competition_list = [format_competition(comp) for comp in competitions]
    
    response = jsonify({'competitions': competition_list})
    response.headers['Cache-Control'] = 'public, max-age=300'  # Cache 5 menit
    return response

# update competitions
@app.route('/competitions/<int:id>', methods=['PUT'])
def update_competition(id):
    competition = Competition.query.get(id)
    if not competition:
        return jsonify({"error": "Competition not found"}), 404

    data = request.get_json()

    competition.title = data.get('title', competition.title)
    competition.description = data.get('description', competition.description)
    competition.img = data.get('img', competition.img)
    competition.recent_quota = data.get('recent_quota', competition.recent_quota)
    competition.fee = data.get('fee', competition.fee)

    db.session.commit()

    return format_competition(competition)


# delete competitions
@app.route('/competitions/<int:id>', methods=['DELETE'])
def delete_competition(id):
    competition = Competition.query.get(id)
    if not competition:
        return jsonify({"error": "Competition not found"}), 404
    
    db.session.delete(competition)
    db.session.commit()
    return jsonify({"message": f"Competition with id: {id} has been deleted."})

@app.route('/registrationdata', methods=["GET"])
def get_registrationdata():
    registrationdata = Registration.query.order_by(Registration.id.asc()).all()
    registrationdata_list = [format_registration(reg) for reg in registrationdata]
    return {'registration_data': registrationdata_list}

# ⚡ NEW: Endpoint untuk upload file secara batch
@app.route('/upload-files', methods=['POST'])
def upload_files():
    try:
        uploaded_files = {}
        
        for key in request.files:
            file = request.files[key]
            folder = "team_photos" if "photo" in key else "documents"
            
            upload_result = cloudinary.uploader.upload(
                file, 
                folder=folder,
                resource_type='auto'
            )
            uploaded_files[key] = upload_result["secure_url"]
        
        return jsonify({"urls": uploaded_files}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/registrationdata', methods=["POST"])
def register():
    try:    
        data = request.form
        competition_id = data.get("competition_id")
        name = data.get("name")  # Nama Tim
        team_leader = data.get("team_leader")  # Nama Ketua Tim
        school = data.get("school")
        email = data.get("email")
        whatsapp = data.get("whatsapp")
        total_fee = data.get("total_fee")
        total_members = data.get("total_members")
        
        # ⚡ VALIDASI: Pastikan total_fee ada
        if not total_fee:
            return jsonify({"error": "Total fee is required"}), 400
        
        try:
            fee = int(total_fee)  # ⚡ PASTI PAKAI total_fee dari frontend
        except ValueError:
            return jsonify({"error": "Invalid total fee format"}), 400
        
        # ⚡ Parse team members data (JSON string)
        team_members_data = json.loads(data.get("team_members", "[]"))
        officials_data = json.loads(data.get("officials", "[]"))

        order_id = f"REG-{random.randint(10000,99999)}"

        # ⚡ Create main registration
        regdata = Registration(
            competition_id=competition_id,
            name=name,
            team_leader=team_leader,
            school=school,
            email=email,
            whatsapp=whatsapp,
            order_id=order_id,
            payment_status="pending",
            total_fee=total_fee,
            total_members=total_members
        )        
        db.session.add(regdata)
        db.session.flush()  # Get the registration ID

        # ⚡ Upload and save team members (including leader)
        for idx, member in enumerate(team_members_data):
            # Check if this is the leader (first member with is_leader=True)
            is_leader = member.get("is_leader", False)
            
            if is_leader:
                # This is the team leader - use leader_ prefix
                photo_file = request.files.get("leader_photo")
                surat_file = request.files.get("leader_surat")
                pakta_file = request.files.get("leader_pakta")
            else:
                # Regular member - calculate correct index (subtract 1 because leader is first)
                member_idx = idx - 1
                photo_file = request.files.get(f"member_{member_idx}_photo")
                surat_file = request.files.get(f"member_{member_idx}_surat")
                pakta_file = request.files.get(f"member_{member_idx}_pakta")
            
            photo_url = None
            surat_url = None
            pakta_url = None
            
            if photo_file:
                photo_upload = cloudinary.uploader.upload(photo_file, folder="team_photos")
                photo_url = photo_upload["secure_url"]
            
            if surat_file:
                surat_upload = cloudinary.uploader.upload(surat_file, folder="surat_keterangan")
                surat_url = surat_upload["secure_url"]
            
            if pakta_file:
                pakta_upload = cloudinary.uploader.upload(pakta_file, folder="pakta")
                pakta_url = pakta_upload["secure_url"]
            
            team_member = TeamMember(
                registration_id=regdata.id,
                name=member.get("name"),
                phone=member.get("phone"),
                photo_url=photo_url,
                surat_keterangan_url=surat_url,
                pakta_url=pakta_url
            )
            db.session.add(team_member)
        
        # ⚡ Upload and save officials
        for idx, official in enumerate(officials_data):
            photo_file = request.files.get(f"official_{idx}_photo")
            
            photo_url = None
            if photo_file:
                photo_upload = cloudinary.uploader.upload(photo_file, folder="official_photos")
                photo_url = photo_upload["secure_url"]
            
            official_record = Official(
                registration_id=regdata.id,
                role=official.get("role"),
                name=official.get("name"),
                phone=official.get("phone"),
                photo_url=photo_url
            )
            db.session.add(official_record)

        db.session.commit()

        # ⚡ Create Midtrans transaction
        competition = Competition.query.get(competition_id)
        
        # ⚡ DEBUG logging
        print(f"FEE DEBUG: Frontend total_fee={total_fee}, DB competition.fee={competition.fee}, Final fee={fee}")

        transaction_params = {
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": fee,  # ⚡ Ini sekarang PASTI pakai calculated fee dari frontend
            },
            "customer_details": {
                "first_name": name,
                "email": email,
                "phone": whatsapp,
            },
            "item_details": [
                {
                    "id": f"COMP-{competition_id}",
                    "price": fee,
                    "quantity": 1,
                    "name": f"{competition.title} ({total_members} members)" if total_members else competition.title
                }
            ]
        }

        snap_token = snap.create_transaction(transaction_params)["token"]
        regdata.snap_token = snap_token
        db.session.commit()

        return jsonify({
            "message": "Berhasil mendaftar!",
            "id": regdata.id,
            "snap_token": snap_token,
            "order_id": order_id,
            "total_fee": fee,
            "total_members": total_members
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error during registration: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ⚡ NEW: Webhook untuk update payment status dari Midtrans
@app.route('/payment-notification', methods=['POST'])
def payment_notification():
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        transaction_status = data.get('transaction_status')
        fraud_status = data.get('fraud_status')
        
        regdata = Registration.query.filter_by(order_id=order_id).first()
        
        if not regdata:
            return jsonify({"error": "Registration not found"}), 404
        
        if transaction_status == 'capture':
            if fraud_status == 'accept':
                regdata.payment_status = 'paid'
        elif transaction_status == 'settlement':
            regdata.payment_status = 'paid'
        elif transaction_status in ['cancel', 'deny', 'expire']:
            regdata.payment_status = 'failed'
        elif transaction_status == 'pending':
            regdata.payment_status = 'pending'
        
        db.session.commit()
        
        return jsonify({"message": "Payment status updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5001)
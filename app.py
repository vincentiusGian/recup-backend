# konfigurasi port: 5000 for db, 5001 for backend server

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:recisbogor123@localhost:5000/recup'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

try:
    with app.app_context():
        db.create_all()
    print("Database connected and tables created successfully.")
except Exception as e:
    print("Database connection failed:", e)


class Competition(db.Model):
    __tablename__ = 'competition'
    id=db.Column(db.Integer, primary_key=True)
    title=db.Column(db.String(100), nullable=False)
    description=db.Column(db.String(100), nullable=False)
    img=db.Column(db.String(300), nullable=False)
    recent_quota=db.Column(db.Integer, primary_key=False)

    def __repr__(self):
        return f"Competition: {self.title}"

    def __init__(self, title,description=None, img=None, recent_quota=None):
        self.title=title
        self.description=description
        self.img=img
        self.recent_quota=recent_quota

with app.app_context():
    db.create_all()

def format_competition(competition):
    return {
        "title": competition.title,
        "id": competition.id,
        "description": competition.description,
        "img":competition.img,
        "recent_quota":competition.recent_quota
    }


@app.route("/")
def debug():
    return "Hi, this is a debugging text. If you're seeing this, it means that you've connected with the server."

# create competition
@app.route("/competitions", methods=['POST'])
def create_competition():
    data = request.get_json()
    title=data.get('title')
    description=data.get('description','')
    img=data.get('img','')
    recent_quota=data.get('recent_quota')

    competition=Competition(title, description, img, recent_quota)
    db.session.add(competition)
    db.session.commit()

    return format_competition(competition)

# get competitions
@app.route("/competitions", methods=['GET'])
def get_competitions():
    competitions=Competition.query.order_by(Competition.id.asc()).all()
    competition_list = []   
    for competition in competitions:
        competition_list.append(format_competition(competition))
    return {'competitions': competition_list}

# update competitions
@app.route('/competitions/<int:id>', methods=['PUT'])
def update_competition(id):
    competition = Competition.query.get(id)
    if not competition:
        return 404

    data = request.get_json()

    competition.title = data.get('title', competition.title)
    competition.description = data.get('description', competition.description)
    competition.img = data.get('img', competition.img)
    competition.recent_quota = data.get('recent_quota', competition.recent_quota)

    db.session.commit()

    return format_competition(competition)


# delete competitions
@app.route('/competitions/<int:id>', methods=['DELETE'])
def delete_competition(id):
    competition = Competition.query.get(id)
    db.session.delete(competition)
    db.session.commit()
    return f"Competition with id: {id} has been deleted."

if __name__ == "__main__":
    app.run(debug=True, port=5001)

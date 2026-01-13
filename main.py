# app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped , mapped_column, relationship
from sqlalchemy import Integer, String
from flask_login import LoginManager , login_user, logout_user, current_user, login_required, UserMixin
import os
import spacy   # your existing module
import requests
from requests.structures import CaseInsensitiveDict
from datetime import date

app = Flask(__name__)
app.config['SECRET_KEY']='your_secret_key_here'
app.config["SQLALCHEMY_DATABASE_URI"]='sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db=SQLAlchemy(app)
login_manager=LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
   
    return User.query.get(int(user_id))

class User(UserMixin,db.Model):
    __tablename__='users'
    id : Mapped[int]=mapped_column(Integer, primary_key=True)
    fullname : Mapped[str] = mapped_column(String, nullable=False)
    contact: Mapped[str] = mapped_column(String, nullable=False)
    email:Mapped[str] = mapped_column(String, nullable=False)
    address:Mapped[str] = mapped_column(String, nullable=True)
    contact1name:Mapped[str] = mapped_column(String, nullable=True)
    contact1phone:Mapped[str] = mapped_column(String, nullable=True)
    contact2name:Mapped[str] = mapped_column(String, nullable=True)
    contact2phone:Mapped[str] = mapped_column(String, nullable=True)

class Sos(UserMixin, db.Model):
    __tablename__="sos_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fullname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=False)
    emergency_type: Mapped[str] = mapped_column(String(50), nullable=False)
    add_detail: Mapped[str | None] = mapped_column(String(300), nullable=True)
    evidence_path: Mapped[str | None] = mapped_column(String(300), nullable=True, comment="Saved file path")
    date = db.Column(db.Date, nullable=False)


volunteers_skill = db.Table(
    'volunteers_skill',
    db.Column('volunteer_id', db.Integer, db.ForeignKey('volunteers.id'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skill.id'), primary_key=True)
)

class Volunteer(UserMixin, db.Model):
    __tablename__ = 'volunteers'

    id: Mapped[int] = mapped_column(primary_key=True)
    fname: Mapped[str] = mapped_column(String, nullable=False)
    lname: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    loc = db.Column(db.String(15),nullable=False)
    date = db.Column(db.Date, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)

    skills: Mapped[list["Skill"]] = db.relationship(
        secondary=volunteers_skill,
        back_populates="volunteers"
    )


class Skill(db.Model):
    __tablename__ = 'skill'

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    volunteers: Mapped[list["Volunteer"]] = db.relationship(
        secondary=volunteers_skill,
        back_populates="skills"
    )


with app.app_context():
    db.create_all()

# with app.app_context():
#     to_be_added=['First Aid','Search & Rescue', 'Translation', 'CPR Certified', 'EMT-B']
#     for entry in to_be_added:
#         new_skill=Skill(skill_name=entry)
#         db.session.add(new_skill)
#         db.session.commit()


@app.route('/')
def home():
    return render_template('index.html')

@app.route("/signin", methods=["GET","POST"])
def signin():
    if request.method == 'POST':
        fullname=request.form.get("yourname")
        contact=request.form.get("contact")
        email=request.form.get("email")
        address=request.form.get("address")
        contact1name=request.form.get("contact1-name")
        contact1phone=request.form.get("contact1-phone")
        contact2name=request.form.get("contact2-name")
        contact2phone=request.form.get("contact2-phone")

        user=db.session.execute(db.select(User).where(User.email==email)).scalar()
        if user:
            return render_template('index.html')

        new_user=User(
            fullname = fullname,
            contact=contact,
            email=email,
            address=address,
            contact1name=contact1name,
            contact1phone=contact1phone,
            contact2name=contact2name,
            contact2phone=contact2phone,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return render_template('index.html')

    return render_template("signin.html")    

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/sos', methods=['GET', 'POST'])
def sos():
    if request.method == 'POST':
        fullname = request.form.get("fullname")
        location = request.form.get("location")
        emergency_type = request.form.get("emergency_type")
        add_detail = request.form.get("add_detail")

        file = request.files.get('evidence')

        UPLOAD_FOLDER = "static/assets/img"
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        todayis = date.today()

        evidence_path = None
        if file and file.filename != "":
            from werkzeug.utils import secure_filename
            filename = secure_filename(file.filename)
            evidence_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(evidence_path)

        # Save to database
        report = Sos(
            fullname=fullname,
            location=location,
            emergency_type=emergency_type,
            add_detail=add_detail,
            evidence_path=evidence_path,
            date=todayis
        )

        db.session.add(report)
        db.session.commit()

        return render_template('index.html')

    return render_template('sos.html')


@app.route('/redirectmap')
def redirectmap():
    return render_template('map.html')

@app.route("/process-text", methods=["POST"])
def process_text_endpoint():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"ok": False, "error": "Missing 'text'"}), 400

    result = spacy.process_text(data["text"])
    return jsonify({"ok": True, "result": result})


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400

    file = request.files["file"]
    contents = file.read()

    # If your spaCy function expects bytes, pass bytes.
    # If it needs string, decode like: contents.decode("utf-8")
    result = spacy.process_bytes(contents)

    return jsonify({"ok": True, "result": result})

@app.route('/volunteer_signup',methods=["POST","GET"])
def volunteer_signup():
    if request.method=="POST":
        fname=request.form.get('fname')
        lname=request.form.get('lname')
        email=request.form.get('email')
        loc=request.form.get('loc')
        password=request.form.get('password')
        cpassword=request.form.get('cpassword')
        todayis = date.today()
        user = db.session.execute(db.select(Volunteer).where(Volunteer.email==email)).scalar()
        if password!=cpassword:
            return redirect(url_for('volunteer_signup'))
        
        elif user!=None:
            return redirect(url_for('volunteer_login'))

        else:
            newv=Volunteer(fname=fname,
                            lname=lname,
                            email=email,
                            loc=loc,
                            password=password,
                            date=todayis)
            db.session.add(newv)
            db.session.commit()
            login_user(newv)
            return redirect(url_for('volunteer'))
        
    return render_template('signup.html')

@app.route('/volunteer_login',methods=["GET","POST"])
def volunteer_login():
    if request.method=='POST':
        email=request.form.get('email')
        password=request.form.get('password')
        remember=request.form.get('remember')
        
        result = db.session.execute(db.select(Volunteer).where(Volunteer.email==email)).scalar()
        if result and result.password==password:
            return redirect(url_for('volunteer'))          
    return render_template('login.html')

@app.route('/volunteer')
def volunteer():
    vol_info=db.session.execute(db.select(Volunteer).order_by(Volunteer.id)).scalars().all()
    sos_info=db.session.execute(db.select(Sos).order_by(Sos.id)).scalars().all()
    
    for y in sos_info:
        coords=y.location
        lat, lon = [float(x.strip()) for x in coords.split(",")]
        url = f"https://nominatim.openstreetmap.org/reverse"
        parameters = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 18,
            "addressdetails": 1
        }
        headers = {
            "User-Agent": "CrisisMitra/1.0 (contact: himanshu746h@gmail.com)"
        }

        response = requests.get(url, params=parameters,headers=headers, timeout=10)

        
        data=response.json()
        area_name=data['address']['suburb']
    return render_template('volunteer.html',vol_info=vol_info,sos_info=sos_info,area=area_name )

@app.route('/evaluate/<int:volid>', methods=["GET", "POST"])
def certify(volid):
    volid=volid
    
    if request.method =='POST':
        
        responses = [
            request.form.get('first_aid'),
            request.form.get('search'),
            request.form.get('cpr_certified'),
            request.form.get('emtb')
        ]

        listed_skills = [
            'First Aid',
            'Search & Rescue',
            'CPR Certified',
            'EMT-B'
        ]
        

        
        person = db.session.execute(db.select(Volunteer).where(Volunteer.id==volid)).scalar()
        print(person)

        

        for response, skill_name in zip(responses, listed_skills):
            if response == "yes":
                skill = Skill.query.filter_by(skill_name=skill_name).first()

                if skill not in person.skills:
                    person.skills.append(skill)

        db.session.commit()
        return redirect(url_for('volunteer'))

    return render_template('certify.html', volid=volid)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

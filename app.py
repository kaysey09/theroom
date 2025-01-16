import unittest
from flask_testing import TestCase
from flask import Flask, render_template, redirect, url_for, request, flash, session,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from datetime import datetime, timedelta,date
app = Flask(__name__,template_folder='template/')
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///room_booking_system.db'
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
logo_url = 'images/image.png'
graphic_url = 'images/meetings.png'
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)

class UserMDT(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    matriculation_number = db.Column(db.String(20), unique=True, nullable=False)
    faculty = db.Column(db.String(100), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    location = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255), nullable=True)  # Add image_url field
    facilities = db.relationship('Facility', 
                               secondary='room_facility',
                               backref=db.backref('rooms', lazy='dynamic'))
    # Relationship with Booking
    bookings = db.relationship('Booking', backref='room', lazy=True)
class Facility(db.Model):
    __tablename__ = "facilities"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)

class RoomFacility(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), nullable=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_date = db.Column(db.DateTime, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='Upcoming')  # Upcoming, Past, Canceled
    # Create database tables
with app.app_context():
    
    db.create_all()
@app.route('/set_admin/<email>')
def set_admin(email):
    try:
        # Use `text()` to safely execute the raw SQL query
        query = text("UPDATE user SET is_admin = 1 WHERE email = :email")
        db.session.execute(query, {'email': email})  # Execute the query with parameters
        db.session.commit()  # Commit the transaction

        return f"The user with {email} is now an admin."
    except Exception as e:
        db.session.rollback()  # In case of error, rollback any changes
        return str(e)
    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Create the new user
        new_user = User(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', logo_url=logo_url)
@app.route('/login', methods=['GET', 'POST'])
def login():
   

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            # Store user ID in session
            session['user_id'] = user.id
          
            # Redirect admin users to admin dashboard
            if user.is_admin:
                login_user(user)
                flash('Welcome, Admin!', 'success')
                return redirect(url_for('admin_dashboard'))
            # Check if master data exists for the user
            user_mdt = UserMDT.query.filter_by(user_id=user.id).first()
            if not user_mdt:
                # Redirect to page to complete profile
                login_user(user)
                flash('Please complete your profile before proceeding.', 'info')
                return redirect(url_for('user_default_index'))
                        # Check if user is verified
            if not user_mdt.is_verified:
                # Redirect to pending verification page
                login_user(user)
                flash('Your profile is pending verification. Please wait for admin approval.', 'warning')
                return redirect(url_for('user_pending'))

            # Redirect to dashboard if master data exists
            login_user(user)
            
            flash(f"Welcome, {user.email}!", 'success')
            return redirect(url_for('dashboard'))

        flash('Login failed. Check your email and/or password', 'error')

    return render_template('login.html',logo_url=logo_url, graphic_url=graphic_url)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged Out!','error')
    return redirect(url_for('login'))
@app.route('/dashboard')
@login_required
def dashboard():
    
    return redirect(url_for('user_dashboard'))
@app.route('/user')
@login_required
def user_dashboard():
    session_email = session.get('email')
    
    logo_url = 'images/image.png'
    rooms = Room.query.all()
    return render_template('user_dashboard.html', rooms=rooms,logo_url=logo_url, session_email=session_email,)
@app.route('/admin')
@login_required
def admin_dashboard():
  
    rooms = Room.query.all()
    image_record = Room.query.first()  # You can modify this to get specific images
    if image_record:
        image = image_record.image_url
    else:
        image = None 
    return render_template('admin_dashboard.html', rooms=rooms, image = image, logo_url=logo_url)

@app.route('/user_default_index')
@login_required
def user_default_index():
    return render_template('user_default_index.html', logo_url=logo_url)
@app.route("/submit_master_data", methods=["GET", "POST"])
@login_required
def submit_master_data():
    if request.method == "POST":
        user_id = session.get("user_id")
        if not user_id:
            flash("You must be logged in to submit data.", "danger")
            return redirect(url_for("login"))

        full_name = request.form.get("full_name")
        matric_number = request.form.get("matriculation_number")
        faculty = request.form.get("faculty")

        # Insert data into user_mdt
        user_mdt = UserMDT(
            user_id=user_id,
            full_name=full_name,
            matriculation_number=matric_number,
            faculty=faculty,
            is_verified=False,
        )
        db.session.add(user_mdt)
        db.session.commit()
        flash("Master data submitted successfully. Please wait for admin verification.", "success")
        return redirect(url_for("user_pending"))

    return render_template("submit_master_data.html",logo_url=logo_url)
@app.route('/user_pending')
@login_required
def user_pending():
    return render_template('user_pending.html',logo_url= logo_url)
@app.route('/admin/facilities', methods=['GET', 'POST'])
@login_required
def manage_facilities():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Handle new facility addition
    if request.method == 'POST':
        facility_name = request.form.get('facility_name')
        
        # Check if facility already exists
        existing_facility = Facility.query.filter_by(name=facility_name).first()
        if existing_facility:
            flash('This facility already exists.', 'error')
        else:
            new_facility = Facility(name=facility_name)
            db.session.add(new_facility)
            db.session.commit()
            flash('Facility added successfully!', 'success')
    
    # Get all facilities for display
    facilities = Facility.query.all()
    return render_template('facilities.html', facilities=facilities, logo_url=logo_url)

@app.route('/admin/delete_facility/<int:facility_id>')
@login_required
def delete_facility(facility_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    facility = Facility.query.get_or_404(facility_id)
    
    # Check if facility is being used by any rooms
    facility_in_use = RoomFacility.query.filter_by(facility_id=facility_id).first()
    if facility_in_use:
        flash('Cannot delete facility as it is currently assigned to one or more rooms.', 'error')
    else:
        db.session.delete(facility)
        db.session.commit()
        flash('Facility deleted successfully!', 'success')
    
    return redirect(url_for('manage_facilities'))
@app.route('/admin/create_room', methods=['GET', 'POST'])
@login_required
def create_room():
    facilities = Facility.query.all()
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        print("Form Data:", request.form)
        print("Facilities Data:", request.form.getlist('facilities[]'))
        room_name = request.form['room_name']
        capacity = request.form['capacity']
        description = request.form['description']
        location = request.form['location']
        image_url = request.form['image_url']
        new_room = Room(room_name=room_name, capacity=capacity, description=description, location=location, image_url=image_url)
        db.session.add(new_room)
        db.session.commit()
        # Handle selected facilities
        facility_ids = request.form.getlist('facilities[]')
        print("Selected facility IDs:", facility_ids)
        for facility_id in set(facility_ids):  # Using set to remove duplicates
            try:
                facility = Facility.query.get(int(facility_id))
                if facility and facility not in new_room.facilities:
                        new_room.facilities.append(facility)
                        print(f"Added facility: {facility.name}")
            except Exception as e:
                print(f"Error adding facility {facility_id}: {str(e)}")
            db.session.commit()
        flash('Room created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('create_room.html', logo_url=logo_url, facilities=facilities)

@app.route('/admin/update_room/<int:room_id>', methods=['GET', 'POST'])
@login_required
def update_room(room_id):
    facilities = Facility.query.all()
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    room = Room.query.get_or_404(room_id)
    session['room_name'] = room.room_name
    if request.method == 'POST':
       try:
            # Update basic room information
            room.room_name = request.form['room_name']
            room.capacity = request.form['capacity']
            room.description = request.form['description']
            room.location = request.form['location']
            room.image_url = request.form['image_url']
            
            # Get selected facilities
            facility_ids = request.form.getlist('facilities[]')
            print("Selected facility IDs:", facility_ids)
            
            # Clear existing facilities
            room.facilities.clear()
            
            # Add new facilities
            for facility_id in set(facility_ids):  # Using set to remove duplicates
                try:
                    facility = Facility.query.get(int(facility_id))
                    if facility:
                        room.facilities.append(facility)
                        print(f"Added facility: {facility.name}")
                except Exception as e:
                    print(f"Error adding facility {facility_id}: {str(e)}")
            
            db.session.commit()
            flash(f'{room.room_name} updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
            
       except Exception as e:
            db.session.rollback()
            print(f"Error updating room: {str(e)}")
            flash(f'Error updating room: {str(e)}', 'error')
            return redirect(url_for('update_room', room_id=room_id))
    
    # Get current facilities for the room
    current_facilities = [f.id for f in room.facilities]
    
    return render_template('update_room.html', 
                         room=room, 
                         facilities=facilities,
                         current_facilities=current_facilities,
                         logo_url=logo_url)
@app.route('/admin/delete_room/<int:room_id>')
@login_required
def delete_room(room_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    flash('Room deleted successfully!','success')
    return redirect(url_for('admin_dashboard'))
@app.route('/admin/verify_users', methods=['GET', 'POST'])
@login_required
def verify_users():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    # Fetch all unverified users with master data
    unverified_users = UserMDT.query.filter_by(is_verified=False).all()

    if request.method == 'POST':
        # Process verification actions
        user_id = request.form.get('user_id')
        action = request.form.get('action')

        if user_id and action:
            user_mdt = UserMDT.query.filter_by(user_id=user_id).first()
            if user_mdt:
                if action == 'confirm':
                    user_mdt.is_verified = True
                    db.session.commit()
                    flash(f'User {user_mdt.full_name} has been verified.', 'success')
                elif action == 'deny':
                    db.session.delete(user_mdt)  # Optional: Remove master data if denied
                    db.session.commit()
                    flash(f'Verification request for {user_mdt.full_name} has been denied.', 'info')
            else:
                flash('Invalid user or action.', 'error')

        return redirect(url_for('verify_users'))

    return render_template('verify_users.html', unverified_users=unverified_users, logo_url=logo_url)

@app.route('/user/view_room/<int:room_id>')
@login_required
def view_room(room_id):
    # Get facilities for this room
    room_facilities = RoomFacility.query.filter_by(room_id=room_id).all()
    facilities = [Facility.query.get(rf.facility_id).name for rf in room_facilities]
    room = Room.query.get_or_404(room_id)
    return render_template('view_room.html', room=room, logo_url=logo_url, facilities=facilities)



@app.route('/user/book_room/<int:room_id>', methods=['GET', 'POST'])
@login_required
def book_room(room_id):
    room = Room.query.get_or_404(room_id)
    user_id = session.get("user_id")
    # Generate available dates for the next 7 days
    available_dates = [(datetime.today() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    # Get the selected date from the query string, or use the first available date as default
    selected_date_str = request.args.get('selected_date', available_dates[0])

    # Find the index of the selected date in available_dates
    selected_index = available_dates.index(selected_date_str)

    # Get all existing bookings for the room, excluding canceled bookings
    bookings = Booking.query.filter_by(room_id=room.id).filter(Booking.status != 'Canceled').all()

    # Generate time slots from 8:00 AM to 6:00 PM (every 30 minutes)
    time_slots = [f'{hour:02}:{minute:02}' for hour in range(8, 19) for minute in (0, 30)]

    # Prepare a dictionary to store booked time slots for each date
    booked_slots = {date: {'start': [], 'end': []} for date in available_dates}
    unavailable_slots = {date: [] for date in available_dates}  # To track unavailable time ranges

    # Check the booked times for each date and calculate unavailable ranges
    for booking in bookings:
        booking_date = booking.booking_date.strftime('%Y-%m-%d')
        if booking_date in booked_slots:
            booked_slots[booking_date]['start'].append(booking.start_time.strftime('%H:%M'))
            booked_slots[booking_date]['end'].append(booking.end_time.strftime('%H:%M'))

            # Add all the intermediate time slots to unavailable slots (disable the entire range)
            start_time = booking.start_time
            end_time = booking.end_time

            # Create a list of all the 30-minute slots between the start and end time
            current_time = start_time
            while current_time < end_time:
                unavailable_slots[booking_date].append(current_time.strftime('%H:%M'))
                current_time = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=30)).time()

    if request.method == 'POST':
        # Get user input from the form
        booking_date = datetime.strptime(request.form['booking_date'], '%Y-%m-%d')
        start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
        end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()

        # Check if the selected time overlaps with an existing booking
        existing_booking = Booking.query.filter_by(
            room_id=room.id,
            booking_date=booking_date,
            status='Upcoming'
        ).filter(
            (Booking.start_time < end_time) & (Booking.end_time > start_time)
        ).first()

        if existing_booking:
            flash("The selected time slot is already booked. Please select a different time.", 'error')
            return redirect(url_for('book_room', room_id=room.id))

        # Ensure the duration is at least 30 minutes
        start_datetime = datetime.combine(booking_date, start_time)
        end_datetime = datetime.combine(booking_date, end_time)

        if (end_datetime - start_datetime) < timedelta(minutes=30):
            flash("The duration of the booking must be at least 30 minutes.", 'error')
            return redirect(url_for('book_room', room_id=room.id))

        # Create a new booking
        new_booking = Booking(
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            room_id=room.id,
            user_id=user_id,
            status='Upcoming'
        )

        db.session.add(new_booking)
        db.session.commit()
        flash("Room successfully booked!", 'success')
        return redirect(url_for('user_dashboard'))

    # Determine which time slots are available based on the bookings for the selected date
    selected_date = available_dates[selected_index]  # Default to the first available date
    booked_start_times = booked_slots[selected_date]['start']
    booked_end_times = booked_slots[selected_date]['end']
    disabled_times = unavailable_slots[selected_date]

    # Check if there's only one available slot left
    available_times = [time for time in time_slots if time not in disabled_times]
    if len(available_times) == 1:
        # Disable the remaining time slot
        disabled_times.append(available_times[0])

    # Calculate valid end times based on the selected start time
    valid_end_times = []
    for time in time_slots:
        # Add the end time if it's at least 30 minutes after the selected start time and not in the unavailable slots
        start_datetime = datetime.strptime(time, '%H:%M')
        end_datetime = (start_datetime + timedelta(minutes=30)).strftime('%H:%M')
        
        if end_datetime not in disabled_times:
            valid_end_times.append(end_datetime)

    # If the request is an AJAX call, return the necessary data as JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'disabled_times': disabled_times,
            'valid_end_times': valid_end_times
        })
    facilities = [facility.name for facility in room.facilities]
    facilities_text = ", ".join(facilities) if facilities else "None"
    # Regular response for rendering the template
    return render_template(
        'book_room.html',
        room=room,
        available_dates=available_dates,
        time_slots=time_slots,
        booked_start_times=booked_start_times,
        booked_end_times=booked_end_times,
        disabled_times=disabled_times,  
        valid_end_times=valid_end_times,  
        selected_date=selected_date,  
        facilities_text=facilities_text,
        logo_url=logo_url
    )

@app.route('/user/booking_history')
@login_required
def booking_history():
    user_id = session.get("user_id")
    today = date.today()
    current_time = datetime.now().time()
    
    # Get all bookings for the user
    bookings = Booking.query.filter_by(user_id=user_id).all()
    
    # Separate bookings into upcoming and history
    upcoming_bookings = []
    history_bookings = []
    
    for booking in bookings:
        # Convert booking date to date object for comparison
        booking_date = booking.booking_date.date()
        
        # Check if booking is in the past or canceled
        is_past = (booking_date < today or 
                  (booking_date == today and booking.end_time < current_time))
        
        # Add to appropriate list
        if booking.status == 'Upcoming' and not is_past:
            upcoming_bookings.append(booking)
        else:
            # If it's past the current date/time, update status to 'Past'
            if is_past and booking.status == 'Upcoming':
                booking.status = 'Past'
                db.session.commit()
            history_bookings.append(booking)
    
    return render_template(
        'booking_history.html',
        upcoming_bookings=upcoming_bookings,
        history_bookings=history_bookings,
        logo_url=logo_url
    )
@app.route('/user/cancel_booking/<int:booking_id>')
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure the booking belongs to the current user
    if booking.user_id != session.get("user_id"):
        flash("You don't have permission to cancel this booking.", 'error')
        return redirect(url_for('booking_history'))
    
    # Only allow canceling upcoming bookings
    if booking.status == 'Upcoming':
        booking.status = 'Canceled'
        db.session.commit()
        flash('Booking has been canceled successfully.', 'success')
    else:
        flash('This booking cannot be canceled.', 'error')
    
    return redirect(url_for('booking_history'))

if __name__ == '__main__':
    app.run(debug=True, port=8081)


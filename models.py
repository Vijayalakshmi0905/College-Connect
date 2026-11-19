"""
College Connect - Database Models
Defines relational models for MySQL:
- User (Flask-Login UserMixin)
- Student
- Staff
- FoodItem
- Order
- OrderItem
- Payment
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='STUDENT', index=True)  # 'STUDENT', 'STAFF', 'ADMIN'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    student_profile = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    staff_profile = db.relationship('Staff', backref='user', uselist=False, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_student(self):
        return self.role == 'STUDENT'

    def is_staff(self):
        return self.role == 'STAFF'

    def is_admin(self):
        return self.role == 'ADMIN'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%d %b %Y, %I:%M %p') if self.created_at else ''
        }


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g. CS2026-084
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    department = db.Column(db.String(100), nullable=True, default='Computer Science')
    year_of_study = db.Column(db.String(20), nullable=True, default='3rd Year')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='student_profile', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'student_id': self.student_id,
            'full_name': self.full_name,
            'phone': self.phone,
            'department': self.department,
            'year_of_study': self.year_of_study
        }


class Staff(db.Model):
    __tablename__ = 'staff'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    staff_id = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g. STF-001
    full_name = db.Column(db.String(100), nullable=False)
    role_title = db.Column(db.String(100), nullable=False, default='Canteen Staff')  # e.g. Kitchen Head
    phone = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'staff_id': self.staff_id,
            'full_name': self.full_name,
            'role_title': self.role_title,
            'phone': self.phone
        }


class FoodItem(db.Model):
    __tablename__ = 'food_items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)  # Breakfast, Lunch, Snacks, Beverages
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(500), nullable=True)
    available = db.Column(db.Boolean, default=True, nullable=False)
    is_veg = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price': self.price,
            'description': self.description,
            'image': self.image,
            'available': self.available,
            'is_veg': self.is_veg
        }


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), unique=True, nullable=False, index=True)  # e.g. CC-59218
    token_number = db.Column(db.String(20), nullable=False, index=True)  # e.g. T-048
    status = db.Column(db.String(30), nullable=False, default='CONFIRMED', index=True)
    student_name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    pickup_slot = db.Column(db.String(100), nullable=False)
    payment_method = db.Column(db.String(50), default='Pay at Canteen Counter / UPI')
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    item_count = db.Column(db.Integer, nullable=False, default=0)

    # Optional association to registered user and student profile
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    student_profile_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='SET NULL'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan', lazy=True)
    payment = db.relationship('Payment', backref='order', uselist=False, cascade='all, delete-orphan')

    def to_dict(self):
        item_list = [item.to_dict() for item in self.items]
        return {
            'order_id': self.order_id,
            'token_number': self.token_number,
            'status': self.status,
            'student_name': self.student_name,
            'student_id': self.student_id,
            'phone': self.phone,
            'pickup_slot': self.pickup_slot,
            'payment_method': self.payment_method,
            'subtotal': self.subtotal,
            'total_amount': self.total_amount,
            'total': self.total_amount,
            'item_count': self.item_count,
            'user_id': self.user_id,
            'created_at': self.created_at.strftime('%d %b %Y, %I:%M %p') if self.created_at else '',
            'updated_at': self.updated_at.strftime('%d %b %Y, %I:%M %p') if self.updated_at else '',
            'items': item_list,
            'ordered_items': item_list,
            'payment': self.payment.to_dict() if self.payment else None
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_items.id', ondelete='SET NULL'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    image = db.Column(db.String(500), nullable=True)

    def to_dict(self):
        return {
            'id': self.food_item_id or self.id,
            'food_item_id': self.food_item_id,
            'name': self.name,
            'category': self.category,
            'price': self.price,
            'quantity': self.quantity,
            'image': self.image
        }


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, unique=True)
    payment_id = db.Column(db.String(50), unique=True, nullable=False, index=True)  # e.g. PAY-CC-59218
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), default='Pay at Counter (UPI / Cash)')
    payment_status = db.Column(db.String(30), default='PENDING', nullable=False)  # 'PENDING', 'COMPLETED', 'FAILED'
    transaction_ref = db.Column(db.String(100), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'payment_id': self.payment_id,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'transaction_ref': self.transaction_ref,
            'paid_at': self.paid_at.strftime('%d %b %Y, %I:%M %p') if self.paid_at else None
        }

from __future__ import annotations
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy import ForeignKey, Table, Column, String, Integer, select, DateTime, func, Float
from sqlalchemy.exc import IntegrityError
from marshmallow import ValidationError, fields, validate
from typing import List, Optional

#Initialize flask app
app = Flask(__name__) 

# SQLite configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///e_commerce_API.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create Base Class
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
ma = Marshmallow(app)
db.init_app(app)

# Association Table
order_product = Table(
    "order_product",
    Base.metadata,
        #Column names          #Refrences the tables
    Column("order_id", ForeignKey("orders.id"), primary_key=True),
    Column("product_id", ForeignKey("products.id"), primary_key=True)
)  

# User model
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    orders: Mapped[List["Order"]] = relationship(backref="user")

# Define the Order model
class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    
    products: Mapped[List["Product"]] = relationship("Product", secondary=order_product, back_populates="orders")


# Product model
class Product(Base): 
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    
    orders: Mapped[List["Order"]] = relationship("Order", secondary=order_product, back_populates="products")

# Schemas

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True

    name = fields.String(required=True, validate=validate.Length(min=1, max=80))
    address = fields.String(required=True, validate=validate.Length(min=1, max=255))
    email = fields.Email(required=True)


class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        load_instance = True
        include_fk = True

    user_id = fields.Integer(required=True)
    order_date = fields.DateTime(dump_only=True)


class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        load_instance = True

    name = fields.String(required=True, validate=validate.Length(min=1, max=120))
    price = fields.Float(required=True, validate=validate.Range(min=0.01))

    
# Instances of Schemas
user_schema = UserSchema()
users_schema = UserSchema(many=True) #allows for the serialization of a list of User objects
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)


# USER ROUTES

# GET route -- retrieves all users
@app.route('/users', methods=['GET'])
def get_users():
    query = select(User)
    users = db.session.execute(query).scalars().all()
    return users_schema.jsonify(users), 200

# GET route -- retrieves single user by ID
@app.route('/users/<int:id>', methods=['GET']) 
def get_user(id):
    user = db.session.get(User, id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    return user_schema.jsonify(user), 200

# POST route -- to create a user
@app.route('/users', methods=['POST'])
def create_user():
    try:
        user_data = user_schema.load(request.json)
        new_user = User(
            name=user_data['name'],
            address=user_data['address'],
            email=user_data['email']
        )
        db.session.add(new_user)
        db.session.commit()
    except ValidationError as e:
        return jsonify(e.messages), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "User with this name or email already exists"}), 409

    return user_schema.jsonify(new_user), 201
    
# PUT route -- updates user by ID
@app.route('/users/<int:id>', methods=['PUT'])
def update_user(id):
    user = db.session.get(User, id)
    
    if not user:
        return jsonify({"message": "Invalid user id"}), 404
    try: 
        user_data = user_schema.load(request.json, partial=True)  # validates input only
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    if 'name' in user_data:
        user.name = user_data['name']
    if 'address' in user_data:
        user.address = user_data['address']
    if 'email' in user_data: 
        user.email = user_data['email']
    
    db.session.commit()
    return user_schema.jsonify(user), 200
    
# DELETE route -- delets user by ID  
@app.route('/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = db.session.get(User, id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"Successfully deleted user {id}"}), 200 

# PRODUCT ROUTES

# GET route -- retrieves all products
@app.route('/products', methods=['GET'])
def get_products():
    query = select(Product)
    products = db.session.execute(query).scalars().all()
    return products_schema.jsonify(products), 200

# GET route -- retrieves single product by ID
@app.route('/products/<int:id>', methods=['GET']) 
def get_product(id):
    product = db.session.get(Product, id)

    if not product:
        return jsonify({"message": "Product not found"}), 404

    return product_schema.jsonify(product), 200

# POST route -- to create a product
@app.route('/products', methods=['POST'])
def create_product():
    try:
        product_data = product_schema.load(request.json)
        new_product = Product(
            name=product_data['name'],
            price=product_data['price'],
        )
        db.session.add(new_product)
        db.session.commit()
    except ValidationError as e:
        return jsonify(e.messages), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "Product with this name already exists"}), 409

    return product_schema.jsonify(new_product), 201

# PUT route -- updates product by ID
@app.route('/products/<int:id>', methods=['PUT'])
def update_product(id):
    product = db.session.get(Product, id)
    
    if not product:
        return jsonify({"message": "Invalid product id"}), 404
    try: 
        product_data = product_schema.load(request.json, partial=True)  # validates input only
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    if 'name' in product_data:
        product.name = product_data['name']
    if 'price' in product_data:
        product.price = product_data['price']
    
    db.session.commit()
    return product_schema.jsonify(product), 200

# DELETE route -- delets product by ID  
@app.route('/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = db.session.get(Product, id)

    if not product:
        return jsonify({"message": "Product not found"}), 404

    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": f"Successfully deleted product {id}"}), 200 




if __name__ == '__main__':
    
    with app.app_context():
        # db.drop_all()
        db.create_all()
        
    app.run(debug=True) #Server updates itself 
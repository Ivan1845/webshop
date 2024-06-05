from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from cloudipsp import Api, Checkout

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shop.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = 'your_secret_key'
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


#Моделі бази даних
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    isActive = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(200))

    def __repr__(self):
        return self.title


# Функція для завантаження користувача
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Головна сторінка
@app.route('/')
def index():
    items = Item.query.order_by(Item.price).all()
    return render_template('index.html', data=items)


# Про магазин
@app.route('/about')
def about():
    return render_template('about.html')


# Сторінка замовлення товару
@app.route('/order/<int:id>', methods=['GET', 'POST'])
def order(id):
    item = Item.query.get_or_404(id)
    return render_template('order.html', item=item)


# Купівля товару
@app.route('/buy/<int:id>', methods=['POST'])
def item_buy(id):
    item = Item.query.get_or_404(id)
    quantity = int(request.form['quantity'])
    total_price = item.price * quantity

    api = Api(merchant_id=1396424, secret_key='test')
    checkout = Checkout(api=api)
    data = {
        "currency": "UAH",
        "amount": total_price * 100,
    }
    url = checkout.url(data).get('checkout_url')
    return redirect(url)


# Створення нового товару
@app.route('/create', methods=['POST', 'GET'])
@login_required
def create():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    if request.method == "POST":
        title = request.form['title']
        price = request.form['price']
        image_url = request.form['image_url']

        item = Item(title=title, price=price, image_url=image_url)
        try:
            db.session.add(item)
            db.session.commit()
            return redirect('/create')
        except Exception as e:
            return f"Помилка при додаванні товару: {str(e)}"
    else:
        items = Item.query.order_by(Item.price).all()
        return render_template('create.html', items=items)


# Авторизація користувача
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Ви успішно увійшли!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неправильне ім\'я користувача або пароль!', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')


# Вихід користувача
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# Реєстрація нового користувача
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Це ім\'я користувача вже зайняте!', 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)  # Автоматичний вхід користувача
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Помилка при реєстрації: {str(e)}", 'error')
            return redirect(url_for('register'))

    return render_template('register.html')


# Оновлення інформації про товар
@app.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    item = Item.query.get_or_404(id)
    if request.method == "POST":
        title = request.form['title']
        price = request.form['price']
        image_url = request.form['image_url']

        item.title = title
        item.price = price
        item.image_url = image_url

        try:
            db.session.commit()
            return redirect('/create')
        except Exception as e:
            return f"Помилка при оновленні товару: {str(e)}"
    else:
        return render_template('update.html', item=item)


# Видалення товару
@app.route('/delete/<int:id>')
@login_required
def delete(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    item = Item.query.get_or_404(id)

    try:
        db.session.delete(item)
        db.session.commit()
        return redirect('/create')
    except Exception as e:
        return f"Помилка при видаленні товару: {str(e)}"


# Управління користувачами
@app.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'admin':
        return redirect(url_for('index'))

    users = User.query.all()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
        return redirect(url_for('manage_users'))

    return render_template('manage_users.html', users=users)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', password=generate_password_hash('adminpassword'), role='admin')
            db.session.add(admin_user)
            db.session.commit()
    app.run(debug=False)

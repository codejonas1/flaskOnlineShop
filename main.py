import os
from flask import Flask, render_template, request, redirect, session, flash
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import formClasses

UPLOAD_FOLDER = './static/graphics/products/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'sklep'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'randomString'

mysql = MySQL(app)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def homePage():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM produkty")
    products = cur.fetchall()
    cur.close()
    return render_template("index.html", products=products)


@app.route("/signIn")
def signIn():
    return render_template('signIn.html')


@app.route("/login", methods=['POST'])
def login():
    userName = request.form['name']
    password = request.form['password']

    conn = mysql.connection.cursor()
    conn.execute(
        'SELECT id FROM klienci WHERE imie="{}" AND haslo=PASSWORD("{}")'
        .format(userName, password))
    userId = conn.fetchone()
    conn.close()

    if userId is not None:
        session['userId'] = userId[0]
        return redirect('/profile')

    return redirect('/signIn')


@app.route("/profile")
def profile():
    if 'userId' in session:
        conn = mysql.connection.cursor()
        conn.execute("SELECT imie, nazwisko FROM klienci WHERE id={}"
                     .format(session['userId']))
        user = conn.fetchone()

        conn.execute('''SELECT z.ID, produkty.Nazwa, z.Data, z.Kod_Pocztowy, z.Miasto, z.Adres, z.Liczba, z.Cena, z.Status
                     FROM zamowienia z INNER JOIN produkty ON z.ProduktyID=produkty.ID
                     WHERE z.KlienciID={} ORDER BY z.Data DESC'''.format(session['userId']))
        orders = conn.fetchall()
        conn.close()

        return render_template("profile.html", user=user, orders=orders)

    return redirect('signIn')


@app.route("/profile/adminPanel")
def adminPanel():
    if 'userId' in session and session['userId'] == 1:
        conn = mysql.connection.cursor()

        conn.execute("SELECT * FROM produkty")
        products = conn.fetchall()

        conn.execute('''SELECT z.ID, klienci.imie, klienci.nazwisko, z.kod_pocztowy, z.miasto,
                        z.adres, produkty.Nazwa, z.Data, z.Liczba, z.Cena, z.Status
                        FROM zamowienia z INNER JOIN produkty ON z.ProduktyID=produkty.ID
                        INNER JOIN klienci ON z.klienciID=klienci.ID ORDER BY z.Data DESC''')
        orders = conn.fetchall()

        conn.close()

        return render_template('adminPanel.html', products=products, orders=orders)

    return redirect('/profile')


@app.route("/profile/adminPanel", methods=['POST'])
def addProduct():
    if request.method == 'POST' and session['userId'] == 1:
        productName = request.form['name']
        description = request.form['description']
        price = request.form['price']
        number = request.form['number']

        if 'image' not in request.files:
            return 'Brak pliku'

        image = request.files['image']

        if image.filename == '':
            return 'Nie wybrano pliku'
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = mysql.connection.cursor()
        conn.execute('''INSERT INTO produkty(nazwa, opis, cena, liczba, zdjecie)
                     VALUES("{}", "{}", {}, {}, "{}")'''
                     .format(productName, description, price, number, filename))
        mysql.connection.commit()
        conn.close()

        return redirect('/profile/adminPanel')

    return redirect('/profile')


@app.route("/profile/adminPanel/<int:productId>", methods=['POST'])
def changeData(productId):
    if 'userId' in session and session['userId'] == 1:
        if request.method == 'POST':
            status = request.form['status']
            cur = mysql.connection.cursor()
            cur.execute('UPDATE zamowienia SET status = "{}" WHERE id = {}'.format(status, productId))
            mysql.connection.commit()
            cur.close()

        return redirect('/profile/adminPanel')

    return redirect('/signIn')


@app.route("/profile/adminPanel/<int:productId>/update", methods=['GET', 'POST'])
def updateProduct(productId):
    if 'userId' in session and session['userId'] == 1:
        if request.method == 'GET':
            conn = mysql.connection.cursor()
            conn.execute('SELECT * FROM produkty WHERE id={}'.format(productId))
            product = conn.fetchone()
            conn.close()

            return render_template("updateProduct.html", product=product)

        if request.method == 'POST':
            productName = request.form['name']
            description = request.form['description']
            price = request.form['price']
            number = request.form['number']

            conn = mysql.connection.cursor()
            conn.execute('''UPDATE produkty SET nazwa="{}", opis="{}", cena={}, liczba={} WHERE id={}'''
                         .format(productName, description, price, number, productId))
            mysql.connection.commit()
            conn.close()

            return redirect('/profile/adminPanel')

    return redirect('/signIn')


@app.route("/logout")
def logout():
    session.pop('userId', None)
    return redirect('/')


@app.route("/<int:id1>/order", methods=['GET', 'POST'])
def order(id1):
    if request.method == "GET":
        conn = mysql.connection.cursor()
        conn.execute("SELECT id, nazwa, opis, cena, liczba, zdjecie FROM produkty WHERE id={}".format(id1))
        product = conn.fetchone()
        conn.close()

        if product is not None:
            return render_template("order.html", product=product)

    if 'userId' in session and request.method == 'POST':
        form = formClasses.OrderForm(request.form)
        if not form.validate():
            flash("Niepoprawne dane", 'error')
            return redirect('/{}/order'.format(id1))

        zip_code = form.zip_code.data
        city = form.city.data
        address = form.address.data
        numOfProduct = request.form['numOfProduct']

        conn = mysql.connection.cursor()
        conn.execute("SELECT liczba FROM produkty WHERE id={}".format(id1))
        num = conn.fetchone()
        conn.close()

        if not form.isZipCode(zip_code) or not form.isCity(city):
            flash("Niepoprawne dane", 'error')
            return redirect('/{}/order'.format(id1))

        if int(num[0]) == 0 or int(numOfProduct) > int(num[0]):
            flash("Brak produktu w magazynie", 'error')
            return redirect('/{}/order'.format(id1))

        conn = mysql.connection.cursor()
        conn.execute('''INSERT INTO zamowienia(KlienciID, ProduktyID, Kod_pocztowy, Miasto, Adres, Liczba) 
                        VALUES({}, {}, "{}", "{}", "{}", {})'''
                        .format(session['userId'], id1, zip_code, city, address, numOfProduct))
        mysql.connection.commit()
        conn.close()
        flash('Zamównie złożono porawnie.', 'success')
        flash('Zamównia możesz śledzić na swoim profilu.', 'info')
        return redirect('/{}/order'.format(id1))

    return redirect('/signIn')


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html")


@app.route('/reply')
def reply():
    return render_template('reply.html')


if __name__ == "__main__":
    app.run(debug=True)

import os, json
from flask import Flask, session, render_template, redirect, url_for, request, jsonify, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
from requests import get
from io import BytesIO
from PIL import Image
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route('/')
#default route to index
def index():
    if "username" in session:
        username = session["username"]
        return render_template("index.html", loggedin = True)
    else:
        return render_template("index.html", loggedin = False)

#route for existing user to login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        #get user input from login form
        username = request.form.get("username")
        password = request.form.get("password")

        #check username and hashed password
        result =  db.execute("SELECT * FROM users WHERE username = :username",{"username":username}).fetchone()

        #if there is no match, produce error
        if result == None:
            return render_template("login.html", error = True, log_out = False)
        elif check_password_hash(result[1], password):
            #login successful, direct to search page
            session["username"] = username
            return redirect(url_for('search'))
        else:
            #if there is a match but password is incorrect
            return render_template("login.html", error = True, log_out = False)
    elif "username" in session:
        username = session["username"]
        return redirect(url_for("search"))
    else:
        #GET request
        return render_template("login.html", error = False, log_out=False)
#route to signup for new users
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get("username")

        #check if username already exists
        if db.execute("SELECT * FROM users WHERE username = :username",{"username":username}).fetchone() != None:
            return render_template("signup.html", new_user = False, error = True)

        #hash password and insert username + password into the database
        hashed_password = generate_password_hash(request.form.get("password"), method='sha256')
        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username": request.form.get("username"), "password": hashed_password})
        db.commit()

        #produce a "Success" message to the user
        return render_template("signup.html", new_user = True, error = False)
    else:
        #GET request
        return render_template("signup.html", new_user = False, error = False)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        #check if the user is already logged in
        if "username" in session:
            username = session["username"]
            return render_template("search.html", error=False)
        else:
            #if user needs to login, redirect them to the login page instead
            return redirect(url_for("login", error =False, log_out=False))
    #If POST and search form is submitted
    else:
        #interpret user input from search submission, determine which field to search based on radio button input
        option = request.form['search_options']
        query = request.form['search']

        if option == "title":
            books = db.execute("SELECT isbn, title, author, year FROM book_list WHERE LOWER(title) LIKE LOWER(:query) LIMIT 15",{"query": "%" + query + "%"})
            if books.rowcount == 0:
                return render_template("search.html", error=True)
            else:
                return render_template("result.html", books=books, func = imageCheck, option = option, query=query, next_page = 2)
        elif option == "author":
            books = db.execute("SELECT isbn, title, author, year FROM book_list WHERE LOWER(author) LIKE LOWER(:query) LIMIT 15",{"query": "%" + query + "%"})
            if books.rowcount == 0:
                return render_template("search.html", error=True)
            else:
                return render_template("result.html", books=books, func = imageCheck, option = option, query=query, next_page = 2)
        elif option == "year":
            books = db.execute("SELECT isbn, title, author, year FROM book_list WHERE year LIKE :query LIMIT 15",{"query":query})
            if books.rowcount == 0:
                return render_template("search.html", error=True)
            else:
                return render_template("result.html", books=books, func = imageCheck, option = option, query=query, next_page = 2)
        else:
            books = db.execute("SELECT isbn, title, author, year FROM book_list WHERE LOWER(isbn) LIKE LOWER(:query) LIMIT 15",{"query": "%" + query + "%"})
            if books.rowcount == 0:
                return render_template("search.html", error=True)
            else:
                return render_template("result.html", books=books, func = imageCheck, option = option, query=query, next_page = 2)

@app.route('/search/<string:field>/<string:query>/<int:page_id>', methods=['GET'])
def searchPage(page_id, field, query):
    offset = 15 * (page_id-1)
    if field == "title":
        books = db.execute("SELECT isbn, title, author, year FROM book_list WHERE LOWER(title) LIKE LOWER(:query) OFFSET :offset ROWS FETCH NEXT 15 ROWS ONLY",{"query": "%" + query + "%", "offset": offset})
        if books.rowcount == 0:
            return render_template("searcherror.html", next_page = page_id-1, field=field, query=query)
        else:
            return render_template("result.html", books=books, func = imageCheck, option = field, query=query, next_page= page_id + 1)
    if field == "author":
        books = db.execute("SELECT isbn, title, author, year FROM book_list WHERE LOWER(author) LIKE LOWER(:query) OFFSET :offset ROWS FETCH NEXT 15 ROWS ONLY",{"query": "%" + query + "%", "offset": offset})
        if books.rowcount == 0:
            return render_template("searcherror.html", next_page = page_id-1, field=field, query=query)
        else:
            return render_template("result.html", books=books, func = imageCheck, option = field, query=query, next_page= page_id + 1)
    if field == "year":
        books = db.execute("SELECT isbn, title, author, year FROM book_list WHERE LOWER(year) LIKE LOWER(:query) OFFSET :offset ROWS FETCH NEXT 15 ROWS ONLY",{"query": "%" + query + "%", "offset": offset})
        if books.rowcount == 0:
            return render_template("searcherror.html", next_page = page_id-1, field=field, query=query)
        else:
            return render_template("result.html", books=books, func = imageCheck, option = field, query=query, next_page= page_id + 1)
    if field == "isbn":
        books = db.execute("SELECT isbn, title, author, year FROM book_list WHERE LOWER(isbn) LIKE LOWER(:query) OFFSET :offset ROWS FETCH NEXT 15 ROWS ONLY",{"query": "%" + query + "%", "offset": offset})
        if books.rowcount == 0:
            return render_template("searcherror.html", next_page = page_id-1, field=field, query=query)
        else:
            return render_template("result.html", books=books, func = imageCheck, option = field, query=query, next_page= page_id + 1)

@app.route('/book/<isbn>', methods=['GET', 'POST'])
def bookPage(isbn):
    #extract data for this book from database
    book = db.execute("SELECT * FROM book_list WHERE isbn LIKE LOWER(:isbn)",{"isbn": isbn}).fetchone()

    #extract data from GoodReads API for this book (decomissioned in Dec 2020 and no longer works). Sample data is populated below and is used for every book.

    # res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "r32opLlYxyoAreMsbkeCdg", "isbns": isbn})
    # review_data = res.json()
    # avg_rating = review_data["books"][0]["average_rating"]
    # num_ratings = review_data["books"][0]["work_ratings_count"]
    avg_rating = 4.07
    num_ratings = 49493
    num_stars = round(float(avg_rating))

    #if the user is submitting a review
    if request.method == 'POST':
        #get current user's username
        currentUser = session["username"]

        #check if user has a review already
        validate_review = db.execute("SELECT * FROM user_reviews WHERE username = :username AND book_id = :book_id",
                    {"username": currentUser,
                     "book_id": book.id})

        # A review already exists
        if validate_review.rowcount == 1:
            book_reviews = db.execute("SELECT * FROM user_reviews WHERE book_id = :review_book_id",{"review_book_id": book.id}).fetchall()
            return render_template("book.html", book=book, book_reviews=book_reviews, avg_rating=avg_rating, num_ratings=num_ratings, num_stars=num_stars, num_blank= 5-num_stars, error=True)

    #if no review exists, update the database
        rating = request.form.get("rating")
        review = request.form.get("review")
        db.execute("INSERT INTO user_reviews (username, rating, review, book_id, book_name, isbn) VALUES (:username, :rating, :review, :book_id, :book_name, :isbn)", {"username": currentUser, "rating": rating, "review": review, "book_id": book.id, "book_name": book.title, "isbn": book.isbn })
        db.commit()
    book_reviews = db.execute("SELECT * FROM user_reviews WHERE book_id = :review_book_id",{"review_book_id": book.id}).fetchall()
    return render_template("book.html", book=book, book_reviews=book_reviews, avg_rating=avg_rating, num_ratings=num_ratings, num_stars=num_stars, num_blank= 5-num_stars, error=False)

#display all reviews written by the current logged in user
@app.route('/myreviews')
def myreviews():
    currentUser = session["username"]
    book_reviews = db.execute("SELECT * FROM user_reviews WHERE username = :currentUser",{"currentUser": currentUser}).fetchall()
    return render_template("myreviews.html", book_reviews=book_reviews)

#return JSON file for API call for given ISBN
@app.route('/api/<isbn>')
def bookAPI(isbn):
    book = db.execute("SELECT title, author, year, book_list.isbn, COUNT(user_reviews.review_id) as reviewCount, AVG(user_reviews.rating) as averageRating FROM book_list INNER JOIN user_reviews on book_list.id = user_reviews.book_id WHERE book_list.isbn = :isbn GROUP BY title, author, year, book_list.isbn", {"isbn": isbn})

    if book.rowcount != 1:
        #return error if no book is return with given ISBN
        return jsonify({"Error": "Invalid ISBN, please try again."}), 422
    else:
        #extract data and convert to dictionary
        row = book.fetchone()
        data = dict(row.items())

        #cast from decimal to float
        data['averagerating'] = float('%.2f'%(data['averagerating']))
        return jsonify(data)

@app.route('/logout')
def logout():
    #remove user data from the session
    session.pop("username", None)
    return redirect(url_for("login", error=False, log_out = True))

#Helper function to evaluate whether the Open Library API returns an image or a blank 1x1 pixel image - returns False to indicate that image not present
def imageCheck(url):
    image_raw = get(url)
    try:
        image = Image.open(BytesIO(image_raw.content))
        width, height = image.size
    except:
        return False
    if width == 1:
        return False
    else:
        return True

if __name__ == '__main__':
    app.run(debug=True)

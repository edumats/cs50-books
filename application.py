import os
import random

from flask import Flask, flash, session, request, redirect, render_template, session, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"),echo=True)
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
@login_required
def index():
    """ Main Page """
    # Creates a random alphabet character, could be from "a" to "z"
    randomChar = chr(random.randint(97, 122))

    # Query database with random alphabet character to get randomized books everytime index runs
    randomBooks = db.execute("SELECT * FROM books WHERE author ILIKE CONCAT(:q, '%') OR title ILIKE CONCAT(:q, '%') LIMIT 9", {"q":randomChar}).fetchall()

    return render_template("index.html", latestBooks=randomBooks)

@app.route("/login", methods=["GET", "POST"])
def login():
    """ Logs user """

    # Forgets user id, if any
    session.clear()

    # Reached via POST method
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Check if username is provided
        if not username:
            return render_template('login.html', error="Please type a username")

        # Check if password is provided
        if not password:
            return render_template('login.html', error="Please provide a password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username":username}).fetchone()

        if rows is not None and check_password_hash(rows.hash, password):
            session["user_id"] = rows.id
            return redirect("/")

        return render_template('login.html', error="Wrong username or password")

    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """ Register user """

    # Forget cached session
    session.clear()

    # Reached via POST method
    if request.method == "POST":

        username = request.form.get("username")

        # Check if username is provided
        if not username:
            return render_template('register.html', error="Please type a username")

        # Check if password is provided
        if not request.form.get("password"):
            return render_template('register.html', error="Please type a password")

        # Check if password matches in confirmation field
        if request.form.get("password") != request.form.get("confirmation"):
            return render_template('register.html', error="Passwords do not match")

        # Check if user exists in database
        user = db.execute('SELECT username FROM users WHERE username=:username', {"username":username}).fetchone()
        if user is not None:
            return render_template('register.html', error="User already exists")

        # Create hash from password
        hash = generate_password_hash(request.form.get("password"))

        # Store new user into database
        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash) RETURNING id",
                            {"username":username, "hash":hash})
        db.commit()

        # Stores id in session
        session["user_id"] = result[0]

        # Redirect user to home page
        return redirect("/")

    # Reached route via GET
    else:
        return render_template("register.html")

@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    if request.method == 'GET':
        username = request.args.get('username')
        # Query database for username
        query = db.execute('SELECT username FROM users WHERE username = :username', {"username":username}).fetchone()

        # If username is lenght > 1 and does not contain in users database, return true; otherwise, false
        if len(username) > 1 and not query:
            return jsonify(True)
        else:
            return jsonify(False)

@app.route("/autocomplete", methods=["GET"])
def autocomplete():
    """ Looks for book information in database """
    # Query from user input
    query = request.args.get("q")

    # Search for matches in database that contain the query
    results = db.execute("SELECT title, author, isbn FROM books WHERE author ILIKE CONCAT('%', :q, '%') OR title ILIKE CONCAT('%', :q, '%') OR isbn ILIKE CONCAT('%', :q, '%') LIMIT 10", {"q":query}).fetchall()
    if not results:
        return render_template('index.html', error="No results")

    data = [dict(result) for result in results]
    return jsonify(data)

@app.route("/search", methods=["GET"])
@login_required
def search():
    """ Looks for book information in database """
    # Query from user input
    query = request.args.get("q")

    # Search for matches in database that contain the query
    results = db.execute("SELECT title, author, isbn FROM books WHERE author ILIKE CONCAT('%', :q, '%') OR title ILIKE CONCAT('%', :q, '%') OR isbn ILIKE CONCAT('%', :q, '%') LIMIT 12", {"q":query}).fetchall()
    if not results:
        flask("No results")
        return redirect(url_for('index', error="No results"))

    return render_template("search.html", results=results)

@app.route("/book/<isbn>", methods=["GET", "POST"])
@login_required
def book(isbn):
    if request.method == 'POST':
        # Check if review is not empty
        # Needs to check if jsonify responses are being received
        review = request.form.get("review")
        if not review:
            print("No review")
            return jsonify(False)

        # Check if rating is not empty
        rating = request.form.get("rating")
        if not rating:
            return jsonify(False)

        # Check if a review from user already exists for book
        reviewExists = db.execute("SELECT id FROM reviews WHERE user_id=:user_id", {"user_id":session["user_id"]}).fetchone()
        if reviewExists:
            return jsonify(False)

        # Insert review into database
        insertReview = db.execute("INSERT INTO reviews (user_id, book_isbn, review, rating) VALUES(:user_id, :book_isbn, :review, :rating)", {"user_id":session["user_id"], "book_isbn":isbn, "review":review, "rating":rating})
        db.commit()
        # Return success message
        return jsonify(True)

    else:
        # Check if a book with the given ISBN exists in database
        book = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone()
        if not book:
            return render_template("index.html", error="No such book")

        # Query Goodreads API for book information
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": os.getenv("KEY"), "isbns": book.isbn})
        resJson = res.json()
        ratingsCount = resJson["books"][0]["work_ratings_count"]
        ratings = resJson["books"][0]["average_rating"]

        getReviews = db.execute("SELECT * FROM reviews WHERE book_isbn=:isbn", {"isbn": isbn}).fetchall()
        if not getReviews:
            # Return book page with book data
            return render_template("book.html", book=book, review=False, ratingsCount=format(ratingsCount, ',d'), ratings=float(ratings))

        return render_template("book.html", book=book, review=True, ratingsCount=format(ratingsCount, ',d'), ratings=float(ratings))

@app.route("/api/<isbn>", methods=["GET"])
def api(isbn):
    # Check if a book with the given ISBN exists in database
    lookForBook = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn": isbn}).fetchone()
    if not lookForBook:
        return jsonify({"error": "Invalid ISBN"}), 422

    # Query Goodreads API for book information
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": os.getenv("KEY"), "isbns": lookForBook.isbn})
    resJson = res.json()
    ratingsCount = resJson["books"][0]["work_ratings_count"]
    ratings = resJson["books"][0]["average_rating"]

    # Return results in JSON format
    return jsonify({
        "title": lookForBook.title,
        "author": lookForBook.author,
        "year": lookForBook.year,
        "isbn": lookForBook.isbn,
        "review_count": ratingsCount,
        "average_score": ratings
    })

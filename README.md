# Project 1

Web Programming with Python and JavaScript

This is a book review website where it is possible to search for books by its author, title or ISBN; write reviews and rate books, as well as use the included API for retrieving information about a particular book. It displays ratings and numbers of reviews of the books by using the Goodreads API.

### Prerequisites

Please install dependecies via the included requirements.txt:

Use pip for that:

```
pip install -r requirements.txt 
````

### API usage

Using the following path it is possible to retrieve data from a particular book using its ISBN:

```
/api/<isbn>
```

If the book is available in database, the API returns the following JSON response:

Example:

```
{
    "title": "Memory",
    "author": "Doug Lloyd",
    "year": 2015,
    "isbn": "1632168146",
    "review_count": 28,
    "average_score": 5.0
}

```

If the provided ISBN is not available, it will return a error JSON response:

```
{"error": "Invalid ISBN"}
```



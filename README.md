# Backend — Future FastAPI Integration

> **This folder is INTENTIONALLY EMPTY.**

This directory is reserved for the future **FastAPI** backend that will power the Sri Manakula Vinayagar Devasthanam website.

## What will go here

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── models/              # SQLAlchemy / Pydantic models
│   │   ├── donation.py
│   │   ├── seva.py
│   │   ├── event.py
│   │   ├── user.py
│   │   └── gallery.py
│   ├── routes/              # API route handlers
│   │   ├── donations.py     # POST /api/donations
│   │   ├── sevas.py         # GET /api/sevas, POST /api/sevas/book
│   │   ├── poojas.py        # GET /api/poojas, POST /api/poojas/book
│   │   ├── events.py        # GET /api/events
│   │   ├── gallery.py       # GET /api/gallery
│   │   ├── blog.py          # GET /api/blog, GET /api/blog/:slug
│   │   ├── contact.py       # POST /api/contact
│   │   ├── newsletter.py    # POST /api/newsletter
│   │   └── auth.py          # POST /api/auth/login, /register
│   ├── services/            # Business logic layer
│   ├── database.py          # DB connection (SQLite → PostgreSQL)
│   └── config.py            # Environment config
├── requirements.txt
└── README.md
```

## Frontend Integration Points

See `src/api/config.js` in the frontend for all the endpoint placeholders that are ready to be connected.

## DO NOT create any files here until the backend is being implemented.

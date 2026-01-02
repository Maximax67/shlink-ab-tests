# Project Structure

Complete file listing for the URL Redirect & A/B Testing application.

## Directory Tree

```text
url-redirect-ab-testing/
│
├── main.py                          # FastAPI application entry point
├── config.py                        # Configuration management (environment variables)
├── database.py                      # Database connection and session management
├── models.py                        # SQLAlchemy ORM models (ShortUrl, Visit, ABTest)
├── schemas.py                       # Pydantic validation models
│
├── routers/
│   ├── __init__.py                  # Router package initialization
│   ├── redirect.py                  # Redirect endpoint with A/B testing logic
│   └── admin.py                     # Admin dashboard and CRUD API
│
├── services/
│   ├── __init__.py                  # Services package initialization
│   ├── redirect_service.py          # Redirect logic, A/B variant selection, visit tracking
│   ├── ab_test_service.py           # A/B test CRUD operations, validation
│   └── auth_service.py              # Admin authentication and session management
│
├── templates/
│   ├── base.html                    # Base template with common layout
│   ├── login.html                   # Admin login page
│   ├── dashboard.html               # Dashboard with short URL list
│   └── short_url_detail.html        # A/B test management for specific URL
│
├── alembic/
│   ├── env.py                       # Alembic environment configuration
│   ├── script.py.mako               # Migration script template (auto-generated)
│   └── versions/
│       └── 001_create_ab_tests.py   # Initial migration to create ab_tests table
│
├── requirements.txt                 # Python dependencies
├── alembic.ini                      # Alembic configuration
├── .env.example                     # Example environment variables
├── .env                             # Actual environment variables (create from .env.example)
│
├── Dockerfile                       # Docker container definition
├── docker-compose.yml               # Docker Compose configuration
├── .dockerignore                    # Files to exclude from Docker build
├── nginx.conf                       # Nginx reverse proxy configuration
│
├── test_app.py                      # Unit tests
├── deploy.sh                        # Deployment script
│
├── README.md                        # Complete documentation
├── QUICKSTART.md                    # Quick start guide
└── PROJECT_STRUCTURE.md             # This file
```

## File Descriptions

### Core Application Files

| File | Purpose | Key Features |
| ------ | --------- | -------------- |
| `main.py` | FastAPI application | - Application setup<br>- Router registration<br>- CORS middleware<br>- Lifespan events |
| `config.py` | Configuration | - Environment variable loading<br>- Settings validation<br>- Cached settings instance |
| `database.py` | Database | - SQLAlchemy engine<br>- Session factory<br>- Dependency injection<br>- Context managers |
| `models.py` | ORM Models | - ShortUrl (read-only)<br>- Visit (read-only)<br>- ABTest (CRUD) |
| `schemas.py` | Validation | - Pydantic models<br>- Request/response validation<br>- Type safety |

### Routers

| File | Endpoints | Purpose |
| ------ | ----------- | --------- |
| `routers/redirect.py` | `GET /{short_code}` | - Resolve short codes<br>- A/B variant selection<br>- Visit recording<br>- Redirect users |
| `routers/admin.py` | `/admin/*` | - Login/logout<br>- Dashboard<br>- A/B test CRUD<br>- Session management |

### Services (Business Logic)

| File | Responsibilities |
| ------ | ------------------ |
| `services/redirect_service.py` | - Short code resolution<br>- A/B variant selection (deterministic IP-based)<br>- Visit creation<br>- Google Forms prefilling<br>- Query parameter forwarding |
| `services/ab_test_service.py` | - A/B test CRUD<br>- Probability validation<br>- Total probability calculation<br>- Test activation/deactivation |
| `services/auth_service.py` | - Admin token verification<br>- Session creation/validation<br>- Session cleanup<br>- In-memory session store |

### Templates (Jinja2)

| File | Purpose | Features |
| ------ | --------- | ---------- |
| `templates/base.html` | Base layout | - Common HTML structure<br>- CSS styles<br>- Navigation<br>- Block definitions |
| `templates/login.html` | Login page | - Token input form<br>- POST to /admin/login<br>- Gradient background |
| `templates/dashboard.html` | URL list | - Paginated table<br>- Search functionality<br>- Probability bars<br>- Quick stats |
| `templates/short_url_detail.html` | Test management | - A/B test list<br>- Create/edit/delete forms<br>- Probability visualization<br>- Inline editing |

### Database Migrations

| File | Purpose |
| ------ | --------- |
| `alembic.ini` | Alembic configuration |
| `alembic/env.py` | Migration environment setup |
| `alembic/versions/001_create_ab_tests.py` | Creates `ab_tests` table with indexes |

### Configuration Files

| File | Purpose |
| ------ | --------- |
| `.env.example` | Example environment variables |
| `.env` | Actual configuration (create from example) |
| `requirements.txt` | Python package dependencies |

### Deployment

| File | Purpose |
| ------ | --------- |
| `Dockerfile` | Container image definition |
| `docker-compose.yml` | Multi-container setup (app + MySQL + Nginx) |
| `.dockerignore` | Files excluded from Docker build |
| `nginx.conf` | Reverse proxy configuration |
| `deploy.sh` | Automated deployment script |

### Testing & Documentation

| File | Purpose |
| ------ | --------- |
| `test_app.py` | Unit tests for key functionality |
| `README.md` | Complete documentation |
| `QUICKSTART.md` | Getting started guide |
| `PROJECT_STRUCTURE.md` | This file |

## Setup Order

Follow these steps to set up the project:

1. **Create directory structure:**

   ```bash
   mkdir -p url-redirect-ab-testing/{routers,services,templates,alembic/versions}
   cd url-redirect-ab-testing
   ```

2. **Create core files:**
   - Copy all `.py` files to root directory
   - Copy `__init__.py` files to respective packages
   - Copy templates to `templates/` directory

3. **Create configuration:**

   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Install dependencies:**

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Initialize database:**

   ```bash
   alembic upgrade head
   ```

6. **Run application:**

   ```bash
   python main.py
   ```

## Key Design Patterns

### Dependency Injection

- Database sessions injected via FastAPI's `Depends()`
- Enables easy testing and session management

### Service Layer

- Business logic separated from routes
- Reusable across different endpoints
- Easier to test independently

### Repository Pattern

- Services encapsulate database operations
- Models remain simple data containers
- Clean separation of concerns

### Template Inheritance

- `base.html` provides common structure
- Child templates extend and customize
- DRY principle applied to UI

## Database Schema

### Existing Tables (Read-Only)

**short_urls:**

- Primary short URL data
- Original URLs, short codes, settings
- Created/managed by Shlink

**visits:**

- Visit tracking data
- IP, user agent, timestamps
- Created by Shlink

### New Table (CRUD Allowed)

**ab_tests:**

- A/B test configurations
- Foreign key to short_urls
- Probability, status, timestamps
- Only table this app modifies

## API Flow

### Redirect Request Flow

```text
1. User visits /{short_code}
   ↓
2. RedirectRouter receives request
   ↓
3. RedirectService.resolve_short_code()
   ↓
4. RedirectService.get_active_ab_tests()
   ↓
5. RedirectService.select_ab_variant()
   ↓
6. RedirectService.build_redirect_url()
   ↓
7. RedirectService.create_visit_record()
   ↓
8. Return RedirectResponse
```

### Admin CRUD Flow

```text
1. User submits A/B test form
   ↓
2. AdminRouter receives POST
   ↓
3. Verify admin session
   ↓
4. ABTestService.validate_probability_sum()
   ↓
5. ABTestService.create_test()
   ↓
6. Database commit
   ↓
7. Redirect to detail page with success message
```

## Environment Variables

### Required

- `DATABASE_URL`: Database connection string
- `ADMIN_TOKEN`: Admin authentication token
- `SECRET_KEY`: Session signing key
- `JWT_SECRET`: JWT secret key

### Optional

- `GOOGLE_CREDENTIALS_PATH`: Google Forms API credentials
- `DEBUG`: Enable debug mode
- `SESSION_MAX_AGE`: Session lifetime
- `CLICK_ID_MAX_AGE_SECONDS`: Click ID inclusion window

## Next Steps

After setup:

1. **Customize**:
   - Modify templates for your branding
   - Add custom validation rules
   - Extend A/B test features

2. **Deploy**:
   - Use Docker Compose for easy deployment
   - Configure Nginx for production
   - Set up HTTPS certificates

3. **Monitor**:
   - Track redirect performance
   - Monitor A/B test distributions
   - Review visit data

4. **Optimize**:
   - Add caching layer
   - Implement rate limiting
   - Scale horizontally

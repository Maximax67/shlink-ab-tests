# URL Redirect & A/B Testing Service

A Python web application that extends existing URL shortener databases (Shlink schema compatible) with A/B testing, visit tracking, Google Forms prefilling, and an admin dashboard.

## Features

- **Database Agnostic**: Works with MySQL, PostgreSQL, SQL Server via SQLAlchemy ORM
- **A/B Testing**: Deterministic variant selection based on user IP hash
- **Visit Tracking**: Records all redirects with detailed metadata
- **Google Forms Prefilling**: Automatically prefills form fields from URL parameters
- **Admin Dashboard**: Web-based interface for managing A/B tests
- **Read-Only Safety**: Only modifies the `ab_tests` table, preserves existing data
- **Cookie-Based Authentication**: Secure admin access with session management

## Architecture

```
├── models.py                 # SQLAlchemy ORM models
├── database.py              # Database connection and session management
├── config.py                # Configuration from environment variables
├── schemas.py               # Pydantic validation models
├── main.py                  # FastAPI application entry point
├── routers/
│   ├── redirect.py          # Redirect endpoint with A/B testing
│   └── admin.py             # Admin dashboard and CRUD API
├── services/
│   ├── redirect_service.py  # Redirect logic and A/B variant selection
│   ├── ab_test_service.py   # A/B test CRUD operations
│   └── auth_service.py      # Admin authentication
├── templates/
│   ├── base.html            # Base template
│   ├── login.html           # Admin login page
│   ├── dashboard.html       # Dashboard with URL list
│   └── short_url_detail.html # A/B test management
└── alembic/
    └── versions/
        └── 001_create_ab_tests.py # Database migration
```

## Installation

### 1. Clone and Setup

```bash
git clone <repository>
cd url-redirect-ab-testing
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file from example:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Database URL (choose based on your database)
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/shlink

# Admin credentials
ADMIN_TOKEN=your-secure-token-here
SECRET_KEY=your-secret-key-here

# Optional: Google Forms API
GOOGLE_CREDENTIALS_PATH=google_credentials.json
```

### 3. Run Database Migration

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create ab_tests table
alembic upgrade head
```

### 4. Start the Application

```bash
# Development
python main.py

# Production with Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

The application will be available at:
- Redirects: `http://localhost:8000/{short_code}`
- Admin: `http://localhost:8000/admin/login`

## Database Support

### MySQL/MariaDB

```bash
pip install pymysql cryptography
```

```env
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/database
```

### PostgreSQL

```bash
pip install psycopg2-binary
```

```env
DATABASE_URL=postgresql://user:password@localhost:5432/database
```

### SQL Server

**Option 1: Using pyodbc**

```bash
pip install pyodbc
```

```env
DATABASE_URL=mssql+pyodbc://user:password@localhost:1433/database?driver=ODBC+Driver+17+for+SQL+Server
```

**Option 2: Using pymssql**

```bash
pip install pymssql
```

```env
DATABASE_URL=mssql+pymssql://user:password@localhost:1433/database
```

## Usage

### Redirect Flow

When a user visits a short URL:

1. **Request**: `GET /{short_code}?utm_source=email&campaign=summer`

2. **Resolution**: Application resolves short code to `short_urls` record

3. **A/B Selection**: 
   - Fetches active A/B tests for this URL
   - Uses IP hash to deterministically select variant
   - If no tests or IP falls in remaining probability → primary URL

4. **Visit Recording**: Creates record in `visits` table with metadata

5. **Redirect**: User is redirected with forwarded query parameters

### A/B Testing Example

Create an A/B test that sends 30% of traffic to variant A:

```python
# Via Admin Dashboard:
# 1. Navigate to short URL detail page
# 2. Create new A/B test:
#    - Target URL: https://example.com/variant-a
#    - Probability: 0.3
#    - Active: Yes

# Result:
# - 30% of traffic → variant A
# - 70% of traffic → primary URL (original_url)
```

### Google Forms Prefilling

The application automatically prefills Google Forms fields:

1. **utm_source**: Always included from query parameters
2. **click_id**: Only included if last visit was ≤ 1 minute ago

Example:
```
Input:  /{short_code}?utm_source=email
Output: https://docs.google.com/forms/d/.../viewform?entry.123=email&entry.456=98765
```

> **Note**: The current implementation uses placeholder entry IDs. In production, you should:
> 1. Use Google Forms API to fetch form structure
> 2. Detect actual entry IDs for each field
> 3. Map query parameters to entry IDs

### Admin Dashboard

1. **Login**: Navigate to `/admin/login` and enter admin token

2. **Dashboard**: View all short URLs with A/B test statistics
   - Search by short code or title
   - View probability usage per URL
   - Pagination support

3. **Manage A/B Tests**:
   - Create: Set target URL, probability, and active status
   - Update: Modify any test parameters
   - Delete: Remove tests (validates probability sum)
   - Validation: System ensures total probability ≤ 1.0

## API Endpoints

### Redirect

```
GET /{short_code}
Query params: Any (forwarded to target URL if enabled)
Response: 307 Redirect
```

### Admin Authentication

```
POST /admin/login
Body: token=<admin_token>
Response: Redirect with session cookie
```

```
POST /admin/logout
Response: Redirect to login, clear session
```

### Admin Dashboard

```
GET /admin/dashboard
Query: page, limit, search
Auth: Session cookie required
Response: HTML dashboard
```

```
GET /admin/short_url/{id}
Auth: Session cookie required
Response: HTML detail page with A/B tests
```

### A/B Test Management

```
POST /admin/short_url/{id}/ab_test
Body: target_url, probability, is_active
Auth: Session cookie required
Response: Redirect with success/error message
```

```
POST /admin/ab_test/{id}/update
Body: target_url, probability, is_active (all optional)
Auth: Session cookie required
Response: Redirect with success/error message
```

```
POST /admin/ab_test/{id}/delete
Auth: Session cookie required
Response: Redirect with success/error message
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLAlchemy connection string | Required |
| `ADMIN_TOKEN` | Token for admin authentication | Required |
| `SECRET_KEY` | Secret key for session signing | Required |
| `GOOGLE_CREDENTIALS_PATH` | Path to Google service account JSON | `google_credentials.json` |
| `DEBUG` | Enable debug mode | `false` |
| `SESSION_MAX_AGE` | Session lifetime in seconds | `86400` (24h) |
| `CLICK_ID_MAX_AGE_SECONDS` | Max age for click_id inclusion | `60` (1 min) |

### Google Forms API Setup (Optional)

For advanced Google Forms prefilling:

1. Create a Google Cloud project
2. Enable Google Forms API
3. Create service account credentials
4. Download JSON credentials
5. Set `GOOGLE_CREDENTIALS_PATH` in `.env`

## A/B Testing Logic

### Probability Distribution

The system uses deterministic IP-based routing:

```python
# Example with 2 A/B tests:
# Test 1: probability = 0.3 (30%)
# Test 2: probability = 0.4 (40%)
# Primary URL: remaining = 0.3 (30%)

hash = MD5(user_ip)[:8]
hash_float = int(hash, 16) / (16^8)  # 0.0 to 1.0

if hash_float < 0.3:
    redirect to Test 1
elif hash_float < 0.7:  # 0.3 + 0.4
    redirect to Test 2
else:
    redirect to Primary URL
```

### Deterministic Routing

- Same IP always gets same variant
- Distribution is stable across sessions
- Enables accurate A/B testing with consistent user experience

### Validation Rules

- Total active probability per URL must be ≤ 1.0
- Individual probabilities must be 0.0 to 1.0
- System prevents invalid configurations
- Inactive tests don't count toward probability sum

## Development

### Project Structure

```
.
├── models.py           # Database models (SQLAlchemy)
├── schemas.py          # API schemas (Pydantic)
├── database.py         # Database connection
├── config.py           # Configuration
├── main.py             # FastAPI app
├── routers/
│   ├── redirect.py     # Redirect logic
│   └── admin.py        # Admin endpoints
├── services/
│   ├── redirect_service.py
│   ├── ab_test_service.py
│   └── auth_service.py
├── templates/          # Jinja2 templates
├── alembic/            # Database migrations
├── requirements.txt
└── .env.example
```

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Adding New Features

1. **New A/B Test Features**: Modify `services/ab_test_service.py`
2. **New Admin Pages**: Add routes to `routers/admin.py` and templates
3. **Custom Redirect Logic**: Extend `services/redirect_service.py`

## Production Deployment

### 1. Security Checklist

- [ ] Change `ADMIN_TOKEN` to a strong random value
- [ ] Generate secure `SECRET_KEY` (32+ characters)
- [ ] Use HTTPS in production
- [ ] Set `DEBUG=false`
- [ ] Configure database connection pooling
- [ ] Set up proper logging

### 2. Database Optimization

```sql
-- Add additional indexes if needed
CREATE INDEX idx_visits_short_url_date ON visits(short_url_id, date);
CREATE INDEX idx_ab_tests_active_short_url ON ab_tests(is_active, short_url_id);
```

### 3. Deployment Options

**Docker**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

**Systemd Service**:
```ini
[Unit]
Description=URL Redirect Service
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/redirect-service
Environment="PATH=/opt/redirect-service/venv/bin"
ExecStart=/opt/redirect-service/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```

### 4. Monitoring

Key metrics to monitor:
- Redirect latency
- A/B test distribution accuracy
- Database connection pool usage
- Session store size
- Error rates

## Troubleshooting

### Common Issues

**Database Connection Errors**:
- Verify `DATABASE_URL` format
- Check database server is running
- Ensure database user has proper permissions
- For SQL Server, verify ODBC driver is installed

**Migration Fails**:
- Ensure database user has CREATE TABLE permission
- Check if `ab_tests` table already exists
- Review Alembic logs for specific errors

**A/B Tests Not Working**:
- Verify tests are marked as active
- Check total probability doesn't exceed 1.0
- Review logs for variant selection
- Ensure IP address is being captured correctly

**Admin Login Issues**:
- Verify `ADMIN_TOKEN` matches `.env` value
- Check browser cookies are enabled
- Clear browser cache and cookies

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

## Support

For issues and questions:
- GitHub Issues: [Your Repo]
- Email: [Your Email]
- Documentation: [Your Docs URL]

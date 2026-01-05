# URL Redirect & A/B Testing Service

⚠️ **Most of the code is written using Claude Sonnet 4.5**

A Python web application that extends existing URL shortener databases (Shlink schema compatible) with A/B testing, visit tracking, Google Forms prefilling, and an admin dashboard.

## Features

- **Database Agnostic**: Works with MySQL, PostgreSQL, SQL Server via SQLAlchemy ORM
- **A/B Testing**: Deterministic variant selection based on user IP hash
- **Visit Tracking**: Records all redirects with detailed metadata
- **Google Forms Prefilling**: Automatically prefills form fields from URL parameters
- **Admin Dashboard**: Web-based interface for managing A/B tests
- **Read-Only Safety**: Only modifies the `ab_tests` table, preserves existing data
- **Cookie-Based Authentication**: Secure admin access with session management

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

Edit `.env` with your settings.

### 3. Run Database Migration

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create ab_tests and google_forms table
alembic upgrade head
```

### 4. Deploy App Script for Google Forms prefilling

1. Visit [https://script.google.com](https://script.google.com).
2. Create New Project.
3. Copy and paste `app_script.gs` file content.
4. Go to the Project settings -> Script Properties -> Add Script Property. Put `API_TOKEN` as property and some random string as value. Click save.
5. Press Deploy -> New Deployment -> Web app.
6. Put some description.
7. Select "Anyone" in "Who has access" dropdown.
8. Click Deploy.
9. Fill `APP_SCRIPT_URL` env variable with deployment url and `APP_SCRIPT_API_KEY` as your string from step 4.

After that if form has questions with names `utm_source`, `utm_medium`, `utm_campaign` they will be prefilled based on url query params. Also if url is visited from Shlink, fields `click_id` and `click_timestamp` be prefilled.

When using Google Forms you can make these fields invisible to user by adding them on a new form section and selecting "Submit form" option after previous section.

### 5. Start the Application

```bash
# Development
fastapi dev app/main.py

# Production
fastapi app/main.py
```

The application will be available at:

- Redirects: `http://localhost:8000/?url={target_url}`
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

#### Option 1: Using pyodbc

```bash
pip install pyodbc
```

```env
DATABASE_URL=mssql+pyodbc://user:password@localhost:1433/database?driver=ODBC+Driver+17+for+SQL+Server
```

#### Option 2: Using pymssql

```bash
pip install pymssql
```

```env
DATABASE_URL=mssql+pymssql://user:password@localhost:1433/database
```

## Usage

### Redirect Flow

When a user visits a short URL:

1. **Request**: `GET /?url={url}&utm_source=email&campaign=summer`

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
# - 70% of traffic → primary URL
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

## A/B Testing Logic

### Deterministic Routing

- Same IP always gets same variant
- Distribution is stable across sessions
- Enables accurate A/B testing with consistent user experience

### Validation Rules

- Total active probability per URL must be ≤ 1.0
- Individual probabilities must be 0.0 to 1.0
- System prevents invalid configurations
- Inactive tests don't count toward probability sum

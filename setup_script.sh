#!/bin/bash
# setup.sh - Automated setup script for URL Redirect & A/B Testing Service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo ""
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main setup
main() {
    print_header "URL Redirect & A/B Testing Setup"
    
    # Check prerequisites
    print_info "Checking prerequisites..."
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.11 or higher."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    print_success "Python $PYTHON_VERSION found"
    
    # Check if we're in the right directory
    if [ ! -f "main.py" ]; then
        print_error "main.py not found. Please run this script from the project root directory."
        exit 1
    fi
    
    # Create virtual environment
    print_header "Creating Virtual Environment"
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists. Skipping..."
    else
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    print_info "Activating virtual environment..."
    source venv/bin/activate || {
        print_error "Failed to activate virtual environment"
        exit 1
    }
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip > /dev/null 2>&1
    print_success "pip upgraded"
    
    # Install dependencies
    print_header "Installing Dependencies"
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi
    
    print_info "Installing Python packages (this may take a few minutes)..."
    pip install -r requirements.txt > /dev/null 2>&1
    print_success "All dependencies installed"
    
    # Create .env file if it doesn't exist
    print_header "Configuring Environment"
    
    if [ -f ".env" ]; then
        print_warning ".env file already exists. Skipping..."
    else
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success ".env file created from example"
            print_warning "⚠️  IMPORTANT: Edit .env file with your actual configuration!"
            
            # Generate secure tokens
            print_info "Generating secure tokens..."
            
            ADMIN_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
            SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
            
            # Update .env with generated tokens
            if command_exists sed; then
                sed -i.bak "s/ADMIN_TOKEN=.*/ADMIN_TOKEN=$ADMIN_TOKEN/" .env
                sed -i.bak "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
                rm -f .env.bak
                print_success "Secure tokens generated and saved to .env"
                echo ""
                print_info "Your admin token: ${GREEN}$ADMIN_TOKEN${NC}"
                print_warning "Save this token securely! You'll need it to login."
                echo ""
            else
                print_warning "Please manually update ADMIN_TOKEN and SECRET_KEY in .env"
            fi
        else
            print_error ".env.example not found"
            exit 1
        fi
    fi
    
    # Verify database URL
    print_header "Database Configuration"
    
    if grep -q "DATABASE_URL=.*your-database-url" .env; then
        print_warning "Database URL not configured yet"
        print_info "Please update DATABASE_URL in .env file with your database connection string"
        print_info "Examples:"
        print_info "  MySQL:      mysql+pymysql://user:pass@localhost:3306/database"
        print_info "  PostgreSQL: postgresql://user:pass@localhost:5432/database"
        print_info "  SQL Server: mssql+pyodbc://user:pass@localhost:1433/database?driver=ODBC+Driver+17+for+SQL+Server"
        echo ""
        read -p "Press Enter after updating DATABASE_URL in .env..."
    fi
    
    # Test database connection
    print_info "Testing database connection..."
    python3 -c "
from config import get_settings
from database import engine
try:
    settings = get_settings()
    conn = engine.connect()
    conn.close()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
" || {
        print_error "Database connection failed. Please check DATABASE_URL in .env"
        exit 1
    }
    
    # Create necessary directories
    print_header "Creating Directories"
    
    mkdir -p templates alembic/versions routers services
    print_success "Directory structure created"
    
    # Initialize Alembic if not already done
    print_header "Database Migration Setup"
    
    if [ ! -f "alembic.ini" ]; then
        print_warning "alembic.ini not found. Please ensure Alembic is configured."
    else
        print_info "Running database migrations..."
        alembic upgrade head || {
            print_error "Migration failed. Please check your database configuration."
            exit 1
        }
        print_success "Database migrations complete"
    fi
    
    # Create __init__.py files
    print_header "Creating Package Files"
    
    touch routers/__init__.py services/__init__.py
    print_success "Package files created"
    
    # Run basic tests
    print_header "Running Basic Tests"
    
    if [ -f "test_app.py" ]; then
        print_info "Running tests..."
        pytest test_app.py -v || print_warning "Some tests failed (this is ok for initial setup)"
    else
        print_warning "test_app.py not found, skipping tests"
    fi
    
    # Final instructions
    print_header "Setup Complete! 🎉"
    
    echo -e "${GREEN}Your application is ready to run!${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo ""
    echo "1. Activate virtual environment:"
    echo -e "   ${YELLOW}source venv/bin/activate${NC}"
    echo ""
    echo "2. Start the application:"
    echo -e "   ${YELLOW}python main.py${NC}"
    echo ""
    echo "3. Access the admin dashboard:"
    echo -e "   ${YELLOW}http://localhost:8000/admin/login${NC}"
    echo ""
    echo "4. Use your admin token to login:"
    echo -e "   ${GREEN}$ADMIN_TOKEN${NC}"
    echo ""
    echo -e "${BLUE}Alternative: Production deployment${NC}"
    echo -e "   ${YELLOW}gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker${NC}"
    echo ""
    print_success "Happy A/B testing! 🚀"
    echo ""
}

# Run main function
main "$@"

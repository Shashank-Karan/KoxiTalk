#!/usr/bin/env python3
"""
Setup script for the Real-Time Chat Application
This script helps set up the development environment
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_command(command, cwd=None, check=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, check=check, 
                              capture_output=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e.stderr}")
        return False


def check_requirements():
    """Check if required software is installed"""
    requirements = {
        'python': 'python --version',
        'pip': 'pip --version',
        'node': 'node --version',
        'npm': 'npm --version',
        'docker': 'docker --version',
        'docker-compose': 'docker-compose --version'
    }
    
    print("🔍 Checking system requirements...")
    missing = []
    
    for name, command in requirements.items():
        if run_command(command, check=False):
            print(f"✅ {name} is installed")
        else:
            print(f"❌ {name} is not installed")
            missing.append(name)
    
    if missing:
        print(f"\n❌ Missing requirements: {', '.join(missing)}")
        print("Please install the missing software before continuing.")
        return False
    
    print("\n✅ All requirements are satisfied!")
    return True


def setup_backend():
    """Set up the Python backend"""
    print("\n🐍 Setting up Python backend...")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ Backend directory not found!")
        return False
    
    # Create virtual environment
    venv_dir = backend_dir / "venv"
    if not venv_dir.exists():
        print("📦 Creating virtual environment...")
        if not run_command("python -m venv venv", cwd=backend_dir):
            return False
    
    # Determine activation script based on OS
    if os.name == 'nt':  # Windows
        activate_script = venv_dir / "Scripts" / "activate.bat"
        pip_cmd = str(venv_dir / "Scripts" / "pip")
    else:  # Unix/Linux/macOS
        activate_script = venv_dir / "bin" / "activate"
        pip_cmd = str(venv_dir / "bin" / "pip")
    
    # Install dependencies
    print("📦 Installing Python dependencies...")
    if not run_command(f"{pip_cmd} install --upgrade pip", cwd=backend_dir):
        return False
    
    if not run_command(f"{pip_cmd} install -r requirements.txt", cwd=backend_dir):
        return False
    
    # Copy environment file
    env_example = backend_dir / ".env.example"
    env_file = backend_dir / ".env"
    
    if env_example.exists() and not env_file.exists():
        print("📝 Creating .env file...")
        shutil.copy(env_example, env_file)
        print("⚠️  Please edit backend/.env with your configuration")
    
    print("✅ Backend setup complete!")
    return True


def setup_frontend():
    """Set up the React frontend"""
    print("\n⚛️  Setting up React frontend...")
    
    client_dir = Path("client")
    if not client_dir.exists():
        print("📦 Creating React application...")
        if not run_command("npx create-next-app@latest client --typescript --tailwind --eslint --app --src-dir --import-alias '@/*'"):
            return False
    
    # Install additional dependencies
    print("📦 Installing additional frontend dependencies...")
    frontend_deps = [
        "socket.io-client",
        "zustand", 
        "@tanstack/react-query",
        "axios",
        "react-hot-toast",
        "lucide-react",
        "@radix-ui/react-avatar",
        "@radix-ui/react-button",
        "@radix-ui/react-dialog",
        "@radix-ui/react-dropdown-menu",
        "@radix-ui/react-input",
        "@radix-ui/react-label",
        "@radix-ui/react-scroll-area",
        "@radix-ui/react-separator",
        "@radix-ui/react-textarea",
        "class-variance-authority",
        "clsx",
        "tailwind-merge"
    ]
    
    deps_str = " ".join(frontend_deps)
    if not run_command(f"npm install {deps_str}", cwd=client_dir):
        return False
    
    print("✅ Frontend setup complete!")
    return True


def setup_database():
    """Set up the database using Docker"""
    print("\n🐘 Setting up database with Docker...")
    
    # Check if Docker is running
    if not run_command("docker info", check=False):
        print("❌ Docker is not running. Please start Docker Desktop.")
        return False
    
    # Start database services
    print("🚀 Starting database services...")
    if not run_command("docker-compose up -d postgres redis"):
        print("❌ Failed to start database services")
        return False
    
    print("⏳ Waiting for database to be ready...")
    import time
    time.sleep(10)  # Wait for services to start
    
    print("✅ Database setup complete!")
    return True


def run_migrations():
    """Run database migrations"""
    print("\n🔄 Running database migrations...")
    
    backend_dir = Path("backend")
    if os.name == 'nt':  # Windows
        python_cmd = str(backend_dir / "venv" / "Scripts" / "python")
    else:  # Unix/Linux/macOS
        python_cmd = str(backend_dir / "venv" / "bin" / "python")
    
    # Initialize Alembic if not already done
    alembic_dir = backend_dir / "alembic"
    if not alembic_dir.exists():
        print("🆕 Initializing database migrations...")
        if not run_command(f"{python_cmd} -m alembic init alembic", cwd=backend_dir):
            return False
    
    # Create migration
    if not run_command(f"{python_cmd} -m alembic revision --autogenerate -m 'Initial migration'", cwd=backend_dir):
        print("⚠️  Migration creation failed (this might be normal for first run)")
    
    # Run migrations
    if not run_command(f"{python_cmd} -m alembic upgrade head", cwd=backend_dir):
        print("⚠️  Migration failed (database might not be ready)")
    
    print("✅ Migrations complete!")
    return True


def print_startup_instructions():
    """Print instructions for starting the application"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    
    print("\n🚀 To start the application:")
    print("\n1. Start all services with Docker:")
    print("   docker-compose up")
    print("\n2. Or start services individually:")
    print("\n   Backend (Python FastAPI):")
    if os.name == 'nt':  # Windows
        print("   cd backend && venv\\Scripts\\activate && uvicorn main:app --reload")
    else:  # Unix/Linux/macOS
        print("   cd backend && source venv/bin/activate && uvicorn main:app --reload")
    
    print("\n   Frontend (React):")
    print("   cd client && npm run dev")
    
    print("\n📱 Access the application:")
    print("   Frontend: http://localhost:3000")
    print("   Backend API: http://localhost:8000")
    print("   API Documentation: http://localhost:8000/docs")
    
    print("\n🔧 Configuration:")
    print("   - Edit backend/.env for database and API settings")
    print("   - Edit client/.env.local for frontend settings")
    
    print("\n📚 Documentation:")
    print("   - README.md: Project overview and features")
    print("   - API docs: Available at /docs endpoint when running")
    
    print("\n" + "="*60)


def main():
    """Main setup function"""
    print("🚀 Real-Time Chat Application Setup")
    print("="*50)
    
    # Check system requirements
    if not check_requirements():
        sys.exit(1)
    
    # Set up backend
    if not setup_backend():
        print("❌ Backend setup failed!")
        sys.exit(1)
    
    # Set up frontend  
    if not setup_frontend():
        print("❌ Frontend setup failed!")
        sys.exit(1)
    
    # Set up database
    if not setup_database():
        print("❌ Database setup failed!")
        sys.exit(1)
    
    # Run migrations
    run_migrations()
    
    # Print startup instructions
    print_startup_instructions()


if __name__ == "__main__":
    main()

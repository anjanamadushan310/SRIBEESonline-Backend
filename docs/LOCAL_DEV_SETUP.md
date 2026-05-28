# 🚀 SRIBEESonline - Local Development Setup Guide

## Prerequisites

### Required Software
1. **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop/)
2. **Android Studio** - [Download](https://developer.android.com/studio)
3. **Flutter SDK** - [Download](https://docs.flutter.dev/get-started/install)
4. **Git** - [Download](https://git-scm.com/)

### Verify Installations
```powershell
# Check Docker
docker --version
docker compose version

# Check Flutter
flutter --version
flutter doctor
```

---

## 🐳 Part 1: Running Backend Stack with Docker Desktop

### Step 1: Prepare Environment Files

1. Copy the environment template:
```powershell
cd c:\Users\Lenovo\Desktop\SRIBEESonline
copy .env.docker .env
```

2. (Optional) Edit `.env` to customize credentials if needed.

3. **(Recommended)** Add your Gemini API key for AI-powered search:
```powershell
# Edit .env and add:
# GEMINI_API_KEY=your-google-gemini-api-key

# Get your API key from: https://aistudio.google.com/apikey
```

> **Note**: Semantic search will work without a Gemini API key by falling back to keyword search.

### Step 2: Start Docker Desktop

1. Open **Docker Desktop** application
2. Wait for Docker to fully start (whale icon in system tray should be steady)
3. Ensure Docker is running in **Linux containers** mode

### Step 3: Build and Start All Services

```powershell
# Navigate to project root
cd c:\Users\Lenovo\Desktop\SRIBEESonline

# Build and start core services (Postgres, Redis, MinIO, FastAPI)
docker compose up -d --build postgres_db redis_cache s3-local minio_init fastapi_backend

# Or start all services including admin panel
docker compose up -d --build

# View logs
docker compose logs -f fastapi_backend
```

### Step 4: Verify Services Are Running

```powershell
# Check running containers
docker compose ps

# Expected healthy containers:
#   sribees_postgres  - Healthy (port 5432)
#   sribees_redis     - Healthy (port 6379)
#   sribees_minio     - Healthy (port 9000, 9001)
#   sribees_backend   - Healthy (port 8000)

# Check logs
docker compose logs -f fastapi_backend
docker compose logs -f postgres_db
docker compose logs -f redis_cache
```

### Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **FastAPI Backend** | http://localhost:8000 | Main API |
| **API Documentation** | http://localhost:8000/docs | Swagger UI |
| **Semantic Search** | http://localhost:8000/api/v1/search | AI-powered search endpoint |
| **Admin Dashboard** | http://localhost:3000 | React Admin Panel |
| **pgAdmin** | http://localhost:5050 | Database Admin Tool |
| **MinIO Console** | http://localhost:9001 | S3 Storage Admin (admin / password123) |
| **MinIO S3 API** | http://localhost:9000 | S3-compatible storage |
| **Redis Commander** | http://localhost:8081 | Redis Admin Tool |

### Step 5: Access Management Tools

#### pgAdmin (Database)
1. Open http://localhost:5050
2. Login with:
   - Email: `admin@sribees.lk`
   - Password: `pgadmin_password_123`
3. Add New Server:
   - Name: `SRIBEESonline Local`
   - Host: `postgres`
   - Port: `5432`
   - Database: `sribeesonline`
   - Username: `sribees_user`
   - Password: `sribees_password_123`

#### Redis Commander
1. Open http://localhost:8081
2. Browse Redis keys and monitor cache

### Common Docker Commands

```powershell
# Stop all services
docker compose down

# Stop and remove volumes (fresh start)
docker compose down -v

# Restart a specific service
docker compose restart fastapi_backend

# View real-time logs
docker compose logs -f

# Rebuild a specific service
docker compose build fastapi_backend
docker compose up -d fastapi_backend

# Access container shell
docker exec -it sribees_backend bash
docker exec -it sribees_postgres psql -U sribees_user -d sribeesonline

# Check container resources
docker stats
```

---

## 📱 Part 2: Running Flutter App with Android Studio

### Step 1: Open Flutter Project

1. Open **Android Studio**
2. Click **Open** or **File > Open**
3. Navigate to: `c:\Users\Lenovo\Desktop\SRIBEESonline\mobile`
4. Click **OK** to open the project

### Step 2: Install Flutter Dependencies

```powershell
cd c:\Users\Lenovo\Desktop\SRIBEESonline\mobile

# Get dependencies
flutter pub get

# Generate code (if using code generation)
flutter pub run build_runner build --delete-conflicting-outputs
```

### Step 3: Configure Android Emulator

1. In Android Studio, go to **Tools > Device Manager**
2. Click **Create Device**
3. Select a device (e.g., Pixel 6)
4. Select a system image (recommend API 33 or 34)
5. Click **Finish**
6. Start the emulator by clicking the ▶️ play button

### Step 4: Configure API URL for Emulator

The app is already configured to use `10.0.2.2:8000` for Android emulator.
This special IP maps to your computer's localhost from inside the emulator.

**Important**: Make sure Docker backend is running before starting the app!

### Step 5: Run the Flutter App

#### Option A: From Android Studio
1. Select your emulator from the device dropdown
2. Click the green **Run** button (▶️)
3. Or press `Shift + F10`

#### Option B: From Terminal
```powershell
cd c:\Users\Lenovo\Desktop\SRIBEESonline\mobile

# Run on connected device/emulator
flutter run

# Run with specific device
flutter devices  # List available devices
flutter run -d <device_id>

# Run in debug mode with hot reload
flutter run --debug
```

### Step 6: Hot Reload and Debug

- **Hot Reload**: Press `r` in terminal or `Ctrl+\` in Android Studio
- **Hot Restart**: Press `R` in terminal
- **Debug**: Use Android Studio's debugger or VS Code's Flutter extension

---

## 🔧 Troubleshooting

### Docker Issues

**Problem**: Containers won't start
```powershell
# Check Docker Desktop is running
# Check for port conflicts
netstat -ano | findstr :8000
netstat -ano | findstr :5432

# Reset everything
docker compose down -v
docker system prune -a
docker compose up -d --build
```

**Problem**: Backend can't connect to database
```powershell
# Ensure postgres is healthy
docker compose ps
docker compose logs postgres_db

# Wait for postgres to be ready, then restart backend
docker compose restart fastapi_backend
```

**Problem**: Permission denied errors
```powershell
# Run Docker Desktop as Administrator
# Or add your user to docker-users group
```

### Flutter Issues

**Problem**: Can't connect to API from emulator
```dart
// Ensure app_config.dart uses correct URL
apiBaseUrl: 'http://10.0.2.2:8000/api/v1'  // for Android Emulator
```

**Problem**: Build errors
```powershell
# Clean and rebuild
flutter clean
flutter pub get
flutter pub run build_runner build --delete-conflicting-outputs
```

**Problem**: Emulator not detected
```powershell
# Check ADB connection
adb devices

# Restart ADB
adb kill-server
adb start-server
```

### Network Issues

**Testing API from Emulator**:
```powershell
# From your computer, test the API is accessible
curl http://localhost:8000/health

# From Android Studio terminal (inside emulator via adb)
adb shell curl http://10.0.2.2:8000/health
```

---

## 🧪 Testing the Full Stack

### 1. Test Backend API
```powershell
# Health check
curl http://localhost:8000/health

# API docs
start http://localhost:8000/docs
```

### 2. Test Admin Dashboard
```powershell
start http://localhost:3000
```
Login with:
- Email: `admin@sribees.lk`
- Password: `Admin@123456`

### 3. Test Flutter App
1. Start emulator
2. Run Flutter app
3. Register a new account or login
4. Browse products

---

## 📊 Development Workflow

### Daily Development

1. **Start Docker Stack**:
   ```powershell
   cd c:\Users\Lenovo\Desktop\SRIBEESonline
   docker compose up -d
   ```

2. **Start Flutter App**:
   ```powershell
   cd mobile
   flutter run
   ```

3. **Make Changes**:
   - Backend changes: Auto-reload enabled
   - Flutter changes: Use hot reload (r)
   - Admin changes: Vite auto-reload enabled

4. **End of Day**:
   ```powershell
   docker compose down
   ```

### Viewing Logs
```powershell
# All services
docker compose logs -f

# Specific service
docker compose logs -f fastapi_backend

# Last 100 lines
docker compose logs --tail=100 fastapi_backend
```

---

## 🔐 Default Credentials

| Service | Username/Email | Password |
|---------|----------------|----------|
| Admin Dashboard | admin@sribees.lk | Admin@123456 |
| pgAdmin | admin@sribees.lk | pgadmin_password_123 |
| PostgreSQL | sribees_user | sribees_password_123 |
| Redis | - | sribees_redis_password |
| MinIO Console | admin | password123 |

⚠️ **Security Note**: Change all passwords before deploying to production!

---

## 📁 Project Structure

```
SRIBEESonline/
├── docker-compose.yml      # Docker orchestration (Postgres, Redis, MinIO, FastAPI)
├── docker-compose.prod.yml # Production overrides
├── Jenkinsfile             # CI/CD pipeline (Build, Test, Health Check)
├── scripts/
│   └── setup.sh            # Automated local setup script
├── .env.docker             # Environment template
├── .env                    # Your local environment (gitignored)
│
├── fastapi_backend/        # Python FastAPI backend
│   ├── Dockerfile
│   ├── app/
│   └── requirements.txt
│
├── admin/                  # React admin dashboard
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│
├── mobile/                 # Flutter mobile app
│   ├── lib/
│   │   └── config/
│   │       └── app_config.dart
│   └── pubspec.yaml
│
└── docker/
    └── postgres/
        └── init.sql        # Database initialization
```

---

## 🗄️ Database Initialization

The database is automatically initialized when containers start for the first time:

1. **Schema creation**: `docker/postgres/init.sql` creates the `sribees` schema with all core tables
2. **Migrations**: Run SQL migrations from `fastapi_backend/migrations/`:
   ```powershell
   # Run all migrations
   Get-ChildItem "fastapi_backend\migrations\*.sql" | Sort-Object Name | ForEach-Object {
       Write-Host "Running: $($_.Name)"
       Get-Content $_.FullName | docker exec -i sribees_postgres psql -U sribees_user -d sribeesonline
   }
   ```
3. **Seed data**: Upload splash video and seed database:
   ```powershell
   # The splash video is automatically seeded via the setup script
   # Or manually set the URL:
   docker exec sribees_postgres psql -U sribees_user -d sribeesonline -c "UPDATE app_settings SET value = 'http://localhost:9000/sribees-assets/splash/splash_video_initial.mp4' WHERE key = 'splash_video_url';"
   ```

### Verified Database Tables (16 total)

The following tables exist in the `sribees` schema after successful initialization:

| Table | Purpose |
|-------|---------|
| `users` | Customer accounts |
| `admin_users` | Admin/staff accounts with RBAC roles |
| `branches` | Store branch locations |
| `products` | Global product catalog |
| `categories` | Product categories (8 seeded) |
| `addresses` | User delivery addresses |
| `orders` | Customer orders |
| `carts` | Shopping carts |
| `wishlists` | User wishlists |
| `product_reviews` | Product reviews & ratings |
| `notifications` | User notifications |
| `audit_logs` | Admin audit trail |
| `post_office_branch_mapping` | Address → Branch routing |
| `branch_inventory` | Branch-specific stock overrides |
| `app_settings` | Runtime configuration (splash video URL) |

---

## 📱 Flutter Mobile App

### First-Time Setup

```powershell
cd mobile

# Install dependencies
flutter pub get

# Generate Android platform (if missing)
flutter create . --org com.sribeesonline --project-name sribees_mobile --platforms android

# Run on connected emulator
flutter run -d emulator-5554 -t lib/main_development.dart
```

### Important Notes

- **Firebase**: Disabled until `google-services.json` is configured. The `FirebaseService` is a no-op stub.
- **Fonts**: Custom Sinhala/Tamil fonts are commented out in `pubspec.yaml` (font files not yet added).
- **First build**: Takes 15-20 minutes (Gradle downloads all dependencies). Subsequent builds are much faster.
- **Cleartext traffic**: Enabled in `AndroidManifest.xml` for local HTTP connections to `10.0.2.2`.

### App Launch Flow

1. Splash screen fetches video URL from `GET /api/v1/app/splash-config`
2. Backend returns emulator-friendly URL (`10.0.2.2:9000` instead of `localhost`)
3. If video fails, shows static branding logo for 2 seconds
4. Checks SharedPreferences for language → Address Selection → Home Screen

---

## ❓ Need Help?

1. Check the logs: `docker compose logs -f`
2. Check Flutter logs: Look at Android Studio's Run tab
3. Check API docs: http://localhost:8000/docs
4. Verify services: `docker compose ps`

Happy coding! 🎉

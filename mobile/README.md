# SEVO Partner & Field Technician Mobile App

A cross-platform Flutter mobile application designed for field technicians, service vendors, and operations administrators to manage service requests, live navigation, on-site diagnostics, quotation estimates, and wallet earnings.

---

## 📱 Features

* **Authentication & Role-Based Cockpit**: Dedicated views tailored for Technicians, Vendor Managers, Admins, and Superadmins.
* **Real-Time Job Offers**: Push notifications and live offer queue with countdown timers, distance matrix, and transparent diagnostic payout preview.
* **Live GPS Navigation & Geofence Presence**: Turn-by-turn routing to customer locations with automatic arrival geofence detection.
* **Pre-Service & Inspection Checklist**: Structured arrival checklist, mandatory photo capture, initial diagnostics, and spare parts identification.
* **Digital Quotation & Approval**: In-app estimation entry powered by real-time rate cards and immediate customer OTP / signature authorization.
* **Secure OTP Job Completion**: Two-factor verification upon job completion ensuring transparent customer handoff.
* **Earnings & Wallet Ledger**: Real-time payout breakdown, advance settlements, cash collection recording, and transaction histories.
* **Offline Resilience**: Local caching of active job state with background sync once connectivity is restored.

---

## 🛠️ Tech Stack & Architecture

* **Framework**: Flutter (Dart SDK `^3.13.0`)
* **State Management**: [Riverpod (`flutter_riverpod: ^2.6.1`)](https://riverpod.dev)
* **Routing**: [GoRouter (`go_router: ^17.5.0`)](https://pub.dev/packages/go_router)
* **Networking**: [Dio (`dio: ^5.11.0`)](https://pub.dev/packages/dio) with custom interceptors for JWT token refresh
* **Secure Storage**: [flutter_secure_storage](https://pub.dev/packages/flutter_secure_storage) for encrypted token & session storage
* **Mapping & Geolocation**: [flutter_map](https://pub.dev/packages/flutter_map), [latlong2](https://pub.dev/packages/latlong2), and [geolocator](https://pub.dev/packages/geolocator)
* **Media & Documents**: [image_picker](https://pub.dev/packages/image_picker) for proof of work and document upload

---

## 📂 Project Structure

```plaintext
mobile/
├── lib/
│   ├── core/
│   │   ├── constants/             # API endpoints, asset paths, and storage keys
│   │   ├── network/               # Dio HTTP client, interceptors & error handlers
│   │   ├── storage/               # Secure storage abstraction for credentials
│   │   └── theme/                 # Design system, color palettes & typography
│   ├── features/
│   │   ├── auth/                  # Login, OTP verification, password reset & profile
│   │   ├── dashboard/             # Role-based dashboards & summary widgets
│   │   ├── jobs/                  # Job offers, active execution, checklists & completion
│   │   ├── location/              # Live background location tracking & map view
│   │   ├── estimations/           # Rate card lookups, dynamic quote entry & approvals
│   │   ├── wallet/                # Payouts, earnings ledger & transaction logs
│   │   └── profile/               # KYC documents, skills & availability toggle
│   ├── shared/
│   │   ├── models/                # Shared data contracts (User, Job, Company, etc.)
│   │   └── widgets/               # Reusable UI components (buttons, chips, modals)
│   └── main.dart                  # Application entry point & service initialization
├── android/                       # Android native configuration & Fastlane metadata
├── ios/                           # iOS native configuration & Podfile
└── pubspec.yaml                   # Package dependencies & asset configuration
```

---

## 🚀 Getting Started

### Prerequisites
* Flutter SDK (3.13.0 or higher)
* Android Studio / Xcode for emulators and native build tools
* Configured backend API server (local or staging)

### Installation & Run

1. **Install dependencies:**
   ```bash
   flutter pub get
   ```

2. **Configure Environment:**
   Ensure `lib/core/constants/api_constants.dart` or your environment config points to the correct backend host:
   ```dart
   // Example local Android emulator endpoint
   const String kBaseUrl = 'http://10.0.2.2:8000/api/v1';
   ```

3. **Run the App:**
   ```bash
   # Run on connected physical device or emulator
   flutter run
   ```

---

## 🔒 Permissions & Security

The app requires specific device permissions for seamless field operations:
* **Location (Foreground & Background)**: For real-time dispatch matching and customer proximity alerts.
* **Camera & Photo Library**: For uploading KYC identity documents, pre-service inspection photos, and job completion proofs.
* **Notifications**: For high-priority job offer alerts and schedule updates.

---

## 📦 Build & Release

### Android App Bundle (AAB)
```bash
flutter build appbundle --release
```

### Android APK
```bash
flutter build apk --release
```

Refer to [`docs/PLAY_STORE_LISTING.md`](file:///c:/Users/USER/Desktop/caldim%20projects/calservice-vendor/docs/PLAY_STORE_LISTING.md) and [`mobile/fastlane/`](file:///c:/Users/USER/Desktop/caldim%20projects/calservice-vendor/mobile/fastlane) for metadata, store copy, privacy policies, and release workflows.

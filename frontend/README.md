# PromoGuard Web

Next.js/TypeScript manager dashboard for the PromoGuard API.

## Local run

1. Start the API from the repository root:

```powershell
uvicorn apps.api.main:app --reload --port 8000
```

2. Install and start the web app:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

The primary flow is `CSV upload -> dataset ID -> quality gate -> report ID -> progress polling -> dashboard/PDF`. A configured local dataset path remains available only for internal compatibility. Authentication, multi-tenant storage, and cloud deployment require the pilot and security gates described in the architecture roadmap.

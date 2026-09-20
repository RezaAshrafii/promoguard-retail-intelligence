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

The browser sends the configured local dataset path to the local API. This is intentionally a local demo boundary; authentication, multi-tenant storage, background jobs, and cloud deployment are later product work.

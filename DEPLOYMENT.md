# Deployment Guide for Vercel

## What was fixed:
1. Updated `vercel.json` with proper build configuration and routing
2. Fixed `api/index.py` to export the correct handler for Vercel
3. Updated dependencies to include all required packages
4. Fixed Pydantic v2 settings configuration

## Before deploying to Vercel:

### 1. Set up Supabase
- Go to https://supabase.com and create a new project
- Once created, go to Project Settings > API
- Copy your project URL (looks like `https://xxxxx.supabase.co`)
- Copy your service_role key (under "Project API keys")

### 2. Create Supabase tables
Run this SQL in the Supabase SQL Editor:

```sql
create table if not exists candidates (
  id text primary key,
  region text not null,
  skills text[] not null,
  experience_years numeric not null,
  desired_roles text[] not null,
  portfolio_link text
);

create table if not exists jobs (
  id text primary key,
  employer text not null,
  title text not null,
  region text not null,
  description text not null,
  incentive_eligible boolean default false
);
```

### 3. Configure ConsentKeys
- Register your app at https://consentkeys.com
- Add redirect URI: `https://your-app.vercel.app/auth/callback`
- You already have credentials in your .env file

### 4. Deploy to Vercel

#### Option A: Using Vercel CLI
```bash
npm i -g vercel
vercel
```

#### Option B: Using Vercel Dashboard
1. Push your code to GitHub
2. Import the repository in Vercel
3. Add environment variables (see below)

### 5. Set Environment Variables in Vercel

Go to your project settings in Vercel and add these:

```
CONSENTKEYS_CLIENT_ID=ck_292674f59a7464fe2e9441574d96df92
CONSENTKEYS_CLIENT_SECRET=B2ZWNlDbPOWMBSh98iNkKjhcflJTANZcpENs1WGRRhc
CONSENTKEYS_ISSUER=https://consentkeys.com
APP_HOST=https://your-app.vercel.app
CONSENTKEYS_REDIRECT_PATH=https://your-app.vercel.app/auth/callback
SESSION_SECRET=<generate-a-long-random-string>
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
SUPABASE_JOBS_TABLE=jobs
SUPABASE_CANDIDATES_TABLE=candidates
```

**Important:** Replace `your-app` with your actual Vercel domain name!

### 6. Update ConsentKeys redirect URI
After deployment, update your ConsentKeys app registration to include your actual Vercel URL.

## Testing locally:

1. Update your `.env` file with your Supabase credentials
2. Change `APP_HOST` to `http://localhost:8000`
3. Change `CONSENTKEYS_REDIRECT_PATH` to `http://localhost:8000/auth/callback`
4. Run: `uvicorn main:app --reload`
5. Visit: http://localhost:8000

## Troubleshooting:

- Check `/health` endpoint to verify configuration
- Check Vercel function logs for errors
- Ensure all environment variables are set correctly
- Verify Supabase tables exist with correct schema

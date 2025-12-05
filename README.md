# MeritBoard

MeritBoard is a minimal FastAPI application that demonstrates a meritocratic job board for WorkBC regions. It relies on ConsentKeys OpenID Connect for privacy-preserving authentication while letting employers and candidates exchange anonymized profiles.

## Features
- ConsentKeys OIDC login via the authorization code flow.
- Simple landing page summarizing jobs and anonymized candidate profiles.
- JSON APIs to post jobs and candidate resumes without demographic identifiers.
- Supabase-backed storage for persistent candidates and job postings.

## Setup
1. Install dependencies (Python 3.11+ recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Configure ConsentKeys OIDC credentials and Supabase connection. Create a `.env` file in the project root (or provide the same values as environment variables in your runtime). **Do not commit this file to GitHub; keep it only on your local machine or runtime environment.**:
   ```bash
   CONSENTKEYS_CLIENT_ID=your_client_id
   CONSENTKEYS_CLIENT_SECRET=your_client_secret
   CONSENTKEYS_ISSUER=https://consentkeys.com
   APP_HOST=http://localhost:8000
   SESSION_SECRET=change_me
   SUPABASE_URL=https://<project>.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   SUPABASE_JOBS_TABLE=jobs
   SUPABASE_CANDIDATES_TABLE=candidates
   # Optional: override redirect path
   # CONSENTKEYS_REDIRECT_PATH=http://localhost:8000/auth/callback
   ```
   The `.env` file is not checked into source control; use it for local development. In production (e.g., Docker, managed hosting,
   or serverless), supply the same variable names through your platform's environment configuration instead of shipping a `.env`
   file with secrets. If you use GitHub Actions or deployments that read from GitHub, store these values in GitHub repository
   **Secrets**, not in the repository itself.
   The registered redirect URI in ConsentKeys should match `APP_HOST + CONSENTKEYS_REDIRECT_PATH` unless the redirect value is provided as a full URL. The default redirect is `https://meritboard.vercel.app/auth/callback`; set `CONSENTKEYS_REDIRECT_PATH=http://localhost:8000/auth/callback` for local development.
   The app surfaces a 500 error with guidance if the ConsentKeys client ID/secret are missing to avoid silent failures during login.

3. For the production host `https://meritboard.vercel.app`, configure the environment with the provided ConsentKeys credentials and callback:
   ```bash
   APP_HOST=https://meritboard.vercel.app
   CONSENTKEYS_REDIRECT_PATH=https://meritboard.vercel.app/auth/callback
   CONSENTKEYS_CLIENT_ID=ck_292674f59a7464fe2e9441574d96df92
   CONSENTKEYS_CLIENT_SECRET=B2ZWNlDbPOWMBSh98iNkKjhcflJTANZcpENs1WGRRhc
   ```
   Ensure the ConsentKeys application registration includes `https://meritboard.vercel.app/auth/callback` as an allowed redirect URI.

3. Run the app locally:
   ```bash
   uvicorn main:app --reload
   ```

4. Check the health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```
   This reports whether ConsentKeys credentials and Supabase connectivity variables are detected in the environment.

## Deploying to Vercel
1. Ensure your repository contains `vercel.json` and `api/index.py` (already included) so Vercel serves the FastAPI app from a Python Serverless Function using Python 3.11.
2. In the Vercel dashboard, add the following **Environment Variables** for your project (names must match exactly):
   - `APP_HOST=https://meritboard.vercel.app`
   - `CONSENTKEYS_REDIRECT_PATH=https://meritboard.vercel.app/auth/callback`
   - `CONSENTKEYS_CLIENT_ID=ck_292674f59a7464fe2e9441574d96df92`
   - `CONSENTKEYS_CLIENT_SECRET=B2ZWNlDbPOWMBSh98iNkKjhcflJTANZcpENs1WGRRhc`
   - `CONSENTKEYS_ISSUER=https://consentkeys.com`
   - `SESSION_SECRET=<a-long-random-string>`
   - `SUPABASE_URL=https://<project>.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>`
   - `SUPABASE_JOBS_TABLE=jobs` (optional override)
   - `SUPABASE_CANDIDATES_TABLE=candidates` (optional override)
3. Create the Supabase tables using the SQL below (or via the Supabase dashboard) before testing writes:
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
4. Deploy with the Vercel CLI or dashboard:
   ```bash
   npm i -g vercel
   vercel --prod
   ```
   Vercel will install `requirements.txt` and serve `api/index.py` automatically.
5. Test the flow:
   - Visit `https://meritboard.vercel.app/` and click **Login with ConsentKeys**; you should be redirected to ConsentKeys and back to `/auth/callback` on success.
   - Post a candidate profile to `POST https://meritboard.vercel.app/api/candidates` with JSON from the API examples above; confirm the record appears in your Supabase tables.
   - While logged in, post a job to `POST https://meritboard.vercel.app/api/jobs` and verify it is stored and visible on the landing page and in Supabase.

## Quick readiness checklist
- ConsentKeys app registration includes `https://meritboard.vercel.app/auth/callback` as an authorized redirect URI and matches the `CONSENTKEYS_CLIENT_ID`/`CONSENTKEYS_CLIENT_SECRET` in your environment.
- Vercel environment variables include `APP_HOST=https://meritboard.vercel.app`, `CONSENTKEYS_REDIRECT_PATH=https://meritboard.vercel.app/auth/callback`, `SESSION_SECRET`, and your Supabase URL and service role key.
- Supabase tables (`jobs`, `candidates`) exist with the schema above so the API inserts succeed.
- `GET /health` returns `true` for both ConsentKeys and Supabase readiness once the environment variables are set in Vercel.

## API usage
- `POST /api/candidates` with JSON body:
  ```json
  {
    "region": "Vancouver Island",
    "skills": ["Python", "React"],
    "experience_years": 4,
    "desired_roles": ["Full Stack Developer"],
    "portfolio_link": "https://example.com"
  }
  ```

- `POST /api/jobs` (requires ConsentKeys session) with JSON body:
  ```json
  {
    "employer": "Inclusive Co-op",
    "title": "Data Analyst",
    "region": "Lower Mainland",
    "description": "Support evidence-based policy for WorkBC participants.",
    "incentive_eligible": true
  }
  ```

- `GET /api/jobs` and `GET /api/candidates` return the current Supabase-backed data.

## Notes
- The ConsentKeys discovery document is loaded from `CONSENTKEYS_ISSUER/.well-known/openid-configuration`.
- Keep demographic information out of candidate payloads to preserve meritocratic review before interviews.

## Supabase schema
Create two tables for persistence (text primary keys allow FastAPI to supply opaque IDs):

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

Use a Supabase service role key for full read/write API access from the backend.

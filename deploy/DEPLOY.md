# Deploying

Frontend on **Vercel**, backend on **Hugging Face Spaces**, both free, both
behind your own subdomain.

Spaces is the unusual choice and the deliberate one: the backend needs ~1 GB of
RAM for spaCy and the sentence-transformer, which is more than most free tiers
allow. Spaces gives 16 GB on the free CPU tier because it exists for exactly
this kind of workload.

Assumes `ats.example.com` for the app and `api.example.com` for the API —
substitute your own.

---

## 1. Backend → Hugging Face Spaces

1. Sign in at [huggingface.co](https://huggingface.co) (free, no card).
2. **New** → **Space**.
   - **Owner:** your username
   - **Space name:** `ats-resume-analyzer-api`
   - **License:** MIT
   - **SDK:** **Docker** → **Blank**
   - **Hardware:** CPU basic (free)
   - **Visibility:** Public — private Spaces aren't reachable without a token,
     which the browser can't supply.
3. Push this repository to the Space (it has its own git remote):

   ```bash
   git remote add space https://huggingface.co/spaces/<user>/ats-resume-analyzer-api
   git push space main
   ```

   The Space builds from the `Dockerfile` at the repository root.

4. Replace the Space's `README.md` with [`deploy/space-README.md`](space-README.md).
   The YAML frontmatter is what tells Spaces to use Docker and port 7860 — the
   Space will not start without it.

5. **Settings → Variables and secrets**, add:

   | Name | Kind | Value |
   | --- | --- | --- |
   | `SUPABASE_URL` | Variable | your project URL |
   | `SUPABASE_KEY` | **Secret** | your Supabase secret key |
   | `GROQ_API_KEY` | **Secret** | your Groq key |
   | `ALLOWED_ORIGINS` | Variable | `https://ats.example.com` |

   The two marked **Secret** must be secrets, not variables — variables are
   visible to anyone who can view the Space.

6. First build takes ~10 minutes (torch, then the models). When it finishes,
   check `https://<user>-ats-resume-analyzer-api.hf.space/api/v1/health` —
   it should report both models loaded.

---

## 2. Frontend → Vercel

1. Sign in at [vercel.com](https://vercel.com) with GitHub.
2. **Add New → Project** → import this repository.
3. **Root Directory: `web`** — this is the one setting that matters. Vercel
   defaults to the repository root, where there is no Next.js app.
4. Environment variables:

   | Name | Value |
   | --- | --- |
   | `NEXT_PUBLIC_SUPABASE_URL` | your project URL |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | your **publishable** key |
   | `NEXT_PUBLIC_API_URL` | `https://api.example.com` |

   All three are `NEXT_PUBLIC_*` and therefore shipped to the browser. Never
   put the Supabase secret key here.

5. **Deploy.**

---

## 3. Your subdomain

In your registrar or hosting control panel's **DNS / Zone Editor**:

| Type | Name | Points to |
| --- | --- | --- |
| CNAME | `ats` | `cname.vercel-dns.com` |
| CNAME | `api` | `<user>-ats-resume-analyzer-api.hf.space` |

Then register each domain with its host so certificates are issued:

- **Vercel:** Project → Settings → Domains → add `ats.example.com`
- **Spaces:** Settings → Custom domain → add `api.example.com`

DNS propagation is usually minutes, occasionally up to an hour.

---

## 4. Point Supabase at production

Auth redirects fail silently against the wrong origin, so this step is not
optional. **Authentication → URL Configuration**:

- **Site URL:** `https://ats.example.com`
- **Redirect URLs:** add `https://ats.example.com/auth/callback`

Keep `http://localhost:3000/**` in the redirect list if you still develop locally.

---

## 5. Check it

1. `https://api.example.com/api/v1/health` → both models loaded
2. `https://ats.example.com` → sign up, upload a resume, confirm it saves to history
3. Confirm a **rate limit** is enforced — the analyze endpoint allows 10/hour
   per caller by default. Without it, a public deployment lets anyone drain
   your Groq quota.

---

## Known behaviour in production

**Cold starts.** A Space that has been idle takes ~20–40s on the first request
while the models load. Subsequent requests are fast. The models are baked into
the image, so this is load time, not download time.

**PDF export works here.** WeasyPrint's native libraries are installed in the
Dockerfile, so the report endpoint that returns 503 on a bare Windows machine
works in this image.

**Rate limits are per-process and reset on restart.** That is correct for a
single container. Running more than one replica needs shared storage — point
`RATE_LIMIT_STORAGE_URI` at a Redis URL.

**Groq retires models.** If analyses start failing with `model_not_found`, set
`GROQ_MODEL` in the Space's variables to a current model; `scripts/check_setup.py`
lists the ones your key can use.

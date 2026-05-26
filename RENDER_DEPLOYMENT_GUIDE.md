# 🚀 DocSeva Final Deployment Guide

Follow these exact steps to get your project from `/home/diggerpuk/Projects/docseva_final_2/docseva_fixed` live on Render.

---

### Step 1: Push to GitHub

1. Go to [GitHub](https://github.com/new) and create a new **empty repository** (do not add a README or `.gitignore` when creating it).
2. Copy the URL of your new repository (e.g., `https://github.com/yourusername/docseva.git`).
3. Open your terminal, navigate to your project, and run these commands to push your code:

```bash
cd /home/diggerpuk/Projects/docseva_final_2/docseva_fixed
git remote add origin <PASTE_YOUR_GITHUB_URL_HERE>
git push -u origin main
```

---

### Step 2: Deploy on Render

1. Go to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Blueprint** (this is important because we configured everything in the `render.yaml` file).
3. Connect your GitHub account (if you haven't already) and select the repository you just created.
4. Click **Apply**.
5. Render will now automatically detect the `render.yaml` file and start creating:
   - Your PostgreSQL Database
   - Your Redis Instance
   - Your Celery Worker
   - Your Celery Beat Scheduler
   - Your Web Service

---

### Step 3: Set Required Environment Variables ⚠️ (Crucial)

Before the deploy finishes, you **must** set a few environment variables in Render, or the app will fail to load.

1. In your Render Dashboard, go to your new **DocSeva Web Service**.
2. Go to the **Environment** tab.
3. Update these specific variables:
   - `ALLOWED_HOSTS`: Set this to your Render URL (e.g., `docseva-something.onrender.com`).
   - `CSRF_TRUSTED_ORIGINS`: Set this to your Render URL starting with `https://` (e.g., `https://docseva-something.onrender.com`).
   - `PUBLIC_BASE_URL`: Same as above (e.g., `https://docseva-something.onrender.com`).
   - `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`: Fill these with your SMTP credentials (like SendGrid or Mailgun) so password resets work.

Once those are set, your app will finish deploying and be fully live and production-ready!

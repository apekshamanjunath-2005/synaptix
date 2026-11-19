# 🚀 Synaptix — Google Cloud Run Zero-Cost Deployment Guide

This guide details how to deploy **Synaptix Multi-Agent AI Personal Productivity Assistant** to **Google Cloud Run** within the permanent **₹0 Free Tier**, ensuring zero unexpected charges.

---

## 1. Google Cloud Run Permanent Free Tier Limits

Google Cloud provides a generous permanent monthly Free Tier for Cloud Run:

| Resource | Free Tier Monthly Allowance | Synaptix Typical Footprint | Safe Within Free Tier? |
| :--- | :--- | :--- | :--- |
| **Invocations / Requests** | **2,000,000 requests/month** | ~3,000 requests/month | ✅ **100% Free** |
| **Compute Time (vCPU)** | **360,000 vCPU-seconds/month** | ~3,000 vCPU-seconds/month | ✅ **100% Free** |
| **Memory Allocation** | **180,000 GiB-seconds/month** | ~1,500 GiB-seconds/month | ✅ **100% Free** |
| **Egress Bandwidth** | **1 GiB/month free** | < 200 MB/month | ✅ **100% Free** |

> [!IMPORTANT]
> To guarantee that horizontal scaling never incurs billing, deploy with `--max-instances 1` and `--cpu-throttling`. With CPU throttling enabled, compute time is only counted during active request processing, meaning idle containers cost **₹0**.

---

## 2. Pre-Deployment Prerequisites

1. Install Google Cloud SDK (`gcloud` CLI):
   ```bash
   gcloud --version
   ```
2. Log into your Google Cloud account:
   ```bash
   gcloud auth login
   ```
3. Set your active project ID:
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```
4. Enable required APIs (Free to enable):
   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com
   ```

---

## 3. Deployment Options

### Option A: Build and Deploy directly from Source (Recommended)

Google Cloud Run can build the container image automatically using Google Cloud Build and deploy it in a single command:

```bash
gcloud run deploy synaptix \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --concurrency 40 \
  --cpu 1 \
  --memory 512Mi \
  --cpu-throttling \
  --set-env-vars ENVIRONMENT=production,PORT=8080,DEFAULT_CITY=Bengaluru
```

### Option B: Local Docker Build & Artifact Registry

If you have Docker Desktop installed locally:

```bash
# 1. Build local container
docker build -t synaptix:v1 .

# 2. Test locally on port 8000
docker run -p 8000:8000 -e ENVIRONMENT=development synaptix:v1

# 3. Verify health
curl http://localhost:8000/api/health
```

---

## 4. Configuring Secrets & Environment Variables on Cloud Run

Set your production API keys securely without embedding them into Git or the Docker image:

```bash
gcloud run services update synaptix \
  --region us-central1 \
  --update-env-vars \
GEMINI_API_KEY="AIzaSy...",\
OPENWEATHERMAP_API_KEY="your_owm_key",\
MAX_DAILY_LLM_REQUESTS=100
```

> [!TIP]
> If you do not configure an `OPENWEATHERMAP_API_KEY` or `GEMINI_API_KEY`, Synaptix automatically operates in **Safe Zero-Cost Fallback Mode**, generating realistic weather metrics and offline multi-agent scheduling without raising errors.

---

## 5. Verifying Live Cloud Run Deployment

After deployment completes, `gcloud` will output your live HTTPS service URL:

```
Service URL: https://synaptix-xyz-uc.a.run.app
```

1. **Verify Health Endpoint:**
   ```bash
   curl https://synaptix-xyz-uc.a.run.app/api/health
   ```
2. **Access Web Dashboard:**
   Open `https://synaptix-xyz-uc.a.run.app` in your browser to access the complete Multi-Agent Productivity Assistant interface.
3. **Verify Zero-Cost Budget Quota:**
   Navigate to the **Budget & Telemetry** tab in the dashboard to inspect active ₹0 safeguards.

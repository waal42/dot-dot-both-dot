# Dot Dot Both Dot 

The official wedding website for **Hanka & Filip** (August 15, 2026).  
A Morse-code-themed site built with **Astro** and **Tailwind CSS**.

## ⚙️ Configuration

This project is **data-driven**. To update wedding details, schedule, or FAQs, edit this file:  
👉 `src/content/wedding/info.yaml`

## 🛠️ Quick Start

```sh
npm install
npm run dev
```

## 🚀 Deployment

Push to `main` and the site deploys automatically via GitHub Actions to the VPS.

### ⚠️ Environment Variables & GitHub Secrets

If you modify `PUBLIC_GOOGLE_SCRIPT_URL` or `DASHBOARD_API_TOKEN` in your `.env` file, you **MUST** update:
1. **GitHub Secrets:** Go to your GitHub repository -> *Settings* -> *Secrets and variables* -> *Actions* -> *Repository secrets* and update `PUBLIC_GOOGLE_SCRIPT_URL`. The static website compiler inside GitHub Actions embeds this URL at build-time.
2. **VPS configuration:** Update the `.env` file in the VPS directory.
3. **Local dev server:** Stop and restart the Astro server (`npm run dev`) to load the new `.env` variables.

---

### ❓ Questions?
If you're looking to adapt this or have questions about the Morse translation/audio logic, feel free to ask!

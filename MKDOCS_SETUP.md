# MkDocs Setup & Deployment Guide

## Quick Setup (5 minutes)

### 1. Install MkDocs

```bash
pip install -r requirements-mkdocs.txt
```

Or:
```bash
pip install mkdocs mkdocs-material
```

### 2. Preview Documentation

```bash
mkdocs serve
```

Visit **http://localhost:8000** in your browser.

The site will auto-reload as you edit markdown files.

### 3. Build Static Site

```bash
mkdocs build
```

This creates a `site/` directory with static HTML files.

## Directory Structure

```
docs/
├── index.md                 # Home page
├── getting-started/
│   ├── overview.md
│   ├── installation.md
│   └── quick-start.md
├── user-guide/
│   ├── uploading.md
│   ├── results.md
│   ├── collection.md
│   └── chat.md
├── api/
│   ├── introduction.md
│   ├── endpoints.md
│   ├── authentication.md
│   └── examples.md
├── architecture/
│   ├── system-design.md
│   ├── data-flow.md
│   ├── components.md
│   └── database.md
├── development/
│   ├── setup.md
│   ├── backend.md
│   ├── frontend.md
│   ├── testing.md
│   └── docker.md
└── deployment/
    ├── cloud-run.md
    └── docker.md

mkdocs.yml              # Configuration file
```

## Customization

### Change Theme

Edit `mkdocs.yml`:

```yaml
theme:
  name: material
  palette:
    primary: indigo      # Change primary color
    accent: indigo       # Change accent color
```

Popular colors: red, pink, purple, blue, cyan, teal, green, lime, yellow, orange, brown, gray

### Add Navigation Item

In `mkdocs.yml`:

```yaml
nav:
  - Home: index.md
  - New Section:
    - Page Title: path/to/file.md
```

### Customize Logo

```yaml
theme:
  logo: images/logo.png
  favicon: images/favicon.ico
```

## Deployment

### Option 1: GitHub Pages (Easiest)

```bash
# Install ghp-import
pip install ghp-import

# Build and deploy
mkdocs gh-deploy
```

Visit: `https://<username>.github.io/phonox`

### Option 2: Cloud Run (Same as Astro blog)

Create `Dockerfile`:
```dockerfile
FROM node:20-alpine

WORKDIR /app

RUN npm install -g http-server

COPY site/ ./

EXPOSE 8080

CMD ["http-server", "-p", "8080", "-c-1"]
```

Build and deploy:
```bash
mkdocs build

docker build -t phonox-docs .

gcloud run deploy phonox-docs \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Option 3: Netlify

1. Push to GitHub
2. Connect repo to Netlify
3. Set build command: `mkdocs build`
4. Set publish directory: `site`
5. Deploy!

### Option 4: Vercel

Create `vercel.json`:
```json
{
  "buildCommand": "pip install -r requirements-mkdocs.txt && mkdocs build",
  "outputDirectory": "site"
}
```

## Search

MkDocs includes built-in search. It's automatically indexed when you build:

```bash
mkdocs build
```

Search is included in the Material theme and works offline!

## Versioning

To add version selector:

```yaml
plugins:
  - search
  - offline
  - mike  # Install: pip install mike

extra:
  version:
    provider: mike
```

Use mike to publish versions:
```bash
pip install mike
mike deploy 1.3.2 latest
mike set-default latest
```

## Tips

### Writing Tips
- Use `!!! note` for admonitions (tip, warning, danger, etc.)
- Use ` ```language ` for syntax highlighting
- Use `[link text](url)` for links
- Use `==highlight==` for highlighting
- Use `~~strikethrough~~` for strikethrough

### Performance
- Keep markdown files small (<10KB)
- Use relative links: `../api/endpoints.md`
- Avoid large images (compress them)
- Use LaTeX for math: `$$ x = \frac{-b \pm \sqrt{b^2-4ac}}{2a} $$`

### SEO
```markdown
---
description: Page description for search engines
keywords: keyword1, keyword2
---
```

## Troubleshooting

**Build fails with "theme not found"?**
```bash
pip install mkdocs-material
```

**Port 8000 already in use?**
```bash
mkdocs serve -a localhost:8001
```

**Search not working?**
```bash
rm -rf site/
mkdocs build
mkdocs serve
```

**Links broken after deploying?**
- Use relative paths: `../other-page.md`
- Don't use leading slashes: `/api/docs.md` ❌ → `api/docs.md` ✅

## Next Steps

1. ✅ Run locally: `mkdocs serve`
2. ✅ Edit markdown files in `docs/`
3. ✅ Deploy to GitHub Pages: `mkdocs gh-deploy`
4. ✅ Share documentation URL with team

## Resources

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [Markdown Guide](https://www.markdownguide.org/)

---

Happy documenting! 📚

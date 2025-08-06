# Sumbird Newsletter

A minimal, responsive newsletter website built with GitHub Pages and TailwindCSS.

## Overview

This repository contains the static website for the Sumbird Newsletter, which displays daily AI news and updates curated by the [Sumbird pipeline](https://github.com/dshayan/sumbird).

## Features

- 🎨 **Clean Design**: Minimal, responsive layout using TailwindCSS
- 📱 **Mobile-First**: Optimized for all device sizes
- 📡 **RSS Feed**: Full-content RSS feed for subscribers
- 🔗 **Permalink Support**: Individual pages for each newsletter issue
- ⚡ **Fast Loading**: Static site with CDN-delivered assets
- 🔍 **SEO Optimized**: Proper meta tags and structured content

## Structure

```
sumbird-web/
├── index.html              # Homepage with recent posts
├── posts/                  # Individual newsletter posts
│   ├── template.html       # Template for generating posts
│   └── YYYY-MM-DD.html     # Generated post files
├── feed.xml                # RSS feed
├── assets/
│   └── style.css          # Custom CSS overrides
└── README.md              # This file
```

## How It Works

1. The [Sumbird pipeline](https://github.com/dshayan/sumbird) generates HTML summaries in `data/summary/`
2. The newsletter generator processes these files and creates:
   - Individual post pages in `posts/`
   - Updated homepage with recent posts
   - RSS feed with the latest 20 posts
3. Changes are automatically committed and pushed to trigger GitHub Pages deployment

## Newsletter Website

The pipeline automatically generates a newsletter website hosted on GitHub Pages at: https://dshayan.github.io/sumbird/

### Features
- 🎨 **Clean Design**: Minimal, responsive layout using TailwindCSS
- 📱 **Mobile-First**: Optimized for all device sizes  
- 📡 **RSS Feed**: Full-content RSS feed at https://dshayan.github.io/sumbird/feed.xml
- 🔗 **Permalink Support**: Individual pages for each newsletter issue
- ⚡ **Fast Loading**: Static site with CDN-delivered assets

### Manual Newsletter Generation

To generate the newsletter manually:

```bash
# Generate newsletter without committing
python scripts/generate_newsletter.py --no-commit

# Generate and auto-commit to trigger GitHub Pages deployment
python scripts/generate_newsletter.py
```

### Local Development

To preview the newsletter locally:

```bash
# Serve the docs directory locally
cd docs
python -m http.server 8000

# Visit http://localhost:8000
```
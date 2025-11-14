#!/usr/bin/env python3
"""
Newsletter Generator for Sumbird - Converts summary HTML files to GitHub Pages newsletter.

This module:
1. Reads HTML summary files from data/summary/
2. Converts them to newsletter posts in the docs directory
3. Updates the homepage with recent posts
4. Generates RSS feed with latest 20 posts
5. Generates XML sitemap for search engines
6. Generates robots.txt for crawler directives
7. Commits and pushes changes to GitHub
"""
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

from config import (
    SITE_BASE_URL, SUMMARY_DIR, TRANSLATED_DIR,
    RSS_FEED_TITLE, RSS_FEED_DESCRIPTION, RSS_FEED_LANGUAGE,
    RSS_FEED_TTL, RSS_FEED_GENERATOR
)
from utils.date_utils import get_now
from utils.file_utils import read_file
from utils.logging_utils import log_error, log_info, log_success
from utils.template_utils import TemplateManager


class NewsletterGenerator:
    """Generates newsletter website from summary HTML files."""
    
    def __init__(self, docs_path: str = None, 
                 language: str = "en", source_dir: str = None):
        """Initialize the newsletter generator.
        
        Args:
            docs_path: Path to the docs directory. 
                      Defaults to docs/ in the current project.
            language: Language code ("en" for English, "fa" for Farsi).
            source_dir: Source directory for content files (overrides default based on language).
        """
        # Set language properties
        self.language = language
        self.is_farsi = language == "fa"
        
        # Determine base docs path
        if docs_path is None:
            # Default to docs directory in current project
            current_dir = Path(__file__).parent.parent
            base_docs_path = current_dir / "docs"
        else:
            base_docs_path = Path(docs_path)
        
        # Set language-aware paths
        if self.is_farsi:
            self.docs_path = base_docs_path / "fa"
            self.source_dir = source_dir or TRANSLATED_DIR
            self.posts_dir = base_docs_path / "fa" / "news"
        else:
            self.docs_path = base_docs_path / "en"
            self.source_dir = source_dir or SUMMARY_DIR
            self.posts_dir = base_docs_path / "en" / "news"
        
        # Templates are now in language-specific directories
        self.template_path = self.docs_path / "templates" / "template.html"
        self.homepage_path = self.docs_path / "index.html"
        self.feed_path = self.docs_path / "feed.xml"
        self.sitemap_path = self.docs_path / "sitemap.xml"
        
        # Initialize template manager for external CSS system with language context
        # Components are now loaded from language-specific directories
        self.template_manager = TemplateManager(
            str(base_docs_path), 
            language=self.language
        )
        
        # Ensure posts directory exists
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate paths
        if not self.docs_path.exists():
            raise FileNotFoundError(f"Docs directory not found at: {self.docs_path}")
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found at: {self.template_path}")
    
    def get_summary_files(self) -> List[Tuple[str, Path]]:
        """Get all content HTML files sorted by date (newest first).
        
        Returns:
            List of (date_str, file_path) tuples sorted by date descending.
        """
        source_dir = Path(self.source_dir)
        if not source_dir.exists():
            log_error("NewsletterGenerator", f"Source directory not found: {source_dir}")
            return []
        
        files = []
        for file_path in source_dir.glob("X-*.html"):
            # Extract date from filename: X-YYYY-MM-DD.html
            match = re.match(r'X-(\d{4}-\d{2}-\d{2})\.html', file_path.name)
            if match:
                date_str = match.group(1)
                files.append((date_str, file_path))
        
        # Sort by date descending (newest first)
        files.sort(key=lambda x: x[0], reverse=True)
        return files
    
    def parse_summary_html(self, file_path: Path) -> Dict[str, str]:
        """Parse summary HTML file and extract content.
        
        Args:
            file_path: Path to the summary HTML file.
            
        Returns:
            Dictionary with parsed content including title, sections, etc.
        """
        try:
            content = read_file(str(file_path))
            if not content:
                return {}
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract title
            title_elem = soup.find('h1')
            title = title_elem.get_text().strip() if title_elem else "AI Updates"
            
            # Extract date from title (e.g., "AI Updates on 2025-05-05")
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', title)
            date_str = date_match.group(1) if date_match else ""
            
            # Clean up the HTML content for display
            # Remove the h1 title since we'll add our own
            if title_elem:
                title_elem.decompose()
            
            # Get the cleaned HTML content
            body_html = str(soup).strip()
            
            return {
                'title': title,
                'date_str': date_str,
                'content': body_html,
                'description': self._extract_description(soup)
            }
            
        except Exception as e:
            log_error("NewsletterGenerator", f"Error parsing {file_path}", e)
            return {}
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract a description from the content for meta tags.
        
        Args:
            soup: BeautifulSoup object of the content.
            
        Returns:
            Description string (first paragraph or similar).
        """
        # Try to get first paragraph or first list item
        first_p = soup.find('p')
        if first_p:
            return first_p.get_text().strip()[:160] + "..."
        
        first_li = soup.find('li')
        if first_li:
            return first_li.get_text().strip()[:160] + "..."
        
        return "AI news and vibes from Twitter"
    
    def generate_post_page(self, date_str: str, content_data: Dict[str, str]) -> bool:
        """Generate individual post page using external CSS template.
        
        Args:
            date_str: Date string in YYYY-MM-DD format.
            content_data: Parsed content data from summary file.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            if not self.template_manager:
                log_error("NewsletterGenerator", "Template manager not initialized for external CSS mode")
                return False
            
            # Generate HTML using template manager
            title = content_data.get('title', 'AI Updates')
            content = content_data.get('content', '')
            description = content_data.get('description', '')
            
            post_html = self.template_manager.generate_post_html(
                title=title,
                content=content,
                description=description,
                date_str=date_str
            )
            
            if not post_html:
                log_error("NewsletterGenerator", f"Failed to generate HTML for {date_str}")
                return False
            
            # Write post file in directory (for clean URLs without .html extension)
            post_dir = self.posts_dir / date_str
            post_dir.mkdir(parents=True, exist_ok=True)
            post_file = post_dir / "index.html"
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(post_html)
            
            log_info("NewsletterGenerator", f"Generated post: {post_file.name}")
            return True
            
        except Exception as e:
            log_error("NewsletterGenerator", f"Error generating post for {date_str}", e)
            return False
    
    def _generate_posts_html(self, posts: List[Tuple[str, Dict[str, str]]]) -> str:
        """Generate HTML for a list of posts.
        
        Args:
            posts: List of (date_str, content_data) tuples.
            
        Returns:
            HTML string with all posts, including dividers between posts.
        """
        posts_html = ""
        for date_str, content_data in posts:
            divider_html = '<div class="border-t"></div>' if posts_html else ''
            # Use language-specific path for post links (from language homepage to news subdirectory, no .html extension)
            post_link = f"news/{date_str}"
            
            post_html = f'''
            {divider_html}
            <article>
                <h1>
                    <a href="{post_link}">
                        {content_data.get('title', 'AI Updates')}
                    </a>
                </h1>
                <div class="prose">
                    {content_data.get('content', '')}
                </div>
            </article>
            '''
            posts_html += post_html
        return posts_html
    
    def generate_homepage(self, recent_posts: List[Tuple[str, Dict[str, str]]]) -> bool:
        """Generate homepage with recent posts and simple pagination.
        
        Args:
            recent_posts: List of (date_str, content_data) tuples for recent posts.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Generate posts HTML for first page (10 posts - more reasonable for a newsletter)
            posts_per_page = 10
            first_page_posts = recent_posts[:posts_per_page]
            posts_html = self._generate_posts_html(first_page_posts)
            
            # Generate simple pagination links
            total_posts = len(recent_posts)
            total_pages = (total_posts + posts_per_page - 1) // posts_per_page
            
            # Generate pagination using component
            pagination_html = self.template_manager.load_pagination(
                current_page=1,
                total_pages=total_pages,
                base_path=""
            )
            
            # Use template manager to generate complete homepage
            homepage_html = self.template_manager.generate_index_html(
                posts_content=posts_html,
                pagination_script=pagination_html,  # Now contains pagination HTML instead of JS
                template_name="page-template.html"
            )
            
            if not homepage_html:
                log_error("NewsletterGenerator", "Failed to generate homepage HTML")
                return False
            
            # Write homepage
            with open(self.homepage_path, 'w', encoding='utf-8') as f:
                f.write(homepage_html)
            
            # Generate additional pages if needed
            if total_pages > 1:
                self._generate_pagination_pages(recent_posts, posts_per_page, total_pages)
            
            log_info("NewsletterGenerator", f"Updated homepage with {len(first_page_posts)} posts ({total_pages} pages total)")
            return True
                
        except Exception as e:
            log_error("NewsletterGenerator", f"Error generating homepage", e)
            return False
    
    def _generate_pagination_pages(self, recent_posts: List[Tuple[str, Dict[str, str]]], posts_per_page: int, total_pages: int) -> None:
        """Generate additional pagination pages.
        
        Args:
            recent_posts: All posts data.
            posts_per_page: Number of posts per page.
            total_pages: Total number of pages.
        """
        try:
            pages_generated = 0
            for page_num in range(2, total_pages + 1):
                start_idx = (page_num - 1) * posts_per_page
                end_idx = start_idx + posts_per_page
                page_posts = recent_posts[start_idx:end_idx]
                
                # Generate posts HTML for this page
                posts_html = self._generate_posts_html(page_posts)
                
                # Generate pagination using component
                pagination_html = self.template_manager.load_pagination(
                    current_page=page_num,
                    total_pages=total_pages,
                    base_path=""
                )
                
                # Generate complete page HTML with adjusted paths for subdirectory
                page_html = self.template_manager.generate_index_html(
                    posts_content=posts_html,
                    pagination_script=pagination_html,
                    template_name="page-template.html"
                )
                
                if page_html:
                    # Save pages directly in docs directory
                    page_file = self.docs_path / f"page{page_num}.html"
                    with open(page_file, 'w', encoding='utf-8') as f:
                        f.write(page_html)
                    pages_generated += 1
            
            # Log summary of pages generated
            if pages_generated > 0:
                log_info("NewsletterGenerator", f"Generated {pages_generated} pagination pages")
                
        except Exception as e:
            log_error("NewsletterGenerator", f"Error generating pagination pages", e)
    
    def generate_rss_feed(self, recent_posts: List[Tuple[str, Dict[str, str]]]) -> bool:
        """Generate RSS feed programmatically with recent posts.
        
        Uses feedgen library to create a valid RSS 2.0 feed with the latest 20 posts.
        The feed is generated from scratch on each run to ensure consistency and accuracy.
        
        Args:
            recent_posts: List of (date_str, content_data) tuples for recent posts, 
                         sorted by date descending (newest first).
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Feed and homepage URLs include language subdirectory
            if self.is_farsi:
                feed_url = f"{SITE_BASE_URL}/fa/feed.xml"
                homepage_url = f"{SITE_BASE_URL}/fa/"
            else:
                feed_url = f"{SITE_BASE_URL}/en/feed.xml"
                homepage_url = f"{SITE_BASE_URL}/en/"
            
            # Determine RSS metadata based on language
            if self.is_farsi:
                rss_title = f"{RSS_FEED_TITLE} - فارسی"
                rss_description = "اخبار و تحلیل‌های هوش مصنوعی از توییتر"
                rss_language = "fa-ir"
            else:
                rss_title = RSS_FEED_TITLE
                rss_description = RSS_FEED_DESCRIPTION
                rss_language = RSS_FEED_LANGUAGE
            
            # Create feed generator
            fg = FeedGenerator()
            fg.title(rss_title)
            fg.description(rss_description)
            fg.link(href=homepage_url, rel='alternate')
            fg.link(href=feed_url, rel='self')
            fg.language(rss_language)
            fg.generator(RSS_FEED_GENERATOR)
            fg.ttl(str(RSS_FEED_TTL))
            
            # Set build date and publication date
            now = get_now()
            fg.lastBuildDate(now)
            fg.pubDate(now)
            
            # Generate items for the last 20 posts
            # Note: feedgen writes entries in reverse order, so we add oldest first
            # to get newest-first in the final RSS feed (RSS best practice)
            items_count = 0
            for date_str, content_data in reversed(recent_posts[:20]):
                try:
                    # Create entry
                    fe = fg.add_entry()
                    
                    # Add title
                    title = content_data.get('title', 'AI Updates')
                    fe.title(title)
                    
                    # Clean and add description (feedgen handles CDATA automatically)
                    content = content_data.get('content', '')
                    soup = BeautifulSoup(content, 'html.parser')
                    cleaned_content = self._clean_html_for_rss(soup)
                    fe.description(cleaned_content)
                    
                    # Add link and GUID with language-specific path (no .html extension)
                    if self.is_farsi:
                        post_url = f"{SITE_BASE_URL}/fa/news/{date_str}"
                    else:
                        post_url = f"{SITE_BASE_URL}/en/news/{date_str}"
                    fe.link(href=post_url)
                    fe.guid(post_url)
                    
                    # Add publication date (convert date_str to datetime with UTC timezone)
                    try:
                        post_date = datetime.strptime(date_str, "%Y-%m-%d")
                        post_date = post_date.replace(tzinfo=timezone.utc)
                        fe.pubDate(post_date)
                    except ValueError:
                        log_error("NewsletterGenerator", f"Invalid date format: {date_str}")
                        continue
                    
                    items_count += 1
                    
                except Exception as e:
                    log_error("NewsletterGenerator", f"Error adding RSS item for {date_str}", e)
                    continue
            
            # Write RSS feed file
            fg.rss_file(str(self.feed_path), pretty=True)
            
            log_success("NewsletterGenerator", 
                       f"Generated RSS feed with {items_count} items at {self.feed_path}")
            return True
            
        except Exception as e:
            log_error("NewsletterGenerator", f"Error generating RSS feed", e)
            return False
    
    def _clean_html_for_rss(self, soup: BeautifulSoup) -> str:
        """Clean HTML content for RSS feed.
        
        Args:
            soup: BeautifulSoup object of the content.
            
        Returns:
            Cleaned HTML string suitable for RSS.
        """
        # Keep basic formatting but clean up complex elements
        for elem in soup.find_all(['script', 'style']):
            elem.decompose()
        
        return str(soup)
    
    def _get_existing_posts(self) -> List[str]:
        """Get all existing post dates from the posts directory.
        
        Returns:
            List of date strings (YYYY-MM-DD) sorted by date descending.
        """
        if not self.posts_dir.exists():
            return []
        
        dates = []
        for post_dir in self.posts_dir.iterdir():
            if post_dir.is_dir():
                # Check if it's a date directory (YYYY-MM-DD format)
                match = re.match(r'(\d{4}-\d{2}-\d{2})', post_dir.name)
                if match and (post_dir / "index.html").exists():
                    dates.append(match.group(1))
        
        # Sort by date descending (newest first)
        dates.sort(reverse=True)
        return dates
    
    def _get_pagination_pages(self) -> List[int]:
        """Get all existing pagination page numbers.
        
        Returns:
            List of page numbers (excluding page 1 which is the homepage).
        """
        if not self.docs_path.exists():
            return []
        
        pages = []
        for page_file in self.docs_path.glob("page*.html"):
            match = re.match(r'page(\d+)\.html', page_file.name)
            if match:
                pages.append(int(match.group(1)))
        
        pages.sort()
        return pages
    
    def generate_sitemap(self, recent_posts: List[Tuple[str, Dict[str, str]]]) -> bool:
        """Generate XML sitemap for search engines.
        
        Args:
            recent_posts: List of (date_str, content_data) tuples for all posts.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Get all existing posts (from filesystem, not just recent)
            all_post_dates = self._get_existing_posts()
            
            # Get pagination pages
            pagination_pages = self._get_pagination_pages()
            
            # Determine base URL for this language
            if self.is_farsi:
                base_url = f"{SITE_BASE_URL}/fa"
            else:
                base_url = f"{SITE_BASE_URL}/en"
            
            # Create sitemap root
            urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
            
            # Add homepage (highest priority)
            url_elem = ET.SubElement(urlset, "url")
            ET.SubElement(url_elem, "loc").text = f"{base_url}/"
            ET.SubElement(url_elem, "lastmod").text = get_now().strftime("%Y-%m-%d")
            ET.SubElement(url_elem, "changefreq").text = "daily"
            ET.SubElement(url_elem, "priority").text = "1.0"
            
            # Add RSS feed
            url_elem = ET.SubElement(urlset, "url")
            ET.SubElement(url_elem, "loc").text = f"{base_url}/feed.xml"
            ET.SubElement(url_elem, "lastmod").text = get_now().strftime("%Y-%m-%d")
            ET.SubElement(url_elem, "changefreq").text = "daily"
            ET.SubElement(url_elem, "priority").text = "0.3"
            
            # Add all post pages
            for date_str in all_post_dates:
                url_elem = ET.SubElement(urlset, "url")
                ET.SubElement(url_elem, "loc").text = f"{base_url}/news/{date_str}"
                
                # Try to get lastmod from post file modification time
                post_file = self.posts_dir / date_str / "index.html"
                if post_file.exists():
                    mod_time = datetime.fromtimestamp(
                        post_file.stat().st_mtime, tz=timezone.utc
                    )
                    ET.SubElement(url_elem, "lastmod").text = mod_time.strftime("%Y-%m-%d")
                else:
                    ET.SubElement(url_elem, "lastmod").text = date_str
                
                ET.SubElement(url_elem, "changefreq").text = "weekly"
                ET.SubElement(url_elem, "priority").text = "0.8"
            
            # Add pagination pages
            for page_num in pagination_pages:
                url_elem = ET.SubElement(urlset, "url")
                ET.SubElement(url_elem, "loc").text = f"{base_url}/page{page_num}.html"
                
                # Try to get lastmod from page file modification time
                page_file = self.docs_path / f"page{page_num}.html"
                if page_file.exists():
                    mod_time = datetime.fromtimestamp(
                        page_file.stat().st_mtime, tz=timezone.utc
                    )
                    ET.SubElement(url_elem, "lastmod").text = mod_time.strftime("%Y-%m-%d")
                else:
                    ET.SubElement(url_elem, "lastmod").text = get_now().strftime("%Y-%m-%d")
                
                ET.SubElement(url_elem, "changefreq").text = "weekly"
                ET.SubElement(url_elem, "priority").text = "0.5"
            
            # Create XML tree and write to file
            tree = ET.ElementTree(urlset)
            
            # Pretty print with indent (Python 3.9+)
            try:
                ET.indent(tree, space="  ")
            except AttributeError:
                # Fallback for Python < 3.9 - XML will still be valid, just not pretty-printed
                pass
            
            with open(self.sitemap_path, 'wb') as f:
                tree.write(f, encoding='utf-8', xml_declaration=True)
            
            log_success("NewsletterGenerator", 
                       f"Generated sitemap with {len(all_post_dates)} posts, "
                       f"{len(pagination_pages)} pagination pages at {self.sitemap_path}")
            return True
            
        except Exception as e:
            log_error("NewsletterGenerator", f"Error generating sitemap", e)
            return False
    
    @staticmethod
    def generate_robots_txt(base_docs_path: Path) -> bool:
        """Generate robots.txt file at the root of docs directory.
        
        Args:
            base_docs_path: Path to the base docs directory.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            robots_path = base_docs_path / "robots.txt"
            
            robots_content = f"""User-agent: *
Allow: /
Allow: /en/
Allow: /fa/
Allow: /en/news/
Allow: /fa/news/
Disallow: /logs/
Disallow: /assets/components/

# Sitemaps
Sitemap: {SITE_BASE_URL}/en/sitemap.xml
Sitemap: {SITE_BASE_URL}/fa/sitemap.xml
"""
            
            with open(robots_path, 'w', encoding='utf-8') as f:
                f.write(robots_content)
            
            log_success("NewsletterGenerator", f"Generated robots.txt at {robots_path}")
            return True
            
        except Exception as e:
            log_error("NewsletterGenerator", f"Error generating robots.txt", e)
            return False
    
    def commit_and_push(self) -> bool:
        """Commit and push changes to the repository.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Change to project root (both en/ and fa/ are subdirectories of docs/)
            # So we need to go up two levels: en/ or fa/ -> docs/ -> project root
            project_root = self.docs_path.parent.parent
            os.chdir(project_root)
            
            # Check if there are changes to commit in docs/ (after content generation)
            result = subprocess.run(['git', 'status', '--porcelain', 'docs/'], 
                                  capture_output=True, text=True, check=True)
            if not result.stdout.strip():
                log_info("NewsletterGenerator", "No changes to commit")
                return True
            
            # Add docs directory changes
            subprocess.run(['git', 'add', 'docs/'], check=True, capture_output=True)
            
            # Commit with timestamp
            commit_message = f"Update newsletter - {get_now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True, capture_output=True)
            
            # Push to origin
            subprocess.run(['git', 'push', 'origin', 'main'], check=True, capture_output=True)
            
            log_success("NewsletterGenerator", "Successfully committed and pushed changes")
            return True
            
        except subprocess.CalledProcessError as e:
            log_error("NewsletterGenerator", f"Git operation failed: {e}")
            return False
        except Exception as e:
            log_error("NewsletterGenerator", f"Error in commit and push", e)
            return False
    
    def generate_newsletter(self, auto_commit: bool = True, force_regenerate: bool = False) -> bool:
        """Generate the complete newsletter from summary files.
        
        Args:
            auto_commit: Whether to automatically commit and push changes.
            force_regenerate: Whether to regenerate existing posts (useful for template updates).
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            log_info("NewsletterGenerator", "Starting newsletter generation...")
            
            # Get all summary files
            summary_files = self.get_summary_files()
            if not summary_files:
                log_error("NewsletterGenerator", "No summary files found")
                return False
            
            log_info("NewsletterGenerator", f"Found {len(summary_files)} summary files")
            
            # Parse and generate posts
            recent_posts = []
            generated_count = 0
            skipped_count = 0
            
            for date_str, file_path in summary_files:
                # Parse summary content
                content_data = self.parse_summary_html(file_path)
                if not content_data:
                    log_error("NewsletterGenerator", f"Failed to parse {file_path}")
                    continue
                
                # Check if post already exists (now in directory structure)
                post_dir = self.posts_dir / date_str
                post_file = post_dir / "index.html"
                if post_file.exists() and not force_regenerate:
                    skipped_count += 1
                else:
                    # Generate new post or regenerate existing one
                    action = "Regenerating" if post_file.exists() else "Generating"
                    log_info("NewsletterGenerator", f"{action} post: {date_str}")
                    if self.generate_post_page(date_str, content_data):
                        generated_count += 1
                
                recent_posts.append((date_str, content_data))
            
            # Log summary of skipped posts
            if skipped_count > 0:
                log_info("NewsletterGenerator", f"Skipped {skipped_count} existing posts")
            
            # Generate homepage with recent posts
            if not self.generate_homepage(recent_posts):
                return False
            
            # Generate RSS feed
            if not self.generate_rss_feed(recent_posts):
                return False
            
            # Generate sitemap
            if not self.generate_sitemap(recent_posts):
                return False
            
            log_success("NewsletterGenerator", 
                       f"Generated {generated_count} new posts, updated homepage, RSS feed, and sitemap")
            
            # Commit and push if requested
            if auto_commit:
                return self.commit_and_push()
            
            return True
            
        except Exception as e:
            log_error("NewsletterGenerator", f"Error in newsletter generation", e)
            return False


def generate_newsletter(force_regenerate: bool = False, language: str = "en", verbose: bool = True, auto_commit: bool = True):
    """Main function to generate newsletter. Can be called from pipeline or standalone.
    
    Args:
        force_regenerate: Whether to regenerate existing posts.
        language: Language code ("en" or "fa").
        verbose: Whether to log verbose messages.
        auto_commit: Whether to automatically commit and push changes.
                    Note: When generating both languages, only commit after the last one.
    """
    try:
        generator = NewsletterGenerator(language=language)
        # Don't auto-commit in generate_newsletter - we'll handle it here if needed
        success = generator.generate_newsletter(force_regenerate=force_regenerate, auto_commit=False)
        
        # Generate robots.txt once (at root of docs, same for all languages)
        # Only generate if we're generating English (first language typically)
        if language == "en":
            base_docs_path = generator.docs_path.parent  # Go from en/ to docs/
            NewsletterGenerator.generate_robots_txt(base_docs_path)
        
        # Commit and push if requested (typically only after both languages are done)
        if auto_commit and success:
            generator.commit_and_push()
        
        if verbose:
            if success:
                log_success("NewsletterGenerator", f"Newsletter generation completed successfully ({language})")
            else:
                log_error("NewsletterGenerator", f"Newsletter generation failed ({language})")
        
        return success
        
    except Exception as e:
        if verbose:
            log_error("NewsletterGenerator", f"Error in generate function ({language})", e)
        return False


if __name__ == "__main__":
    import sys
    
    # Ensure environment is loaded when running standalone
    from utils import env_utils
    if not env_utils.env_vars:
        env_utils.load_environment()
    
    # Check for force regenerate flag
    force_regenerate = "--force" in sys.argv or "-f" in sys.argv
    
    # Check for language flag
    language = "en"  # default
    if "--fa" in sys.argv or "--farsi" in sys.argv:
        language = "fa"
    elif "--en" in sys.argv or "--english" in sys.argv:
        language = "en"
    
    success = generate(force_regenerate=force_regenerate, language=language)
    exit(0 if success else 1)
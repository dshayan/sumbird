#!/usr/bin/env python3
"""
Newsletter Generator for Sumbird - Converts summary HTML files to GitHub Pages newsletter.

This module:
1. Reads HTML summary files from data/summary/
2. Converts them to newsletter posts in the sumbird-web repository
3. Updates the homepage with recent posts
4. Generates RSS feed with latest 20 posts
5. Commits and pushes changes to GitHub
"""
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from config import SUMMARY_DIR, get_date_str
from utils.logging_utils import log_error, log_info, log_success
from utils.date_utils import format_datetime, get_now
from utils.file_utils import read_file
from utils.template_utils import TemplateManager


class NewsletterGenerator:
    """Generates newsletter website from summary HTML files."""
    
    def __init__(self, docs_path: str = None, use_external_css: bool = True):
        """Initialize the newsletter generator.
        
        Args:
            docs_path: Path to the docs directory. 
                      Defaults to docs/ in the current project.
            use_external_css: If True, use external CSS and component-based templates.
                             If False, use the legacy embedded CSS templates (deprecated).
        """
        if docs_path is None:
            # Default to docs directory in current project
            current_dir = Path(__file__).parent.parent
            docs_path = current_dir / "docs"
        
        self.docs_path = Path(docs_path)
        self.posts_dir = self.docs_path / "posts"
        self.use_external_css = use_external_css
        self.template_path = self.posts_dir / "template.html"
        self.homepage_path = self.docs_path / "index.html"
        self.feed_path = self.docs_path / "feed.xml"
        
        # Initialize template manager for external CSS system
        self.template_manager = TemplateManager(str(docs_path))
        
        # Validate paths
        if not self.docs_path.exists():
            raise FileNotFoundError(f"Docs directory not found at: {self.docs_path}")
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found at: {self.template_path}")
    
    def get_summary_files(self) -> List[Tuple[str, Path]]:
        """Get all summary HTML files sorted by date (newest first).
        
        Returns:
            List of (date_str, file_path) tuples sorted by date descending.
        """
        summary_dir = Path(SUMMARY_DIR)
        if not summary_dir.exists():
            log_error("Newsletter Generator", f"Summary directory not found: {summary_dir}")
            return []
        
        files = []
        for file_path in summary_dir.glob("X-*.html"):
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
            log_error("Newsletter Generator", f"Error parsing {file_path}", e)
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
        
        return "Daily AI news and updates curated by Sumbird"
    
    def format_date(self, date_str: str) -> Dict[str, str]:
        """Format date string into various formats.
        
        Args:
            date_str: Date in YYYY-MM-DD format.
            
        Returns:
            Dictionary with various date formats.
        """
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return {
                'iso_date': date_str,
                'formatted_date': dt.strftime("%B %d, %Y"),
                'rss_date': dt.strftime("%a, %d %b %Y %H:%M:%S +0000"),
                'display_date': dt.strftime("%b %d, %Y")
            }
        except ValueError:
            return {
                'iso_date': date_str,
                'formatted_date': date_str,
                'rss_date': date_str,
                'display_date': date_str
            }
    
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
                log_error("Newsletter Generator", "Template manager not initialized for external CSS mode")
                return False
            
            # Generate HTML using template manager
            title = content_data.get('title', 'AI Updates')
            content = content_data.get('content', '')
            description = content_data.get('description', '')
            
            post_html = self.template_manager.generate_post_html(
                title=title,
                content=content,
                description=description
            )
            
            if not post_html:
                log_error("Newsletter Generator", f"Failed to generate HTML for {date_str}")
                return False
            
            # Write post file
            post_file = self.posts_dir / f"{date_str}.html"
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(post_html)
            
            log_info("Newsletter Generator", f"Generated post: {post_file.name}")
            return True
            
        except Exception as e:
            log_error("Newsletter Generator", f"Error generating post for {date_str}", e)
            return False


    
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
            posts_html = ""
            
            for date_str, content_data in first_page_posts:
                # Add divider for all posts except the first one
                divider_html = '<div class="border-t"></div>' if posts_html else ''
                
                post_html = f'''
                {divider_html}
                <article>
                    <h1>
                        <a href="posts/{date_str}.html">
                            {content_data.get('title', 'AI Updates')}
                        </a>
                    </h1>
                    <div class="prose">
                        {content_data.get('content', '')}
                    </div>
                </article>
                '''
                posts_html += post_html
            
            # Generate simple pagination links
            total_posts = len(recent_posts)
            total_pages = (total_posts + posts_per_page - 1) // posts_per_page
            
            pagination_html = ""
            if total_pages > 1:
                pagination_html = '''
                <div class="pagination-container">
                    <div class="pagination-links">
                        <span class="pagination-link current">1</span>
                '''
                
                # Add links to other pages
                for page in range(2, min(6, total_pages + 1)):  # Show up to 5 pages
                    pagination_html += f'''
                        <a href="page{page}.html" class="pagination-link">{page}</a>
                    '''
                
                if total_pages > 5:
                    pagination_html += '''
                        <span class="pagination-dots">...</span>
                        <a href="page{}.html" class="pagination-link">{}</a>
                    '''.format(total_pages, total_pages)
                
                if total_pages > 1:
                    pagination_html += '''
                        <a href="page2.html" class="pagination-next">Next →</a>
                    '''
                
                pagination_html += '''
                    </div>
                            </div>
                '''
            
            # Use template manager to generate complete homepage
            homepage_html = self.template_manager.generate_index_html(
                posts_content=posts_html,
                pagination_script=pagination_html,  # Now contains pagination HTML instead of JS
                template_name="page-template.html"
            )
            
            if not homepage_html:
                log_error("Newsletter Generator", "Failed to generate homepage HTML")
                return False
            
            # Write homepage
            with open(self.homepage_path, 'w', encoding='utf-8') as f:
                f.write(homepage_html)
            
            # Generate additional pages if needed
            if total_pages > 1:
                self._generate_pagination_pages(recent_posts, posts_per_page, total_pages)
            
            log_info("Newsletter Generator", f"Updated homepage with {len(first_page_posts)} posts ({total_pages} pages total)")
            return True
                
        except Exception as e:
            log_error("Newsletter Generator", f"Error generating homepage", e)
            return False
    
    def _generate_pagination_pages(self, recent_posts: List[Tuple[str, Dict[str, str]]], posts_per_page: int, total_pages: int) -> None:
        """Generate additional pagination pages.
        
        Args:
            recent_posts: All posts data.
            posts_per_page: Number of posts per page.
            total_pages: Total number of pages.
        """
        try:
            for page_num in range(2, total_pages + 1):
                start_idx = (page_num - 1) * posts_per_page
                end_idx = start_idx + posts_per_page
                page_posts = recent_posts[start_idx:end_idx]
                
                # Generate posts HTML for this page
                posts_html = ""
                for date_str, content_data in page_posts:
                    # Add divider for all posts except the first one
                    divider_html = '<div class="border-t"></div>' if posts_html else ''
                    
                    post_html = f'''
                    {divider_html}
                    <article>
                        <h1>
                            <a href="posts/{date_str}.html">
                                {content_data.get('title', 'AI Updates')}
                            </a>
                        </h1>
                        <div class="prose">
                            {content_data.get('content', '')}
                        </div>
                    </article>
                    '''
                    posts_html += post_html
                
                # Generate pagination for this page
                pagination_html = f'''
                <div class="pagination-container">
                    <div class="pagination-links">
                '''
                
                # Previous link
                if page_num > 1:
                    prev_link = "index.html" if page_num == 2 else f"page{page_num - 1}.html"
                    pagination_html += f'''
                        <a href="{prev_link}" class="pagination-prev">← Previous</a>
                    '''
                
                # Page numbers
                for page in range(1, min(6, total_pages + 1)):
                    if page == 1:
                        if page_num == 1:
                            pagination_html += '''
                                <span class="pagination-link current">1</span>
                            '''
                        else:
                            pagination_html += '''
                                <a href="index.html" class="pagination-link">1</a>
                            '''
                    else:
                        if page_num == page:
                            pagination_html += f'''
                                <span class="pagination-link current">{page}</span>
                            '''
                        else:
                            pagination_html += f'''
                                <a href="page{page}.html" class="pagination-link">{page}</a>
                            '''
                
                if total_pages > 5:
                    pagination_html += '''
                        <span class="pagination-dots">...</span>
                    '''
                    if page_num == total_pages:
                        pagination_html += f'''
                            <span class="pagination-link current">{total_pages}</span>
                        '''
                    else:
                        pagination_html += f'''
                            <a href="page{total_pages}.html" class="pagination-link">{total_pages}</a>
                        '''
                
                # Next link
                if page_num < total_pages:
                    pagination_html += f'''
                        <a href="page{page_num + 1}.html" class="pagination-next">Next →</a>
                    '''
                
                pagination_html += '''
                    </div>
                </div>
                '''
                
                # Generate complete page HTML with adjusted paths for subdirectory
                page_html = self.template_manager.generate_index_html_for_subdir(
                    posts_content=posts_html,
                    pagination_script=pagination_html,
                    template_name="page-template.html"
                )
                
                if page_html:
                    # Save pages directly in docs directory
                    page_file = self.docs_path / f"page{page_num}.html"
                    with open(page_file, 'w', encoding='utf-8') as f:
                        f.write(page_html)
                    log_info("Newsletter Generator", f"Generated page{page_num}.html")
                
        except Exception as e:
            log_error("Newsletter Generator", f"Error generating pagination pages", e)
    

    
    def _extract_preview(self, soup: BeautifulSoup, max_length: int = 300) -> str:
        """Extract preview text from content.
        
        Args:
            soup: BeautifulSoup object of the content.
            max_length: Maximum length of preview.
            
        Returns:
            Preview HTML string.
        """
        # Get first section or first few list items
        first_section = soup.find('h3')
        if first_section:
            preview_content = []
            current = first_section
            
            # Add the section title
            preview_content.append(str(first_section))
            
            # Add following content until we hit another section or reach max length
            current = first_section.find_next_sibling()
            text_length = 0
            
            while current and text_length < max_length:
                if current.name == 'h3':  # Stop at next section
                    break
                
                if current.name in ['ul', 'ol', 'p']:
                    preview_content.append(str(current))
                    text_length += len(current.get_text())
                    
                    if current.name in ['ul', 'ol']:
                        # For lists, only show first few items
                        items = current.find_all('li')[:3]  # First 3 items
                        if len(items) < len(current.find_all('li')):
                            # Add "and more..." indicator
                            preview_content[-1] = str(current).replace('</ul>', '<li class="text-gray-500 italic">...and more</li></ul>')
                        break
                
                current = current.find_next_sibling()
            
            return ''.join(preview_content)
        
        # Fallback: just get first paragraph or list
        first_content = soup.find(['p', 'ul', 'ol'])
        if first_content:
            return str(first_content)
        
        return "<p>Click to read the full update...</p>"
    
    def generate_rss_feed(self, recent_posts: List[Tuple[str, Dict[str, str]]]) -> bool:
        """Generate RSS feed with recent posts.
        
        Args:
            recent_posts: List of (date_str, content_data) tuples for recent posts.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Read RSS template
            rss_content = read_file(str(self.feed_path))
            if not rss_content:
                log_error("Newsletter Generator", f"Could not read RSS template: {self.feed_path}")
                return False
            
            # Generate RSS items for last 20 posts
            items_xml = ""
            for date_str, content_data in recent_posts[:20]:
                date_formats = self.format_date(date_str)
                
                # Clean content for RSS (remove complex HTML)
                soup = BeautifulSoup(content_data.get('content', ''), 'html.parser')
                rss_description = self._clean_html_for_rss(soup)
                
                item_xml = f'''
    <item>
      <title>{self._escape_xml(content_data.get('title', 'AI Updates'))}</title>
      <description><![CDATA[{rss_description}]]></description>
      <link>https://dshayan.github.io/sumbird/posts/{date_str}.html</link>
      <guid>https://dshayan.github.io/sumbird/posts/{date_str}.html</guid>
      <pubDate>{date_formats['rss_date']}</pubDate>
    </item>'''
                items_xml += item_xml
            
            # Replace template variables
            now = get_now()
            rss_content = rss_content.replace("{{LAST_BUILD_DATE}}", now.strftime("%a, %d %b %Y %H:%M:%S +0000"))
            rss_content = rss_content.replace("{{PUB_DATE}}", now.strftime("%a, %d %b %Y %H:%M:%S +0000"))
            rss_content = rss_content.replace("{{ITEMS}}", items_xml)
            
            # Write RSS feed
            with open(self.feed_path, 'w', encoding='utf-8') as f:
                f.write(rss_content)
            
            log_info("Newsletter Generator", f"Generated RSS feed with {len(recent_posts[:20])} items")
            return True
            
        except Exception as e:
            log_error("Newsletter Generator", f"Error generating RSS feed", e)
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
    
    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters.
        
        Args:
            text: Text to escape.
            
        Returns:
            XML-escaped text.
        """
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))
    
    def commit_and_push(self) -> bool:
        """Commit and push changes to the repository.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Change to project root (parent of docs directory)
            project_root = self.docs_path.parent
            os.chdir(project_root)
            
            # Check if there are changes to commit in docs/
            result = subprocess.run(['git', 'status', '--porcelain', 'docs/'], 
                                  capture_output=True, text=True, check=True)
            if not result.stdout.strip():
                log_info("Newsletter Generator", "No changes to commit")
                return True
            
            # Add docs directory changes
            subprocess.run(['git', 'add', 'docs/'], check=True)
            
            # Commit with timestamp
            commit_message = f"Update newsletter - {get_now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            # Push to origin
            subprocess.run(['git', 'push', 'origin', 'main'], check=True)
            
            log_success("Newsletter Generator", "Successfully committed and pushed changes")
            return True
            
        except subprocess.CalledProcessError as e:
            log_error("Newsletter Generator", f"Git operation failed: {e}")
            return False
        except Exception as e:
            log_error("Newsletter Generator", f"Error in commit and push", e)
            return False
    
    def generate_newsletter(self, auto_commit: bool = True) -> bool:
        """Generate the complete newsletter from summary files.
        
        Args:
            auto_commit: Whether to automatically commit and push changes.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            log_info("Newsletter Generator", "Starting newsletter generation...")
            
            # Get all summary files
            summary_files = self.get_summary_files()
            if not summary_files:
                log_error("Newsletter Generator", "No summary files found")
                return False
            
            log_info("Newsletter Generator", f"Found {len(summary_files)} summary files")
            
            # Parse and generate posts
            recent_posts = []
            generated_count = 0
            
            for date_str, file_path in summary_files:
                # Parse summary content
                content_data = self.parse_summary_html(file_path)
                if not content_data:
                    log_error("Newsletter Generator", f"Failed to parse {file_path}")
                    continue
                
                # Check if post already exists
                post_file = self.posts_dir / f"{date_str}.html"
                if post_file.exists():
                    log_info("Newsletter Generator", f"Post already exists: {date_str}")
                else:
                    # Generate new post
                    if self.generate_post_page(date_str, content_data):
                        generated_count += 1
                
                recent_posts.append((date_str, content_data))
            
            # Generate homepage with recent posts
            if not self.generate_homepage(recent_posts):
                return False
            
            # Generate RSS feed
            if not self.generate_rss_feed(recent_posts):
                return False
            
            log_success("Newsletter Generator", 
                       f"Generated {generated_count} new posts, updated homepage and RSS feed")
            
            # Commit and push if requested
            if auto_commit:
                return self.commit_and_push()
            
            return True
            
        except Exception as e:
            log_error("Newsletter Generator", f"Error in newsletter generation", e)
            return False


def generate():
    """Main function to generate newsletter. Can be called from pipeline or standalone."""
    try:
        generator = NewsletterGenerator(use_external_css=True)
        success = generator.generate_newsletter()
        
        if success:
            log_success("Newsletter Generator", "Newsletter generation completed successfully")
        else:
            log_error("Newsletter Generator", "Newsletter generation failed")
        
        return success
        
    except Exception as e:
        log_error("Newsletter Generator", f"Error in generate function", e)
        return False


if __name__ == "__main__":
    # Ensure environment is loaded when running standalone
    from utils import env_utils
    if not env_utils.env_vars:
        env_utils.load_environment()
    
    success = generate()
    exit(0 if success else 1)
#!/usr/bin/env python3
"""
Template utilities for Sumbird - Manages newsletter website templates and components.

This module provides utilities for:
1. Loading shared components (header, footer, pagination)
2. Processing templates with external CSS system
3. Generating clean HTML for newsletter posts and pages
4. Managing language-specific templates (English/Farsi)
"""
import re
from pathlib import Path

from utils.file_utils import read_file
from utils.logging_utils import log_error, log_info


class TemplateManager:
    """Manages templates and shared components for the newsletter."""
    
    def __init__(self, docs_path: str = "docs", language: str = "en"):
        """Initialize the template manager.
        
        Args:
            docs_path: Path to the docs directory containing templates and components.
            language: Language code ("en" or "fa").
        """
        self.docs_path = Path(docs_path)
        # Components are now in language-specific subdirectories
        self.components_path = self.docs_path / "assets" / "components" / language
        # Templates are now in language-specific subdirectories
        self.templates_path = self.docs_path / language / "templates"
        self.language = language
        
        # Cache for loaded components
        self._component_cache = {}
    
    def _get_posthog_script(self) -> str:
        """Generate PostHog analytics script if API key is configured.
        
        Uses PostHog JavaScript library loaded via CDN for static sites.
        Automatically captures pageviews and user interactions.
        
        Returns:
            PostHog script tag HTML or empty string if not configured.
        """
        try:
            import os
            from dotenv import load_dotenv
            
            # Load environment to ensure .env is read (PostHog vars are optional, not in REQUIRED_VARS)
            load_dotenv()
            
            # Get PostHog config from environment (optional vars)
            posthog_api_key = (os.getenv('POSTHOG_API_KEY') or '').strip()
            posthog_host = (os.getenv('POSTHOG_HOST') or 'https://app.posthog.com').strip()
            
            # Normalize API host format - convert app.posthog.com to us.i.posthog.com
            if posthog_host == 'https://app.posthog.com':
                posthog_host = 'https://us.i.posthog.com'
            
            if not posthog_api_key:
                return ""
            
            # Official PostHog snippet from documentation (Option 1 - Recommended)
            # This loads PostHog dynamically from CDN and automatically captures $pageview events
            posthog_snippet = """!function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey getNextSurveyStep identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);"""
            
            # Build script with proper initialization
            # PostHog automatically captures $pageview and other events when initialized
            script = f'''    <!-- PostHog JavaScript SDK -->
    <script>
        {posthog_snippet}
        posthog.init('{posthog_api_key}',{{
            api_host: '{posthog_host}'
        }})
    </script>'''
            
            return script
        except Exception as e:
            log_error("TemplateManager", f"Error generating PostHog script", e)
            return ""
    
    def load_component(self, component_name: str, **kwargs) -> str:
        """Load a shared component and replace placeholders.
        
        Args:
            component_name: Name of the component file (without .html extension).
            **kwargs: Key-value pairs for placeholder replacement.
            
        Returns:
            The component HTML with placeholders replaced.
        """
        # Check cache first
        cache_key = f"{component_name}_{hash(frozenset(kwargs.items()))}"
        if cache_key in self._component_cache:
            return self._component_cache[cache_key]
        
        # Load component from language-specific directory
        component_path = self.components_path / f"{component_name}.html"
        
        try:
            component_content = read_file(str(component_path))
            if not component_content:
                log_error("TemplateManager", f"Could not load component: {component_name}")
                return ""
            
            # Replace placeholders
            for key, value in kwargs.items():
                placeholder = f"{{{{{key}}}}}"
                component_content = component_content.replace(placeholder, str(value))
            
            # Cache the result
            self._component_cache[cache_key] = component_content
            return component_content
            
        except Exception as e:
            log_error("TemplateManager", f"Error loading component {component_name}", e)
            return ""
    
    def load_header(self, home_url: str = "/") -> str:
        """Load the header component.
        
        Args:
            home_url: URL for the home link.
            
        Returns:
            The header HTML.
        """
        return self.load_component("header", HOME_URL=home_url)
    
    def load_footer(self, home_url: str = "/", rss_url: str = "/feed.xml") -> str:
        """Load the footer component.
        
        Args:
            home_url: URL for the home link.
            rss_url: URL for the RSS feed.
            
        Returns:
            The footer HTML.
        """
        return self.load_component("footer", HOME_URL=home_url, RSS_URL=rss_url)
    
    def load_pagination(self, current_page: int, total_pages: int, base_path: str = "") -> str:
        """Load the pagination component.
        
        Args:
            current_page: Current page number (1-based).
            total_pages: Total number of pages.
            base_path: Base path for links (e.g., "" for root, "../" for subdirectory).
            
        Returns:
            The pagination HTML.
        """
        if total_pages <= 1:
            return ""
        
        # No previous/next links - only numbered pagination
        
        # Generate page links
        page_links = ""
        for page in range(1, min(6, total_pages + 1)):
            if page == 1:
                page_href = f"{base_path}index.html"
            else:
                page_href = f"{base_path}page{page}.html"
            
            if page == current_page:
                page_links += f'<span class="pagination-link current">{page}</span>'
            else:
                page_links += f'<a href="{page_href}" class="pagination-link">{page}</a>'
        
        # Add dots and last page if there are more than 5 pages
        if total_pages > 5:
            page_links += '<span class="pagination-dots">...</span>'
            last_href = f"{base_path}page{total_pages}.html"
            if current_page == total_pages:
                page_links += f'<span class="pagination-link current">{total_pages}</span>'
            else:
                page_links += f'<a href="{last_href}" class="pagination-link">{total_pages}</a>'
        
        return self.load_component("pagination", 
                                 PREV_LINK="",
                                 PAGE_LINKS=page_links,
                                 NEXT_LINK="")
    
    def generate_post_html(self, 
                          title: str, 
                          content: str, 
                          description: str = "", 
                          template_name: str = "template.html",
                          date_str: str = "",
                          og_image: str = "") -> str:
        """Generate a complete post HTML using the template.
        
        Args:
            title: The post title.
            content: The post content (HTML).
            description: The post description for meta tag.
            template_name: Name of the template file to use.
            date_str: Date string for generating canonical URL.
            og_image: URL to Open Graph image.
            
        Returns:
            The complete HTML for the post.
        """
        template_path = self.templates_path / template_name
        
        try:
            template_content = read_file(str(template_path))
            if not template_content:
                log_error("TemplateManager", f"Could not load template: {template_name}")
                return ""
            
            # Load components with language-aware paths
            # Import config values locally to avoid circular imports
            from config import SITE_BASE_URL, OG_IMAGE_URL
            
            if self.language == "fa":
                # Posts are in docs/fa/news/{date_str}/, need ../../ to get to fa/ homepage
                header_html = self.load_header("../../")  # From fa/news/{date_str}/ to fa/ homepage
                footer_html = self.load_footer("../../", "../../feed.xml")  # RSS in fa/ directory
                # Generate canonical URL for Farsi post using SITE_BASE_URL from .env (no .html extension)
                canonical_url = f"{SITE_BASE_URL}/fa/news/{date_str}" if date_str else f"{SITE_BASE_URL}/fa/"
            else:
                # Posts are in docs/en/news/{date_str}/, need ../../ to get to en/ homepage
                header_html = self.load_header("../../")  # From en/news/{date_str}/ to en/ homepage
                footer_html = self.load_footer("../../", "../../feed.xml")  # RSS in en/ directory
                # Generate canonical URL for English post using SITE_BASE_URL from .env (no .html extension)
                canonical_url = f"{SITE_BASE_URL}/en/news/{date_str}" if date_str else f"{SITE_BASE_URL}/en/"
            
            # Use default OG image if none provided
            if not og_image:
                og_image = OG_IMAGE_URL
            
            # Truncate description for OG tags (max 65 chars for good preview)
            og_description = description[:62] + "..." if len(description) > 65 else description
            if not og_description:
                og_description = "AI news and vibes from Twitter"
            
            # Adjust language attributes and asset paths
            # Both English and Persian posts are in en/news/{date_str}/ and fa/news/{date_str}/ subdirectories
            # So they both need ../../../assets/ to get from date_str/ -> news/ -> en|fa/ -> docs/ -> assets/
            html_content = template_content.replace('href="../assets/', 'href="../../../assets/')
            html_content = html_content.replace('src="../assets/', 'src="../../../assets/')
            
            if self.language == "fa":
                # Update HTML lang attribute to Farsi
                html_content = html_content.replace('lang="en"', 'lang="fa"')
                # Remove any existing dir attribute and add dir="rtl"
                html_content = re.sub(r'\s+dir="[^"]*"', '', html_content)  # Remove existing dir attribute
                html_content = html_content.replace('<html lang="fa"', '<html lang="fa" dir="rtl"')
                # Update Open Graph locale
                html_content = html_content.replace('content="en_US"', 'content="fa_IR"')
            else:
                # Update HTML lang attribute to English
                html_content = html_content.replace('lang="fa"', 'lang="en"')
                # Remove any existing dir attribute and add dir="ltr"
                html_content = re.sub(r'\s+dir="[^"]*"', '', html_content)  # Remove existing dir attribute
                html_content = html_content.replace('<html lang="en"', '<html lang="en" dir="ltr"')
                # Update Open Graph locale to English
                html_content = html_content.replace('content="fa_IR"', 'content="en_US"')
            
            # Replace template placeholders
            html_content = html_content.replace("{{TITLE}}", title)
            html_content = html_content.replace("{{DESCRIPTION}}", description)
            html_content = html_content.replace("{{CONTENT}}", content)
            html_content = html_content.replace("{{CANONICAL_URL}}", canonical_url)
            html_content = html_content.replace("{{OG_IMAGE}}", og_image)
            html_content = html_content.replace("{{HEADER}}", header_html)
            html_content = html_content.replace("{{FOOTER}}", footer_html)
            html_content = html_content.replace("{{POSTHOG_SCRIPT}}", self._get_posthog_script())
            
            return html_content
            
        except Exception as e:
            log_error("TemplateManager", f"Error generating post HTML", e)
            return ""
    
    def generate_index_html(self, 
                           posts_content: str, 
                           pagination_script: str = "", 
                           template_name: str = "page-template.html") -> str:
        """Generate the index page HTML using the template.
        
        Args:
            posts_content: The HTML content for all posts.
            pagination_script: JavaScript for pagination functionality.
            template_name: Name of the template file to use.
            
        Returns:
            The complete HTML for the index page.
        """
        # Template is in language-specific templates directory
        template_path = self.templates_path / template_name
        
        try:
            template_content = read_file(str(template_path))
            if not template_content:
                log_error("TemplateManager", f"Could not load template: {template_name}")
                return ""
            
            # Both English and Farsi are now in subdirectories (en/ and fa/)
            # Load components with appropriate paths (both need ../ to get to assets/)
            home_url = "../"  # From en/ or fa/ to root
            rss_url = "feed.xml"
            header_html = self.load_header(home_url)
            footer_html = self.load_footer(home_url, rss_url)
            
            # Adjust asset paths for subdirectory (both languages are in subdirectories)
            template_content = template_content.replace('href="assets/', 'href="../assets/')
            template_content = template_content.replace('src="assets/', 'src="../assets/')
            
            # Adjust language attributes for both languages
            if self.language == "fa":
                # Update HTML lang attribute to Farsi
                template_content = template_content.replace('lang="en"', 'lang="fa"')
                # Remove any existing dir attribute and add dir="rtl"
                template_content = re.sub(r'\s+dir="[^"]*"', '', template_content)  # Remove existing dir attribute
                template_content = template_content.replace('<html lang="fa"', '<html lang="fa" dir="rtl"')
                # Update Open Graph locale
                template_content = template_content.replace('content="en_US"', 'content="fa_IR"')
            else:
                # Update HTML lang attribute to English
                template_content = template_content.replace('lang="fa"', 'lang="en"')
                # Remove any existing dir attribute and add dir="ltr"
                template_content = re.sub(r'\s+dir="[^"]*"', '', template_content)  # Remove existing dir attribute
                template_content = template_content.replace('<html lang="en"', '<html lang="en" dir="ltr"')
                # Update Open Graph locale to English
                template_content = template_content.replace('content="fa_IR"', 'content="en_US"')
            
            # Replace template placeholders
            html_content = template_content.replace("{{POSTS}}", posts_content)
            html_content = html_content.replace("{{PAGINATION}}", pagination_script)
            html_content = html_content.replace("{{HEADER}}", header_html)
            html_content = html_content.replace("{{FOOTER}}", footer_html)
            html_content = html_content.replace("{{POSTHOG_SCRIPT}}", self._get_posthog_script())
            
            return html_content
            
        except Exception as e:
            log_error("TemplateManager", f"Error generating index HTML", e)
            return ""
    
    def clear_cache(self):
        """Clear the component cache."""
        self._component_cache.clear()
        log_info("TemplateManager", "Component cache cleared")
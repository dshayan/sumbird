#!/usr/bin/env python3
"""
Template utilities for Sumbird Newsletter - Handles centralized templates and components.

This module provides utilities for:
1. Loading shared components (header, footer)
2. Processing templates with external CSS
3. Generating clean HTML without embedded styles
"""

import os
from pathlib import Path
from typing import Dict, Optional
from utils.file_utils import read_file
from utils.logging_utils import log_error, log_info


class TemplateManager:
    """Manages templates and shared components for the newsletter."""
    
    def __init__(self, docs_path: str = "docs"):
        """Initialize the template manager.
        
        Args:
            docs_path: Path to the docs directory containing templates and components.
        """
        self.docs_path = Path(docs_path)
        self.components_path = self.docs_path / "assets" / "components"
        self.templates_path = self.docs_path / "posts"
        
        # Cache for loaded components
        self._component_cache = {}
    
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
    
    def generate_post_html(self, 
                          title: str, 
                          content: str, 
                          description: str = "", 
                          template_name: str = "template.html") -> str:
        """Generate a complete post HTML using the template.
        
        Args:
            title: The post title.
            content: The post content (HTML).
            description: The post description for meta tag.
            template_name: Name of the template file to use.
            
        Returns:
            The complete HTML for the post.
        """
        template_path = self.templates_path / template_name
        
        try:
            template_content = read_file(str(template_path))
            if not template_content:
                log_error("TemplateManager", f"Could not load template: {template_name}")
                return ""
            
            # Load components
            header_html = self.load_header("../")
            footer_html = self.load_footer("../", "../feed.xml")
            
            # Replace template placeholders
            html_content = template_content.replace("{{TITLE}}", title)
            html_content = html_content.replace("{{DESCRIPTION}}", description)
            html_content = html_content.replace("{{CONTENT}}", content)
            html_content = html_content.replace("{{HEADER}}", header_html)
            html_content = html_content.replace("{{FOOTER}}", footer_html)
            
            return html_content
            
        except Exception as e:
            log_error("TemplateManager", f"Error generating post HTML", e)
            return ""
    
    def generate_index_html(self, 
                           posts_content: str, 
                           pagination_script: str = "", 
                           template_name: str = "index.html") -> str:
        """Generate the index page HTML using the template.
        
        Args:
            posts_content: The HTML content for all posts.
            pagination_script: JavaScript for pagination functionality.
            template_name: Name of the template file to use.
            
        Returns:
            The complete HTML for the index page.
        """
        template_path = self.docs_path / template_name
        
        try:
            template_content = read_file(str(template_path))
            if not template_content:
                log_error("TemplateManager", f"Could not load template: {template_name}")
                return ""
            
            # Load components
            header_html = self.load_header("/")
            footer_html = self.load_footer("/", "feed.xml")
            
            # Replace template placeholders
            html_content = template_content.replace("{{POSTS}}", posts_content)
            html_content = html_content.replace("{{PAGINATION}}", pagination_script)
            html_content = html_content.replace("{{JAVASCRIPT}}", pagination_script)  # Backwards compatibility
            html_content = html_content.replace("{{HEADER}}", header_html)
            html_content = html_content.replace("{{FOOTER}}", footer_html)
            
            return html_content
            
        except Exception as e:
            log_error("TemplateManager", f"Error generating index HTML", e)
            return ""
    
    def generate_index_html_for_subdir(self, 
                                      posts_content: str, 
                                      pagination_script: str = "", 
                                      template_name: str = "index.html") -> str:
        """Generate index page HTML for subdirectory with adjusted paths.
        
        Args:
            posts_content: The HTML content for all posts.
            pagination_script: JavaScript for pagination functionality.
            template_name: Name of the template file to use.
            
        Returns:
            The complete HTML for the index page with adjusted paths.
        """
        template_path = self.docs_path / template_name
        
        try:
            template_content = read_file(str(template_path))
            if not template_content:
                log_error("TemplateManager", f"Could not load template: {template_name}")
                return ""
            
            # Load components with paths for root directory
            header_html = self.load_header("/")
            footer_html = self.load_footer("/", "feed.xml")
            
            # Replace template placeholders
            html_content = template_content.replace("{{POSTS}}", posts_content)
            html_content = html_content.replace("{{PAGINATION}}", pagination_script)
            html_content = html_content.replace("{{JAVASCRIPT}}", pagination_script)  # Backwards compatibility
            html_content = html_content.replace("{{HEADER}}", header_html)
            html_content = html_content.replace("{{FOOTER}}", footer_html)
            
            # No path adjustments needed for root directory
            # Assets and posts are already at correct relative paths
            
            return html_content
            
        except Exception as e:
            log_error("TemplateManager", f"Error generating index HTML for subdirectory", e)
            return ""
    
    def clear_cache(self):
        """Clear the component cache."""
        self._component_cache.clear()
        log_info("TemplateManager", "Component cache cleared")


def create_template_manager(docs_path: str = "docs") -> TemplateManager:
    """Create a new template manager instance.
    
    Args:
        docs_path: Path to the docs directory.
        
    Returns:
        A new TemplateManager instance.
    """
    return TemplateManager(docs_path)
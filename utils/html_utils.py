#!/usr/bin/env python3
"""
HTML utilities for Sumbird.

This module provides HTML processing utilities:
- HTML tag stripping
- HTML content cleaning
- Text normalization
"""
import re

from bs4 import BeautifulSoup

def strip_html(html):
    """Remove HTML tags from a string using BeautifulSoup.
    
    Used in: fetcher.py
    
    Args:
        html (str): HTML content to strip
        
    Returns:
        str: Plain text with HTML tags removed
    """
    if not html:
        return ""
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text()

def clean_html_for_display(html_content):
    """Clean HTML content for display, preserving essential formatting.
    
    Used in: telegraph_converter.py
    
    Args:
        html_content (str): HTML content to clean
        
    Returns:
        str: Cleaned HTML content
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Ensure all links have href attributes
    for a_tag in soup.find_all('a'):
        if not a_tag.has_attr('href'):
            a_tag.unwrap()
    
    # Convert relative URLs to absolute
    for a_tag in soup.find_all('a', href=True):
        if a_tag['href'].startswith('/'):
            a_tag['href'] = 'https://example.com' + a_tag['href']
    
    # Remove tags not supported by most display formats
    for tag in soup.find_all(['script', 'style', 'iframe', 'form']):
        tag.decompose()
    
    # Preserve proper spacing between elements
    for br in soup.find_all('br'):
        br.replace_with('\n')
    
    # Convert HTML back to string
    return str(soup)

def clean_text(text):
    """Clean text by removing extra whitespace.
    
    Used in: fetcher.py
    
    Args:
        text (str): Text to clean
        
    Returns:
        str: Cleaned text with normalized whitespace
    """
    return re.sub(r'\s+', ' ', text).replace('\n', '\\n').strip()

def html_to_text(html_content):
    """Convert HTML to plain text, preserving basic structure.
    
    Args:
        html_content (str): HTML content to convert
        
    Returns:
        str: Plain text representation of the HTML content
    """
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Handle paragraphs and line breaks
    for br in soup.find_all('br'):
        br.replace_with('\n')
    
    for p in soup.find_all('p'):
        p.append(soup.new_string('\n\n'))
    
    # Handle lists
    for li in soup.find_all('li'):
        li.insert_before(soup.new_string('• '))
        li.append(soup.new_string('\n'))
    
    # Get text and normalize whitespace
    text = soup.get_text()
    return re.sub(r'\n{3,}', '\n\n', text).strip() 
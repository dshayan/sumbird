#!/usr/bin/env python3
"""
Module for converting summarized content to Telegraph format.
This module can be run independently or as part of the pipeline.
"""
import json
import os
import re
import sys
from datetime import datetime

from bs4 import BeautifulSoup

# Add parent directory to sys.path to allow imports from the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    CONVERTED_DIR, FILE_FORMAT, FOOTER_LINK_TEXT, FOOTER_LINK_TEXT_FA,
    FOOTER_LINK_URL, FOOTER_LINK_URL_FA, FOOTER_TEXT, FOOTER_TEXT_FA,
    SUMMARY_DIR, SUMMARY_TITLE_FORMAT, TRANSLATED_DIR, get_date_str,
    get_file_path
)
from utils.html_utils import clean_html_for_display
from utils.json_utils import write_json
from utils.logging_utils import log_error, log_info, log_success

def apply_rtl_formatting(children):
    """Apply RTL formatting to ensure proper display of mixed English/Persian text.
    
    Args:
        children (list): List of child nodes
        
    Returns:
        list: List with RTL formatting applied
    """
    # For mixed content, we need to ensure the entire paragraph flows RTL
    # We'll add a strong RTL marker at the beginning of the first text node
    result = []
    first_text_found = False
    
    for child in children:
        if isinstance(child, str) and child.strip() and not first_text_found:
            # Add Right-to-Left Mark (RLM) at the very beginning to establish RTL context
            # U+200F (RLM) establishes RTL directionality for the entire paragraph
            result.append('\u200F' + child)
            first_text_found = True
        else:
            result.append(child)
    
    return result

def html_to_telegraph_nodes(html_content, is_persian=False):
    """Convert HTML content to Telegraph node format.
    
    Args:
        html_content (str): HTML content as string
        is_persian (bool): Whether this is Persian content (for RTL direction)
        
    Returns:
        list: List of Telegraph node objects
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    result = []
    
    # Process all top-level elements in the HTML
    for element in soup.find_all(recursive=False):
        node = parse_element_to_node(element, is_persian)
        if node:
            result.append(node)
    
    return result

def parse_element_to_node(element, is_persian=False):
    """Parse a BeautifulSoup element to a Telegraph node.
    
    Args:
        element: BeautifulSoup element
        is_persian (bool): Whether this is Persian content (for RTL direction)
        
    Returns:
        dict: Telegraph node object
    """
    # Text node
    if isinstance(element, str) or element.name is None:
        text = str(element) if isinstance(element, str) else str(element.string)
        if text and text.strip():
            return text.strip()
        return None
    
    # Handle different element types
    tag_name = element.name
    

    
    # Create node with tag
    node = {'tag': tag_name}
    
    # Add attributes if needed
    if tag_name == 'a' and element.get('href'):
        node['attrs'] = {'href': element.get('href')}
    elif tag_name == 'img' and element.get('src'):
        node['attrs'] = {'src': element.get('src')}
    
    # Add children
    children = []
    for child in element.children:
        parsed_child = parse_element_to_node(child, is_persian)
        if parsed_child:
            children.append(parsed_child)
    
    # For Persian content, wrap text content with RTL embedding characters
    if is_persian and children and tag_name in ['p', 'h1', 'h3', 'h4', 'h5', 'h6', 'li']:
        # Apply RTL formatting to all children
        children = apply_rtl_formatting(children)
        # Add Right-to-Left Override (RLO) at the beginning and Pop Directional Formatting (PDF) at the end
        # U+202E (RLO) forces RTL direction more strongly than RLE, U+202C (PDF) ends the directional override
        children = ['\u202E'] + children + ['\u202C']
    
    if children:
        node['children'] = children
    
    return node

def ensure_spacing_between_nodes(nodes):
    """Ensure proper spacing between adjacent text and formatted nodes.
    
    Args:
        nodes (list): List of Telegraph nodes
        
    Returns:
        list: List of Telegraph nodes with proper spacing
    """
    if not nodes:
        return nodes
        
    result = []
    formatting_tags = ['b', 'strong', 'i', 'em', 'code']
    
    for i, node in enumerate(nodes):
        # Skip processing if not a valid node
        if not node:
            result.append(node)
            continue
            
        # Case 1: Text node followed by a formatted node
        if (isinstance(node, str) and i+1 < len(nodes) and 
            isinstance(nodes[i+1], dict) and nodes[i+1].get('tag') in formatting_tags):
            
            # Only add space if the text doesn't already end with whitespace or punctuation
            if not node.endswith((' ', '\n', '\t', ',', '.', ':', ';', '?', '!')):
                node = node + ' '
        
        # Case 2: Formatted node followed by a text node
        elif (isinstance(node, dict) and node.get('tag') in formatting_tags and 
              i+1 < len(nodes) and isinstance(nodes[i+1], str)):
            
            next_text = nodes[i+1]
            # Only add space if the next text doesn't start with whitespace or punctuation
            if not next_text.startswith((' ', '\n', '\t', ',', '.', ':', ';', '?', '!')):
                nodes[i+1] = ' ' + next_text
        
        # Case 3: Formatted node followed by another formatted node (e.g., bold to italic)
        elif (isinstance(node, dict) and node.get('tag') in formatting_tags and 
              i+1 < len(nodes) and isinstance(nodes[i+1], dict) and 
              nodes[i+1].get('tag') in formatting_tags):
            
            # Insert a space node between them
            result.append(node)
            result.append(' ')
            continue  # Skip appending the current node again
        
        result.append(node)
    
    return result

def fix_spacing_in_nodes(nodes):
    """Fix spacing issues in nodes.
    
    Args:
        nodes (list): List of Telegraph nodes
        
    Returns:
        list: List of Telegraph nodes with fixed spacing
    """
    # Recursively process all nodes
    def process_node(node):
        # Skip if not a dictionary (text node)
        if not isinstance(node, dict):
            return node
        
        # Process children if they exist
        if 'children' in node and isinstance(node['children'], list):
            # First process all children recursively
            children = [process_node(child) for child in node['children']]
            
            # Then fix spacing between adjacent nodes
            if node['tag'] in ['p', 'li']:  # Only apply to paragraph-like elements
                node['children'] = ensure_spacing_between_nodes(children)
            else:
                node['children'] = children
        
        return node
    
    # Process each top-level node
    return [process_node(node) for node in nodes]

def add_footer(nodes, is_persian=False):
    """Add footer to the content.
    
    Args:
        nodes (list): List of Telegraph nodes
        is_persian (bool): Whether to use Persian footer text
        
    Returns:
        list: List with added footer
    """
    # Add footer node
    if is_persian:
        footer_text = FOOTER_TEXT_FA
        footer_link = FOOTER_LINK_TEXT_FA
        footer_url = FOOTER_LINK_URL_FA
    else:
        footer_text = FOOTER_TEXT
        footer_link = FOOTER_LINK_TEXT
        footer_url = FOOTER_LINK_URL
    
    footer_children = [
        footer_text + ' ',
        {
            'tag': 'a',
            'attrs': {'href': footer_url},
            'children': [footer_link]
        }
    ]
    
    # For Persian footer, wrap with RTL embedding characters
    if is_persian:
        footer_children = ['\u202E'] + footer_children + ['\u202C']
    
    footer_node = {
        'tag': 'p',
        'children': footer_children
    }
    
    nodes.append(footer_node)
    return nodes

def extract_title(html_content):
    """Extract title from HTML content.
    
    Args:
        html_content (str): HTML content
        
    Returns:
        tuple: (title, content_without_title)
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for h1 tags for title
    title_tag = soup.find('h1')
    if title_tag:
        title = title_tag.get_text()
        title_tag.extract()  # Remove the title from content
        return title, str(soup)
    
    # Default title if not found
    return "AI Updates", html_content

def convert_to_telegraph_format(input_file, output_file, date_str, is_persian=False):
    """Convert a summarized HTML file to Telegraph format.
    
    Args:
        input_file (str): Path to the input HTML file
        output_file (str): Path to save the Telegraph format file
        date_str (str): Date string for formatting
        is_persian (bool): Whether this is Persian content
    
    Returns:
        bool: True if conversion was successful, False otherwise
    """
    try:
        # Read the input file
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Content is already in HTML format, no need for conversion
        html_content = content
        
        # Extract title and clean content
        title, html_content = extract_title(html_content)
        
        # Clean HTML to ensure proper display
        html_content = clean_html_for_display(html_content)
        
        # Convert HTML to Telegraph nodes
        nodes = html_to_telegraph_nodes(html_content, is_persian)
        
        # Fix spacing issues
        nodes = fix_spacing_in_nodes(nodes)
        
        # Add footer
        nodes = add_footer(nodes, is_persian)
        
        # Create Telegraph format
        telegraph_data = {
            'title': title,
            'content': nodes
        }
        
        # Save to JSON file
        write_json(output_file, telegraph_data)
        
        log_success('TelegraphConverter', f"Converted to Telegraph format: {output_file}")
        return True
    
    except Exception as e:
        log_error('TelegraphConverter', f"Error converting to Telegraph format: {str(e)}")
        return False

def convert_all_summaries():
    """Convert all summaries to Telegraph format."""
    # Get the date string for today
    date_str = get_date_str()
    
    # Get file paths
    summary_file = get_file_path('summary', date_str)
    translated_file = get_file_path('translated', date_str)
    
    converted_en_file = get_file_path('converted', date_str)
    converted_fa_file = get_file_path('converted', date_str, lang='FA')
    
    # Check if both required files exist
    if not os.path.exists(summary_file):
        log_error('TelegraphConverter', f"Summary file not found: {summary_file}")
        return False
    
    if not os.path.exists(translated_file):
        log_error('TelegraphConverter', f"Translated file not found: {translated_file}")
        return False
    
    # English conversion
    en_result = convert_to_telegraph_format(summary_file, converted_en_file, date_str, is_persian=False)
    
    # Persian conversion (now required)
    fa_result = convert_to_telegraph_format(translated_file, converted_fa_file, date_str, is_persian=True)
    
    # Log completion
    if en_result and fa_result:
        log_success('TelegraphConverter', f"Successfully converted both English and Persian summaries to Telegraph format")
    else:
        log_error('TelegraphConverter', "Failed to convert summaries to Telegraph format")
    
    # Return overall success - both conversions must succeed
    return en_result and fa_result

if __name__ == "__main__":
    # Ensure environment is loaded when running standalone
    from utils import ensure_environment_loaded
    ensure_environment_loaded()
    
    # Create necessary directories when running as standalone, but only if they don't exist
    if not os.path.exists(SUMMARY_DIR):
        log_info('TelegraphConverter', f"Creating directory: {SUMMARY_DIR}")
        os.makedirs(SUMMARY_DIR, exist_ok=True)
    
    if not os.path.exists(TRANSLATED_DIR):
        log_info('TelegraphConverter', f"Creating directory: {TRANSLATED_DIR}")
        os.makedirs(TRANSLATED_DIR, exist_ok=True)
    
    if not os.path.exists(CONVERTED_DIR):
        log_info('TelegraphConverter', f"Creating directory: {CONVERTED_DIR}")
        os.makedirs(CONVERTED_DIR, exist_ok=True)
    
    convert_all_summaries() 
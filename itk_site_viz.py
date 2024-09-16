import xml.etree.ElementTree as ET
from collections import defaultdict
import requests
from bs4 import BeautifulSoup
import os

# Function to parse the XML sitemap
def parse_sitemap(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    urls = []
    for url in root.findall('ns:url', namespace):
        loc = url.find('ns:loc', namespace).text
        urls.append(loc)
    return urls

# Function to build hierarchy from URLs
def build_hierarchy(urls):
    hierarchy = defaultdict(dict)
    
    for url in urls:
        parts = url.replace('https://www.itk-engineering.de', '').strip('/').split('/')
        current_level = hierarchy
        for part in parts:
            if part not in current_level:
                current_level[part] = {}
            current_level = current_level[part]
    
    return hierarchy

# Function to scrape a page for links
def scrape_page(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for errors
        
        # Check Content-Type to ensure it's HTML
        if 'text/html' not in response.headers.get('Content-Type', ''):
            print(f"Skipping non-HTML content: {url}")
            return []

        soup = BeautifulSoup(response.text, 'lxml')  # Try 'lxml' parser
        links = []
        for p in soup.find_all('p', class_='link link-arrow'):
            a_tag = p.find('a')
            if a_tag and a_tag['href']:
                links.append(a_tag['href'])
        return links
    except requests.RequestException as e:
        print(f"Error scraping {url}: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error processing {url}: {e}")
        return []

# Function to build a dependency map
def build_dependency_map(urls):
    dependencies = {url: [] for url in urls}
    reverse_dependencies = {url: [] for url in urls}
    for url in urls:
        links = scrape_page(url)
        for link in links:
            if link in dependencies:
                dependencies[link].append(url)
                reverse_dependencies[url].append(link)
    return dependencies, reverse_dependencies

# Function to generate an HTML file for all dependencies with graphical structure
def generate_dependency_html(dependencies, reverse_dependencies):
    html = '''<html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>All Dependencies</title>
        <style>
            body {
                font-family: Arial, sans-serif;
            }
            .tree ul {
                padding-top: 20px; 
                position: relative;
                transition: all 0.5s;
                display: flex;
                justify-content: center;
            }
            .tree li {
                list-style-type: none;
                margin: 0 20px;
                text-align: center;
                position: relative;
                padding: 20px 5px 0 5px;
            }
            .tree li::before, .tree li::after {
                content: '';
                position: absolute;
                top: 0;
                right: 50%;
                border-top: 2px solid #ccc;
                width: 50%;
                height: 20px;
            }
            .tree li::after {
                right: auto; 
                left: 50%;
                border-left: 2px solid #ccc;
            }
            .tree li:only-child::after, .tree li:only-child::before {
                display: none;
            }
            .tree li:only-child {
                padding-top: 0;
            }
            .tree li:first-child::before, .tree li:last-child::after {
                border: 0 none;
            }
            .tree li:last-child::before {
                border-right: 2px solid #ccc;
            }
            .tree li:first-child::after {
                border-left: 2px solid #ccc;
            }
            .tree ul ul::before {
                content: '';
                position: absolute;
                top: 0;
                left: 50%;
                border-left: 2px solid #ccc;
                width: 0;
                height: 20px;
            }
            .tree li a {
                border: 2px solid #ccc;
                padding: 5px 10px;
                text-decoration: none;
                color: #666;
                font-family: arial, verdana, tahoma;
                font-size: 12px;
                display: inline-block;
                border-radius: 5px;
                transition: all 0.5s;
            }
            .tree li a:hover, .tree li a:hover + ul li a {
                background: #c8e4f8; 
                color: #000;
                border: 2px solid #94a0b4;
            }
        </style>
    </head>
    <body>
        <h1>Page Dependencies</h1>'''

    for page, refs in dependencies.items():
        page_id = page.replace('https://www.itk-engineering.de', '').replace('/', '_')
        html += f'<h2 id="{page_id}">Page: <a href="{page}">{page}</a></h2>'
        
        # Links to this page (Reverse Dependencies)
        html += '<div class="tree"><h3>Links to this page:</h3><ul>'
        if refs:
            for ref in refs:
                ref_id = ref.replace('https://www.itk-engineering.de', '').replace('/', '_')
                html += f'<li><a href="{ref}">{ref}</a></li>'
        else:
            html += '<li>No pages link to this page.</li>'
        html += '</ul></div>'
        
        # This page links to (Dependencies)
        html += '<div class="tree"><h3>This page links to:</h3><ul>'
        if reverse_dependencies.get(page):
            for link in reverse_dependencies[page]:
                link_id = link.replace('https://www.itk-engineering.de', '').replace('/', '_')
                html += f'<li><a href="{link}">{link}</a></li>'
        else:
            html += '<li>No outbound links from this page.</li>'
        html += '</ul></div>'
    
    html += '</body></html>'
    
    with open('all_dependencies.html', 'w', encoding='utf-8') as file:
        file.write(html)
    
    print("Graphical HTML file with all dependencies generated: all_dependencies.html")




def hierarchy_to_html_graph(hierarchy, dependencies, base_url="https://www.itk-engineering.de"):
    html = '<div class="tree">\n'
    counter = [0]  # To keep track of node numbering
    
    def recurse(d, path="", level=1):
        nonlocal html
        for key, value in d.items():
            counter[0] += 1
            node_id = counter[0]
            url = f"{base_url}{path}/{key}" if key else base_url
            color = f"rgb({level * 50}, {255 - level * 50}, 100)"  # Gradient color
            has_dependencies = len(dependencies.get(url, [])) > 0
            page_filename = url.replace(base_url, '').replace('/', '_')
            dependency_link = f'<a href="all_dependencies.html#{page_filename}"> ➔</a>' if has_dependencies else ''
            html += f'<div class="node" style="border-color: {color};">\n'
            html += f'  <a href="{url}">{node_id}: {key if key else "Home"} {dependency_link}</a>\n'
            if isinstance(value, dict) and value:
                html += '  <div class="children">\n'
                recurse(value, path + '/' + key, level + 1)
                html += '  </div>\n'
            html += '</div>\n'

    recurse(hierarchy)
    html += '</div>\n'
    return html
import xml.etree.ElementTree as ET
from collections import defaultdict
import requests
from bs4 import BeautifulSoup
import os

# Function to parse the XML sitemap
def parse_sitemap(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    urls = []
    for url in root.findall('ns:url', namespace):
        loc = url.find('ns:loc', namespace).text
        urls.append(loc)
    return urls

# Function to build hierarchy from URLs
def build_hierarchy(urls):
    hierarchy = defaultdict(dict)
    
    for url in urls:
        parts = url.replace('https://www.itk-engineering.de', '').strip('/').split('/')
        current_level = hierarchy
        for part in parts:
            if part not in current_level:
                current_level[part] = {}
            current_level = current_level[part]
    
    return hierarchy

# Function to scrape a page for links
def scrape_page(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors
        
        # Check Content-Type to ensure it's HTML, ignore pdfs and so on
        if 'text/html' not in response.headers.get('Content-Type', ''):
            print(f"Skipping non-HTML content: {url}")
            return []

        soup = BeautifulSoup(response.text, 'lxml')  # Try 'lxml' parser
        links = []
        for p in soup.find_all('p', class_='link link-arrow'):
            a_tag = p.find('a')
            if a_tag and a_tag['href']:
                links.append(a_tag['href'])
        return links
    except requests.RequestException as e:
        print(f"Error scraping {url}: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error processing {url}: {e}")
        return []

# Function to build a dependency map
def build_dependency_map(urls):
    dependencies = {url: [] for url in urls}
    reverse_dependencies = {url: [] for url in urls}
    for url in urls:
        links = scrape_page(url)
        for link in links:
            if link in dependencies:
                dependencies[link].append(url)
                reverse_dependencies[url].append(link)
    return dependencies, reverse_dependencies

# Function to generate an HTML file for all dependencies with graphical structure
def generate_dependency_html(dependencies, reverse_dependencies):
    html = '''<html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>All Dependencies</title>
        <style>
            body {
                font-family: Arial, sans-serif;
            }
            .tree ul {
                padding-top: 20px; 
                position: relative;
                transition: all 0.5s;
                display: flex;
                justify-content: center;
            }
            .tree li {
                list-style-type: none;
                margin: 0 20px;
                text-align: center;
                position: relative;
                padding: 20px 5px 0 5px;
            }
            .tree li::before, .tree li::after {
                content: '';
                position: absolute;
                top: 0;
                right: 50%;
                border-top: 2px solid #ccc;
                width: 50%;
                height: 20px;
            }
            .tree li::after {
                right: auto; 
                left: 50%;
                border-left: 2px solid #ccc;
            }
            .tree li:only-child::after, .tree li:only-child::before {
                display: none;
            }
            .tree li:only-child {
                padding-top: 0;
            }
            .tree li:first-child::before, .tree li:last-child::after {
                border: 0 none;
            }
            .tree li:last-child::before {
                border-right: 2px solid #ccc;
            }
            .tree li:first-child::after {
                border-left: 2px solid #ccc;
            }
            .tree ul ul::before {
                content: '';
                position: absolute;
                top: 0;
                left: 50%;
                border-left: 2px solid #ccc;
                width: 0;
                height: 20px;
            }
            .tree li a {
                border: 2px solid #ccc;
                padding: 5px 10px;
                text-decoration: none;
                color: #666;
                font-family: arial, verdana, tahoma;
                font-size: 12px;
                display: inline-block;
                border-radius: 5px;
                transition: all 0.5s;
            }
            .tree li a:hover, .tree li a:hover + ul li a {
                background: #c8e4f8; 
                color: #000;
                border: 2px solid #94a0b4;
            }
        </style>
    </head>
    <body>
        <h1>Page Dependencies</h1>'''

    for page, refs in dependencies.items():
        page_id = page.replace('https://www.itk-engineering.de', '').replace('/', '_')
        html += f'<h2 id="{page_id}">Page: <a href="{page}">{page}</a></h2>'
        
        
        html += '<div class="tree"><h3>Links to this page:</h3><ul>'
        if refs:
            for ref in refs:
                ref_id = ref.replace('https://www.itk-engineering.de', '').replace('/', '_')
                html += f'<li><a href="{ref}">{ref}</a></li>'
        else:
            html += '<li>No pages link to this page.</li>'
        html += '</ul></div>'
        
        
        html += '<div class="tree"><h3>This page links to:</h3><ul>'
        if reverse_dependencies.get(page):
            for link in reverse_dependencies[page]:
                link_id = link.replace('https://www.itk-engineering.de', '').replace('/', '_')
                html += f'<li><a href="{link}">{link}</a></li>'
        else:
            html += '<li>No outbound links from this page.</li>'
        html += '</ul></div>'
    
    html += '</body></html>'
    
    with open('all_dependencies.html', 'w', encoding='utf-8') as file:
        file.write(html)
    
    print("Graphical HTML file with all dependencies generated: all_dependencies.html")




def hierarchy_to_html_graph(hierarchy, dependencies, base_url="https://www.itk-engineering.de"):
    html = '<div class="tree">\n'
    counter = [0]  # To keep track of node numbering
    
    def recurse(d, path="", level=1):
        nonlocal html
        for key, value in d.items():
            counter[0] += 1
            node_id = counter[0]
            url = f"{base_url}{path}/{key}" if key else base_url
            color = f"rgb({level * 50}, {255 - level * 50}, 100)"  # Gradient color
            has_dependencies = len(dependencies.get(url, [])) > 0
            page_filename = url.replace(base_url, '').replace('/', '_')
            dependency_link = f'<a href="all_dependencies.html#{page_filename}"> ➔</a>' if has_dependencies else ''
            html += f'<div class="node" style="border-color: {color};">\n'
            html += f'  <a href="{url}">{node_id}: {key if key else "Home"} {dependency_link}</a>\n'
            if isinstance(value, dict) and value:
                html += '  <div class="children">\n'
                recurse(value, path + '/' + key, level + 1)
                html += '  </div>\n'
            html += '</div>\n'

    recurse(hierarchy)
    html += '</div>\n'
    return html


def generate_mesh_dependency_html_with_search(dependencies, reverse_dependencies):
    html = '''<html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Mesh Dependency Graph</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
            }
            #graph {
                width: 100%;
                height: 800px;
                margin: 20px 0;
            }
            #search-container {
                margin: 20px;
            }
            #search-input {
                padding: 8px;
                width: 300px;
                font-size: 16px;
            }
        </style>
        <!-- Import Vis.js library for network visualization -->
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet" type="text/css" />
    </head>
    <body>
        <h1>ITK Website page map Visual</h1>
        
        <div id="search-container">
            <input type="text" id="search-input" placeholder="Search for ITK Page..." onkeyup="searchNode()" />
        </div>
        
        <div id="graph"></div>

        <script type="text/javascript">
            // Create an array of nodes
            var nodes = new vis.DataSet([
    '''

    # Collect all unique nodes (URLs)
    all_pages = set(dependencies.keys()).union(set(reverse_dependencies.keys()))
    
    # Generate node list with clickable URLs and hover tooltips
    for i, page in enumerate(all_pages):
        page_id = page.replace('https://www.itk-engineering.de', '').replace('/', '_')
        html += f'{{id: {i+1}, label: "{page_id}", title: "{page}", url: "{page}"}},\n'
    
    html += ']);\n\n'

    
    html += 'var edges = [\n'

    
    node_map = {page: i+1 for i, page in enumerate(all_pages)}

    # Outgoing links ("This page links to")
    for source_page, linked_pages in dependencies.items():
        source_id = node_map[source_page]
        for target_page in linked_pages:
            target_id = node_map[target_page]
            html += f'{{from: {source_id}, to: {target_id}, arrows: "to", color: {{color: "#6495ED"}}}},\n'  # Uniform color for links
    
    html += '];\n\n'

    # Generate the network graph using Vis.js with clickable nodes
    html += '''
            // Create a network
            var container = document.getElementById('graph');
            var data = {
                nodes: nodes,
                edges: edges
            };
            var options = {
                nodes: {
                    shape: 'dot',
                    size: 15,
                    font: {
                        size: 12
                    },
                    borderWidth: 2
                },
                edges: {
                    width: 2,
                    arrows: {
                        to: {enabled: true, scaleFactor: 1.2}
                    },
                    color: {inherit: 'from'},
                    smooth: {
                        type: 'dynamic'
                    }
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 200
                },
                physics: {
                    enabled: true,
                    stabilization: {iterations: 200}
                }
            };
            var network = new vis.Network(container, data, options);

            // Add click event to nodes to navigate to the page
            network.on("click", function (params) {
                if (params.nodes.length > 0) {
                    var clickedNode = nodes.get(params.nodes[0]);
                    if (clickedNode.url) {
                        window.open(clickedNode.url, '_blank');
                    }
                }
            });

            // Function to search for nodes by label
            function searchNode() {
                var input = document.getElementById("search-input").value.toLowerCase();
                var foundNodes = nodes.get({
                    filter: function (node) {
                        return node.label.toLowerCase().includes(input);
                    }
                });

                if (foundNodes.length > 0) {
                    var nodeIds = foundNodes.map(function(node) { return node.id; });
                    network.selectNodes(nodeIds);
                    network.focus(nodeIds[0], {
                        scale: 1.2,
                        offset: {x: 0, y: 0},
                        animation: {
                            duration: 500,
                            easingFunction: "easeInOutQuad"
                        }
                    });
                } else {
                    network.unselectAll();
                }
            }
        </script>
    </body>
    </html>
    '''

    with open('itk-engineering-graph.html', 'w', encoding='utf-8') as file:
        file.write(html)

    print("Mesh graph HTML file with search generated: mesh_dependencies_with_search.html")



# main function to generate both hierarchy and mesh graph
def generate_html_graph(xml_file):
    
    urls = parse_sitemap(xml_file)  # Step 1: Parse XML
    url_hierarchy = build_hierarchy(urls)  # Step 2: Build hierarchy
    
    # Build dependencies and reverse dependencies (existing logic)
    dependencies, reverse_dependencies = build_dependency_map(urls)  # Step 3: Build dependencies

    
    html_content = hierarchy_to_html_graph(url_hierarchy, dependencies)  # Convert hierarchy to HTML
    with open('website_hierarchy_graph.html', 'w', encoding='utf-8') as file:
        file.write(html_content)

    # Generate mesh dependency view
    generate_mesh_dependency_html_with_search(dependencies, reverse_dependencies)  # Generate mesh dependency HTML

    print("HTML hierarchy and mesh dependency graphs generated!")

# Call the main function
generate_html_graph('sitemap.xml')




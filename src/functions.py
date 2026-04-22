import os
import re
import requests
import mimetypes
from urllib.parse import urljoin, urlparse, unquote
import subprocess
import base64
from bs4 import BeautifulSoup

def rar_compress(filepath, output_dir, vol_size_mb=100, password=None):
    """
    Compress `filepath` into one or more RAR volumes.
    
    Parameters
    ----------
    filepath : str
        Path to the file or directory you want to archive.
    output_dir : str
        Where to put the resulting .rar files.
    vol_size_mb : int, optional
        Maximum size of each volume in megabytes.
    password : str, optional
        Password for the archive (if None, no password is set).
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Base name for the archive
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    archive_path = os.path.join(output_dir, base_name)

    # Build the command
    #  -r   : recurse into subdirectories
    #  -vNNM: volume size (e.g. -v500m)
    #  -p: set password (if provided)
    cmd = ["rar", "a", "-r", f"-v{vol_size_mb}m"]
    if password:
        cmd.append(f"-p{password}")
    else:
        cmd.append("-p-")  # no password
    cmd.append(f"{archive_path}.rar")  # base name + .rar
    cmd.append(filepath)  # file/directory to compress

    # Run
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"RAR failed: {result.stderr}")
    print(result.stdout)
    # removing the file
    os.remove(filepath)

def download_file(url, save_directory="."):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        filename = ""
        
        # 1. Try to get the exact filename from the Content-Disposition header
        cd_header = response.headers.get('content-disposition')
        if cd_header:
            matches = re.findall(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', cd_header)
            if matches:
                filename = matches[0][0].strip('\'"')
                
        # 2. Try to get the filename from the URL
        if not filename:
            parsed_url = urlparse(url)
            filename = unquote(os.path.basename(parsed_url.path))
            
        # 3. Use Content-Type to figure out the file extension
        # Content-Type looks like 'text/html; charset=utf-8', we just want 'text/html'
        content_type = response.headers.get('content-type')
        if content_type:
            mime_type = content_type.split(';')[0].strip()
            # Guess the extension (e.g., 'image/png' becomes '.png')
            guessed_extension = mimetypes.guess_extension(mime_type)
            
            if filename:
                # If we got a filename from the URL, check if it's missing an extension
                _, ext = os.path.splitext(filename)
                if not ext and guessed_extension:
                    filename += guessed_extension
            else:
                # If there was no filename in the URL at all (e.g. "http://example.com/")
                filename = "downloaded_file"
                if guessed_extension:
                    filename += guessed_extension
                    
        # 4. Final fallback if absolutely nothing worked
        if not filename:
            filename = "downloaded_file"
            
        # Create the save directory if it doesn't exist
        os.makedirs(save_directory, exist_ok=True)
        save_path = os.path.join(save_directory, filename)
        
        # Open the file and save it
        print(f"Downloading as: {filename}...")
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    
        print(f"File successfully saved to: {os.path.abspath(save_path)}")
        return save_path

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while downloading the file: {e}")

def get_as_base64(url, session):
    """Fetches a file and returns it as a base64 data URI."""
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', '')
        encoded = base64.b64encode(response.content).decode('utf-8')
        return f"data:{content_type};base64,{encoded}"
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return url # Fallback to original URL if download fails

def url_to_name(url):
    # derive from URL
    parsed = urlparse(url)
    path = parsed.path
    # if ends with slash, use index.html
    if path.endswith('/') or not path:
        name = 'index.html'
    else:
        name = os.path.basename(path)
        if len(name) > 10:
            name = name[:10]
        # ensure .html extension
        if not name.lower().endswith('.html'):
            name += '.html'
    # optionally prefix with domain
    domain = parsed.netloc.replace(':', '_')
    name = f'{domain}_{name}'
    directory = os.getcwd()
    filepath = os.path.join(directory, name)
    return filepath

def save_single_html(url, output_filepath=None):
    if output_filepath == None:
        output_filepath = url_to_name(url)
    # Use a standard user-agent to avoid basic blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    session = requests.Session()
    session.headers.update(headers)

    print(f"Fetching HTML from {url}...")
    response = session.get(url, timeout=15)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")

    # 1. Embed Images
    print("Embedding images...")
    for img in soup.find_all("img"):
        src = img.get("src")
        if src and not src.startswith("data:"):
            full_url = urljoin(url, src)
            img["src"] = get_as_base64(full_url, session)
            # Remove srcset so the browser doesn't try to fetch responsive images externally
            if img.get("srcset"):
                del img["srcset"]

    # 2. Embed CSS Stylesheets
    print("Embedding CSS...")
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if href:
            full_url = urljoin(url, href)
            try:
                css_response = session.get(full_url, timeout=10)
                css_response.raise_for_status()
                
                # Replace the <link> tag with a <style> tag containing the CSS text
                style_tag = soup.new_tag("style")
                style_tag.string = css_response.text
                link.replace_with(style_tag)
            except Exception as e:
                print(f"Failed to download CSS {full_url}: {e}")

    # 3. (Optional) Remove Scripts to prevent errors in the offline file
    # Since we can't bundle dynamic JS perfectly without breaking paths,
    # it's usually safer to remove external scripts for a static reading view.
    for script in soup.find_all("script"):
        if script.get("src"):
            script.decompose()

    # Save to file
    print(f"Saving to {output_filepath}...")
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(str(soup))
        
    print("Done!")
    return output_filepath

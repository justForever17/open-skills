
import sys
import os

# Allow running this script directly without pip install (No-Install Mode)
# This inserts the project root directory into sys.path so 'open_skills' package resolves
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "open_skills"

from mcp.server.fastmcp import FastMCP

from open_skills.sandbox import sandbox_manager
import os
import yaml
import glob
import time
import mimetypes
import boto3
import requests
import sys
import atexit
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Ensure container is cleaned up on exit
atexit.register(sandbox_manager.stop)

# Initialize FastMCP Server
mcp = FastMCP("v8chat-computer", dependencies=["docker", "boto3"])

@mcp.tool()
def upload_to_s3(filename: str) -> str:
    """
    Uploads a file from the current workspace to S3 and returns a public URL.
    
    Args:
        filename: Name of the file in the workspace (relative to root).
    """
    try:
        # Resolve Path on Host via Sandbox Manager (Single User Mode)
        # sandbox_manager.host_work_dir is a Path object
        host_work_dir = sandbox_manager.host_work_dir
        host_path = (host_work_dir / filename).resolve()
        
        # Security Check: Ensure file is inside workspace
        if not host_path.is_relative_to(host_work_dir):
             return "Error: File path is outside the workspace (Security restrictions)."

        safe_filename = host_path.name
        
        print(f"[Upload] Starting upload for {filename} (Path: {host_path})", file=sys.stderr)

        if not host_path.exists():
            return f"Error: File '{filename}' not found in workspace."
            
        # S3 Configuration
        endpoint = os.getenv("S3_ENDPOINT", os.getenv("S3_CUSTOM_DOMAIN"))
        access_key = os.getenv("S3_ACCESS_KEY")
        secret_key = os.getenv("S3_SECRET_KEY")
        bucket = os.getenv("S3_BUCKET")
        region = os.getenv("S3_REGION", "us-east-1")

        if not bucket or not endpoint:
            return "Error: S3 configuration (BUCKET, ENDPOINT) missing."
            
        # Normalize Endpoint
        if not endpoint.startswith("http"):
            endpoint = f"https://{endpoint}"

        # S3 Client Configuration
        from botocore.config import Config
        s3_config = Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        )

        s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=s3_config
        )
        
        # Generate Key: uploads/{yyyy}/{mm}/{ts}-{name}
        t = time.localtime()
        timestamp = int(time.time())
        key = f"uploads/{t.tm_year}/{t.tm_mon}/{timestamp}-{safe_filename}"
        
        # Content Type
        content_type, _ = mimetypes.guess_type(str(host_path))
        final_content_type = content_type or 'application/octet-stream'
        
        # 1. Generate Presigned URL
        try:
            presigned_url = s3.generate_presigned_url(
                ClientMethod='put_object',
                Params={
                    'Bucket': bucket,
                    'Key': key,
                    'ContentType': final_content_type
                },
                ExpiresIn=300
            )
        except Exception as e:
            return f"Error Generating Presigned URL: {str(e)}"

        # 2. Upload via Requests
        with open(host_path, "rb") as f:
            response = requests.put(
                presigned_url, 
                data=f, 
                headers={'Content-Type': final_content_type}
            )
            
        if response.status_code not in [200, 201, 204]:
            return f"Upload Failed: {response.status_code} {response.text}"
            
        # Return URL
        base_url = os.getenv("S3_CUSTOM_DOMAIN", "")
        if base_url and base_url.endswith("/"):
            base_url = base_url[:-1]
            
        public_url = f"{base_url}/{bucket}/{key}"
        return public_url

    except Exception as e:
        return f"Upload Failed: {str(e)}"

@mcp.tool()
def download_from_s3(s3_key: str) -> str:
    """
    Downloads a file from S3 to the current workspace.
    
    Args:
        s3_key: The S3 key or full URL.
    """
    try:
        # Handle Full URL vs Key
        key = s3_key
        base_url = os.getenv("S3_CUSTOM_DOMAIN", "")
        bucket = os.getenv("S3_BUCKET")

        if s3_key.startswith("http") and base_url and base_url in s3_key:
             key = s3_key.replace(f"{base_url}/{bucket}/", "")
        
        filename = os.path.basename(key)
        # Use PathLib
        local_path = sandbox_manager.host_work_dir / filename
        
        # S3 Client
        from botocore.config import Config
        s3_config = Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        )
        
        s3 = boto3.client(
            's3',
            endpoint_url=os.getenv("S3_ENDPOINT", os.getenv("S3_CUSTOM_DOMAIN")),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
            region_name="us-east-1",
            config=s3_config
        )
        
        # Generate Presigned URL for GET
        presigned_url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=300
        )
            
        # Download
        with requests.get(presigned_url, stream=True) as r:
            if r.status_code != 200:
                return f"Download Failed: HTTP {r.status_code}"
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        
        return f"Successfully downloaded '{filename}' to workspace."
        
    except Exception as e:
        return f"Download Failed: {str(e)}"

@mcp.tool()
def execute_command(command: str) -> str:
    """
    Executes a shell command in the sandbox environment (mapped to current workspace).
    
    Args:
        command: The shell command to execute.
    """
    try:
        exit_code, output = sandbox_manager.execute_command(command)
        if exit_code != 0:
            return f"Command failed with exit code {exit_code}.\nOutput:\n{output}"
        return output
    except Exception as e:
        return f"Execution Error: {str(e)}"

@mcp.tool()
def read_file(path: str) -> str:
    """
    Reads a file from the sandbox filesystem (or workspace).
    
    Args:
        path: Absolute path in the container (e.g. /share/file.txt).
    """
    return sandbox_manager.read_file(path)

@mcp.tool()
def write_file(path: str, content: str) -> str:
    """
    Writes content to a file in the sandbox filesystem.
    
    Args:
        path: Absolute path in the container.
        content: Text content to write.
    """
    return sandbox_manager.write_file(path, content)

@mcp.tool()
def manage_skills(action: str, skill_name: str = None) -> str:
    """
    The Librarian Tool to discover and learn skills.
    
    Args:
        action: 'list' (show all skills) or 'inspect' (read SKILL.md for a specific skill).
        skill_name: Required if action is 'inspect'.
    """
    skills_dir = sandbox_manager.host_skill_path
    
    # Ensure skills_dir exists
    if not skills_dir.exists():
        return f"Error: Skills directory not found at {skills_dir}"

    if action == "list":
        results = []
        # Recursive Scan using glob (simpler with pathlib)
        for skill_file in skills_dir.rglob("SKILL.md"):
            try:
                # Calculate category/name (e.g. data-analysis/pandas/SKILL.md)
                rel_path = skill_file.relative_to(skills_dir)
                category = str(rel_path.parent).replace(os.sep, "/")
                
                content = skill_file.read_text(encoding='utf-8')
                if content.startswith("---"):
                    end_idx = content.find("---", 3)
                    if end_idx != -1:
                        frontmatter = content[3:end_idx]
                        meta = yaml.safe_load(frontmatter)
                        name = meta.get('name', 'unknown')
                        desc = meta.get('description', 'No description')
                        results.append(f"- [{category}] {name}: {desc}")
            except:
                pass
        
        if not results:
            return "No skills found in library."
        return "Available Skills:\n" + "\n".join(sorted(results))

    elif action == "inspect":
        if not skill_name:
            return "Error: skill_name is required for inspect action."
        
        # Search logic
        target_file = None
        
        # 1. Exact Match (folder name == skill_name)
        # Iterate over all SKILL.md and check parent folder name
        # OR glob search
        candidates = list(skills_dir.rglob("SKILL.md"))
        
        # Heuristic 1: Exact direct match with parent folder
        for cand in candidates:
            if cand.parent.name == skill_name:
                target_file = cand
                break
        
        # Heuristic 2: Match anywhere in path (e.g. "pandas" in "data/pandas/SKILL.md")
        if not target_file:
            for cand in candidates:
                if skill_name in str(cand.relative_to(skills_dir)):
                    target_file = cand
                    break

        if not target_file:
            return f"Error: Skill '{skill_name}' not found."
            
        raw_content = target_file.read_text(encoding='utf-8')

        # --- ADAPTER LAYER ---
        # "Smart Path Injection" for anthropics/skills compatibility
        # We need to construct the ABSOLUTE path of this skill inside the container.
        # Container Mount: /app/skills  <-- host_skill_path
        
        # 1. Calculate relative path of the skill folder from the skills root
        # target_file.parent is the specific skill folder
        rel_path = target_file.parent.relative_to(skills_dir)
        
        # 2. Convert to POSIX string for Docker
        rel_path_posix = rel_path.as_posix() # WindowsPath handled correctly
        
        # 3. Construct absolute container path
        job_root = f"/app/skills/{rel_path_posix}"
        
        # 4. Inject into Content
        # Replace 'scripts/' with absolute path
        injected_content = raw_content.replace("scripts/", f"{job_root}/scripts/")
        # Common pattern: `python scripts/run.py` -> `python /app/skills/xxx/scripts/run.py`
        
        # Handle {{SKILL_ROOT}} variable
        injected_content = injected_content.replace("{{SKILL_ROOT}}", job_root)
        
        # Prepend Context Header
        header = f"""<!--
[SYSTEM]: Context Injection Active
SKILL_ROOT: {job_root}
WORKING_DIR: /share
HOST_IP: {os.getenv('HOST_IP', 'Auto-Detected')}
-->
"""
        return header + injected_content

    return "Invalid action. Use 'list' or 'inspect'."

def main():
    # Run via Stdio (Standard Input/Output) for direct integration
    mcp.run()

if __name__ == "__main__":
    main()

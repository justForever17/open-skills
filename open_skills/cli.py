
import sys
import os

# Allow running this script directly without pip install (No-Install Mode)
# This inserts the project root directory into sys.path so 'open_skills' package resolves
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "open_skills"

from dotenv import load_dotenv
load_dotenv()

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

# Ensure container is cleaned up on exit
atexit.register(sandbox_manager.stop)

# Initialize FastMCP Server
mcp = FastMCP("v8chat-computer", dependencies=["docker", "boto3"])

@mcp.tool()
def upload_to_s3(filename: str) -> str:
    """
    Uploads a file from your Sandbox (`/share`) to S3 and returns a public URL.
    
    [USAGE SOP]
    1. **Source**: The file MUST strictly exist in your sandbox. 
    2. **Path**: Provide the path relative to `/share`.
       - Example: `output/report.pdf` (refers to `/share/output/report.pdf`).
       - If you have `/share/data.csv`, just pass `data.csv`.
    3. **Return**: A public HTTPS URL for the user to access.
    """
    try:
        # Resolve Path on Host via Sandbox Manager (Single User Mode)
        # sandbox_manager.host_work_dir is a Path object
        host_work_dir = sandbox_manager.host_work_dir
        
        # Robustness: Handle if agent passes "/share/..." prefix by stripping it
        # This aligns code with the "Mental Model" that /share IS the root.
        clean_filename = filename.replace("/share/", "").lstrip("/") if filename.startswith("/share/") else filename
        
        host_path = (host_work_dir / clean_filename).resolve()
        
        # Security Check: Ensure file is inside workspace
        if not host_path.is_relative_to(host_work_dir):
             return "Error: File path is outside the workspace (Security restrictions)."

        safe_filename = host_path.name
        
        print(f"[Upload] Starting upload for {filename} (Path: {host_path})", file=sys.stderr)

        if not host_path.exists():
            return f"Error: File '{filename}' not found in /share. Did you `write_file` or `execute_command` to create it first?"
            
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
    Downloads a file from S3 to your Sandbox (`/share`).
    
    [USAGE SOP]
    1. **Purpose**: Retrieve remote files (e.g. user-provided URLs) into your workspace.
    2. **Destination**: The file will disappear in `/share/{filename}`.
    3. **Action**: After downloading, use `list_directory` or `read_file` to verify.
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
        
        return f"Successfully downloaded '{filename}' to /share/{filename}."
        
    except Exception as e:
        return f"Download Failed: {str(e)}"

@mcp.tool()
def execute_command(command: str) -> str:
    """
    Executes a shell command in the sandbox environment.

    [CORE CONCEPT: DUAL SPACE]
    - **Sandbox Space (Your Avatar)**: You are operating inside a Docker container.
    - **Path Mapping**: `/share` inside the container == Your IDE's Project Root.
    - **Permissions**: You are user `agent` (uid=1000). You have read/write access to `/share`, but NO root/sudo access.

    [USAGE SOP - HARD SKILLS]
    Use this tool when you need to:
    1. Run Python scripts (e.g., `python /app/skills/xxx/script.py`).
    2. Install dependencies (e.g., `pip install pandas` or `npm install axios`).
    3. Perform file operations that `write_file` cannot handle (e.g., `unzip`, `tar`, `mv`).

    [BEST PRACTICES]
    - Always use **ABSOLUTE PATHS** for robust execution (e.g., `/share/data.csv`, `/app/skills/tool/run.py`).
    - If a command fails due to missing dependencies, try `pip install` or `npm install` first (Self-Healing).
    """
    try:
        exit_code, output = sandbox_manager.execute_command(command)
        if exit_code != 0:
            return f"Command failed with exit code {exit_code}.\nOutput:\n{output}"
        return output
    except Exception as e:
        return f"Execution Error: {str(e)}"

@mcp.tool()
def read_file(path: str, start_line: int = 1, line_count: int = 3000) -> str:
    """
    Reads a file from the sandbox filesystem.
    
    [PATH MAPPING REMINDER]
    - `/share/file.txt` corresponds to `file.txt` in your IDE project root.
    - You can also read from the read-only skills library at `/app/skills`.
    
    [PAGINATION SOP - IMPORTANT]
    - Default `line_count` is 3000 to prevent output overflow.
    - If the file is larger, call `read_file` again with `start_line=3001`.
    """
    return sandbox_manager.read_file(path, start_line, line_count)

@mcp.tool()
def write_file(path: str, content: str) -> str:
    """
    Writes content to a file in the sandbox filesystem.

    [PATH MAPPING REMINDER]
    - Writing to `/share/output.txt` will immediately create `output.txt` in your IDE project root.
    - Use this to prepare input files (e.g. `data.json`, `config.yaml`) BEFORE running a skill script.
    
    [WARNING - LARGE FILES]
    - If you are writing a large file (approx > 200 lines or > 10KB), you MUST use `append_file` instead.
    - This tool will fail for large payloads due to JSON protocol limits.
    """
    return sandbox_manager.write_file(path, content)

@mcp.tool()
def append_file(path: str, content: str) -> str:
    """
    Appends content to an existing file in the sandbox.

    [USAGE SOP - LARGE FILES]
    Use this tool when you need to write LARGE content that might fail JSON parsing (e.g. >10kb text).
    1. First call `write_file` with the first chunk (or empty string "" to create file).
    2. Then call `append_file` repeatedly with subsequent chunks.
    """
    return sandbox_manager.append_file(path, content)

@mcp.tool()
def list_directory(path: str = "/share") -> str:
    """
    Lists files and directories in the specified path (sandbox).
    Default is `/share` (Your Workspace Root).
    
    [CONTEXT RECOVERY]
    - Use this tool to "see" what files are in your current workspace.
    - Vital for checking if previous tasks generated the expected output files.
    - If you are lost or resuming a task, always start by listing `/share`.
    """
    # Simply use execute_command("ls -F") for robust output
    # -F adds / to directories, * to executables, etc.
    try:
        # Security: Normalize path
        target_path = path if path.startswith("/") else f"/share/{path}"
        
        # Check basic jail (handled by sandbox execute but explicit check is good)
        if not (target_path.startswith("/share") or target_path.startswith("/app/skills")):
             return "Error: Permission denied. You can only list /share or /app/skills."

        exit_code, output = sandbox_manager.execute_command(f"ls -F {target_path}")
        if exit_code != 0:
            return f"Error listing directory: {output}"
            
        if not output.strip():
            return "(Directory is empty)"
            
        return f"Contents of {target_path}:\n{output}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def manage_skills(action: str, skill_name: str = None) -> str:
    """
    The Librarian Tool to discover and learn skills.
    
    [COGNITIVE SOP - ON-DEMAND LOADING]
    Do not guess! Always follow this strictly:
    
    1. **SEARCH**: Call `manage_skills(action='list')` to see what tools/SOPs are available.
    2. **SELECT**: Pick the most suitable skill for your current problem (e.g. `guide/code-review` for reviewing, `data/analysis` for pandas).
    3. **INSPECT**: Call `manage_skills(action='inspect', skill_name='...')` to read the `SKILL.md`.
    4. **OBEY**: 
       - If it's a **Code execution** skill: Follow the `SKILL.md` syntax to run it via `execute_command`.
       - If it's a **Thinking/SOP** skill: Adopt the methodology described in `SKILL.md` as your temporary system prompt and execute the reasoning process.
       
    **CRITICAL**: You MUST strictly adhere to the instructions within `SKILL.md`. It is the source of truth.
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
    import argparse
    
    # 1. Parse Arguments (Hybrid approach: mix of mcp params and ours)
    # FastMCP uses click/typer internally, but mcp.run() usually takes over sys.argv.
    # We need to peek at args first or filter them.
    
    parser = argparse.ArgumentParser(description="Open Skills MCP Server", add_help=False)
    parser.add_argument("--skills-dir", type=str, help="Path to local skills directory", default=None)
    parser.add_argument("--work-dir", type=str, help="Path to workspace directory", default=None)
    
    # Parse known args only, leaving the rest for mcp/uvicorn
    args, unknown = parser.parse_known_args()
    
    # 2. Configure Sandbox Manager
    if args.skills_dir:
        custom_path = Path(args.skills_dir).resolve()
        if not custom_path.exists():
            print(f"Error: Custom skills directory '{custom_path}' does not exist.", file=sys.stderr)
            sys.exit(1)
        
        # In-place update of the singleton
        sandbox_manager.host_skill_path = custom_path
        sys.stderr.write(f"[Config] Using custom skills path: {sandbox_manager.host_skill_path}\n")

    if args.work_dir:
        custom_work = Path(args.work_dir).resolve()
        if not custom_work.exists():
             custom_work.mkdir(parents=True, exist_ok=True)
        sandbox_manager.host_work_dir = custom_work
        sys.stderr.write(f"[Config] Using custom work dir: {sandbox_manager.host_work_dir}\n")

    # 3. Clean sys.argv for FastMCP/Uvicorn
    # Remove our arguments so FastMCP doesn't complain
    sys.argv = [sys.argv[0]] + unknown

    # Run via Stdio (Standard Input/Output) for direct integration
    
    # Signal Handling: Catch Ctrl+C (SIGINT) and Kill (SIGTERM) from IDEs
    import signal
    
    def handle_signal(signum, frame):
        sys.stderr.write(f"\n[Lifecycle] Received signal {signum}. forcing sandbox cleanup...\n")
        sandbox_manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        mcp.run()
    finally:
        # Fallback for normal exit or unhandled exceptions
        sys.stderr.write("[Lifecycle] Shutting down... cleaning up sandbox.\n")
        sandbox_manager.stop()

# --- LIFECYCLE MANAGEMENT MONKEYPATCH ---
# Goal: Ensure sandbox container starts WHEN SERVER STARTS, and stops WHEN SERVER STOPS.
# Strategy: Wrap the mcp.sse_app() factory to inject Starlette event handlers.

_original_sse_app_factory = mcp.sse_app

def sse_app_wrapper(**kwargs):
    """
    Wrapper around FastMCP's sse_app factory to inject lifecycle hooks.
    This ensures eager sandbox creation and robust cleanup.
    """
    app = _original_sse_app_factory(**kwargs)
    
    # 1. Eager Startup: Create container immediately
    app.add_event_handler("startup", sandbox_manager.get_sandbox)
    
    # 2. Robust Shutdown: Stop container on server exit
    app.add_event_handler("shutdown", sandbox_manager.stop)
    
    return app

# Overwrite the method on the instance so uvicorn calls our wrapper
mcp.sse_app = sse_app_wrapper
# ----------------------------------------

if __name__ == "__main__":
    main()

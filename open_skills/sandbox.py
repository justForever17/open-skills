
import docker
import os
import tarfile
import io
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Optional, Tuple, Dict, Any

# Embedded Dockerfile for "All-in-One" Auto-Build
# Matches the standalone Dockerfile in the project root.
# Start Sandbox logic


class SandboxManager:
    """
    Manages a SINGLE ephemeral Docker container with enhanced security and path handling.
    """
    
    IMAGE_NAME = "open-skills:latest"
    CONTAINER_NAME_PREFIX = "open-skills-sandbox"

    def __init__(self, 
                 image_name: str = IMAGE_NAME):
        self.client = docker.from_env()
        self.image_name = image_name
        self.container = None
        
        # 1. Resolve Paths using PathLib (Host Side)
        base_dir = Path(__file__).parent.resolve()
        
        # Default Skills Path
        self.host_skill_path = Path(os.getenv("HOST_SKILL_PATH", base_dir / "skills")).resolve()
        
        # Workspace Path (CWD by default)
        self.host_work_dir = Path(os.getenv("HOST_WORK_DIR", os.getcwd())).resolve()
        
        self.container_name = self.CONTAINER_NAME_PREFIX
        
        # Virtual Paths in Container (Always POSIX)
        self.container_share_path = PurePosixPath("/share")
        self.container_skill_path = PurePosixPath("/app/skills")
        
        # Host IP Detection
        self.host_ip = self._get_host_ip()
        
        sys.stderr.write(f"[Sandbox] Init. Skills: {self.host_skill_path}, WorkDir: {self.host_work_dir}, HostIP: {self.host_ip}\n")

    def _get_host_ip(self) -> str:
        """Detects the Host IP address accessible from Docker."""
        try:
            import socket
            # Hack to get local interface IP that routes to Internet
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "host.docker.internal" # Fallback for Desktop versions

    def to_posix(self, win_path: str) -> str:
        """Helper to ensure paths passed to Docker SDK are POSIX style (required on Windows)."""
        return Path(win_path).as_posix()

    def validate_path(self, path: str, allow_read_skills=False) -> str:
        """
        Security Jail Check: Ensures absolute container paths are within /share or /app/skills.
        Returns the path if valid, raises ValueError if not.
        """
        # Convert to PurePosixPath for logical manipulation
        target = PurePosixPath(path)
        
        # Check against /share (Read/Write)
        if self._is_subpath(target, self.container_share_path):
            return str(target)
            
        # Check against /app/skills (Read-Only)
        if allow_read_skills and self._is_subpath(target, self.container_skill_path):
            return str(target)
            
        raise ValueError(f"Security Alert: Access denied to path '{path}'. You are jailed in /share.")

    def _is_subpath(self, target: PurePosixPath, parent: PurePosixPath) -> bool:
        """Checks if target is a subpath of parent."""
        try:
            target.relative_to(parent)
            return True
        except ValueError:
            return False

    def get_sandbox(self):
        """Gets or starts the single sandbox container."""
        if self.container:
            try:
                self.container.reload()
                if self.container.status == 'running':
                    return self.container
            except:
                self.container = None
        
        return self._start_sandbox()

    def _start_sandbox(self):
        """Starts the single sandbox container with security options."""
        try:
            # Check Image existence strict check
            try:
                self.client.images.get(self.image_name)
            except docker.errors.ImageNotFound:
                raise RuntimeError(
                    f"⛔ Docker image '{self.image_name}' not found!\n"
                    f"Please run `docker build -t {self.image_name} open_skills/` manually,\n"
                    "or pull it from the registry if available."
                )

            # Remove existing container if strictly needed, 
            # though usually we might want to attach? 
            # For strict sandbox, clean start is better.
            existing = self.client.containers.list(all=True, filters={"name": self.container_name})
            if existing:
                sys.stderr.write(f"[Sandbox] Removing existing container {self.container_name}...\n")
                existing[0].remove(force=True)

            sys.stderr.write(f"[Sandbox] Starting container {self.container_name}...\n")
            sys.stderr.write(f"[Sandbox] 🚀 Eager Initialization Triggered!\n")
            
            # Start Container
            self.container = self.client.containers.run(
                self.image_name,
                name=self.container_name,
                detach=True,
                tty=True,
                # Mounts: Convert Windows Paths to POSIX string for Docker Engine
                volumes={
                    self.to_posix(self.host_skill_path): {'bind': '/app/skills', 'mode': 'ro'},
                    self.to_posix(self.host_work_dir): {'bind': '/share', 'mode': 'rw'},
                    # Persistence for pip/npm cache
                    'open-skills-pip-cache': {'bind': '/home/agent/.cache/pip', 'mode': 'rw'},
                    'open-skills-npm-cache': {'bind': '/home/agent/.npm', 'mode': 'rw'},
                },
                environment={
                    "HOST_IP": self.host_ip,
                    "SKILL_ROOT": "/app/skills" # Default Root
                },
                working_dir="/share",
                user="agent", # Enforce non-root
                security_opt=["no-new-privileges"], # Security Hardening
                cap_drop=["ALL"], # Drop all capabilities
                # cap_add=["NET_BIND_SERVICE"], # If needed later
                restart_policy={"Name": "no"}
            )
            
            sys.stderr.write(f"[Sandbox] Sandbox started with ID: {self.container.id[:12]}\n")
            return self.container

        except Exception as e:
            sys.stderr.write(f"[Sandbox] Failed to start sandbox: {e}\n")
            raise



    def execute_command(self, command: str) -> Tuple[int, str]:
        """Executes a command inside the sandbox."""
        container = self.get_sandbox()
            
        sys.stderr.write(f"[Exec] {command}\n")
        exit_code, output = container.exec_run(
            ["/bin/bash", "-c", command],
            user="agent",
            demux=True 
        )
        
        stdout = output[0].decode('utf-8', errors='ignore') if output[0] else ""
        stderr = output[1].decode('utf-8', errors='ignore') if output[1] else ""
        
        return exit_code, stdout + stderr

    def read_file(self, path: str) -> str:
        """Reads a file from the sandbox with security check."""
        # 1. Security Check
        # We assume 'path' is absolute inside container. If relative, treat as relative to /share
        if not path.startswith("/"):
             path = f"/share/{path}"
        
        # Validate (Allows reading from Skills too)
        safe_path = self.validate_path(path, allow_read_skills=True)

        container = self.get_sandbox()
        try:
            stream, stat = container.get_archive(safe_path)
            file_obj = io.BytesIO()
            for chunk in stream:
                file_obj.write(chunk)
            file_obj.seek(0)
            
            with tarfile.open(fileobj=file_obj) as tar:
                # We expect the tar to contain the basename of the file
                member = tar.getmembers()[0]
                if not member.isfile():
                     return "Error: Target is not a file."
                f = tar.extractfile(member)
                return f.read().decode('utf-8', errors='ignore')
        except Exception as e:
            return f"Error reading file {safe_path}: {str(e)}"

    def write_file(self, path: str, content: str) -> str:
        """Writes a file to the sandbox with security check."""
        # 1. Security Check
        if not path.startswith("/"):
             path = f"/share/{path}"
             
        # Validate (Only allow write to /share)
        safe_path = self.validate_path(path, allow_read_skills=False)

        container = self.get_sandbox()
            
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            data = content.encode('utf-8')
            tar_info = tarfile.TarInfo(name=os.path.basename(safe_path))
            tar_info.size = len(data)
            tar.addfile(tar_info, io.BytesIO(data))
        
        tar_stream.seek(0)
        
        dir_name = os.path.dirname(safe_path)
        try:
            container.put_archive(dir_name, tar_stream)
            return "Success"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    
    def stop(self):
        """Stops and removes the sandbox container."""
        if self.container:
            try:
                sys.stderr.write(f"[Sandbox] Stopping container {self.container.name}...\n")
                self.container.stop()
                self.container.remove()
                self.container = None
            except Exception as e:
                sys.stderr.write(f"[Sandbox] Error stopping container: {e}\n")

# Global Singleton Manager
sandbox_manager = SandboxManager()

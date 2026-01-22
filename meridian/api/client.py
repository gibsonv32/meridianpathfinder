"""MERIDIAN API Python Client"""

import json
from typing import Any, Dict, List, Optional
from pathlib import Path

import requests
from requests.exceptions import RequestException


class MeridianAPIClient:
    """Python client for MERIDIAN REST API"""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        """
        Initialize API client.
        
        Args:
            base_url: API server URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except RequestException as e:
            raise APIError(f"API request failed: {e}")
    
    def health_check(self) -> bool:
        """Check if API is running"""
        try:
            result = self._request("GET", "/")
            return result.get("status") == "ok"
        except:
            return False
    
    # Project Management
    
    def init_project(self, path: str, name: str, force: bool = False) -> Dict[str, Any]:
        """
        Initialize a new MERIDIAN project.
        
        Args:
            path: Project directory path
            name: Project name
            force: Overwrite existing project
            
        Returns:
            Project initialization result
        """
        return self._request("POST", "/project/init", json={
            "path": path,
            "name": name,
            "force": force
        })
    
    def get_status(self, project_path: str) -> Dict[str, Any]:
        """
        Get project status.
        
        Args:
            project_path: Path to project
            
        Returns:
            Project status including modes and artifacts
        """
        return self._request("GET", "/project/status", params={
            "project_path": project_path
        })
    
    # Mode Execution
    
    def run_mode(self, mode: str, params: Dict[str, Any] = None, headless: bool = False) -> Dict[str, Any]:
        """
        Execute a specific mode.
        
        Args:
            mode: Mode to run (e.g., '0', '2', '6.5')
            params: Mode-specific parameters
            headless: Skip LLM calls
            
        Returns:
            Execution status
        """
        return self._request("POST", "/mode/run", json={
            "mode": mode,
            "params": params or {},
            "headless": headless
        })
    
    # Artifact Management
    
    def list_artifacts(
        self,
        project_path: str,
        artifact_type: Optional[str] = None,
        mode: Optional[str] = None,
        latest_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List project artifacts.
        
        Args:
            project_path: Path to project
            artifact_type: Filter by type
            mode: Filter by mode
            latest_only: Only show latest per type
            
        Returns:
            List of artifact information
        """
        params = {"project_path": project_path}
        if artifact_type:
            params["artifact_type"] = artifact_type
        if mode:
            params["mode"] = mode
        if latest_only:
            params["latest_only"] = True
            
        return self._request("GET", "/artifacts/list", params=params)
    
    def get_artifact(self, project_path: str, artifact_id: str) -> Dict[str, Any]:
        """
        Get specific artifact content.
        
        Args:
            project_path: Path to project
            artifact_id: Artifact UUID
            
        Returns:
            Artifact content
        """
        return self._request("GET", f"/artifacts/{artifact_id}", params={
            "project_path": project_path
        })
    
    # Demo Runner
    
    def run_demo(
        self,
        project_path: str,
        data_path: str,
        target_col: str,
        prediction_row: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Run demo pipeline.
        
        Args:
            project_path: Path to project
            data_path: Path to data CSV
            target_col: Target column name
            prediction_row: Row data for prediction
            
        Returns:
            Demo results including training and prediction
        """
        return self._request("POST", "/demo", json={
            "project_path": project_path,
            "data_path": data_path,
            "target_col": target_col,
            "prediction_row": prediction_row
        })
    
    # Convenience Methods
    
    def run_pipeline(self, project_path: str, modes: List[str], params: Dict[str, Any] = None):
        """
        Run multiple modes in sequence.
        
        Args:
            project_path: Path to project
            modes: List of modes to run in order
            params: Parameters for each mode
        """
        results = []
        for mode in modes:
            mode_params = params.get(mode, {}) if params else {}
            result = self.run_mode(mode, mode_params)
            results.append(result)
            
            # Wait for completion (in real implementation, would poll status)
            import time
            time.sleep(2)
            
        return results
    
    def export_artifacts(self, project_path: str, output_dir: str):
        """
        Export all artifacts to directory.
        
        Args:
            project_path: Path to project
            output_dir: Directory to export to
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        artifacts = self.list_artifacts(project_path)
        for artifact_info in artifacts:
            artifact_id = artifact_info["artifact_id"]
            artifact_type = artifact_info["artifact_type"]
            
            content = self.get_artifact(project_path, artifact_id)
            
            file_path = output_path / f"{artifact_type}_{artifact_id}.json"
            with open(file_path, "w") as f:
                json.dump(content, f, indent=2)
        
        return len(artifacts)


class APIError(Exception):
    """API client error"""
    pass


# CLI Usage Example
def main():
    """Example usage of API client"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MERIDIAN API Client")
    parser.add_argument("--server", default="http://localhost:8000", help="API server URL")
    parser.add_argument("--project", required=True, help="Project path")
    parser.add_argument("command", choices=["status", "artifacts", "demo"])
    args = parser.parse_args()
    
    client = MeridianAPIClient(args.server)
    
    if args.command == "status":
        status = client.get_status(args.project)
        print(json.dumps(status, indent=2))
    
    elif args.command == "artifacts":
        artifacts = client.list_artifacts(args.project, latest_only=True)
        for artifact in artifacts:
            print(f"{artifact['mode']}\t{artifact['artifact_type']}\t{artifact['artifact_id']}")
    
    elif args.command == "demo":
        # Example demo
        result = client.run_demo(
            project_path=args.project,
            data_path="data/sample.csv",
            target_col="target",
            prediction_row={"feature1": 0.5, "feature2": 1.0}
        )
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
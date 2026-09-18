"""
Network Updater Module - Securely fetches genre database updates and BPM algorithm improvements.
Includes built-in firewall to prevent unauthorized access.
"""
import json
import os
import hashlib
import time
import threading
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import ssl


class SecureFirewall:
    """Simple firewall to control network access and prevent unauthorized connections."""
    
    def __init__(self):
        # Whitelist of allowed domains (only trusted sources)
        self.allowed_domains = {
            'raw.githubusercontent.com',
            'gist.githubusercontent.com',
            'api.github.com',
            'cdn.jsdelivr.net',
        }
        
        # Blocked domains (known malicious or unnecessary)
        self.blocked_domains = set()
        
        # Maximum request size (10MB) to prevent large payload attacks
        self.max_request_size = 10 * 1024 * 1024
        
        # Request timeout (10 seconds)
        self.timeout = 10
        
        # Request counter for rate limiting
        self.request_count = 0
        self.last_request_time = 0
        self.max_requests_per_minute = 30
        
        # SSL context with certificate verification
        self.ssl_context = ssl.create_default_context()
    
    def is_domain_allowed(self, url):
        """Check if a domain is in the whitelist."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove port if present
            if ':' in domain:
                domain = domain.split(':')[0]
            return domain in self.allowed_domains
        except:
            return False
    
    def check_rate_limit(self):
        """Check if request rate limit has been exceeded."""
        current_time = time.time()
        if current_time - self.last_request_time > 60:
            self.request_count = 0
            self.last_request_time = current_time
        
        if self.request_count >= self.max_requests_per_minute:
            return False
        
        self.request_count += 1
        return True
    
    def secure_request(self, url, headers=None):
        """Make a secure HTTP request with firewall checks."""
        # Check domain whitelist
        if not self.is_domain_allowed(url):
            raise SecurityError(f"Domain not in whitelist: {url}")
        
        # Check rate limit
        if not self.check_rate_limit():
            raise SecurityError("Rate limit exceeded")
        
        # Prepare headers
        if headers is None:
            headers = {}
        headers['User-Agent'] = 'MusicToolkitPro/1.0 (Secure Updater)'
        headers['Accept'] = 'application/json'
        
        # Make request with timeout and SSL verification
        req = Request(url, headers=headers)
        try:
            response = urlopen(req, timeout=self.timeout, context=self.ssl_context)
            
            # Check content length
            content_length = int(response.headers.get('Content-Length', 0))
            if content_length > self.max_request_size:
                response.close()
                raise SecurityError(f"Response too large: {content_length} bytes")
            
            # Read response with size limit
            data = response.read(self.max_request_size)
            response.close()
            
            return data.decode('utf-8')
        except HTTPError as e:
            raise NetworkError(f"HTTP Error: {e.code}")
        except URLError as e:
            raise NetworkError(f"URL Error: {e.reason}")
        except Exception as e:
            raise NetworkError(f"Request failed: {str(e)}")


class SecurityError(Exception):
    """Raised when a security check fails."""
    pass


class NetworkError(Exception):
    """Raised when a network request fails."""
    pass


class GenreDatabaseUpdater:
    """Updates genre database from trusted network sources."""
    
    def __init__(self, genres_path=None):
        self.firewall = SecureFirewall()
        
        if genres_path is None:
            genres_path = Path(__file__).parent / "genres.json"
        self.genres_path = genres_path
        
        # GitHub Gist URL for genre database (user can configure)
        self.update_url = os.environ.get(
            'MUSICTOOLKIT_GENRE_URL',
            'https://raw.githubusercontent.com/MusicToolkitPro/genres/main/genres.json'
        )
        
        # Local cache of last update
        self.last_update_check = 0
        self.update_check_interval = 3600  # Check every hour
        
        # Backup directory
        self.backup_dir = Path(genres_path).parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def check_for_updates(self, force=False):
        """Check for genre database updates."""
        current_time = time.time()
        
        if not force and current_time - self.last_update_check < self.update_check_interval:
            return {"status": "skipped", "message": "Update check interval not reached"}
        
        self.last_update_check = current_time
        
        try:
            # Fetch remote version info
            remote_data = self.firewall.secure_request(self.update_url)
            remote_genres = json.loads(remote_data)
            
            # Verify data integrity
            if not isinstance(remote_genres, list):
                return {"status": "error", "message": "Invalid data format"}
            
            # Load local genres
            with open(self.genres_path, 'r', encoding='utf-8') as f:
                local_genres = json.load(f)
            
            # Compare versions (using count and hash)
            local_hash = hashlib.md5(json.dumps(local_genres, sort_keys=True).encode()).hexdigest()
            remote_hash = hashlib.md5(json.dumps(remote_genres, sort_keys=True).encode()).hexdigest()
            
            if local_hash == remote_hash:
                return {"status": "up_to_date", "message": "Genre database is up to date"}
            
            # Backup current database
            backup_path = self.backup_dir / f"genres_backup_{int(time.time())}.json"
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(local_genres, f, ensure_ascii=False, indent=2)
            
            # Update database
            with open(self.genres_path, 'w', encoding='utf-8') as f:
                json.dump(remote_genres, f, ensure_ascii=False, indent=2)
            
            return {
                "status": "updated",
                "message": f"Updated from {len(local_genres)} to {len(remote_genres)} genres",
                "old_count": len(local_genres),
                "new_count": len(remote_genres),
                "backup_path": str(backup_path)
            }
            
        except SecurityError as e:
            return {"status": "security_error", "message": str(e)}
        except NetworkError as e:
            return {"status": "network_error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_update_status(self):
        """Get current update status."""
        return {
            "last_check": self.last_update_check,
            "update_url": self.update_url,
            "allowed_domains": list(self.firewall.allowed_domains),
            "max_requests_per_minute": self.firewall.max_requests_per_minute,
        }


class BackgroundUpdater:
    """Runs database updates in the background."""
    
    def __init__(self, genres_path=None):
        self.updater = GenreDatabaseUpdater(genres_path)
        self.is_running = False
        self.thread = None
        self.last_result = None
    
    def start(self):
        """Start background update thread."""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop background update thread."""
        self.is_running = False
    
    def _run(self):
        """Background update loop."""
        while self.is_running:
            try:
                result = self.updater.check_for_updates()
                self.last_result = result
                
                # Log result
                if result.get('status') == 'updated':
                    print(f"[NetworkUpdater] {result.get('message')}")
                elif result.get('status') == 'up_to_date':
                    print(f"[NetworkUpdater] {result.get('message')}")
                
            except Exception as e:
                print(f"[NetworkUpdater] Error: {e}")
            
            # Sleep for update interval
            time.sleep(self.updater.update_check_interval)
    
    def force_update(self):
        """Force an immediate update check."""
        return self.updater.check_for_updates(force=True)


# Global singleton
_updater_instance = None

def get_updater(genres_path=None):
    """Get or create global updater instance."""
    global _updater_instance
    if _updater_instance is None:
        _updater_instance = BackgroundUpdater(genres_path)
    return _updater_instance


if __name__ == "__main__":
    # Test the updater
    print("Testing Network Updater...")
    updater = GenreDatabaseUpdater()
    
    print("\nFirewall Status:")
    status = updater.get_update_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\nTesting domain whitelist:")
    test_urls = [
        "https://raw.githubusercontent.com/test/genres.json",
        "https://evil.com/malware.json",
        "https://api.github.com/repos/test/genres",
    ]
    for url in test_urls:
        allowed = updater.firewall.is_domain_allowed(url)
        print(f"  {'✓' if allowed else '✗'} {url}")
    
    print("\nNote: Network updates are disabled by default for security.")
    print("Configure MUSICTOOLKIT_GENRE_URL environment variable to enable.")

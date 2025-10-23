#!/usr/bin/env python3
"""
Cred Checker - Default Credential Scanner
Tests web servers for default credentials using nmap NSE and custom testing.
"""

import argparse
import asyncio
import csv
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Dict, Optional, Tuple
import random

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' not installed. Install for better output: pip3 install rich")

# Constants
VERSION = "1.0.0"
SCRIPT_DIR = Path(__file__).parent.absolute()
DATA_DIR = SCRIPT_DIR / "data"
RESULTS_DIR = SCRIPT_DIR / "results"
FINGERPRINTS_URL = "https://raw.githubusercontent.com/nnposter/nndefaccts/master/http-default-accounts-fingerprints-nndefaccts.lua"

# Default credentials database
DEFAULT_CREDS = [
    {"username": "admin", "password": "admin", "service": "generic"},
    {"username": "admin", "password": "password", "service": "generic"},
    {"username": "root", "password": "root", "service": "generic"},
    {"username": "root", "password": "toor", "service": "generic"},
    {"username": "administrator", "password": "administrator", "service": "generic"},
    {"username": "admin", "password": "", "service": "generic"},
    {"username": "admin", "password": "1234", "service": "generic"},
    {"username": "admin", "password": "12345", "service": "generic"},
    {"username": "tomcat", "password": "tomcat", "service": "tomcat"},
    {"username": "tomcat", "password": "s3cret", "service": "tomcat"},
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


class CredChecker:
    def __init__(self, args):
        self.args = args
        self.console = Console() if RICH_AVAILABLE else None
        self.db_path = RESULTS_DIR / f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        self.nmap_script = self._find_nmap_script()
        self.fingerprints = DATA_DIR / "http-default-accounts-fingerprints-nndefaccts.lua"
        self.results = []
        
        # Create directories
        DATA_DIR.mkdir(exist_ok=True)
        RESULTS_DIR.mkdir(exist_ok=True)
        
        # Initialize database
        self._init_database()
        
    def _find_nmap_script(self) -> Optional[Path]:
        """Find nmap's http-default-accounts.nse script"""
        locations = [
            SCRIPT_DIR / "http-default-accounts.nse",
            Path("/usr/share/nmap/scripts/http-default-accounts.nse"),
            Path("/usr/local/share/nmap/scripts/http-default-accounts.nse"),
        ]
        for loc in locations:
            if loc.exists():
                return loc
        return None
    
    def _init_database(self):
        """Initialize SQLite database for results"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS scans
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      url TEXT,
                      host TEXT,
                      port INTEGER,
                      proto TEXT,
                      method TEXT,
                      username TEXT,
                      password TEXT,
                      success BOOLEAN,
                      response TEXT,
                      timestamp TEXT)''')
        conn.commit()
        conn.close()
    
    def _save_result(self, result: Dict):
        """Save result to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO scans 
                     (url, host, port, proto, method, username, password, success, response, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (result['url'], result['host'], result['port'], result['proto'],
                   result['method'], result.get('username', ''), result.get('password', ''),
                   result['success'], result.get('response', ''), 
                   datetime.now().isoformat()))
        conn.commit()
        conn.close()
        self.results.append(result)
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed"""
        issues = []
        
        # Check nmap
        if not subprocess.run(['which', 'nmap'], capture_output=True).returncode == 0:
            issues.append("nmap is not installed. Install: sudo apt-get install nmap")
        
        # Check nmap script
        if not self.nmap_script:
            issues.append("http-default-accounts.nse not found. Install nmap-scripts package.")
        
        # Check Python version
        if sys.version_info < (3, 8):
            issues.append(f"Python 3.8+ required (found {sys.version_info.major}.{sys.version_info.minor})")
        
        if issues:
            if self.console:
                self.console.print("[red]Dependency Issues:[/red]")
                for issue in issues:
                    self.console.print(f"  ❌ {issue}")
            else:
                print("Dependency Issues:")
                for issue in issues:
                    print(f"  - {issue}")
            return False
        return True
    
    def download_fingerprints(self) -> bool:
        """Download nndefaccts fingerprints"""
        if self.fingerprints.exists() and not self.args.update:
            return True
        
        try:
            if self.console:
                self.console.print(f"[yellow]Downloading fingerprints from {FINGERPRINTS_URL}...[/yellow]")
            else:
                print(f"Downloading fingerprints from {FINGERPRINTS_URL}...")
            
            import urllib.request
            urllib.request.urlretrieve(FINGERPRINTS_URL, self.fingerprints)
            
            if self.console:
                self.console.print("[green]✓ Fingerprints downloaded[/green]")
            else:
                print("✓ Fingerprints downloaded")
            return True
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Failed to download fingerprints: {e}[/red]")
            else:
                print(f"Failed to download fingerprints: {e}")
            return False
    
    def parse_url(self, url: str) -> Dict:
        """Parse URL into components"""
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        parsed = urlparse(url)
        proto = parsed.scheme or 'http'
        host = parsed.hostname or parsed.netloc.split(':')[0]
        port = parsed.port
        
        if not port:
            port = 443 if proto == 'https' else 80
        
        return {
            'url': url,
            'proto': proto,
            'host': host,
            'port': port,
            'path': parsed.path or '/'
        }
    
    def scan_with_nmap(self, target: Dict) -> Dict:
        """Scan target with nmap NSE script"""
        result = {
            'url': target['url'],
            'host': target['host'],
            'port': target['port'],
            'proto': target['proto'],
            'method': 'nmap-nse',
            'success': False
        }
        
        # Check cache
        if not self.args.no_cache:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''SELECT success, username, password, response FROM scans 
                        WHERE host=? AND port=? AND proto=? AND method='nmap-nse' 
                        ORDER BY timestamp DESC LIMIT 1''',
                     (target['host'], target['port'], target['proto']))
            cached = c.fetchone()
            conn.close()
            
            if cached:
                result['success'] = bool(cached[0])
                result['username'] = cached[1]
                result['password'] = cached[2]
                result['response'] = cached[3]
                result['cached'] = True
                return result
        
        try:
            # Create temp script with custom portrule
            temp_script = SCRIPT_DIR / f"temp_{target['host']}_{target['port']}.nse"
            with open(self.nmap_script, 'r') as f:
                script_content = f.read()
            
            # Modify portrule to match specific port
            script_content = re.sub(
                r'^portrule =.*$',
                f'portrule = shortport.port_or_service( {{{target["port"]}}}, {{"http", "https"}}, "tcp", "open")',
                script_content,
                flags=re.MULTILINE
            )
            
            with open(temp_script, 'w') as f:
                f.write(script_content)
            
            # Run nmap
            cmd = [
                'nmap', '-sT', '-p', str(target['port']),
                '-Pn', '-n',
                '--script', str(temp_script),
                '--script-args', f'http-default-accounts.fingerprintfile={self.fingerprints}',
                target['host']
            ]
            
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.args.timeout)
            output = proc.stdout
            
            # Parse results
            if 'credentials found' in output.lower() or 'valid credentials' in output.lower():
                result['success'] = True
                # Try to extract credentials
                cred_match = re.search(r'(\w+):(\w+)', output)
                if cred_match:
                    result['username'] = cred_match.group(1)
                    result['password'] = cred_match.group(2)
            
            result['response'] = output
            
            # Cleanup
            temp_script.unlink(missing_ok=True)
            
        except subprocess.TimeoutExpired:
            result['response'] = 'Timeout'
        except Exception as e:
            result['response'] = f'Error: {str(e)}'
        
        self._save_result(result)
        return result
    
    def scan_with_custom(self, target: Dict) -> List[Dict]:
        """Scan target with custom credential testing"""
        results = []
        
        try:
            import httpx
        except ImportError:
            if self.console:
                self.console.print("[yellow]httpx not installed. Skipping custom tests. Install: pip3 install httpx[/yellow]")
            return results
        
        # Add random delay for evasion
        if self.args.evasion:
            time.sleep(random.uniform(0.5, 2.0))
        
        for cred in DEFAULT_CREDS:
            result = {
                'url': target['url'],
                'host': target['host'],
                'port': target['port'],
                'proto': target['proto'],
                'method': 'custom-basic',
                'username': cred['username'],
                'password': cred['password'],
                'success': False
            }
            
            try:
                headers = {}
                if self.args.evasion:
                    headers['User-Agent'] = random.choice(USER_AGENTS)
                
                client = httpx.Client(timeout=self.args.timeout, verify=False)
                
                # Try Basic Auth
                response = client.get(
                    f"{target['proto']}://{target['host']}:{target['port']}{target['path']}",
                    auth=(cred['username'], cred['password']),
                    headers=headers,
                    follow_redirects=True
                )
                
                # Check for success indicators
                if response.status_code == 200:
                    # Look for success indicators
                    if any(indicator in response.text.lower() for indicator in ['logout', 'dashboard', 'welcome']):
                        result['success'] = True
                        result['response'] = f"HTTP {response.status_code} - Authenticated"
                        results.append(result)
                        self._save_result(result)
                        break  # Stop on first success
                
                client.close()
                
            except Exception as e:
                result['response'] = f'Error: {str(e)}'
            
            # Rate limiting
            time.sleep(0.1)
        
        return results
    
    def scan_target(self, url: str) -> Dict:
        """Scan a single target"""
        target = self.parse_url(url)
        
        results = {
            'target': target,
            'nmap': None,
            'custom': []
        }
        
        # Nmap scan
        if self.args.nmap:
            results['nmap'] = self.scan_with_nmap(target)
        
        # Custom scan
        if self.args.custom:
            results['custom'] = self.scan_with_custom(target)
        
        return results
    
    def scan_targets(self, targets: List[str]):
        """Scan multiple targets with threading"""
        if self.console:
            self.console.print(f"\n[cyan]Starting scan of {len(targets)} targets with {self.args.threads} threads[/cyan]\n")
        else:
            print(f"\nStarting scan of {len(targets)} targets with {self.args.threads} threads\n")
        
        successful = 0
        failed = 0
        
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task("[cyan]Scanning...", total=len(targets))
                
                with ThreadPoolExecutor(max_workers=self.args.threads) as executor:
                    futures = {executor.submit(self.scan_target, url): url for url in targets}
                    
                    for future in as_completed(futures):
                        url = futures[future]
                        try:
                            result = future.result()
                            
                            # Check if any test was successful
                            if (result['nmap'] and result['nmap']['success']) or \
                               any(r['success'] for r in result['custom']):
                                successful += 1
                                if self.args.verbose:
                                    self.console.print(f"[green]✓[/green] {url} - Credentials found!")
                            else:
                                failed += 1
                                if self.args.verbose >= 2:
                                    self.console.print(f"[red]✗[/red] {url} - No credentials")
                        except Exception as e:
                            failed += 1
                            if self.args.verbose >= 2:
                                self.console.print(f"[red]✗[/red] {url} - Error: {e}")
                        
                        progress.update(task, advance=1)
        else:
            # Fallback without rich
            with ThreadPoolExecutor(max_workers=self.args.threads) as executor:
                futures = {executor.submit(self.scan_target, url): url for url in targets}
                
                for i, future in enumerate(as_completed(futures), 1):
                    url = futures[future]
                    try:
                        result = future.result()
                        if (result['nmap'] and result['nmap']['success']) or \
                           any(r['success'] for r in result['custom']):
                            successful += 1
                            print(f"[{i}/{len(targets)}] ✓ {url} - Credentials found!")
                        else:
                            failed += 1
                    except Exception as e:
                        failed += 1
                    
                    if i % 10 == 0:
                        print(f"Progress: {i}/{len(targets)}")
        
        return successful, failed
    
    def generate_reports(self):
        """Generate output reports"""
        if not self.results and not self.args.output:
            return
        
        # Load all results from database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM scans WHERE success=1 ORDER BY timestamp DESC')
        successful_scans = c.fetchall()
        conn.close()
        
        if not successful_scans:
            if self.console:
                self.console.print("\n[yellow]No successful credentials found[/yellow]")
            else:
                print("\nNo successful credentials found")
            return
        
        # Terminal output
        if 'terminal' in self.args.output or not self.args.output:
            self._generate_terminal_report(successful_scans)
        
        # CSV output
        if 'csv' in self.args.output:
            self._generate_csv_report(successful_scans)
        
        # HTML output
        if 'html' in self.args.output:
            self._generate_html_report(successful_scans)
    
    def _generate_terminal_report(self, scans):
        """Generate terminal report"""
        if RICH_AVAILABLE:
            table = Table(title="Successful Credential Findings", show_header=True, header_style="bold magenta")
            table.add_column("URL", style="cyan")
            table.add_column("Method", style="green")
            table.add_column("Username", style="yellow")
            table.add_column("Password", style="yellow")
            
            for scan in scans:
                table.add_row(
                    f"{scan[3]}://{scan[2]}:{scan[4]}",
                    scan[5],
                    scan[6] or "N/A",
                    scan[7] or "N/A"
                )
            
            self.console.print("\n")
            self.console.print(table)
            self.console.print(f"\n[green]Total successful: {len(scans)}[/green]")
        else:
            print("\n=== Successful Credential Findings ===")
            for scan in scans:
                print(f"\nURL: {scan[3]}://{scan[2]}:{scan[4]}")
                print(f"Method: {scan[5]}")
                print(f"Username: {scan[6] or 'N/A'}")
                print(f"Password: {scan[7] or 'N/A'}")
            print(f"\nTotal successful: {len(scans)}")
    
    def _generate_csv_report(self, scans):
        """Generate CSV report"""
        csv_path = RESULTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['URL', 'Host', 'Port', 'Protocol', 'Method', 'Username', 'Password', 'Timestamp'])
            
            for scan in scans:
                writer.writerow([
                    scan[1], scan[2], scan[4], scan[3], scan[5], scan[6], scan[7], scan[10]
                ])
        
        if self.console:
            self.console.print(f"[green]✓ CSV report saved: {csv_path}[/green]")
        else:
            print(f"✓ CSV report saved: {csv_path}")
    
    def _generate_html_report(self, scans):
        """Generate HTML report"""
        html_path = RESULTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Credential Scan Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        h1 {{ color: #333; }}
        .summary {{ background: #fff; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; background: #fff; }}
        th {{ background: #4CAF50; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f5f5f5; }}
        .critical {{ color: #d32f2f; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Default Credential Scan Report</h1>
    <div class="summary">
        <p><strong>Scan Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total Findings:</strong> <span class="critical">{len(scans)}</span></p>
    </div>
    <table>
        <tr>
            <th>URL</th>
            <th>Method</th>
            <th>Username</th>
            <th>Password</th>
            <th>Timestamp</th>
        </tr>
"""
        
        for scan in scans:
            html += f"""
        <tr>
            <td>{scan[3]}://{scan[2]}:{scan[4]}</td>
            <td>{scan[5]}</td>
            <td>{scan[6] or 'N/A'}</td>
            <td>{scan[7] or 'N/A'}</td>
            <td>{scan[10]}</td>
        </tr>
"""
        
        html += """
    </table>
</body>
</html>
"""
        
        with open(html_path, 'w') as f:
            f.write(html)
        
        if self.console:
            self.console.print(f"[green]✓ HTML report saved: {html_path}[/green]")
        else:
            print(f"✓ HTML report saved: {html_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Cred Checker - Default Credential Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://192.168.1.1
  %(prog)s -f targets.txt
  %(prog)s -f targets.txt --threads 50 --output html,csv
  %(prog)s --update
  %(prog)s --doctor
        """
    )
    
    parser.add_argument('target', nargs='?', help='Target URL or file with URLs')
    parser.add_argument('-f', '--file', help='File containing target URLs (one per line)')
    parser.add_argument('-t', '--threads', type=int, default=20, help='Number of threads (default: 20)')
    parser.add_argument('--timeout', type=int, default=30, help='Timeout in seconds (default: 30)')
    parser.add_argument('--nmap', action='store_true', default=True, help='Use nmap NSE scanning (default: True)')
    parser.add_argument('--custom', action='store_true', default=True, help='Use custom credential testing (default: True)')
    parser.add_argument('--no-nmap', dest='nmap', action='store_false', help='Disable nmap scanning')
    parser.add_argument('--no-custom', dest='custom', action='store_false', help='Disable custom testing')
    parser.add_argument('--no-cache', action='store_true', help='Ignore cached results')
    parser.add_argument('--output', default='terminal', help='Output formats: terminal,html,csv (comma-separated)')
    parser.add_argument('--evasion', action='store_true', help='Enable simple evasion (delays, UA rotation)')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Verbose output (-v, -vv, -vvv)')
    parser.add_argument('--update', action='store_true', help='Update fingerprints and exit')
    parser.add_argument('--doctor', action='store_true', help='Check dependencies and exit')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    
    args = parser.parse_args()
    
    # Parse output formats
    if args.output:
        args.output = [fmt.strip() for fmt in args.output.split(',')]
    
    checker = CredChecker(args)
    
    # Handle special commands
    if args.doctor:
        checker.check_dependencies()
        sys.exit(0)
    
    if args.update:
        checker.download_fingerprints()
        sys.exit(0)
    
    # Check dependencies
    if not checker.check_dependencies():
        sys.exit(1)
    
    # Download fingerprints if needed
    if not checker.download_fingerprints():
        sys.exit(1)
    
    # Get targets
    targets = []
    if args.file:
        with open(args.file, 'r') as f:
            targets = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    elif args.target:
        targets = [args.target]
    else:
        parser.print_help()
        sys.exit(1)
    
    # Run scan
    start_time = time.time()
    successful, failed = checker.scan_targets(targets)
    duration = time.time() - start_time
    
    # Generate reports
    checker.generate_reports()
    
    # Summary
    if checker.console:
        checker.console.print("\n" + "="*60)
        checker.console.print(f"[bold]Scan Complete[/bold]")
        checker.console.print(f"Duration: {duration:.2f}s")
        checker.console.print(f"Successful: [green]{successful}[/green]")
        checker.console.print(f"Failed: [red]{failed}[/red]")
        checker.console.print(f"Database: {checker.db_path}")
        checker.console.print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("Scan Complete")
        print(f"Duration: {duration:.2f}s")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Database: {checker.db_path}")
        print("="*60 + "\n")


if __name__ == "__main__":
    main()

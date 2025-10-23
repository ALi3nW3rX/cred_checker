# Cred Checker

A fast, multi-threaded default credential scanner for penetration testing. Tests web servers for default/common credentials using both nmap's NSE scripts with enhanced fingerprints and custom credential testing.

## Features

- 🚀 **Fast**: Multi-threaded scanning (10-50 concurrent threads)
- 🎯 **Dual Testing**: Leverages nmap NSE + custom credential testing
- 📊 **Multiple Output Formats**: Terminal, HTML, CSV reports
- 💾 **Smart Caching**: SQLite-based result storage to avoid re-testing
- 🎨 **Beautiful Output**: Rich terminal UI with progress bars
- 🔍 **Enhanced Fingerprints**: Uses nndefaccts database (1000+ fingerprints)
- ⚡ **Scalable**: Handles 10,000+ targets efficiently
- 🛡️ **Safe**: Built-in rate limiting and timeout controls

## Quick Install

### One-Command Install
```bash
curl -sSL https://your-repo/install.sh | bash
```

### Manual Install
```bash
# Clone the repository
git clone https://github.com/your-org/cred-checker.git
cd cred-checker

# Run install script
chmod +x install.sh
./install.sh
```

### Requirements
- Python 3.8+
- nmap
- pip3

The install script will check and help you install missing dependencies.

## Usage

### Basic Examples

```bash
# Check dependencies
cred-checker --doctor

# Scan a single target
cred-checker https://192.168.1.1

# Scan multiple targets from file
cred-checker -f targets.txt

# Scan with 50 threads and generate HTML + CSV reports
cred-checker -f targets.txt --threads 50 --output html,csv

# Verbose output to see all attempts
cred-checker https://target.com -vv

# Enable simple evasion techniques
cred-checker -f targets.txt --evasion
```

### Input File Format

Create a text file with one URL per line:

```
http://192.168.1.1
https://192.168.1.10:8443
http://router.local
https://admin.example.com
```

Comments (lines starting with `#`) are ignored.

### Command-Line Options

```
usage: cred_checker.py [-h] [-f FILE] [-t THREADS] [--timeout TIMEOUT]
                       [--nmap] [--custom] [--no-nmap] [--no-custom]
                       [--no-cache] [--output OUTPUT] [--evasion] [-v]
                       [--update] [--doctor] [--version]
                       [target]

positional arguments:
  target                Target URL or file with URLs

optional arguments:
  -h, --help            Show this help message and exit
  -f, --file FILE       File containing target URLs (one per line)
  -t, --threads THREADS Number of threads (default: 20)
  --timeout TIMEOUT     Timeout in seconds (default: 30)
  --nmap                Use nmap NSE scanning (default: True)
  --custom              Use custom credential testing (default: True)
  --no-nmap             Disable nmap scanning
  --no-custom           Disable custom testing
  --no-cache            Ignore cached results
  --output OUTPUT       Output formats: terminal,html,csv (comma-separated)
  --evasion             Enable simple evasion (delays, UA rotation)
  -v, --verbose         Verbose output (-v, -vv, -vvv)
  --update              Update fingerprints and exit
  --doctor              Check dependencies and exit
  --version             Show version and exit
```

## How It Works

### Dual Testing Approach

**1. Nmap NSE Script (Primary)**
- Uses nmap's `http-default-accounts.nse` script
- Enhanced with nndefaccts fingerprint database (1000+ fingerprints)
- Identifies web application and tests known default credentials
- Battle-tested and reliable

**2. Custom Credential Testing (Secondary)**
- Tests common generic credentials (admin/admin, root/root, etc.)
- HTTP Basic Authentication testing
- Form-based authentication detection (future enhancement)
- Validates successful authentication by checking response content

### Testing Strategy

1. **URL Parsing**: Extracts protocol, host, port from target
2. **Cache Check**: Looks for previous results in SQLite database
3. **Nmap Scan**: Runs NSE script with custom fingerprints
4. **Custom Tests**: Tests common credentials via HTTP requests
5. **Result Validation**: Verifies actual authenticated access
6. **Report Generation**: Outputs results in requested formats

### Simple Evasion Features

When `--evasion` is enabled:
- Random delays between requests (0.5-2 seconds)
- User-Agent rotation (legitimate browser UAs)
- Request rate limiting

**Note**: These are basic evasion techniques suitable for internal pentests. No aggressive exploitation or network flooding.

## Output Formats

### Terminal Output
Beautiful, color-coded table with successful findings:
```
╔════════════════════════════════════════════════════════════╗
║         Successful Credential Findings                      ║
╚════════════════════════════════════════════════════════════╝
┌────────────────────────┬─────────┬──────────┬──────────┐
│ URL                    │ Method  │ Username │ Password │
├────────────────────────┼─────────┼──────────┼──────────┤
│ http://192.168.1.1:80  │ nmap    │ admin    │ admin    │
└────────────────────────┴─────────┴──────────┴──────────┘
```

### HTML Report
Professional HTML report with:
- Summary statistics
- Sortable table of findings
- Timestamps for audit trail
- Clean, printable format

### CSV Export
Machine-readable CSV for import into other tools:
```csv
URL,Host,Port,Protocol,Method,Username,Password,Timestamp
http://192.168.1.1,192.168.1.1,80,http,nmap-nse,admin,admin,2024-10-23T10:30:00
```

### SQLite Database
All results stored in SQLite database for:
- Result caching
- Historical tracking
- Custom queries
- Integration with other tools

## Default Credentials Tested

The tool tests these common default credentials:

| Username       | Password       | Common Services        |
|----------------|----------------|------------------------|
| admin          | admin          | Routers, cameras, NAS  |
| admin          | password       | Generic admin panels   |
| root           | root           | Linux systems          |
| root           | toor           | Kali/pentest distros   |
| administrator  | administrator  | Windows systems        |
| admin          | (blank)        | Various devices        |
| tomcat         | tomcat         | Apache Tomcat          |

Plus 1000+ application-specific credentials via nndefaccts fingerprints.

## Project Structure

```
cred-checker/
├── cred_checker.py              # Main tool
├── install.sh                   # Installation script
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── data/                        # Data files
│   ├── http-default-accounts-fingerprints-nndefaccts.lua
│   └── credentials.json         # Custom credential database
└── results/                     # Scan results
    ├── scan_YYYYMMDD_HHMMSS.db # SQLite database
    ├── report_YYYYMMDD_HHMMSS.html
    └── report_YYYYMMDD_HHMMSS.csv
```

## Troubleshooting

### nmap not found
```bash
# Ubuntu/Debian
sudo apt-get install nmap

# CentOS/RHEL
sudo yum install nmap

# macOS
brew install nmap
```

### Python version too old
```bash
# Check version
python3 --version

# Ubuntu/Debian - add deadsnakes PPA for newer Python
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.10
```

### Permission denied when running
```bash
chmod +x ~/.local/bin/cred-checker
```

### Command not found after install
Add `~/.local/bin` to your PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Performance Tips

### For Large Scans (1000+ targets)
```bash
# Increase threads
cred-checker -f targets.txt --threads 50

# Reduce timeout for faster scans
cred-checker -f targets.txt --threads 50 --timeout 15

# Skip nmap for speed (custom testing only)
cred-checker -f targets.txt --no-nmap --threads 100
```

### For Slow Networks
```bash
# Reduce threads and increase timeout
cred-checker -f targets.txt --threads 5 --timeout 60
```

### Resume Interrupted Scans
```bash
# Results are cached in SQLite - just re-run
cred-checker -f targets.txt  # Skips already-tested hosts
```

## Security Notes

⚠️ **This tool is for authorized penetration testing only!**

- Only use on systems you own or have explicit permission to test
- Default credential testing is **not** exploitation or brute forcing
- Built-in rate limiting prevents network disruption
- No malicious payloads or vulnerability exploitation
- Tool generates audit logs for compliance

## Contributing

Contributions welcome! To add new default credentials:

1. Edit the `DEFAULT_CREDS` list in `cred_checker.py`
2. Or submit fingerprints to the nndefaccts project

## License

MIT License - See LICENSE file for details

## Credits

- **nmap**: Network scanning framework
- **nndefaccts**: Enhanced fingerprint database by nnposter
- **Original bash script**: InfoSec Matter team
- **Python rewrite**: [Your Team Name]

## Support

For issues, questions, or feature requests:
- GitHub Issues: https://github.com/your-org/cred-checker/issues
- Internal Slack: #pentest-tools

## Changelog

### v1.0.0 (2024-10-23)
- Initial Python rewrite
- Multi-threaded scanning
- SQLite result caching
- HTML/CSV report generation
- Rich terminal output
- Custom credential testing
- Simple evasion features

---

**Happy Hunting! 🎯**

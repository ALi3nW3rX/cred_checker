
# Cred Checker - Quick Start Guide

**For the team: Get up and running in 2 minutes!**

## Installation (30 seconds)

### Option 1: One-Command Install
```bash
curl -sSL https://your-internal-repo/install.sh | bash
```

### Option 2: From Shared Drive
```bash
cd /path/to/shared/cred-checker
./install.sh
```

After installation:
```bash
# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
cred-checker --doctor
```

## Common Use Cases

### 1. Single Target Quick Check
```bash
cred-checker https://192.168.1.1
```

### 2. Scan Your Target List
```bash
# Create targets.txt with your IPs/URLs
cred-checker -f targets.txt
```

### 3. Fast Scan (More Threads)
```bash
cred-checker -f targets.txt --threads 50
```

### 4. Generate Client Report
```bash
# HTML + CSV for deliverables
cred-checker -f targets.txt --output html,csv

# Reports saved to: ~/.local/share/cred-checker/results/
```

### 5. Large Engagement (1000+ hosts)
```bash
cred-checker -f large_targets.txt --threads 50 --timeout 20
```

## Target File Format

Create `targets.txt`:
```
http://192.168.1.1
https://192.168.1.10:8443
http://admin.company.local
https://10.0.0.100:8080
```

One URL per line. That's it!

## Reading the Output

### Terminal Output
```
✓ https://192.168.1.1 - Credentials found!
  Username: admin
  Password: admin
  Method: nmap-nse
```

### Finding Your Reports
```bash
cd ~/.local/share/cred-checker/results/
ls -ltr  # Most recent files at bottom

# View HTML report
firefox report_20241023_143022.html

# Open CSV in Excel/LibreOffice
libreoffice report_20241023_143022.csv
```

## Common Options Cheat Sheet

```bash
# Fast scan
cred-checker -f targets.txt -t 50

# Verbose (see all attempts)
cred-checker https://target.com -vv

# Only nmap (skip custom testing)
cred-checker -f targets.txt --no-custom

# Only custom testing (faster, skip nmap)
cred-checker -f targets.txt --no-nmap

# Ignore cache (retest everything)
cred-checker -f targets.txt --no-cache

# With evasion
cred-checker -f targets.txt --evasion
```

## Troubleshooting

### "Command not found"
```bash
# Check if installed
ls -la ~/.local/bin/cred-checker

# Fix PATH
export PATH="$HOME/.local/bin:$PATH"
```

### "nmap not installed"
```bash
sudo apt-get install nmap
```

### "Python version too old"
```bash
python3 --version  # Need 3.8+
# Ask IT to upgrade Python or use a different box
```

### Slow scans?
```bash
# Increase threads
cred-checker -f targets.txt --threads 100

# Or skip nmap for speed
cred-checker -f targets.txt --no-nmap --threads 100
```

## Tips & Tricks

### Resume Interrupted Scan
Results are cached! Just re-run the same command:
```bash
cred-checker -f targets.txt  # Skips already-tested hosts
```

### Test on Demo Site First
```bash
# Test with httpbin (no actual creds, but tests the tool)
cred-checker http://httpbin.org/basic-auth/admin/admin
```

### Update Fingerprints
```bash
cred-checker --update
```

### Check What Will Be Scanned
```bash
# Use verbose to see targets being processed
cred-checker -f targets.txt -v
```

## Real-World Workflow

**Day 1 of Engagement:**
```bash
# 1. Create target list from recon
cat discovered_hosts.txt > targets.txt

# 2. Run initial scan
cred-checker -f targets.txt --threads 30 --output html,csv

# 3. Check results
cd ~/.local/share/cred-checker/results/
firefox report_*.html

# 4. Share with team
# Copy HTML report to deliverables folder
```

**Follow-up Testing:**
```bash
# Re-scan specific hosts with verbose
cred-checker https://suspicious-host.com -vv

# Test additional credentials manually if needed
# (Tool already tested common ones)
```

## Integration with Other Tools

### Export to CherryTree/Dradis
```bash
# Use CSV export
cred-checker -f targets.txt --output csv

# Import CSV into your reporting tool
```

### Chain with Nmap Scan
```bash
# 1. Nmap discovery
nmap -sn 192.168.1.0/24 -oG - | grep Up | cut -d' ' -f2 > ips.txt

# 2. Add http:

# 📁 Local Work Integration Guide
**How to Upload Work from Desktop Sorisae Folder to GitHub Repository**

## 🎯 Purpose
This guide explains how to safely integrate market analysis files from the "Sorisae" folder on your desktop into the GitHub repository.

---

## 📋 Prerequisites

### 1. Verify Git Installation

```bash
# Check if Git is installed
git --version

# If not installed, download:
# Windows: https://git-scm.com/download/win
# Mac: brew install git
# Linux: sudo apt-get install git
```

### 2. Configure GitHub Account

```bash
# Set Git user information
git config --global user.name "YourName"
git config --global user.email "your.email@example.com"
```

---

## 🚀 Method 1: Add Local Work to Existing Repository (Recommended)

### Step 1: Clone Repository (One-time only)

```bash
# Execute at desired location (e.g., Desktop)
cd ~/Desktop
git clone https://github.com/parkcheolhong/run_all_shinsegye.py.git
cd run_all_shinsegye.py
```

### Step 2: Copy Local Work Files

```bash
# Copy files from Desktop Sorisae folder
# Example:
cp ~/Desktop/소리새/market_analysis_*.py ./
cp ~/Desktop/소리새/*.md ./docs/

# Or use drag-and-drop in Explorer/Finder
```

### Step 3: Check Changes

```bash
# Check which files were added/modified
git status

# View detailed changes
git diff
```

### Step 4: Stage Changes

```bash
# Add all changes
git add .

# Or add specific files
git add filename.py
git add document.md
```

### Step 5: Commit

```bash
# Save with meaningful commit message
git commit -m "Market Analysis: Add local work files"

# More detailed commit message example
git commit -m "Market Analysis: Add new analysis modules

- Add market trend analysis feature
- Add competitor analysis report generation
- Improve data visualization"
```

### Step 6: Push to GitHub

```bash
# Upload to remote repository
git push origin main

# Or push to new branch
git checkout -b feature/market-analysis
git push origin feature/market-analysis
```

---

## 🔄 Method 2: Regular Synchronization Workflow

### Daily Work Flow

```bash
# 1. Get latest changes
git pull origin main

# 2. Work locally (Desktop Sorisae folder)
# ... modify/add files ...

# 3. Copy work files to repository
cp ~/Desktop/소리새/*.py ./
cp ~/Desktop/소리새/*.md ./

# 4. Add changes and commit
git add .
git commit -m "Market Analysis: [Date] Update work content"

# 5. Push
git push origin main
```

### Use Automation Script

```bash
# Use sync_local_work.sh script (see section below)
./sync_local_work.sh

# Windows users:
sync_local_work.bat
```

---

## 🛠️ Method 3: Using GitHub Desktop (GUI Method)

### Step 1: Install GitHub Desktop
- Download: <https://desktop.github.com/>

### Step 2: Clone Repository
1. File → Clone Repository
2. Enter `parkcheolhong/run_all_shinsegye.py` in URL tab
3. Select Local Path and Clone

### Step 3: Add Files
1. Copy files from Desktop Sorisae folder in Explorer
2. Paste into cloned repository folder
3. GitHub Desktop automatically detects changes

### Step 4: Commit and Push
1. Check changed files in left panel
2. Enter commit message
3. Click "Commit to main" button
4. Click "Push origin" button

---

## 📁 Recommended File Structure for Market Analysis Work

```
run_all_shinsegye.py/
├── run_all_shinsegye.py          # Main execution file
├── MARKET_ANALYSIS_REPORT.md     # Market analysis report (already exists)
├── market_analysis/              # Market analysis dedicated folder (create new)
│   ├── __init__.py
│   ├── trend_analyzer.py         # Trend analysis
│   ├── competitor_analysis.py    # Competitor analysis
│   ├── revenue_model.py          # Revenue model analysis
│   └── reports/                  # Analysis reports
│       ├── weekly_report.md
│       └── monthly_report.md
├── data/                         # Analysis data
│   └── market_data/
│       ├── trends.csv
│       └── competitors.json
└── docs/                         # Documentation
    └── market_analysis_guide.md
```

---

## ⚠️ Precautions

### 1. Exclude Sensitive Information

```bash
# Add to .gitignore file to exclude
echo "*.secret" >> .gitignore
echo "config.local.py" >> .gitignore
echo "API_KEYS.txt" >> .gitignore
```

### 2. Be Careful with Large Files

```bash
# For files over 100MB, use Git LFS
git lfs install
git lfs track "*.xlsx"
git lfs track "*.psd"
```

### 3. Conflict Resolution

```bash
# When conflict occurs
git pull origin main  # Get latest changes
# Manually edit conflict files
git add .
git commit -m "Resolve conflicts"
git push origin main
```

---

## 🎯 Market Analysis Work Specific Guide

### Local Work Folder Structure (Desktop/Sorisae)

```
소리새/
├── 시장분석/
│   ├── daily_trend_analysis.xlsx
│   ├── competitor_research.md
│   └── revenue_model_calculation.py
├── 데이터/
│   └── market_raw_data.csv
└── 리포트/
    └── weekly_market_analysis_report.md
```

### Integration Checklist
- [ ] Get latest code: `git pull origin main`
- [ ] Copy work files to appropriate folders
- [ ] Check Python file code style: `flake8 *.py`
- [ ] Run tests: `python -m pytest`
- [ ] Stage changes: `git add .`
- [ ] Write meaningful commit message
- [ ] Verify before push: `git status`
- [ ] Push: `git push origin main`

---

## 📊 Quick Reference Commands

### Basic Git Commands

```bash
# Check repository status
git status

# View changes
git diff

# Add all changes
git add .

# Commit changes
git commit -m "Your message"

# Push to GitHub
git push origin main

# Pull latest changes
git pull origin main

# Create new branch
git checkout -b branch-name

# Switch branch
git checkout branch-name

# View commit history
git log --oneline
```

---

## 🤝 Help

### Troubleshooting
1. **Permission Error**: Verify GitHub account login
2. **Push Failure**: Run `git pull` first
3. **File Conflicts**: Manually edit conflict files then commit
4. **Large Files**: Use Git LFS or compress files

### Additional Resources
- [Official Git Documentation](https://git-scm.com/doc)
- [GitHub Guides](https://guides.github.com/)
- [Pro Git Book](https://git-scm.com/book/en/v2)

---

## 📞 Contact
If you have issues or need help, create an issue:
<https://github.com/parkcheolhong/run_all_shinsegye.py/issues>

---

**✅ Following this guide, you can safely integrate your market analysis work from the Desktop Sorisae folder into the repository!**

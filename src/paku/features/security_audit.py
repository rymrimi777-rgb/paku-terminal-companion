"""
Paku Security Audit Engine
==========================
Comprehensive security analysis:
- Secret detection (API keys, tokens, credentials, private keys)
- Git exposure checks (tracked secrets, .gitignore validation, credential URLs)
- Dependency vulnerability auditing
- Secret redaction and offline safety
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.align import Align
from rich.text import Text
from rich.table import Table

from paku.ui.themes import Theme
from paku.ui.mascot import MascotLoader
from paku.ui.terminal import styled_line, framed_section, build_header, build_mascot_panel

console = Console(legacy_windows=False)

# File patterns that should never be publicly exposed or committed
SENSITIVE_FILE_PATTERNS = [
    r"^\.env(?:\..+)?$",
    r"^id_(?:rsa|ecdsa|ed25519|dsa)(?:\.pub)?$",
    r"^.*\.pem$",
    r"^.*\.key$",
    r"^.*\.pfx$",
    r"^.*\.p12$",
    r"^credentials\.json$",
    r"^client_secret.*\.json$",
    r"^service[-_]account.*\.json$",
    r"^\.htpasswd$",
]

_SENSITIVE_REGEXES = [re.compile(pat, re.IGNORECASE) for pat in SENSITIVE_FILE_PATTERNS]

# Secret Content Signatures with severity and explanation
SECRET_PATTERNS = [
    (
        "AWS Access Key ID",
        re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        "CRITICAL",
        "Potential hardcoded AWS IAM Access Key ID. Revoke and rotate immediately in AWS IAM.",
    ),
    (
        "AWS Secret Access Key",
        re.compile(r"""(?i)(?:aws_secret_access_key|aws_secret_key)\s*[:=]\s*["']?([A-Za-z0-9/+=]{40})["']?"""),
        "CRITICAL",
        "Potential AWS Secret Access Key found. Store secrets in AWS Secrets Manager or environment variables.",
    ),
    (
        "GitHub Personal Access Token (Classic)",
        re.compile(r"\b(ghp_[0-9a-zA-Z]{36})\b"),
        "CRITICAL",
        "GitHub Personal Access Token exposed. Revoke token on GitHub and migrate to fine-grained scoped tokens.",
    ),
    (
        "GitHub Fine-Grained Token",
        re.compile(r"\b(github_pat_[0-9a-zA-Z_]{82})\b"),
        "CRITICAL",
        "GitHub fine-grained access token exposed. Revoke token on GitHub immediately.",
    ),
    (
        "Private Cryptographic Key",
        re.compile(r"(-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----)"),
        "CRITICAL",
        "Private cryptographic key file or string embedded in workspace. Never commit private keys.",
    ),
    (
        "Slack Token",
        re.compile(r"\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b"),
        "HIGH",
        "Slack API token detected. Revoke in Slack App settings.",
    ),
    (
        "Stripe Secret Key",
        re.compile(r"\b(sk_(?:live|test)_[0-9a-zA-Z]{24,})\b"),
        "HIGH",
        "Stripe API key detected. Rotate key in Stripe Dashboard.",
    ),
    (
        "Google Cloud / Firebase API Key",
        re.compile(r"\b(AIza[0-9A-Za-z_-]{35})\b"),
        "HIGH",
        "Google API key detected. Verify key restrictions (HTTP referrers, IP, API services) in GCP Console.",
    ),
    (
        "Generic High-Entropy Secret Assignment",
        re.compile(r"""(?i)\b(?:api_key|apikey|secret_key|auth_token)\s*[:=]\s*["']([A-Za-z0-9_\-]{24,})["']"""),
        "HIGH",
        "Generic credential or secret token assignment detected. Use environment variables or secret vaults.",
    ),
    (
        "JSON Web Token (JWT)",
        re.compile(r"\b(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]{10,}\.[A-Za-z0-9._-]{10,})\b"),
        "MEDIUM",
        "Hardcoded JWT token detected. Ensure tokens are generated at runtime and never persisted in source code.",
    ),
]

IGNORE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "dist", "build", ".idea", ".vscode", "target",
}


def redact_secret(secret_str: str) -> str:
    """Mask sensitive string to prevent credential exposure in logs and output."""
    if not secret_str:
        return "***"
    cleaned = secret_str.strip()
    if len(cleaned) <= 6:
        return "***"
    elif len(cleaned) <= 12:
        return f"{cleaned[:2]}***{cleaned[-2:]}"
    else:
        return f"{cleaned[:4]}***{cleaned[-4:]}"


@dataclass
class Finding:
    category: str      # "SECRET", "GIT_EXPOSURE", "DEPENDENCY", "CONFIG"
    severity: str      # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
    title: str
    target_path: str
    line_number: Optional[int]
    snippet: str
    remediation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _is_sensitive_filename(name: str) -> bool:
    """Check if file name matches sensitive credential patterns."""
    return any(rx.search(name) for rx in _SENSITIVE_REGEXES)


def scan_secrets(root_dir: Path, max_file_size_bytes: int = 2 * 1024 * 1024) -> List[Finding]:
    """Inspect workspace files for sensitive filenames and hardcoded secrets."""
    findings: List[Finding] = []
    root = root_dir.resolve()

    for path in root.rglob("*"):
        # Skip ignored directories
        if any(part in IGNORE_DIRS for part in path.parts):
            continue

        if not path.is_file():
            continue

        rel_str = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)

        # 1. Sensitive filename check
        if _is_sensitive_filename(path.name):
            findings.append(Finding(
                category="SECRET",
                severity="HIGH" if path.name.startswith(".env") else "CRITICAL",
                title=f"Sensitive Secret File Detected: {path.name}",
                target_path=rel_str,
                line_number=None,
                snippet=f"File matching sensitive pattern: {path.name}",
                remediation="Ensure this file is strictly excluded from version control in .gitignore and protected with restricted filesystem permissions.",
            ))

        # Check file size before reading content
        try:
            if path.stat().st_size > max_file_size_bytes:
                continue
        except OSError:
            continue

        # 2. Content regex scanning
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = content.splitlines()
        for line_idx, line in enumerate(lines, 1):
            if len(line) > 1000:  # Skip minified lines
                continue
            for name, pattern, severity, rem in SECRET_PATTERNS:
                match = pattern.search(line)
                if match:
                    secret_raw = match.group(1) if match.groups() else match.group(0)
                    masked = redact_secret(secret_raw)
                    # Create safe snippet
                    safe_line = line.replace(secret_raw, masked).strip()
                    findings.append(Finding(
                        category="SECRET",
                        severity=severity,
                        title=f"{name} Embedded in Source",
                        target_path=rel_str,
                        line_number=line_idx,
                        snippet=safe_line[:120],
                        remediation=rem,
                    ))

    return findings


def scan_git_exposure(root_dir: Path) -> List[Finding]:
    """Inspect Git exposure: tracked secrets, .gitignore coverage, and credential URLs."""
    findings: List[Finding] = []
    root = root_dir.resolve()

    git_dir = root / ".git"
    if not git_dir.exists():
        findings.append(Finding(
            category="GIT_EXPOSURE",
            severity="INFO",
            title="Non-Git Directory",
            target_path=str(root),
            line_number=None,
            snippet="Target folder is not a Git repository",
            remediation="Initialize Git to track change history and protect secrets with .gitignore.",
        ))
        return findings

    git_bin = shutil.which("git")
    if not git_bin:
        findings.append(Finding(
            category="GIT_EXPOSURE",
            severity="INFO",
            title="Git CLI Unavailable",
            target_path=str(root),
            line_number=None,
            snippet="git binary not found on system PATH",
            remediation="Install Git CLI to enable repository exposure checks.",
        ))
        return findings

    # 1. Check tracked files against sensitive patterns
    try:
        out = subprocess.check_output(
            [git_bin, "ls-files"],
            cwd=root, text=True, stderr=subprocess.DEVNULL, timeout=10
        )
        tracked_files = [line.strip() for line in out.splitlines() if line.strip()]
        for f in tracked_files:
            file_name = Path(f).name
            if _is_sensitive_filename(file_name):
                findings.append(Finding(
                    category="GIT_EXPOSURE",
                    severity="CRITICAL",
                    title=f"Sensitive File Committed to Git: {file_name}",
                    target_path=f,
                    line_number=None,
                    snippet=f"File is currently tracked by Git index: {f}",
                    remediation=f"Remove from Git index using 'git rm --cached {f}', add to .gitignore, and rotate any exposed keys immediately.",
                ))
    except Exception:
        pass

    # 2. Check .gitignore presence and standard secret exclusions
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        findings.append(Finding(
            category="GIT_EXPOSURE",
            severity="MEDIUM",
            title="Missing .gitignore File",
            target_path=".gitignore",
            line_number=None,
            snippet=".gitignore does not exist in workspace root",
            remediation="Create a .gitignore file to prevent accidental commits of local secrets, build artifacts, and virtual environments.",
        ))
    else:
        try:
            gi_content = gitignore.read_text(encoding="utf-8", errors="replace")
            # If local .env exists but .gitignore does not mention .env
            has_env_file = any(p.name.startswith(".env") for p in root.iterdir() if p.is_file())
            if has_env_file and ".env" not in gi_content:
                findings.append(Finding(
                    category="GIT_EXPOSURE",
                    severity="HIGH",
                    title=".gitignore Does Not Exclude .env Files",
                    target_path=".gitignore",
                    line_number=None,
                    snippet="Local .env file exists in root, but '.env' is not referenced in .gitignore",
                    remediation="Add '.env' and '.env.*' to .gitignore to prevent accidental credential commits.",
                ))
        except Exception:
            pass

    # 3. Check for plaintext credentials in Git remote configuration
    try:
        remotes_out = subprocess.check_output(
            [git_bin, "remote", "-v"],
            cwd=root, text=True, stderr=subprocess.DEVNULL, timeout=5
        )
        for line in remotes_out.splitlines():
            # Check for embedded user:pass@ format
            cred_match = re.search(r"https?://([^@/]+:[^@/]+)@", line)
            if cred_match:
                masked_remote = line.replace(cred_match.group(1), "***:***")
                findings.append(Finding(
                    category="GIT_EXPOSURE",
                    severity="CRITICAL",
                    title="Plaintext Credentials Embedded in Git Remote URL",
                    target_path=".git/config",
                    line_number=None,
                    snippet=masked_remote.strip(),
                    remediation="Remove embedded credentials from remote URL. Use SSH keys or a Git credential helper instead.",
                ))
                break
    except Exception:
        pass

    return findings


def scan_dependencies(root_dir: Path) -> List[Finding]:
    """Inspect dependency manifests and run reputable vulnerability audits when available."""
    findings: List[Finding] = []
    root = root_dir.resolve()

    manifests: Dict[str, str] = {
        "pyproject.toml": "Python (pyproject.toml)",
        "requirements.txt": "Python (requirements.txt)",
        "package.json": "Node.js (package.json)",
        "Cargo.toml": "Rust (Cargo.toml)",
    }

    found_manifests = [m for m in manifests if (root / m).exists()]

    if not found_manifests:
        findings.append(Finding(
            category="DEPENDENCY",
            severity="INFO",
            title="No Supported Dependency Manifests Detected",
            target_path=str(root),
            line_number=None,
            snippet="No pyproject.toml, requirements.txt, or package.json found",
            remediation="Audit will activate automatically once dependency manifests are present.",
        ))
        return findings

    for m in found_manifests:
        findings.append(Finding(
            category="DEPENDENCY",
            severity="INFO",
            title=f"Detected Manifest: {manifests[m]}",
            target_path=m,
            line_number=None,
            snippet=f"Active manifest file: {m}",
            remediation="Keep dependencies up to date with automated security auditing.",
        ))

    # Python pip-audit check if Python manifests exist
    if any("pyproject.toml" in m or "requirements.txt" in m for m in found_manifests):
        pip_audit = shutil.which("pip-audit")
        if pip_audit:
            try:
                cmd = [pip_audit, "--format", "json"]
                res = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=30)
                if res.stdout:
                    try:
                        audit_data = json.loads(res.stdout)
                        dependencies = audit_data.get("dependencies", [])
                        vuln_count = 0
                        for dep in dependencies:
                            vulns = dep.get("vulns", [])
                            for v in vulns:
                                vuln_count += 1
                                v_id = v.get("id", "Unknown")
                                v_desc = v.get("description", "Vulnerability advisory")[:100]
                                fix_versions = v.get("fix_versions", [])
                                findings.append(Finding(
                                    category="DEPENDENCY",
                                    severity="HIGH",
                                    title=f"Vulnerability in {dep.get('name')} ({v_id})",
                                    target_path=found_manifests[0],
                                    line_number=None,
                                    snippet=f"{v_id}: {v_desc}",
                                    remediation=f"Upgrade {dep.get('name')} to safe version: {', '.join(fix_versions) if fix_versions else 'latest'}",
                                ))
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass
        else:
            findings.append(Finding(
                category="DEPENDENCY",
                severity="INFO",
                title="pip-audit Not Installed",
                target_path=found_manifests[0],
                line_number=None,
                snippet="Automated CVE audit tool 'pip-audit' is not installed in current environment.",
                remediation="Run 'pip install pip-audit' to enable automated dependency vulnerability scans. Note: dependencies cannot be confirmed safe without audit tooling.",
            ))

    # Node npm audit check if package.json exists
    if "package.json" in found_manifests:
        npm_bin = shutil.which("npm")
        if npm_bin and (root / "package-lock.json").exists():
            try:
                res = subprocess.run(
                    [npm_bin, "audit", "--json"],
                    cwd=root, capture_output=True, text=True, timeout=20
                )
                if res.stdout:
                    try:
                        audit_json = json.loads(res.stdout)
                        metadata = audit_json.get("metadata", {}).get("vulnerabilities", {})
                        high = metadata.get("high", 0)
                        critical = metadata.get("critical", 0)
                        if critical > 0 or high > 0:
                            findings.append(Finding(
                                category="DEPENDENCY",
                                severity="HIGH" if critical == 0 else "CRITICAL",
                                title=f"NPM Vulnerabilities: {critical} critical, {high} high",
                                target_path="package.json",
                                line_number=None,
                                snippet=f"Total npm vulnerabilities: {sum(metadata.values())}",
                                remediation="Run 'npm audit fix' or review high/critical packages manually.",
                            ))
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass

    return findings


def run_full_security_audit(target_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Execute complete security audit: secrets, git exposure, and dependencies."""
    target = (target_dir or Path.cwd()).resolve()

    secret_findings = scan_secrets(target)
    git_findings = scan_git_exposure(target)
    dep_findings = scan_dependencies(target)

    all_findings = secret_findings + git_findings + dep_findings

    severity_counts = {
        "CRITICAL": sum(1 for f in all_findings if f.severity == "CRITICAL"),
        "HIGH": sum(1 for f in all_findings if f.severity == "HIGH"),
        "MEDIUM": sum(1 for f in all_findings if f.severity == "MEDIUM"),
        "LOW": sum(1 for f in all_findings if f.severity == "LOW"),
        "INFO": sum(1 for f in all_findings if f.severity == "INFO"),
    }

    is_clean = (severity_counts["CRITICAL"] == 0 and severity_counts["HIGH"] == 0)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target": str(target),
        "clean": is_clean,
        "summary": severity_counts,
        "total_findings": len(all_findings),
        "findings": [f.to_dict() for f in all_findings],
    }


def render_security_audit(
    theme: Theme,
    mascot_loader: MascotLoader,
    target_dir: Optional[Path] = None,
    as_json: bool = False,
    wait_for_enter: bool = False,
) -> int:
    """Render comprehensive security audit screen."""
    report = run_full_security_audit(target_dir)
    findings = report["findings"]
    summary = report["summary"]
    is_clean = report["clean"]
    exit_code = 0 if is_clean else 1

    if as_json:
        print(json.dumps(report, indent=2))
        return exit_code

    console.clear()
    console.print()
    console.print(Align.center(build_header("P A K U   S E C U R I T Y   A U D I T", "セキュリティ監査  •  Secrets & Exposure Analysis", theme)))
    console.print()

    mascot_state = "happy" if is_clean else "error" if summary["CRITICAL"] > 0 else "thinking"
    console.print(Align.center(build_mascot_panel(mascot_loader.load(mascot_state), theme)))
    console.print()

    # Findings Table
    if not findings:
        console.print(Align.center(
            styled_line(("✓  Workspace security check clean! No issues detected.", f"bold {theme.success}"))
        ))
    else:
        table = Table(box=None, expand=True, show_header=True, header_style=f"bold {theme.accent}")
        table.add_column("Severity", width=12, justify="center")
        table.add_column("Finding", width=34, style=theme.text)
        table.add_column("Location", width=22, style=theme.dim)
        table.add_column("Action / Remediation", style=theme.muted)

        for item in findings:
            sev = item["severity"]
            if sev == "CRITICAL":
                sev_style = f"bold {theme.error}"
                sev_label = "CRITICAL"
            elif sev == "HIGH":
                sev_style = theme.error
                sev_label = "HIGH"
            elif sev == "MEDIUM":
                sev_style = theme.warning
                sev_label = "MEDIUM"
            elif sev == "LOW":
                sev_style = theme.accent
                sev_label = "LOW"
            else:
                sev_style = theme.dim
                sev_label = "INFO"

            loc = item["target_path"]
            if item.get("line_number"):
                loc += f":L{item['line_number']}"

            table.add_row(
                Text(f"[{sev_label}]", style=sev_style),
                item["title"],
                loc,
                item["remediation"],
            )

        console.print(Align.center(framed_section(table, "Security Findings", theme)))
        console.print()

    # Summary Panel
    sum_text = Text()
    sum_text.append(f"Target: {report['target']}\n", style=theme.muted)
    sum_text.append(f"Critical: {summary['CRITICAL']}  ·  ", style=f"bold {theme.error}" if summary['CRITICAL'] > 0 else theme.dim)
    sum_text.append(f"High: {summary['HIGH']}  ·  ", style=theme.error if summary['HIGH'] > 0 else theme.dim)
    sum_text.append(f"Medium: {summary['MEDIUM']}  ·  ", style=theme.warning if summary['MEDIUM'] > 0 else theme.dim)
    sum_text.append(f"Low: {summary['LOW']}  ·  ", style=theme.accent if summary['LOW'] > 0 else theme.dim)
    sum_text.append(f"Info: {summary['INFO']}", style=theme.muted)

    console.print(Align.center(framed_section(sum_text, "Audit Summary", theme)))
    console.print()

    # Safe notice
    console.print(Align.center(
        styled_line(("🔒 Offline scan: no files or secret values are uploaded to external services. Secrets are redacted.", theme.muted))
    ))
    console.print()

    if wait_for_enter:
        console.print(Align.center(styled_line(("Press Enter to return.", theme.muted))))
        input()

    return exit_code

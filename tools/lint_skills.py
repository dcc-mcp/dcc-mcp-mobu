"""Validate bundled DCC MCP skill metadata."""

from pathlib import Path

from dcc_mcp_core import validate_skill

skills_root = Path(__file__).parents[1] / "src" / "dcc_mcp_mobu" / "skills"
reports = [validate_skill(str(path)) for path in skills_root.iterdir() if path.is_dir()]
assert all(report.is_clean for report in reports), [report.issues for report in reports]
print(f"validated {len(reports)} bundled skills")

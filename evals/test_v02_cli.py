"""Black-box subprocess CLI tests for v0.2; all records are synthetic fixtures."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class V02CLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "synthetic-research"
        self.call("update_project.py", "init", str(self.project),
                  "--name", "SYNTHETIC FIXTURE", "--question", "Example research question")
    def tearDown(self):
        self.tmp.cleanup()

    def call(self, script, *args, expect=0):
        cp = subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            encoding="utf-8", text=True, capture_output=True, timeout=15
        )
        self.assertEqual(cp.returncode, expect,
                         f"{script} {' '.join(args)}\nstdout={cp.stdout}\nstderr={cp.stderr}")
        return json.loads(cp.stdout) if cp.stdout.strip() else None

    def test_cli_branch_milestone_and_session(self):
        project = str(self.project)
        idea = self.call("update_project.py", "add-item", project,
                         "--type", "Idea", "--title", "Candidate A", "--module", "topic")["result"]
        branch = self.call("v02_project.py", "branch-create", project,
                           "--title", "Branch A", "--goal", "Improve transfer",
                           "--stop-condition", "No reproducible gain")
        milestone = self.call("v02_project.py", "milestone-create", project,
                              "--title", "Stage 1", "--criterion", "Baseline reproduced")
        self.call("update_project.py", "link", project, idea["id"], branch["id"],
                  "--relation", "member-of")
        self.call("update_project.py", "link", project, branch["id"], milestone["id"],
                  "--relation", "contributes-to")
        session = self.call("v02_project.py", "session-create", project,
                            "--provider", "codex", "--workspace", "synthetic",
                            "--session-id", "synthetic-session-A")
        self.call("v02_project.py", "session-link", project,
                  "--session-ref", session["id"], "--entity-id", idea["id"],
                  "--role", "idea-origin")
        sessions = self.call("v02_project.py", "session-list", project)
        self.assertEqual(sessions[0]["entity_ids"], [idea["id"]])
        self.call("validate_state.py", project)
        self.call("build_dashboard.py", project)

    def test_cli_provenance_and_migration_preview(self):
        project = str(self.project)
        claim = self.call("update_project.py", "add-item", project,
                          "--type", "Claim", "--title", "Toy claim", "--module", "synthesis")["result"]
        source = self.call("update_project.py", "add-source", project,
                           "--title", "Synthetic unverified document",
                           "--url", "https://example.org/placeholder")["result"]
        link = self.call("v02_project.py", "evidence-link", project,
                         "--claim", claim["id"], "--evidence-id", source["id"],
                         "--stance", "qualifies", "--quality", "unverified",
                         "--scope", "Synthetic metadata only", "--locator", "abstract")
        view = self.call("v02_project.py", "evidence-show", project,
                         "--claim", claim["id"])
        self.assertEqual(view["links"][0]["link"]["id"], link["id"])
        preview = self.call("migrate_state.py", "preview", project)
        self.assertFalse(preview["needs_migration"])
        self.call("validate_state.py", project)

    def test_cli_rejects_unauthorized_milestone_approval(self):
        project = str(self.project)
        milestone = self.call("v02_project.py", "milestone-create", project,
                              "--title", "Cannot self approve",
                              "--criterion", "Human reviewed evidence")
        cp = subprocess.run([sys.executable, str(SCRIPTS / "v02_project.py"),
                             "milestone-accept", project, "--milestone", milestone["id"],
                             "--approval-note", "Agent self approves", "--actor", "agent"],
                            encoding="utf-8", capture_output=True, text=True, timeout=15)
        self.assertNotEqual(cp.returncode, 0)
        self.call("validate_state.py", project)


if __name__ == "__main__":
    unittest.main()

import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from install_harness import operate, NAMES, skill_root

class InstallTests(unittest.TestCase):
    def test_preview_install_conflict_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp)/"workspace"
            project.mkdir()
            root=skill_root("deepseek","project",project)
            self.assertFalse(operate(root,"install")["applied"])
            self.assertFalse(root.exists())
            self.assertTrue(operate(root,"install",True)["applied"])
            self.assertTrue(all(x["owned_unmodified"] for x in operate(root,"doctor")["skills"]))
            with self.assertRaises(ValueError): operate(root,"install",True)
            self.assertFalse(operate(root,"uninstall")["applied"])
            self.assertTrue(operate(root,"uninstall",True)["applied"])
            self.assertTrue(all(not (root/n).exists() for n in NAMES))
    def test_modified_bundle_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"skills"
            operate(root,"install",True)
            marker=root/NAMES[0]/"user-note.txt"
            marker.write_text("local data",encoding="utf-8")
            with self.assertRaises(ValueError): operate(root,"uninstall",True)
            self.assertEqual(marker.read_text(encoding="utf-8"),"local data")
    def test_project_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            self.assertEqual(skill_root("shared","project",p),p.resolve()/".agents"/"skills")
            self.assertEqual(skill_root("deepseek","project",p),p.resolve()/".dsh"/"skills")
            (p/".git").mkdir()
            sub=p/"nested"
            sub.mkdir()
            with self.assertRaises(ValueError): skill_root("deepseek","project",sub)

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mmcore.external_capabilities import evaluate_capability_configuration, resolve_adapter


class ExternalCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = {
            "capabilities": [
                {"id": "candidate_generation", "owner": "local", "providers": ["xiaoma"], "external_decision_allowed": False},
                {"id": "red_team", "owner": "local_review_system", "providers": ["ars"], "external_decision_allowed": False},
                {"id": "workflow_concepts", "owner": "local", "providers": ["automcm", "zhnnky"], "external_decision_allowed": False},
            ],
            "sources": [
                {"id": "xiaoma", "repository": "https://github.com/XiaoMaColtAI/math-modeling-skill", "pinned_commit": "a" * 40, "license": "UNVERIFIED", "integration_mode": "EXTERNAL_ADAPTER", "capabilities": ["candidate_generation"], "authority": "knowledge_provider", "attribution": "XiaoMaColtAI"},
                {"id": "ars", "repository": "https://github.com/Imbad0202/academic-research-skills", "pinned_commit": "b" * 40, "license": "UNVERIFIED", "integration_mode": "EXTERNAL_ADAPTER", "capabilities": ["red_team"], "authority": "reviewer_only", "attribution": "Imbad0202"},
                {"id": "automcm", "repository": "https://github.com/RealSeaberry/AutoMCM-Pro", "pinned_commit": "c" * 40, "license": "UNVERIFIED", "integration_mode": "ABSTRACT_INSPIRED", "capabilities": ["workflow_concepts"], "authority": "inspiration_only", "attribution": "RealSeaberry"},
                {"id": "zhnnky", "repository": "https://github.com/zhnnky329/MathModeling-skills", "pinned_commit": "d" * 40, "license": "UNVERIFIED", "integration_mode": "ABSTRACT_INSPIRED", "capabilities": ["workflow_concepts"], "authority": "inspiration_only", "attribution": "zhnnky329"},
            ],
        }

    def tearDown(self):
        self.tmp.cleanup()

    def write_config(self):
        path = self.root / "config"
        path.mkdir()
        import yaml
        (path / "capability-registry.yaml").write_text(yaml.safe_dump({"schema_version": 1, "capabilities": self.config["capabilities"]}), encoding="utf-8")
        (path / "external-sources.yaml").write_text(yaml.safe_dump({
            "schema_version": 1,
            "rule_version": "test-v1",
            "effective_date": "2026-09-02",
            "source_title": "Test source registry",
            "verified_at": "2026-09-02",
            "sources": self.config["sources"],
        }), encoding="utf-8")

    def test_pinned_sources_and_local_authority_pass(self):
        self.write_config()
        report = evaluate_capability_configuration(self.root)
        self.assertEqual(report["status"], "PASS", report)
        adapter = resolve_adapter(self.root, "red_team", "ars")
        self.assertEqual(adapter["authority"], "findings_only")
        self.assertEqual(adapter["gate_authority"], [])
        self.assertIn("local gates decide", adapter["output_contract"])

    def test_floating_commit_fails_closed(self):
        self.config["sources"][0]["pinned_commit"] = "main"
        self.write_config()
        report = evaluate_capability_configuration(self.root)
        self.assertEqual(report["status"], "FAIL")

    def test_malformed_source_types_fail_closed(self):
        self.config["sources"][0]["pinned_commit"] = []
        self.config["sources"][0]["integration_mode"] = {}
        self.write_config()
        report = evaluate_capability_configuration(self.root)
        self.assertEqual(report["status"], "FAIL")

    def test_external_provider_cannot_be_final_decision_owner(self):
        self.config["capabilities"][0]["owner"] = "xiaoma"
        self.config["capabilities"][0]["external_decision_allowed"] = True
        self.write_config()
        report = evaluate_capability_configuration(self.root)
        self.assertEqual(report["status"], "FAIL")

    def test_unknown_owner_fails_closed(self):
        self.config["capabilities"][0]["owner"] = "attacker"
        self.write_config()
        report = evaluate_capability_configuration(self.root)
        self.assertEqual(report["status"], "FAIL")

    def test_malformed_owner_type_fails_closed(self):
        self.config["capabilities"][0]["owner"] = []
        self.write_config()
        report = evaluate_capability_configuration(self.root)
        self.assertEqual(report["status"], "FAIL")

    def test_malformed_github_repository_url_fails_closed(self):
        self.config["sources"][0]["repository"] = "https://github.com/"
        self.write_config()
        report = evaluate_capability_configuration(self.root)
        self.assertEqual(report["status"], "FAIL")

    def test_unregistered_local_provider_fails_closed(self):
        self.config["capabilities"][0]["providers"] = ["local_fake"]
        self.write_config()
        report = evaluate_capability_configuration(self.root)
        self.assertEqual(report["status"], "FAIL")

    def test_source_capability_mismatch_fails(self):
        self.config["sources"][0]["capabilities"] = ["red_team"]
        self.write_config()
        report = evaluate_capability_configuration(self.root)
        self.assertEqual(report["status"], "FAIL")

    def test_unknown_adapter_returns_structured_failure(self):
        self.write_config()
        result = resolve_adapter(self.root, "candidate_generation", "unknown")
        self.assertEqual(result["status"], "FAIL")

    def test_bundled_source_registry_has_audit_metadata(self):
        import yaml
        path = Path(__file__).resolve().parents[1] / "config" / "external-sources.yaml"
        registry = yaml.safe_load(path.read_text(encoding="utf-8"))
        for field in ("rule_version", "effective_date", "source_title", "verified_at"):
            self.assertIsInstance(registry.get(field), str)
            self.assertTrue(registry[field].strip())

    def test_source_registry_missing_audit_metadata_fails_closed(self):
        self.write_config()
        import yaml
        path = self.root / "config" / "external-sources.yaml"
        registry = yaml.safe_load(path.read_text(encoding="utf-8"))
        registry.pop("verified_at")
        path.write_text(yaml.safe_dump(registry), encoding="utf-8")
        report = evaluate_capability_configuration(self.root)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(check["rule"] == "SOURCE-AUDIT-METADATA-001" for check in report["checks"]))


if __name__ == "__main__":
    unittest.main()

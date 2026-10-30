from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.industry_classifier import classify_jsonl
from src.policy_classifier import (
    DEFAULT_POLICY_TAXONOMY_PATH, PolicyTaxonomy, ZAIPolicyClassifier,
    classify_policy_archive,
)
from src.storage import _preserve_industry_classification


class PolicyClassifierTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = PolicyTaxonomy.load(DEFAULT_POLICY_TAXONOMY_PATH)
        self.classifier = ZAIPolicyClassifier(api_key="test", taxonomy=self.taxonomy)

    def test_taxonomy_and_semantic_path_validation(self):
        self.assertEqual(len(self.taxonomy.categories), 65)
        self.assertIn(("政策",), self.taxonomy.allowed_paths)
        self.assertIn(("政策", "监管落实型政策", "负外部性", "碳市场", "配额分配机制"), self.taxonomy.allowed_paths)
        self.assertIn(("政策", "监管落实型政策", "正外部性", "消费端优惠", "税收抵免"), self.taxonomy.allowed_paths)
        self.assertNotIn(("政策", "正外部性"), self.taxonomy.allowed_paths)
        matches = self.classifier._validate_matches([
            {"path": ["政策"], "confidence": 0.9},
            {"path": ["政策", "监管落实型政策", "负外部性", "碳市场", "配额分配机制"], "confidence": 0.85},
            {"path": ["政策", "NA"], "confidence": 0.99},
        ])
        self.assertEqual([m["path"][-1] for m in matches], ["配额分配机制"])

    def test_policy_fields_and_non_policy_routing(self):
        policy = {"title": "配额公告", "industry_classification_status": "classified"}
        matches = self.classifier._validate_matches([{"path": ["政策", "监管落实型政策", "负外部性", "碳市场", "配额分配机制"], "confidence": 0.95, "reason": "分配碳市场配额"}])
        self.classifier._write_result(policy, matches, "2026-10-30T00:00:00Z")
        self.assertEqual(policy["policy_level_5"], "配额分配机制")
        self.assertEqual(policy["policy_classification_status"], "classified")
        self.assertNotIn("industry_classification_status", policy)
        other = {"title": "普通新闻"}
        self.classifier._write_result(other, [], "2026-10-30T00:00:00Z")
        self.assertEqual(other["policy_classification_status"], "non_policy")
        self.assertEqual(other["policy_level_1"], "")
        parent = {"title": "政策公告"}
        self.classifier._write_result(parent, self.classifier._validate_matches([{"path": ["政策"], "confidence": 0.8}]), "now")
        self.assertEqual(parent["policy_level_2"], "NA")

    def test_archive_metadata_and_industry_skip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "政策正文" / "公告"
            folder.mkdir(parents=True)
            (folder / "正文.txt").write_text("实施碳市场配额分配", encoding="utf-8")
            (folder / "公告.json").write_text('{"title":"配额公告"}', encoding="utf-8")
            reports = [{"source": "环境部—政策", "notices": [{"title": "配额公告", "folder": "政策正文/公告"}]}]
            class Stub:
                def enrich_articles(self, rows):
                    for row in rows:
                        self_ref.classifier._write_result(row, self_ref.classifier._validate_matches([{"path": ["政策", "监管落实型政策", "负外部性", "碳市场", "配额分配机制"], "confidence": 0.9}]), "now")
            self_ref = self
            self.assertEqual(classify_policy_archive(reports, root, Stub()), 1)
            self.assertEqual(json.loads((folder / "公告.json").read_text())["policy_level_5"], "配额分配机制")
            journal = root / "articles.jsonl"
            journal.write_text(json.dumps(reports[0]["notices"][0], ensure_ascii=False) + "\n", encoding="utf-8")
            class FailIndustry:
                status_field = "industry_classification_status"
                version_field = "industry_taxonomy_version"
                completed_statuses = frozenset()
                taxonomy = self.taxonomy
                def enrich_articles(self, rows):
                    if rows:
                        raise AssertionError("policy was sent to industry classifier")
            self.assertEqual(classify_jsonl(FailIndustry(), journal)["classified"], 0)

    def test_content_refresh_keeps_policy_result(self):
        existing = {"title": "旧", "policy_classification_status": "classified", "policy_level_1": "政策", "industry_classification_status": "classified"}
        merged = _preserve_industry_classification({"title": "新"}, existing)
        self.assertEqual(merged["policy_level_1"], "政策")
        self.assertNotIn("industry_classification_status", merged)


if __name__ == "__main__":
    unittest.main()

"""Conservative exact-finding grouping and declared-impact prioritization."""

import hashlib
import json

from .secrets import Redactor

ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def analyze(report):
    groups = {}
    gaps = []
    redactor = Redactor()
    for result in report.results:
        if result.status in {"blocked", "skipped"}:
            gaps.append({"check": result.id, "status": result.status, "reason": result.reason})
            continue
        if result.status == "passed" and not result.flaky:
            continue
        classification = (
            "unstable_check"
            if result.flaky
            else (
                "potential_issue"
                if result.kind == "security"
                else {
                    "failed": "confirmed_deviation",
                    "error": "runner_error",
                    "observation": "ux_observation",
                }.get(result.status, "unverified")
            )
        )
        signature = redactor.clean(
            {
                "kind": result.kind,
                "requirement": result.requirement,
                "oracle": result.oracle,
                "classification": classification,
                "reason": result.reason,
                "actual": result.actual,
            }
        )
        fingerprint = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[
            :16
        ]
        group = groups.setdefault(
            fingerprint,
            {
                "fingerprint": fingerprint,
                "classification": classification,
                "severity": result.severity,
                "priority_source": "Declared configuration; human impact review remains necessary",
                "requirement": result.requirement,
                "oracle": result.oracle,
                "impact": result.impact or "Impact not provided; review the affected requirement.",
                "reproducibility": "Needs independent replay"
                if result.flaky
                else "Recorded oracle/evidence for this run",
                "checks": [],
                "evidence": [],
                "reason": result.reason,
            },
        )
        if ORDER.get(result.severity, 4) < ORDER.get(group["severity"], 4):
            group["severity"] = result.severity
        group["checks"].append(result.id)
        group["evidence"] = sorted(set(group["evidence"] + result.evidence))
    findings = sorted(
        groups.values(), key=lambda g: (ORDER.get(g["severity"], 4), g["fingerprint"])
    )
    return redactor.clean(
        {
            "run_id": report.run_id,
            "findings": findings,
            "coverage_gaps": gaps,
            "grouping": "Exact kind, requirement, oracle, classification, reason and actual result; different defects stay separate.",
        }
    )

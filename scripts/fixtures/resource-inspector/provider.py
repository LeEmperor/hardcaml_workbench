#!/usr/bin/env python3
"""Synthetic PT6 bridge, implementing the frozen A handoff (not ASIC parsing).

Targets are explicitly seeded diagnostic directories. No named observation, project
execution, emission or EDA command is implemented. This fixture intentionally emits
bad payloads for rejection tests; it must never be used as an actual-run provider.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True


def load(path):
    return json.loads(path.read_text())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def emit(value, code=0):
    print(json.dumps(value, allow_nan=False))
    return code


def metric(name, value, unit="um^2", stage="final_physical", scope="macro footprint", classification="derived", reason=None):
    return dict(name=name, value=value, unit=unit, stage=stage,
                definition=name, scope=scope, reason=None if value is not None else (reason or "ownership unavailable"),
                classification=classification)


def answer(base, args):
    if args == ["--version", "--json"]:
        supported = not (base / "unsupported-capability").exists()
        return emit(dict(cli_contract=dict(version=4, capabilities=dict(
            namedflow1=True, resource_inspection1=supported))))
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["resource-inspect"])
    parser.add_argument("target", type=Path)
    parser.add_argument("--kind", choices=["bundle", "coarse_run", "execution", "finalization"], required=True)
    parser.add_argument("--query", choices=["index", "detail", "artifacts", "bytes"], default="index")
    parser.add_argument("--resource-id")
    parser.add_argument("--section")
    parser.add_argument("--expected-digest")
    parser.add_argument("--artifact-id")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("--json", action="store_true", required=True)
    a = parser.parse_args(args)
    target = a.target.resolve()
    if not target.is_relative_to((base / "targets").resolve()):
        raise ValueError("fixture target not allowlisted")
    control = load(target / "control.json")
    # Snapshot before delay, so tests can distinguish a truly late old response.
    generation = control.get("generation", "a")
    sha = digest((target / "control.json").read_bytes())
    mode = control["case"]
    delay = control.get("delay", 0)
    if delay:
        (target / "query-started").write_text(sha)
        time.sleep(min(delay, 35))
    if (base / "deny-queries").exists():
        raise ValueError("fixture provider queries denied after warming")
    if mode == "invalid":
        raise ValueError("synthetic corrupt source; not empty inventory")
    if mode == "malformed":
        print('{"contract":')
        return 0
    if a.query != "index" and a.expected_digest != sha:
        raise ValueError("stale expected source digest")
    if a.offset < 0 or not 1 <= a.limit <= (16384 if a.query == "bytes" else 64):
        raise ValueError("request exceeds page budget")
    provenance = dict(fixture=True, origin="synthetic_public_evidence_projection",
                      original_run_id="be961b2c95f74c81ad6af81ca4d2b269",
                      note="NOT an authenticated run or a named observation", generation=generation)
    common = dict(contract="hardcaml-asic.resource-inspection", schema_version=1,
                  kind=a.kind, target=str(target), query=a.query,
                  source_digest=sha, provenance=provenance,
                  verdict="fail" if mode in ("failed", "exit0-fail") else
                          "not_evaluated" if mode in ("empty", "unavailable", "old-empty") else "pass")
    exit_code = 1 if common["verdict"] == "fail" else 0
    if mode == "exit1-pass":
        exit_code = 1
    if mode == "exit0-fail":
        exit_code = 0
    if a.query != "index" and (base / "query-exit-override.json").exists():
        exit_code = load(base / "query-exit-override.json").get(a.query, exit_code)

    def reply(value):
        return emit(value, exit_code)
    inventory = load(base / "fixtures/augmented.json")["data"]["resource_inventory"][0]
    unavailable = mode in ("flops", "fallback", "named") or a.kind == "bundle"
    area = control.get("area", 28127.104)
    row = dict(id="program", contract=inventory["requested_contract"], requirement="Exact",
               policy=inventory["policy"], implementation="RM_IHPSG13_1P_256x16_c2_bm_bist",
               reason="Exact_mapping", role=control.get("role", "Selected_implementation"),
               instances=["hc_resource_7_program"], synthesis="matched", final="matched",
               measurements=[metric("macro_footprint_area", area)],
               sections=[dict(id=name, count=count, status="available") for name, count in (
                   ("inventory", 1), ("synthesis", 1), ("final", 1), ("geometry", 1),
                   ("timing", 186), ("electrical", 372), ("provenance", 1))])
    if unavailable:
        row.update(synthesis="unavailable", final="unavailable", instances=[])
        row["measurements"] = [metric("macro_footprint_area", None)]
    if mode in ("flops", "fallback"):
        row.update(implementation="flops", reason="explicit_flops" if mode == "flops" else "flop_fallback",
                   requirement="Flops" if mode == "flops" else "Exact_or_flop_fallback")
    if mode == "incompatible":
        row["measurements"] = [metric("macro_footprint_area", area, stage="synthesis",
                                      scope="combined cell-area estimate")]
    if mode == "failed":
        row["final"] = "missing"
    if mode == "estimate":
        row["measurements"] = [metric("macro_footprint_area", area, classification="estimate",
                                      reason=control.get("reason"))]
    if mode == "original":
        for section in row["sections"]:
            if section["id"] in ("timing", "electrical"):
                section.update(count=0, status="unavailable")
    artifacts = [dict(id=digest(("opaque-source/%d" % n).encode()), label="synthetic-source-%03d" % n,
                      sha256=digest(("resource source %d\n" % n).encode()), format="text")
                 for n in range(76)]
    if a.query == "index":
        if mode == "oversize":
            common["diagnostics"] = ["x" * (2 * 1024 * 1024)]
        else:
            common["diagnostics"] = ["synthetic diagnostic; not new physical evidence"]
        rows = [] if mode in ("empty", "unavailable", "old-empty") else [row]
        if mode == "row-budget":
            rows = [dict(row, id="resource-%04d" % n) for n in range(4097)]
        value = dict(common, rows=rows, measurements=row["measurements"] if mode == "estimate" else [],
                     artifact_count=76, truncated=mode == "truncated", inventory_status="available", inventory_reason=None)
        if mode == "unavailable":
            value.update(inventory_status="unavailable", inventory_reason="no bound historical inventory")
        if mode in ("old", "old-empty"):
            value.pop("inventory_status")
            value.pop("inventory_reason")
            for measurement in value["measurements"] + row["measurements"]:
                measurement.pop("classification", None)
        return reply(value)
    if a.query == "detail":
        if a.resource_id != "program" or a.section not in [s["id"] for s in row["sections"]]:
            raise ValueError("unknown resource/section ID")
        values = dict(inventory=[inventory], geometry=[dict(bounds_um=[40, 81, 276.8, 199.78], area_um2=area)],
                      synthesis=[dict(status=row["synthesis"])], final=[dict(status=row["final"])],
                      provenance=[provenance])
        oracle = load(base / "fixtures/byte-oracles.json")
        values["timing"] = [p["public_path"] for p in oracle["paths"]]
        values["electrical"] = [dict(slew=0.067838, reported_load=0.004815, compliance="not_assessed"),
                                 dict(slew=0.167545, reported_load=None, compliance="not_assessed")]
        if unavailable or mode == "original" and a.section in ("timing", "electrical"):
            values[a.section] = [dict(status="unavailable", reason="no retained proof/ownership")]
        items = [dict(id=a.section + "-%d" % n, title=a.section,
                      fields=[[k, json.dumps(v)] for k, v in value.items()])
                 for n, value in enumerate(values[a.section])]
        if mode == "detail-budget":
            items = [dict(id="too-large", title="oversize", fields=[["value", "x" * 65536]])]
        return reply(dict(common, resource_id=a.resource_id, section=a.section,
                         offset=a.offset, next_offset=min(len(items), a.offset + a.limit),
                         total=len(items), items=items[a.offset:a.offset + a.limit]))
    if a.query == "artifacts":
        return reply(dict(common, offset=a.offset, next_offset=min(76, a.offset + a.limit),
                         total=76, entries=artifacts[a.offset:a.offset + a.limit]))
    artifact = next((item for item in artifacts if item["id"] == a.artifact_id), None)
    if artifact is None:
        raise ValueError("unknown opaque artifact ID")
    n = int(artifact["label"].rsplit("-", 1)[1])
    raw = ("resource source %d\n" % n).encode()
    if a.offset > len(raw):
        raise ValueError("byte offset beyond EOF")
    return reply(dict(common, artifact_id=a.artifact_id, sha256=artifact["sha256"],
                     offset=a.offset, next_offset=min(len(raw), a.offset + a.limit),
                     total=len(raw), bytes_hex=raw[a.offset:a.offset + a.limit].hex()))


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "--fixture-root":
        sys.exit("private --fixture-root required")
    base, args = Path(sys.argv[2]), sys.argv[3:]
    try:
        with (base / "provider-calls.jsonl").open("a") as log:
            log.write(json.dumps(dict(argv=args, time=time.time())) + "\n")
        return answer(base, args)
    except (ValueError, OSError, KeyError) as error:
        return emit(dict(error=str(error), fixture=True), 2)


if __name__ == "__main__":
    sys.exit(main())

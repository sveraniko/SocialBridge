import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path("scripts/registry_to_content_map.py")


def test_registry_to_content_map_success(tmp_path):
    csv_path = tmp_path / "registry.csv"
    out_path = tmp_path / "content_map.json"
    csv_path.write_text(
        "\n".join(
            [
                "campaign_key,start_param,slug,kind,notes,post_url,flow_name",
                "campaign:dress001,DRESS001,dress001,product,Hero,,SB_IG_CAMP_DRESS001",
                "campaign:catalog,,catalog,catalog,Fallback,,SB_IG_FALLBACK",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--in",
            str(csv_path),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(payload) == 2
    assert payload[0]["content_ref"] == "campaign:dress001"
    assert payload[0]["start_param"] == "DRESS001"
    assert payload[1]["content_ref"] == "campaign:catalog"
    assert payload[1]["start_param"] is None


def test_registry_to_content_map_rejects_invalid_values(tmp_path):
    csv_path = tmp_path / "registry_bad.csv"
    out_path = tmp_path / "content_map_bad.json"
    csv_path.write_text(
        "\n".join(
            [
                "campaign_key,start_param,slug,kind,notes,post_url,flow_name",
                "campaign:bad,INVALID VALUE,InvalidSlug,product,broken,,SB_IG_CAMP_BAD",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--in",
            str(csv_path),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "slug" in result.stderr
    assert "start_param" in result.stderr
    assert not out_path.exists()

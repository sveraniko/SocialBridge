from pathlib import Path


def test_baseline_migration_exists_and_contains_constraints():
    file = Path("alembic/versions/0001_baseline_init.py")
    text = file.read_text()
    assert "sb_content_map" in text
    assert "uq_sb_inbound_event_channel_payload_hash" in text
    assert "ck_sb_content_map_slug_re" in text

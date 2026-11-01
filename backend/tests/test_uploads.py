"""Tests for static image uploads and media security headers."""
import io
import os
import pytest
from app.models.enums import UserRole
from tests.conftest import create_location, create_part, create_user, login_as


def test_upload_valid_image_and_nosniff_header(client, db_session):
    loc = create_location(db_session)
    create_user(db_session, employee_id="ADM_UPL1", role=UserRole.STORE_ADMIN, location=loc)
    headers = login_as(client, "ADM_UPL1")

    part = create_part(db_session, part_number="P-UPL-01")

    # 1x1 valid PNG image bytes
    valid_png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00"
        b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    upload_file = io.BytesIO(valid_png_bytes)
    resp = client.post(
        f"/api/admin/parts/{part.id}/image",
        files={"file": ("bearing.png", upload_file, "image/png")},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["image_url"] is not None

    # Request the static image from /uploads/...
    # image_url is usually /uploads/<filename>.png
    static_url = data["image_url"]
    resp_static = client.get(static_url)
    assert resp_static.status_code == 200
    assert resp_static.headers.get("X-Content-Type-Options") == "nosniff"

    # Delete the image
    resp_del = client.delete(f"/api/admin/parts/{part.id}/image", headers=headers)
    assert resp_del.status_code == 200
    assert resp_del.json()["image_url"] is None


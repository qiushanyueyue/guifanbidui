from __future__ import annotations

import json

import requests

from app.services.extractor import extract_standards_deepseek, extract_standards_from_text


class _FakeResponse:
    def __init__(self, payload: dict, *, content: str | None = None) -> None:
        self._payload = payload
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _enable_remote(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_REMOTE_EXTRACTION", "true")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-placeholder")
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)


def test_remote_extraction_defaults_to_v4_flash_and_parses_plain_json(monkeypatch) -> None:
    _enable_remote(monkeypatch)
    captured: dict = {}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return _FakeResponse(
            {"choices": [{"message": {"content": json.dumps([
                {"code": "GB 50016-2014", "name": "建筑设计防火规范", "year": "2014"}
            ], ensure_ascii=False)}}]}
        )

    monkeypatch.setattr(requests, "post", fake_post)

    result = extract_standards_deepseek("请提取规范")

    assert captured["json"]["model"] == "deepseek-v4-flash"
    assert result[0].code == "GB 50016-2014"
    assert result[0].name == "建筑设计防火规范"


def test_remote_extraction_parses_json_fenced_response(monkeypatch) -> None:
    _enable_remote(monkeypatch)
    content = '```json\n[{"code":"JGJ 18-2012","name":"钢筋焊接及验收规程"}]\n```'
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {"choices": [{"message": {"content": content}}]}
        ),
    )

    result = extract_standards_deepseek("请提取规范")

    assert [item.code for item in result] == ["JGJ 18-2012"]


def test_remote_extraction_parses_array_embedded_in_explanation(monkeypatch) -> None:
    _enable_remote(monkeypatch)
    content = '识别结果如下：[{"code":"GB/T 50010-2010","name":"混凝土结构设计规范"}]，请复核。'
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {"choices": [{"message": {"content": content}}]}
        ),
    )

    result = extract_standards_deepseek("请提取规范")

    assert result[0].code == "GB/T 50010-2010"


def test_remote_extraction_discards_malformed_code_without_name(monkeypatch) -> None:
    _enable_remote(monkeypatch)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {"choices": [{"message": {"content": '[{"code":"G B","name":null}]'}}]}
        ),
    )

    assert extract_standards_deepseek("请提取规范") == []


def test_remote_extraction_normalizes_valid_code(monkeypatch) -> None:
    _enable_remote(monkeypatch)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {
                "choices": [
                    {"message": {"content": '[{"code":"GB50016-2014","name":null} ]'}}
                ]
            }
        ),
    )

    result = extract_standards_deepseek("请提取规范")

    assert len(result) == 1
    assert result[0].code == "GB 50016-2014"
    assert result[0].normalized_code == "GB 50016-2014"


def test_remote_extraction_preserves_ocr_code_normalization(monkeypatch) -> None:
    _enable_remote(monkeypatch)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {
                "choices": [
                    {"message": {"content": '[{"code":"JGJ l8-2012","name":null} ]'}}
                ]
            }
        ),
    )

    result = extract_standards_deepseek("请提取规范")

    assert len(result) == 1
    assert result[0].code == "JGJ 18-2012"


def test_remote_extraction_keeps_name_only_reference(monkeypatch) -> None:
    _enable_remote(monkeypatch)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": '[{"code":"G B","name":"钢筋焊接及验收规程"}]'
                        }
                    }
                ]
            }
        ),
    )

    result = extract_standards_deepseek("请提取规范")

    assert len(result) == 1
    assert result[0].code == ""
    assert result[0].normalized_code == ""
    assert result[0].name == "钢筋焊接及验收规程"


def test_remote_prompt_requires_strict_json_and_no_fabrication(monkeypatch) -> None:
    _enable_remote(monkeypatch)
    captured: dict = {}

    def fake_post(url, **kwargs):
        captured.update(kwargs)
        return _FakeResponse({"choices": [{"message": {"content": "[]"}}]})

    monkeypatch.setattr(requests, "post", fake_post)

    assert extract_standards_deepseek("请提取规范") == []

    prompt = captured["json"]["messages"][0]["content"]
    assert "只输出 JSON 数组" in prompt
    assert '"code"' in prompt and '"name"' in prompt
    assert "无法判断" in prompt
    assert "不要臆造" in prompt


def test_remote_extraction_honors_model_override(monkeypatch) -> None:
    _enable_remote(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_MODEL", "custom-model")
    captured: dict = {}

    def fake_post(url, **kwargs):
        captured.update(kwargs)
        return _FakeResponse({"choices": [{"message": {"content": "[]"}}]})

    monkeypatch.setattr(requests, "post", fake_post)

    assert extract_standards_deepseek("请提取规范") == []
    assert captured["json"]["model"] == "custom-model"


def test_remote_extraction_http_failure_is_non_fatal(monkeypatch) -> None:
    _enable_remote(monkeypatch)

    def fake_post(*args, **kwargs):
        raise requests.HTTPError("test failure")

    monkeypatch.setattr(requests, "post", fake_post)

    assert extract_standards_deepseek("请提取规范") == []


def test_remote_extraction_malformed_response_is_non_fatal(monkeypatch) -> None:
    _enable_remote(monkeypatch)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            {"choices": [{"message": {"content": "not JSON"}}]}
        ),
    )

    assert extract_standards_deepseek("请提取规范") == []


def test_local_extraction_remains_first_and_skips_remote(monkeypatch) -> None:
    _enable_remote(monkeypatch)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("remote extraction must not run when local parser finds a standard")

    monkeypatch.setattr(requests, "post", fail_if_called)

    result = extract_standards_from_text("采用 GB 50010-2010。")

    assert [item.code for item in result] == ["GB 50010-2010"]

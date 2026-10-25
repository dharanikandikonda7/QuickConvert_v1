import pytest
from converters.registry import registry, ConversionRegistry


def test_registry_has_converters():
    assert len(registry._converters) > 0


def test_supported_targets_for_pdf():
    targets = registry.get_target_options_for_source("pdf")
    target_dict = {t.target_format: t for t in targets}

    # PDF -> PNG, JPEG, WebP, TXT must be enabled
    assert target_dict["png"].is_enabled is True
    assert target_dict["jpeg"].is_enabled is True
    assert target_dict["webp"].is_enabled is True
    assert target_dict["txt"].is_enabled is True

    # PDF -> PDF must be disabled
    assert target_dict["pdf"].is_enabled is False
    assert "already in pdf" in target_dict["pdf"].disabled_reason.lower()

    # PDF -> DOCX should be disabled with clear explanation
    assert target_dict["docx"].is_enabled is False
    assert len(target_dict["docx"].disabled_reason) > 0


def test_supported_targets_for_png():
    targets = registry.get_target_options_for_source("png")
    target_dict = {t.target_format: t for t in targets}

    assert target_dict["jpeg"].is_enabled is True
    assert target_dict["webp"].is_enabled is True
    assert target_dict["bmp"].is_enabled is True
    assert target_dict["tiff"].is_enabled is True
    assert target_dict["pdf"].is_enabled is True
    assert target_dict["png"].is_enabled is False


def test_empty_or_unknown_source():
    targets = registry.get_target_options_for_source(None)
    for t in targets:
        assert t.is_enabled is False
        assert "no valid file" in t.disabled_reason.lower()


def test_normalization():
    c1 = registry.get_converter("JPG", "PNG")
    c2 = registry.get_converter("jpeg", "png")
    assert c1 is not None
    assert c1 == c2

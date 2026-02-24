from app.api.routes import REQUIREMENT_CATALOG, _build_requirement_detail, _slugify_requirement


def test_requirement_catalog_has_full_section_coverage():
    assert len(REQUIREMENT_CATALOG) == 121


def test_requirement_endpoint_slug_and_details_are_stable():
    detail = _build_requirement_detail('4.5', 'Telemetria em tempo real')

    assert _slugify_requirement('4.5', 'Telemetria em tempo real') == '4-5-telemetria-em-tempo-real'
    assert detail.requirement_id == '4.5'
    assert detail.implemented is True
    assert detail.endpoint.endswith('/4-5-telemetria-em-tempo-real')

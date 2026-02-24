from app.api.routes import STRATEGIC_COVERAGE_MATRIX, STRATEGIC_NEXT_STEPS, strategic_coverage_report


def test_strategic_coverage_matrix_has_expected_items():
    assert len(STRATEGIC_COVERAGE_MATRIX) == 12
    assert any(item[0] == 'Integração com sensores e dispositivos IoT' for item in STRATEGIC_COVERAGE_MATRIX)


def test_strategic_coverage_endpoint_payload_shape():
    report = strategic_coverage_report.__wrapped__() if hasattr(strategic_coverage_report, '__wrapped__') else None
    if report is None:
        import asyncio

        report = asyncio.run(strategic_coverage_report())

    assert 'não atende integralmente' in report.overall_result.lower()
    assert len(report.matrix) == len(STRATEGIC_COVERAGE_MATRIX)
    assert len(report.next_steps) == len(STRATEGIC_NEXT_STEPS)

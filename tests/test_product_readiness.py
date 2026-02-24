import asyncio

from app.api.routes import PRODUCT_MODULES, product_module_detail, product_readiness_report


def test_product_modules_catalog_is_complete_for_requested_scope():
    assert len(PRODUCT_MODULES) == 21
    assert any(module['slug'] == 'integracao-iot-basica' and module['implemented'] for module in PRODUCT_MODULES)


def test_product_readiness_report_endpoint_shape():
    report = product_readiness_report.__wrapped__() if hasattr(product_readiness_report, '__wrapped__') else None
    if report is None:
        report = asyncio.run(product_readiness_report())

    assert 'módulos estratégicos' in report.summary.lower()
    assert len(report.modules) == len(PRODUCT_MODULES)


def test_product_module_detail_for_unknown_slug_returns_catalog_message():
    response = asyncio.run(product_module_detail('nao-existe'))

    assert response.status == 'não catalogado'
    assert response.implemented is False

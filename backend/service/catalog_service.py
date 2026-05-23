# FILE-ID: FILE-BACKEND-SERVICE-CATALOG-SERVICE-PY
# SECTION-ID: SECTION-BACKEND-SERVICE-CATALOG-SERVICE-PY-MAIN
# FEATURE-ID: FEATURE-BACKEND-SERVICE-CATALOG-SERVICE-PY-RUNTIME
# CHUNK-ID: CHUNK-BACKEND-SERVICE-CATALOG-SERVICE-PY-001

def list_catalog_items() -> list[dict]:
    return [
        {'sku': 'starter-kit', 'name': 'Starter Kit', 'price': 39.0, 'inventory': 12, 'category': 'starter'},
        {'sku': 'growth-kit', 'name': 'Growth Kit', 'price': 89.0, 'inventory': 8, 'category': 'growth'},
        {'sku': 'scale-kit', 'name': 'Scale Kit', 'price': 159.0, 'inventory': 4, 'category': 'scale'},
    ]

def build_catalog_facets(items: list[dict]) -> dict:
    categories = sorted({item['category'] for item in items})
    return {'categories': categories, 'in_stock': sum(1 for item in items if item['inventory'] > 0)}

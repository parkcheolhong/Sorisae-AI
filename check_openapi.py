import sys
sys.path.insert(0, '/app')
try:
    from app.main import app
    schema = app.openapi()
    print('OK, routes:', len(schema.get('paths', {})))
except Exception as e:
    import traceback
    traceback.print_exc()

import inspect
from backend.services.project_service import ProjectService

service = ProjectService()
methods = inspect.getmembers(service, predicate=inspect.ismethod)

print("ProjectService Methods:")
for name, value in methods:
    print(f"  - {name}{inspect.signature(value)}")

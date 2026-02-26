"""Lambda 핸들러 - FastAPI를 Mangum으로 래핑"""

from mangum import Mangum
from main import app

handler = Mangum(app, lifespan="off")

import azure.functions as func
from src.blueprints.utils import logger
from src.blueprints.extraction import bp as extraction_bp
from src.blueprints.translation import bp as translation_bp
from src.blueprints.portfolio import bp as portfolio_bp
from src.blueprints.health import bp as health_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

app.register_functions(extraction_bp)
app.register_functions(translation_bp)
app.register_functions(portfolio_bp)
app.register_functions(health_bp)


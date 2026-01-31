import azure.functions as func
from src.blueprints.utils import logger
from src.blueprints.extraction import bp as extraction_bp
from src.blueprints.translation import bp as translation_bp
from src.blueprints.portfolio import bp as portfolio_bp
from src.blueprints.health import bp as health_bp
from src.azure_clients import validate_app_configuration

# Validate configuration on startup
config_status = validate_app_configuration()
if not config_status["valid"]:
    logger.warning("Startup Configuration Warning: The following environment variables are missing: %s", ", ".join(config_status["missing"]))
    if not config_status["blob_status"]["configured"]:
        logger.error("Blob Storage is not configured. Some features (async extraction, large files) will fail.")

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

app.register_functions(extraction_bp)
app.register_functions(translation_bp)
app.register_functions(portfolio_bp)
app.register_functions(health_bp)


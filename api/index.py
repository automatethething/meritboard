from mangum import Mangum
from main import app

# Vercel serverless function handler
handler = Mangum(app, lifespan="off")

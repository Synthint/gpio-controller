from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from utils.pin_mgmt import GPIO_controller


app = FastAPI()
app.mount("/static", StaticFiles(directory="./static"), name="static")

templates = Jinja2Templates(directory="./frontend/templates")
pin_manager = GPIO_controller()

@app.get("/pin/{id}", response_class=HTMLResponse)
async def read_item(request: Request, id: int):
    return templates.TemplateResponse(
        request=request, name="test.html", context={"pin_string": pin_manager.get_pin_string(id) }
    )



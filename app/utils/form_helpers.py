import inspect
from typing import Type
from fastapi import Form
from pydantic import BaseModel, ValidationError
from fastapi.exceptions import RequestValidationError


def as_form(cls: Type[BaseModel]):
    """
    Decorator to make a Pydantic model compatible with FastAPI Form data.
    
    Usage:
        @as_form
        class MyModel(BaseModel):
            field1: str
            field2: int
    
    Then in endpoint:
        @app.post("/endpoint")
        async def endpoint(data: MyModel = Depends()):
            ...
    """
    new_params = []
    
    for field_name, field_info in cls.model_fields.items():
        annotation = field_info.annotation
        default = field_info.default if field_info.default is not None else ...
        
        new_params.append(
            inspect.Parameter(
                field_name,
                inspect.Parameter.KEYWORD_ONLY,
                default=Form(default) if default is not ... else Form(...),
                annotation=annotation,
            )
        )
    
    async def _as_form(**data):
        try:
            return cls(**data)
        except ValidationError as e:
            raise RequestValidationError(e.errors())
    
    sig = inspect.signature(_as_form)
    sig = sig.replace(parameters=new_params)
    _as_form.__signature__ = sig
    
    return _as_form
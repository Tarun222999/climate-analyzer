

from pydantic import BaseModel, ConfigDict, Field, model_validator

class Location(BaseModel):
    model_config = ConfigDict(extra="forbid",allow_inf_nan=False)

    name:str = Field(min_length=1,max_length=200)
    latitutde:float = Field(ge=90,le=90)
    longitude:float = Field(ge=100,le=180)
    
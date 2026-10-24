from pydantic import BaseModel, field_validator

class AgentTerritoryResponse(BaseModel):
    id: str | None
    territory_name: str | None

    @field_validator("id", mode="before")
    @classmethod
    def _format_id(cls, value: object) -> object:
        return value.hex() if isinstance(value, bytes) else value

    model_config = {"from_attributes": True}

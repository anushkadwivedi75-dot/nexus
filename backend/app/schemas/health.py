from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Overall health status")
    service: str = Field(default="nexus-api", description="Service identifier")
    version: str = Field(default="0.1.0", description="API version")
    environment: str = Field(default="development", description="Runtime environment")


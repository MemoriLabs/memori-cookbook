from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.llm import LLMService, get_llm_service

LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

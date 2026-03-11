from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agents.tools import search_symptoms, getmedication_info, find_nearby_hospitals
from app.agents.prompts import MEDICAL_STYSTEM_PROMPT

@dataclass
class ChatResponse:

  message_id: str
  content: str
  metadata: dict[str, object]


def create_medical_agent(model: ChatOpenAI, checkpointer: BaseCheckpointSaver[Any] = None):
  """
  ChatOpenAI 모델과 checkpointer를 받아 의료 에이전트를 생성합니다.
  
  """
  if checkpointer is None:
    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()
  agent = create_agent(
    model=model,
    tools=[search_symptoms, get_medication_info, find_nearby_hospitals],
    system_prompt=MEDICAL_STYSTEM_PROMPT,
    response_fromat=ToolStrategy(ChatResponse),
    checkpointer=checkpointer
  )

  return agent
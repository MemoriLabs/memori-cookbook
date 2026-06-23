import os
from typing import Any

from crewai import Agent, BaseLLM, Crew, Process, Task
from dotenv import load_dotenv
from memori import Memori
from openai import OpenAI

load_dotenv()


PROCESS_ID = "crewai_research_agent"


class MemoriOpenAILLM(BaseLLM):
    """CrewAI LLM adapter that sends every call through a Memori-wrapped client."""

    def __init__(
        self,
        client: OpenAI,
        model: str,
        temperature: float | None = None,
    ) -> None:
        super().__init__(model=model, temperature=temperature)
        self.client = client

    def call(
        self,
        messages: str | list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
    ) -> str:
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""

    def supports_function_calling(self) -> bool:
        return False

    def get_context_window_size(self) -> int:
        return int(os.getenv("OPENAI_CONTEXT_WINDOW", "128000"))


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set in .env")
    return value


def create_memori_llm() -> tuple[Memori, MemoriOpenAILLM]:
    openai_api_key = _get_required_env("OPENAI_API_KEY")
    _get_required_env("MEMORI_API_KEY")
    entity_id = _get_required_env("MEMORI_ENTITY_ID")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))

    client = OpenAI(api_key=openai_api_key)

    # Memori wraps the OpenAI SDK client before CrewAI receives it, so every
    # agent call is intercepted for recall injection and memory capture.
    mem = Memori().llm.register(client)

    # Attribution keeps this user's research memories separate from other users
    # and labels this workflow as the CrewAI research process.
    mem.attribution(entity_id=entity_id, process_id=PROCESS_ID)

    # The same Memori instance and OpenAI client are reused for all agents below,
    # which means the whole crew run shares one session and one memory context.
    llm = MemoriOpenAILLM(client=client, model=model, temperature=temperature)
    return mem, llm


def print_previous_research(mem: Memori, topic: str) -> None:
    print("\nChecking Memori for previous research context...")

    try:
        # Recall surfaces relevant facts from earlier sessions before the crew
        # starts, making it visible that this run is not beginning from scratch.
        memories = mem.recall(
            f"Previous research topics, preferences, and findings about {topic}",
            limit=5,
        )
    except Exception as e:
        print(f"Memori recall was unavailable for this run: {e}")
        return

    if not memories:
        print("No related memories found yet. This may be the first run.")
        return

    print("Memori remembered:")
    if isinstance(memories, dict):
        for item in memories.get("facts", [])[:5]:
            print(f"- {item.get('content', item)}")
        return

    for memory in memories[:5]:
        content = getattr(memory, "content", memory)
        print(f"- {content}")


def create_agents(llm: MemoriOpenAILLM) -> tuple[Agent, Agent, Agent]:
    researcher = Agent(
        role="Researcher",
        goal="Gather practical, relevant findings about the user's research topic.",
        backstory=(
            "You are a careful research specialist who looks for useful patterns, "
            "recent context, open questions, and concrete takeaways."
        ),
        llm=llm,
        verbose=True,
    )

    analyst = Agent(
        role="Analyst",
        goal="Turn raw research notes into clear insights and tradeoffs.",
        backstory=(
            "You are an analytical thinker who finds structure in research, "
            "separates signal from noise, and explains implications plainly."
        ),
        llm=llm,
        verbose=True,
    )

    writer = Agent(
        role="Writer",
        goal="Produce a concise final report that is useful on a second read.",
        backstory=(
            "You are a crisp technical writer who turns analysis into an "
            "organized report with conclusions, caveats, and next steps."
        ),
        llm=llm,
        verbose=True,
    )

    return researcher, analyst, writer


def create_tasks(topic: str, agents: tuple[Agent, Agent, Agent]) -> list[Task]:
    researcher, analyst, writer = agents

    research_task = Task(
        description=(
            "Research this topic: {topic}\n\n"
            "Include key concepts, useful findings, recurring themes, and any "
            "known user preferences or previous findings that appear in memory."
        ),
        expected_output="Detailed research notes with the most important findings.",
        agent=researcher,
    )

    analysis_task = Task(
        description=(
            "Analyze the research notes for {topic}. Identify what matters most, "
            "what is uncertain, and how the findings fit together."
        ),
        expected_output="A structured analysis with key insights and caveats.",
        agent=analyst,
        context=[research_task],
    )

    writing_task = Task(
        description=(
            "Write a clean final report for {topic}. Include an executive summary, "
            "important findings, recommendations, and suggested follow-up work."
        ),
        expected_output="A polished research report in markdown.",
        agent=writer,
        context=[research_task, analysis_task],
    )

    return [research_task, analysis_task, writing_task]


def run_research_crew(topic: str, llm: MemoriOpenAILLM) -> Any:
    agents = create_agents(llm)
    tasks = create_tasks(topic, agents)

    crew = Crew(
        agents=list(agents),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    return crew.kickoff(inputs={"topic": topic})


def main() -> None:
    topic = os.getenv("RESEARCH_TOPIC", "").strip()
    if not topic:
        topic = input("Research topic: ").strip()

    if not topic:
        print("Please provide RESEARCH_TOPIC in .env or enter a topic at runtime.")
        return

    try:
        mem, llm = create_memori_llm()
    except RuntimeError as e:
        if str(e).startswith("MEMORI_API_KEY"):
            print(
                "MEMORI_API_KEY is not set in .env. Add it to enable persistent "
                "cross-session memory for this CrewAI example."
            )
        else:
            print(e)
        return

    print_previous_research(mem, topic)

    result = run_research_crew(topic, llm)

    print("\nFinal report")
    print("=" * 80)
    print(result)


if __name__ == "__main__":
    main()

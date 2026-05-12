# CrewAI Research Agent with Memori

This example builds a three-agent CrewAI research crew with persistent Memori
memory. The crew researches a topic, analyzes the findings, and writes a final
report while remembering prior topics, preferences, and discoveries across runs.

## What It Does

- Creates a `Researcher`, `Analyst`, and `Writer` agent.
- Runs the agents sequentially on one research topic.
- Uses one Memori session for the full crew run.
- Recalls previous research context before the crew starts.
- Saves new research interactions so the next run has continuity.

## Why Memori

CrewAI coordinates the agents. Memori gives the shared OpenAI client long-term
memory.

That means the second run can remember useful details from the first run, such
as:

- Research topics the user already explored
- Preferred report style or level of depth
- Prior findings that should not be rediscovered from scratch
- Follow-up directions from earlier reports

## Without Memori vs With Memori

| Behavior | Without Memori | With Memori |
| --- | --- | --- |
| First run | Agents research the topic normally | Agents research and store useful context |
| Second run | Agents start cold again | Agents recall relevant previous findings |
| User preferences | Must be repeated every time | Can be remembered across sessions |
| Follow-up research | Requires manual recap | Can build on earlier work |
| Shared context | Limited to one CrewAI run | Persists beyond the process lifetime |

## Setup

Install dependencies:

```bash
cd crewai_research_agent
pip install -r requirements.txt
```

Create a `.env` file in this folder:

```bash
OPENAI_API_KEY=<openai_api_key>
MEMORI_API_KEY=<memori_api_key>
MEMORI_ENTITY_ID=<stable_user_or_workspace_id>

# Optional
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.2
OPENAI_CONTEXT_WINDOW=128000
RESEARCH_TOPIC=AI memory systems for multi-agent workflows
```

`MEMORI_API_KEY` enables persistent cloud memory. If it is missing, the example
exits with a clear message instead of failing with a stack trace.

## Run

```bash
python main.py
```

If `RESEARCH_TOPIC` is not set in `.env`, the script asks for a topic at runtime.

## Example Output

```text
Checking Memori for previous research context...
No related memories found yet. This may be the first run.

Final report
================================================================================
# AI Memory Systems for Multi-Agent Workflows

## Executive Summary
...
```

On a later run:

```text
Checking Memori for previous research context...
Memori remembered:
- The user prefers concise research reports with implementation tradeoffs.
- Prior research focused on agent memory, session continuity, and recall quality.

Final report
================================================================================
...
```

## How Memory Works Across Sessions

The example creates one OpenAI SDK client, registers it with Memori, and then
passes that same wrapped client into CrewAI through a small `BaseLLM` adapter.

```python
client = OpenAI(api_key=openai_api_key)
mem = Memori().llm.register(client)
mem.attribution(entity_id=entity_id, process_id="crewai_research_agent")
llm = MemoriOpenAILLM(client=client, model=model)
```

Every agent uses the same `llm` object, so all three agents share the same Memori
session for the run. Memori can inject relevant recalled memories into OpenAI
calls and capture new research context afterward. The next run uses the same
`MEMORI_ENTITY_ID` and process attribution to recall earlier findings.

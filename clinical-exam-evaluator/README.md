# Clinical Exam Evaluator Example

This example demonstrates how to use Memori to build an AI voice agent that evaluates medical candidates (e.g., MRCPCH clinical exam) against a rubric without building complex rule engines.

## Use Case

Build a preparation simulator that:
1. Conducts mock clinical examinations with candidates
2. Automatically extracts structured information from candidate responses
3. Evaluates candidates against a rubric using LLM + structured memory
4. Provides detailed feedback based on extracted skills, facts, and clinical reasoning

## How Memori Helps

Instead of relying on raw conversation transcripts, Memori:
- **Automatically extracts** skills, facts, and events from candidate answers
- **Structures memory** in a queryable format
- **Retrieves relevant context** for evaluation
- **Enables LLM-based scoring** using clean, structured data

## Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   ```

3. **Run the demo**:
   ```bash
   uv run python demo.py
   ```

## What This Example Demonstrates

- **Structured extraction**: Automatically extracts clinical skills, medical knowledge, and reasoning from responses
- **Rubric-based evaluation**: Uses LLM to evaluate against clinical competency rubrics
- **Memory-enhanced scoring**: Retrieves relevant extracted information for accurate assessment
- **Session tracking**: Groups examination sessions for comprehensive evaluation
- **No rule engines needed**: LLM handles evaluation logic using structured memories

## Evaluation Flow

1. **Candidate responds** to clinical scenario
2. **Memori extracts** skills demonstrated, facts mentioned, clinical reasoning
3. **Evaluation prompt** retrieves structured memories
4. **LLM scores** against rubric using clean, structured context
5. **Feedback provided** based on extracted competencies

## Rubric Categories

The example evaluates candidates on:
- **Clinical Knowledge**: Facts and medical information demonstrated
- **Clinical Skills**: Procedures, examination techniques, and practical abilities
- **Communication**: Patient interaction and explanation quality
- **Clinical Reasoning**: Diagnostic approach and decision-making
- **Professionalism**: Ethical considerations and patient-centered care

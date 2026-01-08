import os

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from memori import Memori

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")

# SQLite for simplicity
db_path = "./clinical_exam_demo.db"
database_url = f"sqlite:///{db_path}"

client = OpenAI(api_key=api_key)

engine = create_engine(database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clinical competency rubric
RUBRIC = """
MRCPCH Clinical Competency Rubric:

1. Clinical Knowledge (0-5 points)
2. Clinical Skills (0-5 points)
3. Communication (0-5 points)
4. Clinical Reasoning (0-5 points)
5. Professionalism (0-5 points)
"""

# Pre-defined scenario and candidate response for demo
SCENARIO = """
A 3-year-old child presents to the emergency department with a 2-day history 
of fever (39°C), refusing to eat, and drooling. The child is sitting upright 
and leaning forward. Parents report the child is making a muffled voice and 
having difficulty breathing.

What is your immediate assessment and management approach?
"""

CANDIDATE_RESPONSE = """
This presentation is concerning for acute epiglottitis or severe upper airway 
obstruction. My immediate approach would be:

1. Call for senior help immediately - this is a potential airway emergency
2. Keep the child calm and in their position of comfort (upright)
3. Avoid examining the throat or causing distress
4. Provide high-flow oxygen if tolerated
5. Have emergency airway equipment ready
6. Prepare for potential intubation by an experienced team
7. Consider IV antibiotics once the airway is secured
8. Continuous monitoring of vital signs and oxygen saturation

The priority is airway management while minimizing agitation.
"""


def run_demo():
    """Run the clinical exam evaluation demo"""

    # Setup Memori
    mem = Memori(conn=SessionLocal).openai.register(client)
    mem.attribution(entity_id="demo_candidate_001", process_id="mrcpch-demo")
    mem.config.storage.build()

    print("\n" + "=" * 80)
    print("CLINICAL EXAM EVALUATOR - DEMO")
    print("=" * 80)

    print("\nCLINICAL SCENARIO:")
    print("-" * 80)
    print(SCENARIO)

    print("\nCANDIDATE RESPONSE:")
    print("-" * 80)
    print(CANDIDATE_RESPONSE)
    print()

    # Store the exchange - Memori extracts skills, facts, and reasoning
    print("Processing response with Memori...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are recording a clinical examination response.",
            },
            {
                "role": "user",
                "content": f"Scenario: {SCENARIO}\n\nCandidate Response: {CANDIDATE_RESPONSE}",
            },
        ],
    )
    print("✓ Response stored\n")

    # Evaluate using rubric + Memori's extracted memories
    print("=" * 80)
    print("EVALUATION")
    print("=" * 80)

    evaluation_prompt = f"""
You are evaluating a medical candidate's performance in a clinical examination.

{RUBRIC}

Based on the candidate's response, provide:
1. Score for each rubric category (0-5)
2. Specific observations from their response
3. Key strengths
4. Areas for improvement

Be specific and reference what the candidate said.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a clinical examiner providing evaluation and feedback.",
            },
            {"role": "user", "content": evaluation_prompt},
        ],
    )

    print(f"\n{response.choices[0].message.content}\n")
    print("=" * 80)

    print(f"\n✓ Demo completed! Evaluation saved to: {db_path}")
    print("  Memori has stored structured memories for future evaluations.\n")


if __name__ == "__main__":
    try:
        run_demo()
    except Exception as e:
        print(f"\n Error: {e}")

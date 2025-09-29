import openai

def generate_questions(resume_data, model="gpt-4", temp=0.7):
    """
    Generates 5 rounds of interview questions and ideal answers based on resume_data.
    Returns: List of rounds. Each round is a list of dicts with question, ideal_answer, category.
    """
    rounds = []
    sheet_to_category = list(resume_data.keys())  # Ensure order: [Education, Experience, Projects, Skills, Personality]

    for i, sheet in enumerate(sheet_to_category):
        questions = []
        base_info = resume_data[sheet]
        prompt = build_prompt(sheet, base_info)

        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": f"You are an expert HR conducting a mock interview. Speak in professional tone."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temp,
                max_tokens=700
            )
            raw_output = response['choices'][0]['message']['content']
            questions = parse_output_to_questions(raw_output, category=sheet)

        except Exception as e:
            print(f"❌ Error generating questions for {sheet}: {e}")
            questions = [{"question": f"Tell me something about your {sheet.lower()}.", "ideal_answer": "", "category": sheet}]

        rounds.append(questions)

    return rounds


def build_prompt(sheet_name, info_dict):
    """
    Builds a prompt for OpenAI using resume info from one sheet.
    """
    intro = f"Here is a candidate's {sheet_name} information:\n"
    body = "\n".join([f"{k.replace('_', ' ')}: {v}" for k, v in info_dict.items()])
    instruction = "\n\nBased on this, generate 5 interview questions. For each, also write an ideal answer. Format:\nQ: ...\nA: ..."

    return intro + body + instruction


def parse_output_to_questions(raw_output, category):
    """
    Parses OpenAI output into a list of {question, ideal_answer, category}
    """
    questions = []
    lines = raw_output.strip().split("\n")
    current_q = {}
    for line in lines:
        if line.strip().startswith("Q:"):
            if current_q:
                questions.append(current_q)
                current_q = {}
            current_q["question"] = line.strip()[2:].strip()
        elif line.strip().startswith("A:"):
            current_q["ideal_answer"] = line.strip()[2:].strip()
            current_q["category"] = category
    if current_q:
        questions.append(current_q)
    return questions
